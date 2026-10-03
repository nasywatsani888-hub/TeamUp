# views/sidebar.py — menu samping (Beranda, Unggah Postingan, dst.)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
import config
import data_store
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
    edit_profile_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setStyleSheet(styles.SIDEBAR_STYLE)
        self.setFixedWidth(sizes.SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(10)

        layout.addWidget(helpers.make_logo(width=190, name_size=28, tagline_size=8),
                         alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(24)

        self.buttons = {}
        for key, text, icon_name in MENU_ITEMS:
            button = self.make_button(text, icon_name)
            button.clicked.connect(lambda checked=False, k=key: self.menu_selected.emit(k))
            self.buttons[key] = button
            layout.addWidget(button)

        layout.addStretch()

        # Kartu profil (pindahan dari panel kanan): avatar, @username, tombol Edit Profile
        profile = QFrame()
        profile.setObjectName("ProfileCard")
        profile.setStyleSheet(styles.PROFILE_CARD_STYLE)
        profile.setFixedHeight(sizes.SIDEBAR_PROFILE_HEIGHT)
        profile_row = QHBoxLayout(profile)
        profile_row.setContentsMargins(14, 12, 14, 12)
        profile_row.setSpacing(10)
        avatar = QLabel()
        avatar.setFixedSize(sizes.SIDEBAR_AVATAR_SIZE, sizes.SIDEBAR_AVATAR_SIZE)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"background-color: white; border-radius: {sizes.SIDEBAR_AVATAR_SIZE // 2}px;")
        avatar.setPixmap(icons.make_icon("user", config.COLOR_NAVY, 28).pixmap(QSize(28, 28)))
        profile_text = QVBoxLayout()
        profile_text.setSpacing(4)
        self.username_label = QLabel("@username")
        self.username_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.edit_profile_button = QPushButton("Edit Profile")
        self.edit_profile_button.setStyleSheet(styles.SIDEBAR_EDIT_BUTTON_STYLE)
        self.edit_profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        profile_text.addStretch()
        profile_text.addWidget(self.username_label)
        profile_text.addWidget(self.edit_profile_button)
        profile_text.addStretch()
        profile_row.addWidget(avatar)
        profile_row.addLayout(profile_text, 1)
        layout.addWidget(profile)
        layout.addSpacing(4)

        logout_button = self.make_button("Keluar", "log-out")
        help_button = self.make_button("Pusat Bantuan", "phone")
        # Keluar & Pusat Bantuan ikut dihitung sebagai menu (aktif = merah muda)
        self.buttons["keluar"] = logout_button
        self.buttons["bantuan"] = help_button
        for button in (logout_button, help_button):
            button.setProperty("danger", True)
        logout_button.clicked.connect(self.logout_clicked)
        help_button.clicked.connect(self.help_clicked)
        self.edit_profile_button.clicked.connect(self.edit_profile_clicked)
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

    def refresh_profile(self):
        """Perbarui @username (dipanggil DashboardPage tiap pindah halaman)."""
        user = data_store.current_user
        username = user["username"] if user and user["username"] else "username"
        self.username_label.setText("@" + username)
