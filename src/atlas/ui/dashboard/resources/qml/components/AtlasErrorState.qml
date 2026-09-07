import QtQuick
import AtlasUI 1.0

/**
 * AtlasErrorState — Diagnostic error state with retry support.
 */
Item {
    id: root

    property string title: "Connection Error"
    property string errorMessage: "Unable to communicate with the Atlas service."
    property string retryText: "Retry"
    signal retryClicked()

    implicitWidth: 320
    implicitHeight: 220

    Column {
        anchors.centerIn: parent
        spacing: 12
        width: Math.min(parent.width - 32, 380)

        Rectangle {
            width: 56
            height: 56
            radius: 28
            color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
            border.color: Theme.danger
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: "⚠️"
                font.pixelSize: 26
            }
        }

        Text {
            text: root.title
            font.pixelSize: 16
            font.bold: true
            font.family: Theme.fontSans
            color: Theme.danger
            horizontalAlignment: Text.AlignHCenter
            width: parent.width
        }

        Text {
            text: root.errorMessage
            font.pixelSize: 13
            font.family: Theme.fontSans
            color: Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            width: parent.width
        }

        AtlasButton {
            text: root.retryText
            variant: "secondary"
            iconText: "↻"
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.retryClicked()
        }
    }
}
