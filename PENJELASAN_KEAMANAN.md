# Pertemuan 12 — Security & Error Handling (TeamUp)

Topik RPS: *validasi input, manajemen hak akses, serta global exception handling pada aplikasi.*

Semua angka di bawah diukur dengan tes otomatis, bukan perkiraan: `tes_keamanan.py` (206 pemeriksaan),
`tes_penanganan_error.py` (82), dan `tes_filesystem.py` (111, bagian enkripsi `.env`). Semuanya terisolasi
(folder data, database, dan jam palsu sementara), tidak menyentuh data asli maupun `teamup.db`.

---

## 1. Prinsip yang dipakai

| Prinsip | Arti | Contoh di TeamUp |
|---|---|---|
| **Jangan percaya input** | Semua isian user dianggap tidak aman sampai diperiksa | `validasi.py`: allow-list, bukan menebak yang berbahaya |
| **Least privilege** | Tiap peran hanya diberi izin yang dibutuhkan | Admin hanya boleh memutuskan status postingan, bukan mengubah postingan orang lain |
| **Deny by default** | Kalau tidak jelas siapa pelakunya, jawabannya TIDAK | Tanpa konfigurasi, tidak ada admin; belum login = tidak ada data |
| **Fail closed** | Konfigurasi rusak membuat aplikasi menolak, bukan jalan dengan aman-amanan palsu | `.env` berisi nilai contoh ditolak dengan pesan jelas |
| **Defense in depth** | Pertahanan berlapis: UI, lapisan data, database | Validasi di UI, aturan hak akses di `repository`, query berparameter di SQLite |
| **Satu sumber aturan** | Aturan ditulis di satu tempat | `helpers.is_valid_password` memanggil `validasi.periksa_password` |
| **Jangan bocorkan** | Pesan ke user dan isi log tidak memuat data sensitif | `penanganan_error.laporkan()` dan `samarkan()` |

---

## 2. Peta modul

| Modul | Tugas | Dipakai oleh |
|---|---|---|
| `validasi.py` | Validasi dan pembersihan input (email, nama, username, password, URL, telepon, kontak, teks) | halaman daftar, biodata, edit profil, form postingan, reset password |
| `keamanan_akun.py` | OTP aman, pembatas percobaan login, penyamaan waktu respons | `data_store`, `login_page` |
| `hak_akses.py` | Peran dan izin (kebijakan murni, tanpa database) | `repository`, `data_store` |
| `penanganan_error.py` | Hook error global, log berputar dengan penyamaran data, dialog ramah, `laporkan()` | `main`, semua halaman |
| `enkripsi.py` | Kunci dari `.env` (divalidasi), data lama tetap terbuka | `repository` (kontak), `post_form_page` (dokumen) |

---

## 3. Temuan review kode dan perbaikannya

