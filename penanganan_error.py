# penanganan_error.py — Penanganan error global + log aman TeamUp (Pertemuan 12: Security & Error Handling)
#
# Tujuan:
#   1. Error yang tidak tertangkap TIDAK menampilkan tumpukan kode mentah ke user dan tidak diam-diam hilang.
#   2. Detail teknis (traceback) dicatat ke berkas log; user hanya melihat pesan ramah + KODE REFERENSI
#      yang bisa dilaporkan, lalu pengembang mencari kode itu di log.
#   3. Data sensitif (password, OTP, email, nomor telepon, hash, token, path pribadi) DISAMARKAN sebelum
#      masuk log. Log sering dikirim saat melapor bug, jadi tidak boleh jadi sumber kebocoran.
#   4. Dialog tidak membanjir: satu error yang terulang 60x/detik (mis. di timer) tetap hanya satu dialog.
#   5. Error "yang memang diharapkan" (aturan bisnis: bukan pemilik, status salah, data tidak valid) tampil
#      apa adanya sebagai peringatan, tanpa traceback dan tanpa dianggap crash.
#
# Hook yang dipasang (semuanya dicatat, tidak ada yang lolos diam-diam):
#   sys.excepthook        error di thread utama / slot Qt
#   threading.excepthook  error di thread latar belakang (worker Pertemuan 7)
#   sys.unraisablehook    error di __del__ / callback yang tak bisa di-raise
#   qInstallMessageHandler  peringatan & kesalahan internal Qt
#
# Cara pakai (di main.py, setelah QApplication dibuat):
#       import penanganan_error
#       penanganan_error.pasang_penanganan_global(app)
# Untuk slot / handler tombol yang ingin penanganan lokal:
#       @penanganan_error.aman
#       def handle_save(self): ...
#
# Hanya memakai modul bawaan Python (logging, re, threading, traceback, ...). PySide6 diimpor MALAS,
# jadi modul ini tetap bisa diuji tanpa GUI.
import contextlib
import functools
import inspect
import logging
import logging.handlers
import os
import re
import sys
import threading
import time
import traceback
import uuid

import file_storage

NAMA_LOG = "teamup.log"
MAKS_BYTE_LOG = 512 * 1024         # ukuran satu berkas log sebelum diputar
JUMLAH_CADANGAN_LOG = 3            # teamup.log.1 .. .3 disimpan, yang lebih tua dibuang
JEDA_DIALOG = 5.0                  # detik minimal antar dialog "kesalahan tak terduga"

PESAN_UMUM = "Terjadi kesalahan tak terduga. Silakan coba lagi."
NAMA_BISNIS = {"DataTidakValid", "AturanBisnis", "HakAksesDitolak"}     # kelas error bisnis di database/repository.py

logger = logging.getLogger("teamup")
_jam = time.monotonic              # bisa diganti untuk uji (tidak perlu menunggu sungguhan)


# ============================================================== 1. Penyamaran data sensitif
_POLA_HASH = re.compile(r"pbkdf2_sha256\$\d+\$[0-9a-fA-F]+\$[0-9a-fA-F]+")
_POLA_TOKEN = re.compile(r"enc1\$[A-Za-z0-9_\-=]+")
_POLA_HEX = re.compile(r"\b[0-9a-fA-F]{40,}\b")
_POLA_KV = re.compile(
    r"""(?i)((?:password|passwd|pwd|sandi|otp|token|secret|kunci|api[_-]?key|authorization)["']?\s*[=:]\s*["']?)"""
    r"""([^\s,;"'})\]]+)"""
)
_POLA_OTP = re.compile(r"(?i)(\botp\b[^\d\n]{0,15})(\d{4,8})\b")
_POLA_EMAIL = re.compile(r"([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
_POLA_TELEPON = re.compile(r"(?<![\w+])(?:\+62|62|0)[\s\-]?8\d{1,2}[\s\-.]?\d{3,4}[\s\-.]?\d{2,5}(?!\d)")
_POLA_HOME_UNIX = re.compile(r"(?:/Users|/home)/[^/\s\"']+")
_POLA_HOME_WIN = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"']+")


