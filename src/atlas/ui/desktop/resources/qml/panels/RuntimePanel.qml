import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var runtimeStatus: {}
    property var services: []
    property var tasks: []
    property bool runtimeRunning: false
    property bool starting: false
    property bool stopping: false
    
    Connections {
        target: apiService
        onRuntimeStatusChanged: {
            runtimeStatus = apiService.runtime_status
            runtimeRunning = runtimeStatus.running
        }
    }
    
    Component.onCompleted: {
        apiService.runtime_status()
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
                    text: "Runtime"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                // Runtime control buttons
                Button {
                    text: runtimeRunning ? "Stop Runtime" : "Start Runtime"
                    enabled: !starting && !stopping
                    onClicked: {
                        if (runtimeRunning) {
                            stopping = true
                            apiService.runtime_stop()
                        } else {
                            starting = true
                            apiService.runtime_start()
                        }
                    }
                }
                
                Button {
                    text: "Restart"
                    flat: true
                    enabled: runtimeRunning && !starting && !stopping
                    onClicked: {
                        stopping = true
                        apiService.runtime_stop()
                        // Would need to chain start after stop
                    }
                }
                
                Button {
                    text: "Refresh"
                    onClicked: apiService.runtime_status()
                }
            }
            
            // Status card
            Rectangle {
                width: parent.width
                color: runtimeRunning ? "#1a3d1a" : "#3d1a1a"
                radius: 10
                border.color: runtimeRunning ? "#50fa7b" : "#ff5555"
                border.width: 2
                padding: 24
                
                Row {
                    spacing: 24
                    
                    // Status indicator
                    Column {
                        spacing: 8
                        
                        Rectangle {
                            width: 80
                            height: 80
                            radius: 40
                            color: runtimeRunning ? "#50fa7b" : "#ff5555"
                            opacity: 0.2
                            border.color: runtimeRunning ? "#50fa7b" : "#ff5555"
                            border.width: 3
                            
                            Text {
                                anchors.centerIn: parent
                                text: runtimeRunning ? "▶" : "■"
                                font.pixelSize: 36
                                color: runtimeRunning ? "#50fa7b" : "#ff5555"
                                font.bold: true
                            }
                        }
                        
                        Text {
                            text: runtimeRunning ? "Running" : "Stopped"
                            font.pixelSize: 22
                            font.bold: true
                            color: runtimeRunning ? "#50fa7b" : "#ff5555"
                        }
                    }
                    
                    // Runtime info
                    Column {
                        spacing: 16
                        
                        Row {
                            spacing: 32
                            
                            RuntimeStat {
                                label: "Uptime"
                                value: runtimeStatus.uptime || "N/A"
                            }
                            
                            RuntimeStat {
                                label: "Version"
                                value: runtimeStatus.version || "N/A"
                            }
                            
                            RuntimeStat {
                                label: "PID"
                                value: runtimeStatus.pid || "N/A"
                            }
                        }
                        
                        Row {
                            spacing: 32
                            
                            RuntimeStat {
                                label: "Services"
                                value: runtimeStatus.services_count || services.length
                            }
                            
                            RuntimeStat {
                                label: "Tasks"
                                value: runtimeStatus.tasks_count || tasks.length
                            }
                            
                            RuntimeStat {
                                label: "Memory"
                                value: runtimeStatus.memory_usage || "N/A"
                            }
                        }
                    }
                }
            }
            
            // Services section
            Rectangle {
                width: parent.width
                color: "#282a36"
                radius: 10
                border.color: "#44475a"
                border.width: 1
                padding: 24
                
                Column {
                    spacing: 16
                    
                    Text {
                        text: "Services"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    GridLayout {
                        id: servicesGrid
                        columns: services.length > 2 ? 3 : (services.length > 1 ? 2 : 1)
                        columnSpacing: 16
                        rowSpacing: 16
                        width: parent.width
                        
                        Repeater {
                            model: services
                            
                            ServiceCard {
                                Layout.fillWidth: true
                                Layout.minimumHeight: 180
                                Layout.preferredHeight: 180
                                
                                name: modelData.name
                                status: modelData.status
                                description: modelData.description
                                dependencies: modelData.dependencies
                                uptime: modelData.uptime
                            }
                        }
                        
                        // Empty state
                        Item {
                            visible: services.length === 0
                            GridLayout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.preferredHeight: 150
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: "No services registered"
                                    font.pixelSize: 16
                                    color: "#6272a4"
                                }
                            }
                        }
                    }
                }
            }
            
            // Tasks section
            Rectangle {
                visible: tasks.length > 0
                width: parent.width
                color: "#282a36"
                radius: 10
                border.color: "#44475a"
                border.width: 1
                padding: 24
                
                Column {
                    spacing: 16
                    
                    Text {
                        text: "Background Tasks"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: tasks
                        spacing: 8
                        
                        delegate: TaskItem {
                            width: parent.width
                        }
                    }
                }
            }
        }
    }
}

