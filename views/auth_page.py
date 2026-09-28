# views/auth_page.py — kerangka halaman Login/Daftar/Reset: kiri logo, kanan form
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel,
                               QPushButton, QScrollArea)
from views.base_page import BasePage
import config
import styles
import helpers


class AuthPage(BasePage):
    go_login = Signal()      # tab "Masuk" ditekan
    go_register = Signal()   # tab "Daftar" ditekan

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        split = QHBoxLayout()
        split.setSpacing(0)
        self.main_layout.addLayout(split)

        # Panel kiri: logo
        left = QFrame()
        left.setObjectName("LeftPanel")
        left.setStyleSheet(styles.LEFT_PANEL_STYLE)
        left_layout = QVBoxLayout(left)
        left_layout.addStretch()
        left_layout.addWidget(self.make_logo(), alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        # Panel kanan: form di dalam area scroll (supaya tetap muat di jendela kecil)
        right = QFrame()
        right.setObjectName("RightPanel")
        right.setStyleSheet(styles.RIGHT_PANEL_STYLE)
        self.right_layout = QVBoxLayout(right)
        self.right_layout.setContentsMargins(0, 0, 20, 16)
        self.right_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)

        form = QWidget()
        form.setMaximumWidth(600)
        self.form_layout = QVBoxLayout(form)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(8)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(form, 5)
        row.addStretch(1)
        content_layout.addStretch()
        content_layout.addLayout(row)
        content_layout.addStretch()

        scroll.setWidget(content)
        self.right_layout.addWidget(scroll, 1)

        split.addWidget(left, 1)
        split.addWidget(right, 1)

    def make_logo(self):
        return helpers.make_logo()

    # --- Potongan yang dipakai ulang oleh halaman turunan ---
    def add_title(self, title, subtitle="", title_size=None, subtitle_size=None):
        title_label = helpers.make_title(title)
        if title_size:
            title_label.setStyleSheet(f"font-size: {title_size}px; font-weight: bold; color: {config.COLOR_NAVY};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.form_layout.addWidget(title_label)
        if subtitle:
            sub_label = helpers.make_subtitle(subtitle)
            if subtitle_size:
                sub_label.setStyleSheet(f"font-size: {subtitle_size}px; color: {config.COLOR_SUBTEXT};")
            sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.form_layout.addWidget(sub_label)

    def add_tabs(self, active, frame_size=None, pill_size=None):
        """Tab Masuk | Daftar. active = 'login' atau 'register'.
        frame_size/pill_size (lebar, tinggi) opsional untuk ukuran presisi sesuai desain."""
        box = QFrame()
        box.setObjectName("Tabs")
        if frame_size and pill_size:
            box.setFixedSize(*frame_size)
            box.setStyleSheet(styles.TABS_STYLE.replace("padding: 10px 34px;", "padding: 0;"))
        else:
            box.setStyleSheet(styles.TABS_STYLE)
        row = QHBoxLayout(box)
        if frame_size and pill_size:
            margin_v = max((frame_size[1] - pill_size[1]) // 2, 0)
            side_margin = 4
            spacing = max(frame_size[0] - 2 * pill_size[0] - 2 * side_margin, 0)
            row.setContentsMargins(side_margin, margin_v, side_margin, margin_v)
            row.setSpacing(spacing)
        else:
            row.setContentsMargins(4, 4, 4, 4)
            row.setSpacing(0)

        login_tab = QPushButton("Masuk")
        register_tab = QPushButton("Daftar")
        login_tab.setProperty("active", active == "login")
        register_tab.setProperty("active", active == "register")
        if pill_size:
            login_tab.setFixedSize(*pill_size)
            register_tab.setFixedSize(*pill_size)
        for tab in (login_tab, register_tab):
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(tab)

        login_tab.clicked.connect(lambda: self.go_login.emit())
        register_tab.clicked.connect(lambda: self.go_register.emit())
        self.form_layout.addSpacing(10)
        self.form_layout.addWidget(box, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.form_layout.addSpacing(14)

    def add_field(self, label_text, widget, label_size=None, field_size=None):
        """field_size (lebar, tinggi) opsional: label & widget dibungkus satu kolom
        selebar itu supaya keduanya rata kiri sejajar, sesuai ukuran di desain."""
        if field_size:
            group = QWidget()
            group.setFixedWidth(field_size[0])
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(6)
            group_layout.addWidget(helpers.make_label(label_text, label_size))
            widget.setFixedSize(*field_size)
            group_layout.addWidget(widget)
            self.form_layout.addWidget(group, alignment=Qt.AlignmentFlag.AlignHCenter)
        else:
            self.form_layout.addWidget(helpers.make_label(label_text, label_size))
            self.form_layout.addWidget(widget)
        self.form_layout.addSpacing(12)
