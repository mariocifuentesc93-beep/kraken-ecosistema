"""Single explicit lifecycle owner for the professional Kraken runtime."""

import threading
from dataclasses import dataclass
from pathlib import Path

from engine.runtime import RuntimeStatus


def resolve_internal_directory(settings, fallback_directory):
    """Resolve FILE_COMMON-compatible Scanner output without profiles."""
    scanner_enabled = settings.get_bool(
        "internal.scanner.enabled",
        False,
    )
    scanner_directory = settings.get(
        "internal.scanner.output_directory",
        "",
    )
    legacy_directory = settings.get("internal.csv_directory", "")
    configured = (
        scanner_directory
        if scanner_enabled and str(scanner_directory or "").strip()
        else legacy_directory
    )
    return (
        Path(configured)
        if str(configured or "").strip()
        else Path(fallback_directory)
    )


@dataclass(frozen=True)
class RuntimeSnapshot:
    state: RuntimeStatus
    telegram_state: RuntimeStatus
    internal_state: RuntimeStatus
    last_error: str = ""


class TelegramListenerRuntime:
    """Run Telethon on the persistent Telegram authorization loop."""

    def __init__(
        self,
        account_manager=None,
        listener_factory=None,
        async_runner=None,
    ):
        self._account_manager = account_manager
        self._listener_factory = listener_factory
        self._async_runner = async_runner
        self._future = None
        self._stop_requested = threading.Event()
        self.state = RuntimeStatus.STOPPED
        self.last_error = ""

    @property
    def running(self):
        return self._future is not None and not self._future.done()

    def _runner(self):
        if self._async_runner is None:
            from telegram.async_runner import telegram_async_runner

            self._async_runner = telegram_async_runner
        return self._async_runner

    def _manager(self):
        if self._account_manager is None:
            from telegram.account_manager import telegram_account_manager
            self._account_manager = telegram_account_manager
        return self._account_manager

    def _listener(self):
        if self._listener_factory is None:
            from telegram.listener import register_telegram_listener
            self._listener_factory = register_telegram_listener
        return self._listener_factory

    async def _serve(self):
        manager = self._manager()
        manager.reload()
        account = manager.get_active_account()
        if account is None:
            return
        client = await manager.connect(account.id)
        if not await client.is_user_authorized():
            raise RuntimeError(
                "La cuenta Telegram no está autorizada."
            )
        self._listener()(client, account_id=account.id)
        while not self._stop_requested.is_set():
            import asyncio

            await asyncio.sleep(0.1)
        await manager.disconnect(account.id)

    def _completed(self, future):
        try:
            future.result()
            if self.state != RuntimeStatus.STOPPING:
                self.state = RuntimeStatus.STOPPED
        except Exception as error:
            self.last_error = str(error)
            self.state = RuntimeStatus.ERROR

    def start(self):
        if self.running:
            return False
        self.state = RuntimeStatus.STARTING
        self.last_error = ""
        self._stop_requested.clear()
        self._future = self._runner().submit(self._serve())
        self._future.add_done_callback(self._completed)
        self.state = RuntimeStatus.RUNNING
        return True

    def stop(self, timeout=5.0):
        if self._future is None:
            self.state = RuntimeStatus.STOPPED
            return False
        self.state = RuntimeStatus.STOPPING
        self._stop_requested.set()
        try:
            self._future.result(timeout)
        except Exception as error:
            self.last_error = str(error)
            self.state = RuntimeStatus.ERROR
        self._future = None
        if self.state != RuntimeStatus.ERROR:
            self.state = RuntimeStatus.STOPPED
        return True

    def send_message(self, account_id, chat_id, text, timeout=10.0):
        client = self._manager().peek_client(account_id)
        if client is None or not client.is_connected():
            raise RuntimeError("La cuenta Telegram no está conectada.")
        future = self._runner().submit(
            client.send_message(chat_id, text),
        )
        return future.result(timeout)

    def publisher_client(self, account_id):
        runtime = self

        class PublisherClient:
            def send_message(self, chat_id, text):
                return runtime.send_message(account_id, chat_id, text)

        return PublisherClient()


