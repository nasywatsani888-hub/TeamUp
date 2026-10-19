# tes_skala.py — uji "banyak data": berapa lama UI tertahan kalau datanya banyak? (Pertemuan 7)
# Sesudah paginasi, tiap halaman hanya membuat satu "halaman" item (12-15), jadi waktunya TETAP walau data 1000+.
# Baris "Muat 1 halaman lagi" mengukur klik tombol "Muat lebih banyak" (dilewati '-' kalau versi kode belum punya paginasi).
# Letakkan di folder proyek (sejajar main.py), lalu:   python tes_skala.py
#                                                      python tes_skala.py 100 500 2000   (jumlah data sendiri)
# Data DIPERBANYAK hanya di memori (tidak mengubah file / repo apa pun).
# Yang diukur: waktu thread UI tertahan saat membuka halaman yang menampilkan SEMUA item sekaligus.
import copy
import json
import os
import subprocess
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BATAS_MS = 100   # di atas ini pengguna mulai merasa aplikasi "ngelag"


def ukur_satu(jumlah):
    """Dijalankan di PROSES BARU supaya tiap ukuran data adil (cache kosong)."""
    from PySide6.QtWidgets import QApplication
    import data_store
    import styles
    import workers
    app = QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    dasar_p, dasar_l, dasar_u = (copy.deepcopy(data_store.postingan_list), copy.deepcopy(data_store.lomba_list),
                                 copy.deepcopy(data_store.users))
    data_store.postingan_list.clear()
    data_store.lomba_list.clear()
    for i in range(jumlah):
        p = copy.deepcopy(dasar_p[i % len(dasar_p)]); p["id"] = 1000 + i; p["judul"] += f" #{i}"
        data_store.postingan_list.append(p)
        l = copy.deepcopy(dasar_l[i % len(dasar_l)]); l["id"] = 1000 + i; l["judul"] += f" #{i}"
        data_store.lomba_list.append(l)
        u = copy.deepcopy(dasar_u[i % len(dasar_u)]); u["email"] = f"user{i}@x.id"; u["username"] = f"user{i}"
        data_store.users.append(u)
    from main import MainWindow
    jendela = MainWindow()
    jendela.resize(1320, 820)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    d = jendela.dashboard_page
    for _ in range(3):                      # pemanasan: pekerjaan awal jendela jangan ikut terukur
        d.show_content("beranda")
    # Seperti pengguna yang sudah beberapa detik di layar splash / login: tunggu preload gambar (worker) selesai
    batas = time.time() + 20
    while (workers.jumlah_aktif() or time.time() < batas - 19.7) and time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    def ukur(aksi):
        mulai = time.perf_counter()
        aksi()
        for _ in range(3):
            app.processEvents()
        return (time.perf_counter() - mulai) * 1000

    def muat_post():
        d.upload_page.paginasi.tombol.click()

    def muat_rekan():
        d.partner_page.paginasi.tombol.click()

    hasil = {"Beranda (4 kartu)": ukur(lambda: d.show_content("beranda"))}
    hasil["Buka Postingan Saya"] = ukur(lambda: d.show_content("unggah"))
    hasil["  Muat 1 halaman lagi"] = ukur(muat_post) if hasattr(d.upload_page, "paginasi") and d.upload_page.paginasi.tombol.isVisible() else None
    hasil["Ganti filter status"] = ukur(lambda: d.upload_page.select_status("Disetujui"))
    hasil["Buka halaman Lomba"] = ukur(lambda: d.show_content("lomba"))
    hasil["  Muat 1 halaman lagi "] = ukur(d.lomba_page.backend.muatLagi) if hasattr(d.lomba_page.backend, "muatLagi") else None
    hasil["Filter Lomba"] = ukur(lambda: d.lomba_page.backend.setFilters({"biaya": ["Gratis"]}))
    hasil["Buka Rekan Tim"] = ukur(lambda: d.show_content("rekan"))
    hasil["  Muat 1 halaman lagi  "] = ukur(muat_rekan) if hasattr(d.partner_page, "paginasi") and d.partner_page.paginasi.tombol.isVisible() else None
    workers.tunggu_selesai()
    print("HASIL=" + json.dumps(hasil))


def main():
    daftar = [int(x) for x in sys.argv[1:]] or [10, 50, 200, 1000]
    tabel = {}
    for jumlah in daftar:
        keluaran = subprocess.run([sys.executable, __file__, "--satu", str(jumlah)], capture_output=True, text=True).stdout
        baris = [b for b in keluaran.splitlines() if b.startswith("HASIL=")]
        if not baris:
            print(f"ukuran {jumlah}: gagal / terlalu lama"); continue
        tabel[jumlah] = json.loads(baris[0][6:])
    print(f"=== UJI BANYAK DATA: waktu UI tertahan (ms); di atas {BATAS_MS} ms = terasa ngelag ===\n")
    print(f"{'halaman / aksi':<24}" + "".join(f"{str(n) + ' data':>12}" for n in tabel))
    for nama in next(iter(tabel.values())):
        print(f"{nama:<24}" + "".join((f"{h[nama]:>9.0f} {'!' if h[nama] > BATAS_MS else ' '} " if h.get(nama) is not None else f"{'-':>10}  ")
                                      for h in tabel.values()))
    print("\n'!' = melewati batas. Tanpa paginasi waktu naik sebanding dengan jumlah data (semua widget dibuat sekaligus")
    print("di thread UI; worker TIDAK bisa membuat widget). Dengan paginasi waktunya tetap karena hanya satu halaman yang dibuat.")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--satu":
        ukur_satu(int(sys.argv[2]))
    else:
        main()
