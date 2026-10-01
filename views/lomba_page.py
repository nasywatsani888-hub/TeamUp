# views/lomba_page.py — halaman Lomba ("Ayo jelajahi kompetisi!") versi QML
# Kolom tengah dirender oleh QML (views/qml/LombaPage.qml); kolom kanan tidak dipakai (profil
# sudah ada di sidebar). Signal ke luar tidak berubah.
import os
from PySide6.QtCore import QMetaObject, Qt, QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout
from views.content_page import ContentPage
from views.lomba_backend import LombaBackend

QML_FILE = os.path.join(os.path.dirname(__file__), "qml", "LombaPage.qml")


class LombaPage(ContentPage):
    lomba_detail_clicked = Signal(int)   # id lomba

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(0, 0, 0, 0)

        self.quick = QQuickWidget()
        self.backend = LombaBackend(self.quick)   # anak dari quick: ikut dihapus SETELAH QML-nya
        self.quick.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.quick.setClearColor(QColor("white"))
        self.quick.rootContext().setContextProperty("lombaBackend", self.backend)
        self.quick.setSource(QUrl.fromLocalFile(QML_FILE))
        if self.quick.status() != QQuickWidget.Status.Ready:
            for error in self.quick.errors():
                print("QML error:", error.toString())
        layout.addWidget(self.quick)

        # QScrollArea milik ContentPage yang scroll atas-bawah, jadi QML dibuat setinggi
        # isinya (tanpa scroll sendiri): tinggi widget mengikuti implicitHeight QML.
        self.root_item = self.quick.rootObject()   # None kalau QML gagal dimuat (lihat pesan error di atas)
        if self.root_item is not None:
            self.root_item.implicitHeightChanged.connect(self.fit_height)
        self.fit_height()

        # Signal & Slot: QML minta buka detail -> teruskan ke dashboard
        self.backend.detailRequested.connect(self.lomba_detail_clicked.emit)

    def fit_height(self):
        if self.root_item is not None:
            self.quick.setMinimumHeight(int(self.root_item.implicitHeight()))

    # Widget Lifecycle: data di-refresh setiap halaman tampil
    def refresh(self):
        self.backend.reload()

    def on_hide(self):
        if self.root_item is not None:
            QMetaObject.invokeMethod(self.root_item, "closePopups", Qt.ConnectionType.DirectConnection)
