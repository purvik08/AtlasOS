import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    property var apiService
    property var appState
    property var providers: []
    
    Connections {
        target: apiService
        function onProviders_changed() {
            providers = apiService.providers
        }
    }
    
    Connections {
        target: apiService
        function onError_occurred(error) {
            console.log("Providers error:", error)
        }
    }
    
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
                    text: "Provider Health"
                    font.pixelSize: 28
                    font.bold: true
                    color: Theme.textPrimary
                }
                
                Item { Layout.fillWidth: true }
                
                // Refresh button
                Button {
                    text: "Refresh All"
                    onClicked: apiService.refresh_all()
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
                            apiService.refresh_all()
                        }
                    }
                }
                
                // Empty state
                Item {
                    visible: providers.length === 0
                    Layout.columnSpan: 3
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    
                    Column {
                        anchors.centerIn: parent
                        spacing: 16
                        
                        Rectangle {
                            width: 64
                            height: 64
                            radius: 32
                            color: Theme.bgPanel
                            border.color: Theme.border
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
                            color: Theme.textMuted
                        }
                    }
                }
            }
        }
    }
}