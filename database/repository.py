# database/repository.py — Semua query (native SQL) untuk CRUD TeamUp  [Pertemuan 10]
#
# Prinsip:
#   1. SEMUA nilai dari luar dikirim lewat placeholder '?' (parameterized query) -> kebal SQL injection.
#      Nama kolom pada UPDATE memakai daftar putih (konstanta di bawah), bukan masukan pengguna.
#   2. Satu fungsi publik = satu transaksi (db.koneksi): berhasil semua atau batal semua.
#   3. Fungsi muat_*() mengembalikan dict dengan BENTUK YANG SAMA seperti data contoh lama di data_store.py,
#      sehingga seluruh UI tidak perlu diubah. Nilai turunan ("sisa_hari", "diunggah_hari_lalu", "menit_lalu")
#      dihitung di sini dari tanggal / waktu yang tersimpan, jadi tidak pernah basi.
#   4. Aturan bisnis ditegakkan juga di sini (bukan hanya di tombol UI): UI bisa saja berubah / dilewati.
import sqlite3
from datetime import date, datetime, timedelta

import enkripsi
import hak_akses
from database import db, sandi


class DataTidakValid(Exception):
    """Data melanggar batasan database (UNIQUE, CHECK, FOREIGN KEY, ...) atau kesalahan operasional."""


class AturanBisnis(DataTidakValid):
    """Operasi ditolak oleh aturan bisnis (mis. hanya postingan berstatus Revisi yang boleh diperbarui)."""


class HakAksesDitolak(AturanBisnis):
    """Pelaku tidak berhak melakukan operasi ini (bukan pemilik, bukan admin, atau belum login).
    Turunan AturanBisnis -> kode lama yang menangkap AturanBisnis tetap berfungsi."""


FORMAT_WAKTU = "%Y-%m-%d %H:%M:%S"
KOLOM_PROFIL = ("nama", "username", "prodi", "universitas", "domisili", "bio", "instagram", "foto")   # daftar putih UPDATE
KOLOM_POSTINGAN = ("judul", "kategori", "deskripsi", "tanggal_lomba", "tenggat_lomba", "link", "kontak", "poster", "dokumen")


# ------------------------------------------------------------------ waktu
def _sekarang():
    return datetime.now()


def _tulis_waktu(dt):
    return dt.strftime(FORMAT_WAKTU)


def _baca_waktu(teks):
    return datetime.strptime(teks.split(".")[0], FORMAT_WAKTU)


def _hari_lalu(teks, sekarang=None):
    """Selisih HARI KALENDER (bukan kelipatan 24 jam): diunggah kemarin malam = 1 hari lalu."""
    sekarang = sekarang or _sekarang()
    return max(0, (sekarang.date() - _baca_waktu(teks).date()).days)


