# keamanan_akun.py — Keamanan akun: OTP reset password yang aman + pembatas percobaan login (Pertemuan 12)
#
# Masalah sebelumnya (hasil review kode):
#   OTP   : dibuat dengan random.randint (pengacak biasa, bisa ditebak polanya), hanya 4 digit (10.000 kemungkinan),
#           TIDAK kedaluwarsa, TIDAK ada batas percobaan -> penyerang cukup mencoba 0000..9999 sampai tembus.
#           Kode juga disimpan sebagai teks biasa & dibandingkan dengan "!=" (bocor lewat perbedaan waktu).
#   Login : boleh mencoba password sebanyak-banyaknya tanpa jeda (serangan tebak password / brute force).
#   Waktu : email tidak terdaftar langsung ditolak (cepat), email terdaftar butuh hashing (lambat) ->
#           selisih waktunya membocorkan email mana yang terdaftar.
#
# Perbaikan:
#   OTP   : secrets (pengacak aman), kedaluwarsa 5 menit, maksimal 3 percobaan, sekali pakai, jeda kirim ulang,
#           hanya HASH kode yang disimpan, dibandingkan dengan compare_digest.
#   Login : 5 kali gagal -> dikunci 30 detik, kunci berikutnya berlipat dua (30 -> 60 -> 120 ... maks 15 menit).
#   Waktu : samakan_waktu() membuat "email tidak terdaftar" memakan waktu yang sama dengan "password salah".
#
# Status disimpan di MEMORI (hilang saat aplikasi ditutup). Cukup untuk aplikasi desktop lokal; untuk layanan
# server, status ini harus disimpan di basis data bersama. Hanya memakai modul bawaan Python.
import hashlib
import hmac
import secrets
import threading
import time

from database import sandi

# ---------------- Pengaturan (satu tempat, mudah disesuaikan) ----------------
PANJANG_OTP = 4                 # sesuai UI (4 kotak). Pertahanan utamanya batas percobaan, bukan panjang kode.
MASA_BERLAKU_OTP = 300          # detik (5 menit)
MAKS_PERCOBAAN_OTP = 3          # salah 3x -> kode hangus, harus minta kode baru
JEDA_KIRIM_ULANG = 30           # detik minimal antar permintaan kode untuk email yang sama
MAKS_PERMINTAAN_OTP = 5         # maksimal permintaan kode per JENDELA_PERMINTAAN
JENDELA_PERMINTAAN = 900        # detik (15 menit)
MASA_IZIN_RESET = 600           # detik: batas waktu mengisi password baru setelah OTP benar

MAKS_GAGAL_LOGIN = 5            # gagal beruntun sebelum dikunci
KUNCI_AWAL = 30                 # detik, kunci pertama
KUNCI_MAKS = 900                # detik, batas atas kunci (15 menit)
LUPA_SETELAH = 1800             # detik: catatan gagal yang sudah selama ini tidak aktif dihapus
MAKS_AKUN_DICATAT = 1000        # batas memori: catatan terlama dibuang kalau melebihi ini

_jam = time.monotonic           # jam yang tidak mundur walau waktu sistem diubah; bisa diganti untuk uji
_kunci = threading.RLock()      # worker thread dan thread UI bisa memanggil bersamaan

_otp = {}                       # email -> {"hash", "salt", "kedaluwarsa", "sisa"}
_permintaan = {}                # email -> [waktu permintaan kode]
_izin_reset = {}                # email -> waktu kedaluwarsa izin ganti password
_login = {}                     # email -> {"gagal", "tingkat", "kunci_hingga", "terakhir"}
_hash_palsu = None


def gunakan_jam(fungsi):
    """Ganti sumber waktu (untuk uji otomatis agar tidak perlu menunggu sungguhan)."""
    global _jam
    _jam = fungsi


def atur_ulang():
    """Hapus semua status (dipakai uji otomatis)."""
    with _kunci:
        _otp.clear()
        _permintaan.clear()
        _izin_reset.clear()
        _login.clear()


def _kunci_email(email):
    return str(email).strip().lower()


def _hash_kode(kode, salt):
    return hmac.new(salt, kode.encode("utf-8"), hashlib.sha256).digest()


def format_durasi(detik):
    """30 -> '30 detik', 61 -> '2 menit' (dibulatkan ke atas supaya user tidak mencoba terlalu cepat)."""
    detik = max(1, int(detik + 0.999))
    return f"{detik} detik" if detik < 60 else f"{(detik + 59) // 60} menit"


# =============================================================== A. OTP reset password
def sisa_jeda_kirim(email):
    """Detik yang masih harus ditunggu sebelum boleh meminta kode baru (0 = boleh sekarang)."""
    with _kunci:
        riwayat = _permintaan.get(_kunci_email(email), [])
        if not riwayat:
            return 0
        return max(0, JEDA_KIRIM_ULANG - (_jam() - riwayat[-1]))


