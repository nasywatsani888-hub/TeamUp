# helpers.py — komponen kecil yang dipakai berulang
import hashlib
import os
import tempfile
import threading
from functools import lru_cache
from PySide6.QtCore import Qt, QPointF, QSize, QUrl
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QLineEdit, QFrame, QHBoxLayout, QVBoxLayout, QWidget
import config
import styles


def make_title(text):
    label = QLabel(text)
    label.setStyleSheet(styles.TITLE_STYLE)
    label.setWordWrap(True)
    return label


def make_subtitle(text):
    label = QLabel(text)
    label.setStyleSheet(styles.SUBTITLE_STYLE)
    label.setWordWrap(True)
    return label


def make_label(text, size=None):
    label = QLabel(text)
    if size:
        label.setStyleSheet(f"font-size: {size}px; font-weight: bold; color: {config.COLOR_NAVY};")
    else:
        label.setStyleSheet(styles.LABEL_STYLE)
    return label


def make_primary_button(text):
    button = QPushButton(text)
    button.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_link_button(text, size=16, bold=True):
    button = QPushButton(text)
    button.setStyleSheet(styles.link_button_style(size, bold))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_outline_button(text):
    button = QPushButton(text)
    button.setStyleSheet(styles.OUTLINE_BUTTON_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_message_label():
    """Label kosong untuk pesan error/berhasil di bawah form."""
    label = QLabel("")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def show_error(label, text):
    label.setStyleSheet(styles.ERROR_STYLE)
    label.setText(text)


def show_success(label, text):
    label.setStyleSheet(styles.SUCCESS_STYLE)
    label.setText(text)


def is_valid_password(password):
    """Minimal 8 karakter, mengandung huruf dan angka."""
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return len(password) >= 8 and has_letter and has_digit


# ---------- Cache gambar (optimasi RAM & CPU) ----------
# QPixmap berbagi data secara implisit (copy-on-write), jadi satu pixmap boleh dipasang ke banyak
# QLabel tanpa menggandakan memori. lru_cache(maxsize=...) membatasi jumlahnya: kalau penuh,
# yang paling lama tidak dipakai dibuang -> cache tidak tumbuh tanpa batas.
# 'mtime' (waktu ubah file) ikut jadi kunci, jadi kalau foto diganti otomatis dimuat ulang.
@lru_cache(maxsize=64)
def _pixmap_lebar(path, width, mtime):
    return QPixmap(path).scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)


# ---------- Memuat gambar dua tahap (Pertemuan 7: Concurrency) ----------
# Tahap BERAT (baca file + decode + skala + potong sudut) hanya memakai QImage, yang AMAN dipakai
# di thread mana pun -> bisa dikerjakan worker di latar belakang. QPixmap TIDAK boleh dibuat di luar
# thread UI, jadi tahap RINGAN (QImage -> QPixmap) dilakukan di thread UI.
# Hasil worker "diparkir" di _gambar_siap; saat widget memintanya, thread UI tinggal mengambil.
_gambar_siap = {}          # kunci -> QImage hasil worker
_kunci_dipakai = set()     # kunci yang sudah pernah diminta thread UI (worker tidak perlu mengerjakannya lagi)
_kunci_kunci = threading.Lock()   # dua thread menyentuh dua struktur di atas -> harus dikunci


