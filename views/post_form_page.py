# views/post_form_page.py — formulir Unggah Info Lomba (baru) dan Perbaiki Informasi Lomba (revisi)
import os
import time
from PySide6.QtCore import QDate, QLocale, QSize, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QProgressBar,
                               QLineEdit, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)
from views.base_page import BasePage
from views.upload_dialog import DropZone
import config
import data_store
import helpers
import icons
import sizes
import styles
import workers


UKURAN_POTONGAN = 1024 * 1024   # berkas disalin per 1 MB supaya progres & pembatalan bisa dicek di sela-sela


def salin_berkas(kontrol, daftar):
    """Dijalankan WORKER (thread lain). daftar = [(sumber, tujuan), ...].
    Menyalin per potongan sambil melapor progres. Kalau dibatalkan / gagal, berkas yang sudah
    terlanjur dibuat dihapus lagi -> tidak ada sampah setengah jadi. Tidak menyentuh widget / data_store."""
    total = sum(os.path.getsize(sumber) for sumber, _ in daftar) or 1
    selesai = 0
    dibuat = []
    berhasil = False
    try:
        for sumber, tujuan in daftar:
            os.makedirs(os.path.dirname(tujuan), exist_ok=True)
            dibuat.append(tujuan)
            with open(sumber, "rb") as masuk, open(tujuan, "wb") as keluar:
                while True:
                    potongan = masuk.read(UKURAN_POTONGAN)
                    if not potongan:
                        break
                    if kontrol.dibatalkan:
                        return None
                    keluar.write(potongan)
                    selesai += len(potongan)
                    kontrol.laporkan(selesai * 100 // total)
        berhasil = True
        return [tujuan for _, tujuan in daftar]
    finally:
        if not berhasil:
            for tujuan in dibuat:
                if os.path.exists(tujuan):
                    os.remove(tujuan)


class FileField(QWidget):
    """Kotak 'Tarik atau pilih file' + keterangan format + pesan error.
    Format & ukuran diperiksa di sini (poster: PDF, maksimal 10 MB)."""

    def __init__(self, extensions, max_mb, hint):
        super().__init__()
        self.extensions = extensions
        self.max_mb = max_mb
        self.path = ""       # file baru yang dipilih user
        self.existing = ""   # nama file lama (mode revisi)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.zone = DropZone()
        self.zone.setFixedHeight(sizes.POST_FORM_FILE_HEIGHT)
        self.zone.text_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.zone)
        hint_label = QLabel(hint)
        hint_label.setProperty("role", "hint")
        layout.addWidget(hint_label)
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {config.COLOR_ERROR}; font-size: 11px;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Signal & Slot: klik kotak -> dialog pilih file; seret file -> langsung diperiksa
        self.zone.clicked.connect(self.handle_browse)
        self.zone.file_chosen.connect(self.handle_file_chosen)

    def handle_browse(self):
        patterns = " ".join("*" + ext for ext in self.extensions)
        path, _ = QFileDialog.getOpenFileName(self, "Pilih File", "", f"File ({patterns})")
        if path:
            self.handle_file_chosen(path)

    def handle_file_chosen(self, path):
        extension = os.path.splitext(path)[1].lower()
        if not os.path.isfile(path) or extension not in self.extensions:
            formats = ", ".join(ext.lstrip(".").upper() for ext in self.extensions)
            self.show_error(f"Format file harus {formats}.")
            return
        if os.path.getsize(path) > self.max_mb * 1024 * 1024:
            self.show_error(f"Ukuran file maksimal {self.max_mb} MB.")
            return
        self.error_label.hide()
        self.path = path
        self.zone.text_label.setText(os.path.basename(path))

    def show_error(self, text):
        self.error_label.setText(text)
        self.error_label.show()

    def has_file(self):
        return bool(self.path or self.existing)

    def file_name(self):
        return os.path.basename(self.path) if self.path else self.existing

    def set_existing(self, name):
        self.path = ""
        self.existing = name
        self.error_label.hide()
        self.zone.text_label.setText(name if name else "Tarik atau pilih file")

    def clear(self):
        self.set_existing("")


