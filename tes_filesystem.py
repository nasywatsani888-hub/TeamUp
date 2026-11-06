# tes_filesystem.py — Uji otomatis Pertemuan 11: File System & Local Storage
#
# Yang diuji:
#   1. file_storage   : lokasi folder, nama aman, anti path-traversal, validasi, simpan atomik, hapus
#   2. settings_store : simpan/muat JSON, file rusak, tipe salah, simpan bersamaan dari banyak thread
#   3. disk_cache     : cache hit/miss, pembuatan atomik, batas ukuran (LRU), batas umur
#   4. enkripsi       : teks & berkas, nonce acak, deteksi perubahan data, kunci salah, balapan dua penulis
#   5. integrasi DB   : kontak terenkripsi di database, terbaca normal di aplikasi, migrasi data lama
#   6. integrasi UI   : path_foto (foto user vs foto bawaan), salin_berkas (poster biasa, dokumen .enc)
#
# TERISOLASI: memakai folder data & database sementara, tidak menyentuh data asli maupun teamup.db.
# Cara menjalankan:  python3 tes_filesystem.py
import os
import sys
import tempfile
import threading
import time

# Folder data & database sementara HARUS diatur sebelum modul aplikasi dipakai
TEMP = tempfile.mkdtemp(prefix="teamup_tes_fs_")
os.environ["TEAMUP_DATA"] = os.path.join(TEMP, "data")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import disk_cache
import enkripsi
import file_storage
import settings_store

LULUS = 0
GAGAL = 0


def cek(nama, kondisi):
    global LULUS, GAGAL
    if kondisi:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}")


def tulis(path, isi):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(isi)
    return path


def sisa_tmp(folder):
    return [n for n in os.listdir(folder) if n.endswith(".tmp")]


# =========================================================== 1. file_storage
def uji_file_storage():
    print("\n1. file_storage — penyimpanan berkas lokal")
    fs = file_storage
    cek("folder data mengikuti TEAMUP_DATA", fs.folder_data() == os.environ["TEAMUP_DATA"])
    fs.siapkan_folder()
    cek("semua subfolder dibuat (poster, dokumen, foto, cache, konfigurasi, cadangan)",
        all(os.path.isdir(fs.folder_jenis(j)) for j in fs.JENIS_FOLDER))
    try:
        fs.folder_jenis("tidak_ada")
        cek("jenis berkas tidak dikenal ditolak", False)
    except ValueError:
        cek("jenis berkas tidak dikenal ditolak", True)

    cek("nama_aman membuang path ../../", fs.nama_aman("../../etc/passwd") == "passwd")
    cek("nama_aman membuang path Windows", fs.nama_aman("C:\\Users\\x\\y.PDF") == "y.pdf")
    cek("nama_aman mengganti spasi & simbol", fs.nama_aman("Poster Lomba #1.pdf") == "Poster_Lomba_1.pdf")
    cek("nama_aman: nama kosong diberi nama bawaan", fs.nama_aman("###") == "berkas")
    cek("nama_aman membatasi panjang nama", len(fs.nama_aman("a" * 500 + ".pdf")) <= 70)

    for jahat in ("../x.pdf", "../../etc/passwd", "sub/x.pdf", ""):
        try:
            fs.path_berkas("poster", jahat)
            ditolak = False
        except ValueError:
            ditolak = True
        cek(f"path traversal ditolak: {jahat!r}", ditolak)

    pdf = tulis(os.path.join(TEMP, "sumber", "poster.pdf"), b"%PDF-1.4 isi poster")
    cek("periksa_berkas: PDF valid lolos", fs.periksa_berkas(pdf, (".pdf",), 10) == (True, ""))
    cek("periksa_berkas: format salah ditolak", fs.periksa_berkas(pdf, (".png",), 10)[0] is False)
    cek("periksa_berkas: berkas tidak ada ditolak", fs.periksa_berkas(os.path.join(TEMP, "hilang.pdf"), (".pdf",), 10)[0] is False)
    kosong = tulis(os.path.join(TEMP, "sumber", "kosong.pdf"), b"")
    cek("periksa_berkas: berkas kosong ditolak", fs.periksa_berkas(kosong, (".pdf",), 10)[0] is False)
    besar = tulis(os.path.join(TEMP, "sumber", "besar.pdf"), os.urandom(1024 * 1024 + 1))
    ok, pesan = fs.periksa_berkas(besar, (".pdf",), 1)
    cek("periksa_berkas: lebih dari batas MB ditolak dengan pesan jelas", ok is False and "1 MB" in pesan)

    nama1 = fs.simpan_berkas(pdf, "poster")
    nama2 = fs.simpan_berkas(pdf, "poster")
    cek("simpan_berkas: isi tersalin sama persis", open(fs.path_berkas("poster", nama1), "rb").read() == open(pdf, "rb").read())
    cek("simpan_berkas: dua berkas bernama sama tidak saling menimpa", nama1 != nama2 and fs.berkas_ada("poster", nama2))
    cek("simpan_berkas: tidak meninggalkan berkas .tmp", sisa_tmp(fs.folder_jenis("poster")) == [])
    try:
        fs.simpan_berkas(os.path.join(TEMP, "hilang.pdf"), "poster")
        gagal_bersih = False
    except OSError:
        gagal_bersih = sisa_tmp(fs.folder_jenis("poster")) == []
    cek("simpan_berkas: sumber hilang -> error & tidak ada sisa .tmp", gagal_bersih)

    cek("hapus_berkas: berkas ada -> True", fs.hapus_berkas("poster", nama1) is True and not fs.berkas_ada("poster", nama1))
    cek("hapus_berkas: berkas tidak ada -> False (tidak error)", fs.hapus_berkas("poster", nama1) is False)
    cek("hapus_berkas: nama berbahaya -> False (tidak menghapus di luar folder)", fs.hapus_berkas("poster", "../../x") is False)

    cek("ukuran_folder menghitung isi folder", fs.ukuran_folder(fs.folder_jenis("poster")) == os.path.getsize(pdf))
    cek("format_ukuran: 1536 byte -> 1.5 KB", fs.format_ukuran(1536) == "1.5 KB")
    cek("cukup_ruang: butuh ruang mustahil besar -> False", fs.cukup_ruang(fs.folder_data(), 10 ** 18) is False)


