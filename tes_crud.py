# tes_crud.py — Uji Otomatis Lengkap Operasi CRUD & Data Persistence (Pertemuan 10)
#
# Fitur:
#   1. Terisolasi: Menggunakan db.gunakan_database() dengan file temporer,
#      sehingga TIDAK mengotori atau menyentuh database utama 'teamup.db'.
#   2. Menghapus database temporer secara otomatis setelah pengujian selesai.
#   3. Menguji seluruh aturan bisnis (AturanBisnis), validasi (DataTidakValid),
#      enkripsi sandi (PBKDF2), dan integritas referensial (CASCADE).
#
# Cara menjalankan:
#   python tes_crud.py
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import hak_akses
from database import db, repository, sandi


class TestTeamUpCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Buat database temporer terisolasi khusus pengujian
        cls.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db_path = cls.temp_file.name
        cls.temp_file.close()

        # Alihkan koneksi database ke file temporer
        db.gunakan_database(cls.temp_db_path)
        db.init_db()
        hak_akses.gunakan_admin(["admin@teamup.com"])      # Pertemuan 12: hanya admin yang boleh memutuskan status

    @classmethod
    def tearDownClass(cls):
        # Bersihkan file temporer setelah semua tes selesai
        for akhiran in ("", "-wal", "-shm"):
            path = cls.temp_db_path + akhiran
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    # =========================================================================
    # 1. PENGUJIAN USER & AUTENTIKASI (CREATE, READ, HASH PASSWORD)
    # =========================================================================
    def test_01_create_user_dan_password_hash(self):
        """Membuat user baru dan memverifikasi password di-hash secara aman."""
        raw_password = "PasswordRahasia123!"
        pass_hash = sandi.hash_password(raw_password)

        self.assertTrue(sandi.sudah_di_hash(pass_hash), "Password harus berformat hash PBKDF2")
        self.assertTrue(sandi.cocok(pass_hash, raw_password), "Verifikasi password benar harus lolos")
        self.assertFalse(sandi.cocok(pass_hash, "SalahPassword"), "Verifikasi password salah harus gagal")

        user_data = {
            "nama": "Farhan Developer",
            "email": "farhan@teamup.com",
            "password": pass_hash,
            "username": "farhan_dev",
            "prodi": "Informatika",
            "universitas": "UNY",
            "keahlian": ["Backend Development", "Python"],
            "pengalaman": ["Juara 1 Web Tech 2025"]
        }
        user_id = repository.simpan_user_baru(user_data)
        self.assertIsInstance(user_id, int)
        self.assertGreater(user_id, 0)

        # Cek apakah user terbaca di database
        semua_user = repository.muat_users()
        user_db = next((u for u in semua_user if u["email"] == "farhan@teamup.com"), None)
        self.assertIsNotNone(user_db)
        self.assertEqual(user_db["nama"], "Farhan Developer")
        self.assertIn("Backend Development", user_db["keahlian"])
        self.assertIn("Juara 1 Web Tech 2025", user_db["pengalaman"])

    def test_02_rejeksi_email_duplikat(self):
        """Database harus menolak pendaftaran akun dengan email yang sudah ada (UNIQUE)."""
        pass_hash = sandi.hash_password("dummy123")
        user_duplikat = {
            "nama": "Farhan Kloning",
            "email": "farhan@teamup.com",  # Email sama dengan test 1
            "password": pass_hash,
        }
        with self.assertRaises(repository.DataTidakValid):
            repository.simpan_user_baru(user_duplikat)

    # =========================================================================
    # 2. PENGUJIAN UPDATE USER (PROFIL, KEAHLIAN N-N, PENGALAMAN 1-N)
    # =========================================================================
    def test_03_update_profil_dan_relasi(self):
        """Menguji pembaruan data profil berserta relasi Many-to-Many keahlian dalam satu transaksi."""
        perubahan = {
            "nama": "Farhan Senior Dev",
            "bio": "Fullstack developer antarmuka dan basis data",
            "keahlian": ["Fullstack", "UI/UX Designer", "DevOps"],
            "pengalaman": ["Finalis Hackathon Nasional 2026", "Ketua Lab Komputer"]
        }
        repository.perbarui_user("farhan@teamup.com", perubahan)

        semua_user = repository.muat_users()
        user = next(u for u in semua_user if u["email"] == "farhan@teamup.com")
        self.assertEqual(user["nama"], "Farhan Senior Dev")
        self.assertEqual(user["bio"], "Fullstack developer antarmuka dan basis data")
        self.assertEqual(len(user["keahlian"]), 3)
        self.assertIn("DevOps", user["keahlian"])
        self.assertEqual(len(user["pengalaman"]), 2)

    # =========================================================================
    # 3. PENGUJIAN LOMBA (READ & COUNTER DILIHAT)
    # =========================================================================
    def test_04_lomba_dan_counter_dilihat(self):
        """Membuat kompetisi baru, membaca datanya, dan menaikkan counter dilihat."""
        with db.koneksi() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO lomba (judul, penyelenggara, kategori, tenggat_pendaftaran, tim_min, tim_maks, deskripsi)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, ("Lomba Desain Nasional", "Himanika", "UI/UX", "2026-12-31", 1, 3, "Kompetisi UI/UX"))
            lomba_id = cur.lastrowid
            conn.execute("INSERT INTO lomba_jenjang (lomba_id, jenjang) VALUES (?, ?);", (lomba_id, "Mahasiswa"))
            conn.execute("INSERT INTO syarat_lomba (lomba_id, urutan, isi_syarat) VALUES (?, ?, ?);", (lomba_id, 1, "Mahasiswa aktif"))

        daftar_lomba = repository.muat_lomba()
        lomba = next((l for l in daftar_lomba if l["id"] == lomba_id), None)
        self.assertIsNotNone(lomba)
        self.assertEqual(lomba["dilihat"], 0)

        # Naikkan counter dilihat
        repository.tambah_lomba_dilihat(lomba_id)
        daftar_lomba_update = repository.muat_lomba()
        lomba_update = next(l for l in daftar_lomba_update if l["id"] == lomba_id)
        self.assertEqual(lomba_update["dilihat"], 1)

    # =========================================================================
    # 4. PENGUJIAN POSTINGAN LOMBA & WORKFLOW REVIEW ADMIN
    # =========================================================================
    def test_05_lifecycle_postingan_dan_aturan_bisnis(self):
        """Menguji alur pengajuan lomba: Buat -> Minta Revisi -> Perbaiki -> Setujui -> Tolak Hapus."""
        # 1. User membuat postingan baru
        data_post = {
            "judul": "AI Hackathon Kampus 2026",
            "kategori": "Hackathon",
            "penyelenggara": "Fakultas Teknik",
            "deskripsi": "Lomba inovasi aplikasi AI",
            "link": "https://example.com/daftar"
        }
        post_id = repository.tambah_postingan("farhan@teamup.com", data_post)
        self.assertIsInstance(post_id, int)

        post_awal = next(p for p in repository.muat_postingan() if p["id"] == post_id)
        self.assertEqual(post_awal["status"], "Ditangguhkan", "Status awal postingan harus Ditangguhkan")

        # 2. Admin meminta revisi (otomatis memicu notifikasi)
        repository.putuskan_postingan(
            post_id, status="Revisi", alasan_singkat="Link pendaftaran rusak",
            catatan_admin="Mohon perbaiki tautan pendaftaran", bagian_diperbaiki="link", oleh="admin@teamup.com"
        )
        post_revisi = next(p for p in repository.muat_postingan() if p["id"] == post_id)
        self.assertEqual(post_revisi["status"], "Revisi")
        self.assertEqual(post_revisi["bagian_diperbaiki"], "link")

        # Cek apakah notifikasi revisi terkirim ke user
        notif_user = repository.muat_notifikasi(email_pemilik="farhan@teamup.com")
        self.assertTrue(any(n["jenis"] == "revisi" and "AI Hackathon" in n["judul"] for n in notif_user))

        # 3. User mengirim ulang perbaikan (status harus kembali Ditangguhkan)
        repository.perbarui_postingan(post_id, {"link": "https://example.com/daftar-resmi"}, email_pemilik="farhan@teamup.com")
        post_perbaikan = next(p for p in repository.muat_postingan() if p["id"] == post_id)
        self.assertEqual(post_perbaikan["status"], "Ditangguhkan")
        self.assertEqual(post_perbaikan["link"], "https://example.com/daftar-resmi")

        # 4. Admin menyetujui postingan
        repository.putuskan_postingan(post_id, status="Disetujui", oleh="admin@teamup.com")
        post_setuju = next(p for p in repository.muat_postingan() if p["id"] == post_id)
        self.assertEqual(post_setuju["status"], "Disetujui")

        # 5. ATURAN BISNIS: Postingan yang sudah Disetujui TIDAK BOLEH dihapus!
        with self.assertRaises(repository.AturanBisnis):
            repository.hapus_postingan(post_id, email_pemilik="farhan@teamup.com")

        # 6. ATURAN KEAMANAN: User lain tidak boleh memperbarui postingan ini!
        user2_data = {
            "nama": "User Lain",
            "email": "user2@teamup.com",
            "password": sandi.hash_password("pass123"),
        }
        repository.simpan_user_baru(user2_data)

        with self.assertRaises(repository.AturanBisnis):
            repository.perbarui_postingan(post_id, {"judul": "Bajak Judul"}, email_pemilik="user2@teamup.com")

    # =========================================================================
    # 5. PENGUJIAN NOTIFIKASI & RIWAYAT (UPSERT)
    # =========================================================================
    def test_06_notifikasi_dan_riwayat_upsert(self):
        """Menguji pencatatan riwayat (UPSERT tanpa duplikasi) dan penandaan notifikasi selesai dibaca."""
        # Riwayat
        repository.catat_riwayat("farhan@teamup.com", 1)
        repository.catat_riwayat("farhan@teamup.com", 1)  # Catat lagi (harus ter-update, bukan duplikat)
        riwayat = repository.muat_riwayat("farhan@teamup.com")
        self.assertEqual(riwayat.count(1), 1, "Riwayat lomba tidak boleh terduplikasi (UPSERT)")

        # Notifikasi
        notif_id = repository.buat_notifikasi("farhan@teamup.com", "partner", "Tertarik bergabung tim!")
        notif_sebelum = repository.muat_notifikasi(email_pemilik="farhan@teamup.com", hanya_belum_dibaca=True)
        self.assertTrue(any(n["id"] == notif_id for n in notif_sebelum))

        # Tandai semua notifikasi sudah dibaca
        repository.tandai_semua_notifikasi_dibaca("farhan@teamup.com")
        notif_sesudah = repository.muat_notifikasi(email_pemilik="farhan@teamup.com", hanya_belum_dibaca=True)
        self.assertEqual(len(notif_sesudah), 0, "Semua notifikasi harus sudah berstatus dibaca")

    # =========================================================================
    # 6. PENGUJIAN HAPUS USER & INTEGRITAS CASCADE
    # =========================================================================
    def test_07_hapus_user_cascade(self):
        """Menghapus user dan memastikan data relasi (pengalaman, riwayat) otomatis terhapus (CASCADE)."""
        repository.hapus_user("farhan@teamup.com")
        user_cek = next((u for u in repository.muat_users() if u["email"] == "farhan@teamup.com"), None)
        self.assertIsNone(user_cek, "User harus terhapus dari tabel users")

        # Cek integritas referensial: riwayat milik user harus otomatis kosong
        riwayat_cek = repository.muat_riwayat("farhan@teamup.com")
        self.assertEqual(len(riwayat_cek), 0, "Riwayat user harus ikut terhapus via CASCADE")

    # =========================================================================
    # 7. PENGUJIAN AUDIT TRAIL & VALIDASI GANDA (CATATAN DOSEN)
    # =========================================================================
    def test_08_audit_trail_dan_validasi_ganda(self):
        """Memverifikasi atribut audit (created_at, remark) dan validasi ganda."""
        user = repository.muat_users()[0]
        self.assertTrue(user.get("created_at"), "Record user harus memiliki atribut audit created_at")
        self.assertTrue("remark" in user, "Record user harus memiliki atribut audit remark")

        # Uji validasi ganda yang sah (ID + created_at)
        hasil_sah = repository.validasi_audit_user(user["id"], user["created_at"])
        self.assertIsNotNone(hasil_sah, "Validasi ganda harus berhasil jika ID dan created_at cocok")

        # Uji validasi ganda terhadap data anomali / manipulasi (ID benar, tapi created_at palsu)
        hasil_palsu = repository.validasi_audit_user(user["id"], "2000-01-01 00:00:00")
        self.assertIsNone(hasil_palsu, "Validasi ganda harus menolak record yang tidak sinkron dengan waktu audit")


def jalankan_demo():
    print("\n" + "=" * 65)
    print("      UJI OTOMATIS CRUD & PERSISTENSI BASIS DATA (SQLITE)      ")
    print("                   APLIKASI TEAMUP - PERTEMUAN 10              ")
    print("=" * 65)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTeamUpCRUD)
    runner = unittest.TextTestRunner(verbosity=2)
    hasil = runner.run(suite)
    print("=" * 65)
    if hasil.wasSuccessful():
        print("HASIL: SEMUA TES CRUD BERHASIL LULUS 100%! (SIAP PRESENTASI)")
    else:
        print("HASIL: ADA PENGUJIAN YANG GAGAL.")
    print("=" * 65 + "\n")
    return 0 if hasil.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(jalankan_demo())
