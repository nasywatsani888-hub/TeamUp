#!/usr/bin/env python3
# profil_cpu.py — Profiler CPU TeamUp: menemukan "titik panas" (fungsi yang paling makan waktu) (Pertemuan 13)
#
# Prinsip debugging performa: JANGAN menebak bagian mana yang lambat, UKUR. Seringkali tebakan salah:
# kode yang terlihat rumit ternyata cepat, dan satu baris sepele ternyata memakan 80% waktu.
#
# Alat: cProfile (bawaan Python) = profiler DETERMINISTIK: mencatat SETIAP panggilan fungsi (berapa kali, berapa lama).
#   tottime   = waktu di DALAM fungsi itu sendiri (tidak termasuk fungsi yang dipanggilnya)  -> menemukan titik panas
#   cumtime   = waktu fungsi itu + semua yang dipanggilnya (kumulatif)                       -> menemukan alur yang berat
#   ncalls    = jumlah panggilan                                                               -> lambat karena berat, atau karena dipanggil terlalu sering?
# Kekurangan yang harus diketahui: mencatat tiap panggilan itu sendiri memperlambat program (overhead), terutama untuk
# fungsi kecil yang sangat sering dipanggil. Karena itu laporan memuat "waktu tanpa profiler" sebagai pembanding, dan
# angka profiler dibaca sebagai PERBANDINGAN ANTAR-FUNGSI, bukan waktu mutlak.
#
# Contoh:
#   python3 profil_cpu.py                     semua skenario
#   python3 profil_cpu.py hash_password       satu skenario
#   python3 profil_cpu.py --daftar            daftar skenario
#   python3 profil_cpu.py --atas 12 --urut kumulatif
#   python3 profil_cpu.py --simpan-prof prof  simpan berkas .prof (bisa dibuka: python3 -m pstats prof/validasi.prof)
#   python3 profil_cpu.py --json profil.json  simpan ringkasan (dasar pembanding untuk uji regresi performa)
#
# TERISOLASI seperti jalankan_semua_tes.py: database salinan, folder data sementara, kunci acak, tanpa jendela.
# Hanya modul bawaan Python (cProfile, pstats) + aplikasi itu sendiri.
import argparse
import atexit
import cProfile
import hashlib
import io
import json
import os
import pstats
import secrets
import shutil
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

# ---- Isolasi: harus diatur SEBELUM modul aplikasi diimpor (lokasi database dibaca saat impor)
_TMP = tempfile.mkdtemp(prefix="teamup_profil_")
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))
_DB_ASLI = os.path.join(BASE, "teamup.db")
if os.path.isfile(_DB_ASLI):
    shutil.copy2(_DB_ASLI, os.path.join(_TMP, "teamup.db"))
os.environ["TEAMUP_DB"] = os.path.join(_TMP, "teamup.db")
os.environ["TEAMUP_DATA"] = os.path.join(_TMP, "data")
os.environ["HMAC_SECRET_KEY"] = secrets.token_hex(32)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("TEAMUP_DEBUG_MEMORY", None)

SKENARIO = {}          # nama -> (deskripsi, fungsi_siapkan)

# Penjelasan untuk fungsi yang sering muncul sebagai titik panas
PETUNJUK = (
    ("pbkdf2_hmac", "PBKDF2 SENGAJA lambat (120.000 iterasi) untuk memperlambat penebakan password. Ini bukan bug."),
    ("hmac_digest", "HMAC-SHA256 sebagai keystream enkripsi: satu panggilan per 32 byte data (2 MB = ±65.000 panggilan)."),
    ("hmac.digest", "HMAC-SHA256 sebagai keystream enkripsi: satu panggilan per 32 byte data."),
    ("from_bytes", "Konversi byte <-> bilangan bulat besar untuk XOR; ongkos sebanding dengan ukuran data."),
    ("Pattern.sub", "Penyamaran/pembersihan memakai banyak regex berurutan; tiap regex memindai seluruh teks."),
    ("Pattern.fullmatch", "Pencocokan regex untuk validasi."),
    ("Connection.execute", "Waktu di dalam SQLite (menjalankan query)."),
    ("sqlite3.connect", "Membuka koneksi SQLite baru setiap operasi (ditambah PRAGMA WAL/foreign_keys)."),
    ("setStyleSheet", "Qt menghitung ulang gaya untuk seluruh pohon widget; sering mahal saat startup."),
    ("processEvents", "Qt memproses antrean event (menggambar ulang, timer, dll.)."),
    ("QPixmap", "Memuat / mengubah ukuran gambar; mahal untuk gambar besar."),
)


