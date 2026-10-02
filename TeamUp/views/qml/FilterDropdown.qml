// FilterDropdown.qml — padanan FilterPopup + tombol dropdown (views/filter_bar.py)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string buttonText: "Kategori"
    property string popupTitle: "Pilih kategori"
    property var options: []
    property var selected: []          // pilihan yang sedang diterapkan
    property bool single: false        // true = hanya satu pilihan (Urutkan)
    property bool active: false        // tombol berwarna kalau filter aktif
    signal applied(var picked)         // daftar teks yang dicentang ([] = reset)

    function close() { pop.close() }

    implicitWidth: Math.max(150, btnText.implicitWidth + 36)
    implicitHeight: 40

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: root.active ? "#FFE08F" : "white"
        border.color: "#F5A623"; border.width: 1
        AppText {
            id: btnText; anchors.centerIn: parent
            text: root.buttonText + "   " + (pop.visible ? "▲" : "▼")
            color: "#0F2E6B"; font.pixelSize: 14
        }
        MouseArea {
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
            onClicked: pop.visible ? pop.close() : pop.open()
        }
    }

    Popup {
        id: pop
        x: root.width - width; y: root.height + 6   // rata kanan, tepat di bawah tombol
        width: 280; padding: 20
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 16; color: "white"; border.color: "#F5A623" }

        onAboutToShow: {   // isi centang sesuai pilihan yang sedang diterapkan
            for (let i = 0; i < rep.count; i++)
                rep.itemAt(i).checked = root.selected.indexOf(root.options[i]) >= 0
        }

        contentItem: ColumnLayout {
            spacing: 12
            AppText { text: root.popupTitle; font.pixelSize: 16; font.bold: true; color: "#0F2E6B" }
            Repeater {
                id: rep
                model: root.options
                CheckBox {
                    text: modelData
                    onToggled: if (root.single && checked)      // aturan "hanya satu"
                        for (let i = 0; i < rep.count; i++)
                            if (rep.itemAt(i) !== this) rep.itemAt(i).checked = false
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Button {
                    Layout.fillWidth: true; text: "Reset"
                    onClicked: { root.applied([]); pop.close() }
                }
                Button {
                    Layout.fillWidth: true; text: "Terapkan"
                    onClicked: {
                        let picked = []
                        for (let i = 0; i < rep.count; i++)
                            if (rep.itemAt(i).checked) picked.push(root.options[i])
                        root.applied(picked); pop.close()
                    }
                }
            }
        }
    }
}
