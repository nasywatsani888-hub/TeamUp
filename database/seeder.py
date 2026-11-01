# database/seeder.py — Migrasi Data Awal (Mock Data -> SQLite Versi 2)
import sys
import os
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import db, sandi


def _rentang_tim(teks):
    """'2-4 Anggota' -> (2, 4); 'Individu' -> (1, 1); '3 Anggota' -> (3, 3)."""
    if not teks or teks.lower().startswith("individu"):
        return (1, 1)
    angka = [int(x) for x in "".join(c if c.isdigit() else " " for c in teks).split()]
    if not angka:
        return (1, 1)
    return (min(angka), max(angka))


def seed_database():
    import data_store
    """Mengisi database dengan data awal jika tabel masih kosong (kompatibel skema v2)."""
    status_db = db.init_db()
    sekarang = datetime.now()

    with db.koneksi() as conn:
        cursor = conn.cursor()

        # 1. SEED USERS & KEAHLIAN & PENGALAMAN
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data users...")
            for u in data_store.users:
                # Password di-hash menggunakan PBKDF2-HMAC-SHA256 (database/sandi.py)
                pass_hash = sandi.hash_password(u.get("password", "demo1234"))
                cursor.execute("""
                    INSERT INTO users (nama, email, password, username, prodi, universitas, domisili, bio, instagram, foto, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    u.get("nama", ""),
                    u.get("email", ""),
                    pass_hash,
                    u.get("username") or None,
                    u.get("prodi", ""),
                    u.get("universitas", ""),
                    u.get("domisili", ""),
                    u.get("bio", ""),
                    u.get("instagram", ""),
                    u.get("foto", ""),
                    u.get("remark", "Akun contoh seeder")
                ))
                user_id = cursor.lastrowid

                for skill_name in u.get("keahlian", []):
                    cursor.execute("INSERT OR IGNORE INTO keahlian (nama) VALUES (?);", (skill_name,))
                    cursor.execute("SELECT id FROM keahlian WHERE nama = ?;", (skill_name,))
                    skill_id = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT OR IGNORE INTO user_keahlian (user_id, keahlian_id)
                        VALUES (?, ?);
                    """, (user_id, skill_id))

                for exp_title in u.get("pengalaman", []):
                    cursor.execute("""
                        INSERT INTO pengalaman (user_id, judul)
                        VALUES (?, ?);
                    """, (user_id, exp_title))

        # 2. SEED LOMBA, JENJANG, SYARAT, & POSTER
        cursor.execute("SELECT COUNT(*) FROM lomba;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data lomba...")
            for l in data_store.lomba_list:
                tim_min, tim_maks = _rentang_tim(l.get("anggota_tim", ""))
                sisa_hari = l.get("sisa_hari", 0)
                tenggat_iso = (sekarang.date() + timedelta(days=sisa_hari)).isoformat()
                diunggah_iso = (sekarang - timedelta(days=l.get("diunggah_hari_lalu", 0))).strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO lomba (
                        id, judul, penyelenggara, kategori, warna,
                        tanggal_pelaksanaan, tenggat_pendaftaran, tim_min, tim_maks,
                        deskripsi, link, diunggah_pada, dilihat, jenis, cakupan, biaya, remark
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    l.get("id"),
                    l.get("judul", ""),
                    l.get("penyelenggara", ""),
                    l.get("kategori", ""),
                    l.get("warna", "#1B2A5E"),
                    l.get("tanggal_pelaksanaan", ""),
                    tenggat_iso,
                    tim_min,
                    tim_maks,
                    l.get("deskripsi", ""),
                    l.get("link", ""),
                    diunggah_iso,
                    l.get("dilihat", 0),
                    l.get("jenis", "Lainnya"),
                    l.get("cakupan", "Nasional"),
                    l.get("biaya", "Gratis"),
                    l.get("remark", "Lomba contoh seeder")
                ))
                lomba_id = l.get("id")

                # Masukkan jenjang (1NF)
                jenjang_list = l.get("jenjang", [])
                if isinstance(jenjang_list, str):
                    jenjang_list = [j.strip() for j in jenjang_list.split(",") if j.strip()]
                for j in jenjang_list:
                    if j in ('SMA/SMK/Sederajat', 'Mahasiswa'):
                        cursor.execute("INSERT OR IGNORE INTO lomba_jenjang (lomba_id, jenjang) VALUES (?, ?);", (lomba_id, j))

                # Masukkan syarat lomba
                for idx, syarat in enumerate(l.get("syarat", [])):
                    cursor.execute("""
                        INSERT INTO syarat_lomba (lomba_id, urutan, isi_syarat)
                        VALUES (?, ?, ?);
                    """, (lomba_id, idx + 1, syarat))

                # Masukkan poster alternatif
                for poster_file in l.get("poster", []):
                    cursor.execute("""
                        INSERT INTO poster_lomba (lomba_id, nama_file)
                        VALUES (?, ?);
                    """, (lomba_id, poster_file))

        # 3. SEED POSTINGAN
        cursor.execute("SELECT COUNT(*) FROM postingan;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data postingan...")
            for p in data_store.postingan_list:
                dibuat_iso = (sekarang - timedelta(days=p.get("diunggah_hari_lalu", 0))).strftime("%Y-%m-%d %H:%M:%S")
                catatan_iso = (sekarang - timedelta(days=p.get("catatan_hari_lalu", 0))).strftime("%Y-%m-%d %H:%M:%S") if p.get("catatan_admin") else None
                gambar_str = (p.get("gambar") or [""])[0] if isinstance(p.get("gambar"), list) else str(p.get("gambar") or "")

                tgl_lomba = p.get("tanggal_lomba")
                tenggat_lomba = p.get("tenggat_lomba")
                tgl_lomba_iso = tgl_lomba.isoformat() if hasattr(tgl_lomba, "isoformat") else (str(tgl_lomba) if tgl_lomba else None)
                tenggat_lomba_iso = tenggat_lomba.isoformat() if hasattr(tenggat_lomba, "isoformat") else (str(tenggat_lomba) if tenggat_lomba else None)

                cursor.execute("""
                    INSERT INTO postingan (
                        id, user_id, judul, kategori, penyelenggara, deskripsi,
                        tanggal_lomba, tenggat_lomba, link, kontak, poster, dokumen, gambar,
                        status, dilihat, tersimpan, partner_tertarik,
                        alasan_singkat, catatan_admin, catatan_pada, bagian_diperbaiki,
                        remark, dibuat_pada, diperbarui_pada
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    p.get("id"),
                    1,
                    p.get("judul", ""),
                    p.get("kategori", ""),
                    p.get("penyelenggara", ""),
                    p.get("deskripsi", ""),
                    tgl_lomba_iso,
                    tenggat_lomba_iso,
                    p.get("link", ""),
                    p.get("kontak", ""),
                    p.get("poster", ""),
                    p.get("dokumen", ""),
                    gambar_str,
                    p.get("status", "Ditangguhkan"),
                    p.get("dilihat", 0),
                    p.get("tersimpan", 0),
                    p.get("partner_tertarik", 0),
                    p.get("alasan_singkat", ""),
                    p.get("catatan_admin", ""),
                    catatan_iso,
                    p.get("bagian_diperbaiki", ""),
                    p.get("remark", "Postingan contoh seeder"),
                    dibuat_iso,
                    dibuat_iso
                ))

        # 4. SEED NOTIFIKASI
        cursor.execute("SELECT COUNT(*) FROM notifikasi;")
        if cursor.fetchone()[0] == 0:
            print("[SEED] Memasukkan data notifikasi...")
            for n in data_store.notifikasi_list:
                dibuat_iso = (sekarang - timedelta(minutes=n.get("menit_lalu", 0))).strftime("%Y-%m-%d %H:%M:%S")
                # Cari id pengirim jika jenis partner
                pengirim_id = None
                if n.get("email"):
                    cursor.execute("SELECT id FROM users WHERE email = ?;", (n["email"],))
                    row = cursor.fetchone()
                    if row:
                        pengirim_id = row[0]

                cursor.execute("""
                    INSERT INTO notifikasi (id, user_id, pengirim_id, jenis, judul, dibaca, dibuat_pada)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    n.get("id"),
                    1,
                    pengirim_id,
                    n.get("jenis", "partner"),
                    n.get("judul", n.get("lomba", "")),
                    1 if n.get("dibaca") else 0,
                    dibuat_iso
                ))

        print("[SEED] Sukses! Database SQLite lokal 'teamup.db' (Versi 2) telah siap dan terisi data.")


if __name__ == "__main__":
    seed_database()
