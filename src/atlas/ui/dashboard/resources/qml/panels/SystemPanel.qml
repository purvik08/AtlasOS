import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    property var apiService
    property var appState
    property var systemInfo: null
    
    // Update when signal received
    Connections {
        target: apiService
        function onSystem_info_changed() {
            systemInfo = apiService.system_info
        }
    }
    
    // Request initial data
    Component.onCompleted: {
        apiService.refresh_all()
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
                    color: Theme.textPrimary
                }
                
                Item { Layout.fillWidth: true }
                
                // Connection indicator
                Row {
                    spacing: 8
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 5
                        color: apiService.connected ? Theme.success : Theme.danger
                    }
                    Text {
                        text: apiService.connected ? "Live" : "Offline"
                        font.pixelSize: 13
                        color: apiService.connected ? Theme.success : Theme.danger
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
                    value: systemInfo ? systemInfo.cpu_percent.toFixed(1) + "%" : "--"
                    icon: "cpu"
                    progress: systemInfo ? systemInfo.cpu_percent / 100 : 0
                    color: Theme.accentPurple
                }
                
                // Memory Card
                MetricCard {
                    title: "Memory Usage"
                    value: systemInfo ? systemInfo.memory_percent.toFixed(1) + "%" : "--"
                    icon: "memory"
                    progress: systemInfo ? systemInfo.memory_percent / 100 : 0
                    color: Theme.accent
                }
                
                // Uptime Card
                MetricCard {
                    title: "Uptime"
                    value: systemInfo ? formatUptime(systemInfo.uptime_seconds) : "--"
                    icon: "uptime"
                    progress: 0
                    color: Theme.success
                }
                
                // Status Card
                MetricCard {
                    title: "System Status"
                    value: systemInfo ? systemInfo.status : "--"
                    icon: "status"
                    progress: 0
                    color: Theme.warning
                }
            }
            
            // Detailed info section
            Rectangle {
                Layout.fillWidth: true
                color: Theme.bgPanel
                radius: Theme.radiusMd
                border.color: Theme.border
                border.width: 1
                
                Column {
                    width: parent.width
                    spacing: 0
                    
                    // Section header
                    Rectangle {
                        width: parent.width
                        height: 48
                        color: Theme.bgPrimary
                        border.color: Theme.border
                        border.width: 1
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            text: "Details"
                            font.pixelSize: 16
                            font.bold: true
                            color: Theme.textPrimary
                        }
                    }
                    
                    // Detail rows
                    DetailRow {
                        label: "CPU Usage"
                        value: systemInfo ? systemInfo.cpu_percent.toFixed(1) + "%" : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Memory Usage"
                        value: systemInfo ? systemInfo.memory_percent.toFixed(1) + "%" : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Memory Used"
                        value: systemInfo ? (systemInfo.memory_used_gb.toFixed(1) + " GB / " + systemInfo.memory_total_gb.toFixed(1) + " GB") : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Disk Usage"
                        value: systemInfo ? systemInfo.disk_percent.toFixed(1) + "%" : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Uptime"
                        value: systemInfo ? formatUptime(systemInfo.uptime_seconds) : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Status"
                        value: systemInfo ? systemInfo.status : "Loading..."
                    }
                    
                    DetailRow {
                        label: "Error"
                        value: (systemInfo && systemInfo.error && systemInfo.error !== "") ? systemInfo.error : "None"
                    }
                }
            }
            
            // Error display
            Rectangle {
                visible: systemInfo && systemInfo.error && systemInfo.error !== ""
                Layout.fillWidth: true
                implicitHeight: errorRow.implicitHeight + 32
                color: "#3d1a1a"
                radius: Theme.radiusMd
                border.color: Theme.danger
                border.width: 1
                
                Row {
                    id: errorRow
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 16
                    }
                    spacing: 12
                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: Theme.danger
                        Text {
                            anchors.centerIn: parent
                            text: "!"
                            color: Theme.textPrimary
                            font.bold: true
                        }
                    }
                    Text {
                        text: "Error: " + systemInfo.error
                        color: Theme.danger
                        font.pixelSize: 14
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
    
    function formatUptime(seconds) {
        if (!seconds) return "--"
        var days = Math.floor(seconds / 86400)
        var hours = Math.floor((seconds % 86400) / 3600)
        var minutes = Math.floor((seconds % 3600) / 60)
        if (days > 0) return days + "d " + hours + "h " + minutes + "m"
        if (hours > 0) return hours + "h " + minutes + "m"
        return minutes + "m"
    }
}