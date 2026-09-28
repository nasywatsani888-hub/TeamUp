# views/lomba_page.py — halaman Lomba ("Ayo jelajahi kompetisi!")
# Alur: pilih Kategori / Urutkan -> Terapkan -> daftar lomba -> Lihat Detail
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from views.card_grid import CardGrid
from views.content_page import ContentPage
from views.filter_bar import FilterBar
from views.lomba_card import LombaCard
import config
import data_store
import helpers
import sizes



class LombaPage(ContentPage):
    lomba_detail_clicked = Signal(int)   # id lomba

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(20)

        # Judul: maskot + judul (oranye), subjudul di bawahnya
        greeting = QHBoxLayout()
        greeting.setSpacing(12)
        greeting.addWidget(helpers.make_image("burung.png", 64, "🦜", 40))
        title = QLabel("Ayo jelajahi kompetisi!")
        title.setStyleSheet("font-size: 30px; font-weight: bold; color: #F5A623;")
        greeting.addWidget(title)
        greeting.addStretch()
        layout.addLayout(greeting)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.subtitle_label)

        # Filter (Kategori | Urutkan) dan daftar kartu
        self.filter_bar = FilterBar(data_store.get_kategori_lomba(), data_store.URUTAN_LOMBA,
                                    data_store.URUTAN_LOMBA_DEFAULT, accent="yellow")
        layout.addWidget(self.filter_bar)
        self.card_grid = CardGrid(sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_CARD_SPACING)
        layout.addWidget(self.card_grid)
        self.empty_label = QLabel("Belum ada lomba yang cocok dengan filter ini.")
        self.empty_label.setStyleSheet(f"font-size: 15px; color: {config.COLOR_SUBTEXT};")
        layout.addWidget(self.empty_label)
        layout.addStretch()

        # Signal & Slot: filter berubah -> tampilkan ulang daftar
        self.filter_bar.changed.connect(self.show_lomba)

    def show_lomba(self):
        items = data_store.get_lomba_terfilter(self.filter_bar.selected_categories,
                                               self.filter_bar.selected_order)
        self.subtitle_label.setText(f"{len(items)} lomba aktif yang terverifikasi")
        cards = []
        for lomba in items:
            card = LombaCard(lomba)
            card.setFixedWidth(sizes.LOMBA_CARD_WIDTH)
            card.detail_clicked.connect(lambda lomba_id: self.lomba_detail_clicked.emit(lomba_id))
            cards.append(card)
        self.card_grid.set_cards(cards)
        self.empty_label.setVisible(len(items) == 0)

    # Widget Lifecycle: data di-refresh setiap halaman tampil
    def refresh(self):
        self.show_lomba()

    def on_hide(self):
        self.filter_bar.close_popups()
