# disk_cache.py — Cache di disk untuk hasil olahan yang mahal dibuat ulang (Pertemuan 11)
#
# Contoh di TeamUp: poster yang sudah dipotong & dibulatkan sudutnya. Tanpa cache, gambar diolah ulang
# setiap aplikasi dibuka. Dengan cache disk, hasilnya dibuat SEKALI lalu dibaca dari file.
#
# Bedanya dengan lru_cache di helpers.py (Pertemuan 6):
#   lru_cache  = cache di RAM, hilang saat aplikasi ditutup, dibatasi JUMLAH item.
#   disk_cache = cache di DISK, tetap ada setelah aplikasi ditutup, dibatasi UKURAN (MB) dan UMUR (hari).
#
# Hanya memakai modul bawaan Python: hashlib, os, time, uuid, threading.
import hashlib
import os
import threading
import time
import uuid

import file_storage

MAKS_UKURAN_MB = 50      # total cache tidak boleh melebihi ini
MAKS_UMUR_HARI = 30      # berkas yang tidak dipakai selama ini dianggap basi

_kunci_tulis = threading.Lock()


def folder():
    return file_storage.folder_jenis("cache")


# ---------- 1. Kunci cache ----------
def buat_kunci(*bagian):
    """Ubah beberapa nilai menjadi satu nama berkas unik. Contoh:
         buat_kunci(path_poster, mtime, 300, 200, 12)
    Kalau salah satu nilai berubah (poster diganti -> mtime berubah), kuncinya ikut berubah,
    sehingga cache lama otomatis tidak terpakai (tidak perlu dihapus manual)."""
    teks = "|".join(str(b) for b in bagian)
    return hashlib.sha256(teks.encode("utf-8")).hexdigest()[:32]


def lokasi(kunci, ekstensi=".png"):
    return os.path.join(folder(), kunci + ekstensi)


# ---------- 2. Ambil / simpan ----------
def ambil(kunci, ekstensi=".png"):
    """Path berkas cache kalau ada (cache hit), atau None (cache miss).
    Waktu 'terakhir dipakai' diperbarui agar berkas yang sering dipakai tidak ikut terhapus."""
    path = lokasi(kunci, ekstensi)
    if os.path.isfile(path):
        try:
            os.utime(path, None)                    # tandai "baru saja dipakai"
        except OSError:
            pass
        return path
    return None


def buat_jika_perlu(kunci, pembuat, ekstensi=".png"):
    """Kembalikan path cache. Kalau belum ada, panggil pembuat(path_sementara) untuk membuatnya.
    'pembuat' hanya perlu MENULIS berkas ke path yang diberikan. Hasilnya dipindah secara atomik, jadi
    thread lain tidak pernah membaca berkas setengah jadi. Mengembalikan None kalau pembuatan gagal."""
    path = ambil(kunci, ekstensi)
    if path:
        return path
    tujuan = lokasi(kunci, ekstensi)
    sementara = f"{tujuan}.{uuid.uuid4().hex[:6]}.tmp"      # unik per pemanggil -> dua thread tidak bentrok
    try:
        pembuat(sementara)
        if not os.path.isfile(sementara):
            return None
        os.replace(sementara, tujuan)
        return tujuan
    except Exception:
        return None
    finally:
        if os.path.exists(sementara):
            os.remove(sementara)


# ---------- 3. Pembersihan ----------
def _daftar_berkas():
    """[(path, ukuran, waktu_terakhir_dipakai), ...] untuk semua berkas cache yang sudah jadi."""
    hasil = []
    for nama in os.listdir(folder()):
        path = os.path.join(folder(), nama)
        if nama.endswith(".tmp") or not os.path.isfile(path):
            continue
        try:
            info = os.stat(path)
            hasil.append((path, info.st_size, info.st_mtime))
        except OSError:
            pass
    return hasil


def bersihkan(maks_mb=MAKS_UKURAN_MB, maks_hari=MAKS_UMUR_HARI):
    """Buang cache yang basi lalu, kalau masih kebesaran, buang yang paling lama tidak dipakai
    (strategi LRU: Least Recently Used). Mengembalikan jumlah berkas yang dihapus."""
    with _kunci_tulis:
        dihapus = 0
        batas_umur = time.time() - maks_hari * 86400
        sisa = []
        for path, ukuran, waktu in _daftar_berkas():
            if waktu < batas_umur and _hapus(path):
                dihapus += 1
            else:
                sisa.append((path, ukuran, waktu))
        total = sum(u for _, u, _ in sisa)
        for path, ukuran, _ in sorted(sisa, key=lambda b: b[2]):    # yang terlama dipakai dulu
            if total <= maks_mb * 1024 * 1024:
                break
            if _hapus(path):
                total -= ukuran
                dihapus += 1
        return dihapus


def _hapus(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def kosongkan():
    """Hapus seluruh cache (dipanggil dari tombol 'Bersihkan cache' atau saat logout). Mengembalikan jumlahnya."""
    with _kunci_tulis:
        jumlah = 0
        for nama in os.listdir(folder()):
            if _hapus(os.path.join(folder(), nama)):
                jumlah += 1
        return jumlah


def statistik():
    """(jumlah_berkas, total_byte) untuk ditampilkan di halaman pengaturan / saat demo."""
    daftar = _daftar_berkas()
    return len(daftar), sum(u for _, u, _ in daftar)