def _menit_lalu(teks, sekarang=None):
    sekarang = sekarang or _sekarang()
    return max(0, int((sekarang - _baca_waktu(teks)).total_seconds() // 60))


def _iso(tanggal):
    return tanggal.isoformat() if tanggal else None


def _dari_iso(teks):
    return date.fromisoformat(teks) if teks else None


def teks_tim(tim_min, tim_maks):
    """(2, 4) -> '2-4 Anggota'; (3, 3) -> '3 Anggota'; (1, 1) -> 'Individu'."""
    if tim_min == tim_maks == 1:
        return "Individu"
    return f"{tim_min} Anggota" if tim_min == tim_maks else f"{tim_min}-{tim_maks} Anggota"


def _bungkus(fungsi):
    """Ubah error sqlite3 (IntegrityError dan OperationalError) menjadi DataTidakValid agar lapisan UI bersih."""
    def pembungkus(*args, **kwargs):
        try:
            return fungsi(*args, **kwargs)
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as error:
            raise DataTidakValid(str(error)) from error
    pembungkus.__name__ = fungsi.__name__
    pembungkus.__doc__ = fungsi.__doc__
    return pembungkus


# ================================================================== USERS
def muat_users():
    with db.koneksi() as c:
        baris = c.execute("SELECT * FROM users ORDER BY id").fetchall()
        keahlian, pengalaman = {}, {}
        for r in c.execute("SELECT uk.user_id, k.nama FROM user_keahlian uk JOIN keahlian k ON k.id = uk.keahlian_id ORDER BY uk.rowid"):
            keahlian.setdefault(r["user_id"], []).append(r["nama"])
        for r in c.execute("SELECT user_id, judul FROM pengalaman ORDER BY id"):
            pengalaman.setdefault(r["user_id"], []).append(r["judul"])
    return [{
        "id": r["id"], "nama": r["nama"], "email": r["email"], "password": r["password"], "username": r["username"] or "",
        "prodi": r["prodi"], "universitas": r["universitas"], "domisili": r["domisili"], "bio": r["bio"],
        "keahlian": keahlian.get(r["id"], []), "instagram": r["instagram"],
        "pengalaman": pengalaman.get(r["id"], []), "foto": r["foto"],
        "remark": r["remark"] if "remark" in r.keys() else "",
        "created_at": r["created_at"] if "created_at" in r.keys() else "",
    } for r in baris]


def _id_user(c, email):
    baris = c.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if baris is None:
        raise DataTidakValid(f"Pengguna dengan email {email} tidak ditemukan")
    return baris["id"]


def _tulis_keahlian(c, user_id, daftar):
    c.execute("DELETE FROM user_keahlian WHERE user_id = ?", (user_id,))
    for nama in daftar:
        c.execute("INSERT OR IGNORE INTO keahlian(nama) VALUES (?)", (nama,))
        keahlian_id = c.execute("SELECT id FROM keahlian WHERE nama = ?", (nama,)).fetchone()["id"]
        c.execute("INSERT OR IGNORE INTO user_keahlian(user_id, keahlian_id) VALUES (?, ?)", (user_id, keahlian_id))


def _tulis_pengalaman(c, user_id, daftar):
    c.execute("DELETE FROM pengalaman WHERE user_id = ?", (user_id,))
    c.executemany("INSERT INTO pengalaman(user_id, judul) VALUES (?, ?)", [(user_id, judul) for judul in daftar])


@_bungkus
def simpan_user_baru(user):
    """CREATE: pendaftaran. 'password' pada dict harus sudah berupa hash."""
    with db.koneksi() as c:
        cur = c.execute(
            "INSERT INTO users(nama, email, password, username, prodi, universitas, domisili, bio, instagram, foto, remark) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["nama"], user["email"], user["password"], user.get("username") or None,
             user.get("prodi", ""), user.get("universitas", ""), user.get("domisili", ""), user.get("bio", ""),
             user.get("instagram", ""), user.get("foto", ""), user.get("remark", "Pendaftaran mandiri via aplikasi")))
        _tulis_keahlian(c, cur.lastrowid, user.get("keahlian", []))
        _tulis_pengalaman(c, cur.lastrowid, user.get("pengalaman", []))
        return cur.lastrowid


@_bungkus
def perbarui_user(email, perubahan):
    """UPDATE profil. Keahlian & pengalaman diganti seluruhnya, dalam SATU transaksi dengan kolom profil."""
    with db.koneksi() as c:
        user_id = _id_user(c, email)
        kolom = [k for k in KOLOM_PROFIL if k in perubahan]
        if kolom:
            nilai = [(perubahan[k] or None) if k == "username" else perubahan[k] for k in kolom]
            # nama kolom berasal dari daftar putih KOLOM_PROFIL (bukan masukan pengguna) -> aman dirangkai
            c.execute(f"UPDATE users SET {', '.join(k + ' = ?' for k in kolom)} WHERE id = ?", (*nilai, user_id))
        if "keahlian" in perubahan:
            _tulis_keahlian(c, user_id, perubahan["keahlian"])
        if "pengalaman" in perubahan:
            _tulis_pengalaman(c, user_id, perubahan["pengalaman"])


@_bungkus
def perbarui_password(email, password_hash):
    with db.koneksi() as c:
        c.execute("UPDATE users SET password = ? WHERE id = ?", (password_hash, _id_user(c, email)))


@_bungkus
def hapus_user(email):
    """DELETE akun user. Relasi keahlian, pengalaman, riwayat, dll otomatis terhapus via CASCADE."""
    with db.koneksi() as c:
        c.execute("DELETE FROM users WHERE email = ?", (email,))
        return True


# ================================================================== LOMBA
def muat_lomba():
    sekarang = _sekarang()
    with db.koneksi() as c:
        baris = c.execute("SELECT * FROM lomba ORDER BY id").fetchall()
        syarat, poster, jenjang = {}, {}, {}
        for r in c.execute("SELECT lomba_id, isi_syarat FROM syarat_lomba ORDER BY lomba_id, urutan"):
            syarat.setdefault(r["lomba_id"], []).append(r["isi_syarat"])
        for r in c.execute("SELECT lomba_id, nama_file FROM poster_lomba ORDER BY id"):
            poster.setdefault(r["lomba_id"], []).append(r["nama_file"])
        for r in c.execute("SELECT lomba_id, jenjang FROM lomba_jenjang ORDER BY lomba_id, rowid"):
            jenjang.setdefault(r["lomba_id"], []).append(r["jenjang"])
    return [{
        "id": r["id"], "judul": r["judul"], "penyelenggara": r["penyelenggara"], "kategori": r["kategori"],
        "sisa_hari": max(0, (_dari_iso(r["tenggat_pendaftaran"]) - sekarang.date()).days), "warna": r["warna"],
        "tanggal_pelaksanaan": r["tanggal_pelaksanaan"], "anggota_tim": teks_tim(r["tim_min"], r["tim_maks"]),
        "deskripsi": r["deskripsi"], "syarat": syarat.get(r["id"], []), "link": r["link"],
        "diunggah_hari_lalu": _hari_lalu(r["diunggah_pada"], sekarang), "dilihat": r["dilihat"],
        "jenjang": jenjang.get(r["id"], []), "jenis": r["jenis"], "cakupan": r["cakupan"], "biaya": r["biaya"],
        "poster": poster.get(r["id"], []),
    } for r in baris]


@_bungkus
def tambah_lomba_dilihat(lomba_id):
    """Menaikkan counter dilihat pada kompetisi saat detail lomba dibuka."""
    with db.koneksi() as c:
        c.execute("UPDATE lomba SET dilihat = dilihat + 1 WHERE id = ?", (lomba_id,))


# ================================================================== POSTINGAN
def _baca_kontak(nilai):
    """Kontak penyelenggara disimpan TERENKRIPSI di database; dibuka di sini. Data lama yang masih teks biasa
    tetap terbaca. Kalau kunci hilang / data rusak, tampilkan pesan netral (aplikasi tidak crash)."""
    try:
        return enkripsi.dekripsi_teks(nilai)
    except enkripsi.DataRusak:
        return "(kontak tidak dapat dibuka)"


def amankan_kontak_lama():
    """Migrasi sekali jalan: enkripsi kontak yang masih berupa teks biasa (mis. dari seeder / versi lama).
    Aman dipanggil berulang kali (idempoten). Mengembalikan jumlah baris yang diamankan."""
    with db.koneksi() as c:
        baris = c.execute("SELECT id, kontak FROM postingan WHERE kontak != '' AND kontak NOT LIKE ?",
                          (enkripsi.AWALAN_TEKS + "%",)).fetchall()
        for r in baris:
            c.execute("UPDATE postingan SET kontak = ? WHERE id = ?", (enkripsi.enkripsi_teks(r["kontak"]), r["id"]))
    return len(baris)


def _dict_postingan(r, sekarang):
    return {
        "id": r["id"], "judul": r["judul"], "gambar": [r["gambar"]] if r["gambar"] else [],
        "kategori": r["kategori"], "penyelenggara": r["penyelenggara"], "deskripsi": r["deskripsi"],
        "tanggal_lomba": _dari_iso(r["tanggal_lomba"]), "tenggat_lomba": _dari_iso(r["tenggat_lomba"]),
        "link": r["link"], "kontak": _baca_kontak(r["kontak"]), "poster": r["poster"], "dokumen": r["dokumen"],
        "status": r["status"], "diunggah_hari_lalu": _hari_lalu(r["dibuat_pada"], sekarang),
        "dilihat": r["dilihat"], "tersimpan": r["tersimpan"], "partner_tertarik": r["partner_tertarik"],
        "alasan_singkat": r["alasan_singkat"], "catatan_admin": r["catatan_admin"],
        "catatan_hari_lalu": _hari_lalu(r["catatan_pada"], sekarang) if r["catatan_pada"] else 0,
        "bagian_diperbaiki": r["bagian_diperbaiki"], "pemilik": r["pemilik"],
        "remark": r["remark"] if "remark" in r.keys() else "",
        "dibuat_pada": r["dibuat_pada"] if "dibuat_pada" in r.keys() else "",
    }


def muat_postingan(email_pemilik=None, status=None):
    """Memuat postingan lomba, mendukung filter pemilik dan status di level SQL."""
    sekarang = _sekarang()
    with db.koneksi() as c:
        sql = "SELECT p.*, u.email AS pemilik FROM postingan p JOIN users u ON u.id = p.user_id"
        kondisi = []
        params = []
        if email_pemilik:
            kondisi.append("u.email = ?")
            params.append(email_pemilik)
        if status:
            kondisi.append("p.status = ?")
            params.append(status)
        if kondisi:
            sql += " WHERE " + " AND ".join(kondisi)
        sql += " ORDER BY p.dibuat_pada DESC, p.id DESC"
        rows = c.execute(sql, params).fetchall()
    return [_dict_postingan(r, sekarang) for r in rows]


@_bungkus
def tambah_postingan(email_pemilik, data):
    """CREATE: postingan baru, status awal Ditangguhkan. Mengembalikan id baru."""
    with db.koneksi() as c:
        cur = c.execute(
            "INSERT INTO postingan(user_id, judul, kategori, penyelenggara, deskripsi, tanggal_lomba, tenggat_lomba, "
            "link, kontak, poster, dokumen, gambar, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_id_user(c, email_pemilik), data["judul"], data["kategori"], data["penyelenggara"], data.get("deskripsi", ""),
             _iso(data.get("tanggal_lomba")), _iso(data.get("tenggat_lomba")), data.get("link", ""), enkripsi.enkripsi_teks(data.get("kontak", "")),
             data.get("poster", ""), data.get("dokumen", ""), (data.get("gambar") or [""])[0], data.get("remark", "Pengajuan baru pengguna")))
        return cur.lastrowid


