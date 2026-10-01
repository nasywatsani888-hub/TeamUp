// LombaPage.qml — padanan lama views/lomba_page.py + card_grid.py + filter_bar.py
// Tanpa ScrollView: tingginya (implicitHeight) dibaca Python agar QScrollArea
// milik ContentPage yang menggulung halaman.
import QtQuick
import QtQuick.Layouts

Item {
    id: page
    // minimal 560 supaya popup filter (±300 px) selalu muat walau daftar kosong
    implicitHeight: Math.max(620, col.implicitHeight)

    function closePopups() {
        filterPanel.close()
        urutanDropdown.close()
    }

    ColumnLayout {
        id: col
        width: page.width
        spacing: 20

        // Banner kuning: maskot + judul (oranye), selebar halaman
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 84
            color: "#FFF1C9"
            RowLayout {
                anchors.left: parent.left; anchors.leftMargin: lombaBackend.contentMargin
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Image {
                    visible: lombaBackend.mascotUrl !== ""
                    source: lombaBackend.mascotUrl
                    sourceSize.width: 56
                    fillMode: Image.PreserveAspectFit
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                }
                AppText { visible: lombaBackend.mascotUrl === ""; text: "🦜"; font.pixelSize: 36 }
                AppText {
                    text: "Ayo jelajahi kompetisi!"
                    font.pixelSize: 26; font.bold: true; color: "#F5A623"
                }
            }
        }

        // Baris filter (rata kanan): Filter Lomba + Urutkan
        RowLayout {
            Layout.fillWidth: true
            Layout.rightMargin: lombaBackend.contentMargin
            spacing: 12
            Item { Layout.fillWidth: true }
            FilterPanel {
                id: filterPanel
                groups: lombaBackend.filterGroups
                selected: lombaBackend.selectedFilters
                activeCount: lombaBackend.activeFilterCount
                onApplied: (filters) => lombaBackend.setFilters(filters)
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
