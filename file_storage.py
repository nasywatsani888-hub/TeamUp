# file_storage.py — Penyimpanan file lokal TeamUp (Pertemuan 11: File System & Local Storage)
#
# Masalah sebelumnya: berkas unggahan user (poster, dokumen, foto) disimpan di dalam folder project
# (assets/postingan, assets/foto). Akibatnya:
#   * data user tercampur dengan kode program (ikut terhapus saat project di-update / di-clone ulang),
#   * kalau aplikasi dipasang di folder "Program Files", folder itu sering READ-ONLY -> gagal menyimpan.
#
# Solusi: semua data milik user disimpan di folder data aplikasi per-sistem-operasi:
#   Windows : C:\Users\<nama>\AppData\Roaming\TeamUp
#   macOS   : ~/Library/Application Support/TeamUp
#   Linux   : ~/.local/share/TeamUp
# Hanya memakai modul bawaan Python (os, shutil, uuid, re, sys).
import os
import re
import shutil
import sys
import uuid

APP_FOLDER = "TeamUp"

# Jenis berkas -> nama subfolder di dalam folder data aplikasi
JENIS_FOLDER = {
    "poster": os.path.join("unggahan", "poster"),
    "dokumen": os.path.join("unggahan", "dokumen"),
    "foto": os.path.join("unggahan", "foto"),
    "cache": "cache",
    "konfigurasi": "konfigurasi",
    "cadangan": "cadangan",
}


# ---------- 1. Lokasi folder ----------
def folder_data():
    """Folder data aplikasi sesuai sistem operasi. Env TEAMUP_DATA boleh dipakai untuk menggantinya
    (dipakai uji otomatis agar tidak menyentuh data asli)."""
    ganti = os.environ.get("TEAMUP_DATA")
    if ganti:
        return ganti
    if sys.platform.startswith("win"):
        dasar = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        dasar = os.path.expanduser("~/Library/Application Support")
    else:
        dasar = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(dasar, APP_FOLDER)


def folder_jenis(jenis):
    """Folder untuk satu jenis berkas; dibuat otomatis kalau belum ada."""
    if jenis not in JENIS_FOLDER:
        raise ValueError(f"Jenis berkas tidak dikenal: {jenis}")
    folder = os.path.join(folder_data(), JENIS_FOLDER[jenis])
    os.makedirs(folder, exist_ok=True)
    return folder


def siapkan_folder():
    """Buat semua subfolder sekali saat aplikasi dimulai. Mengembalikan folder data."""
    for jenis in JENIS_FOLDER:
        folder_jenis(jenis)
    return folder_data()


# ---------- 2. Validasi berkas (dipakai ulang oleh semua form upload) ----------
def periksa_berkas(path, ekstensi, maks_mb):
    """Periksa berkas yang dipilih user. Mengembalikan (True, "") atau (False, "pesan error")."""
    if not path or not os.path.isfile(path):
        return False, "Berkas tidak ditemukan."
    if os.path.splitext(path)[1].lower() not in ekstensi:
        daftar = ", ".join(e.lstrip(".").upper() for e in ekstensi)
        return False, f"Format berkas harus {daftar}."
    ukuran = os.path.getsize(path)
    if ukuran == 0:
        return False, "Berkas kosong."
    if ukuran > maks_mb * 1024 * 1024:
        return False, f"Ukuran berkas maksimal {maks_mb} MB."
    return True, ""


def cukup_ruang(folder, butuh_byte):
    """True kalau disk tempat 'folder' berada masih punya ruang kosong (+ cadangan 10 MB)."""
    kosong = shutil.disk_usage(folder).free
    return kosong > butuh_byte + 10 * 1024 * 1024


# ---------- 3. Nama berkas yang aman ----------
def nama_aman(nama):
    """Bersihkan nama berkas dari user: buang path (../../), karakter aneh, dan batasi panjangnya.
    Contoh: '../../etc/passwd' -> 'passwd',  'Poster Lomba #1.pdf' -> 'Poster_Lomba_1.pdf'."""
    nama = os.path.basename(str(nama).replace("\\", "/"))
    dasar, ekstensi = os.path.splitext(nama)
    dasar = re.sub(r"[^A-Za-z0-9_-]+", "_", dasar).strip("_") or "berkas"
    ekstensi = re.sub(r"[^A-Za-z0-9.]", "", ekstensi).lower()
    return dasar[:60] + ekstensi[:10]


def path_berkas(jenis, nama):
    """Lokasi lengkap berkas tersimpan. Menolak nama yang mencoba keluar dari folder (path traversal)."""
    folder = os.path.abspath(folder_jenis(jenis))
    path = os.path.abspath(os.path.join(folder, nama))
    if os.path.dirname(path) != folder:
        raise ValueError("Nama berkas tidak valid.")
    return path


# ---------- 4. Simpan / hapus ----------
def simpan_berkas(sumber, jenis, nama_tujuan=None):
    """Salin berkas pilihan user ke folder data aplikasi. Mengembalikan NAMA berkas tersimpan
    (hanya nama, bukan path penuh -> database tetap valid walau folder data dipindah).

    Penyalinan ATOMIK: ditulis dulu ke berkas .tmp lalu os.replace() -> tidak pernah ada berkas
    setengah jadi di folder tujuan walau aplikasi mati di tengah proses."""
    nama = nama_aman(nama_tujuan or os.path.basename(sumber))
    nama = f"{uuid.uuid4().hex[:8]}_{nama}"          # awalan acak -> dua berkas bernama sama tidak saling timpa
    tujuan = path_berkas(jenis, nama)
    if not cukup_ruang(os.path.dirname(tujuan), os.path.getsize(sumber)):
        raise OSError("Ruang penyimpanan tidak cukup.")
    sementara = tujuan + ".tmp"
    try:
        shutil.copyfile(sumber, sementara)
        os.replace(sementara, tujuan)
    finally:
        if os.path.exists(sementara):               # gagal di tengah jalan -> bersihkan sisa
            os.remove(sementara)
    return nama


def hapus_berkas(jenis, nama):
    """Hapus satu berkas. True kalau berhasil, False kalau memang tidak ada / tidak bisa dihapus."""
    try:
        os.remove(path_berkas(jenis, nama))
        return True
    except (OSError, ValueError):
        return False


def berkas_ada(jenis, nama):
    try:
        return bool(nama) and os.path.isfile(path_berkas(jenis, nama))
    except ValueError:
        return False


# ---------- 5. Informasi penyimpanan ----------
def ukuran_folder(folder):
    """Total ukuran (byte) semua berkas di dalam folder, termasuk subfolder."""
    total = 0
    for induk, _subfolder, daftar in os.walk(folder):
        for nama in daftar:
            try:
                total += os.path.getsize(os.path.join(induk, nama))
            except OSError:
                pass                                 # berkas hilang di tengah penghitungan -> lewati
    return total


def format_ukuran(byte):
    """1536 -> '1.5 KB'."""
    for satuan in ("B", "KB", "MB", "GB"):
        if byte < 1024 or satuan == "GB":
            return f"{byte:.0f} {satuan}" if satuan == "B" else f"{byte:.1f} {satuan}"
        byte /= 1024
