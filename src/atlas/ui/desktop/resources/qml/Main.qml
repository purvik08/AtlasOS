import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: root
    width: 1200
    height: 800
    minimumWidth: 800
    minimumHeight: 600
    visible: true
    title: "Atlas OS System Desktop"
    
    property bool sidebarOpen: true
    property int currentTab: 0
    
    // Color palette
    property color bgPrimary: "#1e1e2e"
    property color bgSecondary: "#282a36"
    property color bgTertiary: "#383a46"
    property color accent: "#6272a4"
    property color accentHover: "#7a8bd1"
    property color textPrimary: "#f8f8f2"
    property color textSecondary: "#bd93f9"
    property color success: "#50fa7b"
    property color warning: "#f1fa8c"
    property color danger: "#ff5555"
    property color border: "#44475a"
    
    // Navigation button component
    Component {
        id: navigationButtonComponent
        Button {
            property string icon
            property bool active: false
            
            Layout.fillWidth: true
            height: 44
            leftPadding: 16
            rightPadding: 16
            contentItem: Row {
                spacing: 12
                Text {
                    text: parent.text
                    font.pixelSize: 14
                    color: parent.active ? accent : textPrimary
                    font.bold: parent.active
                    verticalAlignment: Text.AlignVCenter
                }
            }
            background: Rectangle {
                color: parent.active ? bgTertiary : "transparent"
                radius: 6
                border.color: parent.active ? accent : "transparent"
                border.width: parent.active ? 2 : 0
            }
            onClicked: parent.clicked()
        }
    }
    
    // Connection status component
    Component {
        id: connectionStatusComponent
        Row {
            spacing: 8
            Rectangle {
                width: 10
                height: 10
                radius: 5
                color: connected ? "#50fa7b" : "#ff5555"
                Behavior on color { ColorAnimation { duration: 300 } }
            }
            Text {
                text: connected ? "Connected" : "Disconnected"
                font.pixelSize: 12
                color: connected ? "#50fa7b" : "#ff5555"
            }
        }
    }
    
    // Start auto-refresh on load
    Component.onCompleted: {
        apiService.startAutoRefresh()
    }
    
    // Cleanup on close
    onClosing: {
        apiService.shutdown()
    }
    
    // Main layout with sidebar
    RowLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 0
        
        // Sidebar
        Rectangle {
            id: sidebar
            Layout.preferredWidth: sidebarOpen ? 220 : 0
            Layout.fillHeight: true
            color: bgSecondary
            border.color: border
            border.width: sidebarOpen ? 1 : 0
            opacity: sidebarOpen ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
            Behavior on Layout.preferredWidth { NumberAnimation { duration: 200 } }
            
            Column {
                Layout.fillHeight: true
                width: parent.width
                spacing: 0
                
                // Logo/Title
                Rectangle {
                    width: parent.width
                    height: 60
                    color: bgPrimary
                    border.color: border
                    border.width: 1
                    
                    Row {
                        anchors.centerIn: parent
                        spacing: 10
                        
                        Rectangle {
                            width: 32
                            height: 32
                            radius: 8
                            color: accent
                            
                            Text {
                                anchors.centerIn: parent
                                text: "A"
                                font.pixelSize: 18
                                font.bold: true
                                color: textPrimary
                            }
                        }
                        
                        Text {
                            verticalAlignment: Text.AlignVCenter
                            text: "Atlas OS"
                            font.pixelSize: 16
                            font.bold: true
                            color: textPrimary
                        }
                    }
                }
                
                // Navigation buttons
                Column {
                    spacing: 4
                    anchors.margins: 12
                    
                    NavigationButton {
                        text: "System"
                        icon: "system"
                        active: currentTab === 0
                        onClicked: { currentTab = 0; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Models"
                        icon: "models"
                        active: currentTab === 1
                        onClicked: { currentTab = 1; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Providers"
                        icon: "providers"
                        active: currentTab === 2
                        onClicked: { currentTab = 2; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Chat"
                        icon: "chat"
                        active: currentTab === 3
                        onClicked: { currentTab = 3; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Memory"
                        icon: "memory"
                        active: currentTab === 4
                        onClicked: { currentTab = 4; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Network"
                        icon: "network"
                        active: currentTab === 5
                        onClicked: { currentTab = 5; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Voice"
                        icon: "voice"
                        active: currentTab === 6
                        onClicked: { currentTab = 6; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Plugins"
                        icon: "plugins"
                        active: currentTab === 7
                        onClicked: { currentTab = 7; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Config"
                        icon: "config"
                        active: currentTab === 8
                        onClicked: { currentTab = 8; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Logs"
                        icon: "logs"
                        active: currentTab === 9
                        onClicked: { currentTab = 9; drawer.close() }
                    }
                    
                    NavigationButton {
                        text: "Runtime"
                        icon: "runtime"
                        active: currentTab === 10
                        onClicked: { currentTab = 10; drawer.close() }
                    }
                }
                
                // Connection status at bottom
                Item {
                    Layout.fillHeight: true
                }
                
                ConnectionStatus {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 20
                    connected: apiService.connected
                }
            }
        }
        
        // Main content area with tabs
        StackLayout {
            id: contentStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: currentTab
            
            // System Panel
            SystemPanel {
                apiService: apiService
            }
            
            // Models Panel
            ModelsPanel {
                apiService: apiService
            }
            
            // Providers Panel
            ProvidersPanel {
                apiService: apiService
            }
            
            // Chat Panel
            ChatPanel {
                apiService: apiService
            }
            
            // Memory Panel
            MemoryPanel {
                apiService: apiService
            }
            
            // Network Panel
            NetworkPanel {
                apiService: apiService
            }
            
            // Voice Panel
            VoicePanel {
                apiService: apiService
            }
            
            // Plugins Panel
            PluginsPanel {
                apiService: apiService
            }
            
            // Config Panel
            ConfigPanel {
                apiService: apiService
            }
            
            // Logs Panel
            LogsPanel {
                apiService: apiService
            }
            
            // Runtime Panel
            RuntimePanel {
                apiService: apiService
            }
        }
    }
    
// Mobile drawer for small screens
    Drawer {
        id: drawer
        width: 220
        height: parent.height
        dragMargin: width
        onOpened: sidebarOpen = true
        onClosed: sidebarOpen = false
        
        Rectangle {
            anchors.fill: parent
            color: bgSecondary
            border.color: border
            border.width: 1
        }
    }
    }