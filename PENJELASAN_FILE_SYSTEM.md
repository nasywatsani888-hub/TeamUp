# Pertemuan 11 — File System & Local Storage (TeamUp)

Topik RPS: *integrasi penyimpanan file lokal, caching, konfigurasi, dan enkripsi data sensitif.*

Semua angka di bawah diukur dengan `tes_filesystem.py` (102 pemeriksaan) dan `tes_thread.py` (32 pemeriksaan),
bukan perkiraan. `tes_filesystem.py` **terisolasi**: memakai folder data dan database sementara, tidak menyentuh
data asli maupun `teamup.db`. `tes_thread.py` menjalankan aplikasi sungguhan, jadi bisa mengubah `teamup.db`;
setelah menjalankannya, kembalikan dengan `git restore teamup.db`.

---

## 1. Konsep singkat

| Konsep | Arti | Dipakai di TeamUp untuk |
|---|---|---|
| **Folder data aplikasi** | Lokasi resmi tiap sistem operasi untuk data milik user, terpisah dari kode program | Poster, dokumen, foto, cache, pengaturan |
| **Penulisan atomik** | Tulis ke berkas `.tmp`, lalu `os.replace()`. Berkas tujuan hanya ada dalam keadaan utuh atau tidak ada sama sekali | Semua penyimpanan berkas |
| **Cache disk** | Hasil olahan mahal yang disimpan agar tidak dihitung ulang | Poster yang sudah dipotong dan dibulatkan |
| **Konfigurasi** | Pengaturan yang berubah saat dipakai dan harus diingat antar sesi | Ukuran jendela, "Ingatkan saya" |
| **Hash vs enkripsi** | Hash = satu arah (cukup dicocokkan). Enkripsi = dua arah (bisa dikembalikan jika punya kunci) | Password di-*hash* (`sandi.py`), kontak & dokumen di-*enkripsi* |

**Lokasi folder data** (otomatis sesuai sistem operasi, memakai modul bawaan Python):

| Sistem operasi | Lokasi |
|---|---|
| macOS | `~/Library/Application Support/TeamUp` |
| Windows | `C:\Users\<nama>\AppData\Roaming\TeamUp` |
| Linux | `~/.local/share/TeamUp` |

Isinya: `unggahan/poster`, `unggahan/dokumen`, `unggahan/foto`, `cache`, `konfigurasi`, `cadangan`.

**Masalah sebelumnya:** berkas unggahan disimpan di dalam folder project (`assets/postingan`, `assets/foto`).
Akibatnya data user tercampur dengan kode, ikut hilang saat project di-*clone* ulang, dan gagal tersimpan
kalau aplikasi dipasang di folder yang *read-only*.

---

## 2. Peta modul

| Modul | Tugas | Dipakai oleh |
|---|---|---|
| `file_storage.py` | Lokasi folder, nama berkas aman, validasi, simpan atomik, hapus | `post_form_page`, `edit_profile_page`, `helpers` |
| `settings_store.py` | Pengaturan di `pengaturan.json` (atomik, tahan berkas rusak, aman antar thread) | `main`, `login_page` |
| `disk_cache.py` | Cache disk dengan batas ukuran (50 MB) dan umur (30 hari), strategi LRU | `helpers.lokasi_png_qml`, `main` |
| `enkripsi.py` | Enkripsi teks dan berkas, deteksi perubahan data | `repository` (kontak), `post_form_page` (dokumen) |

Prinsip yang sama dengan pertemuan sebelumnya: hanya modul bawaan Python, arsitektur tidak diubah, dan halaman
lama tetap berjalan (semua tes lama masih lulus).

---

## 3. Keputusan desain

**a. Database hanya menyimpan NAMA berkas, bukan path penuh.**
`1699_Proposal.pdf.enc`, bukan `/Users/mazaya/...`. Folder data boleh pindah tanpa merusak database.

**b. Apa yang dienkripsi, dan kenapa:**

