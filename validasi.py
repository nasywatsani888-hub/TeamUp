# validasi.py — Validasi & pembersihan input terpusat TeamUp (Pertemuan 12: Security & Error Handling)
#
# Masalah sebelumnya: aturan validasi tersebar di tiap halaman dan banyak yang terlalu longgar, mis.
#   * email dianggap valid asal ada "@" dan "."  ->  "@." atau "a@b." lolos
#   * username / nama / bio tidak dibatasi panjang & karakter (username boleh spasi, emoji, atau 5000 huruf)
#   * link hanya dicek awalan "http" tanpa memeriksa isinya, kontak tidak dicek formatnya sama sekali
#
# Prinsip: "jangan percaya input". Semua input dari user dianggap tidak aman sampai diperiksa di sini.
#   * Allow-list (hanya karakter yang DIIZINKAN yang lolos), bukan block-list (menebak yang berbahaya).
#   * Satu tempat untuk semua aturan -> halaman tinggal memanggil, aturannya bisa diuji sendiri.
#   * Validasi di UI hanya untuk kenyamanan user; pertahanan sebenarnya tetap di lapisan database
#     (query berparameter, CHECK/UNIQUE) dan hak akses (hak_akses.py).
#
# Pola setiap fungsi periksa_xxx(nilai): mengembalikan "" kalau VALID, atau PESAN ERROR (bahasa Indonesia)
# yang langsung bisa ditampilkan ke user. Contoh pemakaian di halaman:
#       pesan = validasi.periksa_email(email)
#       if pesan:
#           helpers.show_error(self.message_label, pesan)
#           return
#
# Hanya memakai modul bawaan Python: re, unicodedata, urllib.parse.
import re
import unicodedata
from urllib.parse import urlsplit

# Batas panjang (min, maks) per jenis isian. Satu tempat -> mudah disesuaikan.
BATAS = {
    "nama": (2, 60),
    "username": (3, 20),
    "email": (5, 254),             # 254 = batas panjang alamat email menurut standar
    "password": (16, 128),         # kebijakan revisi dosen: minimal 16 karakter; batas atas mencegah input raksasa
    "bio": (0, 300),
    "prodi": (2, 80),
    "universitas": (2, 100),
    "domisili": (2, 80),
    "judul": (5, 120),
    "deskripsi": (20, 3000),
    "url": (10, 2048),
}

# Username yang tidak boleh dipakai (menyamar sebagai sistem / admin)
USERNAME_DILARANG = {"admin", "administrator", "root", "teamup", "support", "system", "moderator", "official"}

# Password yang terlalu umum (daftar kecil untuk contoh; produk sungguhan memakai daftar ribuan entri)
PASSWORD_UMUM = {
    "password", "password1", "password123", "pass1234", "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyuiop", "abc12345", "abcd1234", "iloveyou1", "admin123", "teamup123",
    "welcome123", "letmein123", "11111111", "00000000",
}

_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"          # satu bagian nama situs: tidak boleh diawali/diakhiri "-"
_POLA_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@(?:" + _LABEL + r"\.)+[A-Za-z]{2,}$")
_POLA_USERNAME = re.compile(r"^[A-Za-z0-9_.]+$")
_POLA_HOST = re.compile(r"^(?:" + _LABEL + r"\.)+" + _LABEL + r"$")


# ---------------------------------------------------------------- 1. Pembersihan
def bersihkan_teks(teks, satu_baris=True):
    """Rapikan teks dari user SEBELUM diperiksa / disimpan:
      * normalisasi Unicode (NFC) -> huruf bertanda ('é') selalu berbentuk sama, tidak ada duplikat tersembunyi
      * buang karakter kontrol (kode 0-31, 127) & karakter tak terlihat (zero-width) -> mencegah nama yang
        tampak sama padahal berbeda, dan byte NUL yang bisa mengacaukan penyimpanan
      * satu_baris=True : semua spasi / tab / baris baru dipadatkan jadi satu spasi
        satu_baris=False : baris baru dipertahankan (untuk deskripsi / bio)
    Mengembalikan teks bersih (str). None dianggap teks kosong."""
    if teks is None:
        return ""
    teks = unicodedata.normalize("NFC", str(teks))
    bersih = []
    for huruf in teks:
        kategori = unicodedata.category(huruf)
        if huruf in "\n\t":
            bersih.append(huruf)
        elif kategori in ("Cc", "Cf", "Cs", "Co", "Cn"):     # kontrol, format (zero-width), surrogate, dll.
            continue
        else:
            bersih.append(huruf)
    teks = "".join(bersih)
    if satu_baris:
        return re.sub(r"\s+", " ", teks).strip()
    teks = teks.replace("\r\n", "\n").replace("\r", "\n")
    teks = re.sub(r"[ \t]+", " ", teks)                      # spasi berulang dipadatkan
    teks = re.sub(r"\n{3,}", "\n\n", teks)                   # maksimal satu baris kosong berturut-turut
    return teks.strip()


