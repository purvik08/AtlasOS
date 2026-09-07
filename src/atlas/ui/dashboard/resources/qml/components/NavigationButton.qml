import QtQuick
import QtQuick.Controls

Button {
    id: navBtn
    property string navIcon: ""
    property bool active: false

    height: 44
    leftPadding: 16
    rightPadding: 16

    contentItem: Row {
        spacing: 12
        Text {
            text: navBtn.text
            font.pixelSize: 14
            color: navBtn.active ? "#6272a4" : "#f8f8f2"
            font.bold: navBtn.active
            verticalAlignment: Text.AlignVCenter
        }
    }
    background: Rectangle {
        color: navBtn.active ? "#383a46" : "transparent"
        radius: 6
        border.color: navBtn.active ? "#6272a4" : "transparent"
        border.width: navBtn.active ? 2 : 0
    }
}