def samarkan(teks):
    """Ganti data sensitif di 'teks' dengan penanda. Contoh:
         budi@gmail.com          -> b***@gmail.com        (domain dipertahankan, berguna untuk diagnosis)
         0812-3456-7890          -> [telp-disamarkan]
         password=abc123         -> password=***
         pbkdf2_sha256$...$...   -> pbkdf2_sha256$[hash-disamarkan]
         enc1$VFVF...            -> enc1$[terenkripsi]
         /Users/mazaya/Documents -> ~/Documents
    Dipakai oleh formatter log, jadi berlaku juga untuk isi traceback."""
    teks = str(teks)
    home = os.path.expanduser("~")
    if len(home) > 1:
        teks = teks.replace(home, "~")
    teks = _POLA_HASH.sub("pbkdf2_sha256$[hash-disamarkan]", teks)
    teks = _POLA_TOKEN.sub("enc1$[terenkripsi]", teks)
    teks = _POLA_KV.sub(r"\1***", teks)
    teks = _POLA_OTP.sub(r"\1***", teks)
    teks = _POLA_HEX.sub("[hex-disamarkan]", teks)
    teks = _POLA_EMAIL.sub(r"\1***@\2", teks)
    teks = _POLA_TELEPON.sub("[telp-disamarkan]", teks)
    teks = _POLA_HOME_UNIX.sub("~", teks)
    teks = _POLA_HOME_WIN.sub("~", teks)
    return teks


class _FormatterAman(logging.Formatter):
    """Menyamarkan HASIL AKHIR pemformatan. Karena traceback (exc_info) dirender oleh formatter, penyamaran
    di sini juga mencakup traceback; penyamaran di logging.Filter tidak (filter jalan sebelum traceback dirender)."""

    def format(self, record):
        return samarkan(super().format(record))


# ============================================================== 2. Logging
def folder_log():
    return os.path.join(file_storage.folder_data(), "log")


def lokasi_log():
    return os.path.join(folder_log(), NAMA_LOG)


def setup_logging(log_file=None):
    """Siapkan logger berputar (512 KB x 3 cadangan) di folder data aplikasi (BUKAN folder project, supaya
    log yang berisi data tidak ikut ter-commit ke GitHub). Aman dipanggil berulang. Kalau folder log tidak
    bisa dibuat (izin / disk penuh), jatuh ke stderr supaya aplikasi tetap jalan."""
    if log_file is None and getattr(logger, "_teamup_siap", False):
        return logger
    lepas_logging()
    formatter = _FormatterAman("%(asctime)s | %(levelname)s | %(threadName)s | %(message)s")
    try:
        path = log_file or lokasi_log()
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=MAKS_BYTE_LOG, backupCount=JUMLAH_CADANGAN_LOG, encoding="utf-8", delay=True)
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger._teamup_siap = True
    logging.raiseExceptions = False          # kegagalan menulis log tidak boleh ikut menjatuhkan aplikasi
    return logger


def lepas_logging():
    for h in list(logger.handlers):
        try:
            h.close()
        finally:
            logger.removeHandler(h)
    logger._teamup_siap = False


def dapatkan_logger(nama):
    """Logger turunan untuk modul lain: dapatkan_logger('data_store') -> 'teamup.data_store' (ikut aturan penyamaran)."""
    setup_logging()
    return logging.getLogger("teamup." + nama)


