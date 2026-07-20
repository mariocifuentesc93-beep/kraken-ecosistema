"""Single responsive layout policy for the Kraken Enterprise interface."""

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget


class EnterpriseLayoutManager:
    """Own the spacing and sizing rules shared by the shell and every page."""

    SIDEBAR_WIDTH = 210
    TOOLBAR_HEIGHT = 46
    STATUSBAR_HEIGHT = 28
    PAGE_MARGINS = (12, 10, 12, 10)
    PAGE_SPACING = 8
    SECTION_SPACING = 8

    _LAYOUT_TYPES = (QVBoxLayout, QHBoxLayout, QGridLayout)

    @classmethod
    def configure_page(cls, page: QWidget) -> QWidget:
        """Apply the global responsive policy to a page and its layout tree."""
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root = page.layout()
        if root is None:
            root = QVBoxLayout(page)
        root.setContentsMargins(*cls.PAGE_MARGINS)
        root.setSpacing(cls.PAGE_SPACING)
        cls._configure_children(root)
        page.setProperty("enterpriseLayoutManaged", True)
        return page

    @classmethod
    def _configure_children(cls, layout) -> None:
        for index in range(layout.count()):
            item = layout.itemAt(index)
            child_layout = item.layout()
            widget = item.widget()
            if child_layout is not None:
                child_layout.setSpacing(cls.SECTION_SPACING)
                child_layout.setContentsMargins(0, 0, 0, 0)
                cls._configure_children(child_layout)
            elif widget is not None:
                if widget.sizePolicy().horizontalPolicy() not in (
                    QSizePolicy.Fixed,
                    QSizePolicy.Maximum,
                    QSizePolicy.Ignored,
                ):
                    widget.setSizePolicy(
                        QSizePolicy.Expanding,
                        widget.sizePolicy().verticalPolicy(),
                    )
                nested = widget.layout()
                if nested is not None:
                    nested.setSpacing(cls.SECTION_SPACING)
                    cls._configure_children(nested)


enterprise_layout = EnterpriseLayoutManager()
