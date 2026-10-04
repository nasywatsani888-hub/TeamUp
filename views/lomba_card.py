# views/lomba_card.py — kartu lomba (dipakai di Beranda dan halaman Lomba)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
import config
import helpers
import styles
import sizes


class LombaCard(QFrame):
    detail_clicked = Signal(int)   # id lomba

    def __init__(self, lomba):
        super().__init__()
        self.lomba_id = lomba["id"]   # disimpan di objek (bukan ditangkap lambda)
        self.setObjectName("LombaCard")
        self.setStyleSheet(styles.LOMBA_CARD_STYLE)
        self.setMinimumWidth(sizes.LOMBA_CARD_MIN_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Poster: gambar asli dari assets/poster/ (sudut atas membulat). Kalau gambarnya belum ada,
        # tampil blok warna + judul sebagai cadangan.
        poster = helpers.make_poster(lomba, sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_POSTER_HEIGHT, 20)
        if poster is None:
            poster = QLabel(lomba["judul"].upper())
            poster.setWordWrap(True)
            poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
            poster.setFixedHeight(sizes.LOMBA_POSTER_HEIGHT)
            poster.setStyleSheet(
                f"background-color: {lomba['warna']}; color: white; font-size: 20px; font-weight: bold; "
                "border-top-left-radius: 20px; border-top-right-radius: 20px; padding: 16px;")
        layout.addWidget(poster)

        info = QVBoxLayout()
        info.setContentsMargins(16, 14, 16, 16)
        info.setSpacing(6)
        layout.addLayout(info)

        tag = QLabel(lomba["kategori"])
        tag.setStyleSheet(styles.TAG_STYLE)
        info.addWidget(tag, alignment=Qt.AlignmentFlag.AlignLeft)

        title = QLabel(lomba["judul"])
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {config.COLOR_NAVY};")
        info.addWidget(title)
        organizer = QLabel(lomba["penyelenggara"])
        organizer.setStyleSheet(f"font-size: 14px; color: {config.COLOR_NAVY};")
        info.addWidget(organizer)

        footer = QHBoxLayout()
        days = QLabel(helpers.format_sisa(lomba["sisa_hari"]))
        days.setStyleSheet("font-size: 13px; font-weight: bold; color: #E53935;")
        detail_button = QPushButton("Lihat Detail")
        detail_button.setStyleSheet(styles.DETAIL_BUTTON_STYLE)
        detail_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addWidget(days)
        footer.addStretch()
        footer.addWidget(detail_button)
        info.addLayout(footer)

        # Signal & Slot: tombol -> kirim id lomba
        detail_button.clicked.connect(self.send_detail)

    @Slot()
    def send_detail(self):
        self.detail_clicked.emit(self.lomba_id)
