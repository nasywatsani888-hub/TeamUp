# data_store.py — data SEMENTARA di memori (tanpa database)
# Data hilang saat aplikasi ditutup. Database baru dipakai di pertemuan 9.
import random
from datetime import date

users = [
    {
        "nama": "Pengguna Demo",
        "email": "demo@teamup.com",
        "password": "demo1234",
        "username": "demo",
        "prodi": "Informatika",
        "universitas": "Universitas Demo",
        "domisili": "Yogyakarta",
        "bio": "",
        "keahlian": [],
        "instagram": "",
        "pengalaman": [],
        "foto": "",
    },
    # --- Data contoh calon rekan tim (untuk halaman Rekan Tim) ---
    {
        "nama": "Marques Hellim",
        "email": "marques@teamup.com",
        "password": "demo1234",
        "username": "Marque_h12",
        "prodi": "Teknik Kimia",
        "universitas": "UGM",
        "domisili": "Sleman, DI Yogyakarta",
        "bio": "Mahasiswa Teknik Kimia yang suka desain antarmuka dan public speaking. "
               "Pernah jadi finalis 3 lomba UI/UX tingkat nasional.",
        "keahlian": ["UI/UX Designer", "Essay"],
        "instagram": "Marqmi_",
        "pengalaman": ["Finalis Lomba UI/UX Nasional 2025", "Juara Hackathon Kampus 2024"],
        "foto": "marques.png",
    },
    {
        "nama": "Ahmed Ahland",
        "email": "ahmed@teamup.com",
        "password": "demo1234",
        "username": "Ahmed4hl",
        "prodi": "Teknologi Informasi",
        "universitas": "UNY",
        "domisili": "Bantul, DI Yogyakarta",
        "bio": "Mahasiswa Teknologi Informasi yang membangun aplikasi web dan senang "
               "eksplorasi teknologi baru. Pernah tergabung dalam finalis 3 hackathon "
               "tingkat nasional sebagai frontend developer.",
        "keahlian": ["Frontend Development", "Programmer"],
        "instagram": "ahmed4hl",
        "pengalaman": ["Finalis Hackathon Nasional 2025", "Juara Hackathon Kampus 2024"],
        "foto": "ahmed.png",
    },
    {
        "nama": "Nadia Putri",
        "email": "nadia@teamup.com",
        "password": "demo1234",
        "username": "nadiaputri",
        "prodi": "Sistem Informasi",
        "universitas": "UII",
        "domisili": "Sleman, DI Yogyakarta",
        "bio": "Suka mengerjakan sisi backend dan basis data.",
        "keahlian": ["Backend Development", "Programmer"],
        "instagram": "nadiaputri",
        "pengalaman": ["Peserta Gemastik 2025"],
        "foto": "nadia.png",
    },
    {
        "nama": "Bima Prakoso",
        "email": "bima@teamup.com",
        "password": "demo1234",
        "username": "bimaprk",
        "prodi": "Desain Komunikasi Visual",
        "universitas": "ISI Yogyakarta",
        "domisili": "Yogyakarta",
        "bio": "Desainer yang fokus ke riset pengguna dan prototipe.",
        "keahlian": ["UI/UX Design", "Ilustrasi"],
        "instagram": "",
        "pengalaman": [],
        "foto": "bima.png",
    },
]

# Kategori di halaman Rekan Tim -> kata kunci yang dicari pada keahlian user
# (keahlian di biodata berupa teks bebas, jadi dicocokkan dengan kata kunci)
KATEGORI_PARTNER = {
    "UI/UX Desain": ["ui/ux", "ui ux", "desain", "design"],
    "Programmer": ["programmer", "developer", "frontend", "backend", "coding"],
}
URUTAN_DEFAULT = "Cari Rekan"
URUTAN_OPSI = ["Nama A-Z", "Nama Z-A"]

