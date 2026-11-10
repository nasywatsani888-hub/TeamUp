"""
penanganan_error.py — Global exception handling TeamUp (Pertemuan 12, tahap 4).

Tujuan:
  1. Error yang tidak tertangkap TIDAK membuat aplikasi mati.
  2. Detail teknis (traceback) dicatat ke file log, bukan ditampilkan ke user.
  3. User hanya melihat pesan ramah + kode referensi untuk dilaporkan ke admin.
  4. Data sensitif (password, OTP, token) disamarkan sebelum masuk log.

Cakupan hook:
  - sys.excepthook        -> error di main thread / slot Qt
  - threading.excepthook  -> error di thread latar belakang
  - sys.unraisablehook    -> error di __del__ / callback yang tak bisa di-raise
  - qInstallMessageHandler-> peringatan/kesalahan internal Qt (opsional)

Pemakaian (main.py):
    from penanganan_error import pasang_penanganan_global
    app = QApplication(sys.argv)
    pasang_penanganan_global(app)
"""
from __future__ import annotations

import logging
import os
import re
import sys
import threading
import traceback
import uuid
from logging.handlers import RotatingFileHandler
from functools import wraps

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "teamup_error.log")
PESAN_UMUM = "Terjadi kesalahan tak terduga. Aplikasi tetap berjalan, silakan coba lagi."

logger = logging.getLogger("teamup")


# --------------------------------------------------------------------------
# Exception khusus aplikasi (pesan aman untuk ditampilkan ke user)
# --------------------------------------------------------------------------
class AplikasiError(Exception):
    """Error yang pesannya boleh dilihat user (mis. validasi, hak akses)."""

    def __init__(self, pesan_pengguna: str):
        super().__init__(pesan_pengguna)
        self.pesan_pengguna = pesan_pengguna


# --------------------------------------------------------------------------
# Logging + penyamaran data sensitif
# --------------------------------------------------------------------------
_POLA_SENSITIF = re.compile(
    r"""(?ix)
    (password|passwd|pwd|otp|token|secret|kode)   # nama field
    (\s*[=:]\s*|['"]\s*:\s*['"])                  # pemisah: = , : , atau "key": "
    ([^\s,'"}\)]+)                                 # nilai
    """
)


class FilterSamarkan(logging.Filter):
    """Ganti nilai field sensitif dengan *** sebelum ditulis ke log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _POLA_SENSITIF.sub(r"\1\2***", str(record.getMessage()))
        record.args = ()
        if record.exc_text:
            record.exc_text = _POLA_SENSITIF.sub(r"\1\2***", record.exc_text)
        return True


def setup_logging(log_file: str = LOG_FILE) -> logging.Logger:
    """Siapkan logger berputar (maks 1 MB x 3 file). Aman dipanggil berulang."""
    if logger.handlers:
        return logger
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(threadName)s | %(message)s")
    )
    handler.addFilter(FilterSamarkan())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


# --------------------------------------------------------------------------
# Inti penanganan
# --------------------------------------------------------------------------
_sedang_menangani = threading.local()
_penampil_dialog = None  # diisi oleh pasang_penanganan_global bila ada Qt


def _buat_kode_error() -> str:
    return uuid.uuid4().hex[:8].upper()


def catat_exception(exc_type, exc_value, exc_tb, konteks: str = "main") -> str:
    """Catat error ke log, kembalikan kode referensi."""
    kode = _buat_kode_error()
    teks = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error("[%s] konteks=%s tipe=%s\n%s", kode, konteks, exc_type.__name__, teks)
    return kode


def _pesan_untuk_user(exc_value, kode: str) -> str:
    if isinstance(exc_value, AplikasiError):
        return exc_value.pesan_pengguna
    return f"{PESAN_UMUM}\n\nKode referensi: {kode}"


def tangani_exception(exc_type, exc_value, exc_tb, konteks: str = "main") -> None:
    """Handler tunggal. TIDAK BOLEH melempar exception sendiri."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    if getattr(_sedang_menangani, "aktif", False):  # cegah rekursi
        return
    _sedang_menangani.aktif = True
    try:
        kode = catat_exception(exc_type, exc_value, exc_tb, konteks)
        pesan = _pesan_untuk_user(exc_value, kode)
        if _penampil_dialog is not None:
            _penampil_dialog(pesan)
        else:
            print(pesan, file=sys.stderr)
    except Exception:  # handler gagal -> jatuh ke hook bawaan, jangan crash
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass
    finally:
        _sedang_menangani.aktif = False


