# memory_tools.py — alat bantu mengukur memori aplikasi (Pertemuan 6: Memory & Resource Management)
# Dipakai oleh tes_memori.py (uji otomatis) dan oleh mode debug di DashboardPage.
import gc
import os
import tracemalloc

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

try:
    import psutil   # opsional: untuk membaca RAM proses
except ImportError:
    psutil = None


def flush_deleted_widgets():
    """deleteLater() baru benar-benar menghapus saat event loop berputar. Fungsi ini
    memaksa 'putaran' itu supaya hasil pengukuran adil (tidak menghitung widget yang
    sebenarnya sudah dijadwalkan hapus)."""
    app = QApplication.instance()
    for _ in range(3):
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# Mode debug: jalankan  TEAMUP_DEBUG_MEMORY=1 python main.py  -> tiap pindah halaman, kondisi
# memori dicetak di terminal (berguna untuk memantau saat demo / presentasi).
DEBUG = os.environ.get("TEAMUP_DEBUG_MEMORY") == "1"


def catat(label):
    """Cetak satu baris kondisi memori. Tidak melakukan apa-apa kalau mode debug mati."""
    if not DEBUG:
        return
    foto = snapshot()
    print(f"[memori] {label:<14} widget={foto['widget']:<5} objek={foto['objek_python']:<7} ram={foto['ram_mb']} MB")


def ram_mb():
    """RAM yang dipakai proses ini (MB), atau 0 kalau psutil belum terpasang."""
    if psutil is None:
        return 0.0
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def snapshot():
    """Foto kondisi memori saat ini -> dict angka."""
    flush_deleted_widgets()
    gc.collect()   # bersihkan objek Python yang sudah tidak dipakai agar angkanya stabil
    jumlah_python_kb = 0
    if tracemalloc.is_tracing():
        jumlah_python_kb = tracemalloc.get_traced_memory()[0] / 1024
    return {
        "widget": len(QApplication.allWidgets()),   # semua QWidget yang masih hidup
        "objek_python": len(gc.get_objects()),      # semua objek Python yang dilacak GC
        "python_kb": round(jumlah_python_kb),       # memori yang dialokasikan kode Python
        "ram_mb": round(ram_mb(), 1),               # RAM proses (termasuk bagian C++ milik Qt)
    }


def widget_per_kelas(top=8):
    """Kelas widget yang paling banyak hidup -> petunjuk siapa yang bocor."""
    hitung = {}
    for widget in QApplication.allWidgets():
        nama = type(widget).__name__
        hitung[nama] = hitung.get(nama, 0) + 1
    return sorted(hitung.items(), key=lambda pasangan: pasangan[1], reverse=True)[:top]