| # | Temuan (sebelumnya) | Perbaikan | Diuji |
|---|---|---|---|
| 1 | OTP dibuat dengan `random` (bisa ditebak), 4 digit, tanpa kedaluwarsa dan tanpa batas percobaan: 10.000 kemungkinan bisa dicoba semua | `secrets`, berlaku 5 menit, maksimal 3 percobaan, sekali pakai, hanya hash yang disimpan | 40 thread menebak serentak hanya dihitung 3 percobaan |
| 2 | Login boleh dicoba tanpa batas | 5 gagal beruntun mengunci 30 detik, lalu 60, 120, dan seterusnya sampai maksimal 15 menit | halaman login asli: gagal ke-5 terkunci, password benar pun ditolak saat terkunci |
| 3 | Email tidak terdaftar ditolak lebih cepat daripada password salah, jadi waktu respons membocorkan email yang punya akun. Layar "Lupa password" juga menjawab "Email tidak terdaftar." | `samakan_waktu()` menjalankan satu hash palsu; layar memberi jawaban yang sama | selisih waktu 0,4x sampai 2,5x; email tak terdaftar tidak menampilkan pesan khusus |
| 4 | Pemeriksaan pemilik di `repository` bersifat opsional: kalau pemanggil lupa mengirim email, aturan terlewati | Pelaku wajib disebut; aturan dari `hak_akses` | ubah/hapus tanpa pelaku ditolak |
| 5 | `putuskan_postingan` (setujui/tolak lomba) bisa dipanggil siapa saja | Wajib `oleh=` admin | pemilik menyetujui lombanya sendiri ditolak |
| 6 | `tandai_dibaca(id)` tidak memeriksa pemilik (IDOR) | Hanya pemilik; id milik orang lain dan id yang tidak ada dijawab sama | pesan identik, id tidak bisa ditebak |
| 7 | "Postingan Saya" dan Notifikasi menampilkan data **semua** user | Disaring per user yang login | user lain, dan yang belum login, melihat 0 data |
| 8 | Error database hanya di-`print`, lalu data di memori tetap diubah: layar terlihat berhasil padahal gagal; akun hantu tetap ditambahkan | Error naik ke UI dan tampil sebagai pesan ramah dengan kode referensi | gagal simpan tidak menambah akun di memori |
| 9 | Unggah postingan tanpa login diam-diam atas nama `demo@teamup.com` | Ditolak | tidak ada postingan baru tercipta |
| 10 | Tidak ada penanganan error global dan tidak ada log | Hook `sys`, thread, dan unraisable, dialog dibatasi, log berputar dengan data disamarkan | 82 pemeriksaan |
| 11 | `.env.example` berisi nilai contoh publik; kalau disalin apa adanya, kunci enkripsi jadi tebakan publik. Kunci baru dari `.env` juga membuat data lama tidak bisa dibuka | Nilai contoh dan kunci terlalu pendek ditolak; dekripsi mencoba kunci `.env` lalu kunci lama | data lama tetap terbuka setelah `.env` aktif |
| 12 | Validasi longgar: email dianggap valid asal ada `@` dan `.`, username dan nama tanpa batas, kontak tidak dicek | `validasi.py` terpusat | 88 pemeriksaan |

**Dua celah yang ditemukan oleh tes sendiri** (bukti tes memang menangkap kesalahan):
- Fungsi `samakan_waktu` sempat saya panggil dengan nama salah (`samarkan_waktu`) di `data_store`, sehingga login
  dengan email tak terdaftar akan error. Tes `find_user` menangkapnya sebelum sampai ke pengguna.
- `validasi.periksa_email("a@b.com\n")` lolos karena `$` pada regex mengizinkan baris baru di akhir. Diperbaiki
  dengan `fullmatch` (berlaku juga untuk username dan nama situs pada URL).

---

## 4. Revisi dosen dan implementasinya

| Revisi | Implementasi |
|---|---|
| Kunci dari `.env` (HMAC) | `enkripsi._kunci_dari_env()`: hex 64 karakter dipakai langsung, teks panjang diturunkan lewat SHA-256, nilai contoh dan terlalu pendek ditolak |
| Pembatasan percobaan login | `keamanan_akun.catat_gagal()` dengan kunci berlipat dua |
| HTTPS saja | `validasi.periksa_url(url, wajib_https=True)`: `http://`, `javascript:`, `file:`, `data:`, dan `user:pass@` ditolak |
| Password 16 karakter | `validasi.periksa_password()`: huruf besar, kecil, angka, simbol; bukan password umum; tidak memuat nama email sendiri |
| Dialog error global | `penanganan_error.pasang_penanganan_global(app)` |

---

## 5. Hash dan kunci (pertanyaan yang sering muncul)

- **Password** di-*hash* satu arah dengan PBKDF2-HMAC-SHA256, 120.000 iterasi, dan **salt** acak 16 byte per
  password. Tersimpan di `teamup.db`, tabel `users`, kolom `password`, dengan format
  `pbkdf2_sha256$120000$<salt>$<hash>`. **Salt bukan rahasia**: tujuannya agar password yang sama menghasilkan hash
  berbeda dan tabel hash yang sudah dihitung tidak bisa dipakai. Tidak ada kunci rahasia untuk password.
- **Kontak dan dokumen** dienkripsi dua arah dengan **kunci rahasia** (`.env` atau `kunci.key`), disimpan **terpisah**
  dari database.
- Belum ada *pepper* (rahasia tambahan untuk hash password). Itu pengembangan lanjutan.

