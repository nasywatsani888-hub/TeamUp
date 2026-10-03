# views/post_detail_page.py — detail satu postingan; isi berbeda tiap status
# (Ditangguhkan / Disetujui / Revisi / Ditolak). Dialog & penghapusan data diurus DashboardPage.
import html
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from views.content_page import ContentPage
import config
import data_store
import helpers
import icons
import styles
import sizes


def format_hari(hari):
    return "hari ini" if hari == 0 else f"{hari} hari lalu"


class PostDetailPage(ContentPage):
    back_clicked = Signal()
    edit_blocked_requested = Signal(int)   # Edit postingan ditekan saat Ditangguhkan
    cancel_requested = Signal(int)         # Batalkan Pengajuan
    delete_requested = Signal(int)         # ikon sampah (Revisi / Ditolak)
    revise_requested = Signal(int)         # Perbaiki & kirim ulang
    new_post_requested = Signal()          # Unggah Lomba Baru
    contact_admin_requested = Signal()     # Hubungi Admin

    def __init__(self):
        super().__init__()
        self.post = None          # salinan data postingan yang sedang dilihat
        self.cancelled = False    # True setelah 'Batalkan Pengajuan' berhasil

        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Pita berwarna di atas (warna sesuai status) berisi panah kembali
        self.band = QFrame()
        self.band.setFixedHeight(64)
        band_row = QHBoxLayout(self.band)
        band_row.setContentsMargins(24, 0, 24, 0)
        self.back_button = QPushButton()
        self.back_button.setIconSize(QSize(26, 26))
        self.back_button.setStyleSheet(styles.BACK_BUTTON_STYLE)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        band_row.addWidget(self.back_button)
        band_row.addStretch()
        layout.addWidget(self.band)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(40, 24, sizes.CONTENT_MARGIN + 8, 32)
        self.body_layout.setSpacing(14)
        layout.addWidget(self.body)
        layout.addStretch()

        self.back_button.clicked.connect(self.back_clicked)

    # ---------- Dibuka dari Dashboard ----------
    def show_post(self, post_id, cancelled=False, salinan=None):
        """salinan dipakai setelah 'Batalkan Pengajuan' (datanya sudah dihapus dari data_store)."""
        self.cancelled = cancelled
        self.post = dict(salinan) if salinan else dict(data_store.get_postingan_by_id(post_id))
        self.build()

    def build(self):
        post = self.post
        status = post["status"]
        color = styles.POST_BAND_COLORS[status]
        arrow_color = "#FFFFFF" if status in styles.POST_BAND_DARK else config.COLOR_NAVY
        self.band.setStyleSheet(f"background-color: {color};")
        self.back_button.setIcon(icons.make_icon("arrow-left", arrow_color, 26))
        helpers.clear_layout(self.body_layout)
        add = self.body_layout.addWidget

        if self.cancelled:
            add(self.make_cancel_banner())

        # Kategori + judul + badge status
        chip = QLabel(post["kategori"])
        chip.setStyleSheet(styles.POST_CATEGORY_CHIP_STYLE)
        add(chip, alignment=Qt.AlignmentFlag.AlignLeft)
        title_row = QHBoxLayout()
        title = QLabel(post["judul"])
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {config.COLOR_NAVY};")
        title_row.addWidget(title, 1)
        background, foreground = styles.POST_STATUS_COLORS[status]
        badge = QLabel(status)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(sizes.POST_BADGE_WIDTH)
        badge.setStyleSheet(f"background-color: {background}; color: {foreground}; border-radius: 12px; "
                            "padding: 5px 0px; font-size: 12px; font-weight: bold;")
        title_row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        self.body_layout.addLayout(title_row)
        subtitle = QLabel(self.make_subtitle_text())
        subtitle.setStyleSheet("font-size: 12px;")
        add(subtitle)

        if status == "Ditangguhkan":
            add(self.make_box(styles.POST_BOX_YELLOW, "ⓘ", "#E8892B", "Sedang diverifikasi admin",
                              "Postingan kamu belum tampil untuk publik. Proses verifikasi selesai paling "
                              "lambat 1x24 jam. Anda akan dapat notifikasi apabila lomba berhasil diverifikasi."))
            self.body_layout.addLayout(self.make_stats())
            self.add_description()
            self.add_dates()
            self.add_buttons_ditangguhkan()
        elif status == "Disetujui":
            self.body_layout.addLayout(self.make_stats())
            self.add_description()
            self.add_dates()
        elif status == "Revisi":
            self.add_revisi()
        else:   # Ditolak
            self.add_ditolak()
        self.body_layout.addStretch()

    # ---------- Bagian-bagian halaman ----------
    def make_subtitle_text(self):
        post = self.post
        organizer = f"Diselenggarakan oleh {post['penyelenggara']}"
        diunggah = f"Diunggah {format_hari(post['diunggah_hari_lalu'])}"
        status = post["status"]
        if status == "Disetujui":
            parts = [organizer, diunggah]
        elif status == "Ditolak":
            parts = [diunggah, "Postingan kamu"]
        else:
            parts = [organizer, "Postingan kamu"]
        return "  •  ".join(parts)

    def make_box(self, style, icon_text, icon_color, title, message, footer=""):
        """Kotak catatan: ikon di kiri, judul tebal, isi, dan (opsional) keterangan kecil di bawah."""
        box = QFrame()
        box.setObjectName("PostBox")
        box.setStyleSheet(style)
        row = QHBoxLayout(box)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(10)
        icon = QLabel(icon_text)
        icon.setStyleSheet(f"font-size: 16px; color: {icon_color}; background: transparent;")
        row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setSpacing(3)
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {icon_color}; background: transparent;")
            column.addWidget(title_label)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 11px; background: transparent;")
        column.addWidget(message_label)
        if footer:
            footer_label = QLabel(footer)
            footer_label.setStyleSheet(f"font-size: 10px; color: {config.COLOR_SUBTEXT}; background: transparent;")
            column.addWidget(footer_label)
        row.addLayout(column, 1)
        return box

    def make_cancel_banner(self):
        return self.make_box(styles.POST_BOX_GREEN, "✓", config.COLOR_SUCCESS, "Pengajuan Berhasil Dibatalkan",
                             f"Pengajuan {self.post['judul']} telah dibatalkan, anda dapat membuat pengajuan "
                             "baru jika diperlukan.")

    def make_stats(self):
        """Tiga angka: Kali dilihat | Tersimpan | Rekan tertarik (dipisah garis tipis)."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 10, 0, 10)
        items = [(self.post["dilihat"], "Kali dilihat"), (self.post["tersimpan"], "Tersimpan"),
                 (self.post["partner_tertarik"], "Rekan tertarik")]
        for index, (number, text) in enumerate(items):
            if index > 0:
                divider = QFrame()
                divider.setFixedSize(1, 34)
                divider.setStyleSheet(styles.POST_STAT_DIVIDER_STYLE)
                row.addWidget(divider)
            column = QVBoxLayout()
            column.setSpacing(0)
            number_label = QLabel(str(number))
            number_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {config.COLOR_NAVY};")
            text_label = QLabel(text)
            text_label.setStyleSheet(f"font-size: 11px; color: {config.COLOR_SUBTEXT};")
            for label in (number_label, text_label):
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                column.addWidget(label)
            row.addLayout(column, 1)
        return row

    def make_heading(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {config.COLOR_NAVY};")
        return label

    def add_description(self):
        self.body_layout.addWidget(self.make_heading("Deskripsi"))
        description = QLabel(self.post["deskripsi"])
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px;")
        self.body_layout.addWidget(description)

    def add_dates(self):
        row = QHBoxLayout()
        row.setSpacing(40)
        for text, value in (("Tanggal lomba", self.post["tanggal_lomba"]),
                            ("Deadline daftar", self.post["tenggat_lomba"])):
            column = QVBoxLayout()
            column.setSpacing(1)
            label = QLabel(text)
            label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {config.COLOR_NAVY};")
            date_label = QLabel(helpers.format_tanggal(value))
            date_label.setStyleSheet("font-size: 12px;")
            column.addWidget(label)
            column.addWidget(date_label)
            row.addLayout(column)
        row.addStretch()
        self.body_layout.addLayout(row)

    def make_button(self, text, style, icon_name=None, icon_color=None):
        button = QPushButton(text)
        button.setStyleSheet(style)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            button.setIcon(icons.make_icon(icon_name, icon_color, 16))
            button.setIconSize(QSize(16, 16))
        return button

    def make_trash_button(self):
        button = QPushButton()
        button.setStyleSheet(styles.POST_TRASH_BUTTON_STYLE)
        button.setIcon(icons.make_icon("trash", "#D9534F", 18))
        button.setIconSize(QSize(18, 18))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.delete_requested.emit(self.post["id"]))
        return button

    def add_buttons_ditangguhkan(self):
        self.body_layout.addSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(14)
        if self.cancelled:
            back = self.make_button("Kembali", styles.POST_BLUE_BUTTON_STYLE)
            back.clicked.connect(self.back_clicked)
            row.addWidget(back, 1)
        else:
            edit = self.make_button("Edit postingan", styles.POST_OUTLINE_BUTTON_STYLE, "edit", config.COLOR_NAVY)
            cancel = self.make_button("Batalkan Pengajuan", styles.POST_BLUE_BUTTON_STYLE)
            edit.clicked.connect(lambda: self.edit_blocked_requested.emit(self.post["id"]))
            cancel.clicked.connect(lambda: self.cancel_requested.emit(self.post["id"]))
            row.addWidget(edit, 1)
            row.addWidget(cancel, 1)
        self.body_layout.addLayout(row)

    def add_revisi(self):
        post = self.post
        quote = "“" + post["catatan_admin"] + "”"
        self.body_layout.addWidget(self.make_box(
            styles.POST_BOX_YELLOW, "ⓘ", "#E8892B", "Catatan perbaikan", quote,
            f"Dikirim oleh Admin  •  {format_hari(post['catatan_hari_lalu'])}"))
        self.body_layout.addWidget(self.make_heading("Bagian yang perlu diperbaiki"))
        if post["bagian_diperbaiki"] == "link":
            box = QFrame()
            box.setObjectName("PostBox")
            box.setStyleSheet(styles.POST_BOX_RED)
            row = QHBoxLayout(box)
            row.setContentsMargins(14, 10, 14, 10)
            row.setSpacing(10)
            icon = QLabel("ⓘ")
            icon.setStyleSheet("font-size: 16px; color: #D9534F; background: transparent;")
            column = QVBoxLayout()
            column.setSpacing(1)
            name = QLabel("Link pendaftaran resmi")
            name.setStyleSheet("font-size: 12px; font-weight: bold; color: #D9534F; background: transparent;")
            value = QLabel(html.escape(post["link"]) + '   <span style="color:#D9534F">(Tidak Valid)</span>')
            value.setTextFormat(Qt.TextFormat.RichText)
            value.setStyleSheet("font-size: 11px; background: transparent;")
            column.addWidget(name)
            column.addWidget(value)
            row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
            row.addLayout(column, 1)
            self.body_layout.addWidget(box)
        self.body_layout.addWidget(self.make_heading("Ringkasan isinya (tidak berubah)"))
        self.add_dates()
        self.body_layout.addSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(12)
        fix = self.make_button("Perbaiki && kirim ulang", styles.POST_BLUE_BUTTON_STYLE, "edit", "#FFFFFF")
        fix.clicked.connect(lambda: self.revise_requested.emit(post["id"]))
        row.addWidget(fix, 1)
        row.addWidget(self.make_trash_button())
        self.body_layout.addLayout(row)

    def add_ditolak(self):
        post = self.post
        quote = "“" + post["catatan_admin"] + "”"
        self.body_layout.addWidget(self.make_box(
            styles.POST_BOX_RED, "ⓘ", "#D9534F", "Alasan penolakan dari admin", quote,
            f"Dikirim oleh Admin  •  {format_hari(post['catatan_hari_lalu'])}"))
        self.body_layout.addWidget(self.make_box(
            styles.POST_BOX_YELLOW, "ⓘ", "#E8892B", "",
            "Postingan yang ditolak tidak bisa diedit langsung. Apabila memiliki bukti resmi tambahan, "
            "unggah ulang sebagai postingan baru dengan dokumen yang lebih lengkap."))
        self.body_layout.addSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(12)
        new = self.make_button("+  Unggah Lomba Baru", styles.POST_BLUE_BUTTON_STYLE)
        contact = self.make_button("Hubungi Admin", styles.POST_OUTLINE_BUTTON_STYLE)
        new.clicked.connect(self.new_post_requested)
        contact.clicked.connect(self.contact_admin_requested)
        row.addWidget(new, 2)
        row.addWidget(contact, 1)
        row.addWidget(self.make_trash_button())
        self.body_layout.addLayout(row)