def _hook_main(exc_type, exc_value, exc_tb):
    tangani_exception(exc_type, exc_value, exc_tb, "main")


def _hook_thread(args: threading.ExceptHookArgs):
    if args.exc_type is SystemExit:
        return
    nama = args.thread.name if args.thread else "unknown"
    tangani_exception(args.exc_type, args.exc_value, args.exc_traceback, f"thread:{nama}")


def _hook_unraisable(unraisable):
    logger.error(
        "[unraisable] %s | obj=%r\n%s",
        unraisable.err_msg or "",
        unraisable.object,
        "".join(
            traceback.format_exception(
                unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback
            )
        ),
    )


# --------------------------------------------------------------------------
# Integrasi Qt (PySide6) — import malas agar modul tetap bisa dites tanpa GUI
# --------------------------------------------------------------------------
def _siapkan_dialog_qt(app) -> None:
    """Dialog harus muncul di main thread; signal Qt otomatis antre lintas thread."""
    global _penampil_dialog
    from PySide6.QtCore import QObject, Signal, Slot
    from PySide6.QtWidgets import QMessageBox

    class _Penyampai(QObject):
        tampil = Signal(str)

        def __init__(self):
            super().__init__()
            self.tampil.connect(self._tampil_dialog)

        @Slot(str)
        def _tampil_dialog(self, pesan: str):
            kotak = QMessageBox()
            kotak.setIcon(QMessageBox.Warning)
            kotak.setWindowTitle("TeamUp")
            kotak.setText(pesan)
            kotak.exec()

    penyampai = _Penyampai()
    penyampai.moveToThread(app.thread())
    app._penyampai_error = penyampai  # cegah garbage collection
    _penampil_dialog = penyampai.tampil.emit


def _pasang_handler_pesan_qt() -> None:
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    peta = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(tipe, konteks, pesan):
        logger.log(peta.get(tipe, logging.WARNING), "[Qt] %s", pesan)

    qInstallMessageHandler(handler)


def pasang_penanganan_global(app=None, tampil_dialog: bool = True) -> logging.Logger:
    """Pasang semua hook. Panggil sekali di main.py, setelah QApplication dibuat."""
    setup_logging()
    sys.excepthook = _hook_main
    threading.excepthook = _hook_thread
    sys.unraisablehook = _hook_unraisable
    if app is not None:
        try:
            _pasang_handler_pesan_qt()
            if tampil_dialog:
                _siapkan_dialog_qt(app)
        except ImportError:
            logger.warning("PySide6 tidak tersedia; dialog error dinonaktifkan.")
    logger.info("Penanganan error global aktif.")
    return logger


# --------------------------------------------------------------------------
# Dekorator opsional untuk slot/handler yang ingin penanganan lokal
# --------------------------------------------------------------------------
def aman(fungsi=None, *, nilai_gagal=None):
    """Bungkus slot: error dicatat & dilaporkan, aplikasi lanjut, return nilai_gagal."""

    def pembungkus(f):
        @wraps(f)
        def dalam(*a, **kw):
            try:
                return f(*a, **kw)
            except Exception:
                tangani_exception(*sys.exc_info(), konteks=f"slot:{f.__name__}")
                return nilai_gagal

        return dalam

    return pembungkus(fungsi) if fungsi else pembungkus
