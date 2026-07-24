from engine.runtime import RuntimeStatus

from engine.signal_engine import signal_engine

from core.event_bus import event_bus
from core.events import (
    ApplicationStartedEvent,
    ApplicationStoppedEvent,
)


class KrakenEngine:

    def __init__(
        self,
        signal_engine_instance=None,
        ingestion_service_instance=None,
        execution_engine_instance=None,
        operation_monitor_instance=None,
    ):

        self.status = RuntimeStatus.STOPPED
        self.telegram_clients = []
        self._signal_engine = signal_engine_instance
        self._ingestion_service = ingestion_service_instance
        self._execution_engine = execution_engine_instance
        self._operation_monitor = operation_monitor_instance

    def _get_signal_engine(self):

        if self._signal_engine is None:
            self._signal_engine = signal_engine

        return self._signal_engine

    def _get_execution_engine(self):

        if self._execution_engine is None:
            from engine.execution_engine import execution_engine
            self._execution_engine = execution_engine

        return self._execution_engine

    def _get_ingestion_service(self):

        if self._ingestion_service is None:
            from services.signal_ingestion_service import (
                SignalIngestionService,
            )
            self._ingestion_service = SignalIngestionService(
                signal_engine_instance=self._get_signal_engine(),
            )

        return self._ingestion_service

    def _get_operation_monitor(self):

        if self._operation_monitor is None:
            from trading.operation_monitor import operation_monitor
            self._operation_monitor = operation_monitor

        return self._operation_monitor

    # ---------------------------------------------------------

    def start(self):

        if self.status == RuntimeStatus.RUNNING:
            return

        self.status = RuntimeStatus.RUNNING

        self._get_signal_engine().start()
        self._get_execution_engine().start()
        self._get_operation_monitor().start()

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

        self._get_operation_monitor().stop()
        self._get_execution_engine().stop()
        self._get_signal_engine().stop()

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

    def process_telegram_signal(
        self,
        signal,
        chat_id,
        account_id=None,
    ):

        if self.status != RuntimeStatus.RUNNING:

            print("Kraken detenido.")
            return False

        return self._get_ingestion_service().ingest(
            signal=signal,
            chat_id=chat_id,
            account_id=account_id,
        )

    def process_signal(
        self,
        signal,
        chat_id,
        account_id=None,
    ):
        """Alias compatible con el contrato único de entrada Telegram."""

        return self.process_telegram_signal(
            signal=signal,
            chat_id=chat_id,
            account_id=account_id,
        )


kraken_engine = KrakenEngine()