def skenario(nama, deskripsi):
    def daftar(fungsi):
        SKENARIO[nama] = (deskripsi, fungsi)
        return fungsi
    return daftar


# ============================================================== Skenario
@skenario("hash_password", "Hash & verifikasi password (PBKDF2) — 3 hash, 3 verifikasi benar, 3 salah, 1 samakan_waktu")
def siapkan_hash():
    from database import sandi
    import keamanan_akun
    tersimpan = sandi.hash_password("Rahasia-Super-Panjang-2026!")

    def kerja():
        for _ in range(3):
            sandi.hash_password("Rahasia-Super-Panjang-2026!")
            sandi.cocok(tersimpan, "Rahasia-Super-Panjang-2026!")
            sandi.cocok(tersimpan, "salah-salah-salah-123!")
        keamanan_akun.samakan_waktu("apa-saja")
    return kerja


@skenario("validasi", "Validasi input — 40 putaran x 160 isian x 7 aturan (email, username, nama, password, URL, kontak, bersihkan)")
def siapkan_validasi():
    import validasi as v
    contoh = []
    for i in range(20):
        contoh += [f"user{i}@kampus.ac.id", f"Budi{i}@x", "a@b.", f"user_{i}", f"bu di{i}!", f"Budi Santoso {i}",
                   f"Rahasia-Super-Panjang-{i}!", f"pendek{i}", f"https://kampus.ac.id/lomba/{i}", f"http://x{i}",
                   f"081234567{i:03d}", f"hubungi saya {i}", f"  spasi   banyak {i}  ", f"javascript:alert({i})",
                   f"<b>{i}</b>", "x" * (i + 1)]

    def kerja():
        for _ in range(40):
            for teks in contoh:
                v.periksa_email(teks)
                v.periksa_username(teks)
                v.periksa_nama(teks)
                v.periksa_password(teks)
                v.periksa_url(teks)
                v.periksa_kontak(teks)
                v.bersihkan_teks(teks)
    return kerja


@skenario("samarkan_log", "Penyamaran log — 20 putaran x 300 baris berisi email, telepon, hash, token, path")
def siapkan_samarkan():
    import penanganan_error as pe
    baris = []
    for i in range(60):
        baris += [f"2026-11-10 04:36:21,196 | INFO | MainThread | mulai sesi user{i}@kampus.ac.id dari /Users/mazaya/Documents/TeamUp",
                  f"2026-11-10 04:36:22,001 | WARNING | MainThread | login_gagal email=budi{i}@x.com sisa={i % 5} hp 0812-3456-{i:04d}",
                  "2026-11-10 04:36:23,500 | INFO | MainThread | hash pbkdf2_sha256$120000$8a2dbbf561c747afbeaa54fca0a1fd14$2a1c380ce26a5d26c2f561e1abfed5e5e06ed0f47e630ec7cbe06c98d673b2c6",
                  f"2026-11-10 04:36:24,100 | INFO | MainThread | kontak enc1$VFVFMR_6uNXO4nr{i} password=abc{i} otp: 4567",
                  f"2026-11-10 04:36:25,900 | INFO | MainThread | memuat {i} postingan dalam 12 ms (tanpa data sensitif sama sekali di baris ini)"]

    def kerja():
        for _ in range(20):
            for b in baris:
                pe.samarkan(b)
    return kerja


