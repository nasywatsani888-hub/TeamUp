# main.py — titik masuk aplikasi TeamUp
# MainWindow = "pusat listener": semua halaman mengirim signal ke sini,
# lalu MainWindow yang menentukan halaman berikutnya (loose coupling).
import gc
import os
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
import sys
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

import config
import styles
import data_store
import helpers
import preload
import workers
from views.login_page import LoginPage
from views.register_page import RegisterPage
from views.success_page import SuccessPage
from views.biodata_page import BiodataPage
from views.reset_password_pages import ForgotPasswordPage, OtpPage, NewPasswordPage
from views.dashboard_page import DashboardPage
from views.splash_page import SplashPage


def load_fonts():
    """Muat semua file .ttf di assets/fonts (mis. Poppins) kalau ada."""
    fonts_dir = os.path.join(config.ASSETS_DIR, "fonts")
    if os.path.isdir(fonts_dir):
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, filename))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Buat semua halaman SATU kali (halaman pertama = yang tampil awal)
        self.login_page = LoginPage()
        self.register_page = RegisterPage()
        self.account_created_page = SuccessPage("Berhasil membuat akun!", "Lanjutkan")
        self.biodata_page = BiodataPage()
        self.forgot_page = ForgotPasswordPage()
        self.otp_page = OtpPage()
        self.new_password_page = NewPasswordPage()
        self.password_updated_page = SuccessPage("Password Berhasil di Perbarui!", "Kembali")
        self.dashboard_page = DashboardPage()
        self.splash_page = SplashPage()

        for page in (self.login_page, self.register_page, self.account_created_page,
                     self.biodata_page, self.forgot_page, self.otp_page,
                     self.new_password_page, self.password_updated_page, self.dashboard_page,
                     self.splash_page):
            self.stack.addWidget(page)

        self.connect_signals()

        # Preload foto & poster di latar belakang (lihat preload.py). Dimulai SETELAH semua halaman jadi
        # (singleShot(0) = "begitu event loop mulai berputar"), supaya tidak berebut CPU dengan
        # pembangunan halaman dan memperlambat startup. User masih di splash / login selama beberapa detik,
        # waktu yang cukup bagi worker untuk menyelesaikannya.
        QTimer.singleShot(0, preload.mulai)

    def connect_signals(self):
        # Tab Masuk | Daftar
        for page in (self.login_page, self.register_page):
            page.go_login.connect(lambda: self.show_page(self.login_page))
            page.go_register.connect(lambda: self.show_page(self.register_page))

        # Masuk
        self.login_page.login_success.connect(self.handle_login_success)
        self.login_page.forgot_password_clicked.connect(lambda: self.show_page(self.forgot_page))
        self.login_page.admin_login_clicked.connect(self.handle_admin_login)

        # Daftar -> Berhasil -> Lengkapi Biodata -> Beranda
        self.register_page.register_success.connect(self.handle_register_success)
        self.account_created_page.button_clicked.connect(lambda: self.show_page(self.biodata_page))
        self.biodata_page.biodata_saved.connect(self.handle_biodata_saved)

        # Lupa password -> OTP -> Password baru -> Berhasil -> Login
        self.forgot_page.email_submitted.connect(self.handle_email_submitted)
        self.forgot_page.back_clicked.connect(lambda: self.show_page(self.login_page))
        self.otp_page.otp_verified.connect(lambda: self.show_page(self.new_password_page))
        self.new_password_page.password_updated.connect(lambda: self.show_page(self.password_updated_page))
        self.password_updated_page.button_clicked.connect(lambda: self.show_page(self.login_page))

        # Dashboard
        self.dashboard_page.logout_requested.connect(self.handle_logout)

    def show_page(self, page):
        self.stack.setCurrentWidget(page)

    def closeEvent(self, event):
        """Aplikasi ditutup: minta semua worker berhenti dan tunggu sebentar. Kalau tidak, Qt bisa
        menutup saat thread masih jalan ('QThread: Destroyed while thread is still running')."""
        workers.tunggu_selesai(3000)
        super().closeEvent(event)

    # --- Listener (slot) ---
    def handle_login_success(self, user_data):
        user = data_store.get_user(user_data["email"])   # record asli, bukan salinan signal
        data_store.current_user = user
        if data_store.is_biodata_complete(user):
            self.show_page(self.dashboard_page)
        else:
            self.show_page(self.biodata_page)   # login pertama: wajib lengkapi biodata

    def handle_register_success(self, user_data):
        data_store.current_user = data_store.get_user(user_data["email"])   # biodata disimpan ke akun ini
        self.show_page(self.account_created_page)

    def handle_biodata_saved(self, user_data):
        data_store.current_user = data_store.get_user(user_data["email"])
        self.show_page(self.dashboard_page)   # ganti ke self.login_page kalau mau balik ke Login dulu

    def handle_email_submitted(self, email):
        code = data_store.generate_otp(email)
        QMessageBox.information(
            self, "Simulasi Email",
            f"Kode OTP kamu: {code}\n\n(Simulasi — aplikasi belum benar-benar mengirim email.)")
        self.show_page(self.otp_page)

    def handle_admin_login(self):
        QMessageBox.information(self, "Login Sebagai Admin", "Halaman admin akan dibuat di tahap berikutnya.")

    def handle_logout(self):
        # Konfirmasi "Yakin mau keluar?" sudah dijawab di DashboardPage; di sini tinggal keluar
        data_store.current_user = None
        # Pembersihan manual: lepas cache gambar milik user lama, lalu paksa garbage collector
        # menyapu objek yang sudah tidak terpakai (aman dilakukan di sini karena user sedang menunggu splash).
        helpers.clear_image_cache()
        gc.collect()
        self.show_page(self.splash_page)                                    # logo TeamUp sebentar
        QTimer.singleShot(1500, lambda: self.show_page(self.login_page))    # lalu Halaman Login


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_fonts()
    app.setStyleSheet(styles.APP_STYLE)
    window = MainWindow()
    app.aboutToQuit.connect(workers.tunggu_selesai)   # pengaman kedua: keluar lewat Cmd+Q / app.quit() juga menunggu worker
    window.showMaximized()
    sys.exit(app.exec())
