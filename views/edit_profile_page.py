# views/edit_profile_page.py — halaman Edit Profil (dibuka dari Beranda / panel profil)
import os
import shutil
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)
from views.base_page import BasePage
from views.upload_dialog import UploadDialog
import config
import data_store
import helpers
import icons
import styles
import sizes

AVATAR_SIZE = sizes.EDIT_PROFILE_AVATAR_SIZE


class SkillChip(QFrame):
    """Chip keahlian dengan tombol x untuk menghapus."""
    remove_clicked = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.setObjectName("SkillChip")
        self.setStyleSheet(styles.SKILL_CHIP_STYLE)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 3, 6, 3)
        row.setSpacing(6)
        row.addWidget(QLabel(text))
        remove_button = QPushButton()
        remove_button.setIcon(icons.make_icon("x", config.COLOR_PRIMARY, 14))
        remove_button.setIconSize(QSize(14, 14))
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.clicked.connect(lambda: self.remove_clicked.emit(text))
        row.addWidget(remove_button)


class EditProfilePage(BasePage):
    profile_saved = Signal(dict)

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.skills = []          # data sementara di form (baru disimpan saat klik Simpan)
        self.experiences = []
        self.photo_name = ""

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("EditForm")
        content.setStyleSheet(styles.EDIT_PAGE_STYLE)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 24)
        layout.setSpacing(0)
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        self.build_header(layout)
        self.build_form(layout)

        # Signal & Slot
        self.camera_button.clicked.connect(self.handle_change_photo)
        self.add_skill_button.clicked.connect(self.handle_add_skill)
        self.add_exp_button.clicked.connect(self.handle_add_experience)
        self.reset_button.clicked.connect(self.handle_reset)
        self.save_button.clicked.connect(self.handle_save)

    # ---------- Tampilan ----------
    def build_header(self, layout):
        # Banner biru muda + foto bulat yang menimpa banner (banner & foto di sel grid yang sama)
        header = QWidget()
        header.setFixedHeight(sizes.EDIT_PROFILE_HEADER_HEIGHT)
        grid = QGridLayout(header)
        grid.setContentsMargins(0, 0, 0, 0)
        banner = QFrame()
        banner.setObjectName("EditBanner")
        banner.setStyleSheet(styles.EDIT_BANNER_STYLE)
        banner.setFixedHeight(sizes.EDIT_PROFILE_BANNER_HEIGHT)
        grid.addWidget(banner, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.avatar_box = QWidget()
        self.avatar_box.setFixedSize(AVATAR_SIZE + 10, AVATAR_SIZE)
        self.avatar_holder = QVBoxLayout(self.avatar_box)
        self.avatar_holder.setContentsMargins(0, 0, 0, 0)
        self.camera_button = QPushButton(self.avatar_box)
        self.camera_button.setFixedSize(sizes.EDIT_PROFILE_CAMERA_BUTTON_SIZE, sizes.EDIT_PROFILE_CAMERA_BUTTON_SIZE)
        self.camera_button.setIcon(icons.make_icon("camera", "white", 14))
        self.camera_button.setIconSize(QSize(14, 14))
        self.camera_button.setStyleSheet(styles.CAMERA_BUTTON_STYLE)
        self.camera_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.camera_button.move(AVATAR_SIZE - 20, AVATAR_SIZE - 26)
        avatar_wrap = QHBoxLayout()
        avatar_wrap.setContentsMargins(40, 0, 0, 0)
        avatar_wrap.addWidget(self.avatar_box, alignment=Qt.AlignmentFlag.AlignBottom)
        avatar_wrap.addStretch()
        grid.addLayout(avatar_wrap, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(header)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(40, 6, 40, 14)
        title_box.setSpacing(0)
        title = QLabel("Edit profil")
        title.setStyleSheet(styles.EDIT_TITLE_STYLE)
        subtitle = QLabel("Lengkapi Profilmu, Temukan Partner yang Tepat!")
        subtitle.setStyleSheet(styles.EDIT_SUBTITLE_STYLE)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

    def make_field(self, text, widget):
        box = QVBoxLayout()
        box.setSpacing(4)
        label = QLabel(text)
        label.setProperty("role", "field")
        box.addWidget(label)
        box.addWidget(widget)
        return box

    def build_form(self, layout):
        columns = QHBoxLayout()
        columns.setContentsMargins(40, 0, 40, 0)
        columns.setSpacing(50)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        layout.addLayout(columns)

        # Kolom kiri
        self.name_input = QLineEdit()
        self.prodi_input = QLineEdit()
        self.domisili_input = QLineEdit()
        self.bio_input = QTextEdit()
        self.bio_input.setFixedHeight(sizes.EDIT_PROFILE_BIO_HEIGHT)
        left.addLayout(self.make_field("Nama Lengkap", self.name_input))
        left.addLayout(self.make_field("Program Studi", self.prodi_input))
        left.addLayout(self.make_field("Domisili", self.domisili_input))
        left.addLayout(self.make_field("Bio Singkat", self.bio_input))
        left.addStretch()

        # Kolom kanan
        self.email_input = QLineEdit()
        self.email_input.setReadOnly(True)   # email = identitas akun, tidak diubah di sini
        self.username_input = QLineEdit()
        self.univ_input = QLineEdit()
        right.addLayout(self.make_field("Email", self.email_input))
        right.addLayout(self.make_field("Username", self.username_input))
        right.addLayout(self.make_field("Universitas", self.univ_input))

        self.skills_grid = QGridLayout()
        self.skills_grid.setHorizontalSpacing(8)
        self.skills_grid.setVerticalSpacing(8)
        self.skills_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.add_skill_button = QPushButton("+  Tambah")
        self.add_skill_button.setStyleSheet(styles.ADD_DASHED_STYLE)
        self.add_skill_button.setCursor(Qt.CursorShape.PointingHandCursor)
        skills_box = QWidget()
        skills_box.setLayout(self.skills_grid)
        right.addLayout(self.make_field("Keahlian", skills_box))

        self.exp_layout = QVBoxLayout()
        self.exp_layout.setSpacing(6)
        exp_box = QWidget()
        exp_box.setLayout(self.exp_layout)
        right.addLayout(self.make_field("Pengalaman dan Prestasi", exp_box))
        self.add_exp_button = QPushButton()
        self.add_exp_button.setFixedSize(sizes.EDIT_PROFILE_ADD_BUTTON_SIZE, sizes.EDIT_PROFILE_ADD_BUTTON_SIZE)
        self.add_exp_button.setIcon(icons.make_icon("plus", config.COLOR_NAVY, 14))
        self.add_exp_button.setIconSize(QSize(14, 14))
        self.add_exp_button.setStyleSheet(styles.ROUND_PLUS_STYLE)
        self.add_exp_button.setCursor(Qt.CursorShape.PointingHandCursor)
        right.addWidget(self.add_exp_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        right.addStretch()

        # Pesan + tombol Reset / Simpan (kanan bawah)
        self.message_label = helpers.make_message_label()
        self.message_label.setContentsMargins(40, 8, 40, 0)
        layout.addWidget(self.message_label)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(40, 8, 40, 0)
        buttons.setSpacing(12)
        buttons.addStretch()
        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet(styles.EDIT_RESET_STYLE)
        self.save_button = QPushButton("Simpan")
        self.save_button.setStyleSheet(styles.EDIT_SAVE_STYLE)
        for button in (self.reset_button, self.save_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addStretch()

    # ---------- Isi tampilan dari data ----------
    def refresh_avatar(self):
        helpers.clear_layout(self.avatar_holder)
        user = {"nama": self.name_input.text().strip() or "?", "foto": self.photo_name}
        avatar = helpers.make_avatar(user, AVATAR_SIZE)
        if self.photo_name == "" or not os.path.exists(os.path.join(config.ASSETS_DIR, "foto", self.photo_name)):
            avatar.setStyleSheet(styles.AVATAR_CIRCLE_STYLE + f" color: {config.COLOR_NAVY}; font-size: 28px; font-weight: bold;")
        self.avatar_holder.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.camera_button.raise_()

    def refresh_skills(self):
        # Kosongkan grid (tombol Tambah dipakai ulang, jadi jangan dihapus), lalu isi ulang
        for index in reversed(range(self.skills_grid.count())):
            widget = self.skills_grid.takeAt(index).widget()
            if widget is not self.add_skill_button:
                widget.deleteLater()
        items = []
        for skill in self.skills:
            chip = SkillChip(skill)
            chip.remove_clicked.connect(self.handle_remove_skill)
            items.append(chip)
        items.append(self.add_skill_button)
        for index, widget in enumerate(items):
            self.skills_grid.addWidget(widget, index // 3, index % 3)

    def refresh_experiences(self):
        helpers.clear_layout(self.exp_layout)
        for index, text in enumerate(self.experiences):
            row = QFrame()
            row.setObjectName("ExpRow")
            row.setStyleSheet(styles.EXP_ROW_STYLE)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 8, 6)
            row_layout.addWidget(QLabel(text), 1)
            edit_button = QPushButton()
            edit_button.setIcon(icons.make_icon("edit", config.COLOR_PRIMARY, 16))
            delete_button = QPushButton()
            delete_button.setIcon(icons.make_icon("trash", config.COLOR_ERROR, 16))
            for button in (edit_button, delete_button):
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                row_layout.addWidget(button)
            edit_button.clicked.connect(lambda checked=False, i=index: self.handle_edit_experience(i))
            delete_button.clicked.connect(lambda checked=False, i=index: self.handle_remove_experience(i))
            self.exp_layout.addWidget(row)

    def load_user(self):
        user = data_store.current_user
        self.name_input.setText(user["nama"])
        self.prodi_input.setText(user["prodi"])
        self.domisili_input.setText(user["domisili"])
        self.bio_input.setPlainText(user["bio"])
        self.email_input.setText(user["email"])
        self.username_input.setText(user["username"])
        self.univ_input.setText(user["universitas"])
        self.skills = list(user["keahlian"])
        self.experiences = list(user.get("pengalaman", []))
        self.photo_name = user.get("foto", "")
        self.refresh_avatar()
        self.refresh_skills()
        self.refresh_experiences()
        self.message_label.setText("")

    # ---------- Listener (slot) ----------
    def handle_change_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pilih Foto Profil", "", "Gambar (*.png *.jpg *.jpeg)")
        if path == "":
            return
        if os.path.getsize(path) > config.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024:
            helpers.show_error(self.message_label, f"Ukuran foto maksimal {config.MAX_ATTACHMENT_SIZE_MB} MB.")
            return
        foto_dir = os.path.join(config.ASSETS_DIR, "foto")
        os.makedirs(foto_dir, exist_ok=True)
        # nama file = bagian depan email + ekstensi asli, mis. demo.png
        new_name = data_store.current_user["email"].split("@")[0] + os.path.splitext(path)[1].lower()
        shutil.copy(path, os.path.join(foto_dir, new_name))
        self.photo_name = new_name
        self.refresh_avatar()

    def handle_add_skill(self):
        text, ok = QInputDialog.getText(self, "Tambah Keahlian", "Nama keahlian (mis. UI/UX Design):")
        text = text.strip()
        if ok and text != "" and text not in self.skills:
            self.skills.append(text)
            self.refresh_skills()

    def handle_remove_skill(self, text):
        if text in self.skills:
            self.skills.remove(text)
            self.refresh_skills()

    def handle_add_experience(self):
        dialog = UploadDialog(self, title="Upload Pengalaman & Prestasi")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            filename = os.path.basename(dialog.selected_path)
            if filename not in self.experiences:
                self.experiences.append(filename)
                self.refresh_experiences()

    def handle_edit_experience(self, index):
        text, ok = QInputDialog.getText(self, "Ubah Keterangan", "Nama / keterangan:", text=self.experiences[index])
        text = text.strip()
        if ok and text != "":
            self.experiences[index] = text
            self.refresh_experiences()

    def handle_remove_experience(self, index):
        del self.experiences[index]
        self.refresh_experiences()

    def handle_reset(self):
        # Kosongkan semua isian form (email tetap). Baru tersimpan kalau klik Simpan.
        for field in (self.name_input, self.prodi_input, self.domisili_input,
                      self.username_input, self.univ_input):
            field.clear()
        self.bio_input.clear()
        self.skills = []
        self.experiences = []
        self.refresh_avatar()
        self.refresh_skills()
        self.refresh_experiences()
        helpers.show_success(self.message_label, "Form dikosongkan. Isi ulang lalu klik Simpan.")

    def handle_save(self):
        name = self.name_input.text().strip()
        username = self.username_input.text().strip().lstrip("@")
        prodi = self.prodi_input.text().strip()
        univ = self.univ_input.text().strip()
        domisili = self.domisili_input.text().strip()

        if name == "" or username == "" or prodi == "" or univ == "" or domisili == "":
            helpers.show_error(self.message_label, "Mohon lengkapi semua data terlebih dahulu.")
            return
        if data_store.username_exists(username, data_store.current_user):
            helpers.show_error(self.message_label, "Username sudah dipakai, coba yang lain.")
            return

        user = data_store.current_user
        user["nama"] = name
        user["username"] = username
        user["prodi"] = prodi
        user["universitas"] = univ
        user["domisili"] = domisili
        user["bio"] = self.bio_input.toPlainText().strip()
        user["keahlian"] = list(self.skills)
        user["pengalaman"] = list(self.experiences)
        user["foto"] = self.photo_name
        self.profile_saved.emit(user)

    # ---------- Widget Lifecycle ----------
    def on_show(self):
        # Selalu muat ulang dari data_store: perubahan yang tidak disimpan otomatis dibuang
        if data_store.current_user is not None:
            self.load_user()
