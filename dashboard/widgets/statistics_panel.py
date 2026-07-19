from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
)

from dashboard.widgets.card_widget import CardWidget


class StatisticsPanel(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QGridLayout(self)

        self.cards = {}

        items = [

            "Balance",
            "Profit",
            "Win Rate",
            "Profit Factor",
            "Drawdown",
            "Expectancy",
            "Operaciones",
            "TP1",
            "SL",
        ]

        row = 0
        col = 0

        for title in items:

            card = CardWidget(
                title,
                "-"
            )

            self.cards[title] = card

            layout.addWidget(
                card,
                row,
                col,
            )

            col += 1

            if col == 3:

                col = 0
                row += 1

    # ------------------------------------------

    def setValue(
        self,
        name,
        value,
    ):

        if name in self.cards:

            self.cards[name].setValue(
                value
            )

    # ------------------------------------------

    def clear(self):

        for card in self.cards.values():

            card.setValue("-")