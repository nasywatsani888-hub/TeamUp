# config.py — pengaturan umum aplikasi TeamUp
import os

APP_NAME = "TeamUp"
WINDOW_WIDTH = 1320
WINDOW_HEIGHT = 720
# Lebar minimum: di bawah ini isi dashboard tidak muat (tanpa scroll kanan-kiri)
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 600

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Aturan upload poster lomba (sesuai dokumen alur)
MAX_POSTER_SIZE_MB = 10

# Warna (disesuaikan dengan tampilan yang kamu kirim)
COLOR_PRIMARY = "#0A7BCB"
COLOR_PRIMARY_HOVER = "#0868AF"
COLOR_NAVY = "#0F2E6B"
COLOR_LEFT_BG = "#E6FAFF"
COLOR_LOGO_DARK = "#0A7BCB"
COLOR_LOGO_LIGHT = "#3AA8DE"
COLOR_BG = "#FFFFFF"
COLOR_TEXT = "#1F2937"
COLOR_SUBTEXT = "#6B7C93"
COLOR_BORDER = "#CBD6E2"
COLOR_ERROR = "#DC2626"
COLOR_SUCCESS = "#22A15E"

# Aturan upload file Pengalaman & Prestasi (Edit Profil)
MAX_ATTACHMENT_SIZE_MB = 10
ATTACHMENT_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")

# Pusat Bantuan
HELP_PHONE = "0812-3456-7890"
HELP_HOURS = "Setiap hari, 08.00 - 20.00 WIB"

# Warna link (mis. "Link pendaftaran" di Detail Lomba) -- ubah kode hex di sini
COLOR_LINK = "#000000"