@_bungkus
def perbarui_postingan(post_id, data, email_pemilik=None):
    """UPDATE (kirim ulang perbaikan). ATURAN: hanya postingan berstatus Revisi. Status kembali Ditangguhkan."""
    with db.koneksi() as c:
        baris = c.execute("SELECT p.status, u.email AS pemilik FROM postingan p JOIN users u ON u.id = p.user_id "
                          "WHERE p.id = ?", (post_id,)).fetchone()
        if baris is None:
            raise DataTidakValid(f"Postingan {post_id} tidak ditemukan")
        # Pelaku WAJIB disebut (dulu opsional -> pemeriksaan bisa dilewati dengan tidak mengirim email)
        izin, pesan = hak_akses.boleh_ubah_postingan(email_pemilik, baris["pemilik"], baris["status"])
        if not izin:
            raise HakAksesDitolak(pesan)
        kolom = [k for k in KOLOM_POSTINGAN if k in data]
        nilai = [_iso(data[k]) if k in ("tanggal_lomba", "tenggat_lomba")
                 else enkripsi.enkripsi_teks(data[k]) if k == "kontak" else data[k] for k in kolom]
        sekarang = _tulis_waktu(_sekarang())
        set_kolom = (', '.join(k + ' = ?' for k in kolom) + ', ') if kolom else ''
        c.execute(
            f"UPDATE postingan SET {set_kolom}status = 'Ditangguhkan', "
            "alasan_singkat = '', catatan_admin = '', catatan_pada = NULL, bagian_diperbaiki = '', "
            "dibuat_pada = ?, diperbarui_pada = ? WHERE id = ?", (*nilai, sekarang, sekarang, post_id))


