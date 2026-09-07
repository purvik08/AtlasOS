import QtQuick
import AtlasUI 1.0

/**
 * AtlasIconButton — Compact icon/action button for headers and lists.
 */
Rectangle {
    id: root

    property string iconText: ""
    property string tooltip: ""
    property color iconColor: Theme.textSecondary
    property color activeColor: Theme.accentCyan
    property bool active: false
    signal clicked()

    implicitWidth: 40
    implicitHeight: 40
    radius: Theme.radiusSm

    color: active ? Qt.rgba(0, 229, 255, 0.12) : (mouseArea.pressed ? Theme.bgSurface : (mouseArea.containsMouse ? Theme.bgElevated : "transparent"))
    border.color: active ? Theme.accentCyan : (mouseArea.containsMouse ? Theme.border : "transparent")
    border.width: 1

    Behavior on color { ColorAnimation { duration: Theme.animFast } }

    Text {
        anchors.centerIn: parent
        text: root.iconText
        font.pixelSize: 18
        color: root.active ? root.activeColor : (mouseArea.containsMouse ? Theme.textPrimary : root.iconColor)
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