# Data lomba contoh (nanti diisi dari hasil Unggah Info Lomba yang disetujui admin)
# sisa_hari = sisa hari sampai tenggat pendaftaran; tanggal tenggat dihitung dari hari ini.
# diunggah_hari_lalu = untuk urutan "Baru diunggah"; dilihat = untuk urutan "Paling populer".
lomba_list = [
    {"id": 1, "judul": "Code & Create: Robotics", "penyelenggara": "Himanika UNY",
     "kategori": "Robotics", "sisa_hari": 10, "warna": "#12351F",
     "tanggal_pelaksanaan": "14 - 15 November 2026", "anggota_tim": "3-5 Anggota",
     "deskripsi": "Kompetisi robotika tingkat mahasiswa. Peserta merancang dan memprogram robot "
                  "untuk menyelesaikan misi pada arena yang sudah ditentukan panitia.",
     "syarat": ["Peserta merupakan mahasiswa aktif D3/S1.",
                "Satu tim terdiri dari 3-5 orang.",
                "Robot dibuat sendiri oleh tim dan dibawa saat final."],
     "link": "https://example.com/robotics-daftar", "diunggah_hari_lalu": 9, "dilihat": 120},
    {"id": 2, "judul": "Lomba UI/UX Nasional", "penyelenggara": "HMIF ITB",
     "kategori": "UI/UX", "sisa_hari": 2, "warna": "#1B2A5C",
     "tanggal_pelaksanaan": "15 - 16 Oktober 2026", "anggota_tim": "2-4 Anggota",
     "deskripsi": "Kompetisi nasional bidang desain antarmuka untuk pelajar SMA/SMK dan mahasiswa. "
                  "Peserta merancang prototipe aplikasi yang menjawab masalah nyata.",
     "syarat": ["Peserta merupakan siswa/i SMA/SMK sederajat atau mahasiswa.",
                "Peserta wajib melakukan pendaftaran sesuai ketentuan yang telah ditetapkan panitia.",
                "Pendaftaran dilaksanakan secara online.",
                "Peserta wajib membayar biaya pendaftaran sebesar Rp35.000.",
                "Karya dikumpulkan dalam rentang waktu yang ditentukan panitia."],
     "link": "https://example.com/uiux-daftar", "diunggah_hari_lalu": 20, "dilihat": 340},
    {"id": 3, "judul": "Lomba Essay Kesehatan", "penyelenggara": "Poltekkes Denpasar",
     "kategori": "Essay", "sisa_hari": 30, "warna": "#7A3B1D",
     "tanggal_pelaksanaan": "20 Desember 2026", "anggota_tim": "Individu",
     "deskripsi": "Lomba menulis esai ilmiah populer bertema kesehatan masyarakat.",
     "syarat": ["Peserta merupakan mahasiswa aktif.",
                "Esai orisinal dan belum pernah dipublikasikan.",
                "Panjang esai 1.000-1.500 kata."],
     "link": "https://example.com/essay-daftar", "diunggah_hari_lalu": 3, "dilihat": 45},
    {"id": 4, "judul": "Byteon Coding Championship", "penyelenggara": "HMIT ITS",
     "kategori": "Coding", "sisa_hari": 2, "warna": "#0F3B2E",
     "tanggal_pelaksanaan": "27 Januari 2027", "anggota_tim": "2-3 Anggota",
     "deskripsi": "Kompetisi pemrograman kompetitif tingkat nasional. Peserta menyelesaikan soal "
                  "algoritma dan struktur data dalam waktu terbatas.",
     "syarat": ["Peserta merupakan mahasiswa aktif D3/S1.",
                "Satu tim terdiri dari 2-3 orang.",
                "Peserta wajib membawa laptop sendiri."],
     "link": "https://example.com/byteon-daftar", "diunggah_hari_lalu": 14, "dilihat": 88},
    {"id": 5, "judul": "Hackathon Competition 2026", "penyelenggara": "Dev Community",
     "kategori": "Hackathon", "sisa_hari": 14, "warna": "#0E4D64",
     "tanggal_pelaksanaan": "28 - 29 November 2026", "anggota_tim": "2-4 Anggota",
     "deskripsi": "Kompetisi membangun solusi digital untuk masalah kampus dalam waktu 24 jam. "
                  "Terbuka untuk seluruh mahasiswa, tim maksimal 4 orang.",
     "syarat": ["Peserta merupakan mahasiswa aktif D3/S1.",
                "Tim terdiri dari 2-4 orang, boleh lintas program studi.",
                "Peserta wajib membawa laptop sendiri.",
                "Hasil karya dinilai oleh dewan juri pada hari final."],
     "link": "https://example.com/hackathon-daftar", "diunggah_hari_lalu": 1, "dilihat": 210},
]

