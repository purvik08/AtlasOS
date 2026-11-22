import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3

Item {
    property var apiService
    
    property var networkInterfaces: []
    property var wifiNetworks: []
    property var apStatus: {}
    property string selectedInterface: ""
    property string wifiSSID: ""
    property string wifiPassword: ""
    property string apSSID: "Atlas-OS"
    property string apPassword: ""
    property int apChannel: 6
    property string apSecurity: "WPA2"
    property bool scanning: false
    property bool connecting: false
    property bool startingAp: false
    
    Connections {
        target: apiService
        onNetworkInterfacesChanged: {
            networkInterfaces = apiService.network_interfaces
        }
        onWifiScanResultsChanged: {
            wifiNetworks = apiService.wifi_scan_results
            scanning = false
        }
        onApStatusChanged: {
            apStatus = apiService.ap_status
        }
    }
    
    Component.onCompleted: {
        apiService.fetch_network_interfaces()
        apiService.fetch_ap_status()
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
                    text: "Network"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#f8f8f2"
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Refresh"
                    onClicked: {
                        apiService.fetch_network_interfaces()
                        apiService.fetch_ap_status()
                    }
                }
            }
            
            // Tab bar
            Row {
                width: parent.width
                spacing: 0
                
                TabButton {
                    text: "Interfaces"
                    active: currentTab === 0
                    onClicked: currentTab = 0
                }
                
                TabButton {
                    text: "WiFi"
                    active: currentTab === 1
                    onClicked: currentTab = 1
                }
                
                TabButton {
                    text: "Access Point"
                    active: currentTab === 2
                    onClicked: currentTab = 2
                }
                
                TabButton {
                    text: "mDNS"
                    active: currentTab === 3
                    onClicked: currentTab = 3
                }
                
                Item { Layout.fillWidth: true }
            }
            
            StackLayout {
                id: contentStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: currentTab
                
                // Interfaces Tab
                InterfacesTab {
                    apiService: apiService
                    networkInterfaces: networkInterfaces
                }
                
                // WiFi Tab
                WifiTab {
                    apiService: apiService
                    wifiNetworks: wifiNetworks
                    selectedInterface: selectedInterface
                    wifiSSID: wifiSSID
                    wifiPassword: wifiPassword
                    scanning: scanning
                    connecting: connecting
                    onInterfaceChanged: selectedInterface = iface
                    onSSIDChanged: wifiSSID = ssid
                    onPasswordChanged: wifiPassword = pwd
                    onScan: apiService.scan_wifi(iface)
                    onConnect: apiService.connect_wifi(ssid, pwd, iface)
                    onDisconnect: apiService.disconnect_wifi(iface)
                }
                
                // Access Point Tab
                AccessPointTab {
                    apiService: apiService
                    apStatus: apStatus
                    apSSID: apSSID
                    apPassword: apPassword
                    apChannel: apChannel
                    apSecurity: apSecurity
                    startingAp: startingAp
                    onSSIDChanged: apSSID = ssid
                    onPasswordChanged: apPassword = pwd
                    onChannelChanged: apChannel = ch
                    onSecurityChanged: apSecurity = sec
                    onStart: apiService.start_ap(ssid, pwd, channel, sec)
                    onStop: apiService.stop_ap()
                }
                
                // mDNS Tab
                MdnsTab {
                    apiService: apiService
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

// Interfaces Tab
Component {
    id: interfacesTabComponent
    Item {
        property var apiService
        property var networkInterfaces: []
        
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
                        text: "Network Interfaces"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        verticalAlignment: Text.AlignVCenter
                        text: networkInterfaces.length + " interfaces"
                        font.pixelSize: 14
                        color: "#6272a4"
                    }
                    
                    Button {
                        text: "Refresh"
                        onClicked: apiService.fetch_network_interfaces()
                    }
                }
                
                // Interfaces list
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
                        model: networkInterfaces
                        spacing: 4
                        anchors.margins: 8
                        
                        delegate: InterfaceItem {
                            width: parent.width
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: networkInterfaces.length === 0 ? 200 : 0
                            visible: networkInterfaces.length === 0
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: "No network interfaces found"
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

// Interface Item
Component {
    id: interfaceItemComponent
    ItemDelegate {
        width: parent.width
        height: 140
        
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
                        width: 48
                        height: 48
                        radius: 12
                        color: modelData.is_up ? "#50fa7b" : "#ff5555"
                        opacity: 0.2
                        border.color: modelData.is_up ? "#50fa7b" : "#ff5555"
                        border.width: 2
                        
                        Text {
                            anchors.centerIn: parent
                            text: modelData.is_up ? "▲" : "▼"
                            font.pixelSize: 20
                            color: modelData.is_up ? "#50fa7b" : "#ff5555"
                            font.bold: true
                        }
                    }
                    
                    Column {
                        spacing: 2
                        
                        Text {
                            text: modelData.name
                            font.pixelSize: 16
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Text {
                            text: "MAC: " + modelData.mac
                            font.pixelSize: 12
                            color: "#6272a4"
                        }
                        
                        Row {
                            spacing: 16
                            
                            Text {
                                text: "IPv4: " + (modelData.ipv4 && modelData.ipv4.length > 0 ? modelData.ipv4.join(", ") : "None")
                                font.pixelSize: 12
                                color: "#bd93f9"
                            }
                            
                            Text {
                                text: "MTU: " + modelData.mtu
                                font.pixelSize: 12
                                color: "#6272a4"
                            }
                        }
                    }
                }
            }
        }
    }
}

