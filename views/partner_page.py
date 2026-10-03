# views/partner_page.py — halaman Rekan Tim / Temukan Partner
# Alur: pilih Kategori / Urutkan -> Terapkan -> daftar kandidat -> Kunjungi Profil
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from views.card_grid import CardGrid
from views.content_page import ContentPage
from views.filter_bar import FilterBar
import config
import data_store
import helpers
import styles
import sizes



class PartnerCard(QFrame):
    """Satu kartu calon rekan tim."""
    profile_clicked = Signal(str)   # email user yang dikunjungi

    def __init__(self, user):
        super().__init__()
        self.email = user["email"]   # disimpan di objek (bukan ditangkap lambda)
        self.setObjectName("PartnerCard")
        self.setStyleSheet(styles.PARTNER_CARD_STYLE)
        self.setFixedSize(sizes.PARTNER_CARD_WIDTH, sizes.PARTNER_CARD_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 16)
        layout.setSpacing(8)
        layout.addWidget(helpers.make_avatar(user, 90), alignment=Qt.AlignmentFlag.AlignHCenter)

        name = QLabel(user["nama"])
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {config.COLOR_NAVY};")
        layout.addWidget(name)
        campus = QLabel(f"{user['prodi']} - {user['universitas']}")
        campus.setWordWrap(True)
        campus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        campus.setStyleSheet(f"font-size: 12px; color: {config.COLOR_NAVY};")
        layout.addWidget(campus)

        # Maksimal 2 tag keahlian; sisanya diringkas "+N lagi"
        skills = user["keahlian"]
        for skill in skills[:2]:
            chip = QLabel(skill)
            chip.setStyleSheet(styles.CARD_CHIP_STYLE)
            layout.addWidget(chip, alignment=Qt.AlignmentFlag.AlignHCenter)
        if len(skills) > 2:
            more = QLabel(f"+{len(skills) - 2} lagi")
            more.setStyleSheet(f"font-size: 11px; color: {config.COLOR_SUBTEXT};")
            layout.addWidget(more, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()
        visit_button = QPushButton("Kunjungi Profil")
        visit_button.setStyleSheet(styles.VISIT_BUTTON_STYLE)
        visit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(visit_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        visit_button.clicked.connect(self.send_profile)

    @Slot()
    def send_profile(self):
        self.profile_clicked.emit(self.email)


class PartnerPage(ContentPage):
    profile_requested = Signal(str)   # email kandidat yang ingin dibuka

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(20)

        # Judul: maskot + judul, subjudul di bawahnya
        greeting = QHBoxLayout()
        greeting.setSpacing(12)
        greeting.addWidget(helpers.make_image("burung_rekan.png", 90, "🦜🦜🦜", 34))
        title = QLabel("Ayo temukan rekan timmu!")
        title.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {config.COLOR_NAVY};")
        greeting.addWidget(title)
        greeting.addStretch()
        layout.addLayout(greeting)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.subtitle_label)

        # Filter (Kategori | Urutkan) dan daftar kartu
        self.filter_bar = FilterBar(list(data_store.KATEGORI_PARTNER.keys()), data_store.URUTAN_OPSI,
                                    data_store.URUTAN_DEFAULT, accent="blue")
        layout.addWidget(self.filter_bar)
        self.card_grid = CardGrid(sizes.PARTNER_CARD_WIDTH, sizes.PARTNER_CARD_SPACING)
        layout.addWidget(self.card_grid)
        self.empty_label = QLabel("Belum ada rekan yang cocok dengan filter ini.")
        self.empty_label.setStyleSheet(f"font-size: 15px; color: {config.COLOR_SUBTEXT};")
        layout.addWidget(self.empty_label)
        layout.addStretch()

        # Signal & Slot: filter berubah -> tampilkan ulang daftar
        self.filter_bar.changed.connect(self.show_partners)

    def show_partners(self):
        """Ambil data sesuai filter, lalu bangun ulang kartu."""
        partners = data_store.get_partners(self.filter_bar.selected_categories, self.filter_bar.selected_order)
        self.subtitle_label.setText(f"{len(partners)} rekan tersedia")
        cards = []
        for user in partners:
            card = PartnerCard(user)
            card.profile_clicked.connect(self.profile_requested)
            cards.append(card)
        self.card_grid.set_cards(cards)
        self.empty_label.setVisible(len(partners) == 0)

    # Widget Lifecycle: data di-refresh setiap halaman tampil (mis. kembali dari profil)
    def refresh(self):
        self.show_partners()

    def on_hide(self):
        self.filter_bar.close_popups()
