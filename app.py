import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from dashboard.main_window import MainWindow
from utils.application_lifecycle import shutdown_application
from utils.startup_validation import validate_startup


def main():
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(shutdown_application)
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
    try:
        return app.exec()
    finally:
        shutdown_application()


if __name__ == "__main__":
    sys.exit(main())
