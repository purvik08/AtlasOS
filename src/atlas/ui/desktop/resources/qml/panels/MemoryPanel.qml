import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

Item {
    property var apiService
    
    property var conversations: []
    property int selectedConversationIndex: -1
    property string searchQuery: ""
    property var searchResults: []
    property string ragQuery: ""
    property var ragResult: null
    property string ingestFile: ""
    property bool ingesting: false
    
    Connections {
        target: apiService
        onConversationsChanged: {
            conversations = apiService.conversations
        }
        onSearchResultsChanged: {
            searchResults = apiService.searchResults
        }
        onRagResultsChanged: {
            ragResult = apiService.ragResults
        }
    }
    
    Component.onCompleted: {
        apiService.refreshAll()
        // Fetch conversations
        // apiService.fetch_conversations()
    }
    
    ScrollView {
        anchors.fill: parent
        clip: true
        ScrollBar.vertical: ScrollBar { }
        
        Column {
            width: parent.width
            spacing: 20
            anchors.margins: 24
            
            // Header with tabs
            Row {
                width: parent.width
                spacing: 8
                
                Text {
                    text: "Memory & RAG"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Refresh"
                    onClicked: apiService.refreshAll()
                }
            }
            
            // Tab bar
            Row {
                width: parent.width
                spacing: 0
                
                TabButton {
                    text: "Conversations"
                    active: currentTab === 0
                    onClicked: currentTab = 0
                }
                
                TabButton {
                    text: "Search"
                    active: currentTab === 1
                    onClicked: currentTab = 1
                }
                
                TabButton {
                    text: "RAG Query"
                    active: currentTab === 2
                    onClicked: currentTab = 2
                }
                
                TabButton {
                    text: "Documents"
                    active: currentTab === 3
                    onClicked: currentTab = 3
                }
                
                Item { Layout.fillWidth: true }
            }
            
            StackLayout {
                id: contentStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: currentTab
                
                // Conversations Tab
                ConversationTab {
                    apiService: apiService
                    conversations: conversations
                    selectedConversationIndex: selectedConversationIndex
                    onConversationSelected: conversationSelected(index)
                }
                
                // Search Tab
                SearchTab {
                    apiService: apiService
                    searchQuery: searchQuery
                    searchResults: searchResults
                    onQueryChanged: searchQuery = query
                    onSearch: apiService.search_memory(query, 10, 0.0)
                }
                
                // RAG Tab
                RagTab {
                    apiService: apiService
                    ragQuery: ragQuery
                    ragResult: ragResult
                    onQueryChanged: ragQuery = query
                    onQuery: apiService.rag_query(query, "", 5, 0.3)
                }
                
                // Documents Tab
                DocumentsTab {
                    apiService: apiService
                    ingestFile: ingestFile
                    ingesting: ingesting
                    onFileSelected: ingestFile = file
                    onIngest: apiService.ingest_document(file, "desktop", 512, 50)
                }
            }
        }
    }
    
    property int currentTab: 0
    property int selectedConversationIndex: -1
    
    function conversationSelected(index) {
        selectedConversationIndex = index
        // Could open detail view
    }
}

// Tab Button Component
Component {
    id: tabButtonComponent
    Button {
        property bool active: false
        
        Layout.fillWidth: true
        height: 40
        flat: true
        font.pixelSize: 13
        font.bold: active
        color: active ? "#bd93f9" : "#f8f8f2"
        
        background: Rectangle {
            color: active ? "#bd93f9" : "transparent"
            opacity: active ? 0.15 : 0
            radius: 6
            border.color: active ? "#bd93f9" : "transparent"
            border.width: active ? 2 : 0
        }
        
        onClicked: parent.clicked()
    }
}

