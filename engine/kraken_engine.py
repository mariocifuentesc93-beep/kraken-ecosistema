from engine.runtime import RuntimeStatus

from engine.signal_engine import signal_engine
from engine.execution_engine import execution_engine

from trading.operation_monitor import operation_monitor

from core.event_bus import event_bus
from core.events import (
    ApplicationStartedEvent,
    ApplicationStoppedEvent,
)


class KrakenEngine:

    def __init__(self):

        self.status = RuntimeStatus.STOPPED
        self.telegram_clients = []

    # ---------------------------------------------------------

    def start(self):

        if self.status == RuntimeStatus.RUNNING:
            return

        self.status = RuntimeStatus.RUNNING

        signal_engine.start()
        execution_engine.start()
        operation_monitor.start()

        event_bus.applicationStarted.emit(
            ApplicationStartedEvent()
        )

        event_bus.logGenerated.emit(
            "Kraken Engine iniciado."
        )

        event_bus.notificationGenerated.emit(
            "Kraken Bot ejecutándose."
        )

        print()
        print("=" * 60)
        print("🐙 KRAKEN ENGINE RUNNING")
        print("=" * 60)
        print(f"Cuentas Telegram: {len(self.telegram_clients)}")
        print("=" * 60)

    # ---------------------------------------------------------

    def stop(self):

        if self.status == RuntimeStatus.STOPPED:
            return

        operation_monitor.stop()
        execution_engine.stop()
        signal_engine.stop()

        for client in self.telegram_clients:

            try:

                if client.is_connected():
                    client.disconnect()

            except Exception:
                pass

        self.telegram_clients.clear()

        self.status = RuntimeStatus.STOPPED

        event_bus.applicationStopped.emit(
            ApplicationStoppedEvent()
        )

        event_bus.notificationGenerated.emit(
            "Kraken Engine detenido."
        )

        print()
        print("=" * 60)
        print("🛑 KRAKEN ENGINE STOPPED")
        print("=" * 60)

    # ---------------------------------------------------------

    def process_signal(
        self,
        signal,
        profile,
    ):

        if self.status != RuntimeStatus.RUNNING:

            print("Kraken detenido.")
            return

        signal_engine.process(
            signal=signal,
            profile=profile,
        )


kraken_engine = KrakenEngine()