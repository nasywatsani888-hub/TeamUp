# views/dashboard_page.py — kerangka dashboard: sidebar di kiri, isi halaman di kanan
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QMessageBox, QStackedWidget
from views.base_page import BasePage
from views.sidebar import Sidebar
from views.edit_profile_page import EditProfilePage
from views.history_page import HistoryPage
from views.help_page import HelpPage
from views.home_page import HomePage
from views.logout_dialog import LogoutDialog
from views.lomba_page import LombaPage
from views.notification_page import NotificationPage
from views.lomba_detail_page import LombaDetailPage
from views.partner_page import PartnerPage
from views.partner_profile_page import PartnerProfilePage
from views.upload_page import UploadPage
from views.post_form_page import PostFormPage
from views.post_detail_page import PostDetailPage
from views.post_success_page import PostSuccessPage
from views.post_dialogs import ConfirmDialog, EditBlockedDialog
import data_store
import memory_tools
import styles


class DashboardPage(BasePage):
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.dialogs = {}   # dialog yang sudah dibuat, dipakai ulang (object pooling)

        # Lapisan gelap di belakang dialog Keluar (disembunyikan kecuali saat dialog tampil)
        self.overlay = QFrame(self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setStyleSheet(styles.OVERLAY_STYLE)
        self.overlay.hide()

        row = QHBoxLayout()
        row.setSpacing(0)
        self.main_layout.addLayout(row)

        self.sidebar = Sidebar()
        self.pages = QStackedWidget()
        row.addWidget(self.sidebar)
        row.addWidget(self.pages, 1)

        self.current_key = "beranda"    # halaman isi yang sedang tampil (selain detail lomba)
        self.detail_origin = "beranda"  # halaman asal saat detail lomba dibuka (tujuan tombol Kembali)
        self.profile_origin = "rekan"   # halaman asal saat profil rekan dibuka (Rekan Tim / Notifikasi)

        # Isi halaman: kunci -> halaman (dibuat SATU kali)
        self.content = {}
        self.home_page = HomePage()
        self.add_content("beranda", self.home_page)
        self.partner_page = PartnerPage()
        self.partner_profile_page = PartnerProfilePage()
        self.add_content("rekan", self.partner_page)
        self.add_content("profil_rekan", self.partner_profile_page)
        self.lomba_page = LombaPage()
        self.lomba_detail_page = LombaDetailPage()
        self.add_content("lomba", self.lomba_page)
        self.add_content("detail_lomba", self.lomba_detail_page)
        self.notification_page = NotificationPage()
        self.add_content("notifikasi", self.notification_page)
        self.history_page = HistoryPage()
        self.add_content("riwayat", self.history_page)
        self.edit_profile_page = EditProfilePage()
        self.add_content("edit_profil", self.edit_profile_page)
        self.help_page = HelpPage()
        self.add_content("bantuan", self.help_page)
        self.upload_page = UploadPage()
        self.add_content("unggah", self.upload_page)
        self.post_form_page = PostFormPage()
        self.add_content("unggah_form", self.post_form_page)
        self.post_detail_page = PostDetailPage()
        self.add_content("post_detail", self.post_detail_page)
        self.post_success_page = PostSuccessPage()
        self.add_content("post_sukses", self.post_success_page)

        # Signal & Slot: sidebar dan Beranda -> listener di sini
        self.sidebar.menu_selected.connect(self.show_content)
        self.sidebar.help_clicked.connect(lambda: self.show_content("bantuan"))
        self.sidebar.edit_profile_clicked.connect(lambda: self.show_content("edit_profil"))
        self.sidebar.logout_clicked.connect(self.handle_logout_clicked)
        self.help_page.cancel_clicked.connect(lambda: self.show_content("beranda"))
        self.home_page.find_partner_clicked.connect(lambda: self.show_content("rekan"))
        self.home_page.lomba_detail_clicked.connect(self.handle_lomba_detail)

        # Lomba -> Detail Lomba -> Kembali (ke halaman asal: Beranda / Lomba / Riwayat)
        self.lomba_page.lomba_detail_clicked.connect(self.handle_lomba_detail)
        self.history_page.lomba_detail_clicked.connect(self.handle_lomba_detail)
        self.lomba_detail_page.back_clicked.connect(lambda: self.show_content(self.detail_origin))
        # Panel "Profil yang Disarankan" di Detail Lomba -> Profil Rekan -> Kembali ke Detail Lomba
        self.lomba_detail_page.partner_disarankan_clicked.connect(self.handle_partner_disarankan)

        # Rekan Tim -> Profil Rekan -> Kembali
        self.partner_page.profile_requested.connect(self.handle_partner_profile)
        self.partner_profile_page.back_clicked.connect(lambda: self.show_content(self.profile_origin))

        # Notifikasi -> profil partner / Postingan Saya
        self.notification_page.partner_profile_requested.connect(self.handle_partner_profile)
        self.notification_page.post_requested.connect(self.handle_post_notification)
        # Unggah Postingan: daftar -> formulir / detail; formulir -> berhasil; detail -> dialog
        self.upload_page.new_post_requested.connect(self.handle_new_post)
        self.upload_page.post_clicked.connect(self.handle_post_detail)
        self.post_form_page.back_clicked.connect(self.handle_form_back)
        self.post_form_page.submitted.connect(self.handle_post_submitted)
        self.post_success_page.back_clicked.connect(lambda: self.show_content("unggah"))
        self.post_success_page.view_status_clicked.connect(self.handle_post_detail)
        self.post_detail_page.back_clicked.connect(lambda: self.show_content("unggah"))
        self.post_detail_page.edit_blocked_requested.connect(self.handle_edit_blocked)
        self.post_detail_page.cancel_requested.connect(self.handle_post_cancel)
        self.post_detail_page.delete_requested.connect(self.handle_post_delete)
        self.post_detail_page.revise_requested.connect(self.handle_post_revise)
        self.post_detail_page.new_post_requested.connect(self.handle_new_post)
        self.post_detail_page.contact_admin_requested.connect(lambda: self.show_content("bantuan"))
        # Edit Profil -> Simpan -> Beranda
        self.edit_profile_page.profile_saved.connect(self.handle_profile_saved)

    def add_content(self, key, page):
        self.content[key] = page
        self.pages.addWidget(page)

    def show_content(self, key, menu=None):
        """menu = menu sidebar yang ditandai kuning (kalau beda dari key,
        mis. Profil Rekan yang dibuka dari Notifikasi tetap menandai 'Notifikasi')."""
        if key not in ("detail_lomba", "profil_rekan", "unggah_form", "post_detail", "post_sukses"):   # halaman "turunan" tidak dihitung
            self.current_key = key
        memory_tools.catat(key)          # hanya mencetak kalau TEAMUP_DEBUG_MEMORY=1
        self.sidebar.refresh_profile()   # @username di kartu profil sidebar
        self.pages.setCurrentWidget(self.content[key])
        self.sidebar.set_active(menu or key)

    def handle_partner_profile(self, email):
        self.partner_profile_page.show_user(email)
        self.profile_origin = self.current_key   # Kembali -> Rekan Tim atau Notifikasi
        self.show_content("profil_rekan", menu=self.current_key)

    def handle_partner_disarankan(self, email):
        """Dari panel 'Profil yang Disarankan' di Detail Lomba -> Kembali harus ke
        Detail Lomba yang sama (bukan ke Beranda/Lomba/Riwayat asalnya)."""
        self.partner_profile_page.show_user(email)
        self.profile_origin = "detail_lomba"
        self.show_content("profil_rekan", menu=self.current_key)

    def handle_logout_clicked(self):
        self.sidebar.set_active("keluar")
        self.overlay.setGeometry(self.rect())
        self.overlay.show()
        self.overlay.raise_()
        confirmed = self.get_dialog("logout", lambda: LogoutDialog(self)).exec() == QDialog.DialogCode.Accepted
        self.overlay.hide()
        if confirmed:
            self.logout_requested.emit()   # MainWindow yang mengurus keluar & pindah halaman
        else:
            self.show_content("beranda")   # Batal -> Beranda

    def handle_profile_saved(self, user):
        QMessageBox.information(self, "Edit Profil", "Profil berhasil disimpan.")
        self.show_content("beranda")

    def handle_post_notification(self, status):
        # Notifikasi "disetujui" / "revisi" -> Postingan Saya dengan filter status itu
        self.upload_page.open_my_posts(status)
        self.show_content("unggah")

    # ---------- Unggah Postingan ----------
    def get_dialog(self, key, factory):
        """Ambil dialog dari kumpulan; dibuat (lewat factory) hanya kalau belum ada."""
        if key not in self.dialogs:
            self.dialogs[key] = factory()
        return self.dialogs[key]

    def run_dialog(self, dialog):
        """Tampilkan dialog di atas lapisan gelap; True kalau user menekan tombol konfirmasi."""
        self.overlay.setGeometry(self.rect())
        self.overlay.show()
        self.overlay.raise_()
        confirmed = dialog.exec() == QDialog.DialogCode.Accepted
        self.overlay.hide()
        return confirmed

    def handle_new_post(self):
        self.post_form_page.show_new()
        self.show_content("unggah_form", menu="unggah")

    def handle_post_detail(self, post_id):
        self.post_detail_page.show_post(post_id)
        self.show_content("post_detail", menu="unggah")

    def handle_form_back(self):
        if self.post_form_page.mode == "revisi":
            self.handle_post_detail(self.post_form_page.post_id)   # batal perbaikan -> kembali ke detail
        else:
            self.show_content("unggah")

    def handle_post_submitted(self, post_id, mode):
        self.post_success_page.show_post(post_id, mode)
        self.show_content("post_sukses", menu="unggah")

    def handle_post_revise(self, post_id):
        self.post_form_page.show_revision(post_id)
        self.show_content("unggah_form", menu="unggah")

    def handle_edit_blocked(self, post_id):
        self.run_dialog(self.get_dialog("edit_diblokir", lambda: EditBlockedDialog(self)))   # Ditangguhkan tidak boleh diedit (sesuai dokumen alur)

    def handle_post_cancel(self, post_id):
        post = data_store.get_postingan_by_id(post_id)
        dialog = self.get_dialog("konfirmasi_batalkan", lambda: ConfirmDialog(self, tone="batalkan"))
        dialog.set_content(
            "Batalkan Pengajuan", "Apakah kamu yakin ingin membatalkan pengajuan", post["judul"],
            "Setelah pengajuan dibatalkan, anda perlu mengajukan kembali jika ingin terus mengunggah",
            "Ya, batalkan pengajuan")
        if self.run_dialog(dialog):
            salinan = dict(post)                      # detail tetap menampilkan datanya + banner berhasil
            data_store.hapus_postingan(post_id)
            self.post_detail_page.show_post(post_id, cancelled=True, salinan=salinan)

    def handle_post_delete(self, post_id):
        post = data_store.get_postingan_by_id(post_id)
        dialog = self.get_dialog("konfirmasi_hapus", lambda: ConfirmDialog(self, tone="hapus"))
        dialog.set_content(
            "Hapus Pengajuan", "Apakah kamu yakin ingin menghapus pengajuan", post["judul"],
            "Setelah pengajuan dihapus, pengajuan akan dibatalkan dan tidak akan diteruskan ke proses "
            "verifikasi admin", "Ya, hapus pengajuan")
        if self.run_dialog(dialog):
            data_store.hapus_postingan(post_id)
            self.show_content("unggah")

    def handle_lomba_detail(self, lomba_id):
        data_store.add_to_history(lomba_id)   # dicatat ke Riwayat setiap dibuka
        self.lomba_detail_page.show_lomba(lomba_id)
        self.detail_origin = self.current_key   # Kembali -> halaman tempat user berasal
        self.show_content("detail_lomba", menu=self.current_key)

    def on_show(self):
        self.show_content("beranda")
