import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

Item {
    property var apiService
    
    property var plugins: []
    property string searchQuery: ""
    property string installName: ""
    property string installVersion: ""
    property bool installing: false
    
    Connections {
        target: apiService
        onPluginsChanged: {
            plugins = apiService.plugins
        }
    }
    
    Component.onCompleted: {
        apiService.fetch_plugins()
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
                    text: "Plugins"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Refresh"
                    onClicked: apiService.fetch_plugins()
                }
            }
            
            // Tab bar
            Row {
                width: parent.width
                spacing: 0
                
                TabButton {
                    text: "Installed"
                    active: currentTab === 0
                    onClicked: currentTab = 0
                }
                
                TabButton {
                    text: "Marketplace"
                    active: currentTab === 1
                    onClicked: currentTab = 1
                }
                
                Item { Layout.fillWidth: true }
            }
            
            StackLayout {
                id: contentStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: currentTab
                
                // Installed Plugins Tab
                InstalledPluginsTab {
                    apiService: apiService
                    plugins: plugins
                }
                
                // Marketplace Tab
                MarketplaceTab {
                    apiService: apiService
                    searchQuery: searchQuery
                    installName: installName
                    installVersion: installVersion
                    installing: installing
                    onQueryChanged: searchQuery = query
                    onSearch: {
                        // Search marketplace
                    }
                    onInstall: apiService.install_plugin(name, version)
                }
            }
        }
    }
    
    property int currentTab: 0
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

