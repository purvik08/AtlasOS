import QtQuick

Row {
    property bool connected: false

    spacing: 8
    Rectangle {
        width: 10
        height: 10
        radius: 5
        color: connected ? "#50fa7b" : "#ff5555"
        Behavior on color { ColorAnimation { duration: 300 } }
    }
    Text {
        text: connected ? "Connected" : "Disconnected"
        font.pixelSize: 12
        color: connected ? "#50fa7b" : "#ff5555"
    }
}