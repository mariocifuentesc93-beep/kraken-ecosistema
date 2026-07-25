"""Read-only MT5 terminal diagnostics.  This module never sends trade requests."""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:  # Allows a clear diagnostic if the optional package is absent.
    mt5 = None

from config.symbols import BRIDGE_CATALOG, get_mt5_symbol, get_symbols
from repositories.mt5_diagnostics_repository import mt5_diagnostics_repository


class MT5ConnectionDiagnostics:
    def __init__(self, mt5_api=None, package_available=None):
        self.mt5 = mt5 if mt5_api is None else mt5_api
        self.package_available = package_available

    def _package_available(self):
        if self.package_available is not None:
            return self.package_available
        return self.mt5 is not None and importlib.util.find_spec("MetaTrader5") is not None

    @staticmethod
    def _error(api):
        try:
            return str(api.last_error())
        except Exception:
            return "Sin detalle adicional de MT5."

    def run(self, account, timeout_ms=10_000):
        report = {
            "success": False, "account_id": getattr(account, "id", None),
            "terminal_path": getattr(account, "terminal_path", "") or "Auto detectado",
            "account": getattr(account, "login", ""), "server": getattr(account, "server", ""),
            "balance": None, "equity": None, "currency": "", "leverage": None,
            "trade_allowed": False, "algorithmic_trading_allowed": False,
            "terminal_connected": False, "connected_timestamp": datetime.now(timezone.utc).isoformat(),
            "last_error": "", "actionable_error": "", "symbols": [],
        }
        if not self._package_available():
            return self._finish(report, "El paquete MetaTrader5 no está instalado.")
        if account is None or not getattr(account, "login", 0) or not getattr(account, "password", "") or not getattr(account, "server", ""):
            return self._finish(report, "Complete número de cuenta, contraseña y servidor MT5.")
        configured_path = getattr(account, "terminal_path", "")
        if configured_path and not Path(configured_path).is_file():
            return self._finish(report, f"No se encontró el ejecutable MT5: {configured_path}")

        kwargs = {"timeout": timeout_ms}
        if configured_path:
            kwargs["path"] = configured_path
        if not self.mt5.initialize(**kwargs):
            return self._finish(report, "No se pudo inicializar el terminal MT5.")
        if not self.mt5.login(login=int(account.login), password=account.password,
                              server=account.server, timeout=timeout_ms):
            return self._finish(report, "MT5 rechazó las credenciales o el servidor.")

        terminal = self.mt5.terminal_info()
        info = self.mt5.account_info()
        if terminal is None or info is None:
            return self._finish(report, "MT5 se conectó pero no devolvió información de terminal o cuenta.")
        report.update({
            "success": True,
            "terminal_path": getattr(terminal, "path", configured_path or "Auto detectado"),
            "account": getattr(info, "login", account.login), "server": getattr(info, "server", account.server),
            "balance": getattr(info, "balance", None), "equity": getattr(info, "equity", None),
            "currency": getattr(info, "currency", ""), "leverage": getattr(info, "leverage", None),
            "trade_allowed": bool(getattr(info, "trade_allowed", False) and getattr(terminal, "trade_allowed", False)),
            "algorithmic_trading_allowed": not bool(getattr(terminal, "tradeapi_disabled", True)),
            "terminal_connected": bool(getattr(terminal, "connected", False)),
            "last_error": self._error(self.mt5),
        })
        report["symbols"] = self.validate_symbols()
        if not report["trade_allowed"]:
            report["actionable_error"] = "El terminal o la cuenta no permiten trading; LIVE continúa bloqueado."
        return self._persist(report)

    def validate_symbols(self):
        if not self._package_available():
            return []
        results = []
        for symbol in get_symbols(BRIDGE_CATALOG):
            mt5_symbol = get_mt5_symbol(symbol)
            info = self.mt5.symbol_info(mt5_symbol)
            available = info is not None
            visible = bool(available and getattr(info, "visible", False))
            selectable = bool(available and (visible or self.mt5.symbol_select(mt5_symbol, True)))
            if selectable and not visible:
                info = self.mt5.symbol_info(mt5_symbol) or info
            tick = self.mt5.symbol_info_tick(mt5_symbol) if selectable else None
            results.append({
                "symbol": symbol, "mt5_symbol": mt5_symbol, "available": available,
                "visible": bool(getattr(info, "visible", visible)) if info else False,
                "selectable": selectable, "tick_available": tick is not None,
                "bid": getattr(tick, "bid", None), "ask": getattr(tick, "ask", None),
                "volume_min": getattr(info, "volume_min", None) if info else None,
                "volume_max": getattr(info, "volume_max", None) if info else None,
                "volume_step": getattr(info, "volume_step", None) if info else None,
                "tick_size": getattr(info, "trade_tick_size", None) if info else None,
                "tick_value": getattr(info, "trade_tick_value", None) if info else None,
                "contract_size": getattr(info, "trade_contract_size", None) if info else None,
                "stops_level": getattr(info, "trade_stops_level", None) if info else None,
                "filling_mode": getattr(info, "filling_mode", None) if info else None,
            })
        return results

    def _finish(self, report, message):
        report["last_error"] = self._error(self.mt5) if self.mt5 else message
        report["actionable_error"] = message
        return self._persist(report)

    @staticmethod
    def to_json(report):
        return json.dumps(report, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def to_text(report):
        fields = ("success", "terminal_path", "account", "server", "balance", "equity", "currency", "leverage", "trade_allowed", "algorithmic_trading_allowed", "terminal_connected", "connected_timestamp", "actionable_error")
        return "MT5 Connection Diagnostics\n" + "\n".join(f"{field}: {report.get(field, '')}" for field in fields) + f"\nSymbols: {len(report.get('symbols', []))}"

    def export_json(self, report, destination):
        Path(destination).write_text(self.to_json(report), encoding="utf-8")

    def export_text(self, report, destination):
        Path(destination).write_text(self.to_text(report), encoding="utf-8")

    @staticmethod
    def _persist(report):
        diagnostic_id = mt5_diagnostics_repository.save_diagnostic(report)
        if report.get("symbols"):
            mt5_diagnostics_repository.save_symbol_results(diagnostic_id, report["symbols"])
        report["diagnostic_id"] = diagnostic_id
        return report


mt5_connection_diagnostics = MT5ConnectionDiagnostics()
