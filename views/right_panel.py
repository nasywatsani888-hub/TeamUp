# views/right_panel.py — kolom kanan (kartu profil + tenggat pendaftaran)
# Dipakai ulang di Beranda, Rekan Tim, dan Profil Rekan.
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
import config
import data_store
import helpers
import icons
import styles
import sizes


class RightPanel(QWidget):
    WIDTH = sizes.RIGHT_PANEL_WIDTH
    edit_profile_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(self.WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(20)

        # Kartu profil
        profile = QFrame()
        profile.setObjectName("ProfileCard")
        profile.setStyleSheet(styles.PROFILE_CARD_STYLE)
        profile_row = QHBoxLayout(profile)
        profile_row.setContentsMargins(20, 20, 20, 20)
        profile_row.setSpacing(16)
        avatar = QLabel()
        avatar.setFixedSize(sizes.RIGHT_PANEL_AVATAR_SIZE, sizes.RIGHT_PANEL_AVATAR_SIZE)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background-color: white; border-radius: 38px;")
        avatar.setPixmap(icons.make_icon("user", config.COLOR_NAVY, 40).pixmap(QSize(40, 40)))
        profile_text = QVBoxLayout()
        self.username_label = QLabel("@username")
        self.username_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.edit_profile_button = QPushButton("Edit Profile")
        self.edit_profile_button.setStyleSheet(styles.EDIT_BUTTON_STYLE)
        self.edit_profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        profile_text.addStretch()
        profile_text.addWidget(self.username_label)
        profile_text.addWidget(self.edit_profile_button)
        profile_text.addStretch()
        profile_row.addWidget(avatar)
        profile_row.addLayout(profile_text, 1)
        layout.addWidget(profile)

        # Kartu tenggat pendaftaran
        deadline = QFrame()
        deadline.setObjectName("DeadlineCard")
        deadline.setStyleSheet(styles.DEADLINE_CARD_STYLE)
        deadline_layout = QVBoxLayout(deadline)
        deadline_layout.setContentsMargins(20, 18, 20, 20)
        deadline_layout.setSpacing(12)
        header = QHBoxLayout()
        calendar = QLabel()
        calendar.setPixmap(icons.make_icon("calendar", config.COLOR_NAVY, 24).pixmap(QSize(24, 24)))
        header_title = QLabel("Tenggat pendaftaran")
        header_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {config.COLOR_NAVY};")
        header.addWidget(calendar)
        header.addWidget(header_title)
        header.addStretch()
        deadline_layout.addLayout(header)
        self.deadline_layout = QVBoxLayout()
        self.deadline_layout.setSpacing(10)
        deadline_layout.addLayout(self.deadline_layout)
        layout.addWidget(deadline)
        layout.addStretch()

        # Signal & Slot: tombol -> kabari halaman induk
        self.edit_profile_button.clicked.connect(lambda: self.edit_profile_clicked.emit())

    def make_deadline_item(self, lomba):
        color = helpers.deadline_color(lomba["sisa_hari"])
        item = QFrame()
        item.setObjectName("DeadlineItem")
        item.setStyleSheet(styles.DEADLINE_ITEM_STYLE)
        row = QHBoxLayout(item)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        bar = QFrame()
        bar.setFixedWidth(sizes.RIGHT_PANEL_BAR_WIDTH)
        bar.setStyleSheet(f"background-color: {color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px;")
        text = QVBoxLayout()
        text.setContentsMargins(0, 8, 8, 8)
        text.setSpacing(2)
        title = QLabel(lomba["judul"])
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {config.COLOR_NAVY};")
        time_left = QLabel(helpers.format_sisa(lomba["sisa_hari"], use_weeks=True))
        time_left.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")
        text.addWidget(title)
        text.addWidget(time_left)
        row.addWidget(bar)
        row.addLayout(text, 1)
        return item

    def refresh(self):
        """Dipanggil setiap halaman tampil: perbarui username & daftar tenggat."""
        user = data_store.current_user
        username = user["username"] if user and user["username"] else "username"
        self.username_label.setText("@" + username)
        helpers.clear_layout(self.deadline_layout)
        for lomba in data_store.get_upcoming(3):
            self.deadline_layout.addWidget(self.make_deadline_item(lomba))
