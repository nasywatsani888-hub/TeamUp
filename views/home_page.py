# views/home_page.py — Beranda (isi utama dashboard)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from views.card_grid import CardGrid
from views.content_page import ContentPage
from views.lomba_card import LombaCard
import config
import data_store
import helpers
import styles
import sizes


class HomePage(ContentPage):
    find_partner_clicked = Signal()
    lomba_detail_clicked = Signal(int)

    def __init__(self):
        super().__init__()   # kerangka kolom tengah ada di ContentPage
        self.build_center(self.center)

    # ---------- Kolom tengah ----------
    def build_center(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(20)

        # Sapaan: maskot + judul di satu baris, subjudul tepat di bawahnya (sesuai desain)
        greeting = QHBoxLayout()
        greeting.setSpacing(14)
        greeting.addWidget(helpers.make_image("burung.png", 64, "🦜", 40))
        title = QLabel("Halo, sobat TeamUP!")
        title.setStyleSheet(f"font-size: 34px; font-weight: bold; color: {config.COLOR_NAVY};")
        greeting.addWidget(title)
        greeting.addStretch()
        layout.addLayout(greeting)
        subtitle = QLabel("Temukan rekan yang tepat, ikuti kompetisi seru, dan raih kemenangan bersama!")
        subtitle.setStyleSheet("font-size: 14px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Banner (ukuran dan teks mengikuti desain Figma: tinggi 186, judul + deskripsi + tombol)
        banner = QFrame()
        banner.setObjectName("Banner")
        banner.setStyleSheet(styles.BANNER_STYLE)
        banner.setFixedHeight(sizes.BANNER_HEIGHT)
        banner_row = QHBoxLayout(banner)
        banner_row.setContentsMargins(41, 16, 48, 16)
        banner_text = QVBoxLayout()
        banner_text.setSpacing(0)
        banner_text.addStretch()
        banner_label = QLabel("Temukan rekan kompetisi yang sempurna untuk Anda!")
        banner_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {config.COLOR_NAVY};")
        banner_label.setWordWrap(True)
        banner_desc = QLabel("Berdasarkan skill, minat dan tujuan kompetisimu, kami bantu carikan rekan yang cocok denganmu!")
        banner_desc.setStyleSheet("font-size: 12px;")
        banner_desc.setWordWrap(True)
        self.find_partner_button = QPushButton("Temukan Partner")
        self.find_partner_button.setStyleSheet(styles.BANNER_BUTTON_STYLE)
        self.find_partner_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.find_partner_button.setFixedHeight(sizes.BANNER_BUTTON_HEIGHT)
        self.find_partner_button.setMaximumWidth(sizes.BANNER_BUTTON_WIDTH)
        self.find_partner_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button_row = QHBoxLayout()           # tombol di tengah, mengecil kalau ruangnya sempit
        button_row.addStretch(1)
        button_row.addWidget(self.find_partner_button, 10)
        button_row.addStretch(1)
        banner_text.addWidget(banner_label)
        banner_text.addSpacing(6)
        banner_text.addWidget(banner_desc)
        banner_text.addSpacing(18)
        banner_text.addLayout(button_row)
        banner_text.addStretch()
        banner_row.addLayout(banner_text, 1)   # kolom teks memakai sisa lebar (tidak terjepit gambar)
        banner_row.addWidget(helpers.make_image("banner_burung.png", sizes.BANNER_IMAGE_WIDTH, "🦜🦜🦜🦜", 56))
        layout.addWidget(banner)

        # Kartu lomba: pakai CardGrid (bukan QHBoxLayout biasa) supaya kolomnya
        # menyesuaikan lebar jendela dan TIDAK PERNAH melebar sampai perlu geser
        # kanan-kiri -- hanya boleh geser atas-bawah (lihat ContentPage/CardGrid).
        # Isinya dibangun ulang lewat show_lomba_terbaru() setiap Beranda tampil,
        # supaya selalu sinkron dengan data_store.lomba_list terbaru.
        self.card_grid = CardGrid(sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_CARD_SPACING)
        layout.addWidget(self.card_grid)
        layout.addStretch()

        # Signal & Slot
        self.find_partner_button.clicked.connect(self.find_partner_clicked)

    def show_lomba_terbaru(self):
        """Bangun ulang kartu lomba di Beranda dari data_store.lomba_list saat ini."""
        cards = []
        for lomba in data_store.lomba_list[:4]:
            card = LombaCard(lomba)
            card.setFixedWidth(sizes.LOMBA_CARD_WIDTH)
            card.detail_clicked.connect(self.lomba_detail_clicked)
            cards.append(card)
        self.card_grid.set_cards(cards)

    # Widget Lifecycle: state (data_store.lomba_list) bisa berubah di halaman lain
    # (mis. lomba baru disetujui admin), jadi kartu di Beranda disegarkan tiap tampil,
    # bukan hanya dibuat sekali di __init__.
    def refresh(self):
        self.show_lomba_terbaru()
