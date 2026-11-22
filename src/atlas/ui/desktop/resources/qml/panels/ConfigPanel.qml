import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

Item {
    property var apiService
    
    property var config: {}
    property string editKey: ""
    property string editValue: ""
    property bool editing: false
    property string newApiKeyName: ""
    property var apiKeys: []
    
    Connections {
        target: apiService
        // Config would come from API
    }
    
    Component.onCompleted: {
        // Load config from file or API
        loadConfig()
    }
    
    function loadConfig() {
        // Load from file or API
        // For now, use default values
        config = {
            "log_level": "INFO",
            "data_dir": "./data",
            "models_dir": "./models",
            "plugins_dir": "./plugins",
            "configs_dir": "./configs",
            "logs_dir": "./logs",
            "ui": {
                "desktop_enabled": true,
                "kiosk_enabled": false,
                "style": "Material"
            },
            "ai": {
                "default_role": "auto",
                "default_provider": "llama_cpp",
                "n_ctx": 4096,
                "n_gpu_layers": 0,
                "n_threads": 4,
                "max_retries": 3,
                "timeout_seconds": 60.0,
                "cache_enabled": true,
                "cache_ttl_seconds": 3600,
                "max_history_messages": 50,
                "max_ram_percent": 90.0
            },
            "voice": {
                "enabled": false,
                "wake_word": "atlas",
                "wake_word_model": "alexa",
                "stt_model": "base.en",
                "tts_model": "en_US-lessac-medium",
                "sample_rate": 16000,
                "vad_threshold": 0.5
            },
            "network": {
                "networking_enabled": true,
                "wifi_enabled": false,
                "wifi_ssid": "",
                "wifi_password": "",
                "wifi_auto_connect": true,
                "ap_fallback": true,
                "ap_ssid": "Atlas-OS",
                "ap_password": "",
                "ap_channel": 6,
                "ap_security": "WPA2",
                "mdns_enabled": true,
                "mdns_hostname": "atlas-os"
            },
            "memory": {
                "enabled": true,
                "db_path": "./data/lancedb",
                "embedding_provider": "sentence-transformers",
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dim": 384,
                "chunk_size": 512,
                "chunk_overlap": 50,
                "top_k": 5,
                "rerank": true,
                "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "max_context_tokens": 4000,
                "auto_embed": true,
                "batch_size": 32,
                "min_score": 0.3
            },
            "heartbeat_interval_seconds": 1.0,
            "graceful_shutdown_timeout_seconds": 10.0
        }
    }
    
    function saveConfig() {
        // Save to file
        // For now, just emit signal
        apiService.set_config("config", JSON.stringify(config))
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
                    text: "Configuration"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Save Config"
                    onClicked: saveConfig()
                }
                
                Button {
                    text: "Reload"
                    flat: true
                    onClicked: loadConfig()
                }
            }
            
            // Tab bar
            Row {
                width: parent.width
                spacing: 0
                
                TabButton {
                    text: "General"
                    active: currentTab === 0
                    onClicked: currentTab = 0
                }
                
                TabButton {
                    text: "AI Engine"
                    active: currentTab === 1
                    onClicked: currentTab = 1
                }
                
                TabButton {
                    text: "Voice"
                    active: currentTab === 2
                    onClicked: currentTab = 2
                }
                
                TabButton {
                    text: "Network"
                    active: currentTab === 3
                    onClicked: currentTab = 3
                }
                
                TabButton {
                    text: "Memory"
                    active: currentTab === 4
                    onClicked: currentTab = 4
                }
                
                TabButton {
                    text: "API Keys"
                    active: currentTab === 5
                    onClicked: currentTab = 5
                }
                
                TabButton {
                    text: "Advanced"
                    active: currentTab === 6
                    onClicked: currentTab = 6
                }
                
                Item { Layout.fillWidth: true }
            }
            
            StackLayout {
                id: contentStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: currentTab
                
                // General Tab
                ConfigTab {
                    apiService: apiService
                    config: config
                    onConfigChanged: config = newConfig
                }
                
                // AI Engine Tab
                ConfigTab {
                    apiService: apiService
                    config: config.ai
                    onConfigChanged: config.ai = newConfig
                }
                
                // Voice Tab
                ConfigTab {
                    apiService: apiService
                    config: config.voice
                    onConfigChanged: config.voice = newConfig
                }
                
                // Network Tab
                ConfigTab {
                    apiService: apiService
                    config: config.network
                    onConfigChanged: config.network = newConfig
                }
                
                // Memory Tab
                ConfigTab {
                    apiService: apiService
                    config: config.memory
                    onConfigChanged: config.memory = newConfig
                }
                
                // API Keys Tab
                ApiKeysTab {
                    apiService: apiService
                    apiKeys: apiKeys
                    newApiKeyName: newApiKeyName
                    onNameChanged: newApiKeyName = name
                    onCreate: apiService.create_api_key(name)
                    onRevoke: apiService.revoke_api_key(keyId)
                    onRefresh: apiService.list_api_keys()
                }
                
                // Advanced Tab
                AdvancedTab {
                    apiService: apiService
                    config: config
                    onConfigChanged: config = newConfig
                }
            }
        }
    }
    
    property int currentTab: 0
}

