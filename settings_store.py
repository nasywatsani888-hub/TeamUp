# settings_store.py — Konfigurasi aplikasi TeamUp yang tersimpan di file JSON (Pertemuan 11)
#
# Bedanya dengan config.py:
#   config.py       = konstanta yang ditulis programmer (warna, batas ukuran file). Tidak berubah saat aplikasi jalan.
#   settings_store  = pengaturan yang berubah saat dipakai user (email terakhir, ukuran jendela, dsb.)
#                     dan harus DIINGAT walau aplikasi ditutup.
#
# Hanya memakai modul bawaan Python: json, os, threading.
import json
import os
import threading
import uuid

import file_storage

NAMA_FILE = "pengaturan.json"
VERSI = 1

# Nilai bawaan. Kunci yang tidak ada di file akan memakai nilai ini,
# jadi menambah pengaturan baru di versi aplikasi berikutnya tidak merusak file lama.
BAWAAN = {
    "versi": VERSI,
    "ingat_email": False,        # centang "Ingat saya" di halaman Login
    "email_terakhir": "",
    "jendela_lebar": 1320,
    "jendela_tinggi": 720,
    "jendela_maksimal": True,
}

_kunci = threading.Lock()        # worker thread dan thread UI bisa menyimpan bersamaan
_data = None                     # salinan di memori; None = belum dimuat


def lokasi_file():
    return os.path.join(file_storage.folder_jenis("konfigurasi"), NAMA_FILE)


def _tipe_cocok(nilai, contoh):
    """True kalau tipe 'nilai' sama dengan tipe nilai bawaan (bool tidak boleh dianggap angka)."""
    if isinstance(contoh, bool):
        return isinstance(nilai, bool)
    if isinstance(contoh, int):
        return isinstance(nilai, int) and not isinstance(nilai, bool)
    return isinstance(nilai, type(contoh))


def muat():
    """Baca file pengaturan ke memori. Tidak pernah melempar error:
      - file belum ada            -> pakai nilai bawaan
      - file rusak / bukan JSON   -> simpan salinannya sebagai .rusak (untuk dicek), pakai nilai bawaan
      - nilai bertipe salah       -> nilai itu diabaikan, pakai bawaan"""
    global _data
    hasil = dict(BAWAAN)
    path = lokasi_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                isi = json.load(f)
            if not isinstance(isi, dict):
                raise ValueError("isi file bukan objek JSON")
            for kunci, contoh in BAWAAN.items():
                if kunci in isi and _tipe_cocok(isi[kunci], contoh):
                    hasil[kunci] = isi[kunci]
        except (OSError, ValueError):               # json.JSONDecodeError adalah turunan ValueError
            try:
                os.replace(path, path + ".rusak")
            except OSError:
                pass
            hasil = dict(BAWAAN)
    with _kunci:
        _data = hasil
    return dict(hasil)


def simpan():
    """Tulis pengaturan ke disk secara ATOMIK (tulis .tmp lalu os.replace): kalau aplikasi mati
    atau listrik padam saat menulis, file lama tetap utuh. Mengembalikan True/False."""
    with _kunci:
        if _data is None:
            return False
        salinan = dict(_data)
    path = lokasi_file()
    sementara = f"{path}.{uuid.uuid4().hex[:6]}.tmp"      # unik -> dua thread yang menyimpan bersamaan tidak bentrok
    try:
        with open(sementara, "w", encoding="utf-8") as f:
            json.dump(salinan, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())                    # paksa isi benar-benar masuk ke disk
        os.replace(sementara, path)
        return True
    except OSError:
        if os.path.exists(sementara):
            os.remove(sementara)
        return False


def ambil(kunci):
    """Nilai satu pengaturan (otomatis memuat file saat pertama kali dipanggil)."""
    if _data is None:
        muat()
    with _kunci:
        return _data.get(kunci, BAWAAN.get(kunci))


def atur(kunci, nilai, langsung_simpan=True):
    """Ubah satu pengaturan. Kunci yang tidak dikenal atau bertipe salah ditolak (return False)."""
    if kunci not in BAWAAN or not _tipe_cocok(nilai, BAWAAN[kunci]):
        return False
    if _data is None:
        muat()
    with _kunci:
        _data[kunci] = nilai
    return simpan() if langsung_simpan else True


def atur_banyak(**pengaturan):
    """Ubah beberapa pengaturan sekaligus lalu simpan SATU kali (lebih hemat daripada simpan berkali-kali)."""
    semua_ok = all(atur(k, v, langsung_simpan=False) for k, v in pengaturan.items())
    return simpan() and semua_ok


def reset():
    """Kembalikan semua pengaturan ke nilai bawaan."""
    global _data
    with _kunci:
        _data = dict(BAWAAN)
    return simpan()
