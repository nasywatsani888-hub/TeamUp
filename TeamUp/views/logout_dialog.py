# views/logout_dialog.py — dialog "Yakin mau keluar?"
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
import config
import icons
import styles
from views.help_page import add_shadow
import sizes


class LogoutDialog(QDialog):
    """exec() == Accepted -> 'Ya, keluar'; Rejected -> 'Batal' (atau tombol Esc)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(sizes.LOGOUT_DIALOG_WIDTH, sizes.LOGOUT_DIALOG_HEIGHT)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)   # ruang untuk bayangan
        card = QFrame()
        card.setObjectName("ModalCard")
        card.setStyleSheet(styles.MODAL_CARD_STYLE)
        add_shadow(card)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 22, 30, 24)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setFixedSize(sizes.LOGOUT_ICON_SIZE, sizes.LOGOUT_ICON_SIZE)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(styles.LOGOUT_ICON_STYLE)
        icon_label.setPixmap(icons.make_icon("log-out", "#E5716F", 26).pixmap(26, 26))
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)

        title = QLabel("Yakin mau keluar?")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {config.COLOR_NAVY};")
        message = QLabel("Kamu perlu masuk lagi untuk mengakses akun TeamUp")
        message.setStyleSheet("font-size: 12px;")
        message.setWordWrap(True)
        for label in (title, message):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        layout.addSpacing(10)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.cancel_button = QPushButton("Batal")
        self.cancel_button.setStyleSheet(styles.LOGOUT_CANCEL_STYLE)
        self.confirm_button = QPushButton("Ya, keluar")
        self.confirm_button.setStyleSheet(styles.LOGOUT_CONFIRM_STYLE)
        for button in (self.cancel_button, self.confirm_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        # Signal & Slot bawaan QDialog: accept() / reject()
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)

    def showEvent(self, event):
        super().showEvent(event)
        # Tengahkan di atas jendela induk
        if self.parentWidget() is not None:
            center = self.parentWidget().mapToGlobal(self.parentWidget().rect().center())
            self.move(center - self.rect().center())
