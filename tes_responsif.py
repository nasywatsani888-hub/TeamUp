# tes_responsif.py — mengukur "UI macet berapa lama" (Pertemuan 7: Concurrency)
# Cara pakai (dari folder proyek):   python tes_responsif.py
#
# Cara mengukur: sebuah timer di thread UI berdetak tiap 10 ms. Kalau thread UI sibuk / macet,
# detaknya tertunda. "Macet terlama" = jeda terpanjang antar dua detak. Pengguna mulai merasa
# aplikasi "ngelag" kalau jedanya > 100 ms (batas persepsi "instan" menurut Nielsen).
import json
import os
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

BATAS_MS = 100


class Detak:
    """Timer 10 ms di thread UI; mencatat waktu tiap detak."""

    def __init__(self):
        self.waktu = []
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(lambda: self.waktu.append(time.perf_counter()))

    def mulai(self):
        self.waktu = [time.perf_counter()]
        self.timer.start()

    def berhenti(self):
        self.timer.stop()
        jeda = [(b - a) * 1000 for a, b in zip(self.waktu, self.waktu[1:])]
        return max(jeda) if jeda else 0.0


def buat_gambar_uji(folder, jumlah=4, ukuran=(4000, 5000)):
    from PIL import Image
    daftar = []
    for i in range(jumlah):
        path = os.path.join(folder, f"uji{i}.jpg")
        Image.effect_noise(ukuran, 60).convert("RGB").save(path, quality=90)
        daftar.append(path)
    return daftar


def kerja_gambar(daftar, kontrol=None):
    """Tugas berat: decode + skala beberapa gambar besar (QImage -> aman di thread mana pun)."""
    import helpers
    for path in daftar:
        if kontrol is not None and kontrol.dibatalkan:
            return None
        helpers.render_kotak(path, 230, 200, 20, False, 2)
    return len(daftar)


def percobaan_a():
    """Tugas yang sama dijalankan (1) di thread UI dan (2) di worker. Bandingkan macet terlama."""
    import workers
    hasil = {}
    with tempfile.TemporaryDirectory() as folder:
        daftar = buat_gambar_uji(folder)
        detak = Detak()
        loop = QEventLoop()

        # 1) di thread UI
        detak.mulai()
        def sinkron():
            mulai = time.perf_counter()
            kerja_gambar(daftar)
            hasil["sinkron_total"] = (time.perf_counter() - mulai) * 1000
            QTimer.singleShot(60, loop.quit)
        QTimer.singleShot(50, sinkron)
        loop.exec()
        hasil["sinkron_macet"] = detak.berhenti()

        # 2) di worker
        detak.mulai()
        mulai = time.perf_counter()
        def selesai(_):
            hasil["worker_total"] = (time.perf_counter() - mulai) * 1000
            QTimer.singleShot(60, loop.quit)
        QTimer.singleShot(50, lambda: workers.jalankan(lambda kontrol, d: kerja_gambar(d, kontrol), daftar, saat_selesai=selesai))
        loop.exec()
        hasil["worker_macet"] = detak.berhenti()
    return hasil


def skenario(nama):
    """Dijalankan di PROSES BARU supaya cache kosong. nama: 'tanpa' atau 'preload'."""
    import data_store, helpers, preload, styles, workers
    app = QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    if nama == "tanpa":
        preload.mulai = lambda: None        # MainWindow memulai preload sendiri; di skenario ini kita matikan
    from main import MainWindow
    jendela = MainWindow()                  # (skenario 'preload' = perilaku aplikasi sebenarnya)
    jendela.resize(1320, 820)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    # user masih di splash / login selama ±1 detik
    selesai = time.time() + 1.0
    while time.time() < selesai:
        app.processEvents()
        time.sleep(0.01)
    d = jendela.dashboard_page
    hasil = {}
    for label, aksi in (("rekan", lambda: d.show_content("rekan")),
                        ("detail_lomba", lambda: d.handle_lomba_detail(2)),
                        ("profil_rekan", lambda: d.handle_partner_profile("marques@teamup.com"))):
        mulai = time.perf_counter()
        aksi()
        app.processEvents()
        hasil[label] = (time.perf_counter() - mulai) * 1000
    workers.tunggu_selesai()
    print("HASIL=" + json.dumps(hasil))


def jalankan_skenario(nama):
    keluaran = subprocess.run([sys.executable, __file__, "--skenario", nama], capture_output=True, text=True).stdout
    for baris in keluaran.splitlines():
        if baris.startswith("HASIL="):
            return json.loads(baris[6:])
    raise RuntimeError("skenario gagal:\n" + keluaran[-400:])


def label(ms):
    return "FREEZE" if ms > BATAS_MS else "lancar"


def main():
    app = QApplication([])
    print(f"=== TES RESPONSIVITAS UI (batas nyaman: {BATAS_MS} ms) ===\n")
    print("A. Dekode 4 gambar besar (4000x5000 px) — tugas yang sama, dua cara:")
    a = percobaan_a()
    print(f"   di thread UI : total {a['sinkron_total']:6.0f} ms | UI macet terlama {a['sinkron_macet']:6.0f} ms -> {label(a['sinkron_macet'])}")
    print(f"   di worker    : total {a['worker_total']:6.0f} ms | UI macet terlama {a['worker_macet']:6.0f} ms -> {label(a['worker_macet'])}")
    print("\nB. Pertama kali membuka halaman yang memuat foto/poster besar (waktu thread UI tertahan):")
    tanpa, dengan = jalankan_skenario("tanpa"), jalankan_skenario("preload")
    print(f"   {'halaman':<16}{'tanpa preload':>16}{'dengan preload':>18}")
    for kunci, nama in (("rekan", "Rekan Tim"), ("detail_lomba", "Detail Lomba"), ("profil_rekan", "Profil Rekan")):
        print(f"   {nama:<16}{tanpa[kunci]:>13.0f} ms{dengan[kunci]:>15.0f} ms")
    lancar = a["worker_macet"] <= BATAS_MS and max(dengan.values()) <= BATAS_MS
    print("\nKESIMPULAN:", "UI LANCAR (tidak ada macet di atas batas)" if lancar else "MASIH ADA MACET > batas")
    return 0 if lancar else 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--skenario":
        skenario(sys.argv[2])
    else:
        sys.exit(main())
