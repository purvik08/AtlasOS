import QtQuick
import QtQuick.Controls
import AtlasUI 1.0

/**
 * AtlasTextField — Clean input field with focus outlines.
 */
Rectangle {
    id: root

    property alias text: input.text
    property alias placeholderText: input.placeholderText
    property alias echoMode: input.echoMode
    property bool isMono: false
    signal accepted()

    implicitWidth: 260
    implicitHeight: 44
    radius: Theme.radiusSm
    color: Theme.bgPanel
    border.color: input.activeFocus ? Theme.borderFocus : Theme.border
    border.width: 1

    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    TextField {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.textPrimary
        font.pixelSize: 14
        font.family: root.isMono ? Theme.fontMono : Theme.fontSans
        placeholderTextColor: Theme.textMuted
        background: Item {}
        selectByMouse: true
        onAccepted: root.accepted()
    }
}