# Atribut tambahan tiap lomba untuk Filter Lomba (data contoh; nanti diisi dari form Unggah).
# jenjang = daftar (boleh lebih dari satu); lainnya = satu nilai.
_ATRIBUT_FILTER = {
    1: {"jenjang": ["Mahasiswa"], "jenis": "Lainnya", "cakupan": "Lokal/Regional", "biaya": "Gratis"},
    2: {"jenjang": ["SMA/SMK/Sederajat", "Mahasiswa"], "jenis": "Desain/UI-UX", "cakupan": "Nasional", "biaya": "Berbayar"},
    3: {"jenjang": ["Mahasiswa"], "jenis": "KTI/PKM", "cakupan": "Nasional", "biaya": "Gratis"},
    4: {"jenjang": ["Mahasiswa"], "jenis": "Lainnya", "cakupan": "Lokal/Regional", "biaya": "Gratis"},
    5: {"jenjang": ["Mahasiswa"], "jenis": "Hackathon", "cakupan": "Nasional", "biaya": "Berbayar"},
}
for _lomba in lomba_list:
    _lomba.update(_ATRIBUT_FILTER.get(_lomba["id"], {}))

# Gambar poster tiap lomba: taruh file-nya di folder assets/poster/. Yang ditulis di sini adalah
# NAMA FILE TANPA EKSTENSI (boleh png / jpg / jpeg / webp). Satu lomba boleh punya beberapa nama
# alternatif; yang pertama ditemukan di folder itulah yang dipakai.
# Kalau tidak ada satu pun, aplikasi otomatis memakai blok warna + judul sebagai cadangan.
_POSTER = {
    1: ["robotics", "robotik"],                                   # Code & Create: Robotics
    2: ["uiux", "informatic", "informatik"],                      # Lomba UI/UX Nasional
    3: ["essay"],                                                 # Lomba Essay Kesehatan
    4: ["byteon"],                                                # Byteon Coding Championship
    5: ["zephyr", "zackhaton", "zakhaton", "hackathon"],          # Hackathon Competition
}
for _lomba in lomba_list:
    _lomba["poster"] = _POSTER.get(_lomba["id"], [])

# Grup Filter Lomba: (kunci, judul, pilihan, hanya_satu). "Semua" = tanpa batasan.
FILTER_LOMBA_GRUP = [
    ("jenjang", "Jenjang", ["SMA/SMK/Sederajat", "Mahasiswa"], False),
    ("jenis", "Jenis Lomba", ["Hackathon", "KTI/PKM", "Desain/UI-UX", "Lainnya"], False),
    ("cakupan", "Cakupan", ["Lokal/Regional", "Nasional", "Internasional"], False),
    ("biaya", "Biaya Pendaftaran", ["Gratis", "Berbayar", "Semua"], True),
    ("anggota", "Anggota Tim", ["Individu", "2-3 Anggota", "4-6 Anggota", "Lainnya"], False),
]
_RENTANG_ANGGOTA = {"Individu": (1, 1), "2-3 Anggota": (2, 3), "4-6 Anggota": (4, 6)}

URUTAN_LOMBA_DEFAULT = "Deadline terdekat"
URUTAN_LOMBA = ["Deadline terdekat", "Baru diunggah", "Paling populer"]

# Notifikasi contoh (nanti dibuat otomatis: partner tertarik, postingan disetujui/perlu revisi)
# jenis: "partner" | "disetujui" | "revisi"; menit_lalu dipakai untuk pengelompokan & teks waktu
notifikasi_list = [
    {"id": 1, "jenis": "partner", "nama": "Marques Hellim", "email": "marques@teamup.com",
     "lomba": "Lomba UI/UX Nasional", "menit_lalu": 10, "dibaca": False},
    {"id": 2, "jenis": "disetujui", "judul": "Lomba UI/UX Nasional 2026",
     "menit_lalu": 120, "dibaca": False},
    {"id": 3, "jenis": "revisi", "judul": "Business Case Competition",
     "menit_lalu": 2 * 24 * 60, "dibaca": True},
]

