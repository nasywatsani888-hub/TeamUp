# tes_penanganan_error.py — Uji otomatis Pertemuan 12 (tahap 4): penanganan error global & log aman
#
# Yang diuji:
#   1. samarkan()        : data sensitif di log (password, OTP, email, telepon, hash, token, path pribadi)
#   2. logging           : lokasi di folder data aplikasi, traceback ikut disamarkan, rotasi, cadangan ke stderr, multi-thread
#   3. pesan untuk user  : error bisnis tampil apa adanya, error teknis tidak membocorkan detail
#   4. hook global       : sys / threading / unraisable, anti-rekursi, Ctrl+C tidak ditelan, dipasang & dilepas bersih
#   5. pembatas banjir   : 30 error beruntun -> 1 dialog (jam palsu, tidak perlu menunggu sungguhan)
#   6. Qt (offscreen)    : dialog sungguhan, error dari worker thread, penutupan dialog, dekorator aman pada tombol
#
# TERISOLASI: memakai folder data sementara. Berjalan dengan:  python3 tes_penanganan_error.py   (tanpa pytest)
import gc
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import threading

TEMP = tempfile.mkdtemp(prefix="teamup_tes_err_")
os.environ["TEAMUP_DATA"] = os.path.join(TEMP, "data")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import penanganan_error as pe

LULUS = 0
GAGAL = 0


def cek(nama, kondisi):
    global LULUS, GAGAL
    if kondisi:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}")


