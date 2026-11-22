import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var apiService
    
    property var modelRegistry: null
    property string selectedProvider: ""
    property bool showLoadedOnly: false
    
    Connections {
        target: apiService
        onModelRegistryChanged: {
            modelRegistry = apiService.modelRegistry
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
            
            // Header with filters
            Row {
                width: parent.width
                spacing: 16
                
                Text {
                    text: "Model Registry"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                // Summary
                Text {
                    verticalAlignment: Text.AlignVCenter
                    text: modelRegistry ? ("Total: " + modelRegistry.total_count + " | Loaded: " + modelRegistry.loaded_count) : "Loading..."
                    font.pixelSize: 14
                    color: "#6272a4"
                }
                
                // Filter: Provider
                ComboBox {
                    id: providerFilter
                    width: 200
                    placeholderText: "All Providers"
                    model: ["All"] + (modelRegistry ? Array.from(new Set(modelRegistry.models.map(m => m.provider))) : [])
                    currentIndex: 0
                    onActivated: {
                        selectedProvider = (index === 0) ? "" : model[index]
                    }
                }
                
                // Filter: Loaded only
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
                    onClicked: apiService.refreshAll()
                }
            }
            
            // Models table
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#282a36"
                radius: 8
                border.color: "#44475a"
                border.width: 1
                
                TableView {
                    id: tableView
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true
                    ScrollBar.vertical: ScrollBar { }
                    
                    model: modelRegistry && modelRegistry.models ? modelRegistry.models : []
                    
                    TableViewColumn {
                        role: "name"
                        title: "Model Name"
                        width: 250
                        delegate: ItemDelegate {
                            text: modelData.name
                            font.pixelSize: 13
                            color: "#f8f8f2"
                            highlighted: selected
                        }
                    }
                    
                    TableViewColumn {
                        role: "provider"
                        title: "Provider"
                        width: 150
                        delegate: ItemDelegate {
                            text: modelData.provider
                            font.pixelSize: 13
                            color: "#bd93f9"
                        }
                    }
                    
                    TableViewColumn {
                        role: "size_gb"
                        title: "Size (GB)"
                        width: 100
                        delegate: ItemDelegate {
                            text: modelData.size_gb.toFixed(2)
                            font.pixelSize: 13
                            color: "#f8f8f2"
                        }
                    }
                    
                    TableViewColumn {
                        role: "quantization"
                        title: "Quantization"
                        width: 130
                        delegate: ItemDelegate {
                            text: modelData.quantization
                            font.pixelSize: 13
                            color: "#f8f8f2"
                        }
                    }
                    
                    TableViewColumn {
                        role: "loaded"
                        title: "Status"
                        width: 100
                        delegate: Item {
                            width: parent.width
                            height: parent.height
                            
                            Rectangle {
                                anchors.centerIn: parent
                                width: 80
                                height: 28
                                radius: 14
                                color: modelData.loaded ? "#50fa7b" : "#6272a4"
                                opacity: modelData.loaded ? 1 : 0.5
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.loaded ? "Loaded" : "Available"
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: "#1e1e2e"
                                }
                            }
                        }
                    }
                    
                    TableViewColumn {
                        role: "actions"
                        title: "Actions"
                        width: 120
                        delegate: Item {
                            width: parent.width
                            height: parent.height
                            
                            Row {
                                anchors.centerIn: parent
                                spacing: 8
                                
                                Button {
                                    text: modelData.loaded ? "Unload" : "Load"
                                    width: 70
                                    height: 32
                                    flat: true
                                    onClicked: {
                                        if (modelData.loaded) {
                                            apiService.unload_model(modelData.name)
                                        } else {
                                            apiService.load_model(modelData.name)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Empty state
                Item {
                    anchors.fill: parent
                    visible: !modelRegistry || modelRegistry.total_count === 0
                    
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
                                text: "📦"
                                font.pixelSize: 28
                            }
                        }
                        
                        Text {
                            text: modelRegistry && modelRegistry.error ? "Error loading models" : "No models found"
                            font.pixelSize: 16
                            color: "#6272a4"
                        }
                        
                        Text {
                            text: modelRegistry && modelRegistry.error ? modelRegistry.error : "Models will appear here when loaded"
                            font.pixelSize: 13
                            color: "#44475a"
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }
            
            // Error display
            Rectangle {
                visible: modelRegistry && modelRegistry.error
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
                        text: "Error: " + modelRegistry.error
                        color: "#ff5555"
                        font.pixelSize: 14
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}