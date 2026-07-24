"""One persistent asyncio loop for interactive Telegram diagnostics."""

import asyncio
import threading


class AsyncioThreadRunner:
    def __init__(self, name="KrakenTelegramAuthorization"):
        self._name = name
        self._thread = None
        self._loop = None
        self._ready = threading.Event()
        self._lock = threading.RLock()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _thread_main(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            try:
                from database.database_manager import database_manager

                database_manager.close()
            except Exception:
                pass
            loop.close()
            self._loop = None
            self._ready.clear()

    def start(self):
        with self._lock:
            if self.running:
                return
            self._thread = threading.Thread(
                target=self._thread_main,
                name=self._name,
                daemon=True,
            )
            self._thread.start()
        if not self._ready.wait(5):
            raise RuntimeError(
                "No se pudo iniciar el asistente de autorización Telegram."
            )

    def run(self, coroutine, timeout=30):
        self.start()
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        return future.result(timeout)

    def shutdown(self, timeout=5):
        with self._lock:
            loop = self._loop
            thread = self._thread
            if loop is None or thread is None:
                return
            loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout)
        self._thread = None


telegram_async_runner = AsyncioThreadRunner()
