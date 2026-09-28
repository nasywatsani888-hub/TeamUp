# data_store.py — data SEMENTARA di memori (tanpa database)
# Data hilang saat aplikasi ditutup. Database baru dipakai di pertemuan 9.
import random

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
        "foto": "",
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
        "foto": "",
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
    {"id": 4, "judul": "Lomba Debat Bahasa", "penyelenggara": "UKM Bahasa",
     "kategori": "Debat", "sisa_hari": 5, "warna": "#5B2A6B",
     "tanggal_pelaksanaan": "1 November 2026", "anggota_tim": "3 Anggota",
     "deskripsi": "Debat bahasa Indonesia format parlementer antar universitas.",
     "syarat": ["Peserta merupakan mahasiswa aktif.",
                "Satu tim terdiri dari 3 orang dari universitas yang sama."],
     "link": "https://example.com/debat-daftar", "diunggah_hari_lalu": 14, "dilihat": 88},
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