def buat_otp(email):
    """Buat kode OTP baru. Mengembalikan (kode, "") kalau berhasil, atau (None, pesan_error) kalau ditolak
    (terlalu sering meminta). Kode lama untuk email yang sama otomatis tidak berlaku.
    Catatan: kode dikembalikan agar bisa ditampilkan (aplikasi ini mensimulasikan pengiriman email);
    yang disimpan di memori hanya HASH-nya."""
    kunci = _kunci_email(email)
    with _kunci:
        sekarang = _jam()
        riwayat = [t for t in _permintaan.get(kunci, []) if sekarang - t < JENDELA_PERMINTAAN]
        if riwayat and sekarang - riwayat[-1] < JEDA_KIRIM_ULANG:
            return None, f"Tunggu {format_durasi(JEDA_KIRIM_ULANG - (sekarang - riwayat[-1]))} sebelum meminta kode baru."
        if len(riwayat) >= MAKS_PERMINTAAN_OTP:
            tunggu = JENDELA_PERMINTAAN - (sekarang - riwayat[0])
            return None, f"Terlalu banyak permintaan kode. Coba lagi dalam {format_durasi(tunggu)}."
        kode = f"{secrets.randbelow(10 ** PANJANG_OTP):0{PANJANG_OTP}d}"
        salt = secrets.token_bytes(16)
        _otp[kunci] = {"hash": _hash_kode(kode, salt), "salt": salt,
                       "kedaluwarsa": sekarang + MASA_BERLAKU_OTP, "sisa": MAKS_PERCOBAAN_OTP}
        riwayat.append(sekarang)
        _permintaan[kunci] = riwayat
        _izin_reset.pop(kunci, None)                      # permintaan baru membatalkan izin lama
        return kode, ""


def periksa_otp(email, kode):
    """Cocokkan kode yang diketik user. Mengembalikan (True, "") atau (False, pesan_untuk_user).
    Sekali berhasil, kode langsung dihapus (tidak bisa dipakai dua kali) dan izin ganti password terbuka."""
    kunci = _kunci_email(email)
    with _kunci:
        data = _otp.get(kunci)
        if data is None:
            return False, "Kode OTP tidak berlaku. Silakan minta kode baru."
        if _jam() > data["kedaluwarsa"]:
            del _otp[kunci]
            return False, "Kode OTP sudah kedaluwarsa. Silakan minta kode baru."
        cocok = hmac.compare_digest(_hash_kode(str(kode), data["salt"]), data["hash"])
        if cocok:
            del _otp[kunci]
            _izin_reset[kunci] = _jam() + MASA_IZIN_RESET
            return True, ""
        data["sisa"] -= 1
        if data["sisa"] <= 0:
            del _otp[kunci]
            return False, "Terlalu banyak kode yang salah. Kode dibatalkan, silakan minta kode baru."
        return False, f"Kode OTP salah. Sisa percobaan: {data['sisa']}."


def izin_reset_password(email):
    """True kalau email ini baru saja lolos OTP dan masih dalam batas waktu mengisi password baru."""
    kunci = _kunci_email(email)
    with _kunci:
        batas = _izin_reset.get(kunci)
        if batas is None:
            return False
        if _jam() > batas:
            del _izin_reset[kunci]
            return False
        return True


def selesai_reset(email):
    """Dipanggil setelah password berhasil diganti: izin dicabut (sekali pakai)."""
    with _kunci:
        _izin_reset.pop(_kunci_email(email), None)


# =============================================================== B. Pembatas percobaan login
def cek_boleh_login(email):
    """(True, 0) kalau boleh mencoba login, atau (False, sisa_detik) kalau akun sedang dikunci sementara.
    Dihitung per email yang DIKETIK, terdaftar atau tidak, supaya penyerang tidak bisa membedakannya."""
    kunci = _kunci_email(email)
    with _kunci:
        catatan = _login.get(kunci)
        if catatan is None:
            return True, 0
        sekarang = _jam()
        if catatan["kunci_hingga"] > sekarang:
            return False, catatan["kunci_hingga"] - sekarang
        if sekarang - catatan["terakhir"] > LUPA_SETELAH:         # lama tidak aktif -> mulai dari awal
            del _login[kunci]
        return True, 0


def catat_gagal(email):
    """Catat satu percobaan login gagal. Mengembalikan (terkunci, sisa_percobaan, sisa_detik_kunci)."""
    kunci = _kunci_email(email)
    with _kunci:
        sekarang = _jam()
        catatan = _login.setdefault(kunci, {"gagal": 0, "tingkat": 0, "kunci_hingga": 0.0, "terakhir": sekarang})
        if catatan["kunci_hingga"] > sekarang:                    # sudah terkunci: tidak menambah hukuman
            return True, 0, catatan["kunci_hingga"] - sekarang
        catatan["gagal"] += 1
        catatan["terakhir"] = sekarang
        if catatan["gagal"] >= MAKS_GAGAL_LOGIN:
            catatan["tingkat"] += 1
            durasi = min(KUNCI_AWAL * 2 ** (catatan["tingkat"] - 1), KUNCI_MAKS)
            catatan["kunci_hingga"] = sekarang + durasi
            catatan["gagal"] = 0
            _pangkas_catatan()
            return True, 0, durasi
        _pangkas_catatan()
        return False, MAKS_GAGAL_LOGIN - catatan["gagal"], 0


def catat_berhasil(email):
    """Login berhasil -> catatan gagal dihapus."""
    with _kunci:
        _login.pop(_kunci_email(email), None)


def _pangkas_catatan():
    """Jaga memori: kalau catatan terlalu banyak (mis. penyerang mengarang ribuan email), buang yang terlama."""
    while len(_login) > MAKS_AKUN_DICATAT:
        terlama = min(_login, key=lambda k: _login[k]["terakhir"])
        del _login[terlama]


def pesan_kunci(sisa_detik):
    return f"Terlalu banyak percobaan. Coba lagi dalam {format_durasi(sisa_detik)}."


# =============================================================== C. Samakan waktu
def samakan_waktu(password):
    """Panggil saat email TIDAK terdaftar: menjalankan satu verifikasi hash palsu supaya waktunya sama dengan
    email terdaftar + password salah. Tanpa ini, penyerang bisa mengukur kecepatan respons untuk menebak
    email mana yang punya akun. Selalu mengembalikan False."""
    global _hash_palsu
    if _hash_palsu is None:
        _hash_palsu = sandi.hash_password("palsu-" + secrets.token_hex(8))
    sandi.cocok(_hash_palsu, str(password))
    return False
