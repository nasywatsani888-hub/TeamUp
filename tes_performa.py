# tes_performa.py — Uji performa CPU & memori dengan ANGGARAN (budget) (Pertemuan 13)
#
# Bedanya dengan profil_cpu.py: profiler MENEMUKAN titik panas (analisis, dijalankan manusia). Tes ini MENJAGA agar
# performa tidak memburuk (otomatis, gagal kalau melewati anggaran). Dipasangkan: profiler menjawab "kenapa lambat?",
# tes performa menjawab "apakah masih sehat?".
#
# Yang diuji (setiap angka anggaran diturunkan dari PENGUKURAN, lihat catatan di bawah):
#   1. kalibrasi mesin     : kecepatan mesin ini dibanding mesin referensi, agar anggaran adil di komputer yang berbeda
#   2. anggaran CPU        : 8 skenario beban kerja nyata (sama dengan profil_cpu.py)
#   3. operasi di thread UI: operasi yang berjalan di thread utama tidak boleh membuat UI terasa macet
#   4. skalabilitas        : waktu naik LINEAR terhadap ukuran data, dan tidak ada ReDoS (regex yang meledak pada input jahat)
#   5. memori puncak       : berkas besar diproses per potongan (RAM konstan), bukan dimuat utuh
#   6. kebocoran memori    : operasi yang diulang tidak membuat memori terus tumbuh; struktur data dibatasi ukurannya
#
# CARA ANGGARAN DITENTUKAN (jujur): diukur di mesin referensi, lalu diberi pengaman 4-5x untuk waktu (mesin & beban
# sesaat berbeda-beda) dan 2-3x untuk memori (lebih deterministik). Waktu diskalakan dengan hasil kalibrasi mesin.
# Tujuan tes ini menangkap kemunduran BESAR (mis. algoritma jadi kuadratik, berkas dimuat utuh ke RAM, struktur tak
# terbatas), bukan selisih 10%. Kalau anggaran terlalu ketat/longgar di komputermu, ubah konstanta di bagian atas.
#
# CPU diukur dengan time.process_time() (waktu CPU, bukan waktu dinding) dan diambil yang TERCEPAT dari beberapa jalan
# hangat, supaya tidak terpengaruh program lain yang sedang berjalan. Memori diukur dengan tracemalloc (hanya memori
# Python; memori objek Qt/C++ tidak terhitung, itu urusan tes_memori.py).
#
# Cara menjalankan:  python3 tes_performa.py      (± 30 detik; jangan menjalankan program berat lain bersamaan)
import gc
import hashlib
import os
import random
import statistics
import sys
import tempfile
import time
import tracemalloc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import profil_cpu                      # mengisolasi database / folder data / kunci, dan menyediakan skenario beban kerja

# ============================================================== ANGGARAN (diukur di mesin referensi)
KALIBRASI_REFERENSI = 0.062            # detik CPU untuk kalibrasi() di mesin referensi

ANGGARAN_CPU_DTK = {                   # skenario -> detik CPU maksimal (ukuran referensi dalam komentar)
    "hash_password": 1.2,              # ukur 0,28  (PBKDF2 sengaja lambat)
    "validasi": 0.6,                   # ukur 0,14
    "samarkan_log": 0.5,               # ukur 0,11
    "enkripsi": 1.2,                   # ukur 0,29
    "database": 0.4,                   # ukur 0,09
    "data_store": 0.15,                # ukur 0,034
    "ui_startup": 1.0,                 # ukur 0,16
    "ui_navigasi": 1.3,                # ukur 0,25
}
ANGGARAN_PUNCAK_MB = {                 # skenario -> memori puncak Python maksimal (MB)
    "hash_password": 2.0, "validasi": 2.0, "samarkan_log": 2.0, "enkripsi": 40.0,        # enkripsi ukur 13,4 (data 2 MB)
    "database": 5.0, "data_store": 5.0, "ui_startup": 10.0, "ui_navigasi": 5.0,
}
ANGGARAN_THREAD_UI = {                 # operasi di thread utama -> detik maksimal per operasi (mesin referensi)
    "verifikasi password (PBKDF2)": 0.12,      # ukur 0,03
    "validasi satu isian (7 aturan)": 0.001,   # ukur 0,00002
    "samarkan satu baris log": 0.0002,         # ukur 0,00002
    "muat daftar postingan dari database": 0.02,   # ukur 0,0015
    "buka satu halaman dashboard": 0.08,       # ukur 0,006
}
BATAS_BERKAS_MB = 16.0                 # puncak memori enkripsi berkas (diukur 8,2 MB untuk berkas 5 maupun 20 MB)
BATAS_TUMBUH_KB = 100.0                # pertumbuhan memori antar-blok yang masih dianggap wajar (diukur 0 - 5 KB)
FAKTOR_LINEAR = 3.0                    # waktu boleh naik sampai 3x lebih besar dari rasio ukuran sebelum dianggap non-linear