# ---------------------------------------------------------------- 2. Panjang & teks umum
def periksa_panjang(teks, nama_field, minimal, maksimal):
    """Cek panjang setelah dibersihkan. Contoh: periksa_panjang(bio, "Bio", 0, 300)."""
    panjang = len(teks)
    if panjang < minimal:
        return f"{nama_field} minimal {minimal} karakter." if minimal > 1 else f"{nama_field} tidak boleh kosong."
    if panjang > maksimal:
        return f"{nama_field} maksimal {maksimal} karakter (sekarang {panjang})."
    return ""


def periksa_teks(teks, nama_field, jenis):
    """Validasi teks isian biasa berdasarkan BATAS[jenis] (prodi, universitas, domisili, judul, deskripsi, bio)."""
    minimal, maksimal = BATAS[jenis]
    if "<" in teks or ">" in teks:                           # tidak ada isian TeamUp yang butuh tanda ini
        return f"{nama_field} tidak boleh mengandung tanda < atau >."
    return periksa_panjang(teks, nama_field, minimal, maksimal)


# ---------------------------------------------------------------- 3. Identitas
def normalisasi_email(email):
    """Email tidak peka huruf besar/kecil: 'Budi@Gmail.COM ' -> 'budi@gmail.com'."""
    return bersihkan_teks(email).lower()


def periksa_email(email):
    minimal, maksimal = BATAS["email"]
    if not email:
        return "Email tidak boleh kosong."
    if len(email) > maksimal:
        return f"Email maksimal {maksimal} karakter."
    if " " in email or not _POLA_EMAIL.fullmatch(email):
        return "Format email tidak valid (contoh: nama@kampus.ac.id)."
    lokal = email.split("@")[0]
    if len(lokal) > 64 or lokal.startswith(".") or lokal.endswith(".") or ".." in email:
        return "Format email tidak valid (contoh: nama@kampus.ac.id)."
    return ""


def periksa_nama(nama):
    """Nama lengkap: huruf dari bahasa apa pun, spasi, titik, koma, apostrof, strip. Tanpa angka & simbol lain."""
    minimal, maksimal = BATAS["nama"]
    pesan = periksa_panjang(nama, "Nama", minimal, maksimal)
    if pesan:
        return pesan
    if not any(h.isalpha() for h in nama):
        return "Nama harus mengandung huruf."
    for huruf in nama:
        if not (huruf.isalpha() or huruf in " .,'-"):
            return "Nama hanya boleh berisi huruf, spasi, titik, koma, apostrof, dan strip."
    return ""


def periksa_username(username):
    """Username dipakai sebagai tag (@AGBell): huruf, angka, garis bawah, titik; 3-20 karakter."""
    minimal, maksimal = BATAS["username"]
    pesan = periksa_panjang(username, "Username", minimal, maksimal)
    if pesan:
        return pesan
    if not _POLA_USERNAME.fullmatch(username):
        return "Username hanya boleh berisi huruf, angka, garis bawah (_), dan titik (.), tanpa spasi."
    if username.startswith(".") or username.endswith(".") or ".." in username:
        return "Username tidak boleh diawali/diakhiri titik atau memuat titik berurutan."
    if username.lower() in USERNAME_DILARANG:
        return "Username ini dicadangkan, coba yang lain."
    return ""


# ---------------------------------------------------------------- 4. Password
ATURAN_PASSWORD = "Min 16 karakter, besar, kecil, angka & simbol"        # teks petunjuk untuk kolom isian


def periksa_password(password, email=""):
    """Kebijakan password (revisi dosen): 16-128 karakter, mengandung huruf BESAR, huruf kecil, angka, dan
    simbol; bukan password umum; tidak memuat bagian depan email sendiri. Spasi di awal/akhir TIDAK dibuang:
    password dipakai apa adanya. Satu-satunya sumber aturan: helpers.is_valid_password memanggil fungsi ini."""
    minimal, maksimal = BATAS["password"]
    pesan_aturan = (f"Password minimal {minimal} karakter dan mengandung huruf besar, huruf kecil, angka, "
                    "dan simbol.")
    if len(password) < minimal:
        return pesan_aturan
    if len(password) > maksimal:
        return f"Password maksimal {maksimal} karakter."
    if not (any(h.isupper() for h in password) and any(h.islower() for h in password)
            and any(h.isdigit() for h in password) and any(not h.isalnum() for h in password)):
        return pesan_aturan
    if password.lower() in PASSWORD_UMUM:
        return "Password terlalu umum dan mudah ditebak. Pilih yang lain."
    depan = email.split("@")[0].lower() if email else ""
    if len(depan) >= 4 and depan in password.lower():
        return "Password tidak boleh memuat nama email kamu."
    return ""