// Conversations Tab
Component {
    id: conversationTabComponent
    Item {
        property var apiService
        property var conversations: []
        property int selectedConversationIndex: -1
        signal conversationSelected(int index)
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 16
                anchors.margins: 24
                
                // Header with create button
                Row {
                    width: parent.width
                    spacing: 16
                    
                    Text {
                        text: "Conversations"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        verticalAlignment: Text.AlignVCenter
                        text: conversations.length + " conversations"
                        font.pixelSize: 14
                        color: "#6272a4"
                    }
                    
                    Button {
                        text: "+ New Conversation"
                        onClicked: {
                            // Dialog for new conversation title
                            var title = prompt("Enter conversation title:", "New Conversation")
                            if (title) {
                                apiService.create_conversation(title)
                            }
                        }
                    }
                }
                
                // Conversations list
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    
                    ListView {
                        id: conversationsList
                        anchors.fill: parent
                        clip: true
                        model: conversations
                        spacing: 4
                        anchors.margins: 8
                        
                        delegate: ConversationItem {
                            width: parent.width
                            selected: index === selectedConversationIndex
                            onClicked: conversationSelected(index)
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: conversations.length === 0 ? 200 : 0
                            visible: conversations.length === 0
                            
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
                                    text: "No conversations yet"
                                    font.pixelSize: 16
                                    color: "#6272a4"
                                }
                                
                                Button {
                                    text: "Create Conversation"
                                    width: 160
                                    onClicked: {
                                        var title = prompt("Enter conversation title:", "New Conversation")
                                        if (title) {
                                            apiService.create_conversation(title)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Conversation Item Component
Component {
    id: conversationItemComponent
    ItemDelegate {
        property bool selected: false
        width: parent.width
        height: 72
        
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
                
                Rectangle {
                    width: 44
                    height: 44
                    radius: 22
                    color: "#bd93f9"
                    opacity: 0.2
                    
                    Text {
                        anchors.centerIn: parent
                        text: "💬"
                        font.pixelSize: 18
                    }
                }
                
                Column {
                    spacing: 4
                    
                    Text {
                        text: modelData.title || "Untitled"
                        font.pixelSize: 14
                        font.bold: true
                        color: selected ? "#bd93f9" : "#f8f8f2"
                    }
                    
                    Row {
                        spacing: 8
                        
                        Text {
                            text: modelData.message_count + " messages"
                            font.pixelSize: 11
                            color: selected ? "#bd93f9" : "#6272a4"
                        }
                        
                        Text {
                            text: new Date(modelData.created_at).toLocaleString()
                            font.pixelSize: 11
                            color: selected ? "#bd93f9" : "#6272a4"
                        }
                    }
                }
            }
        }
    }
}

// Search Tab
Component {
    id: searchTabComponent
    Item {
        property var apiService
        property string searchQuery: ""
        property var searchResults: []
        signal queryChanged(string query)
        signal search()
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 16
                anchors.margins: 24
                
                // Search input
                Row {
                    width: parent.width
                    spacing: 12
                    
                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        height: 44
                        placeholderText: "Search conversations and documents..."
                        font.pixelSize: 14
                        color: "#f8f8f2"
                        placeholderTextColor: "#6272a4"
                        onAccepted: {
                            searchQuery = text
                            queryChanged(text)
                            apiService.search_memory(text, 10, 0.0)
                        }
                        
                        background: Rectangle {
                            color: "#1e1e2e"
                            radius: 8
                            border.color: "#44475a"
                            border.width: 1
                        }
                    }
                    
                    Button {
                        text: "Search"
                        width: 100
                        enabled: searchInput.text.trim().length > 0
                        onClicked: {
                            searchQuery = searchInput.text
                            queryChanged(searchInput.text)
                            apiService.search_memory(searchInput.text, 10, 0.0)
                        }
                    }
                    
                    Button {
                        text: "Clear"
                        flat: true
                        onClicked: {
                            searchInput.text = ""
                            searchQuery = ""
                            queryChanged("")
                        }
                    }
                }
                
                // Results
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    
                    ListView {
                        anchors.fill: parent
                        clip: true
                        model: searchResults
                        spacing: 4
                        anchors.margins: 8
                        
                        delegate: SearchResultItem {
                            width: parent.width
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: searchResults.length === 0 ? 200 : 0
                            visible: searchResults.length === 0 && searchQuery.length > 0
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: "No results found"
                                    font.pixelSize: 16
                                    color: "#6272a4"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Search Result Item
Component {
    id: searchResultItemComponent
    ItemDelegate {
        width: parent.width
        height: 80
        
        contentItem: Rectangle {
            anchors.fill: parent
            color: "transparent"
            radius: 6
            border.color: "#44475a"
            border.width: 1
            
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 4
                
                Row {
                    spacing: 8
                    
                    Rectangle {
                        width: 28
                        height: 28
                        radius: 6
                        color: "#bd93f9"
                        opacity: 0.2
                        
                        Text {
                            anchors.centerIn: parent
                            text: modelData.type === "message" ? "💬" : "📄"
                            font.pixelSize: 14
                        }
                    }
                    
                    Column {
                        spacing: 2
                        
                        Text {
                            text: modelData.conversation_title || modelData.source || "Unknown"
                            font.pixelSize: 13
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Text {
                            text: modelData.content.substring(0, 100) + (modelData.content.length > 100 ? "..." : "")
                            font.pixelSize: 12
                            color: "#bd93f9"
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        text: (modelData.score * 100).toFixed(0) + "%"
                        font.pixelSize: 11
                        color: "#50fa7b"
                    }
                }
            }
        }
    }
}

// RAG Tab
Component {
    id: ragTabComponent
    Item {
        property var apiService
        property string ragQuery: ""
        property var ragResult: null
        signal queryChanged(string query)
        signal query()
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 16
                anchors.margins: 24
                
                // Query input
                Row {
                    width: parent.width
                    spacing: 12
                    
                    TextInput {
                        id: ragInput
                        Layout.fillWidth: true
                        height: 44
                        placeholderText: "Ask a question... (e.g., 'What is Atlas OS?')"
                        font.pixelSize: 14
                        color: "#f8f8f2"
                        placeholderTextColor: "#6272a4"
                        onAccepted: {
                            ragQuery = text
                            queryChanged(text)
                            apiService.rag_query(text, "", 5, 0.3)
                        }
                        
                        background: Rectangle {
                            color: "#1e1e2e"
                            radius: 8
                            border.color: "#44475a"
                            border.width: 1
                        }
                    }
                    
                    Button {
                        text: "Ask"
                        width: 100
                        enabled: ragInput.text.trim().length > 0
                        onClicked: {
                            ragQuery = ragInput.text
                            queryChanged(ragInput.text)
                            apiService.rag_query(ragInput.text, "", 5, 0.3)
                        }
                    }
                    
                    Button {
                        text: "Clear"
                        flat: true
                        onClicked: {
                            ragInput.text = ""
                            ragQuery = ""
                            queryChanged("")
                        }
                    }
                }
                
                // Results
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    clip: true
                    
                    ScrollView {
                        anchors.fill: parent
                        clip: true
                        ScrollBar.vertical: ScrollBar { }
                        
                        Column {
                            id: ragContent
                            width: parent.width
                            spacing: 16
                            anchors.margins: 24
                            
                            // Context
                            Rectangle {
                                visible: ragResult && ragResult.context
                                Layout.fillWidth: true
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                                padding: 16
                                
                                Column {
                                    spacing: 8
                                    
                                    Row {
                                        spacing: 8
                                        Text {
                                            text: "Context"
                                            font.pixelSize: 14
                                            font.bold: true
                                            color: "#bd93f9"
                                        }
                                        Text {
                                            text: ragResult.context_tokens + " tokens"
                                            font.pixelSize: 12
                                            color: "#6272a4"
                                        }
                                    }
                                    
                                    Text {
                                        text: ragResult.context
                                        font.pixelSize: 13
                                        color: "#f8f8f2"
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                            }
                            
                            // Sources
                            Rectangle {
                                visible: ragResult && ragResult.results && ragResult.results.length > 0
                                Layout.fillWidth: true
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                                padding: 16
                                
                                Column {
                                    spacing: 12
                                    
                                    Text {
                                        text: "Sources"
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "#bd93f9"
                                    }
                                    
                                    Repeater {
                                        model: ragResult.results
                                        
                                        Rectangle {
                                            Layout.fillWidth: true
                                            color: "#1e1e2e"
                                            radius: 6
                                            border.color: "#44475a"
                                            border.width: 1
                                            padding: 12
                                            
                                            Column {
                                                spacing: 4
                                                
                                                Row {
                                                    spacing: 8
                                                    
                                                    Text {
                                                        text: modelData.metadata?.source || "Document"
                                                        font.pixelSize: 12
                                                        font.bold: true
                                                        color: "#f8f8f2"
                                                    }
                                                    
                                                    Text {
                                                        text: (modelData.score * 100).toFixed(1) + "%"
                                                        font.pixelSize: 11
                                                        color: "#50fa7b"
                                                    }
                                                }
                                                
                                                Text {
                                                    text: modelData.content.substring(0, 300) + (modelData.content.length > 300 ? "..." : "")
                                                    font.pixelSize: 12
                                                    color: "#bd93f9"
                                                    wrapMode: Text.Wrap
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // No results state
                            Rectangle {
                                visible: !ragResult
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 16
                                    
                                    Text {
                                        text: "Ask a question to get AI-powered answers"
                                        font.pixelSize: 16
                                        color: "#6272a4"
                                    }
                                    
                                    Text {
                                        text: "Uses your conversation history and documents for context"
                                        font.pixelSize: 13
                                        color: "#44475a"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Documents Tab
Component {
    id: documentsTabComponent
    Item {
        property var apiService
        property string ingestFile: ""
        property bool ingesting: false
        signal fileSelected(string file)
        signal ingest(string file)
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 16
                anchors.margins: 24
                
                // Ingest section
                Rectangle {
                    width: parent.width
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    padding: 24
                    
                    Column {
                        spacing: 16
                        
                        Text {
                            text: "Ingest Document"
                            font.pixelSize: 18
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Text {
                            text: "Upload a text file to add it to your knowledge base for RAG queries."
                            font.pixelSize: 13
                            color: "#6272a4"
                            wrapMode: Text.Wrap
                        }
                        
                        Row {
                            spacing: 12
                            
                            TextInput {
                                id: fileInput
                                Layout.fillWidth: true
                                height: 40
                                placeholderText: "Select a text file..."
                                font.pixelSize: 13
                                color: "#f8f8f2"
                                placeholderTextColor: "#6272a4"
                                readOnly: true
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                            
                            Button {
                                text: "Browse"
                                width: 100
                                onClicked: {
                                    var file = fileDialog.open()
                                    if (file) {
                                        fileInput.text = file
                                        ingestFile = file
                                        fileSelected(file)
                                    }
                                }
                            }
                            
                            Button {
                                text: "Ingest"
                                width: 100
                                enabled: fileInput.text.length > 0 && !ingesting
                                onClicked: {
                                    ingesting = true
                                    ingest(ingestFile)
                                }
                            }
                        }
                        
                        // Progress
                        Rectangle {
                            visible: ingesting
                            height: 8
                            radius: 4
                            color: "#1e1e2e"
                            
                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                width: parent.width * 0.5
                                color: "#bd93f9"
                                radius: 4
                                
                                Behavior on width { NumberAnimation { duration: 500 } }
                            }
                        }
                    }
                }
            }
        }
        
        // File dialog
        FileDialog {
            id: fileDialog
            title: "Select Text File"
            nameFilters: ["Text Files (*.txt *.md *.json *.yaml *.yml)", "All Files (*)"]
            selectExisting: true
            selectFolder: false
        }
    }
}