LULUS = 0
GAGAL = 0


def cek(nama, kondisi, rincian=""):
    global LULUS, GAGAL
    if kondisi:
        LULUS += 1
        print(f"  [LULUS] {nama}" + (f"  — {rincian}" if rincian else ""))
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f"  — {rincian}" if rincian else ""))


# ============================================================== Alat ukur
def kalibrasi():
    """Beban tetap campuran (hash, sort, aritmetika) untuk mengukur kecepatan mesin ini. Satuan: detik CPU."""
    mulai = time.process_time()
    data = b"x" * 1_000_000
    for _ in range(15):
        hashlib.sha256(data).digest()
    acak = random.Random(1)
    angka = [acak.random() for _ in range(150_000)]
    angka.sort()
    total = 0
    for i in range(400_000):
        total += i * i % 7
    return time.process_time() - mulai


def skala_mesin():
    """Faktor kecepatan mesin ini relatif terhadap mesin referensi (dibatasi 0,5x - 8x agar anggaran tidak ekstrem)."""
    nilai = statistics.median(kalibrasi() for _ in range(5))
    return max(0.5, min(8.0, nilai / KALIBRASI_REFERENSI)), nilai


def cpu_tercepat(kerja, jalan=3):
    """Waktu CPU tercepat dari beberapa jalan hangat (satu jalan awal dibuang untuk memanaskan cache)."""
    kerja()
    return min(_waktu_cpu(kerja) for _ in range(jalan))


def _waktu_cpu(kerja):
    mulai = time.process_time()
    kerja()
    return time.process_time() - mulai


def waktu_per_panggilan(fungsi, ulang):
    """Detik CPU rata-rata per panggilan (batch tercepat dari 5)."""
    terbaik = float("inf")
    for _ in range(5):
        mulai = time.process_time()
        for _ in range(ulang):
            fungsi()
        terbaik = min(terbaik, (time.process_time() - mulai) / ulang)
    return terbaik


def puncak_mb(kerja):
    gc.collect()
    tracemalloc.start()
    try:
        kerja()
        return tracemalloc.get_traced_memory()[1] / 1e6
    finally:
        tracemalloc.stop()


def tumbuh_kb(blok):
    """Pertumbuhan memori Python (KB) antara akhir blok ke-2 dan ke-3 (blok ke-1 = pemanasan cache)."""
    blok()
    gc.collect()
    tracemalloc.start()
    try:
        blok()
        gc.collect()
        a = tracemalloc.get_traced_memory()[0]
        blok()
        gc.collect()
        b = tracemalloc.get_traced_memory()[0]
    finally:
        tracemalloc.stop()
    return (b - a) / 1024


def rasio_waktu(fungsi_n, fungsi_besar, ulang=20):
    """Rasio waktu antara ukuran besar dan ukuran kecil (masing-masing diambil batch tercepat)."""
    return waktu_per_panggilan(fungsi_besar, ulang) / max(waktu_per_panggilan(fungsi_n, ulang), 1e-9)


# ============================================================== 1. Kalibrasi
def uji_kalibrasi():
    print("\n1. Kalibrasi mesin")
    skala, nilai = skala_mesin()
    print(f"     kalibrasi {nilai:.3f} dtk (referensi {KALIBRASI_REFERENSI:.3f}) -> mesin ini {skala:.2f}x dibanding referensi")
    cek("kalibrasi konsisten antar pengukuran (variasi < 40%)",
        max(kalibrasi() for _ in range(3)) / max(min(kalibrasi() for _ in range(3)), 1e-9) < 1.4)
    return skala


