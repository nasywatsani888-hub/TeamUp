# Pertemuan 7 — Concurrency & Multi-Threading (TeamUp)

Topik RPS: *penerapan background worker untuk menjaga agar UI tidak freeze / not responding.*

Semua angka di bawah diukur dengan alat yang ada di repo (`tes_responsif.py`, `demo_thread.py`, `tes_thread.py`),
bukan perkiraan. Angka bisa sedikit berbeda di komputermu; yang penting perbandingan "sebelum vs sesudah".

---

## 1. Konsep singkat

**Aplikasi GUI hidup dari satu "event loop" di satu thread (thread UI).** Thread itu yang menggambar jendela,
menerima klik, dan menjalankan timer. Kalau thread UI diberi pekerjaan 3 detik, selama 3 detik itu ia tidak bisa
menggambar atau menerima klik → jendela "membeku" (*not responding*).

**Solusinya:** pekerjaan berat dipindah ke *thread lain* (worker), sementara thread UI tetap berputar.
Hasilnya dikirim kembali ke thread UI.

| Konsep | Penjelasan singkat |
|---|---|
| Thread vs proses | Thread berbagi memori satu proses (ringan, tapi rawan bentrok data). Proses punya memori sendiri (aman, tapi lebih berat). |
| Aturan emas Qt | Widget **hanya boleh disentuh dari thread UI**. Worker tidak boleh membuat / mengubah widget. |
| Signal lintas thread | Kalau signal di-emit dari thread lain, Qt otomatis **mengantre** panggilannya ke thread penerima → aman. Inilah cara worker "bicara" ke UI. |
| `QThread` vs `QRunnable` + `QThreadPool` | `QThread` untuk pekerja yang hidup lama dengan event loop sendiri. `QRunnable` + `QThreadPool` untuk banyak tugas pendek (thread dipakai ulang). Kita memakai yang kedua. |
| `QImage` vs `QPixmap` | `QImage` aman dipakai di thread mana pun. `QPixmap` hanya boleh di thread UI. Karena itu pekerjaan berat memakai `QImage`, lalu diubah jadi `QPixmap` di thread UI. |
| GIL (Python) | Hanya satu thread yang menjalankan bytecode Python pada satu waktu. Thread membantu untuk **menunggu** (I/O, jaringan, disk) dan memanggil kode C++ yang melepas GIL, tetapi **tidak mempercepat hitungan Python murni**. |
| Race condition | Dua thread mengubah data yang sama bersamaan → hasil salah. Obatnya: `Lock`, atau (lebih baik) data bersama hanya disentuh satu thread. |
| Deadlock | Dua thread saling menunggu kunci yang dipegang lawannya. Dihindari dengan satu kunci yang pendek dan tidak bersarang. |

---

## 2. Mencari masalah dulu (audit)

Tidak semua hal perlu di-thread-kan; thread menambah kerumitan. Jadi kita **ukur dulu** operasi mana yang menahan UI
lebih dari 100 ms (batas yang mulai terasa "ngelag"):

| Operasi (thread UI) | Hasil ukur |
|---|---|
| Menyalin berkas 10 MB di disk lokal | ±5 ms → tidak perlu, tetapi bisa lama di flashdisk / drive jaringan / iCloud |
| Dekode poster asli (±1 MP) | ±25 ms |
| **Pertama kali membuka Rekan Tim** | **±250 ms** ← masalah |
| **Pertama kali membuka Detail Lomba** | **±190 ms** ← masalah |
| **Pertama kali membuka Profil Rekan** | **±180 ms** ← masalah |

Penyebabnya terlacak dengan `cProfile`: **foto profil di `assets/foto/` terlalu besar**.
`marques.png` berukuran 1920×2876 px (2,8 MB) dan `nadia.png` 1200×1600 px. Dekode + penskalaan foto-foto itu
(`_pixmap_foto`) menghabiskan ±90% waktu pembukaan halaman, dan dilakukan di thread UI.

---

