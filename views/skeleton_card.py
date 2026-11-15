# views/skeleton_card.py — Skeleton (shimmer/pulse) loading card components
# Digunakan saat memuat data rekan tim, lomba, atau navigasi halaman
import math
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame

import sizes


class BaseSkeletonCard(QFrame):
    """Kelas dasar kartu skeleton dengan efek shimmer/pulsing lembut."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(35)  # ~30 FPS
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._timer.isActive():
            self._timer.stop()

    def _on_tick(self):
        self._phase = (self._phase + 0.08) % (2 * math.pi)
        self.update()

    def _get_pulse_color(self) -> QColor:
        # Interpolasi sinusoidal halus antara #E2E8F0 (slate-200) dan #F1F5F9 (slate-100)
        factor = (math.sin(self._phase) + 1.0) / 2.0
        r = int(226 + (241 - 226) * factor)
        g = int(232 + (245 - 232) * factor)
        b = int(240 + (249 - 240) * factor)
        return QColor(r, g, b)


class SkeletonPartnerCard(BaseSkeletonCard):
    """Skeleton kartu calon rekan tim (ukuran dan siluet identik dengan PartnerCard)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SkeletonPartnerCard")
        self.setFixedSize(sizes.PARTNER_CARD_WIDTH, sizes.PARTNER_CARD_HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = 20.0

        # 1. Background kartu putih dengan border halus
        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)
        painter.fillPath(card_path, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1.0))
        painter.drawPath(card_path)

        # 2. Siluet elemen yang berdenyut (pulse)
        pulse_color = self._get_pulse_color()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pulse_color)

        # Avatar placeholder (lingkaran diameter 90px di tengah)
        avatar_size = 90.0
        avatar_x = (w - avatar_size) / 2.0
        avatar_y = 20.0
        painter.drawEllipse(QRectF(avatar_x, avatar_y, avatar_size, avatar_size))

        # Placeholder nama (lebar 130px, tinggi 16px)
        name_w = 130.0
        name_x = (w - name_w) / 2.0
        painter.drawRoundedRect(QRectF(name_x, 126.0, name_w, 16.0), 8.0, 8.0)

        # Placeholder kampus / prodi (lebar 100px, tinggi 12px)
        campus_w = 100.0
        campus_x = (w - campus_w) / 2.0
        painter.drawRoundedRect(QRectF(campus_x, 150.0, campus_w, 12.0), 6.0, 6.0)

        # Placeholder chip skill 1 & 2
        chip1_w = 100.0
        chip1_x = (w - chip1_w) / 2.0
        painter.drawRoundedRect(QRectF(chip1_x, 174.0, chip1_w, 22.0), 11.0, 11.0)

        chip2_w = 75.0
        chip2_x = (w - chip2_w) / 2.0
        painter.drawRoundedRect(QRectF(chip2_x, 204.0, chip2_w, 22.0), 11.0, 11.0)

        # Placeholder tombol "Kunjungi Profil" di bagian bawah
        btn_w = 140.0
        btn_x = (w - btn_w) / 2.0
        btn_y = h - 52.0
        painter.drawRoundedRect(QRectF(btn_x, btn_y, btn_w, 36.0), 10.0, 10.0)


class SkeletonLombaCard(BaseSkeletonCard):
    """Skeleton kartu lomba (ukuran dan siluet identik dengan LombaCard)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SkeletonLombaCard")
        self.setFixedWidth(sizes.LOMBA_CARD_WIDTH)
        self.setFixedHeight(360)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = 20.0

        # 1. Background kartu putih dengan border halus
        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)
        painter.fillPath(card_path, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1.0))
        painter.drawPath(card_path)

        # 2. Siluet elemen berdenyut (pulse)
        pulse_color = self._get_pulse_color()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pulse_color)

        # Placeholder poster (atas membulat radius 20px)
        poster_h = float(sizes.LOMBA_POSTER_HEIGHT)
        poster_path = QPainterPath()
        poster_path.moveTo(0.5, radius)
        poster_path.arcTo(QRectF(0.5, 0.5, radius * 2, radius * 2), 180, -90)
        poster_path.lineTo(w - 0.5 - radius, 0.5)
        poster_path.arcTo(QRectF(w - 0.5 - radius * 2, 0.5, radius * 2, radius * 2), 90, -90)
        poster_path.lineTo(w - 0.5, poster_h)
        poster_path.lineTo(0.5, poster_h)
        poster_path.closeSubpath()
        painter.fillPath(poster_path, pulse_color)

        # Placeholder tag kategori
        painter.drawRoundedRect(QRectF(16.0, poster_h + 14.0, 70.0, 20.0), 10.0, 10.0)

        # Placeholder judul lomba (2 baris)
        painter.drawRoundedRect(QRectF(16.0, poster_h + 42.0, w - 48.0, 16.0), 8.0, 8.0)
        painter.drawRoundedRect(QRectF(16.0, poster_h + 64.0, (w - 48.0) * 0.7, 14.0), 7.0, 7.0)

        # Placeholder penyelenggara
        painter.drawRoundedRect(QRectF(16.0, poster_h + 86.0, 110.0, 12.0), 6.0, 6.0)

        # Placeholder footer (sisa hari + tombol detail)
        painter.drawRoundedRect(QRectF(16.0, poster_h + 116.0, 65.0, 16.0), 8.0, 8.0)
        painter.drawRoundedRect(QRectF(w - 110.0, poster_h + 108.0, 94.0, 32.0), 16.0, 16.0)
