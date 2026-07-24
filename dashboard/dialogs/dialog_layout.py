"""Shared geometry rules for dialogs opened from the Enterprise navigation."""

from PySide6.QtGui import QGuiApplication


def fit_dialog_to_screen(dialog, preferred_width, preferred_height):
    """Keep the dialog and its bottom actions inside the usable desktop area."""
    screen = dialog.screen() or QGuiApplication.primaryScreen()
    if screen is None:
        dialog.resize(preferred_width, preferred_height)
        return
    available = screen.availableGeometry()
    max_width = max(760, available.width() - 64)
    max_height = max(540, available.height() - 64)
    dialog.setMaximumSize(max_width, max_height)
    dialog.resize(min(preferred_width, max_width), min(preferred_height, max_height))
