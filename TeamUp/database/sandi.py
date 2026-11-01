# database/sandi.py — hash password (PBKDF2-HMAC-SHA256, hanya modul bawaan Python)
#
# Kenapa hash? Begitu data disimpan ke file, password teks asli ikut tersimpan di disk: siapa pun yang
# menyalin teamup.db bisa membacanya. Hash satu arah + salt acak membuat password tidak bisa dibalik
# dan dua user dengan password sama tetap punya hash berbeda. (Pendalaman keamanan: Pertemuan 12.)
import hashlib
import hmac
import secrets

ALGORITMA = "pbkdf2_sha256"
ITERASI = 120_000   # makin besar makin lambat ditebak; uji otomatis boleh menurunkannya agar cepat


def hash_password(teks, iterasi=None):
    iterasi = iterasi or ITERASI
    salt = secrets.token_hex(16)
    kunci = hashlib.pbkdf2_hmac("sha256", teks.encode("utf-8"), bytes.fromhex(salt), iterasi)
    return f"{ALGORITMA}${iterasi}${salt}${kunci.hex()}"


def sudah_di_hash(tersimpan):
    return isinstance(tersimpan, str) and tersimpan.startswith(ALGORITMA + "$")


def cocok(tersimpan, masukan):
    """True kalau 'masukan' sesuai dengan yang tersimpan. Mendukung hash dan (mode memori) teks biasa.
    compare_digest membandingkan dalam waktu tetap, supaya tidak bocor lewat perbedaan waktu."""
    if not sudah_di_hash(tersimpan):
        return hmac.compare_digest(str(tersimpan).encode("utf-8"), str(masukan).encode("utf-8"))
    _, iterasi, salt, hasil = tersimpan.split("$")
    kunci = hashlib.pbkdf2_hmac("sha256", masukan.encode("utf-8"), bytes.fromhex(salt), int(iterasi))
    return hmac.compare_digest(kunci.hex(), hasil)
