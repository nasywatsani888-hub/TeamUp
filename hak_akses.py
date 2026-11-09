# hak_akses.py — Manajemen hak akses TeamUp: peran (siapa) + izin (boleh melakukan apa) (Pertemuan 12)
#
# Masalah sebelumnya (hasil review kode):
#   * Pemeriksaan pemilik di repository bersifat OPSIONAL: perbarui_postingan(id, data) tanpa email_pemilik
#     lolos begitu saja -> aturan hanya berlaku kalau pemanggil ingat mengirim emailnya.
#   * putuskan_postingan() (menyetujui / menolak lomba) bisa dipanggil SIAPA SAJA: tidak ada konsep admin.
#   * tandai_dibaca(notif_id) tidak memeriksa pemilik notifikasi -> id notifikasi orang lain bisa dimanipulasi
#     (IDOR: Insecure Direct Object Reference).
#
# Prinsip yang dipakai:
#   1. LEAST PRIVILEGE   : tiap peran hanya diberi izin yang dibutuhkan. Admin hanya memutuskan status
#                          postingan; admin TIDAK otomatis boleh membaca / mengubah data pribadi orang lain.
#   2. DENY BY DEFAULT   : kalau pelaku tidak jelas (belum login / email kosong), jawabannya TIDAK.
#   3. SATU SUMBER ATURAN: semua keputusan ada di file ini. UI memakainya untuk mengatur tombol, repository
#                          memakainya untuk MENEGAKKAN aturan -> keduanya tidak bisa berbeda pendapat.
#   4. SERVER-SIDE (lapisan data) yang menentukan, bukan tombol: tombol yang disembunyikan tidak melindungi apa pun.
#
# Pola setiap fungsi boleh_xxx(...): mengembalikan (True, "") atau (False, "pesan untuk user").
# Fungsi ini MURNI (tanpa database, tanpa Qt) sehingga mudah diuji. Hanya memakai modul bawaan Python.
import os

PERAN_ADMIN = "admin"
PERAN_PENGGUNA = "pengguna"

# Aturan status postingan (sesuai flowchart: Ditangguhkan TIDAK bisa diedit sampai diverifikasi admin)
STATUS_BISA_DIEDIT = ("Revisi",)
STATUS_TIDAK_BISA_DIHAPUS = ("Disetujui",)
STATUS_VALID = ("Ditangguhkan", "Disetujui", "Revisi", "Ditolak")

# Matriks izin (dokumentasi + bahan presentasi). Isi sel = siapa yang boleh.
MATRIKS_IZIN = {
    "Lihat lomba yang sudah terverifikasi": {"Tamu": "ya", "Pengguna": "ya", "Admin": "ya"},
    "Unggah postingan baru": {"Tamu": "tidak", "Pengguna": "ya (atas nama sendiri)", "Admin": "ya (atas nama sendiri)"},
    "Perbarui postingan (kirim ulang perbaikan)": {"Tamu": "tidak", "Pengguna": "hanya miliknya, status Revisi", "Admin": "hanya miliknya, status Revisi"},
    "Hapus / batalkan pengajuan": {"Tamu": "tidak", "Pengguna": "hanya miliknya, bukan yang Disetujui", "Admin": "hanya miliknya, bukan yang Disetujui"},
    "Putuskan status postingan (setujui / revisi / tolak)": {"Tamu": "tidak", "Pengguna": "tidak", "Admin": "ya"},
    "Baca / tandai / hapus notifikasi": {"Tamu": "tidak", "Pengguna": "hanya miliknya", "Admin": "hanya miliknya"},
}

_admin_override = None       # set email (huruf kecil) untuk uji otomatis; None = baca dari lingkungan


# ---------------------------------------------------------------- Peran
def _normal(email):
    return str(email or "").strip().lower()


def _muat_admin():
    """Daftar admin dibaca dari: variabel lingkungan TEAMUP_ADMIN (pisahkan dengan koma), dan config.ADMIN_EMAILS
    (opsional). Kalau keduanya kosong -> TIDAK ADA admin (aman secara bawaan)."""
    hasil = {_normal(e) for e in os.environ.get("TEAMUP_ADMIN", "").split(",") if e.strip()}
    try:
        import config
        hasil |= {_normal(e) for e in getattr(config, "ADMIN_EMAILS", ())}
    except ImportError:
        pass
    return hasil


def gunakan_admin(daftar_email):
    """Tetapkan daftar admin secara manual (dipakai uji otomatis). None = kembali membaca dari lingkungan."""
    global _admin_override
    _admin_override = None if daftar_email is None else {_normal(e) for e in daftar_email}


def adalah_admin(email):
    email = _normal(email)
    if not email:
        return False
    daftar = _admin_override if _admin_override is not None else _muat_admin()
    return email in daftar


def peran(email):
    """'admin', 'pengguna', atau 'tamu' (belum login / email kosong)."""
    if not _normal(email):
        return "tamu"
    return PERAN_ADMIN if adalah_admin(email) else PERAN_PENGGUNA


def sama_orang(email_a, email_b):
    """True kalau dua email menunjuk orang yang sama (tak peka huruf besar/kecil). Email kosong tidak pernah sama."""
    a, b = _normal(email_a), _normal(email_b)
    return a != "" and a == b


# ---------------------------------------------------------------- Izin
def boleh_ubah_postingan(pelaku, pemilik, status):
    """Memperbarui / mengirim ulang postingan: pemiliknya sendiri DAN hanya saat status Revisi.
    (Ditangguhkan, Disetujui, Ditolak tidak bisa diedit.)"""
    if not _normal(pelaku):
        return False, "Anda harus masuk terlebih dahulu."
    if not sama_orang(pelaku, pemilik):
        return False, "Hanya pemilik yang dapat memperbarui postingan ini"
    if status not in STATUS_BISA_DIEDIT:
        return False, f"Hanya postingan berstatus Revisi yang bisa diperbarui (status sekarang: {status})"
    return True, ""


def boleh_hapus_postingan(pelaku, pemilik, status):
    """Menghapus / membatalkan pengajuan: pemiliknya sendiri, dan bukan yang sudah Disetujui."""
    if not _normal(pelaku):
        return False, "Anda harus masuk terlebih dahulu."
    if not sama_orang(pelaku, pemilik):
        return False, "Hanya pemilik yang dapat menghapus pengajuan ini"
    if status in STATUS_TIDAK_BISA_DIHAPUS:
        return False, "Postingan yang sudah disetujui tidak bisa dihapus"
    return True, ""


def boleh_putuskan_postingan(pelaku):
    """Mengubah status verifikasi (Disetujui / Revisi / Ditolak): khusus admin."""
    if not _normal(pelaku):
        return False, "Anda harus masuk terlebih dahulu."
    if not adalah_admin(pelaku):
        return False, "Hanya admin yang dapat memutuskan status postingan."
    return True, ""


def boleh_akses_milik(pelaku, pemilik, objek="data ini"):
    """Aturan umum 'milik sendiri' (mis. notifikasi). Admin pun tidak mendapat pengecualian (least privilege)."""
    if not _normal(pelaku):
        return False, "Anda harus masuk terlebih dahulu."
    if not sama_orang(pelaku, pemilik):
        return False, f"Anda tidak memiliki akses ke {objek}."
    return True, ""


def boleh_lihat_data_pribadi(pelaku, pemilik):
    """Postingan 'Postingan Saya' dan notifikasi hanya untuk pemiliknya. Dipakai untuk menyaring daftar di UI."""
    return sama_orang(pelaku, pemilik)
