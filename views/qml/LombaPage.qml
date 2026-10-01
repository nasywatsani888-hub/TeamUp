// LombaPage.qml — padanan lama views/lomba_page.py + card_grid.py + filter_bar.py
// Tanpa ScrollView: tingginya (implicitHeight) dibaca Python agar QScrollArea
// milik ContentPage yang menggulung halaman.
import QtQuick
import QtQuick.Layouts

Item {
    id: page
    // minimal 560 supaya popup filter (±300 px) selalu muat walau daftar kosong
    implicitHeight: Math.max(560, col.implicitHeight)

    function closePopups() {
        kategoriDropdown.close()
        urutanDropdown.close()
    }

    ColumnLayout {
        id: col
        width: page.width
        spacing: 20

        Item { Layout.preferredHeight: 8 }

        // Judul: maskot + judul (oranye)
        RowLayout {
            Layout.leftMargin: lombaBackend.contentMargin
            spacing: 12
            Image {
                visible: lombaBackend.mascotUrl !== ""
                source: lombaBackend.mascotUrl
                sourceSize.width: 64
                fillMode: Image.PreserveAspectFit
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
            }
            AppText { visible: lombaBackend.mascotUrl === ""; text: "🦜"; font.pixelSize: 40 }
            AppText {
                text: "Ayo jelajahi kompetisi!"
                font.pixelSize: 30; font.bold: true; color: "#F5A623"
            }
        }
        AppText {
            Layout.leftMargin: lombaBackend.contentMargin
            text: lombaBackend.lomba.length + " lomba aktif yang terverifikasi"
            font.pixelSize: 14; color: "#1F2937"
        }

        // FilterBar (rata kanan)
        RowLayout {
            Layout.fillWidth: true
            Layout.rightMargin: lombaBackend.contentMargin
            spacing: 12
            Item { Layout.fillWidth: true }
            FilterDropdown {
                id: kategoriDropdown
                buttonText: "Kategori" + (lombaBackend.selectedCategories.length
                            ? " (" + lombaBackend.selectedCategories.length + ")" : "")
                popupTitle: "Pilih kategori"
                options: lombaBackend.kategoriOptions
                selected: lombaBackend.selectedCategories
                active: lombaBackend.selectedCategories.length > 0
                onApplied: (picked) => lombaBackend.setCategories(picked)
            }
            FilterDropdown {
                id: urutanDropdown
                buttonText: "Urutkan: " + lombaBackend.selectedOrder
                popupTitle: "Urutkan"
                single: true
                options: lombaBackend.urutanOptions
                selected: [lombaBackend.selectedOrder]
                active: lombaBackend.selectedOrder !== lombaBackend.defaultOrder
                onApplied: (picked) => lombaBackend.setOrder(picked)
            }
        }

        // Grid kartu: Flow pindah baris otomatis sesuai lebar (pengganti CardGrid).
        Flow {
            Layout.fillWidth: true
            Layout.leftMargin: lombaBackend.contentMargin
            Layout.rightMargin: lombaBackend.contentMargin
            spacing: lombaBackend.cardSpacing
            Repeater {
                model: lombaBackend.lomba
                LombaCard {
                    lomba: modelData
                    onDetailClicked: (id) => lombaBackend.openDetail(id)
                }
            }
        }

        AppText {
            visible: lombaBackend.lomba.length === 0
            Layout.leftMargin: lombaBackend.contentMargin
            text: "Belum ada lomba yang cocok dengan filter ini."
            font.pixelSize: 15; color: "#6B7C93"
        }

        Item { Layout.preferredHeight: 28 }
    }
}
