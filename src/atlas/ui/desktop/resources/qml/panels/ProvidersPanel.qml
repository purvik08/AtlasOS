import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var providers: []
    
    Connections {
        target: apiService
        onProvidersChanged: {
            providers = apiService.providers
        }
    }
    
    Component.onCompleted: {
        apiService.refreshAll()
    }
    
    ScrollView {
        anchors.fill: parent
        clip: true
        ScrollBar.vertical: ScrollBar { }
        
        Column {
            width: parent.width
            spacing: 20
            anchors.margins: 24
            
            // Header
            Row {
                width: parent.width
                spacing: 16
                
                Text {
                    text: "Provider Health"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                // Refresh button
                Button {
                    text: "Refresh All"
                    onClicked: apiService.refreshAll()
                }
            }
            
            // Providers grid
            GridLayout {
                id: providersGrid
                columns: providers.length > 2 ? 3 : (providers.length > 1 ? 2 : 1)
                columnSpacing: 16
                rowSpacing: 16
                width: parent.width
                
                Repeater {
                    model: providers
                    
                    ProviderCard {
                        Layout.fillWidth: true
                        Layout.minimumHeight: 200
                        Layout.preferredHeight: 200
                        
                        name: modelData.name
                        status: modelData.status
                        modelsCount: modelData.models_count
                        lastCheck: modelData.last_check
                        error: modelData.error
                        onRefreshClicked: {
                            apiService.refreshAll()
                        }
                    }
                }
                
                // Empty state
                Item {
                    visible: providers.length === 0
                    GridLayout.columnSpan: 3
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    
                    Column {
                        anchors.centerIn: parent
                        spacing: 16
                        
                        Rectangle {
                            width: 64
                            height: 64
                            radius: 32
                            color: "#282a36"
                            border.color: "#44475a"
                            border.width: 1
                            
                            Text {
                                anchors.centerIn: parent
                                text: "🔌"
                                font.pixelSize: 28
                            }
                        }
                        
                        Text {
                            text: "No providers configured"
                            font.pixelSize: 16
                            color: "#6272a4"
                        }
                    }
                }
            }
        }
    }
}

// Provider Card Component
Component {
    id: providerCardComponent
    Rectangle {
        property string name
        property var status
        property int modelsCount
        property var lastCheck
        property string error
        signal refreshClicked
        
        color: "#282a36"
        radius: 10
        border.color: "#44475a"
        border.width: 1
        Layout.fillWidth: true
        Layout.minimumHeight: 200
        Layout.preferredHeight: 200
        
        // Status color mapping
        property color statusColor: status === "healthy" ? "#50fa7b" :
                                   status === "degraded" ? "#f1fa8c" :
                                   status === "unhealthy" ? "#ff5555" :
                                   "#6272a4"
        
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
                    color: statusColor
                    opacity: 0.15
                    border.color: statusColor
                    border.width: 2
                    
                    Text {
                        anchors.centerIn: parent
                        text: name.charAt(0).toUpperCase()
                        font.pixelSize: 20
                        font.bold: true
                        color: statusColor
                    }
                }
                
                Column {
                    spacing: 4
                    
                    Text {
                        text: name
                        font.pixelSize: 18
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    // Status badge
                    Rectangle {
                        width: implicitWidth + 16
                        height: 24
                        radius: 12
                        color: statusColor
                        opacity: 0.2
                        border.color: statusColor
                        border.width: 1
                        
                        Text {
                            anchors.centerIn: parent
                            text: status.toUpperCase()
                            font.pixelSize: 11
                            font.bold: true
                            color: statusColor
                            padding: 4
                        }
                    }
                }
                
                Item { Layout.fillWidth: true }
                
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
                width: parent.width
                height: 1
                color: "#44475a"
            }
            
            // Stats grid
            GridLayout {
                columns: 2
                width: parent.width
                rowSpacing: 8
                
                StatItem {
                    label: "Models"
                    value: modelsCount
                }
                
                StatItem {
                    label: "Last Check"
                    value: lastCheck ? (lastCheck.toString ? new Date(lastCheck).toLocaleTimeString() : lastCheck) : "Never"
                }
                
                StatItem {
                    label: "Status"
                    value: status
                }
                
                StatItem {
                    label: "Error"
                    value: error ? "Yes" : "No"
                }
            }
            
            // Error display
            Rectangle {
                visible: error
                width: parent.width
                color: "#3d1a1a"
                radius: 6
                border.color: "#ff5555"
                border.width: 1
                padding: 12
                
                Row {
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
                        text: error
                        color: "#ff5555"
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}

// Stat Item Component
Component {
    id: statItemComponent
    Item {
        property string label
        property var value
        
        width: Layout.fillWidth
        
        Column {
            spacing: 2
            
            Text {
                text: label
                font.pixelSize: 11
                color: "#6272a4"
            }
            
            Text {
                text: value
                font.pixelSize: 16
                font.bold: true
                color: "#f8f8f2"
            }
        }
    }
}