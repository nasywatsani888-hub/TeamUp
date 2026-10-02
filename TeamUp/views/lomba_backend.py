# views/lomba_backend.py — jembatan Python <-> QML untuk halaman Lomba.
# Logika data TETAP di data_store.py; file ini hanya membuka data itu ke QML.
import os
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
import config
import data_store
import helpers
import sizes


class LombaBackend(QObject):
    changed = Signal()                 # data/filter berubah -> QML otomatis refresh
    detailRequested = Signal(int)      # id lomba (diteruskan jadi lomba_detail_clicked)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = {}               # {kunci_grup: [pilihan]} dari Filter Lomba
        self._order = data_store.URUTAN_LOMBA_DEFAULT

    # ---- data untuk QML (property + notify = binding otomatis) ----
    @Property(list, notify=changed)
    def lomba(self):
        return data_store.get_lomba_filter(self._filters, self._order)

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
        """Dipanggil tiap halaman tampil (Widget Lifecycle)."""
        self.changed.emit()

    @Slot("QVariantMap")
    def setFilters(self, filters):
        self._filters = {k: list(v) for k, v in filters.items()}
        self.changed.emit()

    @Slot("QVariantList")
    def setOrder(self, picked):
        self._order = picked[0] if picked else data_store.URUTAN_LOMBA_DEFAULT
        self.changed.emit()

    @Slot(int)
    def openDetail(self, lomba_id):
        self.detailRequested.emit(lomba_id)

    @Slot(int, result=str)
    def sisaText(self, days):
        return helpers.format_sisa(days)
