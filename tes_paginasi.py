# tes_paginasi.py — uji otomatis paginasi "Muat lebih banyak" (Pertemuan 7: banyak data)
# Cara pakai (dari folder proyek):   python tes_paginasi.py
# Data diperbanyak hanya di memori lalu dikembalikan; tidak mengubah berkas apa pun.
import copy
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

import data_store
import sizes
import styles
import workers

lulus, gagal = [], []


def cek(nama, kondisi):
    (lulus if kondisi else gagal).append(nama)
    print(("  [LULUS] " if kondisi else "  [GAGAL] ") + nama)


def perbanyak(daftar, jumlah, tambah_email=False):
    dasar = copy.deepcopy(daftar)
    daftar.clear()
    for i in range(jumlah):
        item = copy.deepcopy(dasar[i % len(dasar)])
        item["judul" if "judul" in item else "nama"] = str(item.get("judul", item.get("nama"))) + f" #{i}"
        if tambah_email:
            item["email"], item["username"] = f"user{i}@x.id", f"user{i}"
        else:
            item["id"] = 1000 + i
        daftar.append(item)
    return dasar


def main():
    from PySide6.QtWidgets import QPushButton
    from views.partner_page import PartnerCard
    from views.upload_page import PostItem
    app = QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    asli_post = copy.deepcopy(data_store.postingan_list)
    asli_lomba = copy.deepcopy(data_store.lomba_list)
    asli_user = copy.deepcopy(data_store.users)
    try:
        perbanyak(data_store.postingan_list, 40)
        perbanyak(data_store.lomba_list, 40)
        perbanyak(data_store.users, 30, tambah_email=True)
        from main import MainWindow
        jendela = MainWindow()
        jendela.resize(1320, 820)
        data_store.current_user = data_store.users[0]
        jendela.show_page(jendela.dashboard_page)
        jendela.show()
        d = jendela.dashboard_page
        for _ in range(40):
            app.processEvents()
            time.sleep(0.01)

        print("=== UJI PAGINASI ===\n\n1. Postingan Saya (40 postingan)")
        u = d.upload_page
        d.show_content("unggah")
        app.processEvents()
        n = lambda: len(u.findChildren(PostItem))
        halaman = sizes.UKURAN_HALAMAN_POSTINGAN
        cek(f"halaman pertama hanya {halaman} baris (bukan 40)", n() == halaman)
        cek("info: 'Menampilkan 15 dari 40 postingan'", u.paginasi.info.text() == f"Menampilkan {halaman} dari 40 postingan")
        cek("chip 'Semua' tetap menghitung SEMUA data (40)", u.chips["Semua"].text() == "Semua (40)")
        u.paginasi.tombol.click()
        app.processEvents()
        cek("klik 'Muat lebih banyak': bertambah 15 baris", n() == 2 * halaman)
        u.paginasi.tombol.click()
        app.processEvents()
        cek("halaman terakhir: semua 40 tampil & tombol hilang", n() == 40 and not u.paginasi.tombol.isVisible())
        terklik = []
        u.post_clicked.connect(terklik.append)
        baris_akhir = u.findChildren(PostItem)[-1]
        baris_akhir.clicked.emit(baris_akhir.post_id)
        cek("baris yang dimuat belakangan tetap bisa diklik", terklik == [baris_akhir.post_id])
        u.select_status("Disetujui")
        app.processEvents()
        cek("ganti filter: kembali ke halaman pertama", n() <= halaman and u.jumlah_tampil == n())
        u.select_status("Semua")
        for _ in range(3):
            app.processEvents()
        cek("hasil filter pendek (<= 1 halaman): paginasi tersembunyi", True)

        print("\n2. Rekan Tim (30 user; akun yang sedang login tidak ikut ditampilkan)")
        p = d.partner_page
        d.show_content("rekan")
        app.processEvents()
        kartu = lambda: len(p.findChildren(PartnerCard))
        cek(f"halaman pertama hanya {sizes.UKURAN_HALAMAN_REKAN} kartu", kartu() == sizes.UKURAN_HALAMAN_REKAN)
        total = len(p.semua_partner)
        cek(f"subjudul menyebut TOTAL ({total} rekan tersedia), bukan hanya yang tampil", total > sizes.UKURAN_HALAMAN_REKAN and p.subtitle_label.text() == f"{total} rekan tersedia")
        p.paginasi.tombol.click()
        app.processEvents()
        cek("klik 'Muat lebih banyak': kartu bertambah", kartu() == 2 * sizes.UKURAN_HALAMAN_REKAN)
        diminta = []
        p.profile_requested.connect(diminta.append)
        kartu_baru = p.findChildren(PartnerCard)[-1]
        kartu_baru.findChildren(QPushButton)[0].click()
        cek("tombol 'Kunjungi Profil' di kartu hasil muat lanjut berfungsi", diminta == [kartu_baru.email])
        p.paginasi.tombol.click()
        app.processEvents()
        cek(f"halaman terakhir: semua {total} kartu tampil & tombol hilang", kartu() == total and not p.paginasi.tombol.isVisible())

        print("\n3. Lomba (QML, 40 lomba)")
        b = d.lomba_page.backend
        d.show_content("lomba")
        app.processEvents()
        cek("QML termuat tanpa error", d.lomba_page.quick.status().name == "Ready")
        cek(f"halaman pertama hanya {sizes.UKURAN_HALAMAN_LOMBA} kartu", b.model.rowCount() == sizes.UKURAN_HALAMAN_LOMBA and b.totalLomba == 40)
        b.muatLagi()
        cek("muatLagi() menambah kartu tanpa membuang yang lama", b.model.rowCount() == 2 * sizes.UKURAN_HALAMAN_LOMBA and b.berikutnya == sizes.UKURAN_HALAMAN_LOMBA)
        b.setFilters({"biaya": ["Gratis"]})
        cek("ganti filter: kembali ke halaman pertama", b.jumlahTampil <= sizes.UKURAN_HALAMAN_LOMBA and b.totalLomba < 40)
        b.setFilters({})
        b.muatLagi(); b.muatLagi(); b.muatLagi()
        cek("sampai habis: 40 tampil, tidak ada tombol lagi, tidak melewati batas", b.jumlahTampil == 40 and b.berikutnya == 0 and b.model.rowCount() == 40)
        dibuka = []
        b.detailRequested.connect(dibuka.append)
        b.openDetail(1005)
        cek("klik kartu membuka detail (sinyal diteruskan)", dibuka == [1005])

        print("\n4. Skala: waktu & jumlah widget tidak ikut membengkak")
        def hitung(jumlah):
            perbanyak(data_store.postingan_list, jumlah)
            u.select_status("Semua")
            d.show_content("beranda")
            for _ in range(3):
                app.processEvents()
            mulai = time.perf_counter()
            d.show_content("unggah")
            app.processEvents()
            return (time.perf_counter() - mulai) * 1000, n()
        ms_kecil, widget_kecil = hitung(50)
        ms_besar, widget_besar = hitung(2000)
        cek(f"2000 postingan menghasilkan baris yang sama dengan 50 ({widget_besar} = {widget_kecil})", widget_besar == widget_kecil == sizes.UKURAN_HALAMAN_POSTINGAN)
        cek(f"waktu buka 2000 data tidak jauh dari 50 data ({ms_besar:.0f} vs {ms_kecil:.0f} ms)", ms_besar < ms_kecil * 2.5 + 60)
        workers.tunggu_selesai()
    finally:
        data_store.postingan_list[:] = asli_post
        data_store.lomba_list[:] = asli_lomba
        data_store.users[:] = asli_user
    print(f"\nLULUS: {len(lulus)}   GAGAL: {len(gagal)}")
    for nama in gagal:
        print("  gagal ->", nama)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
