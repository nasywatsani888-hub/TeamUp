// LombaCard.qml — padanan lama views/lomba_card.py (versi halaman Lomba)
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: card
    property var lomba            // dict dari data_store: judul, kategori, penyelenggara, warna, sisa_hari, id
    signal detailClicked(int id)

    width: lombaBackend.cardWidth
    height: col.implicitHeight
    radius: 20
    color: "#FFE08F"

    ColumnLayout {
        id: col
        width: parent.width
        spacing: 0

        // Poster sementara: blok warna + judul (sudut atas bulat, bawah lurus)
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: lombaBackend.posterHeight
            Rectangle { anchors.fill: parent; radius: 20; color: card.lomba.warna }
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 20; color: card.lomba.warna
            }
            AppText {
                anchors.fill: parent; anchors.margins: 16
                text: card.lomba.judul.toUpperCase()
                color: "white"; font.pixelSize: 20; font.bold: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 14
            Layout.topMargin: 14
            spacing: 6

            Rectangle {   // tag kategori
                color: "#FFD04D"; radius: 12
                implicitWidth: tagText.implicitWidth + 32
                implicitHeight: tagText.implicitHeight + 8
                AppText {
                    id: tagText; anchors.centerIn: parent
                    text: card.lomba.kategori
                    color: "#0F2E6B"; font.pixelSize: 13; font.bold: true
                }
            }
            AppText {
                Layout.fillWidth: true
                text: card.lomba.judul
                wrapMode: Text.WordWrap
                color: "#0F2E6B"; font.pixelSize: 16; font.bold: true
            }
            AppText {
                Layout.fillWidth: true
                text: card.lomba.penyelenggara
                color: "#0F2E6B"; font.pixelSize: 14
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 0
                AppText {
                    text: lombaBackend.sisaText(card.lomba.sisa_hari)
                    color: "#E53935"; font.pixelSize: 13; font.bold: true
                }
                Item { Layout.fillWidth: true }
                Rectangle {   // tombol Lihat Detail
                    radius: 12
                    color: mouse.containsMouse ? "#F5A623" : "#FFB733"
                    implicitWidth: btnText.implicitWidth + 28
                    implicitHeight: btnText.implicitHeight + 16
                    AppText {
                        id: btnText; anchors.centerIn: parent
                        text: "Lihat Detail"
                        color: "white"; font.pixelSize: 13; font.bold: true
                    }
                    MouseArea {
                        id: mouse; anchors.fill: parent
                        hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: card.detailClicked(card.lomba.id)
                    }
                }
            }
        }
    }
}
