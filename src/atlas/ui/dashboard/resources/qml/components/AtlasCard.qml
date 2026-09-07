import QtQuick
import AtlasUI 1.0

/**
 * AtlasCard — Standard container card with subtle depth and clean borders.
 */
Rectangle {
    id: root

    property alias content: contentContainer.data
    property color cardColor: Theme.bgPanel
    property color borderColor: Theme.border
    property bool interactive: false
    signal clicked()

    radius: Theme.radiusMd
    color: interactive && mouseArea.containsMouse ? Theme.bgElevated : cardColor
    border.color: interactive && mouseArea.containsMouse ? Theme.borderFocus : borderColor
    border.width: 1

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    Item {
        id: contentContainer
        anchors.fill: parent
        anchors.margins: Theme.spacingMd
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.interactive
        hoverEnabled: root.interactive
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
