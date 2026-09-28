# views/splash_page.py — layar logo TeamUp sesaat setelah keluar (sebelum Halaman Login)
from PySide6.QtCore import Qt
from views.base_page import BasePage
import helpers


class SplashPage(BasePage):
    def __init__(self):
        super().__init__()
        self.main_layout.addStretch()
        self.main_layout.addWidget(helpers.make_logo(width=380, name_size=80, tagline_size=16),
                                   alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch()
