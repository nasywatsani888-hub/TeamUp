# demo_kebocoran.py — Demo teknik mendeteksi memory leak (Pertemuan 6: Memory & Resource Management)
# Cara pakai:  python demo_kebocoran.py
# Ada 4 percobaan. Tiap percobaan membandingkan versi BOCOR dengan versi PERBAIKAN, lalu mencetak
# angkanya. Percobaan 1-3 sengaja dibuat bocor sebagai bahan belajar (BUKAN kode aplikasi TeamUp).
# Percobaan 4 adalah temuan nyata yang kita ukur di aplikasi TeamUp.
import gc
import os
import sys
import tracemalloc
from functools import lru_cache

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

import helpers
import memory_tools

app = QApplication([])


def ukur(fungsi, ulang):
    """Jalankan 'fungsi' sebanyak 'ulang' kali; kembalikan (tambahan widget, tambahan RAM dalam MB)."""
    fungsi()                                  # pemanasan
    awal = memory_tools.snapshot()
    for _ in range(ulang):
        fungsi()
    akhir = memory_tools.snapshot()
    return akhir["widget"] - awal["widget"], akhir["ram_mb"] - awal["ram_mb"]


def judul(teks):
    print("\n" + "=" * 70 + f"\n{teks}\n" + "=" * 70)


# ---------------------------------------------------------------------------------------------
judul("PERCOBAAN 1 — Widget menumpuk karena lupa dihapus")
wadah = QWidget()
tata = QVBoxLayout(wadah)


def isi_bocor():
    tata.addWidget(QLabel("baris"))           # ditambah terus, tidak pernah dibuang -> numpuk


def isi_benar():
    helpers.clear_layout(tata)                # buang isi lama dulu (hide + setParent(None) + deleteLater)
    tata.addWidget(QLabel("baris"))


for nama, fungsi in (("BOCOR  (tanpa clear_layout)", isi_bocor), ("BENAR  (pakai clear_layout)", isi_benar)):
    helpers.clear_layout(tata)
    tambahan, _ = ukur(fungsi, 300)
    print(f"{nama:<30} 300 kali isi ulang -> widget bertambah {tambahan}")

# ---------------------------------------------------------------------------------------------
judul("PERCOBAAN 2 — Cache tanpa batas vs cache dibatasi (lru_cache)")
cache_liar = {}


def muat_bocor(nomor):
    if nomor not in cache_liar:
        cache_liar[nomor] = QPixmap(400, 400)  # ±640 KB per gambar, tidak pernah dibuang
        cache_liar[nomor].fill()
    return cache_liar[nomor]


@lru_cache(maxsize=8)                          # hanya 8 gambar terakhir yang disimpan
def muat_benar(nomor):
    gambar = QPixmap(400, 400)
    gambar.fill()
    return gambar


def jalan(muat):
    return lambda: [muat(i) for i in range(200)]   # 200 gambar berbeda


memory_tools.snapshot()
ram0 = memory_tools.ram_mb()
for i in range(200):
    muat_bocor(i)
ram1 = memory_tools.ram_mb()
for i in range(200):
    muat_benar(i)
ram2 = memory_tools.ram_mb()
print(f"BOCOR  (dict tanpa batas)  isi cache = {len(cache_liar):>3} gambar -> RAM naik ±{ram1 - ram0:6.1f} MB")
print(f"BENAR  (lru_cache maks 8)  isi cache = {muat_benar.cache_info().currsize:>3} gambar -> RAM naik ±{ram2 - ram1:6.1f} MB")
print("(angka RAM butuh 'pip install psutil'; kalau 0.0 berarti psutil belum terpasang)")
cache_liar.clear()

# ---------------------------------------------------------------------------------------------
judul("PERCOBAAN 3 — Siklus referensi & garbage collector (otomatis vs manual)")


class Simpul:
    def __init__(self):
        self.data = bytearray(200_000)         # muatan 200 KB
        self.pasangan = None


def buat_siklus(jumlah):
    for _ in range(jumlah):
        a, b = Simpul(), Simpul()
        a.pasangan, b.pasangan = b, a           # saling menunjuk -> hitungan referensi tidak pernah 0


tracemalloc.start()
gc.collect()
gc.disable()                                    # matikan GC otomatis supaya efeknya terlihat
dasar = tracemalloc.get_traced_memory()[0]
buat_siklus(100)                                # lalu semua variabel dilepas
sebelum = (tracemalloc.get_traced_memory()[0] - dasar) / 1024 / 1024
terhapus = gc.collect()                         # GC MANUAL menyapu siklusnya
sesudah = (tracemalloc.get_traced_memory()[0] - dasar) / 1024 / 1024
gc.enable()
tracemalloc.stop()
print(f"Setelah 100 pasangan dilepas, GC dimatikan : {sebelum:7.1f} MB masih tertahan  (BOCOR sementara)")
print(f"Setelah gc.collect() (manual)              : {sesudah:7.1f} MB  ({terhapus} objek disapu)")
print("Catatan: Python normalnya menyapu siklus otomatis; gc.collect() manual berguna di saat tertentu,")
print("         mis. setelah logout / menutup jendela besar (itu yang dilakukan MainWindow.handle_logout).")

# ---------------------------------------------------------------------------------------------
judul("PERCOBAAN 4 — Gaya .connect() yang menyisakan memori (temuan nyata di TeamUp)")


class Penerima(QObject):
    diteruskan = Signal(int)


class Kartu(QWidget):
    klik = Signal(int)

    def __init__(self, nomor):
        super().__init__()
        self.nomor = nomor
        self.tombol = QPushButton(self)

    @Slot()
    def kirim(self):
        self.klik.emit(self.nomor)


penerima = Penerima()
GAYA = {
    "lambda (menangkap variabel)": lambda k: k.tombol.clicked.connect(lambda: penerima.diteruskan.emit(k.nomor)),
    "bound .emit":                 lambda k: k.tombol.clicked.connect(penerima.diteruskan.emit),
    "@Slot di dalam kelas":        lambda k: k.tombol.clicked.connect(k.kirim),
    "signal -> signal langsung":   lambda k: k.klik.connect(penerima.diteruskan),
}
JUMLAH = 3000
print(f"{JUMLAH} widget dibuat lalu dihapus; yang diukur = memori Python yang TERSISA:")
for nama, sambung in GAYA.items():
    gc.collect()
    tracemalloc.start()
    dasar = tracemalloc.get_traced_memory()[0]
    for i in range(JUMLAH):
        kartu = Kartu(i)
        sambung(kartu)
        kartu.deleteLater()
        if i % 100 == 0:
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    sisa = tracemalloc.get_traced_memory()[0] - dasar
    tracemalloc.stop()
    print(f"  {nama:<30} sisa {sisa / 1024:7.1f} KB  ({sisa / JUMLAH:5.1f} byte per widget)")
print("Kesimpulan: sambungan signal -> signal langsung nyaris tidak menyisakan apa pun.")
