# enkripsi.py — Enkripsi data sensitif TeamUp (Pertemuan 11)
#
# Apa yang dilindungi?  Data yang tidak boleh terbaca kalau file disalin orang lain, tetapi HARUS bisa
# dibaca lagi oleh aplikasi:  kontak penyelenggara lomba dan dokumen pendukung.
#
# Hash vs enkripsi:
#   hash (sandi.py, untuk password) = SATU ARAH, tidak bisa dikembalikan. Cukup untuk dicocokkan.
#   enkripsi (file ini)             = DUA ARAH, bisa dikembalikan jika punya KUNCI.
#
# Cara kerja (hanya modul bawaan Python: hmac, hashlib, secrets, base64):
#   1. Kunci utama 32 byte diacak SEKALI, disimpan di folder konfigurasi (BUKAN di teamup.db).
#      Jadi orang yang hanya menyalin teamup.db tidak ikut mendapat kuncinya.
#   2. Setiap data diberi nonce acak 16 byte -> data yang sama menghasilkan hasil berbeda tiap kali.
#   3. Pengacakan: keystream = HMAC-SHA256(kunci_enkripsi, nonce + nomor_blok), lalu di-XOR dengan data.
#   4. Keaslian: tag HMAC-SHA256(kunci_mac, header + data_terenkripsi) di akhir.
#      Kalau data diubah 1 bit saja, atau kuncinya salah, dekripsi DITOLAK (bukan menghasilkan sampah).
#      Urutan ini disebut "encrypt-then-MAC".
#
# CATATAN JUJUR: ini dibuat agar alurnya mudah dipelajari dan tanpa library tambahan (sesuai ketentuan
# proyek). Untuk produk sungguhan gunakan library teruji, mis. cryptography (Fernet / AES-GCM).
import base64
import hashlib
import hmac
import io
import os
import secrets
import threading
import uuid

import file_storage

MAGIC = b"TUE1"          # penanda format + versi (TeamUp Encrypted v1)
UKURAN_NONCE = 16
UKURAN_TAG = 32
UKURAN_BLOK = 32         # satu keluaran HMAC-SHA256 = 32 byte
POTONGAN = 1024 * 1024   # berkas diproses per 1 MB (kelipatan 32) agar RAM tetap kecil
AWALAN_TEKS = "enc1$"    # penanda teks terenkripsi di database

_kunci_lock = threading.Lock()
_kunci_utama = None


class DataRusak(Exception):
    """Data diubah orang lain, rusak, atau kunci yang dipakai salah."""


# ---------- 1. Kunci ----------
def lokasi_kunci():
    return os.path.join(file_storage.folder_jenis("konfigurasi"), "kunci.key")