def kekuatan_password(password):
    """Penilaian untuk indikator di UI. Mengembalikan (skor 0-4, label): 0 Sangat lemah ... 4 Kuat.
    Skor bertambah untuk panjang (>=8, >=12), variasi huruf besar+kecil, angka, dan simbol."""
    if not password:
        return 0, "Sangat lemah"
    skor = 0
    skor += len(password) >= 12
    skor += len(password) >= 16
    skor += any(h.islower() for h in password) and any(h.isupper() for h in password)
    skor += any(h.isdigit() for h in password) and any(h.isalpha() for h in password)
    skor += any(not h.isalnum() for h in password)
    if password.lower() in PASSWORD_UMUM:
        skor = 0
    skor = min(skor, 4)
    return skor, ("Sangat lemah", "Lemah", "Cukup", "Baik", "Kuat")[skor]


# ---------------------------------------------------------------- 5. Kontak & tautan
def normalisasi_telepon(nomor):
    """'0812-3456 7890' -> '081234567890'. '+62 812...' dan '62812...' diseragamkan jadi '0812...'."""
    nomor = re.sub(r"[\s\-().]", "", bersihkan_teks(nomor))
    if nomor.startswith("+62"):
        nomor = "0" + nomor[3:]
    elif nomor.startswith("62"):
        nomor = "0" + nomor[2:]
    return nomor


def periksa_telepon(nomor):
    bersih = normalisasi_telepon(nomor)
    if not bersih.isdigit() or not bersih.startswith("0"):
        return "Nomor telepon tidak valid (contoh: 081234567890)."
    if not 10 <= len(bersih) <= 14:
        return "Nomor telepon harus 10-14 digit."
    return ""


def periksa_kontak(kontak):
    """Kontak resmi penyelenggara: boleh nomor telepon ATAU email yang valid."""
    if not kontak:
        return "Kontak penyelenggara tidak boleh kosong."
    if "@" in kontak:
        return periksa_email(kontak)
    return periksa_telepon(kontak)


def periksa_url(url, wajib_https=True):
    """Tautan pendaftaran: HANYA https (revisi dosen; wajib_https=False membolehkan http juga), punya nama situs
    yang wajar, tanpa spasi dan tanpa user:password@. Skema lain (javascript:, file:, data:, ftp:) ditolak ->
    mencegah tautan yang menjalankan kode / membuka berkas lokal."""
    minimal, maksimal = BATAS["url"]
    if not url:
        return "Link pendaftaran tidak boleh kosong."
    if len(url) > maksimal:
        return f"Link maksimal {maksimal} karakter."
    if re.search(r"[\s\x00-\x1f\x7f]", url):
        return "Link tidak boleh mengandung spasi atau karakter kontrol."
    try:
        bagian = urlsplit(url)
        host = bagian.hostname or ""
        bagian.port                                           # memicu ValueError kalau nomor port tidak valid
    except ValueError:
        return "Format link tidak valid."
    if wajib_https and bagian.scheme.lower() != "https":
        return "Link pendaftaran harus aman dan diawali dengan https://"
    if bagian.scheme.lower() not in ("http", "https"):
        return "Link pendaftaran harus diawali https://"
    if bagian.username or bagian.password:
        return "Link tidak boleh memuat nama pengguna / kata sandi."
    if not _POLA_HOST.fullmatch(host) or len(host) > 253:
        return "Nama situs pada link tidak valid (contoh: https://kampus.ac.id/lomba)."
    return ""


def periksa_instagram(akun):
    """Akun Instagram opsional: 1-30 karakter huruf/angka/titik/garis bawah (tanda @ di depan boleh)."""
    akun = akun.lstrip("@")
    if akun == "":
        return ""
    if not re.fullmatch(r"[A-Za-z0-9_.]{1,30}", akun):
        return "Akun Instagram hanya boleh huruf, angka, titik, dan garis bawah (maks. 30 karakter)."
    return ""


# ---------------------------------------------------------------- 6. Kode OTP
def periksa_otp(kode, panjang=4):
    if not (kode.isascii() and kode.isdigit()) or len(kode) != panjang:
        return f"Kode OTP harus {panjang} digit angka."
    return ""
