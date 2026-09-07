import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root

    property var appState: null
    property var apiService: null
    property var wifiModel: null
    property var meshModel: null
    property bool isScanning: false
    property bool showPasswordModal: false
    property string targetSsid: ""
    property int targetRow: -1

    Connections {
        target: wifiModel
        function onScanCompleted(count) {
            root.isScanning = false
        }
    }

    Connections {
        target: apiService
        function onWifi_connect_completed(ssid, success, message) {
            root.isScanning = false
            if (apiService) apiService.refresh_all()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: 12

                Rectangle {
                    width: 38
                    height: 38
                    radius: 9
                    color: Qt.rgba(0, 229, 255, 0.12)
                    Text { anchors.centerIn: parent; text: "NW"; color: Theme.accentCyan; font.bold: true; font.family: Theme.fontMono }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: "Network & Connectivity"; color: Theme.textPrimary; font.pixelSize: 18; font.bold: true }
                    Text {
                        text: "IP: " + (appState ? appState.ipAddress : "127.0.0.1") + " / Host: " + (appState ? appState.hostname : "localhost")
                        color: Theme.textMuted
                        font.pixelSize: 12
                        font.family: Theme.fontMono
                    }
                }

                AtlasStatusBadge {
                    label: apiService && apiService.networkStatus.connected ? "connected" : "offline"
                    status: apiService && apiService.networkStatus.connected ? "success" : "offline"
                }

                AtlasButton {
                    text: "Disconnect"
                    variant: "secondary"
                    enabled: apiService ? !!apiService.networkStatus.connected : false
                    onClicked: if (apiService) apiService.disconnect_wifi("")
                }

                AtlasButton {
                    text: root.isScanning ? "Scanning" : "Scan Wi-Fi"
                    iconText: "SC"
                    variant: "primary"
                    loading: root.isScanning
                    onClicked: {
                        root.isScanning = true
                        if (wifiModel) wifiModel.scan("")
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width > 760 ? 3 : 1
            columnSpacing: Theme.spacingMd
            rowSpacing: Theme.spacingMd

            MetricCard {
                title: "Connectivity"
                value: apiService && apiService.networkStatus.connectivity ? apiService.networkStatus.connectivity : "unknown"
                icon: "IP"
                progress: apiService && apiService.networkStatus.connected ? 1 : 0
                accentColor: apiService && apiService.networkStatus.connected ? Theme.success : Theme.offline
            }
            MetricCard {
                title: "Primary Device"
                value: apiService && apiService.networkStatus.primary_device ? apiService.networkStatus.primary_device : "--"
                icon: "IF"
                progress: 1
                accentColor: Theme.accentCyan
            }
            MetricCard {
                title: "Active SSID"
                value: apiService && apiService.networkStatus.active_ssid ? apiService.networkStatus.active_ssid : "--"
                icon: "WF"
                progress: apiService && apiService.networkStatus.active_ssid ? 1 : 0
                accentColor: Theme.accentAmber
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingMd

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: Theme.spacingSm

                    Text { text: "Wireless Networks"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    ListView {
                        id: wifiListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: wifiModel
                        spacing: 8
                        clip: true

                        delegate: Rectangle {
                            width: wifiListView.width
                            height: 62
                            radius: Theme.radiusSm
                            color: connected ? Qt.rgba(0, 229, 255, 0.08) : Theme.bgSecondary
                            border.color: connected ? Theme.accentCyan : Theme.borderSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Rectangle {
                                    width: 30
                                    height: 30
                                    radius: 7
                                    color: connected ? Qt.rgba(0, 230, 118, 0.14) : Qt.rgba(255, 255, 255, 0.04)
                                    Text { anchors.centerIn: parent; text: connected ? "ON" : "WF"; color: connected ? Theme.success : Theme.textSecondary; font.bold: true; font.family: Theme.fontMono; font.pixelSize: 11 }
                                }

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: ssid; color: connected ? Theme.accentCyan : Theme.textPrimary; font.pixelSize: 14; font.bold: connected; elide: Text.ElideRight; width: parent.width }
                                    Text { text: (secured ? "Secured" : "Open") + " / " + signal + "% / " + frequency; color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontMono }
                                }

                                AtlasButton {
                                    text: connected ? "Connected" : "Connect"
                                    variant: connected ? "ghost" : "secondary"
                                    enabled: !connected
                                    implicitWidth: 96
                                    implicitHeight: 34
                                    onClicked: {
                                        if (secured) {
                                            root.targetSsid = ssid
                                            root.targetRow = index
                                            root.showPasswordModal = true
                                        } else if (wifiModel) {
                                            wifiModel.connectToNetwork(index, "")
                                        }
                                    }
                                }
                            }
                        }

                        AtlasEmptyState {
                            anchors.centerIn: parent
                            visible: !wifiModel || wifiModel.rowCount() === 0
                            iconText: "WF"
                            title: "No Wi-Fi Scan Results"
                            message: "Run a scan to discover nearby wireless access points."
                            actionText: "Scan"
                            onActionClicked: {
                                root.isScanning = true
                                if (wifiModel) wifiModel.scan("")
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: Theme.spacingSm

                    Text { text: "Local Node & Interfaces"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    ListView {
                        id: meshListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: meshModel
                        spacing: 8
                        clip: true

                        delegate: Rectangle {
                            width: meshListView.width
                            height: 64
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Rectangle {
                                    width: 30
                                    height: 30
                                    radius: 7
                                    color: Qt.rgba(0, 229, 255, 0.10)
                                    Text { anchors.centerIn: parent; text: isLocal ? "LO" : "IP"; color: Theme.accentCyan; font.bold: true; font.family: Theme.fontMono; font.pixelSize: 11 }
                                }

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: hostname; color: Theme.textPrimary; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight; width: parent.width }
                                    Text { text: modelName + " / " + address; color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontMono; elide: Text.ElideRight; width: parent.width }
                                }

                                AtlasStatusBadge {
                                    label: model.status.toUpperCase()
                                    status: model.status === "online" || model.status === "serving" ? "success" : "offline"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        visible: root.showPasswordModal
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.76)
        z: 60

        AtlasCard {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 440)
            height: 240

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Text { text: "Connect to " + root.targetSsid; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                Text { text: "Enter the wireless passphrase."; color: Theme.textSecondary; font.pixelSize: 12 }

                AtlasTextField {
                    id: pwdInput
                    Layout.fillWidth: true
                    placeholderText: "Password"
                    echoMode: TextInput.Password
                }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    AtlasButton {
                        text: "Cancel"
                        variant: "ghost"
                        onClicked: {
                            pwdInput.text = ""
                            root.showPasswordModal = false
                        }
                    }
                    AtlasButton {
                        text: "Connect"
                        variant: "primary"
                        onClicked: {
                            if (wifiModel && root.targetRow >= 0) {
                                wifiModel.connectToNetwork(root.targetRow, pwdInput.text.trim())
                            }
                            pwdInput.text = ""
                            root.showPasswordModal = false
                        }
                    }
                }
            }
        }
    }
}
