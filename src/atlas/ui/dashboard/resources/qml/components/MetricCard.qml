import QtQuick
import QtQuick.Layouts
import AtlasUI 1.0

/**
 * MetricCard — Telemetry visual card with animated progress indicator.
 */
Rectangle {
    id: root

    property string title: "Metric"
    property string value: "--"
    property string icon: ""
    property real progress: 0.0
    property color accentColor: Theme.accentCyan

    color: Theme.bgPanel
    radius: Theme.radiusMd
    border.color: Theme.border
    border.width: 1
    Layout.fillWidth: true
    Layout.minimumHeight: 140
    Layout.preferredHeight: 140

    Column {
        anchors.fill: parent
        anchors.margins: Theme.spacingMd
        spacing: 10

        Row {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 32
                height: 32
                radius: Theme.radiusSm
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.15)

                Text {
                    anchors.centerIn: parent
                    text: root.icon
                    font.pixelSize: 16
                }
            }

            Text {
                text: root.title
                font.pixelSize: 13
                font.family: Theme.fontSans
                font.bold: true
                color: Theme.textSecondary
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: root.value
            font.pixelSize: 26
            font.bold: true
            font.family: Theme.fontMono
            color: Theme.textPrimary
        }

        Item { Layout.fillHeight: true }

        // Progress track
        Rectangle {
            visible: root.progress > 0.0
            width: parent.width
            height: 5
            radius: 2.5
            color: Theme.bgElevated

            Rectangle {
                width: Math.max(0, Math.min(parent.width, parent.width * root.progress))
                height: parent.height
                radius: parent.radius
                color: root.accentColor

                Behavior on width {
                    NumberAnimation { duration: 400; easing.type: Easing.OutCubic }
                }
            }
        }
    }
}