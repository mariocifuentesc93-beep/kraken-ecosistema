import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from dashboard.main_window import MainWindow
from utils.application_lifecycle import shutdown_application
from utils.startup_validation import get_setup_warnings, validate_startup
from dashboard.branding import application_icon, splash_pixmap
from dashboard.ui_theme import apply_terminal_palette, application_style


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kraken Bot Enterprise")
    app.setWindowIcon(application_icon())
    apply_terminal_palette(app)
    app.setStyleSheet(application_style())
    splash = QSplashScreen(splash_pixmap())
    splash.show()
    app.processEvents()
    app.aboutToQuit.connect(shutdown_application)
    errors = validate_startup()
    if errors:
        QMessageBox.critical(
            None,
            "Kraken Bot no pudo iniciar",
            "Corrija los siguientes problemas antes de continuar:\n\n- " + "\n- ".join(errors),
        )
        return 1

    warnings = get_setup_warnings()
    if warnings:
        QMessageBox.information(
            None,
            "Configuración inicial",
            "Kraken Bot inicia en modo OFF. Complete la configuración antes de operar:\n\n- "
            + "\n- ".join(warnings),
        )

    window = MainWindow()
    splash.finish(window)
    window.show()
    try:
        return app.exec()
    finally:
        shutdown_application()


if __name__ == "__main__":
    sys.exit(main())