---

## 6. Hak akses (matriks izin)

| Aksi | Tamu | Pengguna | Admin |
|---|---|---|---|
| Lihat lomba terverifikasi | ya | ya | ya |
| Unggah postingan | tidak | ya (atas nama sendiri) | ya (atas nama sendiri) |
| Perbarui postingan | tidak | hanya miliknya, status Revisi | hanya miliknya, status Revisi |
| Hapus / batalkan pengajuan | tidak | hanya miliknya, bukan yang Disetujui | hanya miliknya, bukan yang Disetujui |
| Putuskan status (setujui / revisi / tolak) | tidak | tidak | **ya** |
| Baca / tandai / hapus notifikasi | tidak | hanya miliknya | hanya miliknya |

Admin ditentukan lewat variabel lingkungan `TEAMUP_ADMIN=admin@kampus.ac.id` (boleh beberapa, pisahkan koma) atau
`config.ADMIN_EMAILS`. Tanpa konfigurasi, tidak ada admin. Tidak ada perubahan skema database, jadi data user aman.

---

## 7. Penanganan error dan log

- **User** melihat satu baris ramah + kode referensi (`Terjadi kesalahan tak terduga. Silakan coba lagi. (kode: 403F9C7B)`).
  Detail teknis (nama tabel, path, pesan SQL) tidak pernah tampil.
- **Pengembang** mencari kode itu di `~/Library/Application Support/TeamUp/log/teamup.log` (512 KB × 3 cadangan).
- **Error bisnis** (aturan, hak akses, data tidak valid) tampil apa adanya sebagai peringatan, dicatat satu baris tanpa
  traceback.
- **Penyamaran log:** `budi@gmail.com` menjadi `b***@gmail.com`, nomor telepon, hash, token `enc1$`, `password=...`, OTP,
  dan path `/Users/...` disamarkan. Penyamaran dilakukan di formatter sehingga berlaku juga untuk isi traceback.
- **Pembatas banjir:** 30 error beruntun menjadi 1 dialog; semuanya tetap tercatat di log.
- **Peristiwa keamanan** dicatat sebagai baris `KEAMANAN ...`: login gagal, akun terkunci, akses ditolak, OTP salah,
  reset password.

---

## 8. Hasil uji

```
python3 tes_keamanan.py          # 206 pemeriksaan (jendela muncul sebentar)
python3 tes_penanganan_error.py  # 82 pemeriksaan
python3 tes_filesystem.py        # 111 pemeriksaan
```

| Kelompok `tes_keamanan.py` | Jumlah | Yang dibuktikan |
|---|---|---|
| validasi | 88 | Input valid lolos, input jahat (`<script>`, `DROP TABLE`, `javascript:`, byte NUL, baris baru) ditolak |
| keamanan_akun | 29 | OTP kedaluwarsa/3 percobaan/sekali pakai, 40 thread menebak, kunci login berlipat, memori dibatasi |
| hak_akses | 35 | Matriks izin ditegakkan di `repository` tanpa lewat UI, termasuk percobaan serangan |
| data_store | 33 | Reset password harus lolos OTP, data per user, tidak ada akun hantu |
| halaman | 14 | Pesan di layar daftar, lupa password, login (terkunci), profil, password baru |
| log | 7 | Peristiwa keamanan tercatat, data sensitif tidak |

Semua tes pertemuan sebelumnya tetap lulus: `tes_crud`, `tes_database`, `tes_thread` (32), `tes_paginasi` (21),
`tes_memori`, `tes_responsif`, `tes_skala`.

---

## 9. Demo untuk presentasi (± 3 menit)

1. **Validasi.** Daftar dengan nama `Budi123`, email `a@b.`, lalu password `pendek1A!`. Tiap kali muncul pesan yang jelas.
2. **Pembatas login.** Salah password 5 kali: muncul "Terlalu banyak percobaan. Coba lagi dalam 30 detik."; password
   benar pun ditolak.
3. **OTP.** Lupa password dengan email tak terdaftar: layar tetap lanjut tanpa pesan khusus. Dengan email terdaftar,
   salah kode 3 kali: kode hangus.
