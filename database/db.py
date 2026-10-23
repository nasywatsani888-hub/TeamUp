# database/db.py — Pengelola Koneksi & Eksekusi Native Query SQLite
# Menggunakan modul bawaan Python: sqlite3 (tanpa perlu install library tambahan)
import os
import sqlite3

# Lokasi file database: ditaruh di folder utama proyek (TeamUp/teamup.db)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "teamup.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection():
    """
    Buka koneksi ke database SQLite lokal.
    - row_factory = sqlite3.Row: agar hasil SELECT bisa diakses seperti dictionary (row['nama']),
      bukan hanya tuple indeks angka (row[0]).
    - foreign_keys = ON: agar relasi antar-tabel dan CASCADE delete berfungsi.
    - journal_mode = WAL: Write-Ahead Logging agar thread worker background bisa membaca
      tanpa terblokir saat ada thread lain menulis.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db():
    """
    Mengeksekusi file schema.sql untuk membuat semua tabel jika belum ada.
    Dipanggil otomatis saat pertama kali aplikasi / seeder dijalankan.
    """
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"File skema tidak ditemukan di {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()


def query_all(sql, params=()):
    """Jalankan SELECT dan kembalikan semua baris sebagai list of dict."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def query_one(sql, params=()):
    """Jalankan SELECT dan kembalikan 1 baris sebagai dict (atau None jika tidak ditemukan)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute_commit(sql, params=()):
    """Jalankan perintah INSERT, UPDATE, atau DELETE, lalu simpan perubahan (commit).
    Mengembalikan id baris terakhir yang di-insert (lastrowid)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
