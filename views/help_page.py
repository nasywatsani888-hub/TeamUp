# views/help_page.py — Pusat Bantuan (kartu "Hubungi Kami")
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout)
from PySide6.QtGui import QColor
from views.base_page import BasePage
import config
import helpers
import icons
import styles
import sizes


def add_shadow(widget):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 70))
    widget.setGraphicsEffect(shadow)


class HelpPage(BasePage):
    cancel_clicked = Signal()   # tombol Batal -> DashboardPage kembali ke Beranda

    def __init__(self):
        super().__init__()
        self.main_layout.addWidget(helpers.make_title("Pusat Bantuan"))

        card = QFrame()
        card.setObjectName("ModalCard")
        card.setStyleSheet(styles.MODAL_CARD_STYLE)
        card.setFixedWidth(sizes.HELP_CARD_WIDTH)
        add_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 20)
        layout.setSpacing(6)

        self.cancel_button = QPushButton("Batal")
        self.cancel_button.setStyleSheet(styles.CANCEL_SMALL_STYLE)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignLeft)

        icon_label = QLabel()
        icon_label.setFixedSize(sizes.HELP_ICON_SIZE, sizes.HELP_ICON_SIZE)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(styles.HELP_ICON_STYLE)
        icon_label.setPixmap(icons.make_icon("phone", config.COLOR_NAVY, 26).pixmap(26, 26))
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)

        title = QLabel("Hubungi Kami")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: black;")
        subtitle = QLabel("TeamUp siap bantu")
        subtitle.setStyleSheet("font-size: 12px;")
        number = QLabel(config.HELP_PHONE)
        number.setStyleSheet(styles.HELP_NUMBER_STYLE)
        hours = QLabel(config.HELP_HOURS)
        hours.setStyleSheet("font-size: 10px;")
        for label in (title, subtitle, number, hours):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        self.call_button = QPushButton("  Telepon Sekarang")
        self.call_button.setIcon(icons.make_icon("phone", "white", 16))
        self.call_button.setIconSize(QSize(16, 16))
        self.call_button.setStyleSheet(styles.CALL_BUTTON_STYLE)
        self.call_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addSpacing(6)
        layout.addWidget(self.call_button)

        self.main_layout.addStretch(1)
        self.main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addStretch(2)

        # Signal & Slot
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.call_button.clicked.connect(self.handle_call)

    def handle_call(self):
        # Aplikasi desktop tidak bisa menelepon langsung: salin nomor ke clipboard
        QApplication.clipboard().setText(config.HELP_PHONE)
        QMessageBox.information(self, "Hubungi Kami",
                                f"Nomor {config.HELP_PHONE} sudah disalin.\nSilakan hubungi lewat ponselmu.")