// Installed Plugins Tab
Component {
    id: installedPluginsTabComponent
    Item {
        property var apiService
        property var plugins: []
        
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
                        text: "Installed Plugins"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        verticalAlignment: Text.AlignVCenter
                        text: plugins.length + " plugins"
                        font.pixelSize: 14
                        color: "#6272a4"
                    }
                    
                    Button {
                        text: "Refresh"
                        onClicked: apiService.fetch_plugins()
                    }
                }
                
                // Plugins grid
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    
                    GridLayout {
                        id: pluginsGrid
                        anchors.fill: parent
                        anchors.margins: 16
                        columns: 3
                        columnSpacing: 16
                        rowSpacing: 16
                        
                        Repeater {
                            model: plugins
                            
                            PluginCard {
                                Layout.fillWidth: true
                                Layout.minimumHeight: 200
                                Layout.preferredHeight: 200
                                
                                name: modelData.name
                                version: modelData.version
                                description: modelData.description
                                author: modelData.author
                                enabled: modelData.enabled
                                onToggle: {
                                    if (modelData.enabled) {
                                        apiService.disable_plugin(modelData.name)
                                    } else {
                                        apiService.enable_plugin(modelData.name)
                                    }
                                }
                                onRemove: {
                                    if (confirm("Remove " + modelData.name + "?")) {
                                        apiService.uninstall_plugin(modelData.name)
                                    }
                                }
                                onUpdate: {
                                    // Update plugin
                                }
                            }
                        }
                        
                        // Empty state
                        Item {
                            visible: plugins.length === 0
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
                                    color: "#1e1e2e"
                                    border.color: "#44475a"
                                    border.width: 1
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: "🧩"
                                        font.pixelSize: 28
                                    }
                                }
                                
                                Text {
                                    text: "No plugins installed"
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

// Plugin Card Component
Component {
    id: pluginCardComponent
    Rectangle {
        property string name
        property string version
        property string description
        property string author
        property bool enabled
        signal toggle()
        signal remove()
        signal update()
        
        color: "#282a36"
        radius: 10
        border.color: "#44475a"
        border.width: 1
        Layout.fillWidth: true
        Layout.minimumHeight: 200
        Layout.preferredHeight: 200
        
        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12
            
            // Header
            Row {
                spacing: 12
                
                // Plugin icon
                Rectangle {
                    width: 48
                    height: 48
                    radius: 12
                    color: "#bd93f9"
                    opacity: 0.15
                    border.color: "#bd93f9"
                    border.width: 2
                    
                    Text {
                        anchors.centerIn: parent
                        text: name.charAt(0).toUpperCase()
                        font.pixelSize: 18
                        font.bold: true
                        color: "#bd93f9"
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
                    
                    Text {
                        text: "v" + version
                        font.pixelSize: 12
                        color: "#6272a4"
                    }
                }
                
                Item { Layout.fillWidth: true }
                
                // Enable/Disable button
                Button {
                    text: enabled ? "Disable" : "Enable"
                    width: 80
                    flat: true
                    onClicked: toggle()
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
                
                StatItem { label: "Author"; value: author }
                StatItem { label: "Version"; value: version }
            }
            
            // Actions
            Row {
                spacing: 8
                
                Button {
                    text: enabled ? "Disable" : "Enable"
                    onClicked: toggle()
                }
                
                Button {
                    text: "Update"
                    flat: true
                    onClicked: update()
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Remove"
                    flat: true
                    color: "#ff5555"
                    onClicked: remove()
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

// Marketplace Tab
Component {
    id: marketplaceTabComponent
    Item {
        property var apiService
        property string searchQuery: ""
        property string installName: ""
        property string installVersion: ""
        property bool installing: false
        signal queryChanged(string query)
        signal search()
        signal install(string name, string version)
        
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
                        text: "Plugin Marketplace"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                }
                
                // Search
                Row {
                    width: parent.width
                    spacing: 12
                    
                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        height: 44
                        placeholderText: "Search plugins..."
                        font.pixelSize: 13
                        color: "#f8f8f2"
                        placeholderTextColor: "#6272a4"
                        onTextChanged: queryChanged(text)
                        
                        background: Rectangle {
                            color: "#1e1e2e"
                            radius: 8
                            border.color: "#44475a"
                            border.width: 1
                            padding: 8
                        }
                    }
                    
                    Button {
                        text: "Search"
                        width: 100
                        onClicked: search()
                    }
                }
                
                // Marketplace results
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
                        model: marketplaceResults
                        spacing: 8
                        anchors.margins: 8
                        
                        delegate: MarketplaceItem {
                            width: parent.width
                            onInstall: install(name, version)
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: marketplaceResults.length === 0 ? 200 : 0
                            visible: marketplaceResults.length === 0
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: "No plugins found"
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
    
    property var marketplaceResults: [
        { name: "system-monitor", version: "1.0.0", description: "System monitoring dashboard", author: "Atlas Team" },
        { name: "weather-widget", version: "2.1.0", description: "Weather forecast widget", author: "Community" },
        { name: "network-tools", version: "1.2.3", description: "Network diagnostics tools", author: "Atlas Team" },
        { name: "log-viewer", version: "1.1.0", description: "Advanced log viewer", author: "Community" },
    ]
}

// Marketplace Item
Component {
    id: marketplaceItemComponent
    Rectangle {
        property string name
        property string version
        property string description
        property string author
        signal install(string name, string version)
        
        Layout.fillWidth: true
        height: 120
        color: "#282a36"
        radius: 8
        border.color: "#44475a"
        border.width: 1
        Layout.fillWidth: true
        
        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8
            
            Row {
                spacing: 12
                
                Rectangle {
                    width: 48
                    height: 48
                    radius: 12
                    color: "#bd93f9"
                    opacity: 0.15
                    border.color: "#bd93f9"
                    border.width: 2
                    
                    Text {
                        anchors.centerIn: parent
                        text: name.charAt(0).toUpperCase()
                        font.pixelSize: 18
                        font.bold: true
                        color: "#bd93f9"
                    }
                }
                
                Column {
                    spacing: 4
                    
                    Row {
                        spacing: 8
                        
                        Text {
                            text: name
                            font.pixelSize: 16
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Text {
                            text: "v" + version
                            font.pixelSize: 12
                            color: "#6272a4"
                        }
                    }
                    
                    Text {
                        text: "by " + author
                        font.pixelSize: 11
                        color: "#44475a"
                    }
                }
                
                Text {
                    text: description
                    font.pixelSize: 12
                    color: "#bd93f9"
                    wrapMode: Text.Wrap
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Install " + version
                    width: 120
                    onClicked: install(name, version)
                }
            }
        }
    }
}