4. **Hak akses.** Login dengan dua akun: "Postingan Saya" hanya menampilkan milik masing-masing.
5. **Log.** `cat ~/Library/Application\ Support/TeamUp/log/teamup.log | tail`. Terlihat `KEAMANAN login_gagal
   email=d***@teamup.com`, tanpa password.
6. **Tes.** `python3 tes_keamanan.py` dan tunjukkan `LULUS: 206   GAGAL: 0`.

---

## 10. Keterbatasan (disampaikan terus terang)

- **Status OTP dan pembatas login disimpan di memori**, jadi hilang saat aplikasi ditutup. Orang yang menguasai
  komputer itu bisa menutup dan membuka ulang aplikasi untuk mereset pembatas. Untuk layanan server, status ini harus
  disimpan di database bersama.
- **OTP hanya 4 digit** (sesuai desain UI 4 kotak). Pertahanan utamanya batas 3 percobaan dan kedaluwarsa, bukan
  panjang kode. Pengiriman email masih simulasi (kode ditampilkan di dialog).
- **Daftar password umum hanya contoh kecil.** Produk sungguhan memakai daftar ribuan entri.
- **Belum ada pepper** untuk hash password, dan tidak ada UI admin (admin dikonfigurasi lewat `.env`/variabel lingkungan).
- **Aturan HTTPS saja** menolak penyelenggara yang hanya punya tautan `http://`. Itu konsekuensi revisi dosen.
- **`teamup.db` yang di-commit ke GitHub memuat kontak yang terenkripsi dengan kunci satu komputer.** Di komputer lain
  kontak itu tampil `(kontak tidak dapat dibuka)`. Disarankan `teamup.db` tidak dilacak git, supaya tiap komputer
  membuat data contoh sendiri.
- **Kunci enkripsi yang hilang berarti data terenkripsi tidak bisa dibuka.** Cadangkan `.env` dan `kunci.key`.
- Validasi di UI hanya untuk kenyamanan; pertahanan sebenarnya ada di lapisan data (hak akses, query berparameter).

---

## 11. Contekan tanya-jawab untuk dosen

**Q1: "Kenapa OTP hanya 4 digit, bukankah mudah ditebak?"**
Ada 10.000 kemungkinan, tetapi hanya 3 percobaan per kode dan kode hangus setelah 5 menit. Peluang menebak benar
dalam 3 percobaan sekitar 0,03%. Tes mensimulasikan 40 thread menebak bersamaan dan hanya 3 yang dihitung.

**Q2: "Kenapa password tidak dienkripsi?"**
Password tidak perlu dibaca kembali, hanya dicocokkan. Hash satu arah (PBKDF2, 120.000 iterasi, salt acak) lebih aman
karena tidak ada kunci yang bisa dicuri. Kontak dan dokumen harus dibaca kembali, jadi memakai enkripsi dua arah.

**Q3: "Kenapa pesan error ke user tidak menjelaskan penyebabnya?"**
Pesan teknis (nama tabel, path, pesan SQL) membantu penyerang memetakan sistem. User cukup tahu ada masalah dan kode
referensinya; pengembang membaca detailnya di log.

**Q4: "Kenapa 'Lupa password' tidak bilang email tidak terdaftar?"**
Supaya orang tidak bisa menebak email mana yang punya akun (*user enumeration*). Waktu respons juga disamakan lewat
`samakan_waktu()`.

**Q5: "Apa bedanya hak akses di UI dan di repository?"**
Tombol yang disembunyikan tidak melindungi apa pun karena orang bisa memanggil fungsinya langsung. Karena itu aturan
ditegakkan di `repository`, dan tes memanggilnya tanpa lewat UI sama sekali.

**Q6: "Kenapa admin tidak boleh mengubah postingan orang lain?"**
Prinsip *least privilege*: admin hanya diberi izin yang dibutuhkan, yaitu memutuskan status verifikasi.

**Q7: "Apa kelemahan sistem ini?"**
Lihat bagian 10. Yang paling penting: status pembatas disimpan di memori, enkripsi mengandalkan kunci di komputer
yang sama dengan datanya, dan pengiriman OTP masih simulasi.
