# views/partner_profile_page.py — profil calon rekan tim ("Kunjungi Profil")
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from views.content_page import ContentPage
import config
import data_store
import helpers
import icons
import styles
import sizes


class PartnerProfilePage(ContentPage):
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.user = None   # user yang sedang dilihat (diisi lewat show_user)

        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ----- Header biru: tombol kembali, foto, kartu info -----
        header = QFrame()
        header.setObjectName("ProfileHeader")
        header.setStyleSheet(styles.PROFILE_HEADER_STYLE)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 20, 32, 24)
        header_row.setSpacing(18)

        self.back_button = QPushButton()
        self.back_button.setIcon(icons.make_icon("arrow-left", config.COLOR_NAVY, 26))
        self.back_button.setIconSize(QSize(26, 26))
        self.back_button.setStyleSheet(styles.BACK_BUTTON_STYLE)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop)

        self.avatar_holder = QVBoxLayout()   # foto dibuat ulang tiap kali ganti user
        header_row.addLayout(self.avatar_holder)

        info = QFrame()
        info.setObjectName("ProfileInfo")
        info.setStyleSheet(styles.PROFILE_INFO_STYLE)
        info_grid = QGridLayout(info)
        info_grid.setContentsMargins(24, 18, 24, 18)
        info_grid.setHorizontalSpacing(16)
        info_grid.setVerticalSpacing(8)
        self.name_label = QLabel()
        self.name_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.username_label = QLabel()
        self.username_label.setStyleSheet(f"font-size: 13px; color: {config.COLOR_NAVY};")
        self.email_pill = QLabel()
        self.location_pill = QLabel()
        self.instagram_pill = QLabel()
        for pill in (self.email_pill, self.location_pill, self.instagram_pill):
            pill.setStyleSheet(styles.INFO_PILL_STYLE)
        info_grid.addWidget(self.name_label, 0, 0)
        info_grid.addWidget(self.username_label, 1, 0)
        info_grid.addWidget(self.email_pill, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        info_grid.addWidget(self.instagram_pill, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        info_grid.addWidget(self.location_pill, 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        header_row.addWidget(info, 1)
        layout.addWidget(header)

        # ----- Isi: Tentang Saya, Keahlian, Pengalaman & Prestasi -----
        body = QVBoxLayout()
        body.setContentsMargins(sizes.CONTENT_MARGIN, 24, sizes.CONTENT_MARGIN, 28)
        body.setSpacing(22)
        self.bio_label = QLabel()
        self.bio_label.setWordWrap(True)
        body.addLayout(self.make_section("Tentang Saya", self.bio_label))

        self.skills_grid = QGridLayout()
        self.skills_grid.setSpacing(10)
        self.skills_grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        skills_box = QWidget()
        skills_box.setLayout(self.skills_grid)
        body.addLayout(self.make_section("Keahlian", skills_box))

        self.experience_layout = QVBoxLayout()
        self.experience_layout.setSpacing(6)
        experience_box = QWidget()
        experience_box.setLayout(self.experience_layout)
        body.addLayout(self.make_section("Pengalaman & Prestasi", experience_box))
        body.addStretch()
        layout.addLayout(body, 1)

        # Signal & Slot: tombol kembali -> kabari DashboardPage
        self.back_button.clicked.connect(lambda: self.back_clicked.emit())

    def make_section(self, title, content_widget):
        """Judul (pil bergaris) di atas kartu biru berisi content_widget."""
        section = QVBoxLayout()
        section.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet(styles.SECTION_TITLE_STYLE)
        section.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)
        card = QFrame()
        card.setObjectName("SectionCard")
        card.setStyleSheet(styles.SECTION_CARD_STYLE)
        card.setMinimumHeight(90)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.addWidget(content_widget)
        card_layout.addStretch()
        section.addWidget(card)
        return section

    # ---------- Dipanggil DashboardPage ----------
    def show_user(self, email):
        self.user = data_store.get_user(email)

    # Widget Lifecycle: isi halaman diperbarui sesuai user yang dipilih
    def refresh(self):
        user = self.user
        if user is None:
            return
        helpers.clear_layout(self.avatar_holder)
        self.avatar_holder.addWidget(helpers.make_avatar(user, 130), alignment=Qt.AlignmentFlag.AlignTop)

        self.name_label.setText(user["nama"])
        self.username_label.setText("@" + user["username"])
        self.email_pill.setText(user["email"])
        self.location_pill.setText(user["domisili"])
        instagram = user.get("instagram", "")
        self.instagram_pill.setText(f"ig: @{instagram}")
        self.instagram_pill.setVisible(instagram != "")

        self.bio_label.setText(user["bio"] if user["bio"] else "Belum ada deskripsi.")

        helpers.clear_layout(self.skills_grid)
        for index, skill in enumerate(user["keahlian"]):
            chip = QLabel(skill)
            chip.setStyleSheet(styles.CHIP_STYLE)
            self.skills_grid.addWidget(chip, index // 4, index % 4)

        helpers.clear_layout(self.experience_layout)
        experiences = user.get("pengalaman", [])
        if not experiences:
            experiences = ["Belum ada pengalaman yang ditambahkan."]
        for text in experiences:
            self.experience_layout.addWidget(QLabel(text))