| Data | Perlakuan | Alasan |
|---|---|---|
| Password | Hash PBKDF2 (sudah ada sejak Pertemuan 10) | Tidak perlu dibaca kembali |
| Kontak penyelenggara | Enkripsi di kolom database | Data pribadi (nomor telepon / email) |
| Dokumen pendukung | Enkripsi berkas (`.enc`) | Bisa berisi surat atau identitas |
| Poster | Tidak dienkripsi | Memang untuk dipublikasikan |

**c. Kunci disimpan TERPISAH dari database** (`konfigurasi/kunci.key`, izin `600`). Orang yang hanya
menyalin `teamup.db` tidak ikut mendapat kuncinya.

**d. Data lama tetap terbaca.** `dekripsi_teks()` mengembalikan teks biasa apa adanya, dan
`amankan_kontak_lama()` mengenkripsi data lama sekali saat aplikasi mulai. Migrasinya idempoten (aman diulang).

**e. Foto bawaan project tetap berfungsi.** `helpers.path_foto()` mencari di folder user lebih dulu, lalu di
`assets/foto`.

---

## 4. Cara kerja enkripsi (`enkripsi.py`)

```
kunci utama (32 byte acak, dibuat sekali)
   ├─ kunci_enkripsi = HMAC(kunci utama, "teamup-enkripsi")
   └─ kunci_mac      = HMAC(kunci utama, "teamup-mac")

Enkripsi:  nonce acak 16 byte
           keystream blok-i = HMAC-SHA256(kunci_enkripsi, nonce + i)
           ciphertext = data XOR keystream
           tag        = HMAC-SHA256(kunci_mac, "TUE1" + nonce + ciphertext)
           hasil      = "TUE1" + nonce + ciphertext + tag        (ukuran asli + 52 byte)

Dekripsi:  hitung ulang tag -> BANDINGKAN DULU (compare_digest) -> baru buka
           tag tidak cocok => DataRusak (data diubah atau kunci salah)
```

Hal yang dijaga dan diuji:
- Teks yang sama dienkripsi dua kali menghasilkan hasil **berbeda** (nonce acak).
- Mengubah **1 bit** saja membuat dekripsi **ditolak**, bukan menghasilkan teks sampah.
- Berkas diproses per 1 MB (RAM tetap kecil). Hasil dekripsi ditulis ke berkas sementara dan baru dipindah
  **setelah tag terbukti cocok**, jadi isi yang belum terverifikasi tidak pernah muncul sebagai berkas jadi.
- Berkas 10 MB selesai enkripsi plus dekripsi sekitar 1 detik (diukur di sandbox, angka di laptop bisa berbeda).

---

## 5. Alur yang terpengaruh

**Unggah Info Lomba**
```
Pilih poster (PDF) & dokumen -> periksa_berkas() [format, ukuran, tidak kosong]
  -> Kirim -> worker (thread lain) -> poster disalin apa adanya ke unggahan/poster
                                    -> dokumen dienkripsi ke unggahan/dokumen/<nama>.enc
  -> selesai (thread UI) -> nama berkas + kontak (terenkripsi) disimpan ke database
```

**Ganti foto profil:** validasi -> `simpan_berkas()` ke `unggahan/foto` -> foto lama dihapus **setelah profil
disimpan** (pilihan yang dibatalkan juga dibersihkan, jadi tidak jadi sampah).

**Cache poster:** `buat_kunci(path, mtime, ukuran, radius)` -> ada di disk? pakai; belum? render lalu simpan atomik.
Poster diganti -> `mtime` berubah -> kunci berubah -> cache lama otomatis tidak terpakai. `bersihkan()` jalan saat
startup.

**Pengaturan:** saat aplikasi ditutup, ukuran jendela disimpan; saat dibuka, dipulihkan. "Ingatkan saya" kini
bertahan setelah aplikasi ditutup (sebelumnya hanya di memori).

---

## 6. Temuan dan perbaikan

