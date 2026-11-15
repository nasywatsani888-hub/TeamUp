# views/loading_button.py — Tombol interaktif dengan status loading (Pertemuan 12 UX)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QPushButton, QStyleOptionButton, QStyle


class LoadingButton(QPushButton):
    """
    Tombol khusus yang dapat menampilkan status loading (spinner animasi).
    Mencegah double-click / spam submit dari pengguna.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._is_loading = False
        self._original_text = text
        self._loading_text = "Memproses..."
        self._angle = 0

        # Timer untuk memutar spinner
        self._timer = QTimer(self)
        self._timer.setInterval(40)  # ~25 FPS animasi putaran halus
        self._timer.timeout.connect(self._rotate)

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def start_loading(self, text="Memproses..."):
        """Aktifkan status loading: tombol terkunci dan spinner berputar."""
        if self._is_loading:
            return
        self._is_loading = True
        self._original_text = self.text()
        self._loading_text = text
        self.setEnabled(False)
        self._angle = 0
        self._timer.start()
        self.update()

    def stop_loading(self):
        """Hentikan status loading: tombol kembali aktif ke kondisi normal."""
        if not self._is_loading:
            return
        self._timer.stop()
        self._is_loading = False
        self.setText(self._original_text)
        self.setEnabled(True)
        self.update()

    def is_loading(self):
        return self._is_loading

    def paintEvent(self, event):
        if not self._is_loading:
            super().paintEvent(event)
            return

        # Saat loading: gambar background dan border sesuai style Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ""  # Kosongkan teks bawaan agar tidak tertimpa
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, self)

        # Ukuran dan posisi elemen spinner dan teks
        w = self.width()
        h = self.height()
        spinner_size = min(20, max(12, int(h * 0.4)))
        spacing = 8

        # Font untuk teks loading
        font = self.font()
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(self._loading_text)
        text_h = fm.height()

        total_w = spinner_size + spacing + text_w
        start_x = (w - total_w) / 2
        spinner_y = (h - spinner_size) / 2

        # 1. Gambar Spinner berputar
        spinner_rect = QRectF(start_x, spinner_y, spinner_size, spinner_size)

        # Lingkaran rel latar belakang abu-abu transparan
        pen_bg = QPen(QColor(255, 255, 255, 70), 2.5)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawEllipse(spinner_rect)

        # Busur aktif berputar putih
        pen_arc = QPen(QColor(255, 255, 255, 240), 2.5)
        pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_arc)
        # drawArc memakai satuan 1/16 derajat
        painter.drawArc(spinner_rect, int(-self._angle * 16), int(100 * 16))

        # 2. Gambar Teks Loading
        text_x = int(start_x + spinner_size + spacing)
        text_y = int((h + text_h) / 2 - fm.descent())
        painter.setPen(QColor(255, 255, 255, 230))
        painter.drawText(text_x, text_y, self._loading_text)