// Runtime Stat Component
Component {
    id: runtimeStatComponent
    Item {
        property string label
        property string value
        
        width: Layout.fillWidth
        
        Column {
            spacing: 4
            
            Text {
                text: label
                font.pixelSize: 12
                color: "#6272a4"
            }
            
            Text {
                text: value
                font.pixelSize: 20
                font.bold: true
                color: "#f8f8f2"
            }
        }
    }
}

// Service Card Component
Component {
    id: serviceCardComponent
    Rectangle {
        property string name
        property string status
        property string description
        property var dependencies
        property string uptime
        
        color: "#282a36"
        radius: 10
        border.color: "#44475a"
        border.width: 1
        Layout.fillWidth: true
        Layout.minimumHeight: 180
        Layout.preferredHeight: 180
        
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
                        font.pixelSize: 18
                        font.bold: true
                        color: statusColor
                    }
                }
                
                Column {
                    spacing: 4
                    
                    Text {
                        text: name
                        font.pixelSize: 16
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
                
                // Restart button
                Button {
                    text: "⟳"
                    width: 36
                    height: 36
                    flat: true
                    onClicked: {
                        // Restart service
                    }
                }
            }
            
            // Divider
            Rectangle {
                width: parent.width
                height: 1
                color: "#44475a"
            }
            
            // Description
            Text {
                text: description
                font.pixelSize: 12
                color: "#bd93f9"
                wrapMode: Text.Wrap
            }
            
            // Divider
            Rectangle {
                width: parent.width
                height: 1
                color: "#44475a"
            }
            
            // Meta info
            GridLayout {
                columns: 2
                width: parent.width
                rowSpacing: 8
                
                StatItem {
                    label: "Dependencies"
                    value: dependencies ? dependencies.length : 0
                }
                
                StatItem {
                    label: "Uptime"
                    value: uptime || "N/A"
                }
                
                StatItem {
                    label: "Status"
                    value: status
                }
                
                StatItem {
                    label: "Health"
                    value: status === "healthy" ? "✓ Healthy" : 
                           status === "degraded" ? "⚠ Degraded" : "✗ Unhealthy"
                }
            }
        }
    }
}

// Task Item Component
Component {
    id: taskItemComponent
    ItemDelegate {
        property string name
        property string status
        property string schedule
        property string last_run
        property string next_run
        property int run_count
        property int error_count
        
        width: parent.width
        height: 80
        
        contentItem: Rectangle {
            anchors.fill: parent
            color: "transparent"
            radius: 6
            border.color: "#44475a"
            border.width: 1
            
            Row {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 16
                
                // Status indicator
                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: status === "running" ? "#50fa7b" :
                           status === "pending" ? "#f1fa8c" :
                           status === "completed" ? "#bd93f9" :
                           status === "failed" ? "#ff5555" : "#6272a4"
                }
                
                Column {
                    spacing: 4
                    
                    Text {
                        text: name
                        font.pixelSize: 14
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Row {
                        spacing: 16
                        
                        Text {
                            text: "Schedule: " + schedule
                            font.pixelSize: 11
                            color: "#6272a4"
                        }
                        
                        Text {
                            text: "Runs: " + run_count
                            font.pixelSize: 11
                            color: "#6272a4"
                        }
                        
                        Text {
                            text: "Errors: " + error_count
                            font.pixelSize: 11
                            color: error_count > 0 ? "#ff5555" : "#6272a4"
                        }
                    }
                }
                
                Item { Layout.fillWidth: true }
                
                // Status badge
                Rectangle {
                    width: implicitWidth + 16
                    height: 24
                    radius: 12
                    color: status === "running" ? "#50fa7b" :
                           status === "pending" ? "#f1fa8c" :
                           status === "completed" ? "#bd93f9" :
                           status === "failed" ? "#ff5555" : "#6272a4"
                    opacity: 0.2
                    border.color: status === "running" ? "#50fa7b" :
                                  status === "pending" ? "#f1fa8c" :
                                  status === "completed" ? "#bd93f9" :
                                  status === "failed" ? "#ff5555" : "#6272a4"
                    border.width: 1
                    
                    Text {
                        anchors.centerIn: parent
                        text: status.toUpperCase()
                        font.pixelSize: 10
                        font.bold: true
                        color: status === "running" ? "#50fa7b" :
                               status === "pending" ? "#f1fa8c" :
                               status === "completed" ? "#bd93f9" :
                               status === "failed" ? "#ff5555" : "#6272a4"
                    }
                }
            }
        }
    }
}

// Runtime Stat Component (reusable)
Component {
    id: runtimeStatComponent
    Item {
        property string label
        property string value
        
        width: Layout.fillWidth
        
        Column {
            spacing: 4
            
            Text {
                text: label
                font.pixelSize: 12
                color: "#6272a4"
            }
            
            Text {
                text: value
                font.pixelSize: 20
                font.bold: true
                color: "#f8f8f2"
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