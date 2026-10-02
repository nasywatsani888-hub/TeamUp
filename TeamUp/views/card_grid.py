# views/card_grid.py — grid kartu yang jumlah kolomnya menyesuaikan lebar (tanpa scroll kanan-kiri)
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget


class CardGrid(QWidget):
    def __init__(self, card_width, spacing=20):
        super().__init__()
        self.card_width = card_width
        self.spacing = spacing
        self.cards = []

        # PENTING: tanpa ini, begitu grid pernah tersusun mis. 4 kolom (butuh
        # ruang lebar), lebar minimumnya "terkunci" di situ selamanya --
        # jendela tidak akan pernah diizinkan menyempit lagi di bawah lebar
        # itu, sehingga kolom tidak pernah berkurang lagi saat jendela
        # diperkecil (baru muncul lagi setelah dibesarkan lalu dikecilkan
        # ulang). Dengan minimum width dikunci ke SATU kartu saja, Qt selalu
        # boleh menyempitkan CardGrid, resizeEvent selalu terpicu, dan
        # arrange() selalu sempat menghitung ulang jumlah kolom -- sehingga
        # tidak pernah butuh geser kanan-kiri.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(spacing)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def minimumSizeHint(self):
        return QSize(self.card_width, self.grid.minimumSize().height())

    def set_cards(self, cards):
        """Ganti seluruh kartu dengan daftar baru."""
        for card in self.cards:
            card.deleteLater()
        self.cards = cards
        self.arrange()

    def arrange(self):
        while self.grid.count():
            self.grid.takeAt(0)   # lepas dari grid (widget-nya sendiri tidak dihapus)
        columns = max(1, (self.width() + self.spacing) // (self.card_width + self.spacing))
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arrange()