# Postingan lomba yang diunggah user (Unggah Postingan -> Postingan Saya).
# status: "Ditangguhkan" (sedang ditinjau admin) | "Disetujui" | "Revisi" | "Ditolak"
# alasan_singkat = ringkasan 1 baris di daftar; catatan_admin = penjelasan lengkap dari admin.
# bagian_diperbaiki = field yang ditandai admin (saat ini hanya "link").
STATUS_POSTINGAN = ["Ditangguhkan", "Disetujui", "Revisi", "Ditolak"]
KATEGORI_POSTINGAN = ["Hackathon", "Desain/UI-UX", "KTI/PKM", "Lomba Bisnis",
                      "Seni & Sastra", "Debat", "Robotics", "Lainnya"]


def _postingan_baru(post_id, data):
    """Bungkus data form menjadi satu postingan lengkap (status awal: Ditangguhkan)."""
    return {
        "id": post_id, "judul": data["judul"], "kategori": data["kategori"],
        "penyelenggara": data["penyelenggara"], "deskripsi": data["deskripsi"],
        "tanggal_lomba": data["tanggal_lomba"], "tenggat_lomba": data["tenggat_lomba"],
        "link": data["link"], "kontak": data["kontak"],
        "poster": data["poster"], "dokumen": data["dokumen"],
        "status": "Ditangguhkan", "diunggah_hari_lalu": 0,
        "dilihat": 0, "tersimpan": 0, "partner_tertarik": 0,
        "alasan_singkat": "", "catatan_admin": "", "catatan_hari_lalu": 0,
        "bagian_diperbaiki": "",
    }


postingan_list = [
    {"id": 1, "judul": "Lomba UI/UX Nasional 2026", "kategori": "Desain/UI-UX",
     "penyelenggara": "DPTII FT UNY",
     "deskripsi": "Kompetisi nasional bidang desain antarmuka untuk pelajar SMA/SMK dan mahasiswa. "
                  "Peserta merancang prototipe aplikasi yang menjawab masalah nyata.",
     "tanggal_lomba": date(2026, 10, 12), "tenggat_lomba": date(2026, 10, 20),
     "link": "https://example.com/uiux-daftar", "kontak": "081234567824",
     "poster": "poster_uiux.pdf", "dokumen": "surat_tugas.pdf",
     "status": "Disetujui", "diunggah_hari_lalu": 2,
     "dilihat": 248, "tersimpan": 6, "partner_tertarik": 3,
     "alasan_singkat": "", "catatan_admin": "", "catatan_hari_lalu": 0, "bagian_diperbaiki": ""},
    {"id": 2, "judul": "Hackathon Kampus 2026", "kategori": "Hackathon",
     "penyelenggara": "DPTEI FT UNY",
     "deskripsi": "Kompetisi membangun solusi digital untuk masalah kampus dalam waktu 24 jam. "
                  "Terbuka untuk seluruh mahasiswa UNY, tim maksimal 4 orang.",
     "tanggal_lomba": date(2026, 10, 12), "tenggat_lomba": date(2026, 10, 20),
     "link": "https://uii.ac.id/lomba-daftar", "kontak": "081234567824",
     "poster": "poster_hackathon.pdf", "dokumen": "",
     "status": "Ditangguhkan", "diunggah_hari_lalu": 1,
     "dilihat": 0, "tersimpan": 0, "partner_tertarik": 0,
     "alasan_singkat": "", "catatan_admin": "", "catatan_hari_lalu": 0, "bagian_diperbaiki": ""},
    {"id": 3, "judul": "Business Case Competition", "kategori": "Lomba Bisnis",
     "penyelenggara": "BINUS University",
     "deskripsi": "Kompetisi menganalisis studi kasus bisnis nyata dari industri untuk mahasiswa "
                  "se-Indonesia. Tim menyusun strategi solusi (marketing, keuangan, atau operasional) "
                  "dan mempresentasikannya di hadapan juri praktisi bisnis dan akademisi.",
     "tanggal_lomba": date(2026, 10, 12), "tenggat_lomba": date(2026, 10, 20),
     "link": "https://uui.ac/id/bcc-daftar", "kontak": "086677882424",
     "poster": "poster_bcc.pdf", "dokumen": "surat_resmi.pdf",
     "status": "Revisi", "diunggah_hari_lalu": 4,
     "dilihat": 0, "tersimpan": 0, "partner_tertarik": 0,
     "alasan_singkat": "link pendaftaran tidak valid",
     "catatan_admin": "Link pendaftaran yang dicantumkan tidak dapat diakses (404). Mohon perbaiki "
                      "tautan ini dan pastikan link merupakan tautan pendaftaran resmi.",
     "catatan_hari_lalu": 1, "bagian_diperbaiki": "link"},
    {"id": 4, "judul": "Lomba Essay Ilmiah", "kategori": "Seni & Sastra",
     "penyelenggara": "Komunitas Literasi Nusantara",
     "deskripsi": "Lomba menulis essay ilmiah bertema inovasi pendidikan untuk mahasiswa.",
     "tanggal_lomba": date(2026, 11, 2), "tenggat_lomba": date(2026, 10, 25),
     "link": "https://example.com/essay-daftar", "kontak": "081200001111",
     "poster": "poster_essay.pdf", "dokumen": "",
     "status": "Ditolak", "diunggah_hari_lalu": 6,
     "dilihat": 0, "tersimpan": 0, "partner_tertarik": 0,
     "alasan_singkat": "penyelenggara tidak terverifikasi",
     "catatan_admin": "Kontak dan dokumen pendukung penyelenggara tidak dapat diverifikasi. Kami tidak "
                      "menemukan bukti resmi bahwa lomba ini diselenggarakan oleh pihak yang tercantum.",
     "catatan_hari_lalu": 1, "bagian_diperbaiki": ""},
]