## 3. Solusi yang dibuat

### 3.1 `workers.py` — infrastruktur worker yang bisa dipakai ulang (±100 baris)
```python
def kerja_berat(kontrol, nama):          # berjalan di THREAD LAIN
    for i in range(100):
        if kontrol.dibatalkan: return None    # pembatalan kooperatif
        ...
        kontrol.laporkan(i + 1)               # progres 0-100
    return "hasil"

workers.jalankan(kerja_berat, "x",
                 saat_selesai=...,   # dipanggil di THREAD UI
                 saat_galat=...,     # dipanggil di THREAD UI
                 saat_progres=...)   # dipanggil di THREAD UI
```
- `Worker(QRunnable)` + `SinyalWorker(QObject)` (progres / selesai / galat) + `Kontrol` (lapor progres & tanda batal).
- Error di thread lain **tidak hilang diam-diam**: dikirim ke thread UI lewat signal `galat`.
- Pembatalan **kooperatif**: worker harus rajin memeriksa `kontrol.dibatalkan`. (Thread tidak bisa "dibunuh" dengan aman.)
- Worker yang sedang berjalan dipegang di `_aktif` agar tidak dihapus Python di tengah jalan.
- Batas thread pool dinaikkan minimal 4, karena pekerjaan I/O kebanyakan menunggu (bukan menghitung). Tanpa itu,
  di laptop 2-core penyalinan berkas bisa terpaksa antre di belakang preload.
- `tunggu_selesai()` dipanggil di `closeEvent` dan `aboutToQuit`: aplikasi tidak ditutup saat thread masih jalan.

### 3.2 Preload foto & poster di latar belakang (`preload.py` + `helpers.py`)
Selagi pengguna masih di layar splash / login, worker menyiapkan semua gambar; saat halaman dibuka, tinggal diambil.

```
thread UI : menyusun daftar kerja (menyentuh data_store)          ──┐ data bersama hanya diakses
thread UI : mengambil hasil & membuat QPixmap                      ──┘ oleh SATU thread
worker    : membaca file, decode, skala, potong sudut (QImage saja)
```
- Pemuatan gambar dibagi dua tahap: `render_kotak()` (berat, `QImage`, aman di thread mana pun) dan
  `_bangun_pixmap()` (ringan, `QPixmap`, thread UI).
- Hasil worker diparkir di `_gambar_siap` dengan `threading.Lock`. Kalau thread UI butuh gambar yang belum siap,
  ia mengerjakannya sendiri (cara lama) → tidak pernah menunggu / macet total.
- Berkas PNG untuk QML ditulis worker secara **atomik** (tulis ke `.tmp` lalu `os.replace`), sehingga QML tidak
  pernah membaca berkas setengah jadi.
- Preload dimulai **setelah** semua halaman jadi (`QTimer.singleShot(0, ...)`). Kalau dimulai lebih awal, worker
  berebut CPU dengan pembangunan halaman dan startup melambat (terbukti saat uji: 411 → 741 ms di mesin 1-core).

### 3.3 Menyalin berkas saat "Kirim untuk verifikasi" (`views/post_form_page.py`)
`shutil.copy` di thread UI diganti `salin_berkas()` di worker:
- disalin per potongan 1 MB sambil melapor **progres** → `QProgressBar`;
- tombol **terkunci** selama mengirim (klik ganda tidak membuat postingan dobel);
- kalau **gagal / dibatalkan**, berkas setengah jadi **dihapus lagi**;
- meninggalkan halaman saat mengirim → worker dibatalkan dan hasil yang menyusul diabaikan (`token_kirim`);
- `data_store` hanya diubah di thread UI setelah penyalinan selesai (`selesaikan()`).

---

## 4. Hasil pengukuran

### 4.1 Tugas berat: thread UI vs worker (`python tes_responsif.py`, bagian A)
Dekode 4 gambar besar (4000×5000 px), tugas yang sama:

