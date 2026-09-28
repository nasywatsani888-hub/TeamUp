# views/content_page.py — kerangka halaman isi dashboard: [kolom tengah | garis | kolom kanan]
# Kolom tengah bisa di-scroll atas-bawah saja (kanan-kiri dikunci).
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QWidget
from views.base_page import BasePage
from views.right_panel import RightPanel


class ContentPage(BasePage):
    edit_profile_clicked = Signal()

    def __init__(self, right_panel=None):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        self.scroll = scroll   # dipakai halaman turunan untuk kembali ke posisi atas
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        columns = QHBoxLayout(content)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)

        self.center = QWidget()      # halaman turunan mengisi kolom tengah ini
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #E5E7EB;")
        # Panel kanan: default kartu profil + tenggat pendaftaran (RightPanel), tapi
        # halaman turunan boleh mengganti dengan panel lain (mis. LombaDetailPage
        # memakai SuggestedPartnerPanel / "Rekomendasi Rekan") selama punya
        # method refresh() -- dipanggil otomatis lewat Widget Lifecycle (on_show).
        self.right_panel = right_panel if right_panel is not None else RightPanel()

        columns.addWidget(self.center, 1)
        columns.addWidget(divider)
        columns.addWidget(self.right_panel, 0, Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        if hasattr(self.right_panel, "edit_profile_clicked"):
            self.right_panel.edit_profile_clicked.connect(lambda: self.edit_profile_clicked.emit())

    # Widget Lifecycle: panel kanan selalu di-refresh (kalau punya refresh()), lalu isi halaman turunan
    def on_show(self):
        if hasattr(self.right_panel, "refresh"):
            self.right_panel.refresh()
        self.refresh()

    def refresh(self):
        pass
