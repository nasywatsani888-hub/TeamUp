# views/content_page.py — kerangka halaman isi dashboard: [kolom tengah | (garis + kolom kanan, opsional)]
# Kolom tengah bisa di-scroll atas-bawah saja (kanan-kiri dikunci).
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QWidget
import sizes
from views.base_page import BasePage


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
        self.divider = divider
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #E5E7EB;")
        # Panel kanan: default TIDAK ADA (kartu profil sudah pindah ke sidebar kiri).
        # Hanya halaman yang membutuhkannya yang mengirim panel sendiri, mis.
        # LombaDetailPage memakai SuggestedPartnerPanel / "Rekomendasi Rekan".
        # Panel boleh punya method refresh() -- dipanggil lewat Widget Lifecycle (on_show).
        self.right_panel = right_panel

        columns.addWidget(self.center, 1)
        if self.right_panel is not None:
            columns.addWidget(divider)
            columns.addWidget(self.right_panel, 0, Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        if self.right_panel is not None and hasattr(self.right_panel, "edit_profile_clicked"):
            self.right_panel.edit_profile_clicked.connect(lambda: self.edit_profile_clicked.emit())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        show_side = event.size().width() >= sizes.RIGHT_PANEL_BREAKPOINT
        self.divider.setVisible(show_side)
        self.right_panel.setVisible(show_side)
        
    # Widget Lifecycle: panel kanan selalu di-refresh (kalau punya refresh()), lalu isi halaman turunan
    def on_show(self):
        if self.right_panel is not None and hasattr(self.right_panel, "refresh"):
            self.right_panel.refresh()
        self.refresh()

    def refresh(self):
        pass