| Cara | Total waktu | UI macet terlama |
|---|---|---|
| Di thread UI | ±1.600 ms | **±1.600 ms → FREEZE** |
| Di worker | ±1.650 ms | **±35 ms → lancar** |

Total waktunya sama; bedanya **UI tetap hidup**. Thread tidak membuat pekerjaan lebih cepat, hanya tidak menahan UI.

### 4.2 Pertama kali membuka halaman (bagian B)
| Halaman | Tanpa preload | Dengan preload |
|---|---|---|
| Rekan Tim | 262 ms | **27 ms** |
| Detail Lomba | 189 ms | **33 ms** |
| Profil Rekan | 179 ms | **14 ms** |

### 4.3 Demo percobaan (`python demo_thread.py --otomatis`)
| Percobaan | Hasil |
|---|---|
| Pekerjaan 3 detik di thread UI | UI macet **3.030 ms** |
| Pekerjaan sama di worker | UI macet **12 ms** |
| Loop Python murni 12 juta iterasi di worker | UI macet 15 ms (tetap hidup), tetapi tidak lebih cepat karena GIL |
| 4 thread menambah penghitung bersama, 500× tiap thread, **tanpa Lock** | hasil **±500 dari 2000** (pembaruan hilang) |
| Sama, **dengan Lock** | **2000 dari 2000** |

### 4.4 Tidak merusak yang lama
- `tes_thread.py`: **30 / 30** pemeriksaan lulus.
- Tes fungsi sebelumnya (32 pemeriksaan: tombol, dialog, cache): lulus.
- `tes_memori.py` 100 siklus: widget stabil (736 → 736), pertumbuhan memori Python 0,66 KB/siklus
  (sama seperti Pertemuan 6) → infrastruktur thread tidak menambah kebocoran.

---

## 4b. Kasus "banyak data": apakah UI freeze kalau datanya ribuan?

**Ya, sebelum diperbaiki.** Ini sumber freeze yang *berbeda* dari bagian 2: bukan operasi berat (gambar, berkas), tetapi
**membuat ribuan widget sekaligus**. Halaman Postingan Saya, Rekan Tim, dan Lomba membuat SEMUA baris/kartu begitu
dibuka, di thread UI. Waktunya naik sebanding dengan jumlah data (±3-5 ms per item di mesin uji), sehingga dengan
1000 item jendela tertahan 3-4 detik, dan sudah terasa ngelag di kisaran 20-50 item.

**Kenapa worker tidak menolong?** Qt melarang widget dibuat di thread lain. Pekerjaan yang lambat *adalah* membuat widget,
jadi harus di thread UI. Satu-satunya cara: **membuat lebih sedikit widget sekaligus**.

| Teknik | Cara kerja | Dipakai? |
|---|---|---|
| **Paginasi** ("Muat lebih banyak") | hanya satu halaman (12-15 item) dibuat; sisanya saat diminta | **Ya** |
| Render bertahap | semua item dibuat, tetapi 5-10 per putaran `QTimer` agar UI sempat bernapas | belum (cadangan) |
| List virtual (`QListView`, `ListView` QML) | hanya item yang terlihat di layar yang dibuat | belum (paling ideal untuk puluhan ribu item) |
| Worker | menyiapkan / mengurutkan / memfilter data di latar belakang | tidak perlu: 1000 item hanya beberapa ms |

**Yang dibuat**
- `views/paginasi.py`: komponen "Menampilkan X dari Y" + tombol "Muat lebih banyak (N lagi)" untuk Postingan Saya dan Rekan Tim.
- `ModelLomba(QAbstractListModel)` di `views/lomba_backend.py` untuk halaman Lomba (QML). Dengan array JavaScript biasa,
  *setiap* "Muat lebih banyak" membangun ulang SEMUA kartu (makin lama makin berat). Dengan model Qt,
  `beginInsertRows` hanya menambah kartu baru.
- Ukuran halaman di `sizes.py` (`UKURAN_HALAMAN_*`). Mengganti filter / urutan kembali ke halaman pertama.
- Angka di chip ("Semua (40)") dan subjudul ("24 rekan tersedia") tetap menghitung **semua** data, bukan yang tampil.

