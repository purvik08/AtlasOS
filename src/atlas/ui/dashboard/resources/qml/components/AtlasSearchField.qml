import QtQuick
import QtQuick.Controls
import AtlasUI 1.0

/**
 * AtlasSearchField — Search input with search icon and clear button.
 */
Rectangle {
    id: root

    property alias text: input.text
    property string placeholderText: "Search..."
    signal searchChanged(string query)

    implicitWidth: 280
    implicitHeight: 44
    radius: Theme.radiusSm
    color: Theme.bgPanel
    border.color: input.activeFocus ? Theme.borderFocus : Theme.border
    border.width: 1

    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 10
        spacing: 8

        Text {
            text: "🔍"
            font.pixelSize: 14
            color: Theme.textMuted
            anchors.verticalCenter: parent.verticalCenter
        }

        TextField {
            id: input
            width: parent.width - 24 - (clearBtn.visible ? 28 : 0)
            height: parent.height
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.textPrimary
            font.pixelSize: 14
            font.family: Theme.fontSans
            placeholderText: root.placeholderText
            placeholderTextColor: Theme.textMuted
            background: Item {}
            selectByMouse: true
            onTextChanged: root.searchChanged(text)
        }

        AtlasIconButton {
            id: clearBtn
            visible: input.text.length > 0
            iconText: "✕"
            implicitWidth: 28
            implicitHeight: 28
            anchors.verticalCenter: parent.verticalCenter
            onClicked: {
                input.text = ""
                root.searchChanged("")
            }
        }
    }
}
