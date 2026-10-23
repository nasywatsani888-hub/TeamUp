-- schema.sql — Skema Database Relasional TeamUp (SQLite)
-- Pertemuan 9: Database Design & Native Query
-- Mengaktifkan pengecekan Foreign Key di SQLite
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. TABEL PENGGUNA (USERS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    username TEXT UNIQUE,
    prodi TEXT DEFAULT '',
    universitas TEXT DEFAULT '',
    domisili TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    instagram TEXT DEFAULT '',
    foto TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. TABEL KEAHLIAN & RELASI MANY-TO-MANY KE USER
-- ============================================================================
-- Master data keahlian (misal: "UI/UX Designer", "Programmer", dsb.)
CREATE TABLE IF NOT EXISTS keahlian (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT UNIQUE NOT NULL
);

-- Tabel pivot / persimpangan Many-to-Many antara users dan keahlian
CREATE TABLE IF NOT EXISTS user_keahlian (
    user_id INTEGER NOT NULL,
    keahlian_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, keahlian_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (keahlian_id) REFERENCES keahlian(id) ON DELETE CASCADE
);

-- ============================================================================
-- 3. TABEL PENGALAMAN (ONE-TO-MANY DARI USERS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS pengalaman (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    judul TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================================
-- 4. TABEL LOMBA (INFORMASI KOMPETISI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lomba (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judul TEXT NOT NULL,
    penyelenggara TEXT NOT NULL,
    kategori TEXT NOT NULL,
    sisa_hari INTEGER DEFAULT 0,
    warna TEXT DEFAULT '#1B2A5C',
    tanggal_pelaksanaan TEXT,
    anggota_tim TEXT,
    deskripsi TEXT,
    link TEXT,
    diunggah_hari_lalu INTEGER DEFAULT 0,
    dilihat INTEGER DEFAULT 0,
    -- Atribut filter
    jenjang TEXT DEFAULT 'Mahasiswa',
    jenis TEXT DEFAULT 'Lainnya',
    cakupan TEXT DEFAULT 'Nasional',
    biaya TEXT DEFAULT 'Gratis',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Syarat-syarat lomba (One-to-Many dari lomba)
CREATE TABLE IF NOT EXISTS syarat_lomba (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lomba_id INTEGER NOT NULL,
    urutan INTEGER DEFAULT 0,
    isi_syarat TEXT NOT NULL,
    FOREIGN KEY (lomba_id) REFERENCES lomba(id) ON DELETE CASCADE
);

-- Nama-nama file poster alternatif (One-to-Many dari lomba)
CREATE TABLE IF NOT EXISTS poster_lomba (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lomba_id INTEGER NOT NULL,
    nama_file TEXT NOT NULL,
    FOREIGN KEY (lomba_id) REFERENCES lomba(id) ON DELETE CASCADE
);

-- ============================================================================
-- 5. TABEL POSTINGAN LOMBA OLEH PENGGUNA (WORKFLOW ADMIN)
-- ============================================================================
-- Status: 'Ditangguhkan', 'Disetujui', 'Revisi', 'Ditolak'
CREATE TABLE IF NOT EXISTS postingan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    judul TEXT NOT NULL,
    kategori TEXT NOT NULL,
    penyelenggara TEXT NOT NULL,
    deskripsi TEXT,
    tanggal_lomba TEXT,
    tenggat_lomba TEXT,
    link TEXT,
    kontak TEXT,
    poster TEXT,
    dokumen TEXT,
    status TEXT DEFAULT 'Ditangguhkan',
    diunggah_hari_lalu INTEGER DEFAULT 0,
    dilihat INTEGER DEFAULT 0,
    tersimpan INTEGER DEFAULT 0,
    partner_tertarik INTEGER DEFAULT 0,
    alasan_singkat TEXT DEFAULT '',
    catatan_admin TEXT DEFAULT '',
    catatan_hari_lalu INTEGER DEFAULT 0,
    bagian_diperbaiki TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================================
-- 6. TABEL NOTIFIKASI
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifikasi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    jenis TEXT NOT NULL,  -- 'partner' | 'disetujui' | 'revisi'
    judul TEXT,           -- judul lomba atau postingan
    nama_pengirim TEXT,   -- nama partner yang tertarik
    email_pengirim TEXT,  -- email partner
    menit_lalu INTEGER DEFAULT 0,
    dibaca INTEGER DEFAULT 0, -- 0 = belum, 1 = sudah
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================================
-- 7. TABEL RIWAYAT LOMBA YANG DIBUKA
-- ============================================================================
CREATE TABLE IF NOT EXISTS riwayat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lomba_id INTEGER NOT NULL,
    dibuka_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lomba_id) REFERENCES lomba(id) ON DELETE CASCADE
);

-- ============================================================================
-- 8. TABEL ROADMAP FITUR TIM (DISIAPKAN UNTUK PENGEMBANGAN SELANJUTNYA)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_tim TEXT NOT NULL,
    deskripsi TEXT DEFAULT '',
    lomba_id INTEGER,
    ketua_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lomba_id) REFERENCES lomba(id) ON DELETE SET NULL,
    FOREIGN KEY (ketua_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anggota_tim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tim_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    peran TEXT DEFAULT 'Anggota',
    status TEXT DEFAULT 'Menunggu', -- 'Menunggu', 'Diterima', 'Ditolak'
    FOREIGN KEY (tim_id) REFERENCES tim(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