@_bungkus
def hapus_postingan(post_id, email_pemilik=None):
    """DELETE (batalkan / hapus pengajuan). ATURAN: postingan yang sudah Disetujui tidak boleh dihapus pemiliknya."""
    with db.koneksi() as c:
        baris = c.execute("SELECT p.status, u.email AS pemilik FROM postingan p JOIN users u ON u.id = p.user_id "
                          "WHERE p.id = ?", (post_id,)).fetchone()
        if baris is None:
            return False
        izin, pesan = hak_akses.boleh_hapus_postingan(email_pemilik, baris["pemilik"], baris["status"])
        if not izin:
            raise HakAksesDitolak(pesan)
        c.execute("DELETE FROM postingan WHERE id = ?", (post_id,))
        return True


@_bungkus
def tambah_postingan_counter(post_id, kolom, delta=1):
    """Menaikkan counter postingan: dilihat, tersimpan, atau partner_tertarik."""
    if kolom not in ("dilihat", "tersimpan", "partner_tertarik"):
        raise DataTidakValid(f"Kolom counter tidak dikenal: {kolom}")
    with db.koneksi() as c:
        c.execute(f"UPDATE postingan SET {kolom} = MAX(0, {kolom} + ?) WHERE id = ?", (delta, post_id))


@_bungkus
def putuskan_postingan(post_id, status, alasan_singkat="", catatan_admin="", bagian_diperbaiki="", oleh=None):
    """Sisi ADMIN: ubah status + (kalau Disetujui / Revisi) buat notifikasi untuk pemilik, dalam SATU transaksi.
    'oleh' = email pelaku; WAJIB admin (lihat hak_akses). Tanpa ini siapa pun bisa menyetujui lomba sendiri."""
    izin, pesan = hak_akses.boleh_putuskan_postingan(oleh)
    if not izin:
        raise HakAksesDitolak(pesan)
    if status not in hak_akses.STATUS_VALID:
        raise DataTidakValid(f"Status tidak dikenal: {status}")
    with db.koneksi() as c:
        baris = c.execute("SELECT p.judul, p.user_id FROM postingan p WHERE p.id = ?", (post_id,)).fetchone()
        if baris is None:
            raise DataTidakValid(f"Postingan {post_id} tidak ditemukan")
        sekarang = _tulis_waktu(_sekarang())
        c.execute("UPDATE postingan SET status = ?, alasan_singkat = ?, catatan_admin = ?, catatan_pada = ?, "
                  "bagian_diperbaiki = ?, diperbarui_pada = ? WHERE id = ?",
                  (status, alasan_singkat, catatan_admin, sekarang if catatan_admin else None, bagian_diperbaiki, sekarang, post_id))
        if status in ("Disetujui", "Revisi"):
            c.execute("INSERT INTO notifikasi(user_id, jenis, judul, dibuat_pada) VALUES (?, ?, ?, ?)",
                      (baris["user_id"], status.lower(), baris["judul"], sekarang))


