# tes_keamanan.py — Uji otomatis Pertemuan 12: Security & Error Handling (validasi, akun, hak akses, error)
#
# Yang diuji (setiap bagian memuat percobaan SERANGAN, bukan hanya jalur normal):
#   1. validasi         : email, nama, username, password (16), URL https, telepon, kontak, pembersihan teks
#   2. keamanan_akun    : OTP (kedaluwarsa, 3 percobaan, sekali pakai, 40 thread menebak), pembatas login, samarkan waktu
#   3. hak_akses        : peran, izin, dan penegakannya di repository (melewati UI sama sekali)
#   4. data_store       : OTP & reset password, data per user, login, tidak ada akun hantu
#   5. halaman          : pesan di layar daftar / lupa password / login (terkunci) / profil / password baru
#   6. error & log      : pesan ke user tanpa detail teknis, log tanpa data sensitif
#
# TERISOLASI: folder data, database, dan jam palsu sementara; tidak menyentuh data asli maupun teamup.db.
# Cara menjalankan:  python3 tes_keamanan.py        (membuat jendela sebentar; tanpa pytest)
import os
import shutil
import sys
import tempfile
import threading
import time

TEMP = tempfile.mkdtemp(prefix="teamup_tes_aman_")
os.environ["TEAMUP_DATA"] = os.path.join(TEMP, "data")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("HMAC_SECRET_KEY", None)                # tes tidak boleh terpengaruh .env milik developer
os.environ.pop("TEAMUP_ADMIN", None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import enkripsi
enkripsi.baca_env = lambda: None

import hak_akses
import keamanan_akun
import penanganan_error
import validasi
from database import db, repository, sandi

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


def tolak(nama, fungsi, jenis=repository.HakAksesDitolak):
    try:
        fungsi()
        cek(nama, False)
    except jenis:
        cek(nama, True)
    except Exception as e:
        cek(f"{nama} (error lain: {type(e).__name__}: {e})", False)


def jam_palsu():
    waktu = [1000.0]
    keamanan_akun.gunakan_jam(lambda: waktu[0])
    return lambda detik: waktu.__setitem__(0, waktu[0] + detik)


# ============================================================= 1. validasi
def uji_validasi():
    print("\n1. validasi — input tidak dipercaya")
    v = validasi
    for e in ("nama@kampus.ac.id", "a.b+c@sub.domain.co", "x_y-z@mail.com"):
        cek(f"email valid: {e}", v.periksa_email(e) == "")
    for e in ("", "@.", "a@b.", "a@b", "a b@c.com", "a..b@c.com", ".a@c.com", "a@-.com", "a@b..com", "a@b.c",
              "x" * 65 + "@c.com", "<s>@b.com", "a@b.com>", "a@b.com\n"):
        cek(f"email ditolak: {e[:22]!r}", v.periksa_email(e) != "")
    cek("normalisasi email: huruf kecil & spasi dibuang", v.normalisasi_email(" Budi@Gmail.COM ") == "budi@gmail.com")

    for n in ("Budi Santoso", "Nur Aini, S.Kom.", "O'Brien-Lee", "José Álvarez"):
        cek(f"nama valid: {n}", v.periksa_nama(n) == "")
    for n in ("", "A", "Budi123", "<script>alert(1)</script>", "Budi; DROP TABLE users", "😀😀", "x" * 61):
        cek(f"nama ditolak: {n[:24]!r}", v.periksa_nama(n) != "")

    for u in ("AGBell", "budi_01", "a.b.c"):
        cek(f"username valid: {u}", v.periksa_username(u) == "")
    for u in ("ab", "bu di", "budi!", ".budi", "a..b", "x" * 21, "Admin", "TEAMUP", "' OR 1=1 --"):
        cek(f"username ditolak: {u!r}", v.periksa_username(u) != "")

    cek("password kuat 16+ (besar, kecil, angka, simbol) diterima", v.periksa_password("Rahasia-Super-Panjang-2026") == "")
    for nama, pw in (("kurang dari 16 karakter", "Rahasia-2026!"), ("tanpa huruf besar", "rahasia-super-panjang-2026"),
                     ("tanpa huruf kecil", "RAHASIA-SUPER-PANJANG-2026"), ("tanpa angka", "Rahasia-Super-Panjang-Aman"),
                     ("tanpa simbol", "RahasiaSuperPanjang2026"), ("lebih dari 128 karakter", "Aa1!" * 33)):
        cek(f"password ditolak: {nama}", v.periksa_password(pw) != "")
    cek("password memuat nama email sendiri ditolak", v.periksa_password("Budi.Santoso-Aman-2026!", "budi.santoso@x.com") != "")
    cek("spasi di password tidak dibuang (dipakai apa adanya)", v.periksa_password("Rahasia Super Panjang 2026!") == "")
    cek("kekuatan password: kuat vs lemah", v.kekuatan_password("Rahasia-Super-Panjang-2026!")[0] == 4 and v.kekuatan_password("abc")[0] == 0)
    cek("aturan password di helpers = aturan di validasi (satu sumber)",
        __import__("helpers").is_valid_password("Rahasia-Super-Panjang-2026") is True
        and __import__("helpers").is_valid_password("pendek1A!") is False)

    cek("URL https valid diterima", v.periksa_url("https://kampus.ac.id/lomba?id=1#daftar") == "")
    cek("URL http DITOLAK (revisi dosen: https saja)", v.periksa_url("http://kampus.ac.id") != "")
    cek("URL http boleh bila wajib_https=False", v.periksa_url("http://kampus.ac.id", wajib_https=False) == "")
    for u in ("javascript:alert(1)", "jAvAsCrIpT:alert(1)", "file:///etc/passwd", "data:text/html,<b>x</b>", "ftp://x.com/a",
              "//kampus.ac.id", "kampus.ac.id", "https://", "https://a", "https://a b.com", "https://user:pw@x.com",
              "https://x.com:99999", "https://-.com", "https://x.com/\x00", "https://" + "a" * 2100 + ".com"):
        cek(f"URL ditolak: {u[:30]!r}", v.periksa_url(u, wajib_https=False) != "" or v.periksa_url(u) != "")
    cek("skema berbahaya ditolak walau wajib_https dimatikan", v.periksa_url("javascript:alert(1)", wajib_https=False) != ""
        and v.periksa_url("file:///etc/passwd", wajib_https=False) != "")

    for t in ("081234567824", "0812-3456-7824", "+62 812 3456 7824", "628123456789"):
        cek(f"telepon valid: {t}", v.periksa_telepon(t) == "")
    for t in ("", "abc", "123", "81234567890", "0812345", "0812-abc-7824"):
        cek(f"telepon ditolak: {t!r}", v.periksa_telepon(t) != "")
    cek("kontak: email atau telepon valid, teks bebas ditolak",
        v.periksa_kontak("panitia@kampus.ac.id") == "" and v.periksa_kontak("081234567824") == ""
        and v.periksa_kontak("hubungi saya") != "" and v.periksa_kontak("") != "")
    cek("OTP: hanya 4 digit angka ASCII", v.periksa_otp("1234") == "" and v.periksa_otp("12a4") != ""
        and v.periksa_otp("123") != "" and v.periksa_otp("١٢٣٤") != "")

    cek("bersihkan_teks: spasi dipadatkan", v.bersihkan_teks("  Budi   \t Santoso \n") == "Budi Santoso")
    cek("bersihkan_teks: karakter tak terlihat & NUL dibuang", v.bersihkan_teks("Bu\u200bdi\x00") == "Budi")
    cek("bersihkan_teks: baris baru dipertahankan untuk deskripsi", v.bersihkan_teks("a\n\n\n\nb", satu_baris=False) == "a\n\nb")
    cek("teks bio dengan < atau > ditolak", v.periksa_teks("halo <b>", "Bio", "bio") != "")
    cek("deskripsi terlalu pendek / panjang ditolak", v.periksa_teks("pendek", "Deskripsi", "deskripsi") != ""
        and v.periksa_teks("x" * 3001, "Deskripsi", "deskripsi") != "")


# ============================================================= 2. keamanan_akun
def uji_keamanan_akun():
    print("\n2. keamanan_akun — OTP & pembatas login")
    k = keamanan_akun
    maju = jam_palsu()
    k.atur_ulang()

    kode, pesan = k.buat_otp("Budi@X.com")
    cek("OTP: 4 digit angka", kode and len(kode) == 4 and kode.isdigit() and pesan == "")
    cek("OTP: hanya HASH yang tersimpan, kode asli tidak ada di memori", kode.encode() not in repr(k._otp).encode())
    cek("OTP benar lolos (email beda huruf besar/spasi)", k.periksa_otp(" budi@x.com", kode) == (True, ""))
    cek("izin ganti password terbuka setelah OTP benar", k.izin_reset_password("BUDI@x.com"))
    cek("OTP sekali pakai: kode yang sama ditolak lagi", k.periksa_otp("budi@x.com", kode)[0] is False)
    k.selesai_reset("budi@x.com")
    cek("izin ganti password sekali pakai", not k.izin_reset_password("budi@x.com"))

    k.atur_ulang()
    kode, _ = k.buat_otp("a@b.com")
    salah = "0000" if kode != "0000" else "1111"
    r1, r2 = k.periksa_otp("a@b.com", salah), k.periksa_otp("a@b.com", salah)
    cek("OTP salah: sisa percobaan dilaporkan (2, lalu 1)", "Sisa percobaan: 2" in r1[1] and "Sisa percobaan: 1" in r2[1])
    r3 = k.periksa_otp("a@b.com", salah)
    cek("OTP salah 3x: kode HANGUS", r3[0] is False and "dibatalkan" in r3[1])
    cek("setelah hangus, kode BENAR pun ditolak (brute force 0000-9999 tidak mungkin)", k.periksa_otp("a@b.com", kode)[0] is False)

    k.atur_ulang()
    kode, _ = k.buat_otp("c@d.com")
    maju(301)
    r = k.periksa_otp("c@d.com", kode)
    cek("OTP kedaluwarsa setelah 5 menit", r[0] is False and "kedaluwarsa" in r[1])
    cek("OTP yang belum pernah diminta ditolak", k.periksa_otp("tidak@ada.com", "1234")[0] is False)

    k.atur_ulang()
    k.buat_otp("e@f.com")
    cek("minta kode ulang terlalu cepat ditolak (jeda 30 detik)", k.buat_otp("e@f.com")[0] is None and 0 < k.sisa_jeda_kirim("e@f.com") <= 30)
    maju(31)
    cek("setelah jeda boleh minta lagi", k.buat_otp("e@f.com")[0] is not None)
    k.atur_ulang()
    for _ in range(5):
        assert k.buat_otp("g@h.com")[0] is not None
        maju(31)
    cek("maksimal 5 permintaan per 15 menit", k.buat_otp("g@h.com")[0] is None)
    maju(900)
    cek("jendela 15 menit berlalu: boleh lagi", k.buat_otp("g@h.com")[0] is not None)

    k.atur_ulang()
    kode, _ = k.buat_otp("izin@x.com")
    k.periksa_otp("izin@x.com", kode)
    maju(601)
    cek("izin ganti password kedaluwarsa setelah 10 menit", not k.izin_reset_password("izin@x.com"))

    k.atur_ulang()
    kode, _ = k.buat_otp("race@x.com")
    salah = "0000" if kode != "0000" else "1111"
    hasil = []
    ts = [threading.Thread(target=lambda: hasil.append(k.periksa_otp("race@x.com", salah))) for _ in range(40)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    cek("40 thread menebak serentak: hanya 3 percobaan yang dihitung",
        sum(1 for h in hasil if "Sisa percobaan" in h[1] or "dibatalkan" in h[1]) == 3)

    k.atur_ulang()
    cek("login: awalnya boleh", k.cek_boleh_login("a@b.com") == (True, 0))
    hasil = [k.catat_gagal("a@b.com") for _ in range(4)]
    cek("login: 4 gagal -> belum terkunci, sisa percobaan 4,3,2,1", [h[1] for h in hasil] == [4, 3, 2, 1])
    cek("login: gagal ke-5 -> terkunci 30 detik (email tak peka huruf besar)", k.catat_gagal("A@B.com") == (True, 0, 30))
    cek("login: saat terkunci tidak boleh mencoba", k.cek_boleh_login("a@b.com")[0] is False)
    maju(31)
    for _ in range(4):
        k.catat_gagal("a@b.com")
    cek("kunci kedua berlipat: 60 detik", k.catat_gagal("a@b.com") == (True, 0, 60))
    maju(61)
    for _ in range(5):
        h = k.catat_gagal("a@b.com")
    cek("kunci ketiga: 120 detik", h[2] == 120)
    for _ in range(10):
        maju(k.cek_boleh_login("a@b.com")[1] + 1)
        for _ in range(5):
            h = k.catat_gagal("a@b.com")
    cek("kunci dibatasi maksimal 15 menit", h[2] == 900)
    k.catat_berhasil("a@b.com")
    cek("login berhasil menghapus catatan gagal", k.cek_boleh_login("a@b.com") == (True, 0))
    k.atur_ulang()
    for _ in range(5):
        k.catat_gagal("x@y.com")
    cek("email lain tidak ikut terkunci", k.cek_boleh_login("lain@y.com") == (True, 0))
    cek("email tidak terdaftar dihitung sama (tidak bisa dibedakan penyerang)", k.cek_boleh_login("x@y.com")[0] is False)
    k.atur_ulang()
    for i in range(1500):
        k.catat_gagal(f"e{i}@x.com")
        maju(0.01)
    cek("memori pembatas dibatasi (penyerang tak bisa menghabiskan RAM dengan ribuan email)", len(k._login) <= k.MAKS_AKUN_DICATAT)

    k.gunakan_jam(time.monotonic)
    asli = sandi.hash_password("Rahasia123")
    def ukur(f, n=5):
        mulai = time.perf_counter()
        for _ in range(n):
            f()
        return (time.perf_counter() - mulai) / n
    k.samakan_waktu("x")
    t_terdaftar = ukur(lambda: sandi.cocok(asli, "salah123"))
    t_palsu = ukur(lambda: k.samakan_waktu("salah123"))
    cek(f"samakan_waktu: email tak terdaftar memakan waktu setara ({t_palsu * 1000:.0f} ms vs {t_terdaftar * 1000:.0f} ms)",
        0.4 < t_palsu / t_terdaftar < 2.5)
    k.atur_ulang()


# ============================================================= 3. hak akses + repository
def uji_hak_akses():
    print("\n3. hak_akses — izin ditegakkan di lapisan data (tanpa lewat UI)")
    h = hak_akses
    h.gunakan_admin(None)
    cek("tanpa konfigurasi: TIDAK ada admin (aman secara bawaan)", not h.adalah_admin("admin@teamup.com"))
    os.environ["TEAMUP_ADMIN"] = " Admin@Kampus.ac.id , lain@x.com "
    cek("admin dari TEAMUP_ADMIN (tak peka huruf besar/spasi)", h.adalah_admin("admin@kampus.ac.id") and h.adalah_admin("LAIN@x.com"))
    os.environ.pop("TEAMUP_ADMIN")
    h.gunakan_admin(["admin@teamup.com"])
    cek("peran: tamu / pengguna / admin", h.peran("") == "tamu" and h.peran("a@b.com") == "pengguna" and h.peran("ADMIN@teamup.com") == "admin")
    cek("email kosong tidak pernah dianggap pemilik", not h.sama_orang("", "") and not h.sama_orang(None, None))
    cek("ubah postingan: pemilik + status Revisi", h.boleh_ubah_postingan("a@b.com", "A@B.com", "Revisi")[0])
    for st in ("Ditangguhkan", "Disetujui", "Ditolak"):
        cek(f"ubah postingan ditolak saat status {st}", not h.boleh_ubah_postingan("a@b.com", "a@b.com", st)[0])
    cek("admin BUKAN pemilik tetap tidak boleh mengubah (least privilege)", not h.boleh_ubah_postingan("admin@teamup.com", "a@b.com", "Revisi")[0])
    cek("putuskan status: hanya admin", h.boleh_putuskan_postingan("admin@teamup.com")[0]
        and not h.boleh_putuskan_postingan("a@b.com")[0] and not h.boleh_putuskan_postingan(None)[0])

    tmp = os.path.join(TEMP, "uji_repo.db")
    db.gunakan_database(tmp)
    db.init_db()
    for e in ("a@teamup.com", "b@teamup.com", "admin@teamup.com"):
        repository.simpan_user_baru({"nama": e, "email": e, "password": sandi.hash_password("x12345678")})
    data = {"judul": "Lomba Uji", "kategori": "Mahasiswa", "penyelenggara": "UNY", "deskripsi": "d", "link": "https://x.id", "kontak": "0812"}
    pid = repository.tambah_postingan("a@teamup.com", data)
    status = lambda: next(p for p in repository.muat_postingan() if p["id"] == pid)["status"]

    tolak("ubah TANPA menyebut pelaku: ditolak (dulu lolos)", lambda: repository.perbarui_postingan(pid, {"judul": "Dibajak"}))
    tolak("hapus TANPA menyebut pelaku: ditolak (dulu lolos)", lambda: repository.hapus_postingan(pid))
    tolak("hapus oleh orang lain: ditolak", lambda: repository.hapus_postingan(pid, "b@teamup.com"))
    tolak("setujui sendiri tanpa 'oleh': ditolak (dulu lolos)", lambda: repository.putuskan_postingan(pid, "Disetujui"))
    tolak("setujui oleh pemilik (bukan admin): ditolak", lambda: repository.putuskan_postingan(pid, "Disetujui", oleh="a@teamup.com"))
    tolak("setujui oleh pengguna lain: ditolak", lambda: repository.putuskan_postingan(pid, "Disetujui", oleh="b@teamup.com"))
    tolak("status ngawur oleh admin: ditolak", lambda: repository.putuskan_postingan(pid, "SuperDisetujui", oleh="admin@teamup.com"), repository.DataTidakValid)
    tolak("status berisi SQL injection: ditolak", lambda: repository.putuskan_postingan(pid, "Disetujui'; DROP TABLE postingan;--", oleh="admin@teamup.com"), repository.DataTidakValid)
    cek("status tetap Ditangguhkan setelah semua percobaan", status() == "Ditangguhkan")
    tolak("pemilik sendiri mengubah saat Ditangguhkan: ditolak (sesuai flowchart)", lambda: repository.perbarui_postingan(pid, {"judul": "x"}, "a@teamup.com"), repository.AturanBisnis)
    repository.putuskan_postingan(pid, "Revisi", "perbaiki", "catatan", "link", oleh="ADMIN@teamup.com")
    cek("admin (huruf besar) berhasil memutuskan Revisi", status() == "Revisi")
    tolak("pengguna lain mengubah postingan Revisi: ditolak", lambda: repository.perbarui_postingan(pid, {"judul": "Dibajak"}, "b@teamup.com"))
    tolak("admin mengubah postingan orang lain: ditolak", lambda: repository.perbarui_postingan(pid, {"judul": "Dibajak"}, "admin@teamup.com"))
    repository.perbarui_postingan(pid, {"judul": "Judul Baru"}, "A@teamup.com")
    cek("pemilik (email beda huruf) berhasil memperbarui", status() == "Ditangguhkan")
    cek("pemilik berhasil menghapus pengajuannya", repository.hapus_postingan(pid, "a@teamup.com") is True)

    nid_a = repository.buat_notifikasi("a@teamup.com", "partner", "Tertarik!")
    nid_b = repository.buat_notifikasi("b@teamup.com", "partner", "Tertarik B!")
    dibaca = lambda email, nid: next(n for n in repository.muat_notifikasi(email_pemilik=email) if n["id"] == nid)["dibaca"]
    tolak("tandai notifikasi orang lain (IDOR): ditolak", lambda: repository.tandai_dibaca(nid_b, "a@teamup.com"))
    tolak("tandai TANPA identitas: ditolak", lambda: repository.tandai_dibaca(nid_a))
    tolak("admin menandai notifikasi orang lain: ditolak", lambda: repository.tandai_dibaca(nid_a, "admin@teamup.com"))
    cek("notifikasi B tidak berubah", dibaca("b@teamup.com", nid_b) is False)
    pesan = []
    for nid in (nid_b, 99999):
        try:
            repository.tandai_dibaca(nid, "a@teamup.com")
        except repository.HakAksesDitolak as e:
            pesan.append(str(e))
    cek("id milik orang lain dan id yang tidak ada dijawab SAMA (id tidak bisa ditebak)", len(pesan) == 2 and pesan[0] == pesan[1])
    repository.tandai_dibaca(nid_a, "a@teamup.com")
    cek("pemilik berhasil menandai dibaca", dibaca("a@teamup.com", nid_a) is True)
    tolak("hapus notifikasi TANPA identitas: ditolak (dulu menghapus siapa pun)", lambda: repository.hapus_notifikasi(nid_b))
    tolak("hapus notifikasi orang lain: ditolak", lambda: repository.hapus_notifikasi(nid_b, "a@teamup.com"))
    repository.hapus_notifikasi(nid_b, "b@teamup.com")
    cek("pemilik berhasil menghapus notifikasinya", not any(n["id"] == nid_b for n in repository.muat_notifikasi(email_pemilik="b@teamup.com")))
    cek("HakAksesDitolak turunan AturanBisnis (kode lama tetap berjalan)", issubclass(repository.HakAksesDitolak, repository.AturanBisnis))


# ============================================================= 4. data_store
def uji_data_store(ds):
    print("\n4. data_store — alur akun & data per user")
    k = keamanan_akun
    maju = jam_palsu()
    k.atur_ulang()
    demo = "demo@teamup.com"

    panggilan = []
    asli = k.samakan_waktu
    k.samakan_waktu = lambda pw: (panggilan.append(1), asli(pw))[1]
    cek("find_user: email tak terdaftar -> None & waktu disamakan", ds.find_user("hantu@x.com", "apa-saja-123") is None and len(panggilan) == 1)
    cek("find_user: password salah -> None", ds.find_user(demo, "salah-salah-123") is None and len(panggilan) == 1)
    cek("find_user: password benar -> user", ds.find_user(demo, "demo1234") is not None)
    k.samakan_waktu = asli

    kode, pesan = ds.minta_otp("hantu@x.com")
    cek("minta OTP email tak terdaftar: tidak ada kode, tidak ada OTP tersimpan", kode is None and "hantu@x.com" not in k._otp)
    kode, pesan = ds.minta_otp(demo)
    cek("minta OTP email terdaftar: kode 4 digit", kode and len(kode) == 4)
    cek("data_store tidak menyimpan kode OTP di memori (otp_code kosong)", ds.otp_code == "")
    cek("minta OTP lagi terlalu cepat ditolak", ds.minta_otp(demo)[0] is None)
    salah = "0000" if kode != "0000" else "1111"
    cek("verifikasi OTP salah ditolak", ds.verifikasi_otp(salah)[0] is False)

    tolak("ganti password SEBELUM OTP benar: ditolak", lambda: ds.update_password(demo, "Sandi-Baru-Panjang-2026!"))
    tolak("ganti password untuk email lain: ditolak", lambda: ds.update_password("lain@x.com", "Sandi-Baru-Panjang-2026!"))
    cek("verifikasi OTP benar diterima", ds.verifikasi_otp(kode) == (True, ""))
    tolak("ganti password untuk email YANG BERBEDA dari yang diverifikasi: ditolak", lambda: ds.update_password("marques@teamup.com", "Sandi-Baru-Panjang-2026!"))
    ds.update_password(demo, "Sandi-Baru-Panjang-2026!")
    cek("ganti password berhasil setelah OTP benar; login dengan password baru", ds.find_user(demo, "Sandi-Baru-Panjang-2026!") is not None)
    cek("password lama tidak berlaku lagi", ds.find_user(demo, "demo1234") is None)
    tolak("izin sekali pakai: ganti password kedua kali ditolak", lambda: ds.update_password(demo, "Sandi-Lain-Panjang-2026!"))

    for _ in range(5):
        k.catat_gagal(demo)
    cek("akun terkunci karena gagal berulang", k.cek_boleh_login(demo)[0] is False)
    kode, _ = (maju(31), ds.minta_otp(demo))[1]
    ds.verifikasi_otp(kode)
    ds.update_password(demo, "Sandi-Ketiga-Panjang-2026!")
    cek("reset password berhasil membuka kunci login", k.cek_boleh_login(demo) == (True, 0))

    ds.current_user = ds.find_user(demo, "Sandi-Ketiga-Panjang-2026!")
    punya_demo = repository.muat_postingan(email_pemilik=demo)
    cek("user login: melihat postingan miliknya sendiri", len(ds.get_postingan()) == len(punya_demo) > 0)
    notif_demo = [n for n in repository.muat_notifikasi(email_pemilik=demo)]
    cek("user login: melihat notifikasi miliknya sendiri", len(ds.get_notifikasi()) == len(notif_demo) > 0)
    id_demo = punya_demo[0]["id"]
    cek("jumlah per status hanya menghitung milik sendiri", ds.hitung_postingan()["Semua"] == len(punya_demo))

    ds.current_user = {"email": "orang.lain@x.com", "nama": "Orang Lain"}
    cek("user LAIN tidak melihat postingan milik demo (dulu terlihat semua)", ds.get_postingan() == [])
    cek("user lain tidak melihat notifikasi milik demo", ds.get_notifikasi() == [])
    cek("user lain tidak bisa membuka postingan demo lewat id", ds.get_postingan_by_id(id_demo) is None)
    cek("user lain tidak bisa membuka notifikasi demo lewat id", ds.get_notifikasi_by_id(notif_demo[0]["id"]) is None)
    belum = [n for n in notif_demo if not n["dibaca"]]
    if belum:
        cek("user lain tidak bisa menandai notifikasi demo dibaca (return False, data tak berubah)",
            ds.tandai_dibaca(belum[0]["id"]) is False
            and next(n for n in repository.muat_notifikasi(email_pemilik=demo) if n["id"] == belum[0]["id"])["dibaca"] is False)
    tolak("user lain membatalkan/menghapus postingan demo: ditolak", lambda: ds.hapus_postingan(id_demo))
    tolak("user lain mengirim ulang postingan demo: ditolak", lambda: ds.kirim_ulang_postingan(id_demo, {"judul": "Dibajak"}))
    cek("postingan demo tidak berubah setelah percobaan di atas", repository.muat_postingan(email_pemilik=demo)[0]["judul"] != "Dibajak")

    ds.current_user = None
    cek("belum login: tidak ada postingan / notifikasi", ds.get_postingan() == [] and ds.get_notifikasi() == [])
    awal = len(repository.muat_postingan())
    tolak("belum login: mengunggah postingan ditolak (dulu diam-diam atas nama demo)", lambda: ds.tambah_postingan({"judul": "Hantu"}))
    cek("tidak ada postingan baru tercipta", len(repository.muat_postingan()) == awal)

    jumlah = len(ds.users)
    tolak("daftar dengan email yang sudah ada: error naik ke UI", lambda: ds.add_user("Duplikat", demo, "Sandi-Kuat-Panjang-2026!"), repository.DataTidakValid)
    cek("gagal simpan: TIDAK ada akun hantu di memori (dulu tetap ditambahkan)", len(ds.users) == jumlah)
    k.atur_ulang()
    k.gunakan_jam(time.monotonic)


# ============================================================= 5. halaman
def uji_halaman(app, jendela, ds):
    from PySide6.QtWidgets import QMessageBox
    print("\n5. Halaman — pesan di layar")
    QMessageBox.information = staticmethod(lambda *a, **kw: 0)      # dialog 'Simulasi Email' bersifat modal -> jangan memblokir uji
    k = keamanan_akun
    maju = jam_palsu()
    k.atur_ulang()
    pesan = lambda halaman: halaman.message_label.text()

    def tunggu(kondisi, detik=3):
        batas = time.time() + detik
        while not kondisi() and time.time() < batas:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()

    r = jendela.register_page
    r.name_input.setText("Budi123"); r.email_input.setText("budi@kampus.ac.id")
    r.password_input.input.setText("Sandi-Kuat-Panjang-2026!"); r.confirm_input.input.setText("Sandi-Kuat-Panjang-2026!")
    r.handle_register()
    cek("daftar: nama berisi angka ditolak dengan pesan jelas", "Nama hanya boleh" in pesan(r))
    r.name_input.setText("Budi Santoso"); r.email_input.setText("a@b.")
    r.handle_register()
    cek("daftar: format email salah ditolak", "Format email tidak valid" in pesan(r))
    r.email_input.setText("budi.baru@kampus.ac.id"); r.password_input.input.setText("pendek1A!"); r.confirm_input.input.setText("pendek1A!")
    r.handle_register()
    cek("daftar: password lemah ditolak dengan aturan lengkap", "16 karakter" in pesan(r) and "simbol" in pesan(r))
    r.password_input.input.setText("Budi.Baru-Aman-2026!"); r.confirm_input.input.setText("Budi.Baru-Aman-2026!")
    r.handle_register()
    cek("daftar: password memuat nama email sendiri ditolak", "nama email" in pesan(r))

    asli_add = ds.add_user
    def add_user_rusak(*a, **kw):
        raise RuntimeError("UNIQUE constraint failed: users.email di /Users/mazaya/teamup.db")
    ds.add_user = add_user_rusak
    r.password_input.input.setText("Sandi-Kuat-Panjang-2026!"); r.confirm_input.input.setText("Sandi-Kuat-Panjang-2026!")
    r.terms_checkbox.setChecked(True)                               # syarat & ketentuan wajib dicentang
    r.message_label.setText("")
    r.handle_register()
    tunggu(lambda: pesan(r) != "")                                  # pendaftaran diproses setelah jeda spinner
    ds.add_user = asli_add
    cek("daftar: error teknis TIDAK membocorkan detail (tabel, path), memuat kode referensi",
        "UNIQUE" not in pesan(r) and "/Users" not in pesan(r) and "kode:" in pesan(r))

    f = jendela.forgot_page
    terkirim = []
    f.email_submitted.connect(terkirim.append)
    f.email_input.setText("bukan-email")
    f.handle_send()
    cek("lupa password: format email salah ditolak", "Format email tidak valid" in pesan(f) and terkirim == [])
    f.email_input.setText("Hantu.Tak.Terdaftar@Kampus.ac.id")
    f.handle_send()
    cek("lupa password: email tak terdaftar DIPERLAKUKAN SAMA (lanjut, tanpa pesan 'tidak terdaftar')",
        terkirim == ["hantu.tak.terdaftar@kampus.ac.id"] and "terdaftar" not in pesan(f))

    npg = jendela.new_password_page
    ds.reset_email = "demo@teamup.com"
    npg.password_input.input.setText("lemah"); npg.confirm_input.input.setText("lemah")
    npg.handle_update()
    cek("password baru: lemah ditolak", "16 karakter" in pesan(npg))
    npg.password_input.input.setText("Sandi-Final-Panjang-2026!"); npg.confirm_input.input.setText("Sandi-Final-Panjang-2026!")
    npg.handle_update()
    cek("password baru TANPA lolos OTP: ditolak di layar", "Sesi reset password sudah berakhir" in pesan(npg))

    lg = jendela.login_page
    lg.email_input.setText("demo@teamup.com")
    for i in range(1, 6):
        lg.password_input.input.setText("password-salah-123")
        lg.handle_login()
        tunggu(lambda: pesan(lg) != "")
        if i < 5:
            lg.message_label.setText("")
    cek("login: gagal ke-5 -> pesan akun terkunci sementara", "Terlalu banyak percobaan" in pesan(lg))
    lg.message_label.setText("")
    lg.password_input.input.setText("demo1234")
    lg.handle_login()
    cek("login: saat terkunci, password BENAR pun tidak diproses", "Terlalu banyak percobaan" in pesan(lg))
    maju(31)
    k.catat_berhasil("demo@teamup.com")
    lg.message_label.setText("")
    lg.email_input.setText("demo-tidak-ada@x.com")
    lg.password_input.input.setText("apa-saja-123")
    lg.handle_login()
    tunggu(lambda: pesan(lg) != "")
    cek("login: email tak terdaftar -> pesan sama persis dengan password salah (tidak membocorkan)",
        pesan(lg).startswith("Email atau password salah. Sisa percobaan:"))

    ds.current_user = ds.find_user("demo@teamup.com", "Sandi-Ketiga-Panjang-2026!") or ds.users[0]
    ep = jendela.dashboard_page.edit_profile_page
    ep.name_input.setText("Pengguna Demo"); ep.username_input.setText("demo user!"); ep.prodi_input.setText("Informatika")
    ep.univ_input.setText("Universitas Demo"); ep.domisili_input.setText("Yogyakarta")
    ep.handle_save()
    cek("edit profil: username berisi spasi/simbol ditolak", "Username hanya boleh" in pesan(ep))
    ep.username_input.setText("demo"); ep.bio_input.setPlainText("<script>alert(1)</script>")
    ep.handle_save()
    cek("edit profil: bio berisi tag HTML ditolak", "tanda < atau >" in pesan(ep))
    ds.current_user = None
    k.atur_ulang()
    k.gunakan_jam(time.monotonic)


# ============================================================= 6. error & log
def uji_log():
    print("\n6. Log — peristiwa keamanan tercatat, data sensitif tidak")
    penanganan_error.setup_logging()
    teks = "\n".join(penanganan_error.baca_log_terakhir(400))
    cek("percobaan login gagal tercatat sebagai peristiwa KEAMANAN", "KEAMANAN login_gagal" in teks)
    cek("akun terkunci tercatat", "KEAMANAN akun_terkunci" in teks)
    cek("akses ditolak tercatat", "KEAMANAN akses_ditolak" in teks)
    cek("reset password tercatat", "KEAMANAN password_direset" in teks)
    cek("email di log disamarkan (b***@domain)", "demo@teamup.com" not in teks and "d***@teamup.com" in teks)
    cek("password yang diketik user tidak pernah masuk log", "password-salah-123" not in teks and "Sandi-Kuat" not in teks and "demo1234" not in teks)
    cek("error teknis dicatat dengan kode & traceback, tanpa data sensitif", "RuntimeError" in teks and "UNIQUE" in teks and "/Users/mazaya" not in teks)


def main():
    print("=== UJI OTOMATIS KEAMANAN (Pertemuan 12: Security & Error Handling) ===")
    print(f"(folder sementara: {TEMP})")
    try:
        uji_validasi()
        uji_keamanan_akun()
        uji_hak_akses()
        db.gunakan_database(os.path.join(TEMP, "uji_app.db"))
        db.init_db()
        import data_store
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        import styles
        app.setStyleSheet(styles.APP_STYLE)
        from main import MainWindow
        jendela = MainWindow()
        hak_akses.gunakan_admin(["admin@teamup.com"])
        uji_data_store(data_store)
        uji_halaman(app, jendela, data_store)
        uji_log()
    finally:
        keamanan_akun.gunakan_jam(time.monotonic)
        penanganan_error.lepas_logging()
        shutil.rmtree(TEMP, ignore_errors=True)
    print(f"\nLULUS: {LULUS}   GAGAL: {GAGAL}")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