history = []             # id lomba yang pernah dibuka (untuk halaman Riwayat)
current_user = None      # user yang sedang login
remembered_email = ""    # untuk checkbox "Ingat saya"
reset_email = ""         # email yang sedang reset password
otp_code = ""            # kode OTP terakhir yang dibuat


def find_user(email, password):
    for user in users:
        if user["email"].lower() == email.lower() and user["password"] == password:
            return user
    return None


def get_user(email):
    """Ambil record user ASLI dari daftar users berdasarkan email.
    (Signal(dict) di PySide6 mengirim SALINAN dict, jadi listener harus
    mencari lagi record aslinya supaya perubahan tersimpan di data_store.)"""
    for user in users:
        if user["email"].lower() == email.lower():
            return user
    return None


def email_exists(email):
    for user in users:
        if user["email"].lower() == email.lower():
            return True
    return False


def username_exists(username, except_user=None):
    for user in users:
        if user is not except_user and user["username"].lower() == username.lower():
            return True
    return False


def add_user(nama, email, password):
    user = {
        "nama": nama,
        "email": email,
        "password": password,
        "username": "",
        "prodi": "",
        "universitas": "",
        "domisili": "",
        "bio": "",
        "keahlian": [],
        "instagram": "",
        "pengalaman": [],
        "foto": "",
    }
    users.append(user)
    return user


def generate_otp(email):
    """Buat kode OTP 4 digit (simulasi, tidak benar-benar dikirim lewat email)."""
    global reset_email, otp_code
    reset_email = email
    otp_code = f"{random.randint(0, 9999):04d}"
    return otp_code


def update_password(email, new_password):
    for user in users:
        if user["email"].lower() == email.lower():
            user["password"] = new_password


def is_biodata_complete(user):
    return (user["username"] != "" and user["prodi"] != ""
            and user["universitas"] != "" and user["domisili"] != "")


def get_lomba(lomba_id):
    for lomba in lomba_list:
        if lomba["id"] == lomba_id:
            return lomba
    return None


def get_upcoming(count):
    """Lomba dengan tenggat terdekat."""
    return sorted(lomba_list, key=lambda lomba: lomba["sisa_hari"])[:count]


def add_to_history(lomba_id):
    """Dicatat setiap lomba dibuka; yang terbaru di urutan pertama."""
    if lomba_id in history:
        history.remove(lomba_id)
    history.insert(0, lomba_id)


