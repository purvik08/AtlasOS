import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    property string name
    property var status
    property int modelsCount
    property var lastCheck
    property string error
    signal refreshClicked

    property color statusColor: {
        if (status === "healthy") return "#50fa7b"
        if (status === "degraded") return "#f1fa8c"
        if (status === "unhealthy") return "#ff5555"
        return "#6272a4"
    }

    color: "#282a36"
    radius: 10
    border.color: "#44475a"
    border.width: 1
    Layout.fillWidth: true
    Layout.minimumHeight: 200
    Layout.preferredHeight: 200

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Header
        Row {
            spacing: 12

            // Status indicator
            Rectangle {
                width: 48
                height: 48
                radius: 24
                color: parent.parent.parent.statusColor
                opacity: 0.15
                border.color: parent.parent.parent.statusColor
                border.width: 2

                Text {
                    anchors.centerIn: parent
                    text: parent.parent.parent.parent.name.charAt(0).toUpperCase()
                    font.pixelSize: 20
                    font.bold: true
                    color: parent.parent.parent.statusColor
                }
            }

            Column {
                spacing: 4

                Text {
                    text: parent.parent.parent.name
                    font.pixelSize: 18
                    font.bold: true
                    color: "#f8f8f2"
                }

                // Status badge
                Rectangle {
                    width: statusLabel.implicitWidth + 16
                    height: 24
                    radius: 12
                    color: parent.parent.parent.parent.statusColor
                    opacity: 0.2
                    border.color: parent.parent.parent.parent.statusColor
                    border.width: 1

                    Text {
                        id: statusLabel
                        anchors.centerIn: parent
                        text: parent.parent.parent.parent.parent.status ? parent.parent.parent.parent.parent.status.toUpperCase() : ""
                        font.pixelSize: 11
                        font.bold: true
                        color: parent.parent.parent.parent.statusColor
                    }
                }
            }
        }

        // Refresh button
        Button {
            text: "⟳"
            width: 36
            height: 36
            flat: true
            onClicked: refreshClicked()
        }
    }

    // Divider
    Rectangle {
        x: 0
        y: 120
        width: parent.width
        height: 1
        color: "#44475a"
    }

    // Error display
    Rectangle {
        visible: error !== ""
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        height: 40
        color: "#3d1a1a"
        radius: 6
        border.color: "#ff5555"
        border.width: 1

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 8
            spacing: 8
            Rectangle {
                width: 16
                height: 16
                radius: 8
                color: "#ff5555"
                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: "#f8f8f2"
                    font.bold: true
                    font.pixelSize: 10
                }
            }
            Text {
                text: parent.parent.parent.error
                color: "#ff5555"
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
        }
    }
}