# ================================================================== NOTIFIKASI
def muat_notifikasi(email_pemilik=None, hanya_belum_dibaca=False):
    """Memuat notifikasi pengguna, mendukung filter penerima dan status baca di SQL."""
    sekarang = _sekarang()
    with db.koneksi() as c:
        sql = ("SELECT n.*, u.email AS pemilik, s.nama AS nama_pengirim, s.email AS email_pengirim "
               "FROM notifikasi n JOIN users u ON u.id = n.user_id LEFT JOIN users s ON s.id = n.pengirim_id")
        kondisi = []
        params = []
        if email_pemilik:
            kondisi.append("u.email = ?")
            params.append(email_pemilik)
        if hanya_belum_dibaca:
            kondisi.append("n.dibaca = 0")
        if kondisi:
            sql += " WHERE " + " AND ".join(kondisi)
        sql += " ORDER BY n.dibuat_pada DESC, n.id DESC"
        rows = c.execute(sql, params).fetchall()

    hasil = []
    for r in rows:
        item = {"id": r["id"], "jenis": r["jenis"]}
        if r["jenis"] == "partner":
            item.update({"nama": r["nama_pengirim"] or "Seseorang", "email": r["email_pengirim"] or "", "lomba": r["judul"]})
        else:
            item["judul"] = r["judul"]
        item.update({"menit_lalu": _menit_lalu(r["dibuat_pada"], sekarang), "dibaca": bool(r["dibaca"]), "pemilik": r["pemilik"]})
        hasil.append(item)
    return hasil


@_bungkus
def buat_notifikasi(email_penerima, jenis, judul, email_pengirim=None):
    with db.koneksi() as c:
        pengirim = _id_user(c, email_pengirim) if email_pengirim else None
        return c.execute("INSERT INTO notifikasi(user_id, pengirim_id, jenis, judul, dibuat_pada) VALUES (?, ?, ?, ?, ?)",
                         (_id_user(c, email_penerima), pengirim, jenis, judul, _tulis_waktu(_sekarang()))).lastrowid


def tandai_dibaca(notif_id, email_pemilik=None):
    """Tandai satu notifikasi sudah dibaca. Hanya pemiliknya yang boleh (mencegah IDOR: mengganti id di
    parameter untuk menyentuh notifikasi orang lain). Notifikasi yang tidak ada / milik orang lain diberi
    jawaban yang SAMA, supaya penyerang tidak bisa menebak id mana yang ada."""
    with db.koneksi() as c:
        baris = c.execute("SELECT u.email AS pemilik FROM notifikasi n JOIN users u ON u.id = n.user_id "
                          "WHERE n.id = ?", (notif_id,)).fetchone()
        izin, _pesan = hak_akses.boleh_akses_milik(email_pemilik, baris["pemilik"] if baris else "")
        if not izin:
            raise HakAksesDitolak("Notifikasi tidak ditemukan atau bukan milik Anda.")
        c.execute("UPDATE notifikasi SET dibaca = 1 WHERE id = ?", (notif_id,))


