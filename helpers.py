# helpers.py — komponen kecil yang dipakai berulang
import os
from PySide6.QtCore import Qt, QPointF, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
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


def make_image(filename, width, fallback_text="", fallback_size=None):
    """Gambar dari folder assets. Kalau file belum ada, tampilkan teks/emoji pengganti."""
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = os.path.join(config.ASSETS_DIR, filename)
    if os.path.exists(path):
        pixmap = QPixmap(path).scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pixmap)
    else:
        label.setText(fallback_text)
        label.setStyleSheet(f"font-size: {fallback_size or width // 2}px;")
    return label


def make_logo(width=420, name_size=60, tagline_size=14):
    """Logo TeamUp: pakai assets/logo.png kalau ada, kalau tidak pakai teks."""
    if os.path.exists(os.path.join(config.ASSETS_DIR, "logo.png")):
        return make_image("logo.png", width)
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    name = QLabel(
        f'<span style="color:{config.COLOR_LOGO_DARK}">Team</span>'
        f'<span style="color:{config.COLOR_LOGO_LIGHT}">Up</span>')
    name.setStyleSheet(f"font-size: {name_size}px; font-weight: bold;")
    tagline = QLabel("FIND YOUR PEOPLE, BUILD YOUR TEAM")
    tagline.setStyleSheet(f"font-size: {tagline_size}px; font-weight: bold; color: {config.COLOR_NAVY};")
    layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(tagline, alignment=Qt.AlignmentFlag.AlignCenter)
    return box


def clear_layout(layout):
    """Hapus semua widget di dalam sebuah layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


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
        source = QPixmap(path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
        round_pixmap = QPixmap(size, size)
        round_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(round_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(0, 0, size, size)
        painter.setClipPath(clip)
        painter.drawPixmap((size - source.width()) // 2, (size - source.height()) // 2, source)
        painter.end()
        label.setPixmap(round_pixmap)
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
        source = QPixmap(path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(0, 0, size, size, radius, radius)
        painter.setClipPath(clip)
        painter.drawPixmap((size - source.width()) // 2, (size - source.height()) // 2, source)
        painter.end()
        label.setPixmap(rounded)
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
