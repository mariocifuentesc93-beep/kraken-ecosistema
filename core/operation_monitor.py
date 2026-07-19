from datetime import datetime
import time

import MetaTrader5 as mt5

from mt5.connector import mt5_connector

from repositories.operation_repository import operation_repository
from repositories.operation_events_repository import (
    operation_events_repository,
)

from repositories.log_repository import log_repository

from risk.break_even import break_even
from risk.trailing_stop import trailing_stop
from risk.partial_tp import partial_tp

from core.statistics_manager import statistics_manager


class OperationMonitor:

    def __init__(self):

        self.running = False

        self.interval = 2

    # =====================================================
    # START
    # =====================================================

    def start(self):

        if self.running:

            return

        self.running = True

        log_repository.info(
            "OperationMonitor",
            "Monitor iniciado",
        )

        while self.running:

            try:

                self.monitor()

            except Exception as e:

                log_repository.error(
                    "OperationMonitor",
                    str(e),
                )

            time.sleep(self.interval)

    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.running = False

        log_repository.info(
            "OperationMonitor",
            "Monitor detenido",
        )

    # =====================================================
    # LOOP
    # =====================================================

    def monitor(self):

        operations = operation_repository.get_open()

        for operation in operations:

            self.monitor_operation(operation)

    # =====================================================
    # OPERATION
    # =====================================================

    def monitor_operation(self, operation):

        position = mt5.positions_get(ticket=operation.ticket)

        if not position:

            self.close_operation(operation)

            return

        position = position[0]

        break_even.process(operation, position)

        trailing_stop.process(operation, position)

        partial_tp.process(operation, position)

    # =====================================================
    # CLOSE
    # =====================================================

    def close_operation(self, operation):

        history = mt5.history_deals_get(
            ticket=operation.ticket
        )

        if history:

            deal = history[-1]

            operation.exit_price = deal.price

            operation.profit = deal.profit

            operation.closed_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            operation.status = "CLOSED"

            if operation.profit > 0:

                operation.result = "WIN"

            elif operation.profit < 0:

                operation.result = "LOSS"

            else:

                operation.result = "BREAKEVEN"

            operation_repository.update(operation)

            operation_events_repository.create(
                operation.id,
                "CLOSED",
                operation.result,
            )

            statistics_manager.update_profile_statistics(
                operation.profile_id
            )

            log_repository.info(
                "OperationMonitor",
                f"Operación {operation.ticket} cerrada"
            )


operation_monitor = OperationMonitor()
