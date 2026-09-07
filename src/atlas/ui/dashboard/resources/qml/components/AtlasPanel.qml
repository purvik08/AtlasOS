import QtQuick
import QtQuick.Layouts
import AtlasUI 1.0

/**
 * AtlasPanel — Structured panel with title header and action bar.
 */
Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property alias headerActions: actionsContainer.data
    default property alias content: bodyContainer.data

    color: Theme.bgPanel
    radius: Theme.radiusMd
    border.color: Theme.border
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: Theme.bgPrimary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingMd
                anchors.rightMargin: Theme.spacingMd
                spacing: 12

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: root.title
                        font.pixelSize: 15
                        font.bold: true
                        font.family: Theme.fontSans
                        color: Theme.textPrimary
                    }
                    Text {
                        visible: root.subtitle !== ""
                        text: root.subtitle
                        font.pixelSize: 12
                        font.family: Theme.fontSans
                        color: Theme.textMuted
                    }
                }

                Row {
                    id: actionsContainer
                    spacing: 8
                }
            }
        }

        // Body
        Item {
            id: bodyContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