# ============================================================== 2. Anggaran CPU
def uji_cpu(skala):
    print("\n2. Anggaran CPU per skenario (waktu CPU tercepat dari 3 jalan hangat, anggaran diskalakan dengan kecepatan mesin)")
    kerja_skenario = {}
    for nama in ANGGARAN_CPU_DTK:
        deskripsi, siapkan = profil_cpu.SKENARIO[nama]
        kerja_skenario[nama] = siapkan()
        batas = ANGGARAN_CPU_DTK[nama] * skala
        waktu = cpu_tercepat(kerja_skenario[nama])
        if waktu > batas:                                      # pengukuran ulang sebelum dinyatakan gagal (kurangi gangguan sesaat)
            waktu = min(waktu, cpu_tercepat(kerja_skenario[nama], 4))
        cek(f"CPU {nama}", waktu <= batas, f"{waktu:.3f} dtk <= anggaran {batas:.2f} dtk ({100 * waktu / batas:.0f}% dari anggaran)")
    return kerja_skenario


# ============================================================== 3. Operasi di thread UI
def uji_thread_ui(skala):
    print("\n3. Operasi di thread UI (di atas ±100 ms terasa macet)")
    import data_store
    import validasi
    import penanganan_error
    from database import repository, sandi
    from PySide6.QtWidgets import QApplication
    import styles
    from main import MainWindow
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    jendela = MainWindow()
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    app.processEvents()
    dashboard = jendela.dashboard_page
    tersimpan = sandi.hash_password("Rahasia-Super-Panjang-2026!")
    halaman = ["beranda", "lomba", "rekan", "notifikasi", "riwayat"]
    indeks = [0]

    def buka_halaman():
        dashboard.show_content(halaman[indeks[0] % len(halaman)])
        indeks[0] += 1
        app.processEvents()

    def satu_isian():
        teks = "budi.santoso@kampus.ac.id"
        validasi.periksa_email(teks); validasi.periksa_username(teks); validasi.periksa_nama(teks)
        validasi.periksa_password(teks); validasi.periksa_url(teks); validasi.periksa_kontak(teks); validasi.bersihkan_teks(teks)

    operasi = {
        "verifikasi password (PBKDF2)": (lambda: sandi.cocok(tersimpan, "salah-salah-salah-123!"), 4),
        "validasi satu isian (7 aturan)": (satu_isian, 300),
        "samarkan satu baris log": (lambda: penanganan_error.samarkan("login budi@kampus.ac.id hp 0812-3456-7890 password=abc"), 1000),
        "muat daftar postingan dari database": (repository.muat_postingan, 30),
        "buka satu halaman dashboard": (buka_halaman, 10),
    }
    for nama, (fungsi, ulang) in operasi.items():
        batas = ANGGARAN_THREAD_UI[nama] * skala
        waktu = waktu_per_panggilan(fungsi, ulang)
        satuan = f"{waktu * 1000:.3f} ms" if waktu < 0.01 else f"{waktu * 1000:.1f} ms"
        cek(f"thread UI: {nama}", waktu <= batas, f"{satuan} <= anggaran {batas * 1000:.2f} ms")
    jendela.close()
    jendela.deleteLater()
    app.processEvents()


# ============================================================== 4. Skalabilitas & ReDoS
def uji_skalabilitas(skala):
    print("\n4. Skalabilitas (waktu naik linear) dan ketahanan terhadap input jahat (ReDoS)")
    import copy
    import data_store
    import penanganan_error as pe
    import validasi as v

    def linear(nama, kecil, besar, kali, ulang=20):
        rasio = rasio_waktu(kecil, besar, ulang)
        batas = kali * FAKTOR_LINEAR
        cek(f"linear: {nama}", rasio <= batas, f"data {kali}x lebih besar -> waktu {rasio:.1f}x (batas {batas:.0f}x; kuadratik akan ±{kali * kali}x)")

    for nama, pola, kecil_n in (("samarkan, huruf biasa", "a", 4000), ("samarkan, deretan angka", "0", 4000),
                                ("samarkan, tanda @ berulang", "x@", 2000), ("samarkan, spasi dan huruf", "a b ", 1000)):
        linear(nama, lambda p=pola, n=kecil_n: pe.samarkan(p * n), lambda p=pola, n=kecil_n: pe.samarkan(p * (n * 8)), 8)
    linear("bersihkan_teks", lambda: v.bersihkan_teks("Budi  Santoso " * 500), lambda: v.bersihkan_teks("Budi  Santoso " * 4000), 8, 10)

    jahat = {
        "email: 254 huruf tanpa @": lambda: v.periksa_email("a" * 254),
        "email: strip berulang": lambda: v.periksa_email("a" + "-" * 250 + "@x.com"),
        "email: label panjang berulang": lambda: v.periksa_email("a@" + "a." * 120 + "-"),
        "URL: host 2000 huruf": lambda: v.periksa_url("https://" + "a" * 2000),
        "URL: strip berselang-seling": lambda: v.periksa_url("https://" + "a-" * 1000 + "!"),
        "URL: label berulang": lambda: v.periksa_url("https://" + ("a" * 63 + ".") * 30 + "-"),
        "kontak: 20.000 strip": lambda: v.periksa_kontak("0812" + "-" * 20000),
        "samarkan: 100.000 huruf": lambda: pe.samarkan("a" * 100000),
        "samarkan: 100.000 '@'": lambda: pe.samarkan("@" * 100000),
    }
    for nama, f in jahat.items():
        waktu = waktu_per_panggilan(f, 3)
        batas = 0.05 * skala
        cek(f"ReDoS: {nama}", waktu <= batas, f"{waktu * 1000:.2f} ms <= {batas * 1000:.0f} ms")

    asli = copy.deepcopy(data_store.users)
    data_store.current_user = data_store.get_user("demo@teamup.com")

    def partners(kali):
        data_store.users[:] = [copy.deepcopy(u) for _ in range(kali) for u in asli]
        for i, u in enumerate(data_store.users):
            u["email"] = f"u{i}@x.id"
        data_store.current_user = data_store.users[0]
        return waktu_per_panggilan(data_store.get_partners, 10)

    try:
        kecil, besar = partners(10), partners(80)
        cek("linear: get_partners (jumlah user x8)", besar / max(kecil, 1e-9) <= 8 * FAKTOR_LINEAR,
            f"{len(asli) * 10} -> {len(asli) * 80} user: waktu {besar / max(kecil, 1e-9):.1f}x (batas {8 * FAKTOR_LINEAR:.0f}x)")
    finally:
        data_store.users[:] = asli
        data_store.current_user = None


