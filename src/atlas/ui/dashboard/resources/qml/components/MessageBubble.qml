import QtQuick

Rectangle {
    property bool isUser: false
    property string messageText: ""

    width: parent.width
    implicitHeight: bubbleRow.implicitHeight + 16

    color: "transparent"

    Row {
        id: bubbleRow
        width: parent.width
        spacing: 8

        Item {
            width: isUser ? (parent.width - bubble.width - 8) : 0
            height: 1
        }

        Rectangle {
            id: bubble
            width: Math.min(parent.width * 0.75, 600)
            color: isUser ? "#bd93f9" : "#282a36"
            radius: 16
            border.color: isUser ? "transparent" : "#44475a"
            border.width: isUser ? 0 : 1
            implicitHeight: bubbleColumn.implicitHeight + 32

            Column {
                id: bubbleColumn
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: 16
                }
                spacing: 4

                Text {
                    text: isUser ? "You" : "Assistant"
                    font.pixelSize: 11
                    font.bold: true
                    color: isUser ? "#1e1e2e" : "#6272a4"
                    width: parent.width
                }

                Text {
                    text: messageText
                    font.pixelSize: 14
                    color: isUser ? "#1e1e2e" : "#f8f8f2"
                    wrapMode: Text.Wrap
                    width: parent.width
                }

                Text {
                    text: new Date().toLocaleTimeString()
                    font.pixelSize: 10
                    color: isUser ? "#1e1e2e" : "#6272a4"
                    opacity: 0.6
                }
            }
        }

        Item {
            width: isUser ? 0 : (parent.width - bubble.width - 8)
            height: 1
        }
    }
}