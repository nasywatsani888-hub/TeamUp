# Pertemuan 6 — Memory & Resource Management (TeamUp)

Topik RPS: *deteksi memory leak, manajemen objek grafis, optimasi RAM (garbage collection / manual).*

Semua angka di bawah diukur sendiri dengan `tes_memori.py` (100 siklus buka-tutup semua halaman dan dialog),
bukan perkiraan.

---

## 1. Konsep singkat

**Python mengelola memori dengan dua cara**
1. *Hitungan referensi (reference counting)*: objek dihapus saat tidak ada lagi yang menunjuknya.
2. *Garbage collector (GC) siklik*: menyapu objek yang saling menunjuk (A ↔ B) sehingga hitungannya tidak pernah 0.
   Berjalan otomatis, tetapi bisa dipanggil manual dengan `gc.collect()`.

**Objek PySide punya dua "kehidupan"**: pembungkus Python dan objek C++ milik Qt.
- Widget yang punya *induk* (parent) dimiliki induknya dan baru dihapus saat induknya dihapus.
- `widget.deleteLater()` hanya *menjadwalkan* penghapusan; baru terjadi saat event loop berputar.
- Layout bersarang (`addLayout`) tidak ikut terhapus kalau kita hanya menghapus widget di tingkat atas.

**Kebocoran (leak)** = memori yang seharusnya bebas tetapi masih tertahan, dan *terus bertambah* seiring pemakaian.

---

## 2. Cara mendeteksi (alat yang dibuat)

| Alat | Fungsi |
|---|---|
| `memory_tools.snapshot()` | Foto kondisi: jumlah widget (`QApplication.allWidgets()`), objek Python (`gc.get_objects()`), memori Python (`tracemalloc`), RAM proses (`psutil`). |
| `tes_memori.py` | Uji otomatis: buka semua halaman/dialog berulang-ulang, bandingkan foto awal vs akhir, lalu tunjukkan baris kode yang alokasinya paling bertambah. |
| `TEAMUP_DEBUG_MEMORY=1 python main.py` | Mode debug: tiap pindah halaman, cetak widget / objek / RAM di terminal. |
| `demo_kebocoran.py` | 4 percobaan untuk presentasi: versi bocor vs versi benar. |

**Logika deteksinya:** aplikasi sehat → setelah pemakaian berulang, jumlah widget dan objek *kembali stabil*.
Kalau terus naik → ada yang bocor, lalu `tracemalloc` menunjuk baris kodenya.

> Catatan metodologi: alat ukur tidak boleh mengganggu yang diukur. Di versi pertama, snapshot `tracemalloc`
> dan pembungkus hasil `allWidgets()` ikut terhitung sebagai "kebocoran". Urutan pengambilan foto diperbaiki
> (pemanasan alat → foto awal → ukur awal → siklus → ukur akhir → foto akhir).

---

## 3. Hasil pengukuran: kode asli vs sesudah perbaikan

| Ukuran (100 siklus) | Sebelum | Sesudah |
|---|---|---|
| Widget awal → akhir | 701 → 701 | 734 → 734 |
| Pertumbuhan memori Python | 167 KB (**1,67 KB/siklus**) | 69 KB (**0,69 KB/siklus**) |
| Pertumbuhan RAM proses | +5,2 MB | +2,3 MB |
| Waktu per siklus | 231 ms | 209 ms |

- **Widget tidak bocor** sebelum maupun sesudah. Kode asli sudah memakai `deleteLater()` dengan benar.
- Widget naik 33 (701 → 734) karena dialog sekarang disimpan untuk dipakai ulang. Angkanya **konstan**, bukan bertambah.
- Memori Python turun **59%**, RAM turun sekitar **56%**, dan siklus ±10% lebih cepat.

### Yang diperiksa dan terbukti aman
- Dialog yang dibuat dengan induk (`LogoutDialog(self)`, dll.) tidak menumpuk setelah ditutup.
- Membuka ulang Detail Lomba, Profil Rekan, Detail Postingan, formulir, dan filter QML tidak menambah widget.

---

## 4. Temuan dan perbaikan

### Temuan A — Setiap `.connect()` ke fungsi Python menyisakan ±50 byte
`tracemalloc` menunjuk hampir semua pertumbuhan ke baris `.connect(...)` pada widget yang dibuat ulang
(daftar postingan, kartu, tombol dialog). Percobaan terkontrol (`demo_kebocoran.py`, percobaan 4):

| Gaya sambungan | Sisa memori per widget yang sudah dihapus |
|---|---|
| `connect(self.sinyal.emit)` (bound `.emit`) | ±50 byte |
| `connect(lambda: ...)` menangkap variabel | ±9 byte |
| `connect(self.slot_method)` (`@Slot`) | ±8 byte |
| `connect(self.sinyal)` (**signal → signal**) | ±0,4 byte |

