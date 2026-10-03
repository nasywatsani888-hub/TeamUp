# views/post_dialogs.py — dialog di halaman Postingan: konfirmasi batalkan/hapus & "tidak bisa edit"
import html
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
import config
import icons
import sizes
import styles
from views.help_page import add_shadow


def make_card(dialog, width, height, card_style):
    """Kerangka dialog tanpa bingkai: kartu putih bergaya + bayangan. Mengembalikan layout isi kartu."""
    dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    dialog.setFixedSize(width, height)
    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(20, 20, 20, 20)   # ruang untuk bayangan
    card = QFrame()
    card.setObjectName("ModalCard")
    card.setStyleSheet(card_style)
    add_shadow(card)
    outer.addWidget(card)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(26, 18, 26, 22)
    layout.setSpacing(8)
    return layout


def make_corner_button(icon_name, color):
    button = QPushButton()
    button.setIcon(icons.make_icon(icon_name, color, 20))
    button.setIconSize(QSize(20, 20))
    button.setStyleSheet(styles.BACK_BUTTON_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def center_on_parent(dialog):
    if dialog.parentWidget() is not None:
        center = dialog.parentWidget().mapToGlobal(dialog.parentWidget().rect().center())
        dialog.move(center - dialog.rect().center())


class ConfirmDialog(QDialog):
    """Dialog konfirmasi. exec() == Accepted -> tombol konfirmasi; Rejected -> Kembali / X.
    tone='batalkan' (oranye-kuning) atau 'hapus' (merah).
    Objek ini DIPAKAI ULANG (object pooling): dibuat sekali per tone, lalu isinya diganti lewat
    set_content() -> tidak membangun belasan widget & koneksi baru setiap kali dialog dibuka."""

    TONES = {
        "batalkan": {"icon_bg": "#FBD9A8", "icon": "#E8892B", "box": styles.POST_BOX_YELLOW, "warn": "#E8892B"},
        "hapus": {"icon_bg": "#F4A3A3", "icon": "#D9534F", "box": styles.POST_BOX_RED, "warn": "#D9534F"},
    }

    def __init__(self, parent, tone="batalkan"):
        super().__init__(parent)
        colors = self.TONES[tone]
        layout = make_card(self, sizes.CONFIRM_DIALOG_WIDTH, sizes.CONFIRM_DIALOG_HEIGHT, styles.MODAL_CARD_STYLE)

        close_button = make_corner_button("x", config.COLOR_NAVY)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)

        icon_label = QLabel()
        icon_label.setFixedSize(52, 52)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"background-color: {colors['icon_bg']}; border-radius: 26px;")
        icon_label.setPixmap(icons.make_icon("trash", colors["icon"], 26).pixmap(26, 26))
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.title_label = QLabel()
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.message_label = QLabel()
        self.message_label.setTextFormat(Qt.TextFormat.RichText)
        self.message_label.setStyleSheet("font-size: 12px;")
        self.message_label.setWordWrap(True)
        for label in (self.title_label, self.message_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        layout.addSpacing(6)

        # Kotak peringatan: ikon segitiga + teks
        box = QFrame()
        box.setObjectName("PostBox")
        box.setStyleSheet(colors["box"])
        box_row = QHBoxLayout(box)
        box_row.setContentsMargins(12, 10, 12, 10)
        box_row.setSpacing(10)
        warn_icon = QLabel("⚠")
        warn_icon.setStyleSheet(f"font-size: 18px; color: {colors['warn']}; background: transparent;")
        self.warn_text = QLabel()
        self.warn_text.setWordWrap(True)
        self.warn_text.setStyleSheet("font-size: 11px; background: transparent;")
        box_row.addWidget(warn_icon, alignment=Qt.AlignmentFlag.AlignTop)
        box_row.addWidget(self.warn_text, 1)
        layout.addWidget(box)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.back_button = QPushButton("Kembali")
        self.back_button.setStyleSheet(styles.POST_OUTLINE_BUTTON_STYLE)
        self.confirm_button = QPushButton()
        self.confirm_button.setStyleSheet(styles.POST_BLUE_BUTTON_STYLE)
        for button in (self.back_button, self.confirm_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        # Signal & Slot bawaan QDialog (disambung SEKALI, karena dialog dipakai ulang)
        close_button.clicked.connect(self.reject)
        self.back_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)

    def set_content(self, title, pertanyaan_awal, judul_lomba, peringatan, confirm_text):
        self.title_label.setText(title)
        self.message_label.setText(f'{html.escape(pertanyaan_awal)} <b style="color:{config.COLOR_PRIMARY}">'
                                   f'{html.escape(judul_lomba)}</b>?')
        self.warn_text.setText(peringatan)
        self.confirm_button.setText(confirm_text)

    def showEvent(self, event):
        super().showEvent(event)
        center_on_parent(self)


class EditBlockedDialog(QDialog):
    """Pesan saat user menekan 'Edit postingan' padahal masih Ditangguhkan (belum diverifikasi admin)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        card_style = ("#ModalCard { background-color: #FFF1C9; border: 1px solid #F5C84B; border-radius: 10px; }")
        layout = make_card(self, sizes.EDIT_BLOCKED_DIALOG_WIDTH, sizes.EDIT_BLOCKED_DIALOG_HEIGHT, card_style)

        back_button = make_corner_button("arrow-left", config.COLOR_NAVY)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        message = QLabel("Anda tidak dapat mengakses <u>Edit Postingan</u> saat dalam proses verifikasi")
        message.setTextFormat(Qt.TextFormat.RichText)
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("font-size: 13px; background: transparent;")
        layout.addWidget(message)
        layout.addStretch()

        back_button.clicked.connect(self.accept)

    def showEvent(self, event):
        super().showEvent(event)
        center_on_parent(self)
