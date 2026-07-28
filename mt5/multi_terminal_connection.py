"""Isolated MT5 connections: one MetaTrader5 process per terminal/account."""

from __future__ import annotations

import multiprocessing
import queue
import threading
import uuid
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace


class MT5WorkerError(RuntimeError):
    """Controlled failure returned by an isolated MT5 worker."""


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if hasattr(value, "_asdict"):
        return {
            "__mt5_object__": True,
            "values": {
                key: _plain(item)
                for key, item in value._asdict().items()
            },
        }
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return str(value)


def _object(value):
    if isinstance(value, list):
        return [_object(item) for item in value]
    if isinstance(value, dict):
        if value.get("__mt5_object__"):
            return SimpleNamespace(
                **{
                    key: _object(item)
                    for key, item in value["values"].items()
                }
            )
        return {key: _object(item) for key, item in value.items()}
    return value


def _invoke_mt5(api, method, args=(), kwargs=None):
    """Call MT5 methods while preserving the native trade-request signature."""
    kwargs = kwargs or {}
    if method in {"order_send", "order_check"}:
        if "request" in kwargs:
            trade_request = kwargs["request"]
        elif args:
            trade_request = args[0]
        elif kwargs:
            trade_request = kwargs
        else:
            raise MT5WorkerError(
                f"{method} requiere una solicitud de trading."
            )
        # Keep every MqlTradeRequest field named when crossing into the native
        # extension. ``request=<dict>`` creates an empty request (10013), and
        # a positional mapping is rejected by some MetaTrader5 builds.
        return getattr(api, method)(**trade_request)
    return getattr(api, method)(*args, **kwargs)


def _worker_main(requests, responses, configuration):
    import MetaTrader5 as mt5

    try:
        kwargs = {"timeout": int(configuration.get("timeout_ms", 10_000))}
        terminal_path = str(configuration.get("terminal_path") or "").strip()
        if terminal_path:
            kwargs["path"] = terminal_path
        if not mt5.initialize(**kwargs):
            raise MT5WorkerError(
                f"No se pudo inicializar MT5: {mt5.last_error()}"
            )
        if not mt5.login(
            login=int(configuration["login"]),
            password=configuration["password"],
            server=configuration["server"],
            timeout=int(configuration.get("timeout_ms", 10_000)),
        ):
            raise MT5WorkerError(
                f"MT5 rechazó la cuenta: {mt5.last_error()}"
            )
        account_info = mt5.account_info()
        detected_login = int(getattr(account_info, "login", 0) or 0)
        if detected_login != int(configuration["login"]):
            raise MT5WorkerError(
                "La cuenta conectada no coincide con el login solicitado."
            )
        responses.put(
            {
                "id": "__startup__",
                "ok": True,
                "value": _plain(account_info),
            }
        )
    except Exception as error:
        responses.put(
            {"id": "__startup__", "ok": False, "error": str(error)}
        )
        mt5.shutdown()
        return

    allowed = {
        "terminal_info",
        "account_info",
        "symbol_info",
        "symbol_select",
        "symbol_info_tick",
        "positions_get",
        "orders_get",
        "history_deals_get",
        "order_calc_margin",
        "order_calc_profit",
        "order_send",
        "last_error",
    }
    try:
        while True:
            request = requests.get()
            if request.get("method") == "__stop__":
                break
            request_id = request["id"]
            method = request.get("method", "")
            if method not in allowed:
                responses.put(
                    {
                        "id": request_id,
                        "ok": False,
                        "error": f"Método MT5 no permitido: {method}.",
                    }
                )
                continue
            try:
                result = _invoke_mt5(
                    mt5,
                    method,
                    request.get("args", ()),
                    request.get("kwargs", {}),
                )
                responses.put(
                    {"id": request_id, "ok": True, "value": _plain(result)}
                )
            except Exception as error:
                responses.put(
                    {"id": request_id, "ok": False, "error": str(error)}
                )
    finally:
        mt5.shutdown()


