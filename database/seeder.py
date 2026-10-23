# database/seeder.py — Migrasi Data Awal (Mock Data -> SQLite)
# Mengambil data awal dari data_store.py dan menyimpannya ke file database teamup.db
import sys
import os

# Tambahkan root directory ke sys.path agar bisa mengimpor modul proyek
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import data_store
from database.db import get_connection, init_db


def seed_database():
    """Mengisi database dengan data awal jika tabel masih kosong."""
    init_db()

    with get_connection() as conn:
        cursor = conn.cursor()

        # ---------------------------------------------------------
        # 1. SEED USERS & KEAHLIAN & PENGALAMAN
        # ---------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data users...")
            for u in data_store.users:
                cursor.execute("""
                    INSERT INTO users (nama, email, password, username, prodi, universitas, domisili, bio, instagram, foto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    u.get("nama", ""),
                    u.get("email", ""),
                    u.get("password", ""),
                    u.get("username", ""),
                    u.get("prodi", ""),
                    u.get("universitas", ""),
                    u.get("domisili", ""),
                    u.get("bio", ""),
                    u.get("instagram", ""),
                    u.get("foto", "")
                ))
                user_id = cursor.lastrowid

                # Masukkan keahlian (Many-to-Many)
                for skill_name in u.get("keahlian", []):
                    # Pastikan nama keahlian ada di master tabel keahlian
                    cursor.execute("INSERT OR IGNORE INTO keahlian (nama) VALUES (?);", (skill_name,))
                    cursor.execute("SELECT id FROM keahlian WHERE nama = ?;", (skill_name,))
                    skill_id = cursor.fetchone()[0]

                    # Hubungkan ke pivot table user_keahlian
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_keahlian (user_id, keahlian_id)
                        VALUES (?, ?);
                    """, (user_id, skill_id))

                # Masukkan pengalaman (One-to-Many)
                for exp_title in u.get("pengalaman", []):
                    cursor.execute("""
                        INSERT INTO pengalaman (user_id, judul)
                        VALUES (?, ?);
                    """, (user_id, exp_title))

        # ---------------------------------------------------------
        # 2. SEED LOMBA, SYARAT, & POSTER
        # ---------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM lomba;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data lomba...")
            for l in data_store.lomba_list:
                jenjang_str = ", ".join(l.get("jenjang", [])) if isinstance(l.get("jenjang"), list) else str(l.get("jenjang", ""))
                cursor.execute("""
                    INSERT INTO lomba (
                        id, judul, penyelenggara, kategori, sisa_hari, warna,
                        tanggal_pelaksanaan, anggota_tim, deskripsi, link,
                        diunggah_hari_lalu, dilihat, jenjang, jenis, cakupan, biaya
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    l.get("id"),
                    l.get("judul", ""),
                    l.get("penyelenggara", ""),
                    l.get("kategori", ""),
                    l.get("sisa_hari", 0),
                    l.get("warna", "#1B2A5C"),
                    l.get("tanggal_pelaksanaan", ""),
                    l.get("anggota_tim", ""),
                    l.get("deskripsi", ""),
                    l.get("link", ""),
                    l.get("diunggah_hari_lalu", 0),
                    l.get("dilihat", 0),
                    jenjang_str,
                    l.get("jenis", "Lainnya"),
                    l.get("cakupan", "Nasional"),
                    l.get("biaya", "Gratis")
                ))
                lomba_id = l.get("id")

                # Masukkan syarat-syarat lomba (One-to-Many)
                for idx, syarat in enumerate(l.get("syarat", [])):
                    cursor.execute("""
                        INSERT INTO syarat_lomba (lomba_id, urutan, isi_syarat)
                        VALUES (?, ?, ?);
                    """, (lomba_id, idx + 1, syarat))

                # Masukkan poster alternatif (One-to-Many)
                for poster_file in l.get("poster", []):
                    cursor.execute("""
                        INSERT INTO poster_lomba (lomba_id, nama_file)
                        VALUES (?, ?);
                    """, (lomba_id, poster_file))

        # ---------------------------------------------------------
        # 3. SEED POSTINGAN
        # ---------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM postingan;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data postingan...")
            for p in data_store.postingan_list:
                cursor.execute("""
                    INSERT INTO postingan (
                        id, user_id, judul, kategori, penyelenggara, deskripsi,
                        tanggal_lomba, tenggat_lomba, link, kontak, poster, dokumen,
                        status, diunggah_hari_lalu, dilihat, tersimpan, partner_tertarik,
                        alasan_singkat, catatan_admin, catatan_hari_lalu, bagian_diperbaiki
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    p.get("id"),
                    1, # Default user_id 1 (Demo User)
                    p.get("judul", ""),
                    p.get("kategori", ""),
                    p.get("penyelenggara", ""),
                    p.get("deskripsi", ""),
                    str(p.get("tanggal_lomba", "")),
                    str(p.get("tenggat_lomba", "")),
                    p.get("link", ""),
                    p.get("kontak", ""),
                    p.get("poster", ""),
                    p.get("dokumen", ""),
                    p.get("status", "Ditangguhkan"),
                    p.get("diunggah_hari_lalu", 0),
                    p.get("dilihat", 0),
                    p.get("tersimpan", 0),
                    p.get("partner_tertarik", 0),
                    p.get("alasan_singkat", ""),
                    p.get("catatan_admin", ""),
                    p.get("catatan_hari_lalu", 0),
                    p.get("bagian_diperbaiki", "")
                ))

        # ---------------------------------------------------------
        # 4. SEED NOTIFIKASI
        # ---------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM notifikasi;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data notifikasi...")
            for n in data_store.notifikasi_list:
                cursor.execute("""
                    INSERT INTO notifikasi (id, user_id, jenis, judul, nama_pengirim, email_pengirim, menit_lalu, dibaca)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    n.get("id"),
                    1, # User penerima notif (Demo User)
                    n.get("jenis", ""),
                    n.get("judul", n.get("lomba", "")),
                    n.get("nama", ""),
                    n.get("email", ""),
                    n.get("menit_lalu", 0),
                    1 if n.get("dibaca") else 0
                ))

        conn.commit()
        print("[SEED] Sukses! Database SQLite lokal 'teamup.db' telah siap dan terisi data.")


if __name__ == "__main__":
    seed_database()
