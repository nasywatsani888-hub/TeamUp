# views/login_page.py — halaman Masuk
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget
from views.auth_page import AuthPage
import config
import sizes
import styles
import helpers
import data_store


LOGIN_FIELD = (sizes.LOGIN_FIELD_WIDTH, sizes.LOGIN_FIELD_HEIGHT)


class LoginPage(AuthPage):
    # Halaman hanya MENGIRIM signal; MainWindow yang menentukan navigasi
    login_success = Signal(dict)
    forgot_password_clicked = Signal()
    admin_login_clicked = Signal()

    def __init__(self):
        super().__init__()
        # Ukuran-ukuran di bawah mengikuti redline desain (login_ukuran.png)
        self.add_title("Hai, selamat datang kembali!", title_size=sizes.LOGIN_TITLE_FONT)
        self.add_tabs("login", frame_size=(sizes.LOGIN_TABS_FRAME_WIDTH, sizes.LOGIN_TABS_FRAME_HEIGHT),
                      pill_size=(sizes.LOGIN_TABS_PILL_WIDTH, sizes.LOGIN_TABS_PILL_HEIGHT))

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("nama@email.com")
        self.add_field("Email", self.email_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=LOGIN_FIELD)
        self.email_input.setStyleSheet(f"""
QLineEdit {{
    background-color: white; border: 1px solid {config.COLOR_BORDER};
    border-radius: 10px; padding: 0 16px;
}}
QLineEdit:focus {{ border: 1px solid {config.COLOR_PRIMARY}; }}
""")

        self.password_input = helpers.PasswordField("Masukkan password")
        self.add_field("Password", self.password_input, label_size=sizes.LOGIN_LABEL_FONT, field_size=LOGIN_FIELD)
        self.password_input.input.setStyleSheet("border: none; background: transparent; padding: 0 8px 0 16px;")

        # Baris "Ingatkan saya" & "Lupa password?" dibungkus selebar 320 juga,
        # supaya rata dengan kolom Email/Password di atasnya
        option_row_box = QWidget()
        option_row_box.setFixedWidth(sizes.LOGIN_FIELD_WIDTH)
        option_row = QHBoxLayout(option_row_box)
        option_row.setContentsMargins(0, 0, 0, 0)

        self.remember_checkbox = QCheckBox("Ingatkan saya")
        self.remember_checkbox.setStyleSheet(f"""
QCheckBox {{ spacing: 8px; font-size: 13px; color: {config.COLOR_TEXT}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {config.COLOR_BORDER};
    border-radius: 4px; background: white;
}}
QCheckBox::indicator:checked {{
    background: {config.COLOR_PRIMARY}; border: 1px solid {config.COLOR_PRIMARY};
    image: url({styles.CHECK_ICON});
}}
""")
        self.forgot_button = helpers.make_link_button("Lupa password?", size=13)
        option_row.addWidget(self.remember_checkbox)
        option_row.addStretch()
        option_row.addWidget(self.forgot_button)
        self.form_layout.addWidget(option_row_box, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        self.login_button = helpers.make_primary_button("Masuk")
        self.login_button.setStyleSheet(f"""
QPushButton {{
    background-color: {config.COLOR_PRIMARY}; color: white; border: none;
    border-radius: 10px; padding: 0 16px; font-size: {sizes.LOGIN_BUTTON_FONT}px; font-weight: bold;
}}
QPushButton:hover {{ background-color: {config.COLOR_PRIMARY_HOVER}; }}
""")
        self.login_button.setFixedSize(sizes.LOGIN_FIELD_WIDTH, sizes.LOGIN_FIELD_HEIGHT)
        self.form_layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.admin_button = helpers.make_link_button("Login Sebagai Admin", size=13, bold=False)
        self.right_layout.addWidget(self.admin_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Signal & Slot: tombol (clicked) -> listener
        self.login_button.clicked.connect(self.handle_login)
        self.forgot_button.clicked.connect(lambda: self.forgot_password_clicked.emit())
        self.admin_button.clicked.connect(lambda: self.admin_login_clicked.emit())

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if email == "" or password == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return

        user = data_store.find_user(email, password)
        if user is None:
            helpers.show_error(self.message_label, "Email atau password salah.")
            return

        if self.remember_checkbox.isChecked():
            data_store.remembered_email = email
        else:
            data_store.remembered_email = ""
        self.login_success.emit(user)

    # Widget Lifecycle: refresh isi form setiap halaman tampil
    def on_show(self):
        self.email_input.setText(data_store.remembered_email)
        self.remember_checkbox.setChecked(data_store.remembered_email != "")
        self.password_input.clear()
        self.message_label.setText("")
