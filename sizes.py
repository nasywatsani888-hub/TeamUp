# sizes.py — SEMUA ukuran (lebar, tinggi, jarak) dikumpulkan di sini,
# supaya kamu dan tim tinggal ubah angkanya di SATU tempat ini tanpa
# perlu mencari-cari ke setiap file views/*.py satu per satu.
#
# Pola file ini sama seperti config.py (kumpulan warna) dan styles.py
# (kumpulan tampilan/CSS) -- bedanya file ini khusus untuk ANGKA UKURAN
# dalam piksel (lebar, tinggi, jarak antar elemen).
#
# Cara pakai di file lain:
#   import sizes
#   sidebar.setFixedWidth(sizes.SIDEBAR_WIDTH)

# ---------- Kerangka dashboard (sidebar & panel kanan) ----------
SIDEBAR_WIDTH = 242             # views/sidebar.py
RIGHT_PANEL_WIDTH = 360        # panel Rekomendasi Rekan di views/lomba_detail_page.py
RIGHT_PANEL_BREAKPOINT = 960   # lebar halaman isi di bawah ini -> kolom kanan disembunyikan
SIDEBAR_PROFILE_HEIGHT = 84      # tinggi kartu profil di sidebar
SIDEBAR_AVATAR_SIZE = 48         # views/sidebar.py (kartu profil di sidebar)
CONTENT_MARGIN = 32            # jarak tepi kolom tengah di tiap halaman dashboard

# ---------- Kartu Lomba (dipakai di Beranda & halaman Lomba) ----------
LOMBA_CARD_WIDTH = 230
LOMBA_CARD_MIN_WIDTH = 150     # lebar minimum sebelum di-setFixedWidth
LOMBA_CARD_SPACING = 20
LOMBA_POSTER_HEIGHT = 200      # tinggi gambar poster di bagian atas kartu

# ---------- Detail Lomba: poster di header ----------
DETAIL_POSTER_WIDTH = 190      # views/lomba_detail_page.py
DETAIL_POSTER_HEIGHT = 240

# ---------- Kartu Rekan Tim (halaman Rekan Tim) ----------
PARTNER_CARD_WIDTH = 190
PARTNER_CARD_HEIGHT = 330
PARTNER_CARD_SPACING = 20

# ---------- Panel kanan: kartu profil & tenggat pendaftaran ----------
RIGHT_PANEL_AVATAR_SIZE = 76
RIGHT_PANEL_BAR_WIDTH = 6      # garis warna kecil di kartu tenggat

# ---------- Edit Profil ----------
EDIT_PROFILE_HEADER_HEIGHT = 120
EDIT_PROFILE_BANNER_HEIGHT = 72
EDIT_PROFILE_AVATAR_SIZE = 90
EDIT_PROFILE_CAMERA_BUTTON_SIZE = 24
EDIT_PROFILE_BIO_HEIGHT = 110
EDIT_PROFILE_ADD_BUTTON_SIZE = 26

# ---------- Filter dropdown (Kategori / Urutkan) ----------
FILTER_POPUP_WIDTH = 280
FILTER_POPUP_HEIGHT = 280
FILTER_BUTTON_MIN_WIDTH = 150

# ---------- Notifikasi & Riwayat ----------
NOTIFICATION_ICON_SIZE = 40
NOTIFICATION_DOT_SIZE = 8
HISTORY_ICON_SIZE = 40

# ---------- Pusat Bantuan ----------
HELP_CARD_WIDTH = 350
HELP_ICON_SIZE = 52

# ---------- Dialog (Keluar & Unggah) ----------
LOGOUT_DIALOG_WIDTH = 390
LOGOUT_DIALOG_HEIGHT = 270
LOGOUT_ICON_SIZE = 52
UPLOAD_DIALOG_WIDTH = 440
UPLOAD_DIALOG_HEIGHT = 320

# ---------- Halaman Masuk (Login) ----------
LOGIN_TITLE_FONT = 25
LOGIN_TABS_FRAME_WIDTH = 171
LOGIN_TABS_FRAME_HEIGHT = 50
LOGIN_TABS_PILL_WIDTH = 72
LOGIN_TABS_PILL_HEIGHT = 32
LOGIN_FIELD_WIDTH = 320
LOGIN_FIELD_HEIGHT = 40
LOGIN_LABEL_FONT = 13
LOGIN_BUTTON_FONT = 16

# ---------- Lupa Password: kotak OTP ----------
OTP_BOX_WIDTH = 64
OTP_BOX_HEIGHT = 72

# ---------- Lengkapi Biodata ----------
BIODATA_BIO_HEIGHT = 110

# ---------- Unggah Postingan ----------
POST_THUMB_SIZE = 44           # kotak gambar kecil di tiap baris postingan
POST_BADGE_WIDTH = 100         # lebar badge status (Disetujui / Revisi / ...)

# ---------- Dialog Postingan ----------
CONFIRM_DIALOG_WIDTH = 480      # views/post_dialogs.py (Batalkan / Hapus pengajuan)
CONFIRM_DIALOG_HEIGHT = 400
EDIT_BLOCKED_DIALOG_WIDTH = 500 # dialog "tidak bisa edit saat diverifikasi"
EDIT_BLOCKED_DIALOG_HEIGHT = 190
POST_FORM_FILE_HEIGHT = 120     # tinggi kotak tarik-atau-pilih file di formulir