### Temuan A — Klik ganda "Kirim" memulai dua worker ke berkas yang sama
`handle_submit()` tidak punya penjaga. Kode lama kebetulan lolos karena dua worker menulis isi yang identik.
Begitu penyimpanan memakai berkas `.tmp` bernama tetap, keduanya bentrok (`FileNotFoundError` saat `os.replace`).

**Perbaikan, dua lapis:**
1. `handle_submit()` langsung `return` kalau `sedang_mengirim` masih `True`.
2. Nama `.tmp` dibuat unik (`uuid`) di `enkripsi.py` dan `settings_store.py`, jadi penulis yang berbarengan tidak
   saling menimpa walau penjaga di UI terlewat.

`tes_filesystem.py` menyertakan pemeriksaan empat thread menulis ke tujuan yang sama.

### Temuan B — Nama berkas dari user tidak boleh dipercaya
Nama seperti `../../etc/passwd` bisa membuat berkas keluar dari folder. `nama_aman()` membuang path dan simbol,
`path_berkas()` menolak nama yang keluar dari folder tujuan (*path traversal*), dan `hapus_berkas()` ikut kebal.

### Temuan C — Berkas rusak tidak boleh membuat aplikasi gagal dibuka
`pengaturan.json` yang rusak tidak membuat crash: berkasnya dipindah jadi `.rusak` (untuk diperiksa) dan nilai
bawaan dipakai. Nilai bertipe salah diabaikan satu per satu.

### Temuan D — Kunci hilang tidak boleh membuat aplikasi crash
Kalau `kunci.key` hilang atau berganti, kontak tampil sebagai `(kontak tidak dapat dibuka)` dan aplikasi tetap
berjalan (diuji).

---

## 7. Hasil uji

```
python3 tes_filesystem.py     # 102 pemeriksaan, terisolasi, tanpa menyentuh data asli
python3 tes_thread.py         # 32 pemeriksaan (bagian formulir kini memeriksa lokasi baru + enkripsi dokumen)
                              # mengubah teamup.db -> setelahnya: git restore teamup.db
```

| Kelompok uji | Jumlah | Yang dibuktikan |
|---|---|---|
| `file_storage` | 27 | Nama aman, anti path traversal, validasi, simpan atomik, hapus aman |
| `settings_store` | 16 | Tahan tutup-buka, berkas rusak, tipe salah, 12 thread menyimpan bersamaan |
| `disk_cache` | 14 | Hit/miss, 10 thread berebut kunci, batas ukuran (LRU), batas umur |
| `enkripsi` | 21 | Roundtrip pada batas blok, deteksi perubahan, kunci salah, berkas 3 MB, balapan penulis |
| Integrasi database | 10 | Kontak terenkripsi di database, terbaca normal, migrasi data lama, kunci hilang |
| Integrasi UI | 14 | Foto user vs foto bawaan, salin poster/dokumen `.enc`, pembatalan membersihkan sisa |

Semua tes pertemuan sebelumnya (`tes_database`, `tes_crud`, `tes_memori`, `tes_paginasi`, `tes_responsif`) tetap lulus.

---

## 8. Demo untuk presentasi (± 3 menit)

1. **Lokasi data.** Di Terminal: `ls -R ~/Library/Application\ Support/TeamUp`. Tunjukkan folder `unggahan`,
   `cache`, `konfigurasi`.
2. **Konfigurasi.** `cat ~/Library/Application\ Support/TeamUp/konfigurasi/pengaturan.json`, lalu ubah ukuran
   jendela, tutup, buka lagi, dan ukurannya diingat.
3. **Enkripsi di database.** Jalankan aplikasi sekali (migrasi data lama terjadi saat startup), lalu
   `sqlite3 teamup.db "select kontak from postingan"`. Yang tampil `enc1$...`, bukan nomor telepon. Di aplikasi
   nomornya tampil normal.
4. **Enkripsi berkas.** Unggah dokumen, lalu `xxd .../unggahan/dokumen/<nama>.enc | head`. Isinya acak, hanya
   penanda `TUE1` di awal.
