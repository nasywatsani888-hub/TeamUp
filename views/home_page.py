# views/home_page.py — Beranda (isi utama dashboard)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout
from views.card_grid import CardGrid
from views.content_page import ContentPage
from views.lomba_card import LombaCard
import config
import data_store
import helpers
import icons
import styles
import sizes


class HomePage(ContentPage):
    find_partner_clicked = Signal()
    lomba_detail_clicked = Signal(int)
    search_submitted = Signal(str)

    def __init__(self):
        super().__init__()   # kerangka 3 kolom + panel kanan ada di ContentPage
        self.build_center(self.center)

    # ---------- Kolom tengah ----------
    def build_center(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(20)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setStyleSheet(styles.SEARCH_STYLE)
        self.search_input.setPlaceholderText("Cari lomba...")
        self.search_input.addAction(icons.make_icon("search", config.COLOR_PRIMARY, 20),
                                    QLineEdit.ActionPosition.LeadingPosition)
        layout.addWidget(self.search_input)

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

        # Banner
        banner = QFrame()
        banner.setObjectName("Banner")
        banner.setStyleSheet(styles.BANNER_STYLE)
        banner.setMinimumHeight(230)
        banner_row = QHBoxLayout(banner)
        banner_row.setContentsMargins(32, 24, 32, 24)
        banner_text = QVBoxLayout()
        banner_text.addStretch()
        banner_label = QLabel("Temukan rekan kompetisi yang sempurna untuk Anda!")
        banner_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {config.COLOR_NAVY};")
        banner_label.setWordWrap(True)
        self.find_partner_button = QPushButton("Temukan Partner")
        self.find_partner_button.setStyleSheet(styles.BANNER_BUTTON_STYLE)
        self.find_partner_button.setCursor(Qt.CursorShape.PointingHandCursor)
        banner_text.addWidget(banner_label)
        banner_text.addSpacing(16)
        banner_text.addWidget(self.find_partner_button, alignment=Qt.AlignmentFlag.AlignLeft)
        banner_text.addStretch()
        banner_row.addLayout(banner_text)
        banner_row.addStretch()
        banner_row.addWidget(helpers.make_image("banner_burung.png", 280, "🦜🦜🦜🦜", 56))
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
        self.find_partner_button.clicked.connect(lambda: self.find_partner_clicked.emit())
        self.search_input.returnPressed.connect(self.handle_search)

    def handle_search(self):
        self.search_submitted.emit(self.search_input.text().strip())

    def show_lomba_terbaru(self):
        """Bangun ulang kartu lomba di Beranda dari data_store.lomba_list saat ini."""
        cards = []
        for lomba in data_store.lomba_list[:4]:
            card = LombaCard(lomba)
            card.setFixedWidth(sizes.LOMBA_CARD_WIDTH)
            card.detail_clicked.connect(lambda lomba_id: self.lomba_detail_clicked.emit(lomba_id))
            cards.append(card)
        self.card_grid.set_cards(cards)

    # Widget Lifecycle: state (data_store.lomba_list) bisa berubah di halaman lain
    # (mis. lomba baru disetujui admin), jadi kartu di Beranda disegarkan tiap tampil,
    # bukan hanya dibuat sekali di __init__.
    def refresh(self):
        self.show_lomba_terbaru()
