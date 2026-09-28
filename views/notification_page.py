# views/notification_page.py — halaman Notifikasi
# Tab: Semua | Belum dibaca. Klik notifikasi -> ditandai dibaca -> buka tujuannya.
import html
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from views.base_page import BasePage
import config
import data_store
import helpers
import icons
import styles
import sizes


def make_icon_circle(jenis):
    """Lingkaran ikon di kiri notifikasi (warna & simbol sesuai jenis)."""
    circle = QLabel()
    circle.setFixedSize(sizes.NOTIFICATION_ICON_SIZE, sizes.NOTIFICATION_ICON_SIZE)
    circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if jenis == "partner":
        circle.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; border-radius: 20px;")
        circle.setPixmap(icons.make_icon("user-plus", "white", 22).pixmap(QSize(22, 22)))
    elif jenis == "disetujui":
        circle.setText("✓")
        circle.setStyleSheet("background-color: #7BC950; color: white; border-radius: 20px; "
                             "font-size: 20px; font-weight: bold;")
    else:   # revisi
        circle.setText("!")
        circle.setStyleSheet("background-color: #FDE2E7; color: #E53935; border: 2px solid #E53935; "
                             "border-radius: 20px; font-size: 18px; font-weight: bold;")
    return circle


def make_message(notif):
    """Kalimat notifikasi (HTML sederhana: judul postingan dicetak tebal)."""
    if notif["jenis"] == "partner":
        return f"{html.escape(notif['nama'])} tertarik jadi partner kamu di {html.escape(notif['lomba'])}"
    if notif["jenis"] == "disetujui":
        return f"Postingan <b>{html.escape(notif['judul'])}</b> kamu disetujui admin"
    return f"Postingan <b>{html.escape(notif['judul'])}</b> perlu revisi - lihat catatan admin"


class NotificationItem(QFrame):
    """Satu baris notifikasi; seluruh baris bisa diklik."""
    clicked = Signal(int)   # id notifikasi

    def __init__(self, notif):
        super().__init__()
        self.notif_id = notif["id"]
        self.setObjectName("NotifItem")
        self.setProperty("unread", not notif["dibaca"])   # belum dibaca -> latar biru + titik
        self.setStyleSheet(styles.NOTIF_ITEM_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 20, 10)
        row.setSpacing(14)
        row.addWidget(make_icon_circle(notif["jenis"]))

        text = QVBoxLayout()
        text.setSpacing(2)
        message = QLabel(make_message(notif))
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: 13px; color: {config.COLOR_NAVY};")
        time_label = QLabel(helpers.format_waktu(notif["menit_lalu"]))
        time_label.setStyleSheet(f"font-size: 12px; color: {config.COLOR_SUBTEXT};")
        text.addWidget(message)
        text.addWidget(time_label)
        row.addLayout(text, 1)

        if not notif["dibaca"]:
            dot = QLabel()
            dot.setFixedSize(sizes.NOTIFICATION_DOT_SIZE, sizes.NOTIFICATION_DOT_SIZE)
            dot.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; border-radius: 4px;")
            row.addWidget(dot)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.notif_id)
        super().mousePressEvent(event)


class NotificationPage(BasePage):
    partner_profile_requested = Signal(str)   # email partner
    post_requested = Signal(str)              # status postingan: "Disetujui" / "Revisi"

    def __init__(self):
        super().__init__()
        self.only_unread = False   # False = tab Semua, True = tab Belum dibaca
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(14)

        title = QLabel("Notifikasi")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {config.COLOR_NAVY};")
        layout.addWidget(title)

        tabs = QHBoxLayout()
        tabs.setSpacing(10)
        self.all_tab = QPushButton("Semua")
        self.unread_tab = QPushButton("Belum dibaca")
        for tab in (self.all_tab, self.unread_tab):
            tab.setStyleSheet(styles.NOTIF_TAB_STYLE)
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            tabs.addWidget(tab)
        tabs.addStretch()
        layout.addLayout(tabs)

        self.list_layout = QVBoxLayout()   # isi: judul grup + baris notifikasi (semua widget)
        self.list_layout.setSpacing(10)
        layout.addLayout(self.list_layout)
        layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        # Signal & Slot
        self.all_tab.clicked.connect(lambda: self.select_tab(False))
        self.unread_tab.clicked.connect(lambda: self.select_tab(True))

    # ---------- Listener (slot) ----------
    def select_tab(self, only_unread):
        self.only_unread = only_unread
        self.show_notifications()

    def handle_item_clicked(self, notif_id):
        data_store.tandai_dibaca(notif_id)
        notif = data_store.get_notifikasi_by_id(notif_id)
        if notif["jenis"] == "partner":
            self.partner_profile_requested.emit(notif["email"])
        elif notif["jenis"] == "disetujui":
            self.post_requested.emit("Disetujui")
        else:
            self.post_requested.emit("Revisi")

    # ---------- Tampilan ----------
    def add_group(self, heading, items):
        if len(items) == 0:
            return
        label = QLabel(heading)
        label.setStyleSheet(styles.NOTIF_GROUP_STYLE)
        self.list_layout.addWidget(label)
        for notif in items:
            item = NotificationItem(notif)
            item.clicked.connect(self.handle_item_clicked)
            self.list_layout.addWidget(item)

    def show_notifications(self):
        for tab, active in ((self.all_tab, not self.only_unread), (self.unread_tab, self.only_unread)):
            tab.setProperty("active", active)
            tab.style().unpolish(tab)
            tab.style().polish(tab)

        helpers.clear_layout(self.list_layout)
        notifs = data_store.get_notifikasi(self.only_unread)
        if len(notifs) == 0:
            text = "Semua notifikasi sudah dibaca." if self.only_unread else "Belum ada notifikasi."
            empty = QLabel(text)
            empty.setStyleSheet(f"font-size: 15px; color: {config.COLOR_SUBTEXT};")
            self.list_layout.addWidget(empty)
            return
        one_day = 24 * 60
        self.add_group("Hari ini", [n for n in notifs if n["menit_lalu"] < one_day])
        self.add_group("Minggu ini", [n for n in notifs if n["menit_lalu"] >= one_day])

    # Widget Lifecycle: daftar di-refresh setiap halaman tampil (mis. kembali dari profil)
    def on_show(self):
        self.show_notifications()