class PostFormPage(BasePage):
    back_clicked = Signal()
    submitted = Signal(int, str)   # (id postingan, mode "baru" / "revisi")

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.mode = "baru"
        self.post_id = None
        self.link_awal = ""   # link sebelum diperbaiki (mode revisi)
        self.sedang_mengirim = False   # True selama worker menyalin berkas
        self.token_kirim = None        # penanda pengiriman yang sedang berlaku (untuk mengabaikan hasil yang basi)
        self.worker = None             # worker penyalin berkas milik form ini (agar hanya ini yang dibatalkan)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("PostForm")
        content.setStyleSheet(styles.POST_FORM_STYLE)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, sizes.CONTENT_MARGIN, 28)
        layout.setSpacing(14)
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        # ----- Judul halaman: panah kembali + judul + keterangan -----
        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton()
        self.back_button.setIcon(icons.make_icon("arrow-left", config.COLOR_NAVY, 24))
        self.back_button.setIconSize(QSize(24, 24))
        self.back_button.setStyleSheet(styles.BACK_BUTTON_STYLE)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        self.title_label = QLabel("Unggah info lomba")
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {config.COLOR_NAVY};")
        subtitle = QLabel("Postingan akan diunggah setelah diverifikasi")
        subtitle.setStyleSheet("font-size: 11px;")
        title_column.addWidget(self.title_label)
        title_column.addWidget(subtitle)
        header.addLayout(title_column, 1)
        layout.addLayout(header)

        # ----- Dua kolom: Informasi Lomba | Detail pelaksanaan + Verifikasi penyelenggara -----
        columns = QGridLayout()
        columns.setHorizontalSpacing(36)
        columns.setVerticalSpacing(0)
        left = QVBoxLayout()
        left.setSpacing(6)
        right = QVBoxLayout()
        right.setSpacing(6)
        columns.addLayout(left, 0, 0, Qt.AlignmentFlag.AlignTop)
        columns.addLayout(right, 0, 1, Qt.AlignmentFlag.AlignTop)
        columns.setColumnStretch(0, 1)
        columns.setColumnStretch(1, 1)
        layout.addLayout(columns)

        # Kolom kiri
        left.addWidget(self.make_section("Informasi Lomba"))
        left.addWidget(self.make_field_label("Judul Lomba"))
        self.judul_input = QLineEdit()
        self.judul_input.setPlaceholderText("Contoh: Hackathon Kampus 2026")
        left.addWidget(self.judul_input)
        left.addWidget(self.make_field_label("Kategori"))
        self.kategori_input = QComboBox()
        self.kategori_input.addItems(data_store.KATEGORI_POSTINGAN)
        self.kategori_input.setPlaceholderText("Pilih kategori")
        left.addWidget(self.kategori_input)
        left.addWidget(self.make_field_label("Deskripsi"))
        self.deskripsi_input = QTextEdit()
        self.deskripsi_input.setFixedHeight(96)
        self.deskripsi_input.setPlaceholderText("Jelaskan lomba, peserta yang boleh ikut, dan ketentuan tim")
        left.addWidget(self.deskripsi_input)
        left.addWidget(self.make_field_label("Poster Lomba"))
        self.poster_field = FileField((".pdf",), config.MAX_POSTER_SIZE_MB,
                                      f"Format PDF • Maksimal {config.MAX_POSTER_SIZE_MB} MB")
        left.addWidget(self.poster_field)
        left.addStretch()

        # Kolom kanan
        right.addWidget(self.make_section("Detail pelaksanaan"))
        dates = QHBoxLayout()
        dates.setSpacing(12)
        self.tanggal_input = self.make_date_edit()
        self.tenggat_input = self.make_date_edit()
        for text, widget in (("Tanggal lomba", self.tanggal_input), ("Tenggat Lomba", self.tenggat_input)):
            column = QVBoxLayout()
            column.setSpacing(6)
            column.addWidget(self.make_field_label(text))
            column.addWidget(widget)
            dates.addLayout(column, 1)
        right.addLayout(dates)
        right.addWidget(self.make_field_label("Link Pendaftaran Resmi"))
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("https://...")
        right.addWidget(self.link_input)
        right.addSpacing(10)
        right.addWidget(self.make_section("Verifikasi penyelenggara"))
        right.addWidget(self.make_field_label("Kontak resmi penyelenggara"))
        self.kontak_input = QLineEdit()
        self.kontak_input.setPlaceholderText("Nomor telepon atau email penyelenggara")
        right.addWidget(self.kontak_input)
        right.addWidget(self.make_field_label("Dokumen Pendukung (opsional)"))
        self.dokumen_field = FileField(config.ATTACHMENT_EXTENSIONS, config.MAX_ATTACHMENT_SIZE_MB,
                                       "Surat tugas / bukti resmi • PDF, PNG, JPG • Maksimal "
                                       f"{config.MAX_ATTACHMENT_SIZE_MB} MB")
        right.addWidget(self.dokumen_field)
        right.addStretch()

        # ----- Pesan + tombol kirim -----
        self.message_label = helpers.make_message_label()
        layout.addWidget(self.message_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedWidth(320)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(styles.POST_PROGRESS_STYLE)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.submit_button = QPushButton("Kirim untuk verifikasi")
        self.submit_button.setStyleSheet(styles.POST_BLUE_BUTTON_STYLE)
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_button.setMinimumWidth(320)
        layout.addWidget(self.submit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        # Signal & Slot
        self.back_button.clicked.connect(self.back_clicked)
        self.submit_button.clicked.connect(self.handle_submit)
        self.link_input.textEdited.connect(lambda: self.set_invalid(self.link_input, False))

    # ---------- Pembuat komponen kecil ----------
    def make_section(self, text):
        label = QLabel(text)
        label.setProperty("role", "section")
        return label

    def make_field_label(self, text):
        label = QLabel(text)
        label.setProperty("role", "field")
        return label

    def make_date_edit(self):
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setLocale(QLocale(QLocale.Language.Indonesian, QLocale.Country.Indonesia))
        edit.setDisplayFormat("d MMMM yyyy")
        edit.setDate(QDate.currentDate())
        return edit

    def set_invalid(self, widget, value):
        """Warnai kolom merah muda (field yang perlu diperbaiki)."""
        widget.setProperty("invalid", value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # ---------- Dibuka dari Dashboard ----------
    def show_new(self):
        self.mode = "baru"
        self.post_id = None
        self.link_awal = ""
        self.title_label.setText("Unggah info lomba")
        self.submit_button.setText("Kirim untuk verifikasi")
        self.judul_input.clear()
        self.kategori_input.setCurrentIndex(-1)
        self.deskripsi_input.clear()
        self.poster_field.clear()
        self.tanggal_input.setDate(QDate.currentDate())
        self.tenggat_input.setDate(QDate.currentDate())
        self.link_input.clear()
        self.kontak_input.clear()
        self.dokumen_field.clear()
        self.set_invalid(self.link_input, False)
        self.message_label.setText("")

    def show_revision(self, post_id):
        """Isi form dengan data postingan; kolom yang ditandai admin diwarnai merah muda."""
        post = data_store.get_postingan_by_id(post_id)
        self.mode = "revisi"
        self.post_id = post_id
        self.link_awal = post["link"]
        self.title_label.setText("Perbaiki Informasi Lomba")
        self.submit_button.setText("Kirim untuk verifikasi")
        self.judul_input.setText(post["judul"])
        self.kategori_input.setCurrentText(post["kategori"])
        self.deskripsi_input.setPlainText(post["deskripsi"])
        self.poster_field.set_existing(post["poster"])
        self.tanggal_input.setDate(QDate(post["tanggal_lomba"].year, post["tanggal_lomba"].month,
                                         post["tanggal_lomba"].day))
        self.tenggat_input.setDate(QDate(post["tenggat_lomba"].year, post["tenggat_lomba"].month,
                                         post["tenggat_lomba"].day))
        self.link_input.setText(post["link"])
        self.kontak_input.setText(post["kontak"])
        self.dokumen_field.set_existing(post["dokumen"])
        self.set_invalid(self.link_input, post["bagian_diperbaiki"] == "link")
        self.message_label.setText("")

    # ---------- Listener ----------
    def handle_submit(self):
        judul = self.judul_input.text().strip()
        kategori = self.kategori_input.currentText().strip()
        deskripsi = self.deskripsi_input.toPlainText().strip()
        link = self.link_input.text().strip()
        kontak = self.kontak_input.text().strip()

        if not (judul and kategori and deskripsi and link and kontak and self.poster_field.has_file()):
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        if not link.lower().startswith(("http://", "https://")):
            helpers.show_error(self.message_label, "Link pendaftaran harus diawali http:// atau https://")
            return
        if self.mode == "revisi" and link == self.link_awal and self.link_input.property("invalid"):
            helpers.show_error(self.message_label,
                               "Link pendaftaran belum diperbaiki. Mohon ubah sesuai catatan admin.")
            return

        # Berkas disalin oleh WORKER di thread lain, jadi jendela tetap bisa digerakkan / tidak "not responding"
        # walau berkasnya besar atau disimpan di disk yang lambat (flashdisk, drive jaringan, iCloud).
        nama_poster, tugas_poster = self.rencanakan_salin(self.poster_field)
        nama_dokumen, tugas_dokumen = self.rencanakan_salin(self.dokumen_field)
        data = {
            "judul": judul, "kategori": kategori, "deskripsi": deskripsi,
            "tanggal_lomba": self.tanggal_input.date().toPython(),
            "tenggat_lomba": self.tenggat_input.date().toPython(),
            "link": link, "kontak": kontak,
            "poster": nama_poster, "dokumen": nama_dokumen,
        }
        daftar = [tugas for tugas in (tugas_poster, tugas_dokumen) if tugas]
        if not daftar:                      # tidak ada berkas baru (mis. perbaikan tanpa ganti poster)
            self.selesaikan(data)
            return
        token = object()
        self.token_kirim = token
        self.set_mengirim(True)
        self.worker = workers.jalankan(
            salin_berkas, daftar,
            saat_progres=self.progress_bar.setValue,
            saat_selesai=lambda _hasil: self.selesaikan(data) if token is self.token_kirim else None,
            saat_galat=lambda pesan: self.gagal_kirim(pesan) if token is self.token_kirim else None)

    def rencanakan_salin(self, field):
        """Tentukan nama berkas tujuan (tanpa menyalin). Mengembalikan (nama, (sumber, tujuan) atau None)."""
        if not field.path:
            return field.existing, None
        nama_baru = f"{int(time.time())}_{os.path.basename(field.path)}"
        tujuan = os.path.join(config.ASSETS_DIR, "postingan", nama_baru)
        return nama_baru, (field.path, tujuan)

    def set_mengirim(self, sibuk):
        """Atur tampilan 'sedang mengirim': tombol dikunci supaya tidak terkirim dobel."""
        self.sedang_mengirim = sibuk
        self.submit_button.setEnabled(not sibuk)
        self.back_button.setEnabled(not sibuk)
        self.submit_button.setText("Mengirim..." if sibuk else "Kirim untuk verifikasi")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(sibuk)
        if sibuk:
            self.message_label.setText("")

    def selesaikan(self, data):
        """Dipanggil di THREAD UI setelah semua berkas tersalin. Data bersama (data_store) hanya diubah di sini."""
        self.set_mengirim(False)
        if self.mode == "revisi":
            post = data_store.kirim_ulang_postingan(self.post_id, data)
        else:
            user = data_store.current_user
            data["penyelenggara"] = user["universitas"] if user and user.get("universitas") else "Penyelenggara"
            post = data_store.tambah_postingan(data)
        self.message_label.setText("")
        self.submitted.emit(post["id"], self.mode)

    def gagal_kirim(self, pesan):
        self.set_mengirim(False)
        if pesan != "dibatalkan":
            helpers.show_error(self.message_label, f"Gagal menyimpan berkas ({pesan}). Silakan coba lagi.")

    # Widget Lifecycle: meninggalkan halaman saat pengiriman jalan -> batalkan worker, buang hasilnya
    def on_hide(self):
        if self.sedang_mengirim:
            self.token_kirim = None         # hasil yang menyusul akan diabaikan
            if self.worker is not None:
                self.worker.batalkan()      # hanya worker milik form ini, bukan worker lain (mis. preload)
            self.set_mengirim(False)