// WiFi Tab
Component {
    id: wifiTabComponent
    Item {
        property var apiService
        property var wifiNetworks: []
        property string selectedInterface: ""
        property string wifiSSID: ""
        property string wifiPassword: ""
        property bool scanning: false
        property bool connecting: false
        signal interfaceChanged(string iface)
        signal ssidChanged(string ssid)
        signal passwordChanged(string pwd)
        signal scan(string iface)
        signal connect(string ssid, string pwd, string iface)
        signal disconnect(string iface)
        
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
                        text: "WiFi Networks"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    ComboBox {
                        id: interfaceSelector
                        width: 200
                        placeholderText: "Select Interface"
                        model: networkInterfaces.map(function(iface) { return iface.name })
                        currentIndex: 0
                        onActivated: {
                            selectedInterface = networkInterfaces[index].name
                            interfaceChanged(networkInterfaces[index].name)
                        }
                    }
                    
                    Button {
                        text: scanning ? "Scanning..." : "Scan"
                        enabled: !scanning
                        onClicked: {
                            if (selectedInterface) {
                                scan(selectedInterface)
                            }
                        }
                    }
                }
                
                // Networks list
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
                        model: wifiNetworks
                        spacing: 4
                        anchors.margins: 8
                        
                        delegate: WifiNetworkItem {
                            width: parent.width
                            onConnectClicked: connect(ssid, password, selectedInterface)
                        }
                        
                        // Empty state
                        footer: Item {
                            width: parent.width
                            height: wifiNetworks.length === 0 ? 200 : 0
                            visible: wifiNetworks.length === 0
                            
                            Column {
                                anchors.centerIn: parent
                                spacing: 16
                                
                                Text {
                                    text: scanning ? "Scanning..." : "No networks found"
                                    font.pixelSize: 16
                                    color: "#6272a4"
                                }
                                
                                Button {
                                    text: "Scan"
                                    enabled: !scanning && selectedInterface.length > 0
                                    onClicked: scan(selectedInterface)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    property var networkInterfaces: []
    
    Component.onCompleted: {
        // Fetch interfaces when tab is shown
        apiService.fetch_network_interfaces()
    }
}

// WiFi Network Item
Component {
    id: wifiNetworkItemComponent
    ItemDelegate {
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
                anchors.margins: 12
                spacing: 6
                
                Row {
                    spacing: 12
                    
                    // Signal strength bars
                    Row {
                        spacing: 2
                        Repeater {
                            model: 4
                            Rectangle {
                                width: 4
                                height: index * 4 + 8
                                radius: 2
                                color: index < (modelData.signal_strength / 25) ? "#50fa7b" : "#44475a"
                            }
                        }
                    }
                    
                    Column {
                        spacing: 2
                        
                        Text {
                            text: modelData.ssid
                            font.pixelSize: 16
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Row {
                            spacing: 16
                            
                            Text {
                                text: "Channel: " + modelData.channel
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                            
                            Text {
                                text: modelData.frequency + " MHz"
                                font.pixelSize: 11
                                color: "#6272a4"
                            }
                            
                            Text {
                                text: modelData.security
                                font.pixelSize: 11
                                color: modelData.security === "Open" ? "#f1fa8c" : "#bd93f9"
                            }
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        text: modelData.signal_strength + " dBm"
                        font.pixelSize: 12
                        font.bold: true
                        color: modelData.signal_strength > -50 ? "#50fa7b" : 
                               modelData.signal_strength > -70 ? "#f1fa8c" : "#ff5555"
                    }
                }
                
                // Security info
                Row {
                    spacing: 8
                    
                    Text {
                        text: "BSSID: " + modelData.bssid
                        font.pixelSize: 10
                        color: "#44475a"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    // Connect button
                    Button {
                        text: "Connect"
                        width: 80
                        height: 32
                        flat: true
                        onClicked: {
                            if (modelData.security === "Open") {
                                connectClicked(modelData.ssid, "", "")
                            } else {
                                // Show password dialog
                                var pwd = prompt("Password for " + modelData.ssid + ":")
                                if (pwd !== null) {
                                    connectClicked(modelData.ssid, pwd, "")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Access Point Tab
Component {
    id: accessPointTabComponent
    Item {
        property var apiService
        property var apStatus: {}
        property string apSSID: "Atlas-OS"
        property string apPassword: ""
        property int apChannel: 6
        property string apSecurity: "WPA2"
        property bool startingAp: false
        signal ssidChanged(string ssid)
        signal passwordChanged(string pwd)
        signal channelChanged(int ch)
        signal securityChanged(string sec)
        signal start(string ssid, string pwd, int channel, string sec)
        signal stop()
        
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
                        text: "Access Point"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    // Current status
                    Row {
                        spacing: 12
                        
                        Rectangle {
                            width: 12
                            height: 12
                            radius: 6
                            color: apStatus.active ? "#50fa7b" : "#ff5555"
                        }
                        
                        Text {
                            verticalAlignment: Text.AlignVCenter
                            text: apStatus.active ? "Active: " + apStatus.ssid : "Inactive"
                            font.pixelSize: 14
                            color: apStatus.active ? "#50fa7b" : "#ff5555"
                        }
                    }
                    
                    Button {
                        text: apStatus.active ? "Stop AP" : "Start AP"
                        onClicked: {
                            if (apStatus.active) {
                                stop()
                            } else {
                                start(apSSID, apPassword, apChannel, apSecurity)
                            }
                        }
                    }
                    
                    Button {
                        text: "Refresh"
                        onClicked: apiService.fetch_ap_status()
                    }
                }
                
                // Configuration
                Rectangle {
                    visible: !apStatus.active
                    width: parent.width
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    padding: 24
                    
                    Column {
                        spacing: 16
                        
                        Text {
                            text: "AP Configuration"
                            font.pixelSize: 18
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        // SSID
                        Column {
                            spacing: 8
                            width: parent.width
                            
                            Text {
                                text: "SSID"
                                font.pixelSize: 13
                                color: "#6272a4"
                            }
                            
                            TextInput {
                                width: parent.width
                                height: 40
                                placeholderText: "Atlas-OS"
                                text: apSSID
                                onTextChanged: ssidChanged(text)
                                font.pixelSize: 13
                                color: "#f8f8f2"
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                        }
                        
                        // Password
                        Column {
                            spacing: 8
                            width: parent.width
                            
                            Text {
                                text: "Password (8-63 chars, empty for open)"
                                font.pixelSize: 13
                                color: "#6272a4"
                            }
                            
                            TextInput {
                                width: parent.width
                                height: 40
                                placeholderText: "Leave empty for open network"
                                text: apPassword
                                onTextChanged: passwordChanged(text)
                                echoMode: TextInput.Password
                                font.pixelSize: 13
                                color: "#f8f8f2"
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                        }
                        
                        // Channel
                        Column {
                            spacing: 8
                            width: parent.width
                            
                            Text {
                                text: "Channel"
                                font.pixelSize: 13
                                color: "#6272a4"
                            }
                            
                            SpinBox {
                                id: channelSpin
                                width: 100
                                height: 40
                                minimumValue: 1
                                maximumValue: 13
                                value: apChannel
                                onValueChanged: channelChanged(value)
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                        }
                        
                        // Security
                        Column {
                            spacing: 8
                            width: parent.width
                            
                            Text {
                                text: "Security"
                                font.pixelSize: 13
                                color: "#6272a4"
                            }
                            
                            ComboBox {
                                width: 200
                                height: 40
                                model: ["Open", "WPA2", "WPA3"]
                                currentText: apSecurity
                                onActivated: securityChanged(model[index])
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                        }
                        
                        // Start button
                        Button {
                            text: "Start Access Point"
                            Layout.fillWidth: true
                            enabled: !startingAp
                            onClicked: start(apSSID, apPassword, apChannel, apSecurity)
                        }
                    }
                }
            }
            
            // Active AP info
            Rectangle {
                visible: apStatus.active
                width: parent.width
                color: "#282a36"
                radius: 8
                border.color: "#44475a"
                border.width: 1
                padding: 24
                
                Column {
                    spacing: 16
                    
                    Text {
                        text: "Active Access Point"
                        font.pixelSize: 18
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    GridLayout {
                        columns: 2
                        width: parent.width
                        rowSpacing: 8
                        
                        StatItem { label: "SSID"; value: apStatus.ssid }
                        StatItem { label: "Channel"; value: apStatus.channel }
                        StatItem { label: "Security"; value: apStatus.security }
                        StatItem { label: "Clients"; value: apStatus.clients_connected || 0 }
                        StatItem { label: "Interface"; value: apStatus.interface }
                        StatItem { label: "IP"; value: apStatus.ip || "N/A" }
                    }
                    
                    Button {
                        text: "Stop Access Point"
                        Layout.fillWidth: true
                        onClicked: stop()
                    }
                }
            }
        }
    }
}

// mDNS Tab
Component {
    id: mdnsTabComponent
    Item {
        property var apiService
        
        ScrollView {
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar { }
            
            Column {
                width: parent.width
                spacing: 20
                anchors.margins: 24
                
                Row {
                    width: parent.width
                    spacing: 16
                    
                    Text {
                        text: "mDNS Services"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#f8f8f2"
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Button {
                        text: "Refresh"
                        onClicked: {
                            // apiService.refresh_mdns()
                        }
                    }
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#282a36"
                    radius: 8
                    border.color: "#44475a"
                    border.width: 1
                    
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
                                text: "🔍"
                                font.pixelSize: 28
                            }
                        }
                        
                        Text {
                            text: "mDNS Service Discovery"
                            font.pixelSize: 16
                            color: "#6272a4"
                        }
                        
                        Text {
                            text: "Service discovery coming soon"
                            font.pixelSize: 13
                            color: "#44475a"
                        }
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