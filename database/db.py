# database/db.py — Pengelola Koneksi & Eksekusi Native Query SQLite
# Menggunakan modul bawaan Python: sqlite3 (tanpa perlu install library tambahan)
#
# Perubahan (Pertemuan 9-10):
#   * koneksi() SELALU menutup koneksi. Di sqlite3, `with sqlite3.connect(...)` hanya commit / rollback dan
#     TIDAK menutup koneksi -> koneksi menumpuk sampai GC (kebocoran sumber daya, topik Pertemuan 6).
#   * Skema diberi nomor versi (PRAGMA user_version) supaya perubahan skema bisa dimigrasi dengan aman.
#   * Lokasi database bisa diganti (env TEAMUP_DB / gunakan_database) -> uji otomatis tidak menyentuh teamup.db.
import os
import shutil
import sqlite3
from contextlib import contextmanager

# Lokasi file database: ditaruh di folder utama proyek (TeamUp/teamup.db)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("TEAMUP_DB") or os.path.join(BASE_DIR, "teamup.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
SKEMA_VERSI = 2   # naikkan setiap kali schema.sql berubah


def gunakan_database(path):
    """Ganti file database yang dipakai (dipakai uji otomatis agar tidak menyentuh teamup.db)."""
    global DB_PATH
    DB_PATH = path


def get_connection():
    """
    Buka koneksi ke database SQLite lokal.
    - row_factory = sqlite3.Row: hasil SELECT bisa diakses seperti dictionary (row['nama']).
    - foreign_keys = ON: agar relasi antar-tabel dan CASCADE delete berfungsi (SQLite mematikannya secara bawaan!).
    - journal_mode = WAL: Write-Ahead Logging agar thread worker membaca tanpa terblokir saat ada yang menulis.
    - busy_timeout: kalau database sedang dikunci proses lain, tunggu sampai 5 detik, bukan langsung error.
    Catatan: koneksi dari fungsi ini HARUS ditutup pemanggil. Lebih aman pakai `with koneksi() as conn`.
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def koneksi():
    """Satu koneksi = satu transaksi: commit bila sukses, rollback bila ada error, dan SELALU ditutup."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def versi_skema():
    """Nomor versi skema pada file database saat ini (0 = baru / belum pernah diinisialisasi)."""
    with koneksi() as conn:
        return conn.execute("PRAGMA user_version;").fetchone()[0]


def _jumlah_tabel(conn):
    return conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchone()[0]


def init_db():
    """
    Menyiapkan database. Mengembalikan 'dibuat', 'terbaru', atau 'dimigrasi'.
      - database baru            -> buat semua tabel, tandai versi terbaru.
      - versi sudah terbaru      -> tidak melakukan apa-apa.
      - versi lebih lama         -> cadangkan file lama (teamup.db.vN.bak), lalu bangun ulang skema.
        (Strategi sederhana ini cukup karena aplikasi versi lama belum pernah menulis ke database. Untuk data
        nyata, gunakan migrasi bertahap dengan ALTER TABLE per versi.)
    """
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"File skema tidak ditemukan di {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with koneksi() as conn:
        versi = conn.execute("PRAGMA user_version;").fetchone()[0]
        ada_tabel = _jumlah_tabel(conn)

    hasil = "dibuat"
    if ada_tabel and versi == SKEMA_VERSI:
        return "terbaru"
    if ada_tabel and versi < SKEMA_VERSI:
        shutil.copy2(DB_PATH, f"{DB_PATH}.v{versi}.bak")
        for akhiran in ("", "-wal", "-shm"):
            if os.path.exists(DB_PATH + akhiran):
                os.remove(DB_PATH + akhiran)
        hasil = "dimigrasi"

    with koneksi() as conn:
        conn.executescript(schema_sql)
        conn.execute(f"PRAGMA user_version = {SKEMA_VERSI};")   # PRAGMA tidak bisa diparameterkan; nilainya konstanta
    return hasil


def query_all(sql, params=()):
    """Jalankan SELECT dan kembalikan semua baris sebagai list of dict."""
    with koneksi() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_one(sql, params=()):
    """Jalankan SELECT dan kembalikan 1 baris sebagai dict (atau None jika tidak ditemukan)."""
    with koneksi() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute_commit(sql, params=()):
    """Jalankan INSERT / UPDATE / DELETE lalu simpan (commit). Mengembalikan lastrowid."""
    with koneksi() as conn:
        return conn.execute(sql, params).lastrowid
