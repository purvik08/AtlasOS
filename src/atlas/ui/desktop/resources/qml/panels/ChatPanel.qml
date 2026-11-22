import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var sessions: []
    property int selectedSessionIndex: -1
    property string newMessage: ""
    property var availableModels: []
    property string selectedModel: "qwen3-0.6b"
    property bool skipThinking: true
    property bool showModelSelector: false
    property string newMessage: ""
    
    Connections {
        target: apiService
        function onSessions_changed() {
            sessions = apiService.sessions
        }
        function onModels_changed() {
            // Handle models update
        }
    }
    
    Component.onCompleted: {
        apiService.refreshAll()
        // Load saved model preference
        var savedModel = localStorage.getItem("selectedModel")
        if (savedModel) {
            selectedModel = savedModel
        }
        // Set default model to qwen3-0.6b if no saved preference
        if (!localStorage.getItem("selectedModel")) {
            selectedModel = "qwen3-0.6b"
        }
    }
    
    // Split view: Sessions list on left, chat on right
    RowLayout {
        anchors.fill: parent
        spacing: 0
        
        // Sessions list sidebar
        Rectangle {
            id: sessionsSidebar
            Layout.preferredWidth: 320
            Layout.maximumWidth: 400
            Layout.minimumWidth: 280
            Layout.fillHeight: true
            color: "#282a36"
            border.color: "#44475a"
            border.width: 1
            
            Column {
                anchors.fill: parent
                spacing: 0
                
                // Header
                Rectangle {
                    width: parent.width
                    height: 56
                    color: "#1e1e2e"
                    border.color: "#44475a"
                    border.width: 1
                    
                    Row {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12
                        
                        Text {
                            text: "Chat Sessions"
                            font.pixelSize: 16
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        Text {
                            text: sessions.length
                            font.pixelSize: 12
                            color: "#6272a4"
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        Button {
                            text: "+ New"
                            width: 70
                            height: 32
                            onClicked: {
                                // Create new session dialog would go here
                                apiService.errorOccurred.emit("New session creation not implemented yet")
                            }
                        }
                    }
                }
                
                // Sessions list
                ListView {
                    id: sessionsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: sessions
                    spacing: 4
                    anchors.margins: 8
                    
                    delegate: SessionItem {
                        width: parent.width
                        selected: index === selectedSessionIndex
                        onClicked: {
                            selectedSessionIndex = index
                        }
                    }
                    
                    // Empty state
                    footer: Item {
                        width: parent.width
                        height: sessions.length === 0 ? 200 : 0
                        visible: sessions.length === 0
                        
                        Column {
                            anchors.centerIn: parent
                            spacing: 16
                            
                            Rectangle {
                                width: 64
                                height: 64
                                radius: 32
                                color: "#1e1e2e"
                                border.color: "#44475a"
                                border.width: 1
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: "💬"
                                    font.pixelSize: 28
                                }
                            }
                            
                            Text {
                                text: "No active sessions"
                                font.pixelSize: 16
                                color: "#6272a4"
                            }
                            
                            Button {
                                text: "Create Session"
                                width: 140
                                onClicked: {
                                    apiService.errorOccurred.emit("Session creation not implemented yet")
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // Chat area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e2e"
            border.color: "#44475a"
            border.width: 1
            
            Column {
                anchors.fill: parent
                spacing: 0
                
                // Chat header with model selector
                Rectangle {
                    width: parent.width
                    height: 56
                    color: "#282a36"
                    border.color: "#44475a"
                    border.width: 1
                    
                    Row {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12
                        
                        Rectangle {
                            visible: selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length
                            width: 40
                            height: 40
                            radius: 20
                            color: "#bd93f9"
                            opacity: 0.2
                            
                            Text {
                                anchors.centerIn: parent
                                text: sessions[selectedSessionIndex].provider.charAt(0).toUpperCase()
                                font.pixelSize: 16
                                font.bold: true
                                color: "#bd93f9"
                            }
                        }
                        
                        Column {
                            visible: selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length
                            spacing: 2
                            
                            Text {
                                text: sessions[selectedSessionIndex].provider + " / " + sessions[selectedSessionIndex].model
                                font.pixelSize: 14
                                font.bold: true
                                color: "#f8f8f2"
                            }
                            
                            Text {
                                text: "ID: " + sessions[selectedSessionIndex].id.substring(0, 12) + "..."
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                        }
                        
                        Item {
                            visible: selectedSessionIndex < 0
                            Layout.fillWidth: true
                            
                            Text {
                                anchors.centerIn: parent
                                text: "Select a session to start chatting"
                                font.pixelSize: 14
                                color: "#6272a4"
                            }
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        // Model selector dropdown
                        Rectangle {
                            visible: selectedSessionIndex >= 0
                            Layout.fillWidth: true
                            height: 36
                            color: "#282a36"
                            radius: 8
                            border.color: "#44475a"
                            border.width: 1
                            
                            Row {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8
                                
                                Text {
                                    text: "Model:"
                                    font.pixelSize: 12
                                    color: "#6272a4"
                                }
                                
                                ComboBox {
                                    id: modelCombo
                                    width: 200
                                    height: 32
                                    model: availableModels
                                    currentText: selectedModel
                                    onActivated: {
                                        selectedModel = model[index]
                                        localStorage.setItem("selectedModel", selectedModel)
                                    }
                                }
                                
                                Item { Layout.fillWidth: true }
                                
                                // Skip thinking checkbox
                                CheckBox {
                                    checked: skipThinking
                                    text: "Skip thinking (faster)"
                                    onCheckedChanged: {
                                        skipThinking = checked
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Messages area
                ScrollView {
                    id: messagesScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical: ScrollBar { }
                    
                    Column {
                        id: messagesColumn
                        width: parent.width
                        spacing: 12
                        
                        // Welcome message when no session selected
                        Rectangle {
                            visible: selectedSessionIndex < 0
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            color: "#282a36"
                            radius: 12
                            border.color: "#44475a"
                            border.width: 1
                            padding: 32
                            
                            Column {
                                spacing: 16
                                
                                Text {
                                    text: "💬"
                                    font.pixelSize: 48
                                }
                                
                                Text {
                                    text: "Select a session from the left"
                                    font.pixelSize: 18
                                    font.bold: true
                                    color: "#f8f8f2"
                                }
                                
                                Text {
                                    text: "or create a new one to start chatting"
                                    font.pixelSize: 14
                                    color: "#6272a4"
                                }
                            }
                        }
                        
                        // Messages for selected session
                        Repeater {
                            visible: selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length
                            model: 5  // Placeholder - would be actual messages from session
                            
                            MessageBubble {
                                isUser: index % 2 === 0
                                text: index % 2 === 0 ? "User message " + (index + 1) : "AI response " + (index + 1)
                            }
                        }
                    }
                }
                
                // Message input
                Rectangle {
                    visible: selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length
                    width: parent.width
                    height: 80
                    color: "#282a36"
                    border.color: "#44475a"
                    border.width: 1
                    
                    Row {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12
                        
                        TextArea {
                            id: messageInput
                            Layout.fillWidth: true
                            height: 56
                            placeholderText: "Type a message..."
                            font.pixelSize: 14
                            color: "#f8f8f2"
                            selectionColor: "#bd93f9"
                            background: Rectangle {
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                            }
                            onAccepted: {
                                if (text.trim()) {
                                    // Send message
                                    sendMessage()
                                    messageInput.text = ""
                                }
                            }
                        }
                        
                        // Skip thinking checkbox
                        CheckBox {
                            checked: skipThinking
                            text: "Skip thinking"
                            onCheckedChanged: {
                                skipThinking = checked
                            }
                        }
                        
                        Button {
                            text: "Send"
                            width: 80
                            height: 40
                            enabled: messageInput.text.trim().length > 0
                            onClicked: {
                                sendMessage()
                                messageInput.text = ""
                            }
                        }
                    }
                }
            }
        }
    }
}

// Session Item Component
Component {
    id: sessionItemComponent
    ItemDelegate {
        property bool selected: false
        width: parent.width
        height: 64
        
        contentItem: Rectangle {
            anchors.fill: parent
            color: selected ? "#bd93f9" : "transparent"
            opacity: selected ? 0.15 : 1
            radius: 6
            border.color: selected ? "#bd93f9" : "transparent"
            border.width: selected ? 2 : 0
            
            Row {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                
                // Provider indicator
                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: "#bd93f9"
                    opacity: 0.2
                    
                    Text {
                        anchors.centerIn: parent
                        text: modelData.provider.charAt(0).toUpperCase()
                        font.pixelSize: 14
                        font.bold: true
                        color: "#bd93f9"
                    }
                }
                
                Column {
                    spacing: 2
                    
                    Text {
                        text: modelData.provider + " / " + modelData.model
                        font.pixelSize: 13
                        font.bold: true
                        color: selected ? "#bd93f9" : "#f8f8f2"
                    }
                    
                    Text {
                        text: modelData.message_count + " messages • " + new Date(modelData.created_at).toLocaleTimeString()
                        font.pixelSize: 11
                        color: selected ? "#bd93f9" : "#6272a4"
                    }
                }
            }
        }
    }
}

// Message Bubble Component
Component {
    id: messageBubbleComponent
    Item {
        property bool isUser
        property string text
        
        width: parent.width
        height: implicitHeight
        
        Row {
            width: parent.width
            spacing: 8
            
            Item {
                Layout.fillWidth: true
                visible: !isUser
            }
            
            Rectangle {
                width: Math.min(parent.width * 0.75, 600)
                color: isUser ? "#bd93f9" : "#282a36"
                radius: 16
                border.color: isUser ? "transparent" : "#44475a"
                border.width: isUser ? 0 : 1
                padding: 16
                
                Column {
                    spacing: 4
                    
                    Text {
                        text: isUser ? "You" : "Assistant"
                        font.pixelSize: 11
                        font.bold: true
                        color: isUser ? "#1e1e2e" : "#6272a4"
                    }
                    
                    Text {
                        text: text
                        font.pixelSize: 14
                        color: isUser ? "#1e1e2e" : "#f8f8f2"
                        wrapMode: Text.Wrap
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
                Layout.fillWidth: true
                visible: isUser
            }
        }
    }
}