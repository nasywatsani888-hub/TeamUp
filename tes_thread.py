# tes_thread.py — uji otomatis fitur concurrency TeamUp (Pertemuan 7)
# Cara pakai (dari folder proyek):   python tes_thread.py
# Mencetak LULUS / GAGAL tiap pemeriksaan. Kode keluar 0 = semua lulus.
import inspect
import os
import shutil
import sys
import tempfile
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEventLoop, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

import config
import data_store
import helpers
import preload
import sizes
import styles
import workers

lulus, gagal = [], []


def cek(nama, kondisi):
    (lulus if kondisi else gagal).append(nama)
    print(("  [LULUS] " if kondisi else "  [GAGAL] ") + nama)


def tunggu(app, kondisi, detik=6):
    batas = time.time() + detik
    while not kondisi() and time.time() < batas:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()


def macet_terlama(aksi, durasi_ms):
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


def uji_worker(app):
    print("\n1. Infrastruktur Worker")
    tunggu(app, lambda: workers.jumlah_aktif() == 0, 15)   # preload yang dimulai MainWindow harus selesai dulu
    utama = threading.get_ident()
    catatan = {"prog": [], "thread_kerja": None}

    def kerja(kontrol, n):
        catatan["thread_kerja"] = threading.get_ident()
        for i in range(n):
            if kontrol.dibatalkan:
                return "berhenti"
            time.sleep(0.02)
            kontrol.laporkan((i + 1) * 100 // n)
        return "ok"

    hasil = []
    workers.jalankan(kerja, 5, saat_selesai=lambda h: hasil.append((h, threading.get_ident())),
                     saat_progres=lambda p: catatan["prog"].append((p, threading.get_ident())))
    tunggu(app, lambda: hasil)
    cek("fungsi berjalan di thread BERBEDA dari thread UI", catatan["thread_kerja"] not in (None, utama))
    cek("callback selesai dipanggil di thread UI", hasil and hasil[0][0] == "ok" and hasil[0][1] == utama)
    nilai = [p for p, _ in catatan["prog"]]
    cek("callback progres di thread UI, naik teratur sampai 100", nilai == sorted(nilai) and nilai[-1] == 100
        and all(t == utama for _, t in catatan["prog"]))

    # error di worker harus sampai ke thread UI (tidak hilang diam-diam)
    galat = []
    workers.jalankan(lambda kontrol: 1 / 0, saat_galat=lambda m: galat.append((m, threading.get_ident())))
    tunggu(app, lambda: galat)
    cek("error di worker diteruskan ke thread UI", galat and "ZeroDivisionError" in galat[0][0] and galat[0][1] == utama)

    # pembatalan
    akhir = []
    selesai_normal = []
    w = workers.jalankan(kerja, 200, saat_selesai=lambda h: selesai_normal.append(h), saat_galat=lambda m: akhir.append(m))
    time.sleep(0.1)
    mulai = time.perf_counter()
    w.batalkan()
    tunggu(app, lambda: akhir or selesai_normal)
    cek("pembatalan menghentikan worker dengan cepat (< 300 ms)", akhir == ["dibatalkan"] and (time.perf_counter() - mulai) < 0.3)
    cek("worker yang dibatalkan TIDAK memanggil saat_selesai", not selesai_normal)

    # dua worker berjalan bersamaan (bukan antre)
    selesai = []
    mulai = time.perf_counter()
    for _ in range(3):
        workers.jalankan(lambda kontrol: time.sleep(0.4) or "x", saat_selesai=lambda h: selesai.append(h))
    tunggu(app, lambda: len(selesai) == 3)
    cek("3 worker 0,4 detik selesai paralel (< 0,9 detik, bukan 1,2)", len(selesai) == 3 and time.perf_counter() - mulai < 0.9)
    cek("batas thread pool >= 4", QThreadPool.globalInstance().maxThreadCount() >= 4)
    tunggu(app, lambda: workers.jumlah_aktif() == 0)
    cek("tidak ada worker tersisa setelah semua selesai", workers.jumlah_aktif() == 0)


def uji_responsif(app):
    print("\n2. UI tetap responsif")
    macet_sync = macet_terlama(lambda: time.sleep(0.6), 900)
    macet_worker = macet_terlama(lambda: workers.jalankan(lambda kontrol: time.sleep(0.6)), 900)
    workers.tunggu_selesai()
    cek(f"tanpa thread UI macet ({macet_sync:.0f} ms > 500)", macet_sync > 500)
    cek(f"dengan worker UI lancar ({macet_worker:.0f} ms < 100)", macet_worker < 100)


def uji_preload(app, jendela):
    print("\n3. Preload foto & poster di latar belakang")
    cek("preload.kerjakan tidak menyentuh data_store (data bersama hanya diakses thread UI)",
        "data_store" not in inspect.getsource(preload.kerjakan))
    kerja = preload.susun_daftar_kerja()
    cek(f"daftar kerja tersusun ({len(kerja)} gambar), tanpa duplikat", len(kerja) > 0 and len(kerja) == len(set(kerja)))
    tunggu(app, lambda: workers.jumlah_aktif() == 0, 15)
    cek("preload selesai", workers.jumlah_aktif() == 0)
    siap = len(helpers._gambar_siap)
    cek(f"gambar siap diparkir ({siap})", siap > 0)
    d = jendela.dashboard_page
    d.show_content("rekan")
    app.processEvents()
    cek("gambar yang dipakai UI diambil dari parkiran (parkiran berkurang)", len(helpers._gambar_siap) < siap)
    mulai = time.perf_counter()
    d.handle_lomba_detail(2)
    app.processEvents()
    ms = (time.perf_counter() - mulai) * 1000
    cek(f"buka Detail Lomba setelah preload cepat ({ms:.0f} ms < 100)", ms < 100)
    kunci_kartu = [k for k in kerja if (k[1], k[2], k[3], k[4]) == (sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_POSTER_HEIGHT, 20, False)]
    png = [os.path.exists(helpers.lokasi_png_qml(k[0], k[6], k[1], k[2], k[3])) for k in kunci_kartu]
    cek("berkas PNG untuk QML sudah disiapkan worker", png and all(png))
    sisa = [f for f in os.listdir(os.path.dirname(helpers.lokasi_png_qml("x", 0, 1, 1, 1))) if f.endswith(".tmp")]
    cek("tidak ada berkas .tmp setengah jadi (penulisan atomik)", not sisa)
    worker1 = preload.mulai()
    worker2 = preload.mulai()
    cek("preload.mulai() aman dipanggil dua kali", worker1 is worker2 or worker2 is not None or worker1 is None)
    tunggu(app, lambda: workers.jumlah_aktif() == 0)


def uji_form(app, jendela):
    print("\n4. Formulir kirim postingan (penyalinan berkas di worker)")
    import views.post_form_page as pf
    d = jendela.dashboard_page
    f = d.post_form_page
    tmp = tempfile.mkdtemp()
    poster = os.path.join(tmp, "poster_tes_thread.pdf")
    dokumen = os.path.join(tmp, "surat_tes_thread.pdf")
    open(poster, "wb").write(os.urandom(6 * 1024 * 1024))
    open(dokumen, "wb").write(os.urandom(3 * 1024 * 1024))

    def isi():
        d.handle_new_post()
        f.judul_input.setText("Lomba Uji Thread")
        f.kategori_input.setCurrentIndex(1)
        f.deskripsi_input.setPlainText("d")
        f.link_input.setText("https://x.id")
        f.kontak_input.setText("0812")
        f.poster_field.handle_file_chosen(poster)
        f.dokumen_field.handle_file_chosen(dokumen)

    isi()
    awal = len(data_store.postingan_list)
    terkirim = []
    f.submitted.connect(lambda i, m: terkirim.append((i, m)))
    f.submit_button.click()
    cek("saat mengirim: tombol terkunci & progress bar tampil",
        not f.submit_button.isEnabled() and not f.back_button.isEnabled() and f.submit_button.text() == "Mengirim...")
    f.submit_button.click()
    f.handle_submit()   # klik ganda harus diabaikan
    tunggu(app, lambda: terkirim)
    cek("berhasil: sinyal submitted tepat satu kali", len(terkirim) == 1)
    cek("klik ganda tidak membuat postingan dobel", len(data_store.postingan_list) == awal + 1)
    p = data_store.postingan_list[0]
    folder = os.path.join(config.ASSETS_DIR, "postingan")
    cek("berkas tersalin utuh (6 MB + 3 MB)", os.path.getsize(os.path.join(folder, p["poster"])) == 6 * 1024 * 1024
        and os.path.getsize(os.path.join(folder, p["dokumen"])) == 3 * 1024 * 1024)
    cek("tombol kembali normal setelah selesai", f.submit_button.isEnabled() and f.submit_button.text() == "Kirim untuk verifikasi")

    isi()
    awal = len(data_store.postingan_list)
    terkirim.clear()
    f.poster_field.path = os.path.join(tmp, "hilang.pdf")
    f.submit_button.click()
    tunggu(app, lambda: f.submit_button.isEnabled())
    cek("berkas sumber hilang: pesan error & tombol aktif lagi", "Gagal menyimpan" in f.message_label.text() and f.submit_button.isEnabled())
    cek("berkas sumber hilang: data tidak berubah", len(data_store.postingan_list) == awal and not terkirim)

    class KontrolPalsu:
        n = 0
        @property
        def dibatalkan(self):
            self.n += 1
            return self.n > 3
        def laporkan(self, persen):
            pass
    a, b = os.path.join(tmp, "o", "a.bin"), os.path.join(tmp, "o", "b.bin")
    hasil = pf.salin_berkas(KontrolPalsu(), [(poster, a), (dokumen, b)])
    cek("salin dibatalkan di tengah: berkas setengah jadi dihapus", hasil is None and not os.path.exists(a) and not os.path.exists(b))

    isi()
    awal = len(data_store.postingan_list)
    terkirim.clear()
    asli = pf.salin_berkas

    def lambat(kontrol, daftar):
        for i in range(80):
            if kontrol.dibatalkan:
                return None
            time.sleep(0.02)
        return [t for _, t in daftar]
    pf.salin_berkas = lambat
    f.submit_button.click()
    time.sleep(0.1)
    app.processEvents()
    d.show_content("beranda")   # meninggalkan form saat pengiriman jalan
    tunggu(app, lambda: workers.jumlah_aktif() == 0)
    for _ in range(20):
        app.processEvents()
    pf.salin_berkas = asli
    cek("pindah halaman saat mengirim: dibatalkan, tidak ada data & tidak lompat halaman",
        len(data_store.postingan_list) == awal and not terkirim)
    shutil.rmtree(tmp, ignore_errors=True)
    for nama in os.listdir(os.path.join(config.ASSETS_DIR, "postingan")):
        if "tes_thread" in nama:
            os.remove(os.path.join(config.ASSETS_DIR, "postingan", nama))


def uji_penutupan(app, jendela):
    print("\n5. Penutupan aplikasi saat worker masih jalan")
    def kooperatif(kontrol):          # worker yang BAIK: sering memeriksa tanda batal
        for _ in range(300):
            if kontrol.dibatalkan:
                return None
            time.sleep(0.02)
    workers.jalankan(kooperatif)
    time.sleep(0.05)
    mulai = time.perf_counter()
    jendela.close()   # memicu closeEvent -> workers.tunggu_selesai
    cek(f"closeEvent membatalkan & menunggu worker ({(time.perf_counter() - mulai) * 1000:.0f} ms, bukan 6 detik)",
        workers.jumlah_aktif() == 0 and (time.perf_counter() - mulai) < 1.0)


def main():
    app = QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    from main import MainWindow
    jendela = MainWindow()
    jendela.resize(1320, 820)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    print("=== UJI OTOMATIS CONCURRENCY ===")
    uji_worker(app)
    uji_responsif(app)
    uji_preload(app, jendela)
    uji_form(app, jendela)
    uji_penutupan(app, jendela)
    print(f"\nLULUS: {len(lulus)}   GAGAL: {len(gagal)}")
    for nama in gagal:
        print("  gagal ->", nama)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