def _cocok_kategori(user, kategori_dipilih):
    """True kalau salah satu keahlian user cocok dengan salah satu kategori terpilih."""
    for kategori in kategori_dipilih:
        for keahlian in user["keahlian"]:
            for kata_kunci in KATEGORI_PARTNER[kategori]:
                if kata_kunci in keahlian.lower():
                    return True
    return False


def get_partners(kategori_dipilih=(), urutan=URUTAN_DEFAULT):
    """Daftar calon rekan tim (bukan user yang sedang login, biodata lengkap, punya keahlian).
    kategori_dipilih kosong = semua kategori. urutan: 'Cari Rekan' (urutan asli), 'Nama A-Z', 'Nama Z-A'."""
    hasil = []
    for user in users:
        if current_user is not None and user["email"] == current_user["email"]:
            continue
        if not is_biodata_complete(user) or len(user["keahlian"]) == 0:
            continue
        if len(kategori_dipilih) > 0 and not _cocok_kategori(user, kategori_dipilih):
            continue
        hasil.append(user)

    if urutan == "Nama A-Z":
        hasil.sort(key=lambda user: user["nama"].lower())
    elif urutan == "Nama Z-A":
        hasil.sort(key=lambda user: user["nama"].lower(), reverse=True)
    return hasil


# Kategori lomba -> kata kunci yang dicari pada keahlian user (Bagian 6.3 alur:
# panel "Profil yang Disarankan" di Halaman Detail Lomba). Beda dengan KATEGORI_PARTNER
# (dipakai di halaman Rekan Tim) karena di sini kategorinya mengikuti kategori LOMBA.
KATEGORI_LOMBA_KEAHLIAN = {
    "Robotics": ["robot", "elektro", "mekanik", "embedded", "hardware", "programmer"],
    "UI/UX": ["ui/ux", "ui ux", "desain", "design", "ilustrasi"],
    "Essay": ["essay", "menulis", "penulis", "riset"],
    "Coding": ["programmer", "coding", "developer", "backend", "frontend", "algoritma", "web"],
    "Debat": ["debat", "public speaking", "komunikasi"],
    "Hackathon": ["programmer", "developer", "frontend", "backend", "coding", "fullstack"],
}


def cari_partner_sesuai_keahlian(kategori_lomba, count=3):
    """Cocokkan kategori lomba dengan keahlian user lain (real-time, dipanggil
    setiap Detail Lomba dibuka -> lihat Bagian 6.3 dokumentasi alur)."""
    kata_kunci = KATEGORI_LOMBA_KEAHLIAN.get(kategori_lomba, [])
    hasil = []
    for user in users:
        if current_user is not None and user["email"] == current_user["email"]:
            continue
        if not is_biodata_complete(user) or len(user["keahlian"]) == 0:
            continue
        cocok = any(kata in keahlian.lower() for keahlian in user["keahlian"] for kata in kata_kunci)
        if cocok:
            hasil.append(user)
        if len(hasil) >= count:
            break
    return hasil


def get_kategori_lomba():
    """Daftar kategori lomba yang ada (tanpa duplikat, urut abjad) untuk popup Kategori."""
    return sorted(set(lomba["kategori"] for lomba in lomba_list))


def get_lomba_terfilter(kategori_dipilih=(), urutan=URUTAN_LOMBA_DEFAULT):
    """Lomba sesuai kategori terpilih (kosong = semua), diurutkan menurut 'urutan'."""
    hasil = [lomba for lomba in lomba_list
             if len(kategori_dipilih) == 0 or lomba["kategori"] in kategori_dipilih]
    if urutan == "Baru diunggah":
        hasil.sort(key=lambda lomba: lomba["diunggah_hari_lalu"])
    elif urutan == "Paling populer":
        hasil.sort(key=lambda lomba: lomba["dilihat"], reverse=True)
    else:
        hasil.sort(key=lambda lomba: lomba["sisa_hari"])
    return hasil


def _rentang_tim(teks):
    """'2-4 Anggota' -> (2, 4); 'Individu' -> (1, 1); '3 Anggota' -> (3, 3)."""
    if teks.lower().startswith("individu"):
        return (1, 1)
    angka = [int(x) for x in "".join(c if c.isdigit() else " " for c in teks).split()]
    if not angka:
        return (0, 0)
    return (min(angka), max(angka))


