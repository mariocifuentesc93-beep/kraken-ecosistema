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
        runtime_coordinator_instance=None,
    ):

        self.status = RuntimeStatus.STOPPED
        self.telegram_clients = []
        self._signal_engine = signal_engine_instance
        self._ingestion_service = ingestion_service_instance
        self._execution_engine = execution_engine_instance
        self._operation_monitor = operation_monitor_instance
        self._runtime_coordinator = runtime_coordinator_instance
        self._explicit_components = any(
            component is not None
            for component in (
                signal_engine_instance,
                ingestion_service_instance,
                execution_engine_instance,
                operation_monitor_instance,
            )
        )

    def _get_runtime_coordinator(self):
        if self._runtime_coordinator is None:
            from services.runtime_coordinator import RuntimeCoordinator
            self._runtime_coordinator = RuntimeCoordinator(
                signal_engine=self._get_signal_engine(),
                execution_engine=self._get_execution_engine(),
                operation_monitor=self._get_operation_monitor(),
                enable_sources=not self._explicit_components,
            )
        return self._runtime_coordinator

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

        self.status = RuntimeStatus.STARTING
        try:
            self._get_runtime_coordinator().start()
        except Exception:
            self.status = RuntimeStatus.ERROR
            raise
        self.status = RuntimeStatus.RUNNING

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

        self.status = RuntimeStatus.STOPPING
        self._get_runtime_coordinator().stop()
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

    def get_status(self):
        if self._runtime_coordinator is None:
            return None
        return self._runtime_coordinator.get_status()
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