def isi_log():
    for h in pe.logger.handlers:
        h.flush()
    try:
        with open(pe.lokasi_log(), "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def jam_palsu():
    waktu = [1000.0]
    pe._jam = lambda: waktu[0]
    return lambda detik: waktu.__setitem__(0, waktu[0] + detik)


def reset_banjir():
    pe._terakhir_dialog = 0.0
    pe._ditahan = 0
    pe._dialog_terbuka = False


def buat_error(tipe=RuntimeError, pesan="boom"):
    try:
        raise tipe(pesan)
    except Exception:
        return sys.exc_info()


# ============================================================= 1. Penyamaran
def uji_samarkan():
    print("\n1. samarkan() — data sensitif tidak boleh masuk log")
    s = pe.samarkan
    cek("email: huruf pertama + domain dipertahankan", s("login budi.santoso@gmail.com") == "login b***@gmail.com")
    for nomor in ("0812-3456-7890", "081234567824", "+62 812 3456 7824", "628123456789", "0812 3456 7824"):
        cek(f"telepon disamarkan: {nomor}", s(f"hubungi {nomor} segera") == "hubungi [telp-disamarkan] segera")
    cek("password=...", s("gagal password=Rahasia123 lagi") == "gagal password=*** lagi")
    cek('JSON "password": "..."', s('{"password": "abc123", "nama": "Budi"}') == '{"password": "***", "nama": "Budi"}')
    cek("sandi, token, secret, kunci, api_key", all(
        "rahasia" not in s(f"{k}=rahasia") for k in ("sandi", "token", "secret", "kunci", "api_key", "api-key")))
    cek("otp: 456789", s("otp: 456789") == "otp: ***")
    cek("kode OTP 1234 (tanpa tanda baca)", s("kode OTP 1234 salah") == "kode OTP *** salah")
    hash_pw = "pbkdf2_sha256$120000$8a2dbbf561c747afbeaa54fca0a1fd14$2a1c380ce26a5d26c2f561e1abfed5e5e06ed0f47e630ec7cbe06c98d673b2c6"
    cek("hash password PBKDF2", "8a2dbbf5" not in s(f"row hash={hash_pw}") and "[hash-disamarkan]" in s(hash_pw))
    cek("token terenkripsi enc1$...", s("kontak enc1$VFVFMR_6uNXO4nr=") == "kontak enc1$[terenkripsi]")
    cek("hex panjang (>= 40 karakter)", "[hex-disamarkan]" in s("kunci " + "ab12" * 12) or "***" in s("kunci " + "ab12" * 12))
    cek("path macOS", s("File /Users/mazaya/Documents/TeamUp/main.py") == "File ~/Documents/TeamUp/main.py")
    cek("path Windows", s(r"File C:\Users\Mazaya\Documents\x.py") == r"File ~\Documents\x.py")
    cek("path Linux", s("File /home/budi/proyek/x.py") == "File ~/proyek/x.py")
    for aman_teks in ("2026-11-10 04:36:21,196 | INFO | MainThread | mulai", "port 8080 id=12345 versi 6.12.0", "ukuran 6291456 byte"):
        cek(f"teks biasa tidak berubah: {aman_teks[:30]}", s(aman_teks) == aman_teks)
    campur = "u=a@b.com hp 0812-3456-7890 password=x /Users/z/f otp 1234"
    cek("idempoten (disamarkan dua kali = sama)", s(s(campur)) == s(campur))
    cek("masukan bukan str tidak error", s(None) == "None" and s(12345) == "12345")


# ============================================================= 2. Logging
def uji_logging():
    print("\n2. Logging — lokasi, traceback, rotasi, cadangan")
    pe.lepas_logging()
    pe.setup_logging()
    cek("log di folder data aplikasi (bukan folder project)",
        pe.lokasi_log().startswith(os.environ["TEAMUP_DATA"]) and not pe.lokasi_log().startswith(BASE_DIR))
    pe.logger.info("tes awal")
    cek("berkas log dibuat setelah ada isi", os.path.isfile(pe.lokasi_log()))
    cek("setup_logging() dua kali: tidak menambah handler", len(pe.setup_logging().handlers) == 1 and len(pe.setup_logging().handlers) == 1)

    try:
        raise ValueError("kontak 0812-3456-7890 email siti@kampus.ac.id password=abc")
    except ValueError:
        pe.logger.error("gagal simpan", exc_info=True)
    teks = isi_log()
    cek("traceback tercatat lengkap", "Traceback (most recent call last)" in teks and "ValueError" in teks)
    cek("TRACEBACK lewat exc_info ikut disamarkan (email, telepon, password)",
        "siti@kampus" not in teks and "0812-3456" not in teks and "password=abc" not in teks)

    pe.catat_keamanan("login_gagal", email="budi@x.com", sisa=3)
    teks = isi_log()
    cek("catat_keamanan: tercatat & email disamarkan", "KEAMANAN login_gagal email=b***@x.com sisa=3" in teks)
    cek("baca_log_terakhir(2): paling banyak 2 baris, baris terakhir = peristiwa terakhir",
        len(pe.baca_log_terakhir(2)) <= 2 and "login_gagal" in pe.baca_log_terakhir(1)[0])
    cek("dapatkan_logger: ikut aturan penyamaran", (pe.dapatkan_logger("uji").warning("hp 081234567824"), "081234567824" not in isi_log())[1])

    hasil = []
    def tulis(i):
        for j in range(50):
            pe.logger.info("thread-%d baris-%d", i, j)
        hasil.append(i)
    ts = [threading.Thread(target=tulis, args=(i,)) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    teks = isi_log()
    cek("8 thread x 50 baris: semua 400 baris utuh", sum(1 for i in range(8) for j in range(50) if f"thread-{i} baris-{j}\n" in teks) == 400)

    lama = (pe.MAKS_BYTE_LOG, pe.JUMLAH_CADANGAN_LOG)
    pe.MAKS_BYTE_LOG, pe.JUMLAH_CADANGAN_LOG = 2000, 2
    jalur = os.path.join(TEMP, "putar", "putar.log")
    pe.setup_logging(jalur)
    for i in range(200):
        pe.logger.info("baris putar nomor %03d %s", i, "x" * 80)
    for h in pe.logger.handlers:
        h.flush()
    daftar = sorted(os.listdir(os.path.dirname(jalur)))
    cek("rotasi: berkas diputar, cadangan dibatasi 2", daftar == ["putar.log", "putar.log.1", "putar.log.2"])
    cek("rotasi: berkas aktif tidak melewati batas besar", os.path.getsize(jalur) <= 2000 + 200)
    pe.MAKS_BYTE_LOG, pe.JUMLAH_CADANGAN_LOG = lama

    berkas_biasa = os.path.join(TEMP, "bukan_folder")
    open(berkas_biasa, "w").close()
    pe.setup_logging(os.path.join(berkas_biasa, "sub", "x.log"))          # tidak mungkin dibuat
    cek("folder log tidak bisa dibuat: jatuh ke stderr, tidak crash",
        any(type(h) is logging.StreamHandler for h in pe.logger.handlers))
    pe.logger.error("tetap aman walau tanpa berkas")
    cek("menulis log tanpa berkas tidak melempar error", True)
    pe.lepas_logging()
    pe.setup_logging()


# ============================================================= 3. Pesan untuk user
def uji_pesan():
    print("\n3. Pesan untuk user")
    from database import repository
    from enkripsi import DataRusak
    p = pe.pesan_untuk_user
    umum = p(RuntimeError("koneksi DB ke 10.0.0.5 tabel users gagal di /Users/mazaya/x.py"), "ABC12345")
    cek("error teknis: tidak membocorkan detail (IP, tabel, path)",
        "10.0.0.5" not in umum and "users" not in umum and "/Users" not in umum)
    cek("error teknis: memuat kode referensi", "ABC12345" in umum and "log" in umum)
    cek("HakAksesDitolak tampil apa adanya, tanpa kode",
        p(repository.HakAksesDitolak("Hanya pemilik yang dapat memperbarui postingan ini"), "") == "Hanya pemilik yang dapat memperbarui postingan ini")
    cek("AturanBisnis & DataTidakValid dikenali sebagai error bisnis",
        pe.adalah_error_bisnis(repository.AturanBisnis("x")) and pe.adalah_error_bisnis(repository.DataTidakValid("x")))
    cek("error teknis BUKAN error bisnis", not pe.adalah_error_bisnis(RuntimeError("x")) and not pe.adalah_error_bisnis(KeyError("x")))

    class DenganPesan(Exception):
        pesan_pengguna = "Isi nama terlebih dahulu."
    cek("objek dengan atribut pesan_pengguna dipakai apa adanya", p(DenganPesan("detail teknis"), "") == "Isi nama terlebih dahulu.")
    cek("DataRusak: pesan khusus", "rusak" in p(DataRusak("tag tidak cocok"), "K1"))
    cek("PermissionError: pesan izin", "izin" in p(PermissionError("denied /Users/x"), "K1") and "/Users" not in p(PermissionError("denied /Users/x"), "K1"))
    cek("FileNotFoundError: pesan berkas", "tidak ditemukan" in p(FileNotFoundError("x"), "K1"))
    cek("disk penuh (errno 28): pesan ruang", "Ruang penyimpanan" in p(OSError(28, "No space left"), "K1"))
    cek("database terkunci: pesan sibuk", "sibuk" in p(sqlite3.OperationalError("database is locked"), "K1"))
    cek("OperationalError lain: pesan umum", pe.PESAN_UMUM in p(sqlite3.OperationalError("no such table: users"), "K1")
        and "users" not in p(sqlite3.OperationalError("no such table: users"), "K1"))


# ============================================================= 4. Hook global
def uji_hook():
    print("\n4. Hook global & penanganan inti")
    from database import repository
    asli = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    pe.lepas_penanganan_global()
    pe._penampil_dialog = None
    dialog = []
    pe._penampil_dialog = lambda pesan, bisnis: dialog.append((pesan, bisnis))
    reset_banjir()
    jam_palsu()

    pe.tangani_exception(*buat_error(ZeroDivisionError, "pembagian nol token=token123"))
    teks = isi_log()
    cek("error tak terduga: tercatat dengan kode, tipe, dan traceback",
        "ZeroDivisionError" in teks and "konteks=main" in teks and "Traceback" in teks)
    cek("error tak terduga: nilai sensitif di pesan error disamarkan", "token123" not in teks)
    kode = dialog[-1][0].split("Kode referensi: ")[1].split("\n")[0]
    cek("kode referensi di dialog sama dengan kode di log", f"[{kode}]" in teks and len(kode) == 8)
    cek("dialog untuk error teknis bertanda bukan-bisnis", dialog[-1][1] is False)

    sebelum = isi_log().count("ERROR")
    pe.tangani_exception(*buat_error(repository.HakAksesDitolak, "Notifikasi bukan milik Anda."))
    teks = isi_log()
    cek("error bisnis: dicatat sebagai WARNING satu baris, bukan ERROR/traceback",
        "[bisnis]" in teks and "Notifikasi bukan milik Anda." in teks and teks.count("ERROR") == sebelum)
    cek("error bisnis: dialog berisi pesannya apa adanya", dialog[-1] == ("Notifikasi bukan milik Anda.", True))

    jumlah = len(dialog)
    pe._penampil_dialog = lambda pesan, bisnis: (_ for _ in ()).throw(RuntimeError("dialog gagal"))
    reset_banjir()
    try:
        pe.tangani_exception(*buat_error(KeyError, "x"))
        aman = True
    except Exception:
        aman = False
    cek("dialog yang error tidak melempar & dicatat", aman and "Gagal menampilkan dialog error" in isi_log())

    panggilan = []
    def dialog_reentran(pesan, bisnis):
        panggilan.append(1)
        pe.tangani_exception(*buat_error(RuntimeError, "error di dalam penanganan"))
    pe._penampil_dialog = dialog_reentran
    reset_banjir()
    pe.tangani_exception(*buat_error(RuntimeError, "pertama"))
    cek("error di dalam penanganan error tidak menimbulkan rekursi", len(panggilan) == 1)

    dipanggil = []
    hook_asli = sys.__excepthook__
    sys.__excepthook__ = lambda *a: dipanggil.append(a)
    try:
        pe.tangani_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
    finally:
        sys.__excepthook__ = hook_asli
    cek("Ctrl+C (KeyboardInterrupt) diteruskan ke hook bawaan, tidak ditelan", len(dipanggil) == 1)

    pe._penampil_dialog = lambda pesan, bisnis: dialog.append((pesan, bisnis))
    pe.pasang_penanganan_global()
    cek("pasang: ketiga hook terpasang", sys.excepthook is pe._hook_main and threading.excepthook is pe._hook_thread
        and sys.unraisablehook is pe._hook_unraisable)
    pe.pasang_penanganan_global()
    cek("pasang dua kali: hook bawaan asli tetap tersimpan (bisa dikembalikan)", pe._asli["excepthook"] is asli[0])

    reset_banjir()
    def kerja():
        raise RuntimeError("gagal di latar belakang")
    t = threading.Thread(target=kerja, name="worker-uji")
    t.start(); t.join()
    teks = isi_log()
    cek("error di thread latar belakang: tercatat dengan nama thread", "thread:worker-uji" in teks and "gagal di latar belakang" in teks)

    sebelum = isi_log().count("ERROR")
    t = threading.Thread(target=lambda: sys.exit(0), name="keluar-normal")
    t.start(); t.join()
    cek("SystemExit di thread tidak dianggap error", isi_log().count("ERROR") == sebelum)

    class Pecah:
        def __del__(self):
            raise ValueError("gagal di __del__ email=a@b.com")
    objek = Pecah()
    del objek
    gc.collect()
    teks = isi_log()
    cek("error tak terangkat (unraisable) tercatat & disamarkan", "[unraisable]" in teks and "a@b.com" not in teks)

    sys.excepthook = pe._hook_main
    try:
        sys.excepthook(*buat_error(OSError, "lewat sys.excepthook"))
        cek("sys.excepthook -> masuk ke penanganan", "lewat sys.excepthook" in isi_log())
    finally:
        pass

    pe.lepas_penanganan_global()
    cek("lepas: hook bawaan Python dikembalikan", (sys.excepthook, threading.excepthook, sys.unraisablehook) == asli)

    pe._penampil_dialog = lambda pesan, bisnis: dialog.append((pesan, bisnis))
    reset_banjir()
    n = len(dialog)
    with pe.tangkap("simpan profil"):
        raise ValueError("gagal simpan")
    cek("tangkap(): error di dalam blok dicatat & program lanjut", "konteks=simpan profil" in isi_log() and len(dialog) == n + 1)
    pe._penampil_dialog = None


# ============================================================= 5. Pembatas banjir
def uji_banjir():
    print("\n5. Pembatas banjir dialog")
    dialog = []
    pe._penampil_dialog = lambda pesan, bisnis: dialog.append(bisnis)
    pe._penampil_persisten = False
    maju = jam_palsu()
    reset_banjir()
    pe.logger.info("--- awal uji banjir ---")
    for _ in range(30):
        pe.tangani_exception(*buat_error(RuntimeError, "terulang di timer"))
    cek("30 error beruntun -> hanya 1 dialog", len(dialog) == 1)
    cek("semua 30 error tetap tercatat di log (tidak ada yang hilang)", isi_log().split("--- awal uji banjir ---")[1].count("terulang di timer") >= 30)
    maju(5.1)
    pe.tangani_exception(*buat_error(RuntimeError, "setelah jeda"))
    cek("setelah jeda 5 detik dialog boleh muncul lagi", len(dialog) == 2)
    cek("jumlah yang ditahan dicatat di log", "29 pemberitahuan error ditahan" in isi_log())

    from database import repository
    dialog.clear()
    for _ in range(3):
        pe.tangani_exception(*buat_error(repository.AturanBisnis, "status salah"))
    cek("error bisnis (hasil aksi user) tidak ikut ditahan: 3 -> 3 pesan", len(dialog) == 3)

    dialog.clear()
    reset_banjir()
    pe._penampil_persisten = True
    maju(10)
    pe.tangani_exception(*buat_error(RuntimeError, "a"))
    maju(10)
    pe.tangani_exception(*buat_error(RuntimeError, "b"))
    cek("dialog masih terbuka: pesan berikutnya ditahan walau jeda sudah lewat", len(dialog) == 1)
    pe.dialog_ditutup()
    maju(10)
    pe.tangani_exception(*buat_error(RuntimeError, "c"))
    cek("setelah dialog ditutup, pesan berikutnya muncul lagi", len(dialog) == 2)
    pe._penampil_persisten = False
    pe._penampil_dialog = None
    pe._jam = __import__("time").monotonic


# ============================================================= 6. Qt
def uji_qt():
    print("\n6. Integrasi Qt (offscreen)")
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler, qWarning
    from PySide6.QtWidgets import QApplication, QPushButton, QWidget
    app = QApplication.instance() or QApplication([])
    pe.lepas_penanganan_global()
    maju = jam_palsu()
    reset_banjir()
    pe.jumlah_dialog_qt = 0
    pe.pasang_penanganan_global(app)

    for _ in range(30):
        pe.tangani_exception(*buat_error(RuntimeError, "gagal rahasia=XYZ123 di 10.0.0.5"))
    app.processEvents()
    cek("30 error di thread utama -> 1 dialog Qt sungguhan", pe.jumlah_dialog_qt == 1)
    kotak = app._penyampai_error.kotak
    cek("dialog memuat kode referensi, tanpa detail teknis", "Kode referensi:" in kotak.text()
        and "XYZ123" not in kotak.text() and "10.0.0.5" not in kotak.text())

    maju(10)
    def kerja():
        raise RuntimeError("dari worker")
    t = threading.Thread(target=kerja, name="worker-qt")
    t.start(); t.join()
    for _ in range(5):
        app.processEvents()
    cek("error dari worker thread: aman, tidak menumpuk dialog kedua (dialog pertama masih terbuka)", pe.jumlah_dialog_qt == 1)
    cek("error worker thread tetap tercatat di log", "thread:worker-qt" in isi_log())

    kotak.close()
    for _ in range(5):
        app.processEvents()
    cek("dialog ditutup: tanda 'terbuka' dibersihkan", pe._dialog_terbuka is False)
    maju(10)
    t = threading.Thread(target=kerja, name="worker-qt2")
    t.start(); t.join()
    for _ in range(5):
        app.processEvents()
    cek("error dari worker thread muncul sebagai dialog di thread utama setelah dialog lama ditutup", pe.jumlah_dialog_qt == 2)
    app._penyampai_error.kotak.close()
    app.processEvents()

    qWarning("peringatan dari qt uji")
    cek("pesan internal Qt (qWarning) masuk ke log", "[Qt] peringatan dari qt uji" in isi_log())

    class Halaman(QWidget):
        def __init__(self):
            super().__init__()
            self.hitung = 0
            self.ok, self.rusak = QPushButton("ok", self), QPushButton("rusak", self)
            self.ok.clicked.connect(self.handle_ok)
            self.rusak.clicked.connect(self.handle_rusak)

        @pe.aman
        def handle_ok(self):
            self.hitung += 1

        @pe.aman(nilai_gagal=-1)
        def handle_rusak(self):
            raise ValueError("gagal simpan password=abc")

    h = Halaman()
    h.ok.click()
    cek("@aman pada slot clicked: argumen 'checked' dari Qt dibuang, handler berjalan", h.hitung == 1)
    maju(10)
    h.rusak.click()
    cek("@aman: error di handler tombol tidak menjatuhkan aplikasi & tercatat", "konteks=slot:handle_rusak" in isi_log() and "password=abc" not in isi_log())
    cek("@aman mengembalikan nilai_gagal", h.handle_rusak() == -1)

    @pe.aman
    def satu_param(x):
        return x
    @pe.aman
    def banyak(*a):
        return a
    cek("@aman memangkas argumen berlebih sesuai tanda tangan", satu_param(1, 2, 3) == 1 and banyak(1, 2, 3) == (1, 2, 3))

    qInstallMessageHandler(None)
    pe.lepas_penanganan_global()
    pe._jam = __import__("time").monotonic
    h.deleteLater()


def main():
    print("=== UJI OTOMATIS PENANGANAN ERROR & LOG (Pertemuan 12, tahap 4) ===")
    print(f"(folder sementara: {TEMP})")
    try:
        uji_samarkan()
        uji_logging()
        uji_pesan()
        uji_hook()
        uji_banjir()
        uji_qt()
    finally:
        pe.lepas_penanganan_global()
        pe.lepas_logging()
        shutil.rmtree(TEMP, ignore_errors=True)
    print(f"\nLULUS: {LULUS}   GAGAL: {GAGAL}")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
