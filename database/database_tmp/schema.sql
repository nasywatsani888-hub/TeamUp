-- schema.sql — Skema Database Relasional TeamUp (SQLite), VERSI 2
-- Pertemuan 9: Database Design & Native Query
--
-- Perubahan dari versi 1 (alasannya dijelaskan di PENJELASAN_DATABASE_ORM.md):
--   * INDEX pada kolom yang dipakai WHERE / JOIN / ORDER BY (versi 1 tidak punya index sama sekali)
--   * CHECK untuk kolom bernilai terbatas (status, jenis notifikasi, biaya, ...) dan UNIQUE untuk mencegah duplikat
--   * Waktu disimpan sebagai TANGGAL / WAKTU, bukan "berapa hari lalu" (nilai itu basi besok pagi).
--     "sisa_hari", "diunggah_hari_lalu", "menit_lalu" kini DIHITUNG saat data dibaca.
--   * Data berulang dipecah: lomba_jenjang (1NF), notifikasi.pengirim_id (rujukan, bukan salinan nama/email),
--     lomba.tim_min / tim_maks (angka, bukan teks "2-4 Anggota").
--   * users.username boleh NULL (belum mengisi biodata) supaya UNIQUE tidak menolak dua akun baru.
--
-- Semua waktu memakai waktu LOKAL ('YYYY-MM-DD HH:MM:SS'); tanggal memakai 'YYYY-MM-DD'.
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. PENGGUNA
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nama        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password    TEXT NOT NULL,                       -- HASH "pbkdf2_sha256$iterasi$salt$hash", bukan teks asli
    username    TEXT UNIQUE COLLATE NOCASE,          -- NULL sampai biodata dilengkapi
    prodi       TEXT NOT NULL DEFAULT '',
    universitas TEXT NOT NULL DEFAULT '',
    domisili    TEXT NOT NULL DEFAULT '',
    bio         TEXT NOT NULL DEFAULT '',
    instagram   TEXT NOT NULL DEFAULT '',
    foto        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================================
