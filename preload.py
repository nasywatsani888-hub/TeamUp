# preload.py — memuat foto & poster di LATAR BELAKANG saat aplikasi dibuka (Pertemuan 7)
#
# Masalah yang diukur: foto profil besar (mis. marques.png 1920x2876 px) membutuhkan ±200 ms untuk
# di-decode & diskalakan. Kalau itu dilakukan di thread UI saat halaman Rekan Tim pertama kali dibuka,
# aplikasi "macet" sesaat. Solusi: selagi user masih di layar splash / login, worker menyiapkan
# semua gambar; saat halaman dibuka, gambarnya sudah siap (helpers._bangun_pixmap tinggal mengambil).
#
# Pembagian tugas (penting!):
#   thread UI  -> MENYUSUN daftar kerja (menyentuh data_store), karena data bersama hanya boleh
#                 diakses dari satu thread supaya tidak terjadi race condition.
#   thread worker -> hanya MERENDER gambar (QImage) dan menulis berkas; tidak menyentuh data_store / widget.
import os
import time

import config
import data_store
import helpers
import memory_tools
import sizes
import workers

UKURAN_AVATAR = (44, 90, sizes.EDIT_PROFILE_AVATAR_SIZE)   # make_avatar dipakai dengan ukuran ini
UKURAN_PROFIL_KOTAK = 170                                  # make_photo_square di halaman Profil Rekan


def susun_daftar_kerja():
    """Daftar kunci gambar yang akan dipakai UI: (path, lebar, tinggi, radius, bulat_bawah, skala, mtime)."""
    poster, foto, lain = [], [], []   # urutan kerja: yang dibutuhkan paling awal dikerjakan paling dulu
    for lomba in data_store.lomba_list:
        path = helpers.poster_file(lomba)
        if path:
            mtime = os.path.getmtime(path)
            poster.append((path, sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_POSTER_HEIGHT, 20, False, 2, mtime))   # kartu (Beranda)
            lain.append((path, sizes.DETAIL_POSTER_WIDTH, sizes.DETAIL_POSTER_HEIGHT, 16, True, 2, mtime))  # halaman detail
    foto_dir = os.path.join(config.ASSETS_DIR, "foto")
    for user in data_store.users:
        path = os.path.join(foto_dir, user.get("foto", "")) if user.get("foto") else ""
        if path and os.path.isfile(path):
            mtime = os.path.getmtime(path)
            for ukuran in UKURAN_AVATAR:
                foto.append((path, ukuran, ukuran, ukuran // 2, True, 1, mtime))     # lingkaran
            foto.append((path, UKURAN_PROFIL_KOTAK, UKURAN_PROFIL_KOTAK, 16, True, 1, mtime))
    for post in data_store.postingan_list:
        path = helpers.cari_gambar_poster(post.get("gambar", []))
        if path:
            lain.append((path, sizes.POST_THUMB_SIZE, sizes.POST_THUMB_SIZE, 4, True, 2, os.path.getmtime(path)))
    kerja = poster + foto + lain
    return list(dict.fromkeys(kerja))   # buang duplikat, urutan tetap


def kerjakan(kontrol, kerja):
    """Dijalankan WORKER. Merender tiap gambar lalu memarkirnya untuk thread UI."""
    mulai = time.perf_counter()
    jumlah = 0
    for nomor, kunci in enumerate(kerja, start=1):
        if kontrol.dibatalkan:
            break
        if helpers.sudah_dipakai(kunci):          # thread UI sudah membuatnya sendiri -> lewati
            continue
        path, lebar, tinggi, radius, bulat_bawah, skala, mtime = kunci
        gambar = helpers.render_kotak(path, lebar, tinggi, radius, bulat_bawah, skala)
        helpers.simpan_siap(kunci, gambar)
        if not bulat_bawah and (lebar, tinggi, radius) == (sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_POSTER_HEIGHT, 20):
            tujuan = helpers.lokasi_png_qml(path, mtime, lebar, tinggi, radius)     # berkas yang dibaca QML
            if not os.path.exists(tujuan):
                helpers.simpan_png_atomik(gambar, tujuan)
        jumlah += 1
        kontrol.laporkan(nomor * 100 // len(kerja))
    return jumlah, (time.perf_counter() - mulai) * 1000


def _selesai(hasil):
    jumlah, ms = hasil
    if memory_tools.DEBUG:
        print(f"[preload] {jumlah} gambar disiapkan di latar belakang dalam {ms:.0f} ms")


_worker = None   # preload yang sedang berjalan


def mulai():
    """Mulai preload. Aman dipanggil berkali-kali: kalau yang sebelumnya masih jalan, tidak dimulai lagi
    (dua worker yang mengerjakan gambar yang sama hanya membuang CPU)."""
    global _worker
    if _worker is not None and _worker in workers._aktif:
        return _worker
    kerja = susun_daftar_kerja()
    if not kerja:
        return None
    _worker = workers.jalankan(kerjakan, kerja, saat_selesai=_selesai)
    return _worker