// Config Tab Component (Generic)
Component {
    id: configTabComponent
    Item {
        property var apiService
        property var config: {}
        signal configChanged(var newConfig)
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 16
                anchors.margins: 24
                
                // Dynamic form based on config object
                Repeater {
                    model: Object.keys(config)
                    
                    ConfigField {
                        key: modelData
                        value: config[modelData]
                        onValueChanged: {
                            var newConfig = Object.assign({}, config)
                            newConfig[key] = value
                            configChanged(newConfig)
                        }
                    }
                }
            }
        }
    }
}

// Config Field Component
Component {
    id: configFieldComponent
    Item {
        property string key
        property var value
        signal valueChanged(string key, var value)
        
        width: parent.width
        
        Column {
            spacing: 8
            
            Text {
                text: key
                font.pixelSize: 13
                color: "#6272a4"
            }
            
            // Dynamic input based on value type
            Loader {
                sourceComponent: getInputComponent(value)
                
                onStatusChanged: {
                    if (status === Loader.Ready) {
                        item.width = parent.width
                        item.value = value
                        item.valueChanged.connect(function(v) {
                            valueChanged(key, v)
                        })
                    }
                }
            }
        }
        
        function getInputComponent(val) {
            if (typeof val === "boolean") {
                return checkboxComponent
            } else if (typeof val === "number") {
                return spinBoxComponent
            } else {
                return textInputComponent
            }
        }
        
        Component {
            id: checkboxComponent
            CheckBox {
                property var value
                checked: value
                text: value ? "Enabled" : "Disabled"
                onCheckedChanged: valueChanged(key, checked)
            }
        }
        
        Component {
            id: spinBoxComponent
            SpinBox {
                property var value
                value: value
                onValueChanged: valueChanged(key, value)
            }
        }
        
        Component {
            id: textInputComponent
            TextInput {
                property var value
                text: value.toString()
                onTextChanged: valueChanged(key, text)
                
                background: Rectangle {
                    color: "#1e1e2e"
                    radius: 6
                    border.color: "#44475a"
                    border.width: 1
                }
            }
        }
    }
}

