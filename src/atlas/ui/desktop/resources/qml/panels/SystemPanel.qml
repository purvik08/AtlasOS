import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var systemInfo: null
    
    // Update when signal received
    Connections {
        target: apiService
        onSystemInfoChanged: {
            systemInfo = apiService.systemInfo
        }
    }
    
    // Request initial data
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
                    text: "System Overview"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                // Connection indicator
                Row {
                    spacing: 8
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 5
                        color: apiService.connected ? "#50fa7b" : "#ff5555"
                    }
                    Text {
                        text: apiService.connected ? "Live" : "Offline"
                        font.pixelSize: 13
                        color: apiService.connected ? "#50fa7b" : "#ff5555"
                    }
                }
            }
            
            // Main metrics grid
            GridLayout {
                columns: 3
                columnSpacing: 16
                rowSpacing: 16
                width: parent.width
                
                // CPU Card
                MetricCard {
                    title: "CPU Usage"
                    value: systemInfo ? systemInfo.cpu_usage.toFixed(1) + "%" : "--"
                    icon: "cpu"
                    progress: systemInfo ? systemInfo.cpu_usage / 100 : 0
                    color: "#bd93f9"
                }
                
                // Memory Card
                MetricCard {
                    title: "Memory Usage"
                    value: systemInfo ? systemInfo.memory_usage.toFixed(1) + "%" : "--"
                    icon: "memory"
                    progress: systemInfo ? systemInfo.memory_usage / 100 : 0
                    color: "#6272a4"
                }
                
                // Uptime Card
                MetricCard {
                    title: "Uptime"
                    value: systemInfo ? systemInfo.uptime : "--"
                    icon: "uptime"
                    progress: 0
                    color: "#50fa7b"
                }
                
                // Status Card
                MetricCard {
                    title: "System Status"
                    value: systemInfo ? systemInfo.status : "--"
                    icon: "status"
                    progress: 0
                    color: "#f1fa8c"
                }
            }
            
            // Detailed info section
            Rectangle {
                Layout.fillWidth: true
                color: "#282a36"
                radius: 8
                border.color: "#44475a"
                border.width: 1
                
                Column {
                    width: parent.width
                    spacing: 0
                    
                    // Section header
                    Rectangle {
                        width: parent.width
                        height: 48
                        color: "#1e1e2e"
                        border.color: "#44475a"
                        border.width: 1
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            text: "Details"
                            font.pixelSize: 16
                            font.bold: true
                            color: "#f8f8f2"
                        }
                    }
                    
                    // Detail rows
                    DetailRow {
                        label: "CPU Usage"
                        value: systemInfo ? systemInfo.cpu_usage.toFixed(1) + "%" : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Memory Usage"
                        value: systemInfo ? systemInfo.memory_usage.toFixed(1) + "%" : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Uptime"
                        value: systemInfo ? systemInfo.uptime : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Status"
                        value: systemInfo ? systemInfo.status : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Error"
                        value: (systemInfo && systemInfo.error) ? systemInfo.error : "None"
                    }
                }
            }
            
            // Error display
            Rectangle {
                visible: systemInfo && systemInfo.error
                Layout.fillWidth: true
                color: "#3d1a1a"
                radius: 8
                border.color: "#ff5555"
                border.width: 1
                padding: 16
                
                Row {
                    spacing: 12
                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: "#ff5555"
                        Text {
                            anchors.centerIn: parent
                            text: "!"
                            color: "#f8f8f2"
                            font.bold: true
                        }
                    }
                    Text {
                        text: "Error: " + systemInfo.error
                        color: "#ff5555"
                        font.pixelSize: 14
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}

// Metric Card Component
Component {
    id: metricCardComponent
    Rectangle {
        property string title
        property string value
        property string icon
        property real progress
        property color color
        
        color: "#282a36"
        radius: 10
        border.color: "#44475a"
        border.width: 1
        Layout.fillWidth: true
        Layout.minimumHeight: 140
        Layout.preferredHeight: 140
        
        Column {
            anchors.centerIn: parent
            spacing: 12
            
            // Icon
            Rectangle {
                width: 48
                height: 48
                radius: 12
                color: color
                opacity: 0.2
                
                Text {
                    anchors.centerIn: parent
                    text: icon
                    font.pixelSize: 24
                    color: color
                }
            }
            
            // Value
            Text {
                text: value
                font.pixelSize: 32
                font.bold: true
                color: "#f8f8f2"
            }
            
            // Title
            Text {
                text: title
                font.pixelSize: 13
                color: "#6272a4"
            }
            
            // Progress bar (if progress > 0)
            Rectangle {
                visible: progress > 0
                width: 120
                height: 6
                radius: 3
                color: "#1e1e2e"
                
                Rectangle {
                    width: parent.width * progress
                    height: parent.height
                    radius: 3
                    color: color
                    Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                }
            }
        }
    }
}

// Detail Row Component
Component {
    id: detailRowComponent
    Rectangle {
        property string label
        property string value
        
        color: "transparent"
        height: 44
        border.color: "#44475a"
        border.width: index % 2 === 0 ? 0 : 1
        
        Row {
            anchors.fill: parent
            anchors.margins: 16
            
            Text {
                text: label
                font.pixelSize: 14
                color: "#6272a4"
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: value
                font.pixelSize: 14
                font.bold: true
                color: "#f8f8f2"
            }
        }
    }
}

// MetricCard, DetailRow will be defined inline in Main.qml for simplicity