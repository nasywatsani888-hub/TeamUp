# views/placeholder_page.py — halaman sementara untuk menu yang belum dibuat
from views.base_page import BasePage
import helpers


class PlaceholderPage(BasePage):
    def __init__(self, title):
        super().__init__()
        self.main_layout.addWidget(helpers.make_title(title))
        self.main_layout.addWidget(helpers.make_subtitle("Halaman ini akan dibuat di tahap berikutnya."))
        self.main_layout.addStretch()
