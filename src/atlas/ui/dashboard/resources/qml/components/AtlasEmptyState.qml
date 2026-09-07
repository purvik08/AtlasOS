import QtQuick
import AtlasUI 1.0

/**
 * AtlasEmptyState — Informative empty view placeholder.
 */
Item {
    id: root

    property string iconText: "📦"
    property string title: "No Items Available"
    property string message: "Nothing has been added or discovered yet."
    property string actionText: ""
    signal actionClicked()

    implicitWidth: 320
    implicitHeight: 220

    Column {
        anchors.centerIn: parent
        spacing: 12
        width: Math.min(parent.width - 32, 360)

        Rectangle {
            width: 56
            height: 56
            radius: 28
            color: Theme.bgElevated
            border.color: Theme.borderSubtle
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: root.iconText
                font.pixelSize: 26
            }
        }

        Text {
            text: root.title
            font.pixelSize: 16
            font.bold: true
            font.family: Theme.fontSans
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            width: parent.width
        }

        Text {
            text: root.message
            font.pixelSize: 13
            font.family: Theme.fontSans
            color: Theme.textMuted
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            width: parent.width
        }

        AtlasButton {
            visible: root.actionText !== ""
            text: root.actionText
            variant: "secondary"
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.actionClicked()
        }
    }
}
