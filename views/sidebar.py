# views/sidebar.py — menu samping (Beranda, Unggah Postingan, dst.)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout
import config
import helpers
import icons
import styles
import sizes

# (kunci, teks, nama ikon)
MENU_ITEMS = [
    ("beranda", "Beranda", "home"),
    ("unggah", "Unggah Postingan", "plus-circle"),
    ("rekan", "Rekan Tim", "users"),
    ("notifikasi", "Notifikasi", "bell"),
    ("lomba", "Lomba", "award"),
    ("riwayat", "Riwayat", "clock"),
]


class Sidebar(QFrame):
    # Sidebar hanya mengirim kabar; halaman induk yang memutuskan apa yang tampil
    menu_selected = Signal(str)
    logout_clicked = Signal()
    help_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setStyleSheet(styles.SIDEBAR_STYLE)
        self.setFixedWidth(sizes.SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(10)

        layout.addWidget(helpers.make_logo(width=190, name_size=34, tagline_size=9),
                         alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(24)

        self.buttons = {}
        for key, text, icon_name in MENU_ITEMS:
            button = self.make_button(text, icon_name)
            button.clicked.connect(lambda checked=False, k=key: self.menu_selected.emit(k))
            self.buttons[key] = button
            layout.addWidget(button)

        layout.addStretch()

        logout_button = self.make_button("Keluar", "log-out")
        help_button = self.make_button("Pusat Bantuan", "phone")
        # Keluar & Pusat Bantuan ikut dihitung sebagai menu (aktif = merah muda)
        self.buttons["keluar"] = logout_button
        self.buttons["bantuan"] = help_button
        for button in (logout_button, help_button):
            button.setProperty("danger", True)
        logout_button.clicked.connect(lambda: self.logout_clicked.emit())
        help_button.clicked.connect(lambda: self.help_clicked.emit())
        layout.addWidget(logout_button)
        layout.addWidget(help_button)

    def make_button(self, text, icon_name):
        button = QPushButton("  " + text)
        button.setIcon(icons.make_icon(icon_name, config.COLOR_NAVY, 22))
        button.setIconSize(QSize(22, 22))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def set_active(self, key):
        """Tandai menu yang sedang dibuka (kuning). Kunci tak dikenal = tidak ada yang aktif."""
        for button_key, button in self.buttons.items():
            button.setProperty("active", button_key == key)
            button.style().unpolish(button)
            button.style().polish(button)