def _cocok_anggota(lomba, pilihan):
    """True kalau rentang anggota lomba beririsan dengan salah satu pilihan."""
    awal, akhir = _rentang_tim(lomba["anggota_tim"])
    for opsi in pilihan:
        if opsi == "Lainnya":
            if not any(awal <= b and akhir >= a for a, b in _RENTANG_ANGGOTA.values()):
                return True
        else:
            a, b = _RENTANG_ANGGOTA[opsi]
            if awal <= b and akhir >= a:
                return True
    return False


def get_lomba_filter(filter_dipilih, urutan=URUTAN_LOMBA_DEFAULT):
    """Filter Lomba bertingkat: nilai dalam satu grup = ATAU, antar grup = DAN.
    filter_dipilih: {kunci_grup: [pilihan, ...]}; grup kosong / 'Semua' = tanpa batasan."""
    hasil = []
    for lomba in lomba_list:
        cocok = True
        for kunci, pilihan in filter_dipilih.items():
            pilihan = [p for p in pilihan if p != "Semua"]
            if not pilihan:
                continue
            if kunci == "jenjang":
                cocok = any(p in lomba.get("jenjang", []) for p in pilihan)
            elif kunci == "anggota":
                cocok = _cocok_anggota(lomba, pilihan)
            else:
                cocok = lomba.get(kunci) in pilihan
            if not cocok:
                break
        if cocok:
            hasil.append(lomba)
    if urutan == "Baru diunggah":
        hasil.sort(key=lambda lomba: lomba["diunggah_hari_lalu"])
    elif urutan == "Paling populer":
        hasil.sort(key=lambda lomba: lomba["dilihat"], reverse=True)
    else:
        hasil.sort(key=lambda lomba: lomba["sisa_hari"])
    return hasil


def get_postingan(status=None):
    """Postingan milik user. status=None -> semua; selain itu hanya yang statusnya cocok."""
    return [post for post in postingan_list if status is None or post["status"] == status]


def get_postingan_by_id(post_id):
    for post in postingan_list:
        if post["id"] == post_id:
            return post
    return None


def tambah_postingan(data):
    """Postingan baru dari form Unggah Info Lomba -> status Ditangguhkan, paling atas."""
    post_id = max([post["id"] for post in postingan_list], default=0) + 1
    post = _postingan_baru(post_id, data)
    postingan_list.insert(0, post)
    return post


def kirim_ulang_postingan(post_id, data):
    """Perbaikan dari status Revisi -> data diganti, status kembali Ditangguhkan."""
    post = get_postingan_by_id(post_id)
    post.update(data)
    post["status"] = "Ditangguhkan"
    post["diunggah_hari_lalu"] = 0
    post["alasan_singkat"] = ""
    post["catatan_admin"] = ""
    post["bagian_diperbaiki"] = ""
    return post


def hapus_postingan(post_id):
    """Dipakai untuk 'Batalkan pengajuan' (Ditangguhkan) dan 'Hapus pengajuan' (Revisi / Ditolak)."""
    post = get_postingan_by_id(post_id)
    if post is not None:
        postingan_list.remove(post)


def hitung_postingan():
    """{'Semua': 4, 'Ditangguhkan': 1, ...} untuk angka di chip filter."""
    hasil = {"Semua": len(postingan_list)}
    for status in STATUS_POSTINGAN:
        hasil[status] = len(get_postingan(status))
    return hasil


def get_notifikasi(hanya_belum_dibaca=False):
    """Notifikasi terbaru di atas. hanya_belum_dibaca=True -> untuk tab 'Belum dibaca'."""
    hasil = [n for n in notifikasi_list if not (hanya_belum_dibaca and n["dibaca"])]
    return sorted(hasil, key=lambda n: n["menit_lalu"])


def get_notifikasi_by_id(notif_id):
    for notif in notifikasi_list:
        if notif["id"] == notif_id:
            return notif
    return None


def tandai_dibaca(notif_id):
    notif = get_notifikasi_by_id(notif_id)
    if notif is not None:
        notif["dibaca"] = True


def get_history():
    """Lomba yang pernah dibuka user, yang terbaru di atas."""
    return [get_lomba(lomba_id) for lomba_id in history]
