import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * ChatScreen — Real-time AI chat interface with token streaming, model selection, and sessions.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var apiService: typeof apiService !== "undefined" ? apiService : null
    property var chatModel: typeof chatModel !== "undefined" ? chatModel : null
    property var llmModel: typeof llmModel !== "undefined" ? llmModel : null

    property bool isGenerating: false
    property string activeModelName: {
        if (modelSelector.currentText && modelSelector.currentText !== "") {
            return modelSelector.currentText
        }
        if (!llmModel || !llmModel._models) return "default"
        for (var i = 0; i < llmModel._models.length; i++) {
            if (llmModel._models[i].loaded) return llmModel._models[i].name
        }
        return "default"
    }

    Connections {
        target: chatModel
        function onRowsInserted() {
            scrollTimer.restart()
        }
        function onAssistantStartedTyping() {
            isGenerating = true
        }
        function onAssistantFinishedTyping() {
            isGenerating = false
            scrollTimer.restart()
        }
    }

    Timer {
        id: scrollTimer
        interval: 80
        onTriggered: messageList.positionViewAtEnd()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        // 1. Header Bar with Model Selector
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingMd
                anchors.rightMargin: Theme.spacingMd
                spacing: 12

                Text {
                    text: "💬"
                    font.pixelSize: 18
                }

                Text {
                    text: "Atlas OS Assistant"
                    font.pixelSize: 15
                    font.bold: true
                    color: Theme.textPrimary
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "Model:"
                    font.pixelSize: 12
                    font.family: Theme.fontMono
                    color: Theme.textMuted
                }

                // Model Selector ComboBox
                ComboBox {
                    id: modelSelector
                    implicitWidth: 200
                    implicitHeight: 36
                    model: {
                        var list = ["default"]
                        if (llmModel && llmModel._models) {
                            for (var i = 0; i < llmModel._models.length; i++) {
                                list.push(llmModel._models[i].name)
                            }
                        }
                        return list
                    }
                    onActivated: function(index) {
                        if (chatModel) chatModel.setSelectedModel(currentText)
                    }
                }

                AtlasStatusBadge {
                    label: isGenerating ? "GENERATING" : (root.activeModelName !== "default" ? "READY" : "STANDBY")
                    status: isGenerating ? "warning" : (root.activeModelName !== "default" ? "success" : "offline")
                }

                AtlasButton {
                    text: "Clear"
                    variant: "ghost"
                    implicitWidth: 70
                    implicitHeight: 34
                    onClicked: {
                        if (chatModel) chatModel.clear()
                    }
                }
            }
        }

        // 2. Chat Transcript Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border
            border.width: 1
            clip: true

            ListView {
                id: messageList
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingMd
                model: chatModel
                clip: true

                delegate: Row {
                    width: messageList.width
                    spacing: 10
                    layoutDirection: sender === "user" ? Qt.RightToLeft : Qt.LeftToRight

                    // Avatar bubble
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: sender === "user" ? Theme.accent : Theme.accentPurple
                        anchors.top: bubbleContainer.top

                        Text {
                            anchors.centerIn: parent
                            text: sender === "user" ? "U" : "A"
                            font.pixelSize: 13
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }

                    // Message Content Box
                    Rectangle {
                        id: bubbleContainer
                        width: Math.min(Math.max(bubbleText.implicitWidth + 24, 120), messageList.width * 0.76)
                        height: bubbleColumn.implicitHeight + 20
                        radius: Theme.radiusMd
                        color: sender === "user" ? Theme.bgElevated : Theme.bgSecondary
                        border.color: sender === "user" ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Column {
                            id: bubbleColumn
                            anchors {
                                left: parent.left
                                right: parent.right
                                top: parent.top
                                margins: 10
                            }
                            spacing: 4

                            Text {
                                id: bubbleText
                                width: parent.width
                                text: model.text
                                color: Theme.textPrimary
                                font.pixelSize: 14
                                font.family: Theme.fontSans
                                wrapMode: Text.Wrap
                            }

                            Row {
                                spacing: 6
                                anchors.right: parent.right

                                Text {
                                    text: isStreaming ? "generating..." : timestamp
                                    font.pixelSize: 10
                                    font.family: Theme.fontMono
                                    color: isStreaming ? Theme.accentCyan : Theme.textMuted
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Input Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: inputField.activeFocus ? Theme.borderFocus : Theme.border
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                TextField {
                    id: inputField
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.family: Theme.fontSans
                    placeholderText: "Ask Atlas OS anything (runs completely offline)..."
                    placeholderTextColor: Theme.textMuted
                    background: Item {}
                    selectByMouse: true
                    verticalAlignment: TextInput.AlignVCenter
                    leftPadding: 10
                    rightPadding: 10
                    Keys.onReturnPressed: sendAction()
                }

                AtlasButton {
                    text: isGenerating ? "Stop" : "Send"
                    iconText: isGenerating ? "■" : "➤"
                    variant: isGenerating ? "danger" : "primary"
                    implicitWidth: 100
                    implicitHeight: 44
                    enabled: inputField.text.trim().length > 0 || isGenerating
                    onClicked: sendAction()
                }
            }
        }
    }

    function sendAction() {
        if (isGenerating) {
            isGenerating = false
            if (apiService) apiService.cancel_streaming()
            return
        }
        var msg = inputField.text.trim()
        if (msg.length === 0) return
        inputField.text = ""
        if (chatModel) {
            chatModel.sendMessageWithModel(msg, root.activeModelName)
        }
    }
}
