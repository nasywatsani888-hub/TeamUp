# views/filter_bar.py — baris dropdown "Kategori" + "Urutkan" beserta popup-nya
# Dipakai di halaman Rekan Tim (biru) dan Lomba (kuning).
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
import styles
import sizes


class FilterPopup(QFrame):
    """Kotak pilihan yang muncul di bawah tombol dropdown.
    single=True  -> hanya boleh satu pilihan (Urutkan)
    single=False -> boleh banyak pilihan (Kategori)"""
    applied = Signal(list)   # daftar teks pilihan yang dicentang
    closed = Signal()        # popup tertutup (untuk mengembalikan panah dropdown)

    def __init__(self, title, options, single=False, accent="blue"):
        super().__init__()
        # Qt.Popup: otomatis tertutup kalau user klik di luar kotak
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(sizes.FILTER_POPUP_WIDTH, sizes.FILTER_POPUP_HEIGHT)
        self.single = single

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        box = QFrame()
        box.setObjectName("PopupBox")
        box.setStyleSheet(styles.popup_style(accent))
        outer.addWidget(box)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("PopupTitle")
        layout.addWidget(title_label)

        self.checkboxes = []
        for text in options:
            checkbox = QCheckBox(text)
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            # Signal & Slot: setiap kotak dicentang -> cek aturan "hanya satu"
            checkbox.toggled.connect(lambda checked, cb=checkbox: self.handle_toggled(cb, checked))
            self.checkboxes.append(checkbox)
            layout.addWidget(checkbox)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet(styles.popup_reset_style(accent))
        self.apply_button = QPushButton("Terapkan")
        self.apply_button.setStyleSheet(styles.popup_apply_style(accent))
        for button in (self.reset_button, self.apply_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button, 1)
        layout.addLayout(buttons)

        self.reset_button.clicked.connect(self.handle_reset)
        self.apply_button.clicked.connect(self.handle_apply)

    def handle_toggled(self, checkbox, checked):
        if self.single and checked:
            for other in self.checkboxes:
                if other is not checkbox:
                    other.setChecked(False)

    def selected(self):
        return [checkbox.text() for checkbox in self.checkboxes if checkbox.isChecked()]

    def set_selected(self, selected):
        for checkbox in self.checkboxes:
            checkbox.setChecked(checkbox.text() in selected)

    def handle_apply(self):
        self.applied.emit(self.selected())
        self.close()

    def handle_reset(self):
        self.set_selected([])
        self.applied.emit([])   # kosong = semua kategori / urutan awal
        self.close()

    def hideEvent(self, event):
        self.closed.emit()
        super().hideEvent(event)


class FilterBar(QWidget):
    """Dua tombol dropdown (rata kanan). Halaman induk cukup mendengarkan signal changed,
    lalu membaca selected_categories dan selected_order."""
    changed = Signal()

    def __init__(self, category_options, sort_options, default_order, accent="blue"):
        super().__init__()
        self.default_order = default_order
        self.selected_categories = []
        self.selected_order = default_order

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addStretch()
        self.category_button = QPushButton()
        self.sort_button = QPushButton()
        for button in (self.category_button, self.sort_button):
            button.setStyleSheet(styles.DROPDOWN_BUTTON_STYLE)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumWidth(sizes.FILTER_BUTTON_MIN_WIDTH)
            row.addWidget(button)

        # Popup dibuat SATU kali; hanya ditampilkan/disembunyikan
        self.category_popup = FilterPopup("Pilih kategori", category_options, accent=accent)
        self.sort_popup = FilterPopup("Urutkan", sort_options, single=True, accent=accent)

        # Signal & Slot
        self.category_button.clicked.connect(
            lambda: self.open_popup(self.category_popup, self.category_button, self.selected_categories))
        self.sort_button.clicked.connect(
            lambda: self.open_popup(self.sort_popup, self.sort_button, [self.selected_order]))
        self.category_popup.applied.connect(self.handle_category_applied)
        self.sort_popup.applied.connect(self.handle_sort_applied)
        self.category_popup.closed.connect(self.update_button_labels)
        self.sort_popup.closed.connect(self.update_button_labels)

        self.update_button_labels()

    # ---------- Listener (slot) ----------
    def open_popup(self, popup, button, selected):
        popup.set_selected(selected)
        # Rata kanan dengan tombol, tepat di bawahnya
        popup.move(button.mapToGlobal(QPoint(button.width() - popup.width(), button.height() + 6)))
        popup.show()
        self.update_button_labels(opened=button)

    def handle_category_applied(self, selected):
        self.selected_categories = selected
        self.update_button_labels()
        self.changed.emit()

    def handle_sort_applied(self, selected):
        self.selected_order = selected[0] if selected else self.default_order
        self.update_button_labels()
        self.changed.emit()

    # ---------- Tampilan ----------
    def update_button_labels(self, opened=None):
        """Panah ▲ untuk dropdown yang sedang terbuka, ▼ untuk yang tertutup."""
        category_text = "Kategori"
        if self.selected_categories:
            category_text += f" ({len(self.selected_categories)})"
        arrow = "▲" if opened is self.category_button else "▼"
        self.category_button.setText(f"{category_text}   {arrow}")
        self.category_button.setProperty("selected", len(self.selected_categories) > 0)

        arrow = "▲" if opened is self.sort_button else "▼"
        self.sort_button.setText(f"Urutkan: {self.selected_order}   {arrow}")
        self.sort_button.setProperty("selected", self.selected_order != self.default_order)

        for button in (self.category_button, self.sort_button):   # terapkan ulang style property
            button.style().unpolish(button)
            button.style().polish(button)

    def close_popups(self):
        self.category_popup.close()
        self.sort_popup.close()