**Hasil ukur** (`python tes_skala.py`, alat dan mesin sama, dalam ms; di atas 100 ms terasa ngelag)

| Halaman / aksi | Sebelum 50 data | Sebelum 200 | Sebelum 1000 | **Sesudah 50** | **Sesudah 1000** |
|---|---|---|---|---|---|
| Buka Postingan Saya | 134 | 662 | **4.314** | 54 | **51** |
| Ganti filter status | 44 | 189 | 1.215 | 41 | 44 |
| Buka halaman Lomba | 109 | 636 | **3.202** | 59 | **55** |
| Filter Lomba | 31 | 251 | 1.376 | 16 | 14 |
| Buka Rekan Tim | 109 | 462 | **3.063** | 45 | **36** |
| Muat 1 halaman lagi | – | – | – | 35 / 36 / 35 | 36 / 21 / 32 |
| Beranda (hanya 4 kartu) | 2 | 2 | 2 | 2 | 2 |

Setelah paginasi waktunya **datar**: 1000 data sama cepatnya dengan 50 data. `tes_paginasi.py` memeriksa ini secara otomatis
(2000 postingan menghasilkan jumlah baris yang sama dengan 50, dan waktu bukanya tidak jauh berbeda).

---

## 5. Aturan keselamatan thread yang dipakai

1. **Widget hanya disentuh thread UI.** Worker hanya mengembalikan nilai / mengirim signal.
2. **`data_store` hanya diakses thread UI.** `preload.kerjakan` tidak menyebut `data_store` sama sekali
   (diperiksa otomatis oleh `tes_thread.py` lewat `inspect.getsource`).
3. **Struktur yang memang dibagi antar-thread dikunci** (`_gambar_siap`, `_kunci_dipakai` memakai satu `Lock` yang
   dipegang sangat singkat dan tidak pernah bersarang → tidak mungkin deadlock).
4. **Worker harus kooperatif**: memeriksa `kontrol.dibatalkan` secara berkala. Worker yang tidak mau berhenti
   akan membuat `closeEvent` menunggu sampai batas waktu (3 detik).
5. **Hasil basi diabaikan** (`token_kirim`), supaya pekerjaan yang sudah dibatalkan tidak mengubah UI / data.

---

## 6. Batasan yang jujur
- Preload hanya membantu kalau selesai sebelum halaman dibuka. Kalau pengguna secepat kilat membuka Rekan Tim,
  thread UI mengerjakan sendiri (sama seperti sebelumnya, tidak lebih buruk).
- **Akar masalahnya sebenarnya ukuran foto.** Diukur: membuat avatar 90 px dari `marques.png` asli (1920×2876 px,
  2,8 MB) butuh ±162 ms, sedangkan dari versi 600 px (±457 KB) hanya ±15 ms, sepuluh kali lebih cepat.
  Thread *menyembunyikan* biayanya, mengecilkan aset *menghilangkannya*. Idealnya dua-duanya.
- Parkiran `_gambar_siap` menyimpan sampai ±20 `QImage` sampai dipakai (±beberapa MB). Dibatasi daftar kerja dan
  dikosongkan oleh `clear_image_cache()`.
- Penyalinan foto profil di `edit_profile_page.py` masih sinkron (berkasnya kecil). Bisa dipindah dengan pola yang sama.
- Paginasi memakai tombol "Muat lebih banyak", bukan *infinite scroll*; Notifikasi dan Riwayat belum dipaginasi
  (polanya sama). Untuk puluhan ribu item, list virtual (`QListView` / QML `ListView`) lebih tepat.
- Pemfilteran / pengurutan data masih berjalan di Python (O(N)); untuk 1000 item hanya beberapa milidetik. Untuk
  jutaan item perlu database dengan query (Pertemuan 9-10).
- Kirim OTP di aplikasi ini hanya simulasi, jadi tidak ada panggilan jaringan nyata yang perlu di-thread-kan.
  Kalau nanti memakai SMTP / API sungguhan, pola `workers.jalankan(...)` yang sama dipakai.
- Uji berjalan tanpa jendela dan di mesin 1-core; di Mac multi-core angka mutlaknya lebih kecil, tetapi
  perbandingan "freeze vs lancar" tetap sama.

---

## 7. Cara menjalankan

```bash
pip install psutil                 # opsional (membaca RAM)
python demo_thread.py              # JENDELA demo: bola bergerak; klik tombol 1 (freeze) vs tombol 2 (worker)
python demo_thread.py --otomatis   # angka percobaan di terminal
python tes_responsif.py            # ukur macet UI: tanpa vs dengan worker / preload
python tes_thread.py               # 30 uji otomatis
python tes_skala.py                # ukur "banyak data": 10 / 50 / 200 / 1000 item (atau: python tes_skala.py 100 5000)
python tes_paginasi.py             # 21 uji otomatis paginasi
TEAMUP_DEBUG_MEMORY=1 python main.py   # juga mencetak "[preload] N gambar ... ms" saat aplikasi dibuka
```

## 8. Kemungkinan pertanyaan saat presentasi

- **Kenapa tidak semua dipindah ke thread?** Thread menambah kerumitan (race condition, pembatalan, penutupan).
  Kita ukur dulu; hanya yang terbukti > 100 ms yang dipindah. Penyalinan 10 MB lokal hanya 5 ms, tetapi tetap
  dipindah karena kecepatan disk tujuan tidak bisa dijamin.
- **Kenapa tidak membuat `QPixmap` di worker?** Qt melarangnya; `QPixmap` terikat ke sistem grafis yang hanya
  boleh diakses thread UI. `QImage` bebas thread.
- **Apa bedanya thread dan proses? Kapan pakai yang mana?** Thread untuk menunggu / I/O dan kode C++ yang melepas
  GIL; proses terpisah (`multiprocessing` / `QProcess`) untuk hitungan Python berat.
- **Bagaimana kalau worker error?** Pengecualian ditangkap di `Worker.run` lalu dikirim lewat signal `galat` ke thread UI.
- **Bagaimana mencegah race condition?** Data bersama (`data_store`) hanya diubah thread UI; struktur yang dibagi
  dilindungi `Lock`; demo percobaan 3 menunjukkan bedanya (±500 vs 2000).
- **Bagaimana cara membatalkan thread?** Tidak bisa dipaksa; pakai tanda batal yang diperiksa worker (kooperatif).
- **Kenapa signal aman lintas thread?** Qt mengubahnya jadi *queued connection*: panggilan dimasukkan ke antrean
  event thread penerima dan dijalankan di sana.

## 9. Daftar file
| File | Isi |
|---|---|
| `workers.py` (baru) | `Worker`, `Kontrol`, `jalankan()`, `tunggu_selesai()` |
| `preload.py` (baru) | menyusun & menjalankan preload gambar di latar belakang |
| `helpers.py` | pemuatan gambar dua tahap (`render_kotak` QImage + `_bangun_pixmap` QPixmap) dan parkiran terkunci |
| `views/post_form_page.py` | penyalinan berkas di worker + progress bar + pembatalan |
| `main.py` | mulai preload, `closeEvent` & `aboutToQuit` menunggu worker |
| `styles.py` | gaya progress bar |
| `tes_responsif.py`, `tes_thread.py`, `demo_thread.py` (baru) | alat ukur, uji otomatis, demo presentasi |
| `views/paginasi.py` (baru) | komponen "Muat lebih banyak" |
| `views/upload_page.py`, `views/partner_page.py`, `views/card_grid.py` | memakai paginasi |
| `views/lomba_backend.py`, `views/qml/LombaPage.qml` | `ModelLomba` + paginasi QML |
| `tes_skala.py`, `tes_paginasi.py` (baru) | uji banyak data dan uji paginasi |
