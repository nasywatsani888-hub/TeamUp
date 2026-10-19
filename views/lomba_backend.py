# views/lomba_backend.py — jembatan Python <-> QML untuk halaman Lomba.
# Logika data TETAP di data_store.py; file ini hanya membuka data itu ke QML.
import os
from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, QUrl, Signal, Slot
import config
import data_store
import helpers
import sizes


class ModelLomba(QAbstractListModel):
    """Daftar kartu untuk Repeater QML. Kelebihan dibanding array JavaScript: baris BARU bisa ditambahkan
    (beginInsertRows) tanpa membuang & membangun ulang kartu yang sudah ada. Dengan array biasa, setiap
    'Muat lebih banyak' akan membuat ulang SEMUA kartu (makin lama makin berat)."""
    PERAN_LOMBA = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._data)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == self.PERAN_LOMBA:
            return self._data[index.row()]
        return None

    def roleNames(self):
        return {self.PERAN_LOMBA: b"lomba"}   # di QML dibaca sebagai model.lomba

    def ganti(self, data):
        self.beginResetModel()
        self._data = list(data)
        self.endResetModel()

    def tambah(self, data):
        if not data:
            return
        awal = len(self._data)
        self.beginInsertRows(QModelIndex(), awal, awal + len(data) - 1)
        self._data.extend(data)
        self.endInsertRows()

    def semua(self):
        return list(self._data)


class LombaBackend(QObject):
    changed = Signal()                 # data/filter berubah -> QML otomatis refresh
    detailRequested = Signal(int)      # id lomba (diteruskan jadi lomba_detail_clicked)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = {}               # {kunci_grup: [pilihan]} dari Filter Lomba
        self._order = data_store.URUTAN_LOMBA_DEFAULT
        self.model = ModelLomba(self)    # kartu yang SUDAH dibuat (satu halaman demi satu halaman)
        self._semua = []                 # hasil filter lengkap; kartunya baru dibuat saat diminta
        self._tampil = 0
        self._susun()

    # ---- data untuk QML (property + notify = binding otomatis) ----
    # ---- paginasi: hanya satu halaman kartu dibuat sekaligus (Pertemuan 7: banyak data) ----
    def _susun(self):
        """Hitung ulang hasil filter lalu tampilkan halaman PERTAMA saja."""
        self._semua = data_store.get_lomba_filter(self._filters, self._order)
        self._tampil = 0
        self.model.ganti([])
        self._muat_halaman()

    def _muat_halaman(self):
        awal = self._tampil
        akhir = min(awal + sizes.UKURAN_HALAMAN_LOMBA, len(self._semua))
        baru = []
        for lomba in self._semua[awal:akhir]:
            item = dict(lomba)   # salinan, supaya data asli tidak ikut berubah
            item["poster_url"] = helpers.poster_url(lomba, sizes.LOMBA_CARD_WIDTH, sizes.LOMBA_POSTER_HEIGHT, 20)
            baru.append(item)
        self.model.tambah(baru)   # hanya kartu baru yang dibuat QML
        self._tampil = akhir
        self.changed.emit()

    @Property(list, notify=changed)
    def lomba(self):
        """Daftar lomba yang SEDANG tampil (kompatibel dengan versi lama)."""
        return self.model.semua()

    @Property(QObject, constant=True)
    def modelLomba(self):
        return self.model

    @Property(int, notify=changed)
    def totalLomba(self):
        return len(self._semua)

    @Property(int, notify=changed)
    def jumlahTampil(self):
        return self._tampil

    @Property(int, notify=changed)
    def berikutnya(self):
        return min(sizes.UKURAN_HALAMAN_LOMBA, len(self._semua) - self._tampil)

    @Slot()
    def muatLagi(self):
        self._muat_halaman()

    @Property("QVariantMap", notify=changed)
    def selectedFilters(self):
        return self._filters

    @Property(int, notify=changed)
    def activeFilterCount(self):
        return sum(len([p for p in v if p != "Semua"]) for v in self._filters.values())

    @Property(list, constant=True)
    def filterGroups(self):
        return [{"key": k, "title": t, "options": o, "single": one}
                for k, t, o, one in data_store.FILTER_LOMBA_GRUP]

    @Property(str, notify=changed)
    def selectedOrder(self):
        return self._order

    @Property(list, constant=True)
    def urutanOptions(self):
        return data_store.URUTAN_LOMBA

    @Property(str, constant=True)
    def defaultOrder(self):
        return data_store.URUTAN_LOMBA_DEFAULT

    # ---- ukuran: tetap dari sizes.py supaya satu sumber ----
    @Property(int, constant=True)
    def contentMargin(self):
        return sizes.CONTENT_MARGIN

    @Property(int, constant=True)
    def cardsPerPage(self):
        return sizes.UKURAN_HALAMAN_LOMBA

    @Property(int, constant=True)
    def cardWidth(self):
        return sizes.LOMBA_CARD_WIDTH

    @Property(int, constant=True)
    def cardSpacing(self):
        return sizes.LOMBA_CARD_SPACING

    @Property(int, constant=True)
    def posterHeight(self):
        return sizes.LOMBA_POSTER_HEIGHT

    @Property(str, constant=True)
    def mascotUrl(self):
        """URL assets/burung.png kalau ada; kosong kalau belum ada (QML pakai emoji)."""
        path = os.path.join(config.ASSETS_DIR, "burung.png")
        return QUrl.fromLocalFile(path).toString() if os.path.exists(path) else ""

    # ---- aksi dari QML ----
    @Slot()
    def reload(self):
        """Dipanggil tiap halaman tampil (Widget Lifecycle): data bisa berubah -> mulai lagi dari halaman pertama."""
        self._susun()

    @Slot("QVariantMap")
    def setFilters(self, filters):
        self._filters = {k: list(v) for k, v in filters.items()}
        self._susun()

    @Slot("QVariantList")
    def setOrder(self, picked):
        self._order = picked[0] if picked else data_store.URUTAN_LOMBA_DEFAULT
        self._susun()

    @Slot(int)
    def openDetail(self, lomba_id):
        self.detailRequested.emit(lomba_id)

    @Slot(int, result=str)
    def sisaText(self, days):
        return helpers.format_sisa(days)
