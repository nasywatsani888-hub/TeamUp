# views/register_page.py — halaman Daftar
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit
from views.auth_page import AuthPage
import helpers
import data_store


class RegisterPage(AuthPage):
    register_success = Signal(dict)

    def __init__(self):
        super().__init__()
        self.add_title("Selamat bergabung!", "Isi data diri untuk mulai menggunakan aplikasi")
        self.add_tabs("register")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama lengkap Anda")
        self.add_field("Nama lengkap", self.name_input)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("nama@email.com")
        self.add_field("Email", self.email_input)
        self.password_input = helpers.PasswordField("Minimal 8 karakter, huruf & angka")
        self.add_field("Password", self.password_input)
        self.confirm_input = helpers.PasswordField("Ulangi password")
        self.add_field("Konfirmasi Password", self.confirm_input)

        row = QHBoxLayout()
        self.terms_checkbox = QCheckBox()
        terms_label = helpers.make_subtitle("Saya setuju dengan syarat & ketentuan serta kebijakan privasi")
        terms_label.setStyleSheet("font-size: 15px;")
        row.addWidget(self.terms_checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(terms_label, 1)
        self.form_layout.addLayout(row)

        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        self.register_button = helpers.make_primary_button("Daftar")
        self.form_layout.addWidget(self.register_button)

        self.register_button.clicked.connect(self.handle_register)

    def handle_register(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if name == "" or email == "" or password == "" or confirm == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        if "@" not in email or "." not in email:
            helpers.show_error(self.message_label, "Format email tidak valid.")
            return
        if data_store.email_exists(email):
            helpers.show_error(self.message_label, "Email sudah terdaftar.")
            return
        if not helpers.is_valid_password(password):
            helpers.show_error(self.message_label, "Password minimal 8 karakter dan mengandung huruf serta angka.")
            return
        if password != confirm:
            helpers.show_error(self.message_label, "Konfirmasi password tidak sama.")
            return
        if not self.terms_checkbox.isChecked():
            helpers.show_error(self.message_label, "Setujui syarat & ketentuan terlebih dahulu.")
            return

        user = data_store.add_user(name, email, password)
        self.register_success.emit(user)

    def on_show(self):
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.terms_checkbox.setChecked(False)
        self.message_label.setText("")
