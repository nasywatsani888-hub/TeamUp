# demo_thread.py — Demo Concurrency untuk presentasi (Pertemuan 7)
#
#   python demo_thread.py              -> membuka JENDELA demo (bola bergerak = tanda UI hidup)
#   python demo_thread.py --otomatis   -> mencetak angka percobaan di terminal (tanpa jendela)
#
# Di jendela: klik tombol 1 -> bola BERHENTI 3 detik (UI freeze / "not responding").
#             klik tombol 2 -> pekerjaan sama berjalan di worker; bola TETAP bergerak, ada progress bar, bisa dibatalkan.
import os
import sys
import threading
import time

if "--otomatis" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEventLoop, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QApplication, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget)

import workers

LANGKAH = 100           # pekerjaan dibagi 100 langkah
JEDA = 0.03             # tiap langkah 30 ms -> total 3 detik (mewakili unduh / kirim data / hitung berat)


def pekerjaan_berat(kontrol):
    """Pekerjaan 3 detik yang sama dipakai oleh kedua cara. 'kontrol' None = dijalankan di thread UI."""
    for langkah in range(LANGKAH):
        if kontrol is not None and kontrol.dibatalkan:
            return "dibatalkan"
        time.sleep(JEDA)
        if kontrol is not None:
            kontrol.laporkan(langkah + 1)
    return "selesai"


