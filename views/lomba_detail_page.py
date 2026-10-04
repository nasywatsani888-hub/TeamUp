# views/lomba_detail_page.py — detail satu lomba (dibuka dari Beranda / Lomba / Riwayat)
import datetime
import os
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from views.content_page import ContentPage
import config
import data_store
import helpers
import icons
import styles
import sizes


class SuggestedPartnerCard(QFrame):
    """Satu kartu kandidat ringkas di panel Rekomendasi Rekan (foto, nama,
    username, 2 tag keahlian, tombol Lihat Profil)."""
    profile_clicked = Signal(str)   # email

    def __init__(self, user):
        super().__init__()
        self.email = user["email"]   # disimpan di objek (bukan ditangkap lambda)
        self.setObjectName("SuggestedPartnerCard")
        self.setStyleSheet(styles.SUGGESTED_PARTNER_CARD_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(helpers.make_avatar(user, 44))
        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(user["nama"])
        name.setWordWrap(True)
        name.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {config.COLOR_NAVY};")
        username = QLabel("@" + user["username"])
        username.setStyleSheet(f"font-size: 12px; color: {config.COLOR_SUBTEXT};")
        text.addWidget(name)
        text.addWidget(username)
        header.addLayout(text, 1)
        layout.addLayout(header)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        for skill in user["keahlian"][:2]:
            chip = QLabel(skill)
            chip.setStyleSheet(styles.CARD_CHIP_STYLE)
            chips.addWidget(chip)
        chips.addStretch()
        layout.addLayout(chips)

        visit_button = QPushButton("Lihat Profil")
        visit_button.setStyleSheet(styles.VISIT_BUTTON_STYLE)
        visit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(visit_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        visit_button.clicked.connect(self.send_profile)

    @Slot()
    def send_profile(self):
        self.profile_clicked.emit(self.email)


class SuggestedPartnerPanel(QWidget):
    """Panel kanan khusus Detail Lomba: 'Rekomendasi Rekan' (Bagian 6.3 dokumentasi
    alur) — menggantikan kartu profil + tenggat pendaftaran (RightPanel) di halaman
    ini. Isinya dicocokkan otomatis dari kategori lomba <-> keahlian user lain,
    dan disegarkan lewat show_kandidat() setiap Detail Lomba dibuka/berubah."""
    WIDTH = sizes.RIGHT_PANEL_WIDTH
    profile_clicked = Signal(str)   # email kandidat yang dipilih

    def __init__(self):
        super().__init__()
        self.setFixedWidth(self.WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 28, 24, 28)

        self.box = QFrame()
        self.box.setObjectName("SuggestedPartnerBox")
        self.box.setStyleSheet(styles.SUGGESTED_PARTNER_BOX_STYLE)
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(18, 18, 18, 18)
        box_layout.setSpacing(12)

        title = QLabel("Rekomendasi Rekan")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {config.COLOR_NAVY};")
        box_layout.addWidget(title)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(12)
        box_layout.addLayout(self.cards_layout)

        outer.addWidget(self.box)
        outer.addStretch()

    def show_kandidat(self, kandidat):
        """Dipanggil dari LombaDetailPage.refresh() setiap lomba yang dilihat berubah."""
        helpers.clear_layout(self.cards_layout)
        if len(kandidat) == 0:
            empty_label = QLabel("Belum ada rekan yang cocok dengan kategori lomba ini.")
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet(f"font-size: 13px; color: {config.COLOR_SUBTEXT};")
            self.cards_layout.addWidget(empty_label)
            return
        for user in kandidat:
            card = SuggestedPartnerCard(user)
            card.profile_clicked.connect(self.profile_clicked)
            self.cards_layout.addWidget(card)

    # Panel ini tidak perlu Widget Lifecycle refresh() tersendiri -- isinya
    # sepenuhnya tergantung lomba yang sedang dilihat, jadi diperbarui langsung
    # lewat show_kandidat() dari LombaDetailPage.refresh(), bukan lewat on_show().


class LombaDetailPage(ContentPage):
    back_clicked = Signal()
    partner_disarankan_clicked = Signal(str)   # email kandidat yang dipilih

    def __init__(self):
        super().__init__(right_panel=SuggestedPartnerPanel())
        self.lomba = None   # lomba yang sedang dilihat (diisi lewat show_lomba)
        self.right_panel.profile_clicked.connect(self.partner_disarankan_clicked)

        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ----- Header kuning: kembali, judul, penyelenggara, badge -----
        header = QFrame()
        header.setObjectName("DetailHeader")
        header.setStyleSheet(styles.DETAIL_HEADER_STYLE)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 20, 32, 20)
        header_row.setSpacing(14)

        self.back_button = QPushButton()
        self.back_button.setIcon(icons.make_icon("arrow-left", config.COLOR_NAVY, 26))
        self.back_button.setIconSize(QSize(26, 26))
        self.back_button.setStyleSheet(styles.BACK_BUTTON_STYLE)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop)

        # Poster sementara (blok warna + judul, seperti di kartu lomba)
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(sizes.DETAIL_POSTER_WIDTH, sizes.DETAIL_POSTER_HEIGHT)
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setWordWrap(True)
        header_row.addWidget(self.poster_label, alignment=Qt.AlignmentFlag.AlignTop)

        title_column = QVBoxLayout()
        title_column.setSpacing(6)
        title_column.addSpacing(8)
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {config.COLOR_NAVY};")
        self.organizer_label = QLabel()
        self.organizer_label.setStyleSheet("font-size: 14px;")
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.organizer_label)

        badges = QHBoxLayout()
        badges.setSpacing(8)
        verified = QLabel("Terverifikasi ✓")
        verified.setStyleSheet(styles.VERIFIED_BADGE_STYLE)
        self.days_badge = QLabel()
        self.days_badge.setStyleSheet(styles.DAYS_BADGE_STYLE)
        badges.addWidget(verified)
        badges.addWidget(self.days_badge)
        badges.addStretch()
        title_column.addLayout(badges)
        title_column.addStretch()
        header_row.addLayout(title_column, 1)
        layout.addWidget(header)

        # ----- Isi -----
        body = QVBoxLayout()
        body.setContentsMargins(sizes.CONTENT_MARGIN, 24, sizes.CONTENT_MARGIN, 28)
        body.setSpacing(20)

        # Tiga kotak info: pelaksanaan | tenggat | anggota tim
        info_row = QHBoxLayout()
        info_row.setSpacing(20)
        self.date_label = QLabel()
        self.deadline_label = QLabel()
        self.team_label = QLabel()
        for title, label in (("Tanggal Pelaksanaan", self.date_label),
                             ("Tanggal Pendaftaran", self.deadline_label),
                             ("Anggota Tim", self.team_label)):
            info_row.addLayout(self.make_info_box(title, label), 1)
        body.addLayout(info_row)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        body.addLayout(self.make_section("Deskripsi", self.description_label))

        self.rules_layout = QVBoxLayout()
        self.rules_layout.setSpacing(4)
        rules_box = QWidget()
        rules_box.setLayout(self.rules_layout)
        body.addLayout(self.make_section("Syarat & Ketentuan", rules_box))

        # Panel "Profil yang Disarankan" (Bagian 6.3): muncul otomatis begitu Detail
        # Lomba dibuka, tanpa user perlu buka Temukan Partner secara terpisah.
        # (Tampil di panel kanan "Rekomendasi Rekan" -- lihat SuggestedPartnerPanel.)

        self.link_label = QLabel()
        self.link_label.setStyleSheet(styles.LOMBA_LINK_STYLE)
        self.link_label.setOpenExternalLinks(True)   # klik -> buka di browser
        body.addLayout(self.make_section("Link Pendaftaran", self.link_label))
        body.addStretch()
        layout.addLayout(body, 1)

        # Signal & Slot: tombol kembali -> kabari DashboardPage
        self.back_button.clicked.connect(self.back_clicked)

    def make_info_box(self, title, value_label):
        """Judul (pil oranye) di atas kotak kuning berisi satu nilai."""
        column = QVBoxLayout()
        column.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet(styles.INFO_TITLE_STYLE)
        column.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        box = QFrame()
        box.setObjectName("InfoBox")
        box.setStyleSheet(styles.INFO_BOX_STYLE)
        box.setMinimumHeight(70)
        box_layout = QVBoxLayout(box)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setWordWrap(True)
        box_layout.addWidget(value_label)
        column.addWidget(box)
        return column

    def make_section(self, title, content_widget):
        """Judul (pil oranye) di atas kotak krem berisi content_widget."""
        section = QVBoxLayout()
        section.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet(styles.INFO_TITLE_STYLE)
        section.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)
        box = QFrame()
        box.setObjectName("DetailBox")
        box.setStyleSheet(styles.DETAIL_BOX_STYLE)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(20, 14, 20, 14)
        box_layout.addWidget(content_widget)
        section.addWidget(box)
        return section

    # ---------- Dipanggil DashboardPage ----------
    def show_lomba(self, lomba_id):
        self.lomba = data_store.get_lomba(lomba_id)

    # Widget Lifecycle: isi halaman diperbarui sesuai lomba yang dipilih
    def refresh(self):
        lomba = self.lomba
        if lomba is None:
            return
        self.title_label.setText(lomba["judul"] + " - " + lomba["kategori"])
        poster = helpers.poster_file(lomba)
        if poster:   # gambar poster asli
            self.poster_label.setStyleSheet("")
            self.poster_label.setText("")
            self.poster_label.setPixmap(helpers._pixmap_poster(
                poster, sizes.DETAIL_POSTER_WIDTH, sizes.DETAIL_POSTER_HEIGHT, 16, True, os.path.getmtime(poster)))
        else:        # cadangan: blok warna + judul
            self.poster_label.setPixmap(QPixmap())
            self.poster_label.setText(lomba["judul"].upper())
            self.poster_label.setStyleSheet(
                f"background-color: {lomba['warna']}; color: white; border-radius: 16px; "
                "padding: 12px; font-size: 18px; font-weight: bold;")
        self.organizer_label.setText("Diselenggarakan oleh " + lomba["penyelenggara"])
        self.days_badge.setText(helpers.format_sisa(lomba["sisa_hari"]))

        deadline = datetime.date.today() + datetime.timedelta(days=lomba["sisa_hari"])
        self.date_label.setText(lomba["tanggal_pelaksanaan"])
        self.deadline_label.setText(helpers.format_tanggal(deadline))
        self.team_label.setText(lomba["anggota_tim"])
        self.description_label.setText(lomba["deskripsi"])

        helpers.clear_layout(self.rules_layout)
        for number, rule in enumerate(lomba["syarat"], start=1):
            item = QLabel(f"{number}. {rule}")
            item.setWordWrap(True)
            self.rules_layout.addWidget(item)

        self.link_label.setText(
            f'<a href="{lomba["link"]}" style="color:{config.COLOR_LINK}">{lomba["link"]}</a>')
        self.right_panel.show_kandidat(data_store.cari_partner_sesuai_keahlian(lomba["kategori"]))
        self.scroll.verticalScrollBar().setValue(0)   # selalu mulai dari atas