-- 2. KEAHLIAN (master) + relasi MANY-TO-MANY ke user
-- ============================================================================
CREATE TABLE IF NOT EXISTS keahlian (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS user_keahlian (
    user_id     INTEGER NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    keahlian_id INTEGER NOT NULL REFERENCES keahlian(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, keahlian_id)
);
CREATE INDEX IF NOT EXISTS idx_user_keahlian_keahlian ON user_keahlian(keahlian_id);

-- ============================================================================
-- 3. PENGALAMAN (ONE-TO-MANY dari users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS pengalaman (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    judul   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pengalaman_user ON pengalaman(user_id);

-- ============================================================================
-- 4. LOMBA (informasi kompetisi yang sudah diverifikasi)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lomba (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    judul               TEXT NOT NULL,
    penyelenggara       TEXT NOT NULL,
    kategori            TEXT NOT NULL,
    warna               TEXT NOT NULL DEFAULT '#1B2A5E',
    tanggal_pelaksanaan TEXT NOT NULL DEFAULT '',          -- teks tampilan, mis. "15 - 16 Oktober 2026"
    tenggat_pendaftaran TEXT NOT NULL,                     -- tanggal ISO; "sisa hari" dihitung dari sini
    tim_min             INTEGER NOT NULL DEFAULT 1 CHECK (tim_min >= 1),
    tim_maks            INTEGER NOT NULL DEFAULT 1 CHECK (tim_maks >= tim_min),
    deskripsi           TEXT NOT NULL DEFAULT '',
    link                TEXT NOT NULL DEFAULT '',
    diunggah_pada       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    dilihat             INTEGER NOT NULL DEFAULT 0 CHECK (dilihat >= 0),
    jenis               TEXT NOT NULL DEFAULT 'Lainnya'
                        CHECK (jenis IN ('Hackathon', 'KTI/PKM', 'Desain/UI-UX', 'Lainnya')),
    cakupan             TEXT NOT NULL DEFAULT 'Nasional'
                        CHECK (cakupan IN ('Lokal/Regional', 'Nasional', 'Internasional')),
    biaya               TEXT NOT NULL DEFAULT 'Gratis' CHECK (biaya IN ('Gratis', 'Berbayar'))
);
CREATE INDEX IF NOT EXISTS idx_lomba_kategori ON lomba(kategori);
CREATE INDEX IF NOT EXISTS idx_lomba_tenggat  ON lomba(tenggat_pendaftaran);

-- Satu lomba bisa untuk beberapa jenjang (atribut berganda dipecah ke tabel sendiri -> 1NF)
CREATE TABLE IF NOT EXISTS lomba_jenjang (
    lomba_id INTEGER NOT NULL REFERENCES lomba(id) ON DELETE CASCADE,
    jenjang  TEXT NOT NULL CHECK (jenjang IN ('SMA/SMK/Sederajat', 'Mahasiswa')),
    PRIMARY KEY (lomba_id, jenjang)
);

CREATE TABLE IF NOT EXISTS syarat_lomba (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lomba_id   INTEGER NOT NULL REFERENCES lomba(id) ON DELETE CASCADE,
    urutan     INTEGER NOT NULL,
    isi_syarat TEXT NOT NULL,
    UNIQUE (lomba_id, urutan)
);

CREATE TABLE IF NOT EXISTS poster_lomba (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    lomba_id  INTEGER NOT NULL REFERENCES lomba(id) ON DELETE CASCADE,
    nama_file TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_poster_lomba_lomba ON poster_lomba(lomba_id);

-- ============================================================================
-- 5. POSTINGAN (lomba yang diunggah user, menunggu / sudah diverifikasi admin)
-- ============================================================================
CREATE TABLE IF NOT EXISTS postingan (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    judul             TEXT NOT NULL,
    kategori          TEXT NOT NULL,
    penyelenggara     TEXT NOT NULL,
    deskripsi         TEXT NOT NULL DEFAULT '',
    tanggal_lomba     TEXT,                                -- tanggal ISO
    tenggat_lomba     TEXT,                                -- tanggal ISO
    link              TEXT NOT NULL DEFAULT '',
    kontak            TEXT NOT NULL DEFAULT '',
    poster            TEXT NOT NULL DEFAULT '',            -- nama berkas yang diunggah user
    dokumen           TEXT NOT NULL DEFAULT '',
    gambar            TEXT NOT NULL DEFAULT '',            -- nama gambar di assets/poster/ untuk kotak kecil
    status            TEXT NOT NULL DEFAULT 'Ditangguhkan'
                      CHECK (status IN ('Ditangguhkan', 'Disetujui', 'Revisi', 'Ditolak')),
    dilihat           INTEGER NOT NULL DEFAULT 0 CHECK (dilihat >= 0),
    tersimpan         INTEGER NOT NULL DEFAULT 0 CHECK (tersimpan >= 0),
    partner_tertarik  INTEGER NOT NULL DEFAULT 0 CHECK (partner_tertarik >= 0),
    alasan_singkat    TEXT NOT NULL DEFAULT '',
    catatan_admin     TEXT NOT NULL DEFAULT '',
    catatan_pada      TEXT,                                -- kapan admin menulis catatan
    bagian_diperbaiki TEXT NOT NULL DEFAULT '' CHECK (bagian_diperbaiki IN ('', 'link')),
    dibuat_pada       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    diperbarui_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
-- Query utama halaman "Postingan Saya": WHERE user_id = ? [AND status = ?] ORDER BY dibuat_pada DESC
CREATE INDEX IF NOT EXISTS idx_postingan_user_status ON postingan(user_id, status);
CREATE INDEX IF NOT EXISTS idx_postingan_user_waktu  ON postingan(user_id, dibuat_pada DESC);

-- ============================================================================
-- 6. NOTIFIKASI
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifikasi (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,     -- penerima
    pengirim_id INTEGER REFERENCES users(id) ON DELETE SET NULL,             -- rujukan; nama & email lewat JOIN
    jenis       TEXT NOT NULL CHECK (jenis IN ('partner', 'disetujui', 'revisi')),
    judul       TEXT NOT NULL DEFAULT '',                                    -- judul lomba / postingan terkait
    dibaca      INTEGER NOT NULL DEFAULT 0 CHECK (dibaca IN (0, 1)),
    dibuat_pada TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_notifikasi_user_dibaca ON notifikasi(user_id, dibaca, dibuat_pada DESC);

-- ============================================================================
-- 7. RIWAYAT (lomba yang pernah dibuka) — satu baris per (user, lomba)
-- ============================================================================
CREATE TABLE IF NOT EXISTS riwayat (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lomba_id    INTEGER NOT NULL REFERENCES lomba(id) ON DELETE CASCADE,
    dibuka_pada TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
    UNIQUE (user_id, lomba_id)
);
CREATE INDEX IF NOT EXISTS idx_riwayat_user_waktu ON riwayat(user_id, dibuka_pada DESC);

-- ============================================================================
-- 8. TIM & ANGGOTA TIM (roadmap: belum dipakai UI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tim (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_tim   TEXT NOT NULL,
    lomba_id   INTEGER REFERENCES lomba(id) ON DELETE SET NULL,
    ketua_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_tim_ketua ON tim(ketua_id);

CREATE TABLE IF NOT EXISTS anggota_tim (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    tim_id  INTEGER NOT NULL REFERENCES tim(id)   ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    peran   TEXT NOT NULL DEFAULT 'Anggota',
    status  TEXT NOT NULL DEFAULT 'Diundang' CHECK (status IN ('Diundang', 'Diterima', 'Ditolak')),
    UNIQUE (tim_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_anggota_tim_user ON anggota_tim(user_id);
