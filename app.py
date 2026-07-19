import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from dashboard.main_window import MainWindow
from utils.startup_validation import validate_startup


def main():
    app = QApplication(sys.argv)
    errors = validate_startup()
    if errors:
        QMessageBox.critical(
            None,
            "Kraken Bot no pudo iniciar",
            "Corrija los siguientes problemas antes de continuar:\n\n- " + "\n- ".join(errors),
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
