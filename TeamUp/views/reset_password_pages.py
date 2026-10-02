# views/reset_password_pages.py — alur Lupa Password: Email -> OTP -> Password Baru
from PySide6.QtCore import Qt, Signal, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QHBoxLayout, QLineEdit
from views.auth_page import AuthPage
import helpers
import data_store
import styles
import sizes


class ForgotPasswordPage(AuthPage):
    email_submitted = Signal(str)
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.add_title("Lupa Password?", "Masukkan email kamu, kami akan mengirimkan kode OTP untuk mengonfirmasi identitasmu.")
        self.form_layout.addWidget(helpers.make_image("ilustrasi_email.png", 150, "📱"))

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("nama@email.com")
        self.add_field("Email", self.email_input)
        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        self.send_button = helpers.make_primary_button("Kirim")
        self.form_layout.addWidget(self.send_button)
        self.back_button = helpers.make_link_button("Kembali ke Masuk")
        self.form_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.send_button.clicked.connect(self.handle_send)
        self.back_button.clicked.connect(lambda: self.back_clicked.emit())

    def handle_send(self):
        email = self.email_input.text().strip()
        if email == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        if not data_store.email_exists(email):
            helpers.show_error(self.message_label, "Email tidak terdaftar.")
            return
        self.email_submitted.emit(email)

    def on_show(self):
        self.email_input.clear()
        self.message_label.setText("")


class OtpBox(QLineEdit):
    """Satu kotak OTP (1 digit)."""
    backspace_on_empty = Signal()

    def __init__(self):
        super().__init__()
        self.setMaxLength(1)
        self.setFixedSize(sizes.OTP_BOX_WIDTH, sizes.OTP_BOX_HEIGHT)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]")))
        self.setStyleSheet(styles.OTP_BOX_STYLE)

    # Event Handling: menangkap tombol keyboard langsung
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace and self.text() == "":
            self.backspace_on_empty.emit()
        super().keyPressEvent(event)


class OtpPage(AuthPage):
    otp_verified = Signal()

    def __init__(self):
        super().__init__()
        self.add_title("Masukkan Kode OTP", "Masukkan 4 digit kode yang kami kirim ke email kamu.")
        self.form_layout.addWidget(helpers.make_image("ilustrasi_email.png", 150, "📱"))

        row = QHBoxLayout()
        row.setSpacing(16)
        row.addStretch()
        self.boxes = []
        for i in range(4):
            box = OtpBox()
            box.textChanged.connect(lambda text, i=i: self.handle_digit_typed(i, text))
            box.backspace_on_empty.connect(lambda i=i: self.handle_backspace(i))
            self.boxes.append(box)
            row.addWidget(box)
        row.addStretch()
        self.form_layout.addSpacing(10)
        self.form_layout.addLayout(row)

        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)
        self.send_button = helpers.make_primary_button("Kirim")
        self.form_layout.addWidget(self.send_button)
        self.send_button.clicked.connect(self.handle_send)

    def handle_digit_typed(self, index, text):
        if text != "" and index < 3:
            self.boxes[index + 1].setFocus()   # loncat ke kotak berikutnya

    def handle_backspace(self, index):
        if index > 0:
            self.boxes[index - 1].clear()
            self.boxes[index - 1].setFocus()

    def handle_send(self):
        code = "".join(box.text() for box in self.boxes)
        if len(code) < 4:
            helpers.show_error(self.message_label, "Mohon lengkapi 4 digit kode OTP.")
            return
        if code != data_store.otp_code:
            helpers.show_error(self.message_label, "Kode OTP salah.")
            return
        self.otp_verified.emit()

    def on_show(self):
        for box in self.boxes:
            box.clear()
        self.message_label.setText("")
        self.boxes[0].setFocus()


class NewPasswordPage(AuthPage):
    password_updated = Signal()

    def __init__(self):
        super().__init__()
        self.add_title("Atur Password Baru!", "Buat password baru untuk akunmu. Pastikan unik dan mudah diingat.")
        self.form_layout.addWidget(helpers.make_image("ilustrasi_gembok.png", 130, "🔒"))

        self.password_input = helpers.PasswordField("Minimal 8 karakter, huruf & angka")
        self.add_field("Password Baru", self.password_input)
        self.confirm_input = helpers.PasswordField("Ulangi password")
        self.add_field("Konfirmasi Password", self.confirm_input)
        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        self.update_button = helpers.make_primary_button("Perbarui")
        self.form_layout.addWidget(self.update_button)
        self.update_button.clicked.connect(self.handle_update)

    def handle_update(self):
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        if password == "" or confirm == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        if not helpers.is_valid_password(password):
            helpers.show_error(self.message_label, "Password minimal 8 karakter dan mengandung huruf serta angka.")
            return
        if password != confirm:
            helpers.show_error(self.message_label, "Konfirmasi password tidak sama.")
            return
        data_store.update_password(data_store.reset_email, password)
        self.password_updated.emit()

    def on_show(self):
        self.password_input.clear()
        self.confirm_input.clear()
        self.message_label.setText("")
