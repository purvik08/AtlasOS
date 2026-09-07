import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    property var apiService
    property var appState
    property var llmModel
    property var modelRegistry: null
    property string selectedProvider: ""
    property bool showLoadedOnly: false
    
    Connections {
        target: apiService
        function onModel_registry_changed() {
            modelRegistry = apiService.model_registry
        }
    }
    
    Connections {
        target: apiService
        function onProviders_changed() {
            // Update provider filter if needed
        }
    }
    
    Connections {
        target: apiService
        function onModel_operation_result(model_id, success, error_msg) {
            console.log("Model operation:", model_id, success ? "success" : "failed", error_msg)
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
            
            // Header with filters
            Row {
                width: parent.width
                spacing: 16
                
                Text {
                    text: "Model Registry"
                    font.pixelSize: 28
                    font.bold: true
                    color: Theme.textPrimary
                }
                
                Item { Layout.fillWidth: true }
                
                // Summary
                Text {
                    verticalAlignment: Text.AlignVCenter
                    text: modelRegistry ? (modelRegistry.models.filter(m => m.loaded).length + " / " + modelRegistry.models.length + " loaded") : "Loading..."
                    font.pixelSize: 13
                    color: Theme.textMuted
                }
                
                // Filter: Provider
                ComboBox {
                    id: providerFilter
                    width: 200
                    displayText: currentIndex === 0 ? "All Providers" : currentText
                    model: ["All"] + (modelRegistry ? Array.from(new Set(modelRegistry.models.map(m => m.provider))) : [])
                    currentIndex: 0
                    onActivated: {
                        selectedProvider = (index === 0) ? "" : modelRegistry.models[index - 1].provider
                    }
                }
                
                // Filter: Loaded Only
                CheckBox {
                    id: loadedFilter
                    text: "Loaded Only"
                    checked: false
                    onCheckedChanged: {
                        showLoadedOnly = checked
                    }
                }
                
                // Refresh button
                Button {
                    text: "Refresh"
                    onClicked: apiService.refresh_all()
                }
            }
            
            // Models table
            ListView {
                anchors.fill: parent
                clip: true
                model: modelRegistry && modelRegistry.models ? modelRegistry.models : []
                spacing: 4
                anchors.margins: 8
                
                delegate: ItemDelegate {
                    width: parent.width
                    height: 40
                    
                    Row {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8
                        
                        Text {
                            text: modelData.model_id
                            font.pixelSize: 13
                            color: Theme.textPrimary
                        }
                        
                        Text {
                            text: "(" + modelData.provider + ", " + (modelData.quantization || "N/A") + ", " + (modelData.loaded ? "Loaded" : "Available") + ")"
                            font.pixelSize: 11
                            color: Theme.textMuted
                        }
                        
                        Button {
                            text: modelData.loaded ? "Unload" : "Load"
                            width: 70
                            height: 32
                            flat: true
                            onClicked: {
                                if (modelData.loaded) {
                                    apiService.unload_model(modelData.model_id)
                                } else {
                                    apiService.load_model(modelData.model_id)
                                }
                            }
                        }
                    }
                }
            }
            
            // Empty state
            Item {
                anchors.fill: parent
                visible: !modelRegistry || modelRegistry.models.length === 0
                
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
                            text: "📦"
                            font.pixelSize: 28
                        }
                    }
                    
                    Text {
                        text: modelRegistry && modelRegistry.error ? "Error loading models" : "No models found"
                        font.pixelSize: 16
                        color: Theme.textMuted
                    }
                    
                    Text {
                        text: modelRegistry && modelRegistry.error ? modelRegistry.error : "Models will appear here when loaded"
                        font.pixelSize: 13
                        color: Theme.border
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}