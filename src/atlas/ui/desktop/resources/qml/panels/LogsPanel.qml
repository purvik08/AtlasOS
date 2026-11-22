import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var logLines: []
    property int maxLines: 1000
    property string filterText: ""
    property string levelFilter: "ALL"
    property bool autoScroll: true
    property bool paused: false
    
    Connections {
        target: apiService
        onLogLinesChanged: {
            if (!paused) {
                logLines = apiService.log_lines
            }
        }
    }
    
    Component.onCompleted: {
        apiService.fetch_logs(1000)
    }
    
    ScrollView {
        anchors.fill: parent
        clip: true
        ScrollBar.vertical: ScrollBar { }
        
        Column {
            width: parent.width
            spacing: 16
            anchors.margins: 24
            
            // Header with controls
            Row {
                width: parent.width
                spacing: 16
                
                Text {
                    text: "Logs"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                // Level filter
                ComboBox {
                    id: levelCombo
                    width: 140
                    model: ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                    currentText: levelFilter
                    onActivated: levelFilter = model[index]
                }
                
                // Search
                TextInput {
                    id: filterInput
                    width: 250
                    height: 36
                    placeholderText: "Filter logs..."
                    font.pixelSize: 13
                    color: "#f8f8f2"
                    placeholderTextColor: "#6272a4"
                    onTextChanged: filterText = text
                    
                    background: Rectangle {
                        color: "#1e1e2e"
                        radius: 6
                        border.color: "#44475a"
                        border.width: 1
                    }
                }
                
                // Auto-scroll toggle
                CheckBox {
                    id: autoScrollCheck
                    text: "Auto-scroll"
                    checked: autoScroll
                    onCheckedChanged: autoScroll = checked
                }
                
                // Pause toggle
                CheckBox {
                    id: pauseCheck
                    text: "Pause"
                    checked: paused
                    onCheckedChanged: paused = checked
                }
                
                Button {
                    text: "Clear"
                    onClicked: {
                        logLines = []
                    }
                }
                
                Button {
                    text: "Refresh"
                    onClicked: apiService.fetch_logs(maxLines)
                }
                
                Button {
                    text: "Export"
                    onClicked: {
                        // Export logs to file
                        var content = logLines.join("\n")
                        // Would need file dialog
                    }
                }
            }
            
            // Log display
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#1e1e2e"
                radius: 8
                border.color: "#44475a"
                border.width: 1
                
                ListView {
                    id: logView
                    anchors.fill: parent
                    clip: true
                    model: filteredLogs
                    spacing: 0
                    anchors.margins: 1
                    
                    delegate: LogLineItem {
                        width: parent.width
                    }
                    
                    // Auto-scroll to bottom
                    onContentYChanged: {
                        if (autoScroll && contentY >= contentHeight - height) {
                            contentY = contentHeight - height
                        }
                    }
                }
            }
        }
    }
    
    property var filteredLogs: []
    
    function filterLogs() {
        var result = []
        for (var i = 0; i < logLines.length; i++) {
            var line = logLines[i]
            var match = true
            
            // Level filter
            if (levelFilter !== "ALL") {
                if (!line.includes("[" + levelFilter + "]")) {
                    match = false
                }
            }
            
            // Text filter
            if (filterText.length > 0) {
                if (!line.toLowerCase().includes(filterText.toLowerCase())) {
                    match = false
                }
            }
            
            if (match) {
                result.push({ line: line, index: i })
            }
        }
        return result
    }
    
    onLogLinesChanged: {
        filteredLogs = filterLogs()
    }
    
    onFilterTextChanged: {
        filteredLogs = filterLogs()
    }
    
    onLevelFilterChanged: {
        filteredLogs = filterLogs()
    }
}

// Log Line Item
Component {
    id: logLineItemComponent
    ItemDelegate {
        property var modelData: { line: "", index: 0 }
        
        width: parent.width
        height: 24
        
        contentItem: Rectangle {
            anchors.fill: parent
            color: index % 2 === 0 ? "#1e1e2e" : "#25252e"
            
            Text {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.line
                font.family: "Monospace"
                font.pixelSize: 12
                color: getLevelColor(modelData.line)
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
            }
        }
        
        function getLevelColor(line) {
            if (line.includes("[ERROR]") || line.includes("[CRITICAL]")) {
                return "#ff5555"
            } else if (line.includes("[WARNING]")) {
                return "#f1fa8c"
            } else if (line.includes("[DEBUG]")) {
                return "#6272a4"
            } else if (line.includes("[INFO]")) {
                return "#50fa7b"
            }
            return "#f8f8f2"
        }
    }
}

// Log Entry Component (for more detailed view)
Component {
    id: logEntryComponent
    Item {
        property var entry: {}
        
        width: parent.width
        height: 60
        
        Rectangle {
            anchors.fill: parent
            color: index % 2 === 0 ? "#1e1e2e" : "#25252e"
            border.color: "#44475a"
            border.width: index % 2 === 0 ? 0 : 1
            
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 4
                
                Row {
                    spacing: 16
                    
                    // Level badge
                    Rectangle {
                        width: 70
                        height: 20
                        radius: 4
                        color: getLevelColor(entry.level)
                        
                        Text {
                            anchors.centerIn: parent
                            text: entry.level
                            font.pixelSize: 10
                            font.bold: true
                            color: "#1e1e2e"
                        }
                    }
                    
                    // Timestamp
                    Text {
                        text: entry.timestamp
                        font.pixelSize: 11
                        font.family: "Monospace"
                        color: "#6272a4"
                    }
                    
                    // Source/module
                    Text {
                        text: entry.module || ""
                        font.pixelSize: 11
                        color: "#bd93f9"
                    }
                    
                    Item { Layout.fillWidth: true }
                }
                
                // Message
                Text {
                    text: entry.message
                    font.family: "Monospace"
                    font.pixelSize: 12
                    color: "#f8f8f2"
                    wrapMode: Text.Wrap
                }
                
                function getLevelColor(level) {
                    switch (level) {
                        case "CRITICAL":
                        case "ERROR": return "#ff5555"
                        case "WARNING": return "#f1fa8c"
                        case "DEBUG": return "#6272a4"
                        case "INFO": return "#50fa7b"
                        default: return "#44475a"
                    }
                }
            }
        }
    }
}