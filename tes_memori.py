# tes_memori.py — uji kebocoran memori TeamUp (Pertemuan 6)
# Cara pakai (dari folder proyek):   python tes_memori.py          (30 siklus)
#                                    python tes_memori.py 100      (100 siklus)
# Idenya: buka-tutup semua halaman & dialog berulang kali. Aplikasi yang sehat
# jumlah widget / objeknya TIDAK bertambah di akhir; kalau bertambah = ada kebocoran.
import os
import sys
import time
import tracemalloc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # tanpa jendela -> bisa jalan di terminal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import data_store
import memory_tools
import styles
from main import MainWindow


def tutup_dialog(app, terima):
    """Dialog modal menahan program (exec). Jadwalkan penutupan otomatis."""
    def tutup():
        dialog = app.activeModalWidget()
        if dialog is not None:
            dialog.accept() if terima else dialog.reject()
    QTimer.singleShot(0, tutup)


def satu_siklus(app, window):
    """Satu putaran memakai fitur-fitur yang membangun / menghapus widget."""
    dash = window.dashboard_page
    for kunci in ("beranda", "rekan", "lomba", "notifikasi", "riwayat", "unggah", "edit_profil", "bantuan"):
        dash.show_content(kunci)
    for lomba in data_store.lomba_list:                      # Detail Lomba + panel Rekomendasi Rekan
        dash.handle_lomba_detail(lomba["id"])
    for user in data_store.users[:3]:                        # Profil Rekan
        dash.handle_partner_profile(user["email"])
    dash.lomba_page.backend.setFilters({"biaya": ["Gratis"]})   # Filter Lomba (QML)
    dash.lomba_page.backend.setFilters({})
    dash.notification_page.only_unread = True
    dash.show_content("notifikasi")
    dash.notification_page.only_unread = False
    dash.show_content("notifikasi")
    for post in list(data_store.postingan_list):             # Detail Postingan (4 status)
        dash.handle_post_detail(post["id"])
    dash.handle_new_post()                                   # Formulir Unggah
    dash.handle_post_revise(3)                               # Formulir Perbaiki
    tutup_dialog(app, terima=False); dash.handle_logout_clicked()        # dialog Keluar -> Batal
    tutup_dialog(app, terima=True); dash.handle_edit_blocked(2)          # dialog tidak bisa edit
    tutup_dialog(app, terima=False); dash.handle_post_cancel(2)          # dialog Batalkan -> Kembali
    tutup_dialog(app, terima=False); dash.handle_post_delete(4)          # dialog Hapus -> Kembali
    dash.show_content("beranda")


def main():
    siklus = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    app = QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    window = MainWindow()
    window.resize(1320, 820)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    window.show_page(window.dashboard_page)
    window.show()

    tracemalloc.start(15)
    for _ in range(3):                  # pemanasan: cache & lazy-init selesai dulu
        satu_siklus(app, window)
    # Urutan penting: foto_awal diambil SEBELUM pengukuran awal, dan foto_akhir SESUDAH pengukuran
    # akhir. Dengan begitu memori milik foto tracemalloc itu sendiri tidak ikut dihitung sebagai
    # "kebocoran" (alat ukur tidak boleh mengganggu yang diukur).
    memory_tools.snapshot()   # pemanasan alat ukur: allWidgets() membuat pembungkus Python saat pertama dipanggil
    foto_awal = tracemalloc.take_snapshot()
    awal = memory_tools.snapshot()

    mulai = time.perf_counter()
    for _ in range(siklus):
        satu_siklus(app, window)
    ms_per_siklus = (time.perf_counter() - mulai) * 1000 / siklus
    akhir = memory_tools.snapshot()
    foto_akhir = tracemalloc.take_snapshot()

    print(f"\n=== HASIL UJI MEMORI ({siklus} siklus) ===")
    print(f"{'ukuran':<14}{'awal':>10}{'akhir':>10}{'selisih':>10}{'per siklus':>13}")
    bocor = False
    for kunci, label in (("widget", "widget"), ("objek_python", "objek Python"),
                         ("python_kb", "Python (KB)"), ("ram_mb", "RAM (MB)")):
        selisih = akhir[kunci] - awal[kunci]
        print(f"{label:<14}{awal[kunci]:>10}{akhir[kunci]:>10}{selisih:>10}{selisih / siklus:>13.2f}")
    bocor = akhir["widget"] > awal["widget"]
    print(f"{'waktu (ms)':<14}{'':>10}{'':>10}{'':>10}{ms_per_siklus:>13.1f}")
    print("\nKelas widget terbanyak:", memory_tools.widget_per_kelas())
    print("\nBaris kode yang alokasinya paling bertambah (tracemalloc):")
    for statistik in foto_akhir.compare_to(foto_awal, "lineno")[:5]:
        print("  ", statistik)
    print("\nKESIMPULAN:", "ADA KEBOCORAN widget (jumlahnya terus naik)" if bocor else "AMAN, jumlah widget stabil")
    return 1 if bocor else 0


if __name__ == "__main__":
    sys.exit(main())