@_bungkus
def tandai_semua_notifikasi_dibaca(email_penerima):
    """Menandai seluruh notifikasi milik user menjadi sudah dibaca."""
    with db.koneksi() as c:
        user_id = _id_user(c, email_penerima)
        c.execute("UPDATE notifikasi SET dibaca = 1 WHERE user_id = ?", (user_id,))


@_bungkus
def hapus_notifikasi(notif_id, email_pemilik=None):
    """Menghapus satu notifikasi. Pemilik WAJIB disebut (dulu tanpa email = menghapus notifikasi siapa pun)."""
    with db.koneksi() as c:
        baris = c.execute("SELECT u.email AS pemilik FROM notifikasi n JOIN users u ON u.id = n.user_id "
                          "WHERE n.id = ?", (notif_id,)).fetchone()
        izin, _pesan = hak_akses.boleh_akses_milik(email_pemilik, baris["pemilik"] if baris else "")
        if not izin:
            raise HakAksesDitolak("Notifikasi tidak ditemukan atau bukan milik Anda.")
        c.execute("DELETE FROM notifikasi WHERE id = ?", (notif_id,))


# ================================================================== RIWAYAT
def muat_riwayat(email):
    """id lomba yang pernah dibuka user ini, yang TERBARU di depan."""
    with db.koneksi() as c:
        rows = c.execute("SELECT r.lomba_id FROM riwayat r JOIN users u ON u.id = r.user_id WHERE u.email = ? "
                         "ORDER BY r.dibuka_pada DESC, r.id DESC", (email,)).fetchall()
    return [r["lomba_id"] for r in rows]


@_bungkus
def catat_riwayat(email, lomba_id):
    """UPSERT: pertama kali -> INSERT; dibuka lagi -> hanya perbarui waktunya (tidak menumpuk duplikat)."""
    with db.koneksi() as c:
        c.execute("INSERT INTO riwayat(user_id, lomba_id, dibuka_pada) VALUES (?, ?, ?) "
                  "ON CONFLICT(user_id, lomba_id) DO UPDATE SET dibuka_pada = excluded.dibuka_pada",
                  (_id_user(c, email), lomba_id, _sekarang().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))


@_bungkus
def hapus_riwayat(email, lomba_id=None):
    """Hapus satu entri riwayat lomba, atau hapus seluruh riwayat jika lomba_id=None."""
    with db.koneksi() as c:
        user_id = _id_user(c, email)
        if lomba_id is not None:
            c.execute("DELETE FROM riwayat WHERE user_id = ? AND lomba_id = ?", (user_id, lomba_id))
        else:
            c.execute("DELETE FROM riwayat WHERE user_id = ?", (user_id,))


# ================================================================== AUDIT TRAIL
def validasi_audit_user(user_id, created_at, remark=None):
    """
    Validasi ganda untuk keperluan audit (Sesuai Catatan Dosen):
    Memvalidasi integritas data pengguna berdasarkan ID dan created_at / remark.
    Mencegah modifikasi sepihak atau pemalsuan identitas baris database.
    """
    with db.koneksi() as c:
        if remark:
            baris = c.execute(
                "SELECT id, nama, email, created_at, remark FROM users WHERE id = ? AND created_at = ? AND remark = ?",
                (user_id, created_at, remark)
            ).fetchone()
        else:
            baris = c.execute(
                "SELECT id, nama, email, created_at, remark FROM users WHERE id = ? AND created_at = ?",
                (user_id, created_at)
            ).fetchone()
        return dict(baris) if baris else None


def validasi_audit_postingan(post_id, dibuat_pada, remark=None):
    """
    Validasi ganda untuk keperluan audit (Sesuai Catatan Dosen):
    Memvalidasi integritas pengajuan lomba berdasarkan ID dan dibuat_pada / remark.
    """
    with db.koneksi() as c:
        if remark:
            baris = c.execute(
                "SELECT id, judul, status, dibuat_pada, remark FROM postingan WHERE id = ? AND dibuat_pada = ? AND remark = ?",
                (post_id, dibuat_pada, remark)
            ).fetchone()
        else:
            baris = c.execute(
                "SELECT id, judul, status, dibuat_pada, remark FROM postingan WHERE id = ? AND dibuat_pada = ?",
                (post_id, dibuat_pada)
            ).fetchone()
        return dict(baris) if baris else None