// API Keys Tab
Component {
    id: apiKeysTabComponent
    Item {
        property var apiService
        property var apiKeys: []
        property string newApiKeyName: ""
        signal nameChanged(string name)
        signal create(string name)
        signal revoke(string keyId)
        signal refresh()
        
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
                        text: "API Keys"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        verticalAlignment: Text.AlignVCenter
                        text: apiKeys.length + " keys"
                        font.pixelSize: 14
                        color: "#6272a4"
                    }
                    
                    // Create new key
                    Row {
                        spacing: 8
                        
                        TextInput {
                            id: nameInput
                            width: 250
                            height: 40
                            placeholderText: "Key name (e.g., dashboard, mobile)"
                            font.pixelSize: 13
                            color: "#f8f8f2"
                            placeholderTextColor: "#6272a4"
                            onTextChanged: nameChanged(text)
                            
                            background: Rectangle {
                                color: "#1e1e2e"
                                radius: 6
                                border.color: "#44475a"
                                border.width: 1
                            }
                        }
                        
                        Button {
                            text: "Create Key"
                            enabled: nameInput.text.length > 0
                            onClicked: create(nameInput.text)
                        }
                    }
                    
                    Button {
                        text: "Refresh"
                        onClicked: refresh()
                    }
                }
                
                // API Keys list
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
                        model: apiKeys
                        spacing: 4
                        anchors.margins: 8
                        
                        delegate: ApiKeyItem {
                            width: parent.width
                            onRevoke: revoke(key_id)
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: apiKeys.length === 0 ? 200 : 0
                            visible: apiKeys.length === 0
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: "No API keys created"
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

// API Key Item
Component {
    id: apiKeyItemComponent
    ItemDelegate {
        property string name
        property string key_id
        property string key_prefix
        property string created_at
        property string last_used
        signal revoke(string keyId)
        
        width: parent.width
        height: 90
        
        contentItem: Rectangle {
            anchors.fill: parent
            color: "transparent"
            radius: 6
            border.color: "#44475a"
            border.width: 1
            
            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8
                
                Row {
                    spacing: 12
                    
                    Rectangle {
                        width: 44
                        height: 44
                        radius: 10
                        color: "#bd93f9"
                        opacity: 0.15
                        border.color: "#bd93f9"
                        border.width: 2
                        
                        Text {
                            anchors.centerIn: parent
                            text: "🔑"
                            font.pixelSize: 18
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
                        
                        Row {
                            spacing: 16
                            
                            Text {
                                text: "Prefix: " + key_prefix
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                            
                            Text {
                                text: "Created: " + new Date(created_at).toLocaleString()
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                            
                            Text {
                                text: last_used ? "Last used: " + new Date(last_used).toLocaleString() : "Never used"
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Button {
                        text: "Revoke"
                        flat: true
                        color: "#ff5555"
                        onClicked: {
                            if (confirm("Revoke API key '" + name + "'?")) {
                                revoke(key_id)
                            }
                        }
                    }
                }
            }
        }
    }
}

// Advanced Tab
Component {
    id: advancedTabComponent
    Item {
        property var apiService
        property var config: {}
        signal configChanged(var newConfig)
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 20
                anchors.margins: 24
                
                // Runtime settings
                ConfigSection {
                    title: "Runtime"
                    fields: [
                        { key: "heartbeat_interval_seconds", label: "Heartbeat Interval (s)", type: "number" },
                        { key: "graceful_shutdown_timeout_seconds", label: "Graceful Shutdown Timeout (s)", type: "number" }
                    ]
                    config: config
                    onConfigChanged: configChanged(newConfig)
                }
                
                // UI settings
                ConfigSection {
                    title: "UI"
                    fields: [
                        { key: "ui.desktop_enabled", label: "Desktop Enabled", type: "boolean" },
                        { key: "ui.kiosk_enabled", label: "Kiosk Enabled", type: "boolean" },
                        { key: "ui.style", label: "Style", type: "string" }
                    ]
                    config: config
                    onConfigChanged: configChanged(newConfig)
                }
                
                // Data directories
                ConfigSection {
                    title: "Data Directories"
                    fields: [
                        { key: "data_dir", label: "Data Dir", type: "string" },
                        { key: "models_dir", label: "Models Dir", type: "string" },
                        { key: "plugins_dir", label: "Plugins Dir", type: "string" },
                        { key: "configs_dir", label: "Configs Dir", type: "string" },
                        { key: "logs_dir", label: "Logs Dir", type: "string" }
                    ]
                    config: config
                    onConfigChanged: configChanged(newConfig)
                }
                
                // Danger zone
                Rectangle {
                    Layout.fillWidth: true
                    color: "#3d1a1a"
                    radius: 8
                    border.color: "#ff5555"
                    border.width: 1
                    padding: 24
                    
                    Column {
                        spacing: 16
                        
                        Text {
                            text: "⚠ Danger Zone"
                            font.pixelSize: 18
                            font.bold: true
                            color: "#ff5555"
                        }
                        
                        Text {
                            text: "These actions are irreversible. Use with caution."
                            font.pixelSize: 13
                            color: "#f1fa8c"
                        }
                        
                        Row {
                            spacing: 12
                            
                            Button {
                                text: "Reset Config to Defaults"
                                flat: true
                                color: "#ff5555"
                                onClicked: {
                                    if (confirm("Reset all configuration to defaults?")) {
                                        // Reset config
                                    }
                                }
                            }
                            
                            Button {
                                text: "Clear All Data"
                                flat: true
                                color: "#ff5555"
                                onClicked: {
                                    if (confirm("DELETE ALL DATA? This cannot be undone!")) {
                                        // Clear data
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Config Section Component
Component {
    id: configSectionComponent
    Rectangle {
        property string title
        property var fields: []
        property var config: {}
        signal configChanged(var newConfig)
        
        width: parent.width
        color: "#282a36"
        radius: 8
        border.color: "#44475a"
        border.width: 1
        padding: 16
        
        Column {
            spacing: 16
            
            Text {
                text: title
                font.pixelSize: 16
                font.bold: true
                color: "#f8f8f2"
            }
            
            Repeater {
                model: fields
                
                ConfigField {
                    key: modelData.key
                    value: config[modelData.key]
                    onValueChanged: {
                        var newConfig = Object.assign({}, config)
                        newConfig[key] = value
                        configChanged(newConfig)
                    }
                }
            }
        }
    }
}