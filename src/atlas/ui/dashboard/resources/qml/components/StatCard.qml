import QtQuick
import AtlasUI 1.0

Rectangle {
    id: root
    property string label: ""
    property string value: ""
    property color accent: Theme.accentCyan

    radius: Theme.radiusMd
    color: Theme.bgPanel
    border.color: Theme.borderSubtle
    border.width: 1
    implicitHeight: 92

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 6

        Text {
            text: root.label
            color: Theme.textMuted
            font.pixelSize: 13
        }
        Text {
            text: root.value
            color: root.accent
            font.pixelSize: 26
            font.bold: true
            font.family: Theme.fontMono
        }
    }
}
