# views/upload_dialog.py — dialog "Tarik atau pilih file" (bisa dipakai ulang, mis. untuk poster lomba)
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout
import config
import helpers
import icons
import styles
import sizes


class DropZone(QFrame):
    """Kotak untuk menarik file (drag & drop) atau diklik untuk memilih file.
    Contoh event handling: dragEnterEvent, dragLeaveEvent, dropEvent, mousePressEvent."""
    file_chosen = Signal(str)   # path file yang dijatuhkan
    clicked = Signal()          # kotak diklik -> buka dialog pilih file

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setStyleSheet(styles.DROP_ZONE_STYLE)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel()
        icon_label.setPixmap(icons.make_icon("folder", config.COLOR_NAVY, 56).pixmap(56, 56))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label = QLabel("Tarik atau pilih file")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("font-size: 15px;")
        for label in (icon_label, self.text_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(label)

    def set_hover(self, value):
        self.setProperty("hover", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.set_hover(True)

    def dragLeaveEvent(self, event):
        self.set_hover(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.set_hover(False)
        urls = event.mimeData().urls()
        if urls:
            self.file_chosen.emit(urls[0].toLocalFile())

    def mousePressEvent(self, event):
        self.clicked.emit()


class UploadDialog(QDialog):
    def __init__(self, parent=None, title="Upload File",
                 extensions=config.ATTACHMENT_EXTENSIONS, max_mb=config.MAX_ATTACHMENT_SIZE_MB):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(sizes.UPLOAD_DIALOG_WIDTH, sizes.UPLOAD_DIALOG_HEIGHT)
        self.extensions = extensions
        self.max_mb = max_mb
        self.selected_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(10)

        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone, 1)

        formats = ", ".join(ext.lstrip(".").upper() for ext in extensions)
        layout.addWidget(helpers.make_subtitle(f"Format: {formats} • Maksimal {max_mb} MB"))
        self.message_label = helpers.make_message_label()
        layout.addWidget(self.message_label)

        self.upload_button = QPushButton("Upload")
        self.upload_button.setStyleSheet(styles.UPLOAD_BUTTON_STYLE)
        self.upload_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_button.setEnabled(False)   # aktif setelah ada file yang valid
        layout.addWidget(self.upload_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Signal & Slot
        self.drop_zone.clicked.connect(self.handle_browse)
        self.drop_zone.file_chosen.connect(self.handle_file_chosen)
        self.upload_button.clicked.connect(self.accept)

    def handle_browse(self):
        patterns = " ".join("*" + ext for ext in self.extensions)
        path, _ = QFileDialog.getOpenFileName(self, "Pilih File", "", f"File ({patterns})")
        if path:
            self.handle_file_chosen(path)

    def handle_file_chosen(self, path):
        self.selected_path = ""
        self.upload_button.setEnabled(False)
        if not os.path.isfile(path) or os.path.splitext(path)[1].lower() not in self.extensions:
            helpers.show_error(self.message_label, "Format file tidak didukung.")
            return
        if os.path.getsize(path) > self.max_mb * 1024 * 1024:
            helpers.show_error(self.message_label, f"Ukuran file maksimal {self.max_mb} MB.")
            return
        self.selected_path = path
        self.drop_zone.text_label.setText(os.path.basename(path))
        helpers.show_success(self.message_label, "File siap diunggah.")
        self.upload_button.setEnabled(True)
