import QtQuick
import AtlasUI 1.0

/**
 * AtlasLoadingIndicator — Lightweight pulsing hardware-friendly spinner.
 */
Item {
    id: root

    property int size: 24
    property color color: Theme.accentCyan
    property bool running: visible

    implicitWidth: size
    implicitHeight: size

    Rectangle {
        id: ring
        anchors.centerIn: parent
        width: parent.size
        height: parent.size
        radius: parent.size / 2
        color: "transparent"
        border.color: root.color
        border.width: Math.max(2, root.size / 8)

        SequentialAnimation on scale {
            running: root.running
            loops: Animation.Infinite
            NumberAnimation { from: 0.85; to: 1.15; duration: 600; easing.type: Easing.InOutQuad }
            NumberAnimation { from: 1.15; to: 0.85; duration: 600; easing.type: Easing.InOutQuad }
        }

        SequentialAnimation on opacity {
            running: root.running
            loops: Animation.Infinite
            NumberAnimation { from: 0.4; to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
            NumberAnimation { from: 1.0; to: 0.4; duration: 600; easing.type: Easing.InOutQuad }
        }
    }
}