5. **Deteksi perubahan.** Jalankan `python3 tes_filesystem.py` dan tunjukkan bagian 4 ("1 bit diubah -> ditolak").

---

## 9. Keterbatasan (disampaikan terus terang)

- **Enkripsi dibuat dengan modul bawaan Python** supaya sesuai ketentuan "tanpa library tambahan" dan alurnya
  bisa dijelaskan. Konstruksi (HMAC-SHA256 sebagai keystream, *encrypt-then-MAC*) memang standar, tetapi **tidak
  diaudit**. Untuk produk sungguhan gunakan library teruji seperti `cryptography` (Fernet / AES-GCM).
- **Kunci berada di komputer yang sama dengan datanya.** Ini melindungi dari penyalinan `teamup.db` saja, bukan
  dari orang yang menguasai seluruh akun pengguna di komputer itu. Solusi lanjutan: simpan kunci di Keychain
  macOS / Windows Credential Manager, atau turunkan dari password user.
- **Kunci hilang = data terenkripsi tidak bisa dibuka.** `kunci.key` perlu ikut dicadangkan.
- **Izin `600` pada berkas kunci hanya berlaku di macOS dan Linux.** Di Windows berkas hanya terlindungi oleh
  folder profil user.
- **Berkas lama di `assets/postingan` tidak dipindahkan.** Aplikasi hanya menyimpan namanya dan tidak pernah
  membukanya, jadi tidak berdampak, tetapi berkas itu masih ada di folder project.
- **Kontak terenkripsi tidak bisa dicari lewat SQL** (`LIKE`). Saat ini aplikasi tidak mencari berdasarkan kontak.
  Kalau nanti perlu, pencarian dilakukan setelah data dibuka di Python.

---

## 10. Contekan tanya-jawab untuk dosen

**Q1: "Kenapa data tidak disimpan di folder project saja?"**
Folder project berisi kode dan bisa *read-only* saat aplikasi dipasang. Data user bisa hilang waktu project
di-*clone* ulang atau di-*update*. Folder data aplikasi per sistem operasi adalah tempat yang memang disediakan
untuk itu, dan folder itu tidak ikut ke GitHub.

**Q2: "Apa bedanya hash dan enkripsi? Kenapa password tidak dienkripsi?"**
Hash satu arah: aplikasi hanya perlu mencocokkan password, tidak perlu membacanya, jadi tidak ada yang bisa
dibocorkan. Kontak dan dokumen harus bisa dibaca kembali oleh aplikasi, jadi memakai enkripsi dua arah.

**Q3: "Kenapa tidak pakai library `cryptography`?"**
Ketentuan proyek: hanya Python standard library. Konsekuensinya kami jelaskan terus terang di bagian 9, dan untuk
produksi kami menyarankan `cryptography`.

**Q4: "Apa yang terjadi kalau listrik mati saat berkas sedang disimpan?"**
Kami tulis ke berkas `.tmp` lalu `os.replace()`. Berkas tujuan hanya ada dalam keadaan utuh atau tidak ada. Sisa
`.tmp` dibersihkan, dan tes memeriksanya.

**Q5: "Bagaimana kalau seseorang mengubah isi berkas terenkripsi?"**
Tag HMAC tidak akan cocok dan dekripsi ditolak. Tes mengubah 1 bit di tengah berkas 3 MB dan hasilnya ditolak,
tanpa meninggalkan berkas setengah jadi.

**Q6: "Cache disk tidak akan memenuhi harddisk?"**
Dibatasi 50 MB dan 30 hari. Saat melebihi batas, yang paling lama tidak dipakai dibuang lebih dulu (LRU).
Waktu pemakaian dicatat lewat `os.utime`, bukan `atime`, karena banyak sistem mematikan `atime`.

**Q7: "Apa hubungannya dengan Pertemuan 7 (thread)?"**
Penyalinan dan enkripsi dokumen berjalan di *worker*, jadi UI tidak membeku. Saat dua worker menulis ke berkas
yang sama, muncul race condition yang kami temukan lewat tes dan perbaiki (Temuan A).