def baca_log_terakhir(jumlah_baris=50):
    """Baris terakhir log (untuk layar bantuan / lampiran laporan bug). Kosong kalau belum ada log."""
    for h in logger.handlers:
        h.flush()
    try:
        with open(lokasi_log(), "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()[-jumlah_baris:]
    except OSError:
        return []


def catat_keamanan(peristiwa, **rincian):
    """Catat peristiwa keamanan (login gagal, akun terkunci, akses ditolak) sebagai satu baris:
         catat_keamanan("login_gagal", email=email, sisa=3)  ->  ... | WARNING | ... | KEAMANAN login_gagal email=b***@x.com sisa=3"""
    setup_logging()
    bagian = " ".join(f"{k}={v}" for k, v in rincian.items())
    logging.getLogger("teamup.keamanan").warning("KEAMANAN %s %s", peristiwa, bagian)


# ============================================================== 3. Klasifikasi & pesan untuk user
def adalah_error_bisnis(exc):
    """True untuk error yang MEMANG diharapkan & pesannya aman dibaca user (aturan bisnis, data tidak valid,
    hak akses). Dikenali lewat NAMA kelas di rantai pewarisan, jadi modul ini tidak perlu mengimpor repository."""
    if hasattr(exc, "pesan_pengguna"):
        return True
    return any(k.__name__ in NAMA_BISNIS for k in type(exc).__mro__)


def pesan_untuk_user(exc, kode):
    """Teks yang boleh dilihat user. Detail teknis TIDAK pernah ikut (alamat server, nama tabel, path, dsb.)."""
    if hasattr(exc, "pesan_pengguna"):
        return str(exc.pesan_pengguna)
    if adalah_error_bisnis(exc):
        return str(exc)
    nama = {k.__name__ for k in type(exc).__mro__}
    if "DataRusak" in nama:
        isi = "Data tersimpan tidak dapat dibuka (rusak atau kunci tidak cocok)."
    elif isinstance(exc, PermissionError):
        isi = "Aplikasi tidak memiliki izin untuk mengakses berkas yang dibutuhkan."
    elif isinstance(exc, FileNotFoundError):
        isi = "Berkas yang dibutuhkan tidak ditemukan."
    elif isinstance(exc, OSError) and getattr(exc, "errno", None) == 28:         # ENOSPC
        isi = "Ruang penyimpanan penuh."
    elif "OperationalError" in nama and "locked" in str(exc).lower():
        isi = "Database sedang sibuk. Coba lagi sebentar lagi."
    else:
        isi = PESAN_UMUM
    return f"{isi}\n\nKode referensi: {kode}\n(Detail teknis tersimpan di berkas log.)"


# ============================================================== 4. Inti penanganan
_lokal = threading.local()
_kunci = threading.Lock()
_penampil_dialog = None            # fungsi(pesan, bisnis) -> None; diisi oleh pasang_penanganan_global bila ada Qt
_penampil_persisten = False        # True = dialog tetap terbuka sampai ditutup user (mode Qt)
_dialog_terbuka = False
_terakhir_dialog = 0.0
_ditahan = 0                       # jumlah dialog yang ditahan sejak dialog terakhir (untuk diagnosis di log)


def _buat_kode():
    return uuid.uuid4().hex[:8].upper()


def catat_exception(exc_type, exc_value, exc_tb, konteks="main"):
    """Catat error tak terduga ke log lengkap dengan traceback (disamarkan). Mengembalikan kode referensi."""
    setup_logging()
    kode = _buat_kode()
    logger.error("[%s] konteks=%s tipe=%s", kode, konteks, exc_type.__name__, exc_info=(exc_type, exc_value, exc_tb))
    return kode


def _beritahu_user(pesan, bisnis):
    """Tampilkan pesan ke user dengan pembatas banjir. Tidak pernah melempar error."""
    global _dialog_terbuka, _terakhir_dialog, _ditahan
    with _kunci:
        sekarang = _jam()
        if _penampil_persisten and _dialog_terbuka:
            tahan = True                                       # satu dialog masih terbuka: jangan menumpuk
        elif not bisnis and sekarang - _terakhir_dialog < JEDA_DIALOG and _terakhir_dialog > 0:
            tahan = True                                       # error tak terduga yang terulang cepat
        else:
            tahan = False
        if tahan:
            _ditahan += 1
            return
        if _ditahan:
            logger.info("%d pemberitahuan error ditahan (pembatas banjir dialog)", _ditahan)
            _ditahan = 0
        if not bisnis:
            _terakhir_dialog = sekarang
        if _penampil_persisten:
            _dialog_terbuka = True
    try:
        if _penampil_dialog is not None:
            _penampil_dialog(pesan, bisnis)
        else:
            print(pesan, file=sys.stderr)
    except Exception:
        logger.exception("Gagal menampilkan dialog error")


def dialog_ditutup():
    """Dipanggil saat dialog Qt ditutup user: dialog berikutnya boleh muncul."""
    global _dialog_terbuka
    with _kunci:
        _dialog_terbuka = False


def tangani_exception(exc_type, exc_value, exc_tb, konteks="main"):
    """Pintu tunggal semua error. TIDAK BOLEH melempar error sendiri."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)         # Ctrl+C tetap menghentikan program
        return
    if getattr(_lokal, "aktif", False):                         # cegah rekursi (error di dalam penanganan error)
        return
    _lokal.aktif = True
    try:
        if adalah_error_bisnis(exc_value):
            setup_logging()
            logger.warning("[bisnis] konteks=%s tipe=%s pesan=%s", konteks, exc_type.__name__, exc_value)
            _beritahu_user(pesan_untuk_user(exc_value, ""), True)
        else:
            kode = catat_exception(exc_type, exc_value, exc_tb, konteks)
            _beritahu_user(pesan_untuk_user(exc_value, kode), False)
    except Exception:
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)     # penanganan gagal -> hook bawaan, jangan crash
        except Exception:
            pass
    finally:
        _lokal.aktif = False


def _hook_main(exc_type, exc_value, exc_tb):
    tangani_exception(exc_type, exc_value, exc_tb, "main")


def _hook_thread(args):
    if args.exc_type is SystemExit:
        return
    nama = args.thread.name if args.thread else "tidak-diketahui"
    tangani_exception(args.exc_type, args.exc_value, args.exc_traceback, f"thread:{nama}")


def _hook_unraisable(tak_terangkat):
    try:
        setup_logging()
        logger.error("[unraisable] %s | objek=%.200r", tak_terangkat.err_msg or "", tak_terangkat.object,
                     exc_info=(tak_terangkat.exc_type, tak_terangkat.exc_value, tak_terangkat.exc_traceback))
    except Exception:
        pass


# ============================================================== 5. Integrasi Qt (import malas)
jumlah_dialog_qt = 0               # berapa dialog Qt yang benar-benar ditampilkan (diagnosis & uji)


def _siapkan_dialog_qt(app):
    """Dialog harus dibuat di thread utama. Sinyal Qt otomatis diantrekan lintas thread, jadi error dari
    worker thread pun aman. Memakai open() (tidak memblokir), bukan exec() yang membuat event loop bertingkat."""
    global _penampil_dialog, _penampil_persisten
    from PySide6.QtCore import QObject, Qt, Signal, Slot
    from PySide6.QtWidgets import QMessageBox

    class _Penyampai(QObject):
        tampil = Signal(str, bool)

        def __init__(self):
            super().__init__()
            self.tampil.connect(self._tampil_dialog, Qt.QueuedConnection)
            self.kotak = None

        @Slot(str, bool)
        def _tampil_dialog(self, pesan, bisnis):
            global jumlah_dialog_qt
            kotak = QMessageBox()
            kotak.setIcon(QMessageBox.Information if bisnis else QMessageBox.Warning)
            kotak.setWindowTitle("TeamUp" if bisnis else "TeamUp — Terjadi Kesalahan")
            kotak.setText(pesan)
            kotak.setAttribute(Qt.WA_DeleteOnClose)
            kotak.finished.connect(lambda _=0: dialog_ditutup())
            self.kotak = kotak                                  # tahan referensi agar tidak dibuang pemulung memori
            jumlah_dialog_qt += 1
            kotak.open()

    penyampai = _Penyampai()
    penyampai.moveToThread(app.thread())
    app._penyampai_error = penyampai
    _penampil_dialog = lambda pesan, bisnis: penyampai.tampil.emit(pesan, bisnis)
    _penampil_persisten = True


def _pasang_handler_pesan_qt():
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    peta = {QtMsgType.QtDebugMsg: logging.DEBUG, QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
            QtMsgType.QtFatalMsg: logging.CRITICAL}

    def penangan(tipe, konteks, pesan):
        tingkat = peta.get(tipe, logging.WARNING)
        logger.log(tingkat, "[Qt] %s", pesan)
        if tingkat >= logging.ERROR:                            # kesalahan serius tetap tampil di konsol
            print(f"[Qt] {pesan}", file=sys.stderr)

    qInstallMessageHandler(penangan)


_asli = {}


def pasang_penanganan_global(app=None, tampil_dialog=True, qt_log=True):
    """Pasang semua hook. Panggil SEKALI di main.py setelah QApplication dibuat. Aman dipanggil berulang."""
    setup_logging()
    if not _asli:
        _asli.update(excepthook=sys.excepthook, threadhook=threading.excepthook, unraisable=sys.unraisablehook)
    sys.excepthook = _hook_main
    threading.excepthook = _hook_thread
    sys.unraisablehook = _hook_unraisable
    if app is not None:
        try:
            if qt_log:
                _pasang_handler_pesan_qt()
            if tampil_dialog:
                _siapkan_dialog_qt(app)
        except ImportError:
            logger.warning("PySide6 tidak tersedia; dialog error dinonaktifkan.")
    logger.info("Penanganan error global aktif.")
    return logger


def lepas_penanganan_global():
    """Kembalikan hook bawaan Python (dipakai uji otomatis agar tidak mengganggu pengujian lain)."""
    global _penampil_dialog, _penampil_persisten, _dialog_terbuka
    if _asli:
        sys.excepthook = _asli["excepthook"]
        threading.excepthook = _asli["threadhook"]
        sys.unraisablehook = _asli["unraisable"]
        _asli.clear()
    _penampil_dialog, _penampil_persisten, _dialog_terbuka = None, False, False


# ============================================================== 6. Alat bantu untuk handler & slot
def aman(fungsi=None, *, nilai_gagal=None):
    """Dekorator untuk slot / handler tombol: error dicatat & dilaporkan, aplikasi lanjut, mengembalikan nilai_gagal.
        @penanganan_error.aman
        def handle_save(self): ...
    Argumen berlebih yang dikirim Qt (mis. 'checked' dari clicked) otomatis dibuang sesuai tanda tangan fungsi."""
    def pembungkus(f):
        try:
            parameter = list(inspect.signature(f).parameters.values())
            punya_varargs = any(p.kind == p.VAR_POSITIONAL for p in parameter)
            maks_posisi = sum(1 for p in parameter if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
        except (TypeError, ValueError):
            punya_varargs, maks_posisi = True, 0

        @functools.wraps(f)
        def dalam(*a, **kw):
            if not punya_varargs:
                a = a[:maks_posisi]
            try:
                return f(*a, **kw)
            except Exception:
                tangani_exception(*sys.exc_info(), konteks=f"slot:{f.__name__}")
                return nilai_gagal
        return dalam

    return pembungkus(fungsi) if fungsi else pembungkus


@contextlib.contextmanager
def tangkap(konteks):
    """Blok pengaman: with tangkap("simpan profil"): ... -> error di dalam dicatat & dilaporkan, program lanjut."""
    try:
        yield
    except Exception:
        tangani_exception(*sys.exc_info(), konteks=konteks)