class MT5TerminalConnection:
    """Synchronous proxy whose child process exclusively owns MetaTrader5."""

    # Stable MQL5 enum values used to build requests in the parent process.
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_INVALID_FILL = 10030
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 3
    DEAL_REASON_SL = 4
    DEAL_REASON_TP = 5

    def __init__(
        self,
        account,
        terminal,
        *,
        timeout=15.0,
        process_factory=None,
        context=None,
    ):
        self.account_id = int(account.id)
        self.terminal_id = int(terminal.id)
        self.login = int(account.login)
        self.terminal_path = (
            str(getattr(terminal, "executable_path", "") or "").strip()
            or str(getattr(account, "terminal_path", "") or "").strip()
        )
        self.timeout = float(timeout)
        self._context = context or multiprocessing.get_context("spawn")
        self._requests = self._context.Queue()
        self._responses = self._context.Queue()
        self._pending = {}
        self._lock = threading.RLock()
        factory = process_factory or self._context.Process
        configuration = {
            "login": self.login,
            "password": account.password,
            "server": account.server,
            "terminal_path": self.terminal_path,
            "timeout_ms": int(self.timeout * 1000),
        }
        self._process = factory(
            target=_worker_main,
            args=(self._requests, self._responses, configuration),
            daemon=True,
            name=f"Kraken-MT5-{self.terminal_id}-{self.account_id}",
        )
        self._process.start()
        startup = self._receive("__startup__", self.timeout)
        if not startup["ok"]:
            self.close()
            raise MT5WorkerError(startup.get("error", "MT5 no inició."))

    @property
    def process_id(self):
        return getattr(self._process, "pid", None)

    @property
    def alive(self):
        return bool(self._process and self._process.is_alive())

    def _receive(self, request_id, timeout):
        if request_id in self._pending:
            return self._pending.pop(request_id)
        while True:
            try:
                response = self._responses.get(timeout=timeout)
            except queue.Empty as error:
                raise MT5WorkerError(
                    f"Timeout esperando respuesta MT5 ({request_id})."
                ) from error
            if response.get("id") == request_id:
                return response
            self._pending[response.get("id")] = response

    def call(self, method, *args, timeout=None, **kwargs):
        with self._lock:
            if not self.alive:
                raise MT5WorkerError("El worker MT5 no está activo.")
            request_id = uuid.uuid4().hex
            self._requests.put(
                {
                    "id": request_id,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs,
                }
            )
            response = self._receive(
                request_id,
                self.timeout if timeout is None else float(timeout),
            )
            if not response.get("ok"):
                raise MT5WorkerError(response.get("error", "Error MT5."))
            return _object(response.get("value"))

    def close(self):
        process = getattr(self, "_process", None)
        if process is None:
            return
        if process.is_alive():
            self._requests.put({"id": "__stop__", "method": "__stop__"})
            process.join(timeout=5.0)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2.0)
        self._process = None

    def terminal_info(self):
        return self.call("terminal_info")

    def account_info(self):
        return self.call("account_info")

    def symbol_info(self, symbol):
        return self.call("symbol_info", symbol)

    def symbol_select(self, symbol, enabled):
        return self.call("symbol_select", symbol, enabled)

    def symbol_info_tick(self, symbol):
        return self.call("symbol_info_tick", symbol)

    def positions_get(self, **kwargs):
        return self.call("positions_get", **kwargs)

    def orders_get(self, **kwargs):
        return self.call("orders_get", **kwargs)

    def history_deals_get(self, *args, **kwargs):
        return self.call("history_deals_get", *args, **kwargs)

    def order_calc_margin(self, *args):
        return self.call("order_calc_margin", *args)

    def order_calc_profit(self, *args):
        return self.call("order_calc_profit", *args)

    def order_send(self, request):
        # Preserve the MqlTradeRequest fields until the isolated worker calls
        # the native MetaTrader5 extension.
        return self.call("order_send", **request)

    def last_error(self):
        return self.call("last_error")
