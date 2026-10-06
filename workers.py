# workers.py — pekerja latar belakang (background worker) supaya UI tidak freeze (Pertemuan 7)
#
# ATURAN EMAS Qt: widget HANYA boleh disentuh dari thread utama (thread UI).
# Pekerjaan berat dijalankan di thread lain lewat Worker; hasilnya dikirim kembali ke thread utama
# lewat SIGNAL (Qt otomatis "mengantre" signal lintas thread sehingga aman).
#
# Cara pakai:
#     def kerja_berat(kontrol, nama):             # berjalan di THREAD LAIN
#         for i in range(100):
#             if kontrol.dibatalkan: return None   # periksa tombol batal
#             ...pekerjaan...
#             kontrol.laporkan(i + 1)              # lapor progres 0-100
#         return "hasil"
#
#     workers.jalankan(kerja_berat, "x",
#                      saat_selesai=tampilkan,     # berjalan di THREAD UI
#                      saat_galat=tampilkan_error, # berjalan di THREAD UI
#                      saat_progres=isi_progress_bar)
import threading
import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class SinyalWorker(QObject):
    """Kumpulan signal milik satu Worker. Dibuat di thread utama, di-emit dari thread worker."""
    progres = Signal(int)      # 0-100
    selesai = Signal(object)   # hasil fungsi
    galat = Signal(str)        # pesan error


class Kontrol:
    """Dipegang fungsi worker: untuk melapor progres dan memeriksa apakah diminta berhenti."""

    def __init__(self, sinyal):
        self._sinyal = sinyal
        self._batal = threading.Event()   # Event aman dipakai lintas thread

    @property
    def dibatalkan(self):
        return self._batal.is_set()

    def laporkan(self, persen):
        try:
            self._sinyal.progres.emit(max(0, min(100, int(persen))))
        except RuntimeError:
            pass   # objek signal sudah dihapus (aplikasi ditutup)


class Worker(QRunnable):
    """Satu pekerjaan latar belakang. Dijalankan oleh QThreadPool (kumpulan thread siap pakai)."""

    def __init__(self, fungsi, *args):
        super().__init__()
        self.setAutoDelete(False)         # objek ini kita pegang sendiri sampai selesai (lihat _aktif)
        self._fungsi = fungsi
        self._args = args
        self.sinyal = SinyalWorker()
        self.kontrol = Kontrol(self.sinyal)

    def run(self):
        """Berjalan di thread worker. Jangan menyentuh widget di sini!"""
        try:
            hasil = self._fungsi(self.kontrol, *self._args)
        except Exception:                                   # error di thread lain tidak boleh hilang diam-diam
            self._kirim(self.sinyal.galat, traceback.format_exc(limit=3).strip().splitlines()[-1])
            return
        if not self.kontrol.dibatalkan:
            self._kirim(self.sinyal.selesai, hasil)
        else:
            self._kirim(self.sinyal.galat, "dibatalkan")

    @staticmethod
    def _kirim(sinyal, nilai):
        try:
            sinyal.emit(nilai)
        except RuntimeError:
            pass   # aplikasi sedang ditutup dan objek signal sudah dihapus Qt -> tidak ada yang perlu diberi tahu

    def batalkan(self):
        self.kontrol._batal.set()


# Bawaan QThreadPool = jumlah core CPU. Di laptop 2-core, penyalinan berkas bisa terpaksa MENUNGGU
# preload selesai. Pekerjaan I/O (baca/tulis berkas, jaringan) kebanyakan menunggu, bukan menghitung,
# jadi aman memakai lebih banyak thread daripada core.
_pool = QThreadPool.globalInstance()
if _pool.maxThreadCount() < 4:
    _pool.setMaxThreadCount(4)

_aktif = set()   # menjaga Worker tetap hidup selama berjalan (kalau tidak, bisa dihapus Python di tengah jalan)


def jalankan(fungsi, *args, saat_selesai=None, saat_galat=None, saat_progres=None):
    """Jalankan fungsi di thread lain. Mengembalikan Worker (punya .batalkan()).
    saat_selesai / saat_galat / saat_progres dipanggil di THREAD UTAMA."""
    worker = Worker(fungsi, *args)
    _aktif.add(worker)

    def lepas(*_):
        _aktif.discard(worker)

    if saat_progres:
        worker.sinyal.progres.connect(saat_progres)
    if saat_selesai:
        worker.sinyal.selesai.connect(saat_selesai)
    if saat_galat:
        worker.sinyal.galat.connect(saat_galat)
    worker.sinyal.selesai.connect(lepas)
    worker.sinyal.galat.connect(lepas)
    QThreadPool.globalInstance().start(worker)
    return worker


def jumlah_aktif():
    return len(_aktif)


def batalkan_semua():
    for worker in list(_aktif):
        worker.batalkan()


def tunggu_selesai(ms=3000):
    """Dipanggil saat aplikasi ditutup: minta semua worker berhenti lalu tunggu. True kalau semua sudah selesai."""
    batalkan_semua()
    selesai = QThreadPool.globalInstance().waitForDone(ms)
    if selesai:
        _aktif.clear()   # semua thread sudah selesai; jangan menunggu signal 'lepas' yang masih mengantre
    return selesai
