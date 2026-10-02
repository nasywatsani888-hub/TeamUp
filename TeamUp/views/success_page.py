# views/success_page.py — halaman "berhasil" (centang hijau), dipakai ulang
from PySide6.QtCore import Qt, Signal
from views.auth_page import AuthPage
import helpers


class SuccessPage(AuthPage):
    button_clicked = Signal()

    def __init__(self, title, button_text):
        super().__init__()
        self.add_title(title)
        self.form_layout.addSpacing(16)
        self.form_layout.addWidget(helpers.make_check_circle(), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.form_layout.addSpacing(16)

        self.button = helpers.make_primary_button(button_text)
        self.form_layout.addWidget(self.button)
        self.button.clicked.connect(lambda: self.button_clicked.emit())
