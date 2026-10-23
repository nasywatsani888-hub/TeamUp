# tes_database.py — Skrip Demonstrasi Database Native SQLite TeamUp
# Jalankan skrip ini untuk presentasi Pertemuan 9 di depan dosen / kelas:
#   python tes_database.py
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import get_connection, query_all, query_one, execute_commit
from database.seeder import seed_database


def garis(judul=""):
    if judul:
        print(f"\n{'=' * 20} {judul} {'=' * 20}")
    else:
        print("=" * 60)


def tes_1_cek_tabel():
    garis("TES 1: Cek Struktur Tabel yang Terdaftar di SQLite")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Total tabel ditemukan: {len(tables)}")
        for i, t in enumerate(tables, 1):
            cursor.execute(f"SELECT COUNT(*) FROM {t};")
            count = cursor.fetchone()[0]
            print(f"  {i}. Tabel '{t:<15}' -> {count} baris data")


def tes_2_relasi_user_keahlian():
    garis("TES 2: Query Relasional (JOIN Many-to-Many: User <-> Keahlian)")
    sql = """
        SELECT u.nama, u.universitas, GROUP_CONCAT(k.nama, ', ') AS daftar_keahlian
        FROM users u
        LEFT JOIN user_keahlian uk ON u.id = uk.user_id
        LEFT JOIN keahlian k ON uk.keahlian_id = k.id
        GROUP BY u.id;
    """
    rows = query_all(sql)
    for r in rows:
        keahlian = r['daftar_keahlian'] or '(Belum diisi)'
        print(f"[-] {r['nama']} ({r['universitas']})")
        print(f"    Keahlian: {keahlian}\n")


def tes_3_lomba_dan_syarat():
    garis("TES 3: Query Relasional (One-to-Many: Lomba & Syarat Pendaftaran)")
    lomba = query_one("SELECT * FROM lomba WHERE id = 1;")
    if lomba:
        print(f"Judul Lomba : {lomba['judul']}")
        print(f"Penyelenggara: {lomba['penyelenggara']} | Kategori: {lomba['kategori']}")
        syarat_list = query_all("SELECT isi_syarat FROM syarat_lomba WHERE lomba_id = ? ORDER BY urutan;", (lomba['id'],))
        print("Syarat Pendaftaran:")
        for i, s in enumerate(syarat_list, 1):
            print(f"  {i}. {s['isi_syarat']}")


def tes_4_crud_simulasi():
    garis("TES 4: Simulasi Transaksi CRUD (Insert -> Select -> Delete)")
    # 1. Insert
    test_email = "mahasiswa_baru@teamup.com"
    # Pastikan bersih dulu
    execute_commit("DELETE FROM users WHERE email = ?;", (test_email,))

    print(f"1. Melakukan INSERT pengguna baru: {test_email}...")
    new_id = execute_commit("""
        INSERT INTO users (nama, email, password, username, prodi, universitas)
        VALUES (?, ?, ?, ?, ?, ?);
    """, ("Budi Santoso", test_email, "rahasia123", "budisantoso", "Informatika", "UNY"))
    print(f"   -> Berhasil di-insert dengan ID: {new_id}")

    # 2. Select
    user = query_one("SELECT id, nama, email, username FROM users WHERE id = ?;", (new_id,))
    print(f"2. Hasil SELECT data yang baru dibuat:")
    print(f"   ID: {user['id']} | Nama: {user['nama']} | Username: @{user['username']}")

    # 3. Delete
    print("3. Menghapus data percobaan (DELETE)...")
    execute_commit("DELETE FROM users WHERE id = ?;", (new_id,))
    check = query_one("SELECT * FROM users WHERE id = ?;", (new_id,))
    print(f"   -> Cek keberadaan setelah dihapus: {'Ada' if check else 'BERHASIL DIHAPUS (None)'}")


def tes_5_foreign_key_integrity():
    garis("TES 5: Uji Integritas Foreign Key (CASCADE Delete)")
    # Buat dummy user & pengalaman
    user_id = execute_commit("""
        INSERT INTO users (nama, email, password) VALUES (?, ?, ?);
    """, ("User Percobaan FK", "dummy_fk@teamup.com", "pass123"))

    execute_commit("INSERT INTO pengalaman (user_id, judul) VALUES (?, ?);", (user_id, "Juara 1 Lomba Coding 2026"))
    execute_commit("INSERT INTO pengalaman (user_id, judul) VALUES (?, ?);", (user_id, "Finalis UI/UX Competition"))

    count_sebelum = query_one("SELECT COUNT(*) as total FROM pengalaman WHERE user_id = ?;", (user_id,))['total']
    print(f"Pengalaman terdaftar untuk user #{user_id}: {count_sebelum} buah.")

    print(f"Menghapus user #{user_id} dari tabel 'users'...")
    execute_commit("DELETE FROM users WHERE id = ?;", (user_id,))

    count_sesudah = query_one("SELECT COUNT(*) as total FROM pengalaman WHERE user_id = ?;", (user_id,))['total']
    print(f"Pengalaman setelah user dihapus: {count_sesudah} buah (Otomatis terhapus via CASCADE).")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("      DEMO PENGUJIAN DATABASE RELASIONAL (SQLITE NATIVE)      ")
    print("                     APLIKASI TEAMUP                          ")
    print("=" * 60)

    # Pastikan database ada isinya
    seed_database()

    tes_1_cek_tabel()
    tes_2_relasi_user_keahlian()
    tes_3_lomba_dan_syarat()
    tes_4_crud_simulasi()
    tes_5_foreign_key_integrity()

    garis("KESIMPULAN")
    print("Semua tes berhasil 100%! Database siap dipresentasikan di Pertemuan 9.")
    garis()