@skenario("enkripsi", "Enkripsi — 2 MB bytes (enkripsi+dekripsi) dan 1500 teks pendek (kontak)")
def siapkan_enkripsi():
    import enkripsi
    data = os.urandom(2 * 1024 * 1024)

    def kerja():
        enkripsi.dekripsi_bytes(enkripsi.enkripsi_bytes(data))
        for i in range(1500):
            enkripsi.dekripsi_teks(enkripsi.enkripsi_teks(f"0812-3456-{i:04d}"))
    return kerja


@skenario("database", "Database — 60 putaran muat_users, muat_lomba, muat_postingan, muat_notifikasi (SQLite)")
def siapkan_database():
    from database import repository

    def kerja():
        for _ in range(60):
            repository.muat_users()
            repository.muat_lomba()
            repository.muat_postingan()
            repository.muat_notifikasi()
    return kerja


@skenario("data_store", "Logika data — 5000 putaran get_partners, get_lomba_filter, cari_partner_sesuai_keahlian, get_postingan")
def siapkan_data_store():
    import data_store
    data_store.current_user = data_store.get_user("demo@teamup.com")
    kategori = data_store.lomba_list[0].get("kategori", "") if data_store.lomba_list else ""

    def kerja():
        for _ in range(5000):
            data_store.get_partners()
            data_store.get_lomba_filter({"Biaya": ["Gratis"]})
            data_store.cari_partner_sesuai_keahlian(kategori)
            data_store.get_postingan()
    return kerja


def _siapkan_ui():
    from PySide6.QtWidgets import QApplication
    import data_store
    import styles
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(styles.APP_STYLE)
    data_store.current_user = data_store.get_user("demo@teamup.com")
    return app, data_store


@skenario("ui_startup", "Startup UI — membuat MainWindow (semua halaman) sekali, lalu menutupnya")
def siapkan_ui_startup():
    app, _ = _siapkan_ui()
    from main import MainWindow

    def kerja():
        jendela = MainWindow()
        app.processEvents()
        jendela.close()
        jendela.deleteLater()
        app.processEvents()
    return kerja


@skenario("ui_navigasi", "Navigasi UI — 8 putaran membuka Beranda, Lomba, Rekan Tim, Notifikasi, Riwayat")
def siapkan_ui_navigasi():
    app, data_store = _siapkan_ui()
    from main import MainWindow
    jendela = MainWindow()
    jendela.resize(1320, 820)
    jendela.show_page(jendela.dashboard_page)
    jendela.show()
    app.processEvents()
    dashboard = jendela.dashboard_page

    def kerja():
        for _ in range(8):
            for kunci in ("beranda", "lomba", "rekan", "notifikasi", "riwayat"):
                dashboard.show_content(kunci)
                app.processEvents()
    kerja._penutup = jendela            # tahan referensi agar jendela tidak dibuang sebelum dipakai
    return kerja