class RuntimeCoordinator:
    """Start and stop every signal source through one idempotent contract."""

    def __init__(
        self,
        telegram_runtime=None,
        internal_watcher=None,
        internal_source=None,
        signal_engine=None,
        execution_engine=None,
        operation_monitor=None,
        mt5_connection_registry=None,
        enable_sources=True,
    ):
        self._telegram_runtime = telegram_runtime
        self._internal_watcher = internal_watcher
        self._internal_source = internal_source
        self._signal_engine = signal_engine
        self._execution_engine = execution_engine
        self._operation_monitor = operation_monitor
        self._mt5_connection_registry = mt5_connection_registry
        self._enable_sources = bool(enable_sources)
        self.state = RuntimeStatus.STOPPED
        self.internal_state = RuntimeStatus.STOPPED
        self.last_error = ""
        self._lock = threading.RLock()

    def _build_defaults(self):
        if self._mt5_connection_registry is None:
            from services.mt5_connection_registry import (
                mt5_connection_registry,
            )

            self._mt5_connection_registry = mt5_connection_registry
        if self._signal_engine is None:
            from engine.signal_engine import signal_engine
            self._signal_engine = signal_engine
        if self._execution_engine is None:
            from engine.execution_engine import execution_engine
            self._execution_engine = execution_engine
        if self._operation_monitor is None:
            from trading.operation_monitor import operation_monitor
            self._operation_monitor = operation_monitor
        if self._enable_sources and self._telegram_runtime is None:
            self._telegram_runtime = TelegramListenerRuntime()
        if self._enable_sources and self._internal_source is None:
            from internal.checkpoint_store import InternalCheckpointStore
            from internal.source import (
                InternalSignalSource,
                default_internal_directory,
            )
            from services.signal_ingestion_service import (
                signal_ingestion_service,
            )
            from services.internal_signal_publication_service import (
                InternalSignalPublicationService,
            )
            from repositories.internal_publication_config_repository import (
                internal_publication_config_repository,
            )
            from repositories.telegram_channel_repository import (
                telegram_channel_repository,
            )
            from repositories.telegram_publication_repository import (
                TelegramPublicationRepository,
            )
            from telegram.account_manager import telegram_account_manager
            from telegram.signal_publisher import TelegramSignalPublisher
            from repositories.settings_repository import settings_repository

            directory = resolve_internal_directory(
                settings_repository,
                default_internal_directory(),
            )
            observation_only = settings_repository.get_bool(
                "internal.observation_only",
                False,
            )
            publication_service = InternalSignalPublicationService(
                repository=TelegramPublicationRepository(),
                publisher=TelegramSignalPublisher(
                    self._telegram_runtime.publisher_client
                ),
                config_provider=internal_publication_config_repository.get,
                account_provider=telegram_account_manager.get_account,
                destinations_provider=(
                    telegram_channel_repository.list_sendable
                ),
            )
            from services.internal_signal_level_update_service import (
                InternalSignalLevelUpdateService,
            )
            from repositories.signal_repository import signal_repository
            from repositories.operation_repository import operation_repository
            from repositories.profile_repository import profile_repository
            from repositories.operation_milestone_repository import (
                operation_milestone_repository,
            )
            from repositories.log_repository import log_repository
            from mt5.executor import mt5_executor

            level_update_service = InternalSignalLevelUpdateService(
                signal_repository=signal_repository,
                operation_repository=operation_repository,
                profile_repository=profile_repository,
                milestone_repository=operation_milestone_repository,
                executor=mt5_executor,
                connection_registry=self._mt5_connection_registry,
                logger=log_repository,
                publication_service=publication_service,
            )
            self._internal_source = InternalSignalSource(
                directory=directory,
                checkpoint_store=InternalCheckpointStore(
                    directory / ".kraken_internal_checkpoint.json"
                ),
                observation_only=observation_only,
                ingestion_service=signal_ingestion_service,
                publication_service=publication_service,
                level_update_service=level_update_service,
            )
        if self._enable_sources and self._internal_watcher is None:
            from internal.csv_watcher import InternalCsvWatcher
            self._internal_watcher = InternalCsvWatcher(
                self._internal_source.directory,
                callback=self._process_internal_file,
            )

    def _process_internal_file(self, path):
        try:
            self._internal_source.process_file(path)
        except Exception as error:
            self.internal_state = RuntimeStatus.ERROR
            self.last_error = str(error)
            raise
        finally:
            from database.database_manager import database_manager
            database_manager.close()

    def start(self):
        with self._lock:
            if self.state in (RuntimeStatus.STARTING, RuntimeStatus.RUNNING):
                return False
            self.state = RuntimeStatus.STARTING
            self.last_error = ""
            try:
                self._build_defaults()
                self._signal_engine.start()
                self._execution_engine.start()
                self._operation_monitor.start()
                if self._telegram_runtime is not None:
                    self._telegram_runtime.start()
                if self._internal_watcher is not None:
                    self.internal_state = RuntimeStatus.STARTING
                    self._internal_watcher.start()
                    self.internal_state = RuntimeStatus.RUNNING
                self.state = RuntimeStatus.RUNNING
                return True
            except Exception as error:
                self.last_error = str(error)
                self.state = RuntimeStatus.ERROR
                self.internal_state = RuntimeStatus.ERROR
                self.stop()
                raise

    def stop(self):
        with self._lock:
            if self.state in (RuntimeStatus.STOPPED, RuntimeStatus.STOPPING):
                return False
            preserve_error = self.state == RuntimeStatus.ERROR
            self.state = RuntimeStatus.STOPPING
            if self._internal_watcher is not None:
                self._internal_watcher.stop()
            self.internal_state = RuntimeStatus.STOPPED
            if self._telegram_runtime is not None:
                self._telegram_runtime.stop()
            if self._operation_monitor is not None:
                self._operation_monitor.stop()
            if self._mt5_connection_registry is not None:
                self._mt5_connection_registry.stop_all()
            if self._execution_engine is not None:
                self._execution_engine.stop()
            if self._signal_engine is not None:
                self._signal_engine.stop()
            self.state = (
                RuntimeStatus.ERROR
                if preserve_error
                else RuntimeStatus.STOPPED
            )
            return True

    def get_status(self):
        telegram_state = (
            getattr(self._telegram_runtime, "state", RuntimeStatus.STOPPED)
            if self._telegram_runtime is not None
            else RuntimeStatus.STOPPED
        )
        internal_state = self.internal_state
        watcher_state = getattr(self._internal_watcher, "state", None)
        if watcher_state:
            try:
                internal_state = RuntimeStatus(str(watcher_state))
            except ValueError:
                pass
        watcher_error = getattr(self._internal_watcher, "last_error", "")
        return RuntimeSnapshot(
            self.state,
            telegram_state,
            internal_state,
            self.last_error or watcher_error,
        )


runtime_coordinator = RuntimeCoordinator()
