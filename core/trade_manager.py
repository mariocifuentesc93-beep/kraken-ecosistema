from core.execution_modes import ExecutionMode
from core.event_bus import event_bus
from core.events import (
    OperationCreatedEvent,
    OperationOpenedEvent,
    OperationClosedEvent,
    RiskRejectedEvent,
)


class TradeManager:

    def __init__(self):

        self.execution_mode = ExecutionMode.OFF

    # ---------------------------------------------------------

    def _load_execution_mode(self):

        return self.execution_mode

    # ---------------------------------------------------------

    def reload(self):

        return self.execution_mode

    # ---------------------------------------------------------

    def _log_preflight(
        self, signal, profile, account, state, code, reason
    ):
        from repositories.log_repository import log_repository

        sizing = (getattr(signal, "metadata", None) or {}).get(
            "position_sizing", {}
        )
        message = (
            f"Signal ID={getattr(signal, 'external_signal_id', None) or getattr(signal, 'id', None)} | "
            f"Perfil={getattr(profile, 'name', None)} | "
            f"Cuenta={getattr(account, 'name', None)} | "
            f"Terminal={getattr(account, 'mt5_terminal_id', None)} | "
            f"Símbolo={getattr(signal, 'symbol', None)} | "
            f"Lote={getattr(signal, 'volume', None)} | "
            f"Riesgo={sizing.get('riesgo_estimado', sizing.get('estimated_risk'))} | "
            f"Decisión={state} | Motivo={code}: {reason}"
        )
        log_repository.info("ExecutionPreflight", message)

    # ---------------------------------------------------------

    def process_signal(
        self,
        signal,
        profile,
        account,
    ):
        from risk.risk_manager import risk_manager
        from trading.operation_manager import operation_manager

        print()
        print("=" * 60)
        print("⚙️ TRADE MANAGER")
        print("=" * 60)

        signal.profile_id = profile.id
        signal.profile_name = profile.name

        signal.mt5_account_id = account.id
        signal.mt5_account_name = account.name

        mode_value = str(
            getattr(profile, "execution_mode", "OFF") or "OFF"
        ).strip().upper()
        try:
            self.execution_mode = ExecutionMode(mode_value)
        except ValueError:
            self.execution_mode = ExecutionMode.OFF

        if (
            str(getattr(signal, "source", "")).strip().upper()
            == "INTERNAL"
            and self.execution_mode
            not in (ExecutionMode.OFF, ExecutionMode.SIMULATION)
        ):
            return False

        operation = operation_manager.create(
            signal=signal,
            profile=profile,
            account=account,
        )

        event_bus.operationCreated.emit(
            OperationCreatedEvent(
                operation=operation,
            )
        )

        approved, message = risk_manager.validate(
            signal=signal,
            account=account,
            profile=profile,
        )

        if not approved:

            print(f"❌ Riesgo rechazado: {message}")

            operation_manager.reject(
                operation=operation,
                code="RISK_REJECTED",
                reason=message,
            )
            self._log_preflight(
                signal, profile, account, "REJECTED", "RISK_REJECTED", message
            )

            event_bus.riskRejected.emit(
                RiskRejectedEvent(
                    signal=signal,
                    reason=message,
                )
            )

            return False

        volume = risk_manager.calculate_lot(
            signal=signal,
            profile=profile,
            account=account,
        )

        signal.volume = volume

        from services.execution_preflight_service import (
            execution_preflight_service,
        )

        preflight = execution_preflight_service.validate(
            signal=signal,
            profile=profile,
            account=account,
            volume=volume,
            risk_result=(getattr(signal, "metadata", None) or {}).get(
                "position_sizing"
            ),
        )
        if getattr(signal, "metadata", None) is None:
            signal.metadata = {}
        signal.metadata["execution_preflight"] = {
            "state": preflight.state,
            "code": preflight.code,
            "reason": preflight.reason,
            "details": preflight.details,
        }
        self._log_preflight(
            signal, profile, account, preflight.state,
            preflight.code, preflight.reason
        )
        if not preflight.allowed:
            operation_manager.reject(
                operation=operation,
                code=preflight.code,
                reason=preflight.reason,
            )
            return False

        print(f"📊 Lote calculado: {volume}")

        # -----------------------------------------------------
        # OFF
        # -----------------------------------------------------

        if self.execution_mode == ExecutionMode.OFF:

            operation_manager.close(
                operation=operation,
                reason="OFF_MODE",
            )

            event_bus.operationClosed.emit(
                OperationClosedEvent(
                    operation=operation,
                    profit=0,
                )
            )

            return self._off(signal)

        # -----------------------------------------------------
        # SIMULATION
        # -----------------------------------------------------

        if self.execution_mode == ExecutionMode.SIMULATION:

            operation_manager.open(
                operation=operation,
                ticket=0,
                position_id=0,
                volume=volume,
            )

            event_bus.operationOpened.emit(
                OperationOpenedEvent(
                    operation=operation,
                )
            )

            return self._simulation(
                signal,
                profile,
                account,
                operation,
            )

        if self.execution_mode == ExecutionMode.PAPER:
            from trading.paper_trading_engine import paper_trading_engine

            return paper_trading_engine.execute(
                signal, profile, account
            ) is not None

        # -----------------------------------------------------
        # DEMO / LIVE
        # -----------------------------------------------------

        if self.execution_mode == ExecutionMode.DEMO:

            result = self._demo(
                signal,
                volume,
                account,
                profile,
                preflight,
            )

        elif self.execution_mode == ExecutionMode.LIVE:

            result = self._live(
                signal,
                volume,
                account,
                profile,
                preflight,
            )

        else:

            operation_manager.close(
                operation=operation,
                reason="INVALID_EXECUTION_MODE",
            )

            event_bus.operationClosed.emit(
                OperationClosedEvent(
                    operation=operation,
                    profit=0,
                )
            )

            return False

        # -----------------------------------------------------
        # ERROR MT5
        # -----------------------------------------------------

        if result is None:

            operation_manager.close(
                operation=operation,
                reason="SEND_ERROR",
            )

            event_bus.operationClosed.emit(
                OperationClosedEvent(
                    operation=operation,
                    profit=0,
                )
            )

            return False

        ticket = getattr(result, "order", 0)
        position_id = getattr(result, "deal", 0)

        operation_manager.open(
            operation=operation,
            ticket=ticket,
            position_id=position_id,
            volume=volume,
        )

        event_bus.operationOpened.emit(
            OperationOpenedEvent(
                operation=operation,
            )
        )

        print(f"✅ Ticket {ticket}")

        return True

    # ---------------------------------------------------------

    def _off(self, signal):

        print("[OFF] Señal ignorada.")
        return True

    # ---------------------------------------------------------

    def _simulation(self, signal, profile, account, operation):
        from core.simulation_engine import simulation_engine

        simulation_engine.execute(
            signal=signal,
            profile=profile,
            account=account,
            operation=operation,
        )

        return True

    # ---------------------------------------------------------

    def _demo(
        self,
        signal,
        volume,
        account,
        profile,
        preflight,
    ):
        from mt5.executor import mt5_executor

        return mt5_executor.execute_market_order(
            signal=signal,
            volume=volume,
            account=account,
            profile=profile,
            preflight_result=preflight,
        )

    # ---------------------------------------------------------

    def _live(
        self,
        signal,
        volume,
        account,
        profile,
        preflight,
    ):
        from mt5.executor import mt5_executor

        return mt5_executor.execute_market_order(
            signal=signal,
            volume=volume,
            account=account,
            profile=profile,
            preflight_result=preflight,
        )


trade_manager = TradeManager()
