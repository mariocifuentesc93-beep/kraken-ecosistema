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

            operation_manager.close(
                operation=operation,
                reason="RISK_REJECTED",
                profit=0,
            )

            event_bus.riskRejected.emit(
                RiskRejectedEvent(
                    signal=signal,
                    reason=message,
                )
            )

            event_bus.operationClosed.emit(
                OperationClosedEvent(
                    operation=operation,
                    profit=0,
                )
            )

            return False

        volume = risk_manager.calculate_lot(
            signal=signal,
            profile=profile,
            account=account,
        )

        signal.volume = volume

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
            )

        elif self.execution_mode == ExecutionMode.LIVE:

            result = self._live(
                signal,
                volume,
                account,
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
    ):
        from mt5.executor import mt5_executor

        return mt5_executor.execute_market_order(
            signal=signal,
            volume=volume,
            account=account,
        )

    # ---------------------------------------------------------

    def _live(
        self,
        signal,
        volume,
        account,
    ):
        from mt5.executor import mt5_executor

        return mt5_executor.execute_market_order(
            signal=signal,
            volume=volume,
            account=account,
        )


trade_manager = TradeManager()
