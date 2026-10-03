# views/post_success_page.py — "Berhasil dikirim!" setelah Unggah Info Lomba / Perbaiki & kirim ulang
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from views.base_page import BasePage
import config
import data_store
import helpers
import icons
import styles


class PostSuccessPage(BasePage):
    back_clicked = Signal()
    view_status_clicked = Signal(int)   # id postingan

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(24, 22, 24, 24)
        self.post_id = None

        self.back_button = QPushButton()
        self.back_button.setIcon(icons.make_icon("arrow-left", config.COLOR_NAVY, 24))
        self.back_button.setIconSize(QSize(24, 24))
        self.back_button.setStyleSheet(styles.BACK_BUTTON_STYLE)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addStretch(1)

        self.main_layout.addWidget(helpers.make_check_circle(72), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addSpacing(10)
        self.title_label = QLabel()
        self.title_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.message_label = QLabel()
        self.message_label.setTextFormat(Qt.TextFormat.RichText)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 12px;")
        for label in (self.title_label, self.message_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(label)
        self.main_layout.addSpacing(10)

        # Status + estimasi tinjauan
        info = QGridLayout()
        info.setHorizontalSpacing(60)
        info.setVerticalSpacing(8)
        background, foreground = styles.POST_STATUS_COLORS["Ditangguhkan"]
        badge = QLabel("Ditangguhkan")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background-color: {background}; color: {foreground}; border-radius: 10px; "
                            "padding: 3px 14px; font-size: 11px; font-weight: bold;")
        rows = [("Status", badge), ("Estimasi tinjauan", QLabel("1 - 2 hari kerja"))]
        for index, (text, widget) in enumerate(rows):
            info.addWidget(QLabel(text), index, 0, alignment=Qt.AlignmentFlag.AlignLeft)
            info.addWidget(widget, index, 1, alignment=Qt.AlignmentFlag.AlignRight)
        holder = QHBoxLayout()
        holder.addStretch()
        holder.addLayout(info)
        holder.addStretch()
        self.main_layout.addLayout(holder)
        self.main_layout.addSpacing(10)

        note = QLabel("Kamu akan mendapat notifikasi begitu admin selesai meninjau ulang")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"font-size: 11px; color: {config.COLOR_SUBTEXT};")
        self.main_layout.addWidget(note)
        self.main_layout.addSpacing(6)
        self.status_button = QPushButton("Lihat status postingan")
        self.status_button.setStyleSheet(styles.POST_BLUE_BUTTON_STYLE)
        self.status_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_button.setMinimumWidth(280)
        self.main_layout.addWidget(self.status_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addStretch(2)

        self.back_button.clicked.connect(lambda: self.back_clicked.emit())
        self.status_button.clicked.connect(lambda: self.view_status_clicked.emit(self.post_id))

    def show_post(self, post_id, mode):
        self.post_id = post_id
        post = data_store.get_postingan_by_id(post_id)
        judul = f"<b>{post['judul']}</b>"
        if mode == "revisi":
            self.title_label.setText("Berhasil dikirim ulang!")
            self.message_label.setText(f"Perbaikan untuk {judul} sudah kami terima dan<br>akan ditinjau ulang oleh admin")
        else:
            self.title_label.setText("Berhasil dikirim!")
            self.message_label.setText(f"Info lomba {judul} sudah kami terima dan<br>akan diverifikasi oleh admin")
