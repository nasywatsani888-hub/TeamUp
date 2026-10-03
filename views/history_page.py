# views/history_page.py — halaman Riwayat: lomba yang pernah dibuka (seperti riwayat penjelajahan)
# Setiap lomba tercatat otomatis saat detailnya dibuka (lihat DashboardPage.handle_lomba_detail).
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from views.base_page import BasePage
import config
import data_store
import helpers
import icons
import styles
import sizes


class HistoryItem(QFrame):
    """Satu baris riwayat; seluruh baris bisa diklik untuk membuka detail lomba."""
    clicked = Signal(int)   # id lomba

    def __init__(self, lomba):
        super().__init__()
        self.lomba_id = lomba["id"]
        self.setObjectName("HistoryItem")
        self.setStyleSheet(styles.HISTORY_ITEM_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 20, 10)
        row.setSpacing(14)

        # Ikon jam di lingkaran berwarna sesuai poster lomba
        icon = QLabel()
        icon.setFixedSize(sizes.HISTORY_ICON_SIZE, sizes.HISTORY_ICON_SIZE)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {lomba['warna']}; border-radius: 20px;")
        icon.setPixmap(icons.make_icon("clock", "white", 22).pixmap(QSize(22, 22)))
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(lomba["judul"])
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {config.COLOR_NAVY};")
        subtitle = QLabel(f"{lomba['penyelenggara']} • {lomba['kategori']}")
        subtitle.setStyleSheet(f"font-size: 12px; color: {config.COLOR_SUBTEXT};")
        text.addWidget(title)
        text.addWidget(subtitle)
        row.addLayout(text, 1)

        days = QLabel(helpers.format_sisa(lomba["sisa_hari"]))
        days.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {helpers.deadline_color(lomba['sisa_hari'])};")
        row.addWidget(days)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.lomba_id)
        super().mousePressEvent(event)


class HistoryPage(BasePage):
    lomba_detail_clicked = Signal(int)   # id lomba

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(14)

        title = QLabel("Riwayat")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {config.COLOR_NAVY};")
        layout.addWidget(title)
        subtitle = QLabel("Lomba yang pernah kamu lihat")
        subtitle.setStyleSheet("font-size: 14px;")
        layout.addWidget(subtitle)

        self.list_layout = QVBoxLayout()   # isi: baris riwayat (semua widget)
        self.list_layout.setSpacing(10)
        layout.addLayout(self.list_layout)
        layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

    def show_history(self):
        helpers.clear_layout(self.list_layout)
        items = data_store.get_history()
        if len(items) == 0:
            empty = QLabel("Belum ada riwayat. Lomba yang kamu buka detailnya akan tercatat di sini.")
            empty.setWordWrap(True)
            empty.setStyleSheet(f"font-size: 15px; color: {config.COLOR_SUBTEXT};")
            self.list_layout.addWidget(empty)
            return
        for lomba in items:
            item = HistoryItem(lomba)
            item.clicked.connect(self.lomba_detail_clicked)
            self.list_layout.addWidget(item)

    # Widget Lifecycle: daftar di-refresh setiap halaman tampil (mis. kembali dari detail lomba)
    def on_show(self):
        self.show_history()