# ============================================================== Pengukuran
def sidik_jari(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def asal(berkas):
    if berkas == "~":
        return "C"
    nyata = os.path.abspath(berkas)
    if nyata.startswith(BASE) and "site-packages" not in nyata:
        return "proyek"
    return "pustaka"


def nama_fungsi(kunci):
    berkas, baris, nama = kunci
    if berkas == "~":
        return nama.strip("<>").replace("built-in method ", "").replace("method ", "")
    if asal(berkas) == "proyek":
        tampil = os.path.relpath(os.path.abspath(berkas), BASE)
    else:
        bagian = os.path.abspath(berkas).split(os.sep)
        tampil = os.sep.join(bagian[-2:])
    return f"{tampil}:{baris}({nama})"


def ukur(nama, kerja):
    """Empat kali jalan: (1) DINGIN (pertama: impor modul, cache kosong, inisialisasi Qt), (2-3) HANGAT tanpa profiler
    (diambil yang tercepat sebagai pembanding yang adil), (4) HANGAT dengan cProfile. Membandingkan jalan dingin dengan jalan berprofil akan
    menyesatkan: profiler terlihat 'mempercepat' padahal hanya cache yang sudah terisi."""
    mulai = time.perf_counter()
    kerja()
    dingin = time.perf_counter() - mulai
    polos = float("inf")
    for _ in range(2):                          # dua jalan hangat, ambil yang tercepat (kurangi gangguan sesaat)
        mulai = time.perf_counter()
        kerja()
        polos = min(polos, time.perf_counter() - mulai)
    profiler = cProfile.Profile()
    mulai = time.perf_counter()
    profiler.enable()
    kerja()
    profiler.disable()
    dengan_profiler = time.perf_counter() - mulai
    return profiler, dingin, polos, dengan_profiler


def ringkas(profiler):
    """Daftar fungsi dari hasil cProfile -> list dict, plus total waktu di dalam fungsi (jumlah tottime)."""
    st = pstats.Stats(profiler, stream=io.StringIO())
    total = st.total_tt or 1e-9
    daftar = []
    for kunci, (cc, nc, tt, ct, _penelepon) in st.stats.items():
        daftar.append({"fungsi": nama_fungsi(kunci), "asal": asal(kunci[0]), "ncalls": nc, "tottime": tt,
                       "cumtime": ct, "persen_self": 100.0 * tt / total})
    return daftar, total, st


def cari_petunjuk(fungsi):
    for kata, teks in PETUNJUK:
        if kata.lower() in fungsi.lower():
            return teks
    return ""


def batang(persen, lebar=24):
    isi = max(0, min(lebar, round(persen / 100 * lebar)))
    return "█" * isi + "·" * (lebar - isi)


def laporkan(nama, deskripsi, profiler, dingin, polos, dengan_profiler, atas, urut):
    daftar, total, st = ringkas(profiler)
    print("=" * 96)
    print(f"SKENARIO: {nama} — {deskripsi}")
    print(f"Jalan pertama (dingin): {dingin:.3f} dtk | hangat tanpa profiler: {polos:.3f} dtk | hangat dengan cProfile: "
          f"{dengan_profiler:.3f} dtk (overhead {dengan_profiler / polos if polos else 0:.1f}x) | panggilan: {sum(d['ncalls'] for d in daftar):,}")
    kunci = "cumtime" if urut == "kumulatif" else "tottime"
    teratas = sorted(daftar, key=lambda d: d[kunci], reverse=True)[:atas]
    print(f"\n  TITIK PANAS — urut {'kumulatif' if urut == 'kumulatif' else 'waktu di dalam fungsi sendiri (tottime)'}")
    print(f"  {'% self':>6}  {'':<24}  {'tottime':>8}  {'cumtime':>8}  {'ncalls':>9}  fungsi")
    for d in teratas:
        print(f"  {d['persen_self']:5.1f}%  {batang(d['persen_self'])}  {d['tottime']:8.3f}  {d['cumtime']:8.3f}  {d['ncalls']:9,}  "
              f"{d['fungsi'][:70]}{'  [' + d['asal'] + ']' if d['asal'] != 'proyek' else ''}")
    proyek = sorted((d for d in daftar if d["asal"] == "proyek" and not d["fungsi"].endswith("(<module>)")),
                    key=lambda d: d["cumtime"], reverse=True)[:min(atas, 6)]
    if proyek:
        print("\n  KODE PROYEK PALING MAKAN WAKTU (kumulatif, termasuk yang dipanggilnya)")
        for d in proyek:
            print(f"  {d['cumtime']:8.3f} dtk  {d['ncalls']:9,}x  {d['fungsi'][:78]}")
    if polos and dengan_profiler / polos < 0.85:
        print("\n  Catatan: overhead < 1x berarti jalan berprofil lebih ringan dari jalan pembanding (cache / antrean event Qt "
              "berbeda antar jalan). Baca PERSENTASE antar-fungsi, bukan waktu mutlaknya.")
    puncak = max(daftar, key=lambda d: d["tottime"])
    petunjuk = cari_petunjuk(puncak["fungsi"])
    print(f"\n  TEMUAN: {puncak['persen_self']:.0f}% waktu dihabiskan di {puncak['fungsi'][:70]} "
          f"({puncak['ncalls']:,} panggilan, rata-rata {puncak['tottime'] / max(1, puncak['ncalls']) * 1e6:.1f} µs).")
    if petunjuk:
        print(f"          {petunjuk}")
    elif puncak["ncalls"] > 5000 and puncak["tottime"] / max(1, puncak["ncalls"]) < 20e-6:
        print("          Murah per panggilan tetapi SANGAT sering dipanggil: kurangi jumlah panggilan, bukan isi fungsinya.")
    print()
    return {"waktu_dingin": round(dingin, 4), "waktu_polos": round(polos, 4), "waktu_profil": round(dengan_profiler, 4), "total_tottime": round(total, 4),
            "teratas": [{"fungsi": d["fungsi"], "persen_self": round(d["persen_self"], 1), "tottime": round(d["tottime"], 4),
                         "ncalls": d["ncalls"]} for d in teratas]}, st


def main(argv=None):
    ap = argparse.ArgumentParser(description="Profiler CPU TeamUp (cProfile).")
    ap.add_argument("skenario", nargs="*", help="nama skenario (kosong = semua)")
    ap.add_argument("--daftar", action="store_true", help="tampilkan daftar skenario")
    ap.add_argument("--atas", type=int, default=8, help="jumlah fungsi teratas yang ditampilkan")
    ap.add_argument("--urut", choices=("total", "kumulatif"), default="total", help="urutan tabel titik panas")
    ap.add_argument("--simpan-prof", metavar="FOLDER", help="simpan berkas .prof per skenario")
    ap.add_argument("--json", metavar="BERKAS", help="simpan ringkasan JSON")
    a = ap.parse_args(argv)

    if a.daftar:
        for nama, (deskripsi, _f) in SKENARIO.items():
            print(f"{nama:<14} {deskripsi}")
        return 0
    pilihan = a.skenario or list(SKENARIO)
    tak_dikenal = [n for n in pilihan if n not in SKENARIO]
    if tak_dikenal:
        print(f"Skenario tidak dikenal: {', '.join(tak_dikenal)}. Lihat --daftar.")
        return 1

    sidik_awal = sidik_jari(_DB_ASLI)
    print(f"PROFIL CPU TEAMUP — Python {sys.version.split()[0]} | database salinan sementara | tanpa jendela\n")
    laporan = {}
    for nama in pilihan:
        deskripsi, siapkan = SKENARIO[nama]
        kerja = siapkan()
        profiler, dingin, polos, dengan_profiler = ukur(nama, kerja)
        ringkasan, st = laporkan(nama, deskripsi, profiler, dingin, polos, dengan_profiler, a.atas, a.urut)
        laporan[nama] = ringkasan
        if a.simpan_prof:
            os.makedirs(a.simpan_prof, exist_ok=True)
            profiler.dump_stats(os.path.join(a.simpan_prof, f"{nama}.prof"))
    print("=" * 96)
    print("RINGKASAN WAKTU (hangat, tanpa profiler):")
    for nama, r in laporan.items():
        puncak = r["teratas"][0]
        print(f"  {nama:<14} {r['waktu_polos']:7.3f} dtk (dingin {r['waktu_dingin']:.3f})   titik panas: {puncak['persen_self']:4.0f}% di {puncak['fungsi'][:52]}")
    if sidik_awal is not None:
        print("\nteamup.db asli:", "TIDAK berubah" if sidik_jari(_DB_ASLI) == sidik_awal else "BERUBAH! (isolasi bocor)")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"python": sys.version.split()[0], "skenario": laporan}, f, indent=2, ensure_ascii=False)
        print(f"Ringkasan JSON: {a.json}")
    if a.simpan_prof:
        print(f"Berkas .prof: {a.simpan_prof}/  (buka: python3 -m pstats {a.simpan_prof}/<nama>.prof)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
