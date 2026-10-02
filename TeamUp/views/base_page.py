# views/base_page.py — kelas dasar untuk SEMUA halaman
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout


class BasePage(QWidget):
    """Widget dibuat SATU kali di __init__.
    showEvent / hideEvent hanya memperbarui data & tampilan (Widget Lifecycle),
    tidak membuat ulang komponen."""

    def __init__(self):
        super().__init__()
        self.setObjectName("Page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(12)

    # --- Widget Lifecycle ---
    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():   # abaikan saat jendela di-restore dari minimize
            self.on_show()

    def hideEvent(self, event):
        self.on_hide()
        super().hideEvent(event)

    # Halaman turunan cukup mengisi dua fungsi ini
    def on_show(self):
        pass

    def on_hide(self):
        pass
