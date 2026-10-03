# views/upload_page.py — halaman Unggah Postingan: tab "Unggah Baru" | "Postingan Saya"
# Tahap ini: "Postingan Saya" (daftar + filter status). "Unggah Baru" (formulir) menyusul.
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)
from views.base_page import BasePage
import config
import data_store
import helpers
import styles
import sizes


def format_hari(hari):
    return "hari ini" if hari == 0 else f"{hari} hari lalu"


class PostItem(QFrame):
    """Satu baris postingan: gambar kecil, judul + keterangan, badge status di kanan.
    Diklik -> sinyal clicked(id) -> Dashboard membuka detail postingan."""
    clicked = Signal(int)

    def __init__(self, post):
        super().__init__()
        self.post_id = post["id"]
        self.setObjectName("PostItem")
        self.setStyleSheet(styles.POST_ITEM_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 14, 10)
        row.setSpacing(12)

        thumb = QLabel()
        thumb.setFixedSize(sizes.POST_THUMB_SIZE, sizes.POST_THUMB_SIZE)
        thumb.setStyleSheet(styles.POST_THUMB_STYLE)
        row.addWidget(thumb, alignment=Qt.AlignmentFlag.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(post["judul"])
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {config.COLOR_NAVY};")
        info = QLabel()
        info.setWordWrap(True)
        self.fill_info(info, post)
        text.addWidget(title)
        text.addWidget(info)
        row.addLayout(text, 1)

        background, foreground = styles.POST_STATUS_COLORS[post["status"]]
        badge = QLabel(post["status"])
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(sizes.POST_BADGE_WIDTH)
        badge.setStyleSheet(
            f"background-color: {background}; color: {foreground}; border-radius: 12px; "
            "padding: 5px 0px; font-size: 12px; font-weight: bold;")
        row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        self.clicked.emit(self.post_id)

    def fill_info(self, label, post):
        """Keterangan di bawah judul (isinya beda tiap status, sesuai desain)."""
        status = post["status"]
        if status == "Revisi":
            label.setText("Perlu revisi: " + post["alasan_singkat"])
            label.setStyleSheet("font-size: 11px; color: #E39A1F;")
        elif status == "Ditolak":
            label.setText("Ditolak: " + post["alasan_singkat"])
            label.setStyleSheet("font-size: 11px; color: #D32F2F;")
        elif status == "Ditangguhkan":
            label.setText(f"Diunggah {format_hari(post['diunggah_hari_lalu'])}  •  sedang ditinjau admin")
            label.setStyleSheet("font-size: 11px; color: #1F2937;")
        else:   # Disetujui
            label.setText(f"Diunggah {format_hari(post['diunggah_hari_lalu'])}  •  {post['dilihat']} dilihat"
                          f"  •  {post['partner_tertarik']} partner tertarik")
            label.setStyleSheet("font-size: 11px; color: #1F2937;")


class UploadPage(BasePage):
    new_post_requested = Signal()     # tab "Unggah Baru" -> formulir
    post_clicked = Signal(int)        # baris postingan -> detail

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.status_filter = None   # None = Semua

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(sizes.CONTENT_MARGIN, 28, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(14)

        title = QLabel("Unggah postingan")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {config.COLOR_NAVY};")
        layout.addWidget(title)

        # ----- Tab utama: Unggah Baru | Postingan Saya -----
        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.new_tab = self.make_button("Unggah Baru", styles.POST_TAB_STYLE)
        self.mine_tab = self.make_button("Postingan Saya", styles.POST_TAB_STYLE)
        self.tab_group = QButtonGroup(self)
        for button in (self.new_tab, self.mine_tab):
            self.tab_group.addButton(button)
            tabs.addWidget(button)
        tabs.addStretch()
        layout.addLayout(tabs)

        # Postingan Saya: chip status + daftar
        mine_layout = QVBoxLayout()
        mine_layout.setContentsMargins(0, 8, 0, 0)
        mine_layout.setSpacing(14)
        layout.addLayout(mine_layout)
        self.chip_row = QHBoxLayout()
        self.chip_row.setSpacing(10)
        self.chip_group = QButtonGroup(self)
        self.chips = {}   # nama status ("Semua", "Revisi", ...) -> tombol
        for name in ["Semua"] + data_store.STATUS_POSTINGAN:
            chip = self.make_button(name, styles.POST_CHIP_STYLE)
            self.chip_group.addButton(chip)
            self.chip_row.addWidget(chip)
            self.chips[name] = chip
            chip.clicked.connect(lambda checked=False, n=name: self.select_status(n))
        self.chip_row.addStretch()
        mine_layout.addLayout(self.chip_row)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(12)
        mine_layout.addLayout(self.list_layout)

        layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        # Signal & Slot: tab utama
        self.new_tab.clicked.connect(self.handle_new_tab)
        self.reset_state()

    def make_button(self, text, style):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setStyleSheet(style)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    # ---------- Listener (slot) ----------
    def handle_new_tab(self):
        self.mine_tab.setChecked(True)   # tab 'Postingan Saya' tetap menyala; formulir ada di halaman lain
        self.new_post_requested.emit()

    def select_status(self, name):
        """name = 'Semua' atau salah satu status. Dipanggil juga dari Notifikasi (lewat Dashboard)."""
        self.status_filter = None if name == "Semua" else name
        self.chips[name].setChecked(True)
        self.show_posts()

    def open_my_posts(self, status=None):
        """Dipanggil Dashboard: buka 'Postingan Saya' dengan filter status tertentu."""
        self.mine_tab.setChecked(True)
        self.select_status(status if status in self.chips else "Semua")

    def reset_state(self):
        self.mine_tab.setChecked(True)
        self.select_status("Semua")

    # ---------- Tampilan ----------
    def show_posts(self):
        counts = data_store.hitung_postingan()
        for name, chip in self.chips.items():
            chip.setText(f"{name} ({counts[name]})")
        helpers.clear_layout(self.list_layout)
        posts = data_store.get_postingan(self.status_filter)
        if len(posts) == 0:
            empty = QLabel("Belum ada postingan dengan status ini.")
            empty.setStyleSheet(f"font-size: 14px; color: {config.COLOR_SUBTEXT};")
            self.list_layout.addWidget(empty)
            return
        for post in posts:
            item = PostItem(post)
            item.clicked.connect(self.post_clicked)
            self.list_layout.addWidget(item)

    # Widget Lifecycle: daftar di-refresh tiap halaman tampil; saat ditinggalkan, kembali ke awal
    def on_show(self):
        self.show_posts()

    def on_hide(self):
        self.reset_state()