def render_kotak(path, lebar, tinggi, radius, bulat_bawah, skala):
    """Gambar dipotong (cover-crop) pas ke lebar x tinggi dengan sudut membulat -> QImage.
    bulat_bawah=False: hanya sudut atas yang bulat. Aman dipanggil dari thread mana pun."""
    w, h, r = lebar * skala, tinggi * skala, radius * skala
    sumber = QImage(path).scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation)
    hasil = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    hasil.fill(Qt.GlobalColor.transparent)
    painter = QPainter(hasil)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    # Kalau sudut bawah tidak dibulatkan, kotak bulatnya dibuat lebih tinggi dan "tumpah" ke luar gambar
    clip.addRoundedRect(0, 0, w, h if bulat_bawah else h + r, r, r)
    painter.setClipPath(clip)
    painter.drawImage((w - sumber.width()) // 2, (h - sumber.height()) // 2, sumber)
    painter.end()
    return hasil


def simpan_siap(kunci, gambar):
    """Dipanggil WORKER: parkir hasil render, kecuali thread UI sudah membuatnya sendiri."""
    with _kunci_kunci:
        if kunci not in _kunci_dipakai:
            _gambar_siap[kunci] = gambar


def sudah_dipakai(kunci):
    with _kunci_kunci:
        return kunci in _kunci_dipakai


def _bangun_pixmap(path, lebar, tinggi, radius, bulat_bawah, skala, mtime):
    """Dipanggil THREAD UI. Pakai hasil worker kalau sudah ada; kalau belum, render sendiri (cara lama)."""
    kunci = (path, lebar, tinggi, radius, bulat_bawah, skala, mtime)
    with _kunci_kunci:
        _kunci_dipakai.add(kunci)
        gambar = _gambar_siap.pop(kunci, None)    # pop = ambil sekaligus kosongkan (hemat RAM)
    if gambar is None:
        gambar = render_kotak(path, lebar, tinggi, radius, bulat_bawah, skala)
    hasil = QPixmap.fromImage(gambar)
    hasil.setDevicePixelRatio(skala)
    return hasil


@lru_cache(maxsize=64)
def _pixmap_foto(path, size, radius, mtime):
    """Foto persegi dipotong bertepi membulat; radius = size // 2 menghasilkan lingkaran."""
    return _bangun_pixmap(path, size, size, radius, True, 1, mtime)


@lru_cache(maxsize=32)
def _pixmap_poster(path, width, height, radius, bulat_bawah, mtime):
    """Poster dipotong pas ke width x height. Dirender 2x supaya tajam di layar Retina."""
    return _bangun_pixmap(path, width, height, radius, bulat_bawah, 2, mtime)


EKSTENSI_POSTER = (".png", ".jpg", ".jpeg", ".webp")


@lru_cache(maxsize=2)
def _isi_folder_poster(folder, mtime_folder):
    """Daftar gambar di folder poster: {nama tanpa ekstensi (huruf kecil): path}.
    'mtime_folder' (waktu ubah folder) ikut jadi kunci cache, jadi kalau ada file ditambah / dihapus /
    diganti nama, daftar otomatis dibaca ulang. Tanpa cache, folder dibaca setiap kartu dibuat."""
    ada = {}
    for nama_file in sorted(os.listdir(folder)):
        nama, ekstensi = os.path.splitext(nama_file)
        if ekstensi.lower() in EKSTENSI_POSTER:
            ada.setdefault(nama.lower(), os.path.join(folder, nama_file))
    return ada


def cari_gambar_poster(daftar_nama):
    """Path gambar di assets/poster/ dari daftar nama file TANPA ekstensi, atau '' kalau tidak ada.
    Pencarian tidak peduli huruf besar/kecil ("Essay.JPG" = "essay.jpg"), boleh ada spasi di nama,
    dan menerima ekstensi png / jpg / jpeg / webp."""
    folder = os.path.join(config.ASSETS_DIR, "poster")
    if not os.path.isdir(folder):
        return ""
    ada = _isi_folder_poster(folder, os.path.getmtime(folder))
    for nama in daftar_nama:
        if nama.lower() in ada:
            return ada[nama.lower()]
    return ""


def poster_file(lomba):
    """Path gambar poster sebuah lomba (lomba["poster"] = daftar nama), atau ''."""
    return cari_gambar_poster(lomba.get("poster", []))


def make_thumbnail(post, size, radius):
    """Kotak kecil bergambar untuk baris Postingan Saya (post["gambar"] = daftar nama file di
    assets/poster/). None kalau gambarnya belum ada -> pemanggil memakai kotak polos."""
    path = cari_gambar_poster(post.get("gambar", []))
    if not path:
        return None
    label = QLabel()
    label.setFixedSize(size, size)
    label.setPixmap(_pixmap_poster(path, size, size, radius, True, os.path.getmtime(path)))
    return label


def make_poster(lomba, width, height, radius, bulat_bawah=False):
    """QLabel berisi poster; None kalau gambarnya belum ada (pemanggil memakai blok warna)."""
    path = poster_file(lomba)
    if not path:
        return None
    label = QLabel()
    label.setFixedSize(width, height)
    label.setPixmap(_pixmap_poster(path, width, height, radius, bulat_bawah, os.path.getmtime(path)))
    return label


def lokasi_png_qml(path, mtime, width, height, radius):
    """Lokasi berkas PNG sementara yang dibaca QML (poster sudah dipotong & dibulatkan)."""
    kunci = hashlib.md5(f"{path}|{mtime}|{width}x{height}|{radius}".encode()).hexdigest()[:16]
    folder = os.path.join(tempfile.gettempdir(), "teamup_poster_cache")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{kunci}.png")


def simpan_png_atomik(gambar, tujuan):
    """Tulis ke berkas sementara lalu 'rename' -> pembaca tidak pernah melihat berkas setengah jadi
    (penting karena worker menulis sementara QML bisa membacanya)."""
    sementara = f"{tujuan}.{threading.get_ident()}.tmp"
    gambar.save(sementara, "PNG")
    os.replace(sementara, tujuan)


@lru_cache(maxsize=32)
def _url_poster(path, mtime, width, height, radius):
    """Render poster ke folder sementara SEKALI per (file, ukuran), lalu ingat lokasinya."""
    hasil = lokasi_png_qml(path, mtime, width, height, radius)
    if not os.path.exists(hasil):
        simpan_png_atomik(_pixmap_poster(path, width, height, radius, False, mtime).toImage(), hasil)
    return hasil


def poster_url(lomba, width, height, radius):
    """Untuk QML: poster yang sudah dipotong & dibulatkan disimpan ke folder sementara; kembalikan URL-nya.
    QML tidak bisa memotong sudut gambar dengan mudah, jadi dikerjakan di Python."""
    path = poster_file(lomba)
    if not path:
        return ""
    hasil = _url_poster(path, os.path.getmtime(path), width, height, radius)
    if not os.path.exists(hasil):          # folder sementara dibersihkan sistem -> render ulang
        _url_poster.cache_clear()
        hasil = _url_poster(path, os.path.getmtime(path), width, height, radius)
    return QUrl.fromLocalFile(hasil).toString()


def clear_image_cache():
    """Kosongkan cache gambar (manual), mis. setelah logout atau saat RAM ingin dilepas."""
    _pixmap_lebar.cache_clear()
    _pixmap_foto.cache_clear()
    _pixmap_poster.cache_clear()
    _url_poster.cache_clear()
    _isi_folder_poster.cache_clear()
    with _kunci_kunci:
        _gambar_siap.clear()
        _kunci_dipakai.clear()


def make_image(filename, width, fallback_text="", fallback_size=None):
    """Gambar dari folder assets. Kalau file belum ada, tampilkan teks/emoji pengganti."""
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = os.path.join(config.ASSETS_DIR, filename)
    if os.path.exists(path):
        label.setPixmap(_pixmap_lebar(path, width, os.path.getmtime(path)))
    else:
        label.setText(fallback_text)
        label.setStyleSheet(f"font-size: {fallback_size or width // 2}px;")
    return label


def make_logo(width=420, name_size=60, tagline_size=14):
    """Logo TeamUp = gambar ikon (assets/logo.png: huruf T + burung) di kiri,
    lalu tulisan "TeamUp" dan tagline yang diketik lewat kode di kanannya."""
    box = QWidget()
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(max(6, name_size // 5))

    if os.path.exists(os.path.join(config.ASSETS_DIR, "logo.png")):
        row.addWidget(make_image("logo.png", int(name_size * 1.7)))   # tinggi ikon ~ tinggi tulisan

    text_box = QWidget()
    text_layout = QVBoxLayout(text_box)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(0)
    name = QLabel(
        f'<span style="color:{config.COLOR_LOGO_DARK}">Team</span>'
        f'<span style="color:{config.COLOR_LOGO_LIGHT}">Up</span>')
    name.setStyleSheet(f"font-size: {name_size}px; font-weight: bold;")
    tagline = QLabel("FIND YOUR PEOPLE, BUILD YOUR TEAM")
    tagline.setStyleSheet(f"font-size: {tagline_size}px; font-weight: bold; color: {config.COLOR_NAVY};")
    text_layout.addWidget(name)
    text_layout.addWidget(tagline)
    row.addWidget(text_box)
    return box


def clear_layout(layout):
    """Kosongkan layout SEKARANG: widget disembunyikan, dilepas dari induknya, lalu dihapus
    (deleteLater). Layout bersarang (addLayout) ikut dibersihkan secara rekursif, karena kalau
    hanya widget langsung yang dihapus, widget di dalam sub-layout tertinggal dan menumpuk."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
            item.layout().deleteLater()


def format_sisa(days, use_weeks=False):
    if use_weeks and days >= 14:
        return f"{days // 7} minggu lagi"
    return f"{days} hari lagi"


def deadline_color(days):
    """Merah = mepet, oranye = sebentar lagi, hijau = masih lama."""
    if days <= 3:
        return "#E53935"
    if days <= 7:
        return "#F5A000"
    return "#2EB872"


def make_check_circle(size=170):
    """Lingkaran hijau dengan tanda centang (halaman berhasil)."""
    label = QLabel("✓")
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"background-color: {config.COLOR_SUCCESS}; color: white; "
        f"border-radius: {size // 2}px; font-size: {size // 2}px; font-weight: bold;"
    )
    return label


def make_eye_icon(slashed):
    """Gambar ikon mata (slashed=True -> mata dicoret / password tersembunyi)."""
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#7A8CA5")
    pen = QPen(color)
    pen.setWidthF(3.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    outline = QPainterPath()
    outline.moveTo(4, 24)
    outline.quadTo(24, 4, 44, 24)
    outline.quadTo(24, 44, 4, 24)
    painter.drawPath(outline)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(24, 24), 6, 6)
    if slashed:
        painter.drawLine(9, 41, 39, 7)
    painter.end()
    return QIcon(pixmap)


class PasswordField(QFrame):
    """Kolom password dengan tombol mata untuk lihat/sembunyikan."""

    def __init__(self, placeholder=""):
        super().__init__()
        self.setObjectName("PasswordField")
        self.setStyleSheet(styles.PASSWORD_FIELD_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setEchoMode(QLineEdit.EchoMode.Password)

        self.eye_button = QPushButton()
        self.eye_button.setCheckable(True)
        self.eye_button.setIcon(make_eye_icon(True))
        self.eye_button.setIconSize(QSize(24, 24))
        self.eye_button.setFixedSize(36, 36)
        self.eye_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self.input)
        layout.addWidget(self.eye_button)

        # Signal & Slot: tombol mata (toggled) -> ganti mode tampilan password
        self.eye_button.toggled.connect(self.toggle_visibility)

    def toggle_visibility(self, checked):
        if checked:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.eye_button.setIcon(make_eye_icon(not checked))

    def text(self):
        return self.input.text()

    def clear(self):
        self.input.clear()
        self.eye_button.setChecked(False)


def make_avatar(user, size):
    """Foto bulat user dari assets/foto/<nama file>. Kalau foto belum ada,
    tampilkan lingkaran dengan inisial nama (mis. 'Marques Hellim' -> 'MH')."""
    label = QLabel()
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    path = os.path.join(config.ASSETS_DIR, "foto", user.get("foto", ""))
    if user.get("foto") and os.path.exists(path):
        label.setPixmap(_pixmap_foto(path, size, size // 2, os.path.getmtime(path)))   # lingkaran
    else:
        words = user["nama"].split()
        initials = "".join(word[0] for word in words[:2]).upper()
        label.setText(initials)
        label.setStyleSheet(
            f"background-color: white; color: {config.COLOR_NAVY}; border: 3px solid #FFC71F; "
            f"border-radius: {size // 2}px; font-size: {size // 3}px; font-weight: bold;")
    return label


def make_photo_square(user, size, radius=16):
    """Foto user persegi bertepi membulat (halaman Profil Rekan). Kalau foto belum
    ada, tampilkan kotak dengan inisial nama."""
    label = QLabel()
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = os.path.join(config.ASSETS_DIR, "foto", user.get("foto", ""))
    if user.get("foto") and os.path.exists(path):
        label.setPixmap(_pixmap_foto(path, size, radius, os.path.getmtime(path)))   # persegi membulat
    else:
        words = user["nama"].split()
        label.setText("".join(word[0] for word in words[:2]).upper())
        label.setStyleSheet(
            f"background-color: #FFE08F; color: {config.COLOR_NAVY}; border-radius: {radius}px; "
            f"font-size: {size // 3}px; font-weight: bold;")
    return label


BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def format_tanggal(tanggal):
    """date -> '20 Oktober 2026'"""
    return f"{tanggal.day} {BULAN[tanggal.month - 1]} {tanggal.year}"


def format_waktu(menit):
    """Jumlah menit yang lalu -> '10 menit lalu' / '2 jam lalu' / '2 hari lalu'."""
    if menit < 60:
        return f"{menit} menit lalu"
    if menit < 24 * 60:
        return f"{menit // 60} jam lalu"
    return f"{menit // (24 * 60)} hari lalu"
