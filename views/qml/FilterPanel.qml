// FilterPanel.qml — tombol "Filter Lomba" + popup berisi grup chip
// (Jenjang, Jenis Lomba, Cakupan, Biaya Pendaftaran, Anggota Tim) + tombol Terapkan.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var groups: []        // [{key, title, options, single}]
    property var selected: ({})    // filter yang sedang diterapkan {key: [pilihan]}
    property int activeCount: 0
    property var draft: ({})       // pilihan sementara di dalam popup
    signal applied(var filters)

    function close() { pop.close() }
    function isOn(key, opt) { return (draft[key] || []).indexOf(opt) >= 0 }
    function toggle(g, opt) {
        let cur = (draft[g.key] || []).slice()
        let i = cur.indexOf(opt)
        if (g.single) cur = (i >= 0 ? [] : [opt])
        else if (i >= 0) cur.splice(i, 1)
        else cur.push(opt)
        let d = Object.assign({}, draft)
        d[g.key] = cur
        draft = d
    }

    implicitWidth: Math.max(160, btnText.implicitWidth + 40)
    implicitHeight: 40

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: root.activeCount > 0 ? "#FFE08F" : "white"
        border.color: "#0F2E6B"; border.width: 1
        AppText {
            id: btnText; anchors.centerIn: parent
            text: "Filter Lomba" + (root.activeCount > 0 ? " (" + root.activeCount + ")" : "")
                  + "   " + (pop.visible ? "▲" : "▼")
            color: "#0F2E6B"; font.pixelSize: 14
        }
        MouseArea {
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
            onClicked: pop.visible ? pop.close() : pop.open()
        }
    }

    Popup {
        id: pop
        x: root.width - width; y: root.height + 6
        width: 520; padding: 24
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 16; color: "white"; border.color: "#D5DCE8" }
        onAboutToShow: root.draft = JSON.parse(JSON.stringify(root.selected))

        contentItem: ColumnLayout {
            spacing: 14
            AppText { text: "Filter Lomba"; font.pixelSize: 16; font.bold: true; color: "#0F2E6B" }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#E5E7EB" }

            GridLayout {
                Layout.fillWidth: true
                columns: 2; columnSpacing: 24; rowSpacing: 14
                Repeater {
                    model: root.groups
                    ColumnLayout {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: 230
                        spacing: 6
                        property var group: modelData
                        AppText { text: group.title; font.pixelSize: 13; font.bold: true; color: "#0F2E6B" }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: group.options
                                Rectangle {
                                    property bool on: root.isOn(group.key, modelData)
                                    radius: 12
                                    color: on ? "#FFB733" : "white"
                                    border.color: on ? "#FFB733" : "#0F2E6B"; border.width: 1
                                    implicitWidth: chipText.implicitWidth + 20
                                    implicitHeight: chipText.implicitHeight + 8
                                    AppText {
                                        id: chipText; anchors.centerIn: parent
                                        text: modelData; font.pixelSize: 11
                                        color: "#0F2E6B"
                                    }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: root.toggle(group, modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Item { Layout.fillWidth: true }
                Button { text: "Reset"; onClicked: { root.applied({}); pop.close() } }
                Button {
                    id: applyBtn
                    text: "Terapkan"
                    onClicked: { root.applied(root.draft); pop.close() }
                    contentItem: AppText {
                        text: applyBtn.text; color: "white"; font.pixelSize: 13; font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        implicitWidth: 100; implicitHeight: 32; radius: 8
                        color: applyBtn.down ? "#0868AF" : "#0A7BCB"
                    }
                }
            }
        }
    }
}
