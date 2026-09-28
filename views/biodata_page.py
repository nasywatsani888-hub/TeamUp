# views/biodata_page.py — halaman Lengkapi Biodata
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QLineEdit, QTextEdit, QVBoxLayout
from views.auth_page import AuthPage
import helpers
import data_store
import styles
import sizes


class BiodataPage(AuthPage):
    biodata_saved = Signal(dict)

    def __init__(self):
        super().__init__()
        self.skills = []
        self.add_title("Ayo lengkapi biodata!")

        self.name_input = QLineEdit()
        self.add_field("Nama lengkap", self.name_input)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("contoh: AGBell")
        self.add_field("Username", self.username_input)

        # Program studi & Universitas bersebelahan
        row = QHBoxLayout()
        self.prodi_input = QLineEdit()
        self.univ_input = QLineEdit()
        for text, widget in (("Program studi", self.prodi_input), ("Universitas", self.univ_input)):
            column = QVBoxLayout()
            column.setSpacing(4)
            column.addWidget(helpers.make_label(text))
            column.addWidget(widget)
            row.addLayout(column)
        self.form_layout.addLayout(row)
        self.form_layout.addSpacing(12)

        self.domisili_input = QLineEdit()
        self.add_field("Domisili", self.domisili_input)

        self.bio_input = QTextEdit()
        self.bio_input.setFixedHeight(sizes.BIODATA_BIO_HEIGHT)
        self.add_field("Bio (opsional)", self.bio_input)

        # Keahlian: chip + tombol tambah
        self.form_layout.addWidget(helpers.make_label("Keahlian (opsional)"))
        skills_row = QHBoxLayout()
        self.chips_layout = QHBoxLayout()
        self.add_skill_button = helpers.make_outline_button("+ Tambah")
        skills_row.addLayout(self.chips_layout)
        skills_row.addWidget(self.add_skill_button)
        skills_row.addStretch()
        self.form_layout.addLayout(skills_row)

        self.message_label = helpers.make_message_label()
        self.form_layout.addWidget(self.message_label)

        self.save_button = helpers.make_primary_button("Masuk")
        # Sesuai desain: tombol Masuk kecil, di kanan bawah
        self.form_layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.add_skill_button.clicked.connect(self.handle_add_skill)
        self.save_button.clicked.connect(self.handle_save)

    def handle_add_skill(self):
        text, ok = QInputDialog.getText(self, "Tambah Keahlian", "Nama keahlian (mis. UI/UX Design):")
        text = text.strip()
        if ok and text != "" and text not in self.skills:
            self.skills.append(text)
            self.refresh_skills()

    def refresh_skills(self):
        # Kosongkan chip lama, lalu buat ulang dari daftar self.skills
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            item.widget().deleteLater()
        for skill in self.skills:
            chip = QLabel(skill)
            chip.setStyleSheet(styles.CHIP_STYLE)
            self.chips_layout.addWidget(chip)

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
        self.biodata_saved.emit(user)

    def on_show(self):
        user = data_store.current_user
        self.name_input.setText(user["nama"] if user else "")
        self.username_input.clear()
        self.prodi_input.clear()
        self.univ_input.clear()
        self.domisili_input.clear()
        self.bio_input.clear()
        self.skills = []
        self.refresh_skills()
        self.message_label.setText("")