# ============================================================== 5. Memori puncak & streaming
def uji_memori_puncak(kerja_skenario):
    print("\n5. Memori puncak (tracemalloc) dan pemrosesan berkas per potongan")
    for nama, batas in ANGGARAN_PUNCAK_MB.items():
        puncak = puncak_mb(kerja_skenario[nama])
        cek(f"memori puncak {nama}", puncak <= batas, f"{puncak:.2f} MB <= anggaran {batas:.0f} MB")

    import enkripsi
    import file_storage
    tmp = tempfile.mkdtemp(prefix="teamup_tes_performa_")
    hasil = {}
    for mb in (5, 20):
        sumber = os.path.join(tmp, f"b{mb}.bin")
        with open(sumber, "wb") as f:
            f.write(os.urandom(mb * 1024 * 1024))
        hasil[mb] = (puncak_mb(lambda: enkripsi.enkripsi_berkas(sumber, sumber + ".enc")),
                     puncak_mb(lambda: enkripsi.dekripsi_berkas(sumber + ".enc", sumber + ".out")),
                     puncak_mb(lambda: file_storage.simpan_berkas(sumber, "poster")))
    enk, dek, salin = hasil[20]
    cek("enkripsi berkas 20 MB: puncak memori jauh di bawah ukuran berkas (streaming)", enk <= BATAS_BERKAS_MB and enk < 20 * 0.5,
        f"{enk:.2f} MB untuk berkas 20 MB (batas {BATAS_BERKAS_MB:.0f} MB)")
    cek("dekripsi berkas 20 MB: puncak memori jauh di bawah ukuran berkas", dek <= BATAS_BERKAS_MB, f"{dek:.2f} MB")
    cek("puncak memori TIDAK ikut membesar saat berkas 4x lebih besar (konstan)", hasil[20][0] <= hasil[5][0] * 1.5 + 0.5,
        f"5 MB -> {hasil[5][0]:.2f} MB; 20 MB -> {hasil[20][0]:.2f} MB")
    cek("simpan_berkas 20 MB (salin): hampir tanpa memori tambahan", salin <= 1.0, f"{salin:.3f} MB")
    muat_utuh = puncak_mb(lambda: enkripsi.enkripsi_bytes(open(os.path.join(tmp, "b20.bin"), "rb").read()))
    cek("pembanding: memuat berkas utuh ke RAM memakai jauh lebih banyak (membuktikan desain per-potongan perlu)",
        muat_utuh > enk * 4, f"utuh {muat_utuh:.1f} MB vs per potongan {enk:.1f} MB")


