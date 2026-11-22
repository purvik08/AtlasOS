import QtQuick
import QtQuick.Controls
import AtlasUI 1.0
import "../components"

Item {
    id: root

    // Scroll to bottom whenever a new message arrives
    Connections {
        target: chatModel
        function onRowsInserted() { scrollTimer.start() }
    }
    Timer { id: scrollTimer; interval: 60; onTriggered: listView.positionViewAtEnd() }

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        // Header row: title + model selector
        Item {
            width: parent.width
            height: 44

            SectionHeader {
                title: "Chat"
                subtitle: "Streaming responses, fully local"
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
            }

            // Active-model pill (right side)
            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                radius: Theme.radiusSm
                color: Theme.bgElevated
                border.color: Theme.accentCyan
                border.width: 1
                width: modelPillText.implicitWidth + 20
                height: 30

                Text {
                    id: modelPillText
                    anchors.centerIn: parent
                    text: "\u25CF  qwen2.5:3b-instruct · :9001"
                    color: Theme.accentCyan
                    font.pixelSize: 12
                    font.family: Theme.fontMono
                }
            }
        }

        // Message list
        Rectangle {
            width: parent.width
            height: parent.height - 44 - 12 - inputRow.height - 12
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.borderSubtle
            border.width: 1
            clip: true

            ListView {
                id: listView
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                model: chatModel
                clip: true

                delegate: Row {
                    width: listView.width
                    spacing: 10
                    layoutDirection: sender === "user" ? Qt.RightToLeft : Qt.LeftToRight

                    // Avatar dot
                    Rectangle {
                        width: 28; height: 28; radius: 14
                        color: sender === "user" ? Theme.accentAmber : Theme.accentCyan
                        Text {
                            anchors.centerIn: parent
                            text: sender === "user" ? "U" : "A"
                            color: Theme.bgPrimary
                            font.pixelSize: 13
                            font.bold: true
                        }
                    }

                    // Bubble
                    Rectangle {
                        width: Math.min(implicitWidth, listView.width * 0.72)
                        height: bubbleText.implicitHeight + 18
                        radius: Theme.radiusMd
                        color: sender === "user" ? Theme.bgElevated : Theme.bgPanel
                        border.color: sender === "user" ? Theme.accentAmber : Theme.borderSubtle
                        border.width: 1

                        Text {
                            id: bubbleText
                            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                            text: model.text
                            color: Theme.textPrimary
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }

                    // Timestamp
                    Text {
                        text: timestamp
                        color: Theme.textMuted
                        font.pixelSize: 11
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                    }
                }

                // Typing indicator row
                Item {
                    visible: false
                    id: typingRow
                    width: listView.width
                    height: 32

                    Connections {
                        target: chatModel
                        function onAssistantStartedTyping() { typingRow.visible = true }
                        function onAssistantFinishedTyping() { typingRow.visible = false }
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 38
                        spacing: 6
                        anchors.verticalCenter: parent.verticalCenter
                        Repeater {
                            model: 3
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: Theme.accentCyan
                                opacity: 0.4
                                SequentialAnimation on opacity {
                                    running: typingRow.visible
                                    loops: Animation.Infinite
                                    PauseAnimation { duration: index * 160 }
                                    NumberAnimation { to: 1.0; duration: 240 }
                                    NumberAnimation { to: 0.4; duration: 240 }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Input row
        Row {
            id: inputRow
            width: parent.width
            spacing: 10

            Rectangle {
                width: parent.width - sendBtn.width - 10
                height: 48
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: inputField.activeFocus ? Theme.accentCyan : Theme.borderSubtle
                border.width: 1

                TextField {
                    id: inputField
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 4 }
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    placeholderText: "Type a message or tap mic…"
                    placeholderTextColor: Theme.textMuted
                    background: Item {}
                    Keys.onReturnPressed: sendBtn.clicked()
                    selectByMouse: true
                    leftPadding: 10; rightPadding: 10
                }
            }

            Rectangle {
                id: sendBtn
                width: 100; height: 48; radius: Theme.radiusMd
                color: Theme.accentCyan
                property bool hovered: false

                Text {
                    anchors.centerIn: parent
                    text: "Send"
                    color: Theme.bgPrimary
                    font.pixelSize: 15
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (inputField.text.trim() === "") return
                        chatModel.sendMessage(inputField.text)
                        inputField.text = ""
                    }
                }
            }
        }
    }
}
