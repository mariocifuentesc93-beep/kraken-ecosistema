import threading
import time

import MetaTrader5 as mt5

from repositories.operation_repository import (
    operation_repository,
)


class OperationMonitor:

    def __init__(self):

        self.running = False

        self.thread = None

        self.interval = 1

    # -------------------------------------------------

    def start(self):

        if self.running:

            return

        self.running = True

        self.thread = threading.Thread(

            target=self._loop,

            daemon=True,

        )

        self.thread.start()

        print(

            "[OperationMonitor] iniciado."

        )

    # -------------------------------------------------

    def stop(self):

        self.running = False

        print(

            "[OperationMonitor] detenido."

        )

    # -------------------------------------------------

    def _loop(self):

        while self.running:

            try:

                self.update()

            except Exception as e:

                print(

                    f"[OperationMonitor] {e}"

                )

            time.sleep(self.interval)

    # -------------------------------------------------

    def update(self):

        operations = operation_repository.get_open()

        if not operations:

            return

        positions = mt5.positions_get()

        if positions is None:

            return

        active = {

            position.ticket: position

            for position in positions

        }

        for operation in operations:

            if operation.ticket not in active:

                operation.status = "CLOSED"

                operation.closed_at = datetime.now()

                operation_repository.update(

                    operation

                )

                print(

                    f"✅ Operación cerrada {operation.ticket}"

                )

                continue

            position = active[operation.ticket]

            operation.profit = position.profit

            operation.swap = position.swap

            operation_repository.update(

                operation

            )


operation_monitor = OperationMonitor()