**Perbaikan:** 27 sambungan yang hanya "meneruskan" signal diubah menjadi signal → signal langsung.

```python
# sebelum
self.back_button.clicked.connect(lambda: self.back_clicked.emit())
card.profile_clicked.connect(lambda email: self.profile_clicked.emit(email))
item.clicked.connect(self.post_clicked.emit)
# sesudah
self.back_button.clicked.connect(self.back_clicked)
card.profile_clicked.connect(self.profile_clicked)
item.clicked.connect(self.post_clicked)
```
Kartu yang membawa data (`LombaCard`, `PartnerCard`, `SuggestedPartnerCard`) memakai method `@Slot`
dan menyimpan id/email di objek, sehingga tidak ada variabel yang "ditangkap" lambda.

### Temuan B — Dialog dibangun ulang setiap dibuka
Setiap membuka dialog Batalkan/Hapus/Keluar, belasan widget dan beberapa koneksi baru dibuat.
**Perbaikan: object pooling.** Dialog dibuat sekali (`DashboardPage.get_dialog`), lalu isinya diganti
lewat `ConfirmDialog.set_content(...)`.

### Temuan C — Ikon dan gambar digambar/dimuat ulang terus
`icons.make_icon` merender SVG → pixmap pada setiap panggilan, dan `make_avatar` membaca + menskalakan
foto dari disk setiap kartu dibuat.
**Perbaikan: cache dengan batas.**
- `@lru_cache(maxsize=256)` pada `make_icon`.
- `_pixmap_lebar` dan `_pixmap_foto` memakai `lru_cache(maxsize=64)`; kunci cache memuat *waktu ubah file*
  (`mtime`), jadi foto yang diganti otomatis dimuat ulang.
- Batas `maxsize` mencegah cache menjadi sumber kebocoran baru (lihat percobaan 2 pada demo: dict tanpa batas
  menambah ±123 MB untuk 200 gambar, `lru_cache` hanya ±5 MB).

### Temuan D — `clear_layout` tidak membersihkan layout bersarang
Versi lama hanya memanggil `deleteLater()` pada widget langsung, sehingga widget di dalam sub-layout
tertinggal (tampil dobel di layar). Versi baru bersifat **rekursif**, menyembunyikan widget segera
(`hide` + `setParent(None)`), lalu `deleteLater()`. Salinan fungsi serupa di `PostDetailPage` dan `UploadPage`
dihapus dan memakai satu fungsi yang sama.

### Pembersihan manual (GC)
`MainWindow.handle_logout` sekarang memanggil `helpers.clear_image_cache()` dan `gc.collect()`:
saat user keluar, state-nya dilepas dan pengguna toh sedang menunggu layar splash.

---

## 5. Batasan yang jujur
- Sisa **0,69 KB/siklus** berasal dari ±50 byte per `.connect()` pada kartu yang dibuat ulang. Ini perilaku
  internal PySide; untuk pemakaian wajar (ratusan kali buka halaman) totalnya hanya puluhan KB.
- `tracemalloc` hanya melihat alokasi Python. Memori C++ milik Qt terlihat lewat RAM proses (`psutil`),
  yang nilainya bergoyang kecil karena alokator sistem.
- Uji berjalan tanpa jendela (`QT_QPA_PLATFORM=offscreen`), jadi tidak mengukur memori kartu grafis.

---

## 6. Cara menjalankan

```bash
pip install psutil                  # sekali saja (opsional, untuk membaca RAM)
python tes_memori.py 100            # uji kebocoran, 100 siklus
python demo_kebocoran.py            # 4 percobaan untuk presentasi
TEAMUP_DEBUG_MEMORY=1 python main.py   # pantau memori saat aplikasi berjalan
```

## 7. Kemungkinan pertanyaan saat presentasi

- **Apa bedanya `del obj` dengan `deleteLater()`?** `del` hanya melepas nama di Python; objek C++ yang
  punya induk tetap hidup. `deleteLater()` menjadwalkan penghapusan objek C++ saat event loop berputar.
- **Kenapa tidak semua widget langsung dihapus saat halaman ditutup?** Halaman dibuat sekali dan
  dipakai ulang (efisien); yang dibangun ulang hanya isi yang berubah, dan itu yang dibersihkan.
- **Kapan `gc.collect()` manual masuk akal?** Setelah melepaskan banyak objek sekaligus (logout, menutup
  jendela besar), bukan di dalam loop yang sering berjalan karena menyapu seluruh heap itu mahal.
- **Apakah cache aman?** Hanya jika dibatasi (`maxsize`) dan kuncinya memuat versi data (`mtime`).
