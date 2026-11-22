import QtQuick
import AtlasUI 1.0

Item {
    id: root
    width: label.implicitWidth + 32
    height: 44
    opacity: 0
    visible: opacity > 0

    function show(message) {
        label.text = message
        opacity = 1
        hideTimer.restart()
    }

    Behavior on opacity { NumberAnimation { duration: 220 } }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.color: Theme.accentCyan
        border.width: 1
    }

    Text {
        id: label
        anchors.centerIn: parent
        color: Theme.textPrimary
        font.pixelSize: 14
    }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: root.opacity = 0
    }
}