class Bola(QWidget):
    """Bola yang bergerak bolak-balik. Kalau thread UI macet, bola berhenti -> mudah terlihat."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.x = 0.0
        self.arah = 1
        timer = QTimer(self)
        timer.timeout.connect(self.gerak)
        timer.start(16)

    def gerak(self):
        self.x += 4 * self.arah
        if self.x > self.width() - 40 or self.x < 0:
            self.arah *= -1
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#3374C7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(self.x, 10, 40, 40))


class Jendela(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Thread — TeamUp")
        self.resize(560, 330)
        self.terakhir = time.perf_counter()
        self.macet_terlama = 0.0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Demo: UI freeze vs background worker</b><br>Bola di bawah bergerak selama UI hidup."))
        layout.addWidget(Bola())
        self.label_macet = QLabel("UI macet terlama: 0 ms")
        layout.addWidget(self.label_macet)
        self.tombol_sinkron = QPushButton("1. Jalankan TANPA thread (UI akan freeze 3 detik)")
        self.tombol_worker = QPushButton("2. Jalankan DENGAN worker (UI tetap lancar)")
        self.tombol_batal = QPushButton("Batalkan worker")
        self.tombol_batal.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, LANGKAH)
        self.status = QLabel("Siap.")
        for widget in (self.tombol_sinkron, self.tombol_worker, self.tombol_batal, self.progress, self.status):
            layout.addWidget(widget)
        self.worker = None
        self.tombol_sinkron.clicked.connect(self.jalankan_sinkron)
        self.tombol_worker.clicked.connect(self.jalankan_worker)
        self.tombol_batal.clicked.connect(self.batalkan)
        # Detak pengukur: kalau thread UI macet, jeda antar detak membesar
        self.detak = QTimer(self)
        self.detak.timeout.connect(self.catat_detak)
        self.detak.start(10)

    def catat_detak(self):
        sekarang = time.perf_counter()
        self.macet_terlama = max(self.macet_terlama, (sekarang - self.terakhir) * 1000)
        self.terakhir = sekarang
        self.label_macet.setText(f"UI macet terlama: {self.macet_terlama:.0f} ms")

    def jalankan_sinkron(self):
        self.macet_terlama = 0.0
        self.status.setText("Berjalan di thread UI... (jendela akan 'membeku')")
        QApplication.processEvents()
        hasil = pekerjaan_berat(None)          # <- MEMBLOKIR thread UI selama 3 detik
        self.status.setText(f"Tanpa thread: {hasil}. Lihat angka macet di atas.")

    def jalankan_worker(self):
        self.macet_terlama = 0.0
        self.progress.setValue(0)
        self.tombol_worker.setEnabled(False)
        self.tombol_batal.setEnabled(True)
        self.status.setText("Berjalan di worker... coba gerakkan / ubah ukuran jendela!")
        self.worker = workers.jalankan(
            pekerjaan_berat,
            saat_progres=self.progress.setValue,
            saat_selesai=lambda hasil: self.akhiri(f"Dengan worker: {hasil}."),
            saat_galat=lambda pesan: self.akhiri(f"Dengan worker: {pesan}."))

    def batalkan(self):
        if self.worker:
            self.worker.batalkan()

    def akhiri(self, teks):
        self.tombol_worker.setEnabled(True)
        self.tombol_batal.setEnabled(False)
        self.status.setText(teks + " Lihat angka macet di atas.")

    def closeEvent(self, event):
        workers.tunggu_selesai()
        super().closeEvent(event)


# ------------------------------------------------------------------ mode otomatis (tanpa jendela)
def ukur_macet(aksi, durasi_ms):
    """Jalankan 'aksi' sambil mengukur jeda terpanjang detak UI."""
    waktu = [time.perf_counter()]
    timer = QTimer()
    timer.timeout.connect(lambda: waktu.append(time.perf_counter()))
    loop = QEventLoop()
    timer.start(10)
    QTimer.singleShot(50, aksi)
    QTimer.singleShot(durasi_ms, loop.quit)
    loop.exec()
    timer.stop()
    return max((b - a) * 1000 for a, b in zip(waktu, waktu[1:]))


def otomatis():
    app = QApplication([])
    print("PERCOBAAN 1 — pekerjaan 3 detik: thread UI vs worker")
    macet = ukur_macet(lambda: pekerjaan_berat(None), 3400)
    print(f"  di thread UI : UI macet terlama {macet:7.0f} ms  -> FREEZE")
    macet = ukur_macet(lambda: workers.jalankan(pekerjaan_berat), 3400)
    print(f"  di worker    : UI macet terlama {macet:7.0f} ms  -> lancar")
    workers.tunggu_selesai(4000)

    print("\nPERCOBAAN 2 — tugas CPU murni Python di worker (jebakan GIL)")
    def hitung(kontrol):
        total = 0
        for i in range(12_000_000):
            total += i * i
        return total
    mulai = time.perf_counter()
    selesai_ms = []
    def catat(_):
        selesai_ms.append((time.perf_counter() - mulai) * 1000)
    macet = ukur_macet(lambda: workers.jalankan(hitung, saat_selesai=catat), 2500)
    print(f"  loop Python di worker: UI macet terlama {macet:5.0f} ms (UI masih bergerak)")
    print("  Catatan: karena GIL, thread Python bergantian memakai interpreter, BUKAN berjalan paralel. UI tetap")
    print("           hidup, tapi menambah thread tidak mempercepat hitungan Python. Untuk komputasi berat pakai")
    print("           proses terpisah (multiprocessing / QProcess) atau fungsi C++ yang melepas GIL (mis. QImage.scaled).")
    workers.tunggu_selesai(4000)

    print("\nPERCOBAAN 3 — race condition: 4 thread menambah satu penghitung bersama, 500x tiap thread")
    def hitung_bersama(pakai_kunci):
        penghitung, kunci = [0], threading.Lock()
        def tambah():
            for _ in range(500):
                if pakai_kunci:
                    with kunci:
                        nilai = penghitung[0]; time.sleep(0); penghitung[0] = nilai + 1
                else:
                    nilai = penghitung[0]; time.sleep(0); penghitung[0] = nilai + 1   # baca-ubah-tulis tidak atomik!
        pekerja = [threading.Thread(target=tambah) for _ in range(4)]
        for t in pekerja: t.start()
        for t in pekerja: t.join()
        return penghitung[0]
    print(f"  tanpa Lock : hasil {hitung_bersama(False):5d} dari seharusnya 2000  (ada pembaruan yang hilang -> SALAH)")
    print(f"  dengan Lock: hasil {hitung_bersama(True):5d} dari seharusnya 2000  (benar)")


if __name__ == "__main__":
    if "--otomatis" in sys.argv:
        otomatis()
    else:
        app = QApplication(sys.argv)
        jendela = Jendela()
        jendela.show()
        sys.exit(app.exec())
