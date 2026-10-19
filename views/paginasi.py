# views/paginasi.py — baris di bawah daftar: "Menampilkan X dari Y" + tombol "Muat lebih banyak" (Pertemuan 7)
#
# Kenapa paginasi? Membuat widget TIDAK bisa dipindah ke worker (Qt melarang widget dibuat di thread
# lain). Satu-satunya cara agar thread UI tidak tertahan oleh daftar yang panjang adalah membuat lebih
# sedikit widget sekaligus: hanya halaman pertama dibuat, sisanya dimuat saat pengguna minta.
# Dipakai oleh: Postingan Saya dan Rekan Tim. (Halaman Lomba memakai model QML: views/lomba_backend.py)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

import config
import styles


class PaginasiBawah(QWidget):
    muat_diminta = Signal()

    def __init__(self, satuan):
        super().__init__()
        self.satuan = satuan   # "postingan" / "rekan"
        baris = QHBoxLayout(self)
        baris.setContentsMargins(0, 4, 0, 4)
        baris.setSpacing(14)
        self.info = QLabel("")
        self.info.setStyleSheet(f"font-size: 12px; color: {config.COLOR_SUBTEXT};")
        self.tombol = QPushButton("Muat lebih banyak")
        self.tombol.setStyleSheet(styles.POST_OUTLINE_BUTTON_STYLE)
        self.tombol.setCursor(Qt.CursorShape.PointingHandCursor)
        baris.addWidget(self.info)
        baris.addWidget(self.tombol)
        baris.addStretch()
        self.tombol.clicked.connect(self.muat_diminta)   # signal -> signal langsung
        self.hide()

    def perbarui(self, tampil, total, ukuran_halaman):
        """Panggil setelah daftar berubah. Tersembunyi kalau semua sudah tampil dan daftarnya pendek."""
        berikutnya = min(ukuran_halaman, total - tampil)
        self.info.setText(f"Menampilkan {tampil} dari {total} {self.satuan}")
        self.tombol.setText(f"Muat lebih banyak ({berikutnya} lagi)")
        self.tombol.setVisible(berikutnya > 0)
        self.setVisible(total > ukuran_halaman)