def muat_kunci():
    """Kunci utama 32 byte. Dibuat otomatis saat pertama kali dipakai, lalu dibaca dari berkas."""
    global _kunci_utama
    with _kunci_lock:
        if _kunci_utama is not None:
            return _kunci_utama
        path = lokasi_kunci()
        if os.path.isfile(path):
            with open(path, "rb") as f:
                kunci = f.read()
            if len(kunci) != 32:
                raise DataRusak("Berkas kunci rusak. Jangan dihapus jika sudah ada data terenkripsi!")
        else:
            kunci = secrets.token_bytes(32)             # pengacak aman (bukan random biasa)
            sementara = path + ".tmp"
            fd = os.open(sementara, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # hanya pemilik yang boleh baca
            with os.fdopen(fd, "wb") as f:
                f.write(kunci)
            os.replace(sementara, path)
        _kunci_utama = kunci
        return kunci


def gunakan_kunci(kunci):
    """Ganti kunci yang dipakai (untuk uji otomatis). None = baca ulang dari berkas."""
    global _kunci_utama
    with _kunci_lock:
        _kunci_utama = kunci


def _turunkan(kunci, label):
    """Dari satu kunci utama dibuat dua kunci terpisah (enkripsi & MAC) -> tidak dipakai untuk dua tujuan."""
    return hmac.digest(kunci, label, "sha256")


# ---------- 2. Inti: proses aliran data ----------
def _keystream(kunci_enk, nonce, blok_awal, jumlah_byte):
    jumlah_blok = (jumlah_byte + UKURAN_BLOK - 1) // UKURAN_BLOK
    bagian = (hmac.digest(kunci_enk, nonce + (blok_awal + i).to_bytes(8, "big"), "sha256")
              for i in range(jumlah_blok))
    return b"".join(bagian)[:jumlah_byte]


def _xor(a, b):
    """XOR dua byte-string sama panjang (lewat int agar cepat; tanpa loop per byte)."""
    if not a:
        return b""
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big")


def _proses(masuk, keluar, kunci, nonce, mac, enkripsi):
    """Baca 'masuk' per potongan, XOR dengan keystream, tulis ke 'keluar'.
    MAC selalu dihitung atas DATA TERENKRIPSI (hasil saat enkripsi, masukan saat dekripsi)."""
    kunci_enk = _turunkan(kunci, b"teamup-enkripsi")
    blok = 0
    while True:
        potongan = masuk.read(POTONGAN)
        if not potongan:
            break
        hasil = _xor(potongan, _keystream(kunci_enk, nonce, blok, len(potongan)))
        blok += POTONGAN // UKURAN_BLOK
        mac.update(hasil if enkripsi else potongan)
        keluar.write(hasil)


def _mac_baru(kunci, nonce):
    mac = hmac.new(_turunkan(kunci, b"teamup-mac"), digestmod="sha256")
    mac.update(MAGIC + nonce)
    return mac


# ---------- 3. Bytes ----------
def enkripsi_bytes(data, kunci=None):
    kunci = kunci or muat_kunci()
    nonce = secrets.token_bytes(UKURAN_NONCE)
    keluar = io.BytesIO()
    mac = _mac_baru(kunci, nonce)
    _proses(io.BytesIO(data), keluar, kunci, nonce, mac, True)
    return MAGIC + nonce + keluar.getvalue() + mac.digest()


def dekripsi_bytes(token, kunci=None):
    kunci = kunci or muat_kunci()
    if len(token) < len(MAGIC) + UKURAN_NONCE + UKURAN_TAG or not token.startswith(MAGIC):
        raise DataRusak("Format data terenkripsi tidak dikenal.")
    nonce = token[len(MAGIC):len(MAGIC) + UKURAN_NONCE]
    isi = token[len(MAGIC) + UKURAN_NONCE:-UKURAN_TAG]
    tag = token[-UKURAN_TAG:]
    mac = _mac_baru(kunci, nonce)
    keluar = io.BytesIO()
    _proses(io.BytesIO(isi), keluar, kunci, nonce, mac, False)
    if not hmac.compare_digest(mac.digest(), tag):      # bandingkan dalam waktu tetap
        raise DataRusak("Data diubah atau kunci salah.")
    return keluar.getvalue()


# ---------- 4. Teks (untuk kolom database) ----------
def sudah_terenkripsi(teks):
    return isinstance(teks, str) and teks.startswith(AWALAN_TEKS)


def enkripsi_teks(teks, kunci=None):
    """'0812-3456-7890' -> 'enc1$VFVFMX...' (aman disimpan di kolom TEXT). Teks kosong dibiarkan kosong."""
    if not teks or sudah_terenkripsi(teks):
        return teks
    token = enkripsi_bytes(teks.encode("utf-8"), kunci)
    return AWALAN_TEKS + base64.urlsafe_b64encode(token).decode("ascii")


def dekripsi_teks(teks, kunci=None):
    """Kebalikan enkripsi_teks. Teks biasa (data lama sebelum ada enkripsi) dikembalikan apa adanya,
    jadi data lama tetap terbaca dan aplikasi tidak rusak saat transisi."""
    if not sudah_terenkripsi(teks):
        return teks
    try:
        token = base64.urlsafe_b64decode(teks[len(AWALAN_TEKS):].encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        raise DataRusak("Teks terenkripsi rusak.")
    return dekripsi_bytes(token, kunci).decode("utf-8")


# ---------- 5. Berkas ----------
def enkripsi_berkas(sumber, tujuan, kunci=None):
    """Enkripsi 'sumber' menjadi berkas 'tujuan' (per 1 MB, RAM tetap kecil). Penulisan atomik."""
    kunci = kunci or muat_kunci()
    nonce = secrets.token_bytes(UKURAN_NONCE)
    mac = _mac_baru(kunci, nonce)
    sementara = f"{tujuan}.{uuid.uuid4().hex[:6]}.tmp"      # unik -> dua proses ke tujuan yang sama tidak bentrok
    try:
        with open(sumber, "rb") as masuk, open(sementara, "wb") as keluar:
            keluar.write(MAGIC + nonce)
            _proses(masuk, keluar, kunci, nonce, mac, True)
            keluar.write(mac.digest())
        os.replace(sementara, tujuan)
    finally:
        if os.path.exists(sementara):
            os.remove(sementara)


def dekripsi_berkas(sumber, tujuan, kunci=None):
    """Kebalikan enkripsi_berkas. Hasil ditulis ke berkas sementara dan baru dipindah ke 'tujuan' SETELAH
    tag terbukti cocok -> isi yang belum terverifikasi tidak pernah muncul sebagai berkas jadi."""
    kunci = kunci or muat_kunci()
    ukuran = os.path.getsize(sumber)
    awal = len(MAGIC) + UKURAN_NONCE
    if ukuran < awal + UKURAN_TAG:
        raise DataRusak("Berkas terenkripsi terlalu pendek.")
    sementara = f"{tujuan}.{uuid.uuid4().hex[:6]}.tmp"      # unik -> dua proses ke tujuan yang sama tidak bentrok
    try:
        with open(sumber, "rb") as masuk:
            kepala = masuk.read(awal)
            if not kepala.startswith(MAGIC):
                raise DataRusak("Format berkas tidak dikenal.")
            nonce = kepala[len(MAGIC):]
            mac = _mac_baru(kunci, nonce)
            tersisa = ukuran - awal - UKURAN_TAG            # jumlah byte data (di luar tag)
            with open(sementara, "wb") as keluar:
                _proses(_Batas(masuk, tersisa), keluar, kunci, nonce, mac, False)
            tag = masuk.read(UKURAN_TAG)
        if not hmac.compare_digest(mac.digest(), tag):
            raise DataRusak("Berkas diubah atau kunci salah.")
        os.replace(sementara, tujuan)
    finally:
        if os.path.exists(sementara):
            os.remove(sementara)


class _Batas:
    """Pembungkus berkas yang hanya mau dibaca sampai 'sisa' byte (agar tag di ujung tidak ikut diproses)."""
    def __init__(self, f, sisa):
        self.f, self.sisa = f, sisa

    def read(self, n):
        data = self.f.read(min(n, self.sisa))
        self.sisa -= len(data)
        return data
