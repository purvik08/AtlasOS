import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    property var apiService
    property var appState
    property var chatModel
    property var sessions: []
    property int selectedSessionIndex: -1
    property string newMessage: ""
    property bool isSendingMessage: false
    
    Connections {
        target: apiService
        function onSessions_changed() {
            sessions = apiService.sessions
            // Auto-select first session if available
            if (sessions.length > 0 && selectedSessionIndex === -1) {
                selectedSessionIndex = 0
            }
        }
    }
    
    onSelectedSessionIndexChanged: {
        // Fetch messages for the newly selected session
        if (selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length) {
            const sessionId = sessions[selectedSessionIndex].id
            apiService.fetch_session_messages(sessionId)
        }
    }
    
    Connections {
        target: apiService
        function onChat_message_received(message) {
            // Append AI response to the current session's messages
            if (selectedSessionIndex >= 0 && selectedSessionIndex < sessions.length) {
                const sessionId = sessions[selectedSessionIndex].id
                apiService.fetch_session_messages(sessionId)
            }
            isSendingMessage = false
        }
    }
    
    Connections {
        target: apiService
        function onError_occurred(error) {
            // Reset sending state on error
            isSendingMessage = false
        }
    }
    
    Connections {
        target: apiService
        function onSession_created_signal(sessionData) {
            // New session created, refresh the list
            apiService.refresh_all()
        }
    }
    
    Connections {
        target: apiService
        function onModel_operation_result(model_id, success, error_msg) {
            console.log("Model operation result:", model_id, success, error_msg)
            // Could show a notification to user here
        }
    }
    
    Connections {
        target: apiService
        function onSession_messages_fetched(messages) {
            // Messages fetched, could update chatModel here
        }
    }
    
    Component.onCompleted: {
        apiService.refresh_all()
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
                                apiService.error_occurred("New session creation not implemented yet")
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
                                    apiService.create_session("", "", "", "")
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
                
                // Chat header
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
                        
                        Button {
                            visible: selectedSessionIndex >= 0
                            text: "End Session"
                            flat: true
                            onClicked: {
                                // Delete session
                                apiService.delete_session(sessions[selectedSessionIndex].id)
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
                        anchors.margins: 16
                        
                        // Welcome message when no session selected
                        Rectangle {
                            visible: selectedSessionIndex < 0
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            color: "#282a36"
                            radius: 12
                            border.color: "#44475a"
                            border.width: 1
                            implicitWidth: emptyCol.implicitWidth + 64
                            implicitHeight: emptyCol.implicitHeight + 64

                            Column {
                                id: emptyCol
                                anchors.centerIn: parent
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
                            model: apiService.session_messages
                            
                            MessageBubble {
                                isUser: modelData.role === "user"
                                messageText: modelData.content
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
                            Keys.onReturnPressed: {
                                if (text.trim() && !isSendingMessage) {
                                    // Send message via API
                                    isSendingMessage = true
                                    apiService.send_chat_message(
                                        sessions[selectedSessionIndex].id,
                                        sessions[selectedSessionIndex].model,
                                        text
                                    )
                                    messageInput.text = ""
                                }
                            }
                        }
                        
                        Button {
                            text: "Send"
                            width: 80
                            height: 40
                            enabled: messageInput.text.trim().length > 0 && !isSendingMessage
                            onClicked: {
                                // Send message via API
                                if (messageInput.text.trim()) {
                                    isSendingMessage = true
                                    apiService.send_chat_message(
                                        sessions[selectedSessionIndex].id,
                                        sessions[selectedSessionIndex].model,
                                        messageInput.text
                                    )
                                    messageInput.text = ""
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}