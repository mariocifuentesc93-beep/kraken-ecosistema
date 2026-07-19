import sys

from PySide6.QtWidgets import QApplication

print("1 - Inicio")

from database.database_manager import database_manager

print("2 - Database importado")

from dashboard.main_window import MainWindow

print("3 - MainWindow importada")


def main():

    print("4 - Entró a main()")

    database_manager.initialize()

    print("5 - Base inicializada")

    app = QApplication(sys.argv)

    print("6 - QApplication creada")

    window = MainWindow()

    print("7 - MainWindow creada")

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()