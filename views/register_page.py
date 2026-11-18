# views/register_page.py — halaman Daftar
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QWidget
from views.auth_page import AuthPage
from views.loading_button import LoadingButton
import config
import data_store
import helpers
import penanganan_error
import sizes
import styles
import validasi


REGISTER_FIELD = (sizes.LOGIN_FIELD_WIDTH, sizes.LOGIN_FIELD_HEIGHT)


class RegisterPage(AuthPage):
    register_success = Signal(dict)

    def __init__(self):
        super().__init__()
        # Ukuran proporsional mengikuti standar halaman Masuk (sizes.py)
        self.add_title("Selamat bergabung!", "Isi data diri untuk mulai menggunakan aplikasi",
                       title_size=sizes.LOGIN_TITLE_FONT, subtitle_size=13)
        self.add_tabs("register", frame_size=(sizes.LOGIN_TABS_FRAME_WIDTH, sizes.LOGIN_TABS_FRAME_HEIGHT),
                      pill_size=(sizes.LOGIN_TABS_PILL_WIDTH, sizes.LOGIN_TABS_PILL_HEIGHT))

        input_style = f"""
QLineEdit {{
    background-color: white; border: 1px solid {config.COLOR_BORDER};
    border-radius: 10px; padding: 0 16px;
}}
QLineEdit:focus {{ border: 1px solid {config.COLOR_PRIMARY}; }}
"""

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama lengkap Anda")
        self.name_input.setStyleSheet(input_style)
        self.add_field("Nama lengkap", self.name_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=REGISTER_FIELD)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("nama@email.com")
        self.email_input.setStyleSheet(input_style)
        self.add_field("Email", self.email_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=REGISTER_FIELD)

        self.password_input = helpers.PasswordField(validasi.ATURAN_PASSWORD)
        self.add_field("Password", self.password_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=REGISTER_FIELD)
        self.password_input.input.setStyleSheet("border: none; background: transparent; padding: 0 8px 0 16px;")

        self.confirm_input = helpers.PasswordField("Ulangi password")
        self.add_field("Konfirmasi Password", self.confirm_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=REGISTER_FIELD)
        self.confirm_input.input.setStyleSheet("border: none; background: transparent; padding: 0 8px 0 16px;")

        # Kotak checkbox syarat & ketentuan: terkunci 320px dan minimum tinggi 44px agar teks 2 baris tidak terpotong
        terms_row_box = QWidget()
        terms_row_box.setFixedWidth(sizes.LOGIN_FIELD_WIDTH)
        terms_row_box.setMinimumHeight(44)
        terms_row = QHBoxLayout(terms_row_box)
        terms_row.setContentsMargins(0, 2, 0, 2)
        terms_row.setSpacing(10)

        self.terms_checkbox = QCheckBox()
        self.terms_checkbox.setStyleSheet(f"""
QCheckBox {{ spacing: 0px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {config.COLOR_BORDER};
    border-radius: 4px; background: white;
}}
QCheckBox::indicator:checked {{
    background: {config.COLOR_PRIMARY}; border: 1px solid {config.COLOR_PRIMARY};
    image: url({styles.CHECK_ICON});
}}
""")
        terms_label = QLabel("Saya setuju dengan syarat & ketentuan serta kebijakan privasi")
        terms_label.setStyleSheet(f"font-size: 11px; color: {config.COLOR_SUBTEXT};")
        terms_label.setWordWrap(True)
        terms_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # Klik teks langsung mengaktifkan / mematikan checkbox
        terms_label.mousePressEvent = lambda ev: self.terms_checkbox.setChecked(not self.terms_checkbox.isChecked())

        terms_row.addWidget(self.terms_checkbox, alignment=Qt.AlignmentFlag.AlignTop)
        terms_row.addWidget(terms_label, 1, alignment=Qt.AlignmentFlag.AlignTop)
        self.form_layout.addWidget(terms_row_box, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        # Tombol Daftar dengan ukuran yang sama dengan tombol Masuk + animasi spinner loading
        self.register_button = LoadingButton("Daftar")
        self.register_button.setStyleSheet(f"""
QPushButton {{
    background-color: {config.COLOR_PRIMARY}; color: white; border: none;
    border-radius: 10px; padding: 0 16px; font-size: {sizes.LOGIN_BUTTON_FONT}px; font-weight: bold;
}}
QPushButton:hover {{ background-color: {config.COLOR_PRIMARY_HOVER}; }}
QPushButton:disabled {{ background-color: {config.COLOR_PRIMARY_HOVER}; color: rgba(255, 255, 255, 210); }}
""")
        self.register_button.setFixedSize(sizes.LOGIN_FIELD_WIDTH, sizes.LOGIN_FIELD_HEIGHT)
        self.register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.form_layout.addWidget(self.register_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.register_button.clicked.connect(self.handle_register)

    def handle_register(self):
        name = validasi.bersihkan_teks(self.name_input.text())
        email = validasi.normalisasi_email(self.email_input.text())
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if name == "" or email == "" or password == "" or confirm == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        pesan = validasi.periksa_nama(name) or validasi.periksa_email(email)
        if pesan:
            helpers.show_error(self.message_label, pesan)
            return
        if data_store.email_exists(email):
            helpers.show_error(self.message_label, "Email sudah terdaftar.")
            return
        pesan = validasi.periksa_password(password, email)
        if pesan:
            helpers.show_error(self.message_label, pesan)
            return
        if password != confirm:
            helpers.show_error(self.message_label, "Konfirmasi password tidak sama.")
            return
        if not self.terms_checkbox.isChecked():
            helpers.show_error(self.message_label, "Setujui syarat & ketentuan terlebih dahulu.")
            return

        # Tampilkan animasi loading & anti-double-click
        self.register_button.start_loading("Mendaftarkan...")

        def _do_register():
            try:
                user = data_store.add_user(name, email, password)
                self.register_button.stop_loading()
                self.register_success.emit(user)
            except Exception as e:
                self.register_button.stop_loading()
                helpers.show_error(self.message_label, penanganan_error.laporkan(e, "daftar akun"))

        QTimer.singleShot(250, _do_register)

    def on_show(self):
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.terms_checkbox.setChecked(False)
        self.message_label.setText("")
        self.register_button.stop_loading()