# ========================================================== 2. settings_store
def uji_settings():
    print("\n2. settings_store — konfigurasi JSON")
    st = settings_store
    cek("tanpa berkas: memakai nilai bawaan", st.ambil("jendela_lebar") == st.BAWAAN["jendela_lebar"] and st.ambil("ingat_email") is False)
    cek("atur() menyimpan ke disk", st.atur("email_terakhir", "a@b.com") and os.path.isfile(st.lokasi_file()))
    cek("atur() menolak kunci tak dikenal", st.atur("tidak_ada", 1) is False)
    cek("atur() menolak tipe salah (teks untuk bool)", st.atur("ingat_email", "ya") is False)
    cek("atur() menolak bool untuk angka", st.atur("jendela_lebar", True) is False)
    cek("atur_banyak() menyimpan beberapa nilai sekaligus", st.atur_banyak(jendela_lebar=1000, jendela_tinggi=600, ingat_email=True))
    st._data = None
    data = st.muat()
    cek("muat() ulang: nilai tetap ada (tahan tutup-buka aplikasi)",
        data["jendela_lebar"] == 1000 and data["ingat_email"] is True and data["email_terakhir"] == "a@b.com")
    cek("penulisan atomik: tidak ada sisa .tmp", sisa_tmp(os.path.dirname(st.lokasi_file())) == [])

    with open(st.lokasi_file(), "w") as f:
        f.write("{ ini bukan json")
    data = st.muat()
    cek("file rusak: aplikasi tidak crash, memakai nilai bawaan", data == st.BAWAAN)
    cek("file rusak: salinannya disimpan sebagai .rusak", os.path.exists(st.lokasi_file() + ".rusak"))

    with open(st.lokasi_file(), "w") as f:
        f.write('{"jendela_lebar": "besar", "jendela_tinggi": 800, "kunci_asing": 1}')
    data = st.muat()
    cek("tipe salah di file diabaikan, nilai valid tetap dipakai",
        data["jendela_lebar"] == st.BAWAAN["jendela_lebar"] and data["jendela_tinggi"] == 800)
    cek("kunci asing di file tidak ikut dimuat", "kunci_asing" not in data)

    hasil = []
    def tulis_bersamaan(i):
        hasil.append(st.atur_banyak(jendela_lebar=800 + i, jendela_tinggi=600 + i))
    ts = [threading.Thread(target=tulis_bersamaan, args=(i,)) for i in range(12)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    st._data = None
    data = st.muat()
    cek("12 thread menyimpan bersamaan: semua berhasil", all(hasil))
    cek("12 thread menyimpan bersamaan: berkas tetap JSON utuh & konsisten",
        data["jendela_lebar"] - 800 == data["jendela_tinggi"] - 600 and not os.path.exists(st.lokasi_file() + ".rusak.2"))
    cek("tidak ada sisa .tmp setelah penulisan bersamaan", sisa_tmp(os.path.dirname(st.lokasi_file())) == [])
    cek("reset() mengembalikan nilai bawaan", st.reset() and st.ambil("jendela_lebar") == st.BAWAAN["jendela_lebar"])


# ============================================================= 3. disk_cache
def uji_disk_cache():
    print("\n3. disk_cache — cache di disk")
    c = disk_cache
    c.kosongkan()
    dibuat = []

    def pembuat(path):
        dibuat.append(path)
        with open(path, "wb") as f:
            f.write(b"x" * 1000)

    k = c.buat_kunci("a.png", 123, 300, 200)
    cek("kunci sama untuk masukan sama", k == c.buat_kunci("a.png", 123, 300, 200))
    cek("kunci berubah kalau mtime berubah (file diganti -> cache lama tak terpakai)", k != c.buat_kunci("a.png", 124, 300, 200))
    cek("cache miss: ambil() -> None", c.ambil(k) is None)
    p1 = c.buat_jika_perlu(k, pembuat)
    p2 = c.buat_jika_perlu(k, pembuat)
    cek("cache hit: pembuat hanya dipanggil SEKALI", p1 == p2 and len(dibuat) == 1)
    cek("pembuat yang error -> None, tidak crash", c.buat_jika_perlu("gagal", lambda p: 1 / 0) is None)
    cek("pembuat yang tidak menulis apa pun -> None", c.buat_jika_perlu("kosong", lambda p: None) is None)
    cek("tidak ada sisa .tmp setelah pembuatan gagal", sisa_tmp(c.folder()) == [])

    hasil = []
    ts = [threading.Thread(target=lambda: hasil.append(c.buat_jika_perlu("balapan", pembuat))) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    cek("10 thread berebut kunci sama: semua dapat berkas yang sama & utuh",
        len(set(hasil)) == 1 and None not in hasil and os.path.getsize(hasil[0]) == 1000)
    cek("balapan: tidak ada sisa .tmp", sisa_tmp(c.folder()) == [])

    c.kosongkan()
    sekarang = time.time()
    for i in range(10):
        path = c.buat_jika_perlu(f"k{i}", pembuat)
        os.utime(path, (sekarang - 1000 + i, sekarang - 1000 + i))      # k0 paling lama dipakai, k9 paling baru
    dipakai = c.ambil("k0")                                              # k0 dipakai lagi -> jadi yang terbaru
    dihapus = c.bersihkan(maks_mb=3000 / 1048576)                       # batas 3000 byte = 3 berkas
    jumlah, total = c.statistik()
    cek("batas ukuran: cache dipangkas sampai <= batas", total <= 3000 and jumlah == 3 and dihapus == 7)
    cek("LRU: berkas yang baru dipakai (k0) tetap dipertahankan", c.ambil("k0") is not None and dipakai is not None)
    cek("LRU: berkas yang lama tak dipakai (k1) dibuang", c.ambil("k1") is None)

    tua = c.lokasi("tua")
    tulis(tua, b"x")
    lama = time.time() - 40 * 86400
    os.utime(tua, (lama, lama))
    c.bersihkan()
    cek("batas umur: cache > 30 hari dibuang", not os.path.exists(tua))
    cek("kosongkan() menghapus semua", c.kosongkan() >= 1 and c.statistik() == (0, 0))


# ============================================================== 4. enkripsi
def uji_enkripsi():
    print("\n4. enkripsi — data sensitif")
    e = enkripsi
    e.gunakan_kunci(None)
    rahasia = "0812-3456-7890"
    token = e.enkripsi_teks(rahasia)
    cek("teks terenkripsi berawalan enc1$ & tidak memuat teks asli", token.startswith("enc1$") and rahasia not in token)
    cek("dekripsi mengembalikan teks asli", e.dekripsi_teks(token) == rahasia)
    cek("teks sama dienkripsi dua kali -> hasil BERBEDA (nonce acak)", e.enkripsi_teks(rahasia) != token)
    cek("teks Unicode/emoji aman", e.dekripsi_teks(e.enkripsi_teks("Kontak: Budi — 😀")) == "Kontak: Budi — 😀")
    cek("teks kosong dibiarkan kosong", e.enkripsi_teks("") == "")
    cek("tidak dienkripsi dua kali", e.enkripsi_teks(token) == token)
    cek("data lama (teks biasa) tetap terbaca", e.dekripsi_teks("081234 lama") == "081234 lama")

    ok = True
    for n in (0, 1, 31, 32, 33, 1024 * 1024, 2 * 1024 * 1024 + 5):
        data = os.urandom(n)
        ok = ok and e.dekripsi_bytes(e.enkripsi_bytes(data)) == data
    cek("roundtrip bytes pada batas blok (0, 1, 31, 32, 33 byte, 1 MB, 2 MB+5)", ok)

    mentah = bytearray(e.enkripsi_bytes(b"data rahasia"))
    mentah[25] ^= 1
    try:
        e.dekripsi_bytes(bytes(mentah))
        ditolak = False
    except e.DataRusak:
        ditolak = True
    cek("1 bit diubah -> dekripsi DITOLAK (bukan menghasilkan sampah)", ditolak)
    try:
        e.dekripsi_bytes(e.enkripsi_bytes(b"x", b"A" * 32), b"B" * 32)
        ditolak = False
    except e.DataRusak:
        ditolak = True
    cek("kunci salah -> dekripsi DITOLAK", ditolak)
    try:
        e.dekripsi_bytes(b"sampah" * 20)
        ditolak = False
    except e.DataRusak:
        ditolak = True
    cek("format tak dikenal -> DataRusak (bukan crash lain)", ditolak)

    cek("berkas kunci 32 byte & dibuat otomatis", os.path.getsize(e.lokasi_kunci()) == 32)
    if sys.platform != "win32":
        cek("berkas kunci hanya bisa dibaca pemilik (izin 600)", oct(os.stat(e.lokasi_kunci()).st_mode & 0o777) == "0o600")
    e.gunakan_kunci(None)
    cek("kunci dibaca ulang dari berkas: data lama tetap terbuka", e.dekripsi_teks(token) == rahasia)

    asal = tulis(os.path.join(TEMP, "enk", "besar.bin"), os.urandom(3 * 1024 * 1024 + 7))
    enc, hasil = asal + ".enc", asal + ".hasil"
    e.enkripsi_berkas(asal, enc)
    cek("berkas terenkripsi = ukuran asli + 52 byte (kepala 20 + tag 32)", os.path.getsize(enc) == os.path.getsize(asal) + 52)
    cek("isi berkas terenkripsi tidak mengandung data asli", open(asal, "rb").read()[:64] not in open(enc, "rb").read())
    e.dekripsi_berkas(enc, hasil)
    cek("dekripsi berkas 3 MB: isi identik", open(hasil, "rb").read() == open(asal, "rb").read())

    rusak = bytearray(open(enc, "rb").read())
    rusak[1_500_000] ^= 1
    tulis(enc + ".rusak", bytes(rusak))
    keluaran = os.path.join(TEMP, "enk", "keluaran.bin")
    try:
        e.dekripsi_berkas(enc + ".rusak", keluaran)
        ditolak = False
    except e.DataRusak:
        ditolak = True
    cek("berkas diubah 1 bit -> ditolak", ditolak)
    cek("berkas ditolak: tidak ada keluaran & tidak ada sisa .tmp (isi belum terverifikasi tak pernah jadi berkas)",
        not os.path.exists(keluaran) and sisa_tmp(os.path.dirname(keluaran)) == [])

    # Regresi bug yang ditemukan saat integrasi: dua penulis ke tujuan yang sama (klik ganda "Kirim")
    tujuan = os.path.join(TEMP, "enk", "kembar.enc")
    galat = []
    def enkripsi_lagi():
        try:
            e.enkripsi_berkas(asal, tujuan)
        except Exception as ex:
            galat.append(ex)
    ts = [threading.Thread(target=enkripsi_lagi) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    cek("4 thread mengenkripsi ke tujuan yang sama: tidak ada yang error (.tmp unik)", galat == [])
    kembar = os.path.join(TEMP, "enk", "kembar.hasil")
    e.dekripsi_berkas(tujuan, kembar)
    cek("hasil balapan tetap utuh & bisa dibuka", open(kembar, "rb").read() == open(asal, "rb").read())


# ========================================================= 5. integrasi DB
def uji_database():
    print("\n5. Integrasi database — kontak terenkripsi")
    import sqlite3
    from database import db, repository, sandi
    db.gunakan_database(os.path.join(TEMP, "uji.db"))
    db.init_db()
    enkripsi.gunakan_kunci(None)

    repository.simpan_user_baru({"nama": "Uji FS", "email": "fs@teamup.com", "password": sandi.hash_password("x12345678"),
                                 "username": "uji_fs"})
    data = {"judul": "Lomba Uji", "kategori": "Mahasiswa", "penyelenggara": "UNY", "deskripsi": "d",
            "link": "https://x.id", "kontak": "081234567824", "poster": "p.pdf", "dokumen": "d.pdf.enc"}
    post_id = repository.tambah_postingan("fs@teamup.com", data)

    def kolom_mentah(id_):
        with sqlite3.connect(db.DB_PATH) as c:
            return c.execute("SELECT kontak FROM postingan WHERE id = ?", (id_,)).fetchone()[0]

    mentah = kolom_mentah(post_id)
    cek("di database: kontak tersimpan terenkripsi (enc1$...)", mentah.startswith("enc1$"))
    cek("di database: nomor telepon asli TIDAK terlihat", "081234567824" not in mentah)
    cek("di aplikasi: kontak terbaca normal lewat muat_postingan()",
        next(p for p in repository.muat_postingan() if p["id"] == post_id)["kontak"] == "081234567824")

    with db.koneksi() as c:
        c.execute("UPDATE postingan SET status = 'Revisi' WHERE id = ?", (post_id,))
    repository.perbarui_postingan(post_id, {"kontak": "089999000111"}, "fs@teamup.com")
    cek("perbarui_postingan: kontak baru juga terenkripsi", kolom_mentah(post_id).startswith("enc1$"))
    cek("perbarui_postingan: kontak baru terbaca normal",
        next(p for p in repository.muat_postingan() if p["id"] == post_id)["kontak"] == "089999000111")

    with db.koneksi() as c:
        c.execute("UPDATE postingan SET kontak = '085500001111' WHERE id = ?", (post_id,))   # meniru data lama (teks biasa)
    cek("data lama (teks biasa) tetap terbaca sebelum migrasi",
        next(p for p in repository.muat_postingan() if p["id"] == post_id)["kontak"] == "085500001111")
    cek("amankan_kontak_lama(): mengenkripsi data lama", repository.amankan_kontak_lama() == 1 and kolom_mentah(post_id).startswith("enc1$"))
    cek("amankan_kontak_lama(): idempoten (dipanggil lagi -> 0)", repository.amankan_kontak_lama() == 0)
    cek("setelah migrasi: nilai tetap benar",
        next(p for p in repository.muat_postingan() if p["id"] == post_id)["kontak"] == "085500001111")

    enkripsi.gunakan_kunci(b"Z" * 32)                      # meniru kunci hilang / berganti
    try:
        kontak = next(p for p in repository.muat_postingan() if p["id"] == post_id)["kontak"]
        aman = "tidak dapat dibuka" in kontak
    except Exception:
        aman = False
    cek("kunci hilang/berganti: aplikasi TIDAK crash, tampil pesan netral", aman)
    enkripsi.gunakan_kunci(None)


# ========================================================== 6. integrasi UI
def uji_ui():
    print("\n6. Integrasi UI — foto profil & penyalinan berkas")
    import config
    import helpers
    import views.post_form_page as pf

    cek("path_foto: nama kosong -> ''", helpers.path_foto("") == "")
    cek("path_foto: foto tidak ada -> ''", helpers.path_foto("tidak_ada_sama_sekali.png") == "")
    bawaan = [n for n in os.listdir(os.path.join(config.ASSETS_DIR, "foto"))
              if n.lower().endswith((".png", ".jpg", ".jpeg"))] if os.path.isdir(os.path.join(config.ASSETS_DIR, "foto")) else []
    if bawaan:
        cek("path_foto: foto bawaan project (assets/foto) tetap ditemukan",
            helpers.path_foto(bawaan[0]) == os.path.join(config.ASSETS_DIR, "foto", bawaan[0]))
    nama = "uji_foto.png"
    tulis(file_storage.path_berkas("foto", nama), b"\x89PNG data foto user")
    cek("path_foto: foto unggahan user ditemukan di folder data aplikasi",
        helpers.path_foto(nama) == file_storage.path_berkas("foto", nama))
    cek("path_foto: foto user diutamakan daripada foto bawaan bernama sama",
        helpers.path_foto(nama).startswith(os.environ["TEAMUP_DATA"]))
    cek("lokasi_png_qml: cache poster ada di folder data aplikasi (bukan folder temp sistem)",
        helpers.lokasi_png_qml("x.png", 1, 300, 200, 12).startswith(disk_cache.folder()))

    class KontrolPalsu:
        def __init__(self, batal_setelah=None):
            self.n, self.batas, self.persen = 0, batal_setelah, []
        @property
        def dibatalkan(self):
            self.n += 1
            return self.batas is not None and self.n > self.batas
        def laporkan(self, persen):
            self.persen.append(persen)

    poster = tulis(os.path.join(TEMP, "form", "poster.pdf"), os.urandom(2 * 1024 * 1024))
    dokumen = tulis(os.path.join(TEMP, "form", "surat.pdf"), os.urandom(1024 * 1024))
    tuj_poster = file_storage.path_berkas("poster", "123_poster.pdf")
    tuj_dok = file_storage.path_berkas("dokumen", "123_surat.pdf.enc")
    kontrol = KontrolPalsu()
    hasil = pf.salin_berkas(kontrol, [(poster, tuj_poster), (dokumen, tuj_dok)])
    cek("salin_berkas: poster disalin apa adanya", open(tuj_poster, "rb").read() == open(poster, "rb").read())
    cek("salin_berkas: dokumen (.enc) terenkripsi, bukan salinan polos",
        open(tuj_dok, "rb").read(4) == enkripsi.MAGIC and open(dokumen, "rb").read()[:32] not in open(tuj_dok, "rb").read())
    buka = os.path.join(TEMP, "form", "buka.pdf")
    enkripsi.dekripsi_berkas(tuj_dok, buka)
    cek("salin_berkas: dokumen terenkripsi bisa dibuka kembali", open(buka, "rb").read() == open(dokumen, "rb").read())
    cek("salin_berkas: progres naik teratur sampai 100", kontrol.persen == sorted(kontrol.persen) and kontrol.persen[-1] == 100)
    cek("salin_berkas: mengembalikan daftar tujuan", hasil == [tuj_poster, tuj_dok])

    a = file_storage.path_berkas("poster", "batal_a.pdf")
    b = file_storage.path_berkas("dokumen", "batal_b.pdf.enc")
    cek("salin_berkas dibatalkan: mengembalikan None & berkas setengah jadi dihapus",
        pf.salin_berkas(KontrolPalsu(batal_setelah=1), [(poster, a), (dokumen, b)]) is None
        and not os.path.exists(a) and not os.path.exists(b))
    cek("nama_tampil: '1699_Proposal.pdf.enc' -> 'Proposal.pdf'", pf.nama_tampil("1699_Proposal.pdf.enc") == "Proposal.pdf")
    cek("nama_tampil: nama biasa tidak diubah", pf.nama_tampil("Proposal.pdf") == "Proposal.pdf")


def main():
    print("=== UJI OTOMATIS FILE SYSTEM & LOCAL STORAGE (Pertemuan 11) ===")
    print(f"(folder sementara: {TEMP})")
    try:
        uji_file_storage()
        uji_settings()
        uji_disk_cache()
        uji_enkripsi()
        uji_database()
        uji_ui()
    finally:
        import shutil
        shutil.rmtree(TEMP, ignore_errors=True)
    print(f"\nLULUS: {LULUS}   GAGAL: {GAGAL}")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