# ============================================================== 6. Kebocoran memori
def uji_kebocoran():
    print("\n6. Kebocoran memori (pertumbuhan antar-blok pada operasi yang diulang) dan struktur data terbatas")
    import data_store
    import disk_cache
    import enkripsi
    import keamanan_akun
    import penanganan_error as pe
    import validasi as v
    from database import repository
    from PySide6.QtWidgets import QApplication
    import styles
    from main import MainWindow

    def blok_samarkan():
        for i in range(3000):
            pe.samarkan(f"user{i}@kampus.ac.id hp 0812-3456-{i:04d} password=abc{i}")

    def blok_validasi():
        for i in range(3000):
            v.periksa_email(f"user{i}@kampus.ac.id"); v.periksa_password(f"Rahasia-Super-Panjang-{i}!"); v.periksa_url(f"https://k.ac.id/{i}")

    def blok_database():
        for _ in range(80):
            repository.muat_postingan(); repository.muat_users(); repository.muat_notifikasi()

    def blok_log():
        pe.setup_logging()
        for i in range(3000):
            pe.logger.info("baris log %d dari user%d@x.com", i, i)

    def blok_laporkan():
        for i in range(300):
            try:
                raise RuntimeError(f"gagal {i} dari user{i}@x.com")
            except RuntimeError as e:
                pe.laporkan(e, "uji")

    def blok_cache():
        for i in range(300):
            disk_cache.buat_jika_perlu(f"k{i % 200}", lambda p: open(p, "wb").write(b"x" * 500))
        disk_cache.bersihkan()

    def blok_enkripsi():
        for i in range(1500):
            enkripsi.dekripsi_teks(enkripsi.enkripsi_teks(f"0812-{i}"))

    def blok_limiter():
        keamanan_akun.atur_ulang()
        for i in range(3000):
            keamanan_akun.catat_gagal(f"orang{i}@x.com")

    for nama, blok, batas in (("penyamaran log (samarkan)", blok_samarkan, BATAS_TUMBUH_KB), ("validasi input", blok_validasi, BATAS_TUMBUH_KB),
                              ("baca database berulang", blok_database, BATAS_TUMBUH_KB), ("penulisan log berputar", blok_log, 2 * BATAS_TUMBUH_KB),
                              ("laporkan error ke user", blok_laporkan, BATAS_TUMBUH_KB), ("cache disk", blok_cache, BATAS_TUMBUH_KB),
                              ("enkripsi teks", blok_enkripsi, BATAS_TUMBUH_KB), ("pembatas login", blok_limiter, BATAS_TUMBUH_KB)):
        kb = tumbuh_kb(blok)
        cek(f"tidak bocor: {nama}", kb <= batas, f"tumbuh {kb:.1f} KB antar-blok (batas {batas:.0f} KB)")

    keamanan_akun.atur_ulang()
    keamanan_akun.gunakan_jam(lambda: 1000.0)
    tracemalloc.start()
    for i in range(20000):
        keamanan_akun.catat_gagal(f"serang{i}@x.com")
    entri, memori_kb = len(keamanan_akun._login), tracemalloc.get_traced_memory()[0] / 1024
    tracemalloc.stop()
    keamanan_akun.atur_ulang()
    keamanan_akun.gunakan_jam(time.monotonic)
    cek("pembatas login terbatas: 20.000 email berbeda tidak menghabiskan memori", entri <= keamanan_akun.MAKS_AKUN_DICATAT and memori_kb < 2048,
        f"{entri} entri, {memori_kb:.0f} KB (penyerang mengarang 20.000 email)")

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    jendela = MainWindow()
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    app.processEvents()
    dashboard = jendela.dashboard_page

    def blok_navigasi():
        for _ in range(10):
            for kunci in ("beranda", "lomba", "rekan", "notifikasi", "riwayat"):
                dashboard.show_content(kunci)
                app.processEvents()

    kb = tumbuh_kb(blok_navigasi)
    cek("tidak bocor: navigasi UI (memori Python mendatar setelah pemanasan)", kb <= 256.0, f"tumbuh {kb:.1f} KB per 50 pembukaan halaman")
    jendela.close()
    jendela.deleteLater()
    app.processEvents()


def main():
    print("=== UJI PERFORMA CPU & MEMORI DENGAN ANGGARAN (Pertemuan 13) ===")
    from database.seeder import seed_database
    seed_database()                                     # teamup.db tidak lagi di repo: pastikan data contoh ada
    skala = uji_kalibrasi()
    kerja = uji_cpu(skala)
    uji_thread_ui(skala)
    uji_skalabilitas(skala)
    uji_memori_puncak(kerja)
    uji_kebocoran()
    print(f"\nLULUS: {LULUS}   GAGAL: {GAGAL}")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
