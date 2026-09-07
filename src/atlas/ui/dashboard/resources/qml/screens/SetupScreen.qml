import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root

    property var appState: null
    property var apiService: null
    property var llmModel: null
    property var memoryModel: null
    property var wifiModel: null

    signal openPanel(int index)

    function modelCount() { return llmModel ? llmModel.rowCount() : 0 }
    function memoryCount() { return memoryModel ? memoryModel.count : 0 }
    function pluginsReady() { return apiService ? apiService.pluginList.length : 0 }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingMd

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 86
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: 14

                    Rectangle {
                        width: 42
                        height: 42
                        radius: 10
                        color: Theme.accentCyan
                        Text { anchors.centerIn: parent; text: "OS"; color: Theme.bgPrimary; font.bold: true; font.family: Theme.fontMono }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Atlas OS Setup"; color: Theme.textPrimary; font.pixelSize: 20; font.bold: true }
                        Text { text: "Bring core services online, discover hardware, and prepare the assistant."; color: Theme.textMuted; font.pixelSize: 13 }
                    }

                    AtlasButton {
                        text: "Refresh"
                        variant: "secondary"
                        onClicked: {
                            if (apiService) apiService.refresh_all()
                            if (appState) appState.refreshSystemInfo()
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 760 ? 2 : 1
                columnSpacing: Theme.spacingMd
                rowSpacing: Theme.spacingMd

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 190
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        Text { text: "1. Runtime Connection"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                        DetailRow { label: "API"; value: apiService && apiService.connected ? "Connected" : "Offline" }
                        DetailRow { label: "Host"; value: appState ? appState.hostname : "atlas" }
                        DetailRow { label: "Address"; value: appState ? appState.ipAddress : "127.0.0.1" }
                        AtlasButton { text: "Open System"; variant: "secondary"; onClicked: root.openPanel(9) }
                    }
                }

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 190
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        Text { text: "2. Model Library"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                        DetailRow { label: "Models"; value: root.modelCount() + " discovered" }
                        DetailRow { label: "Directory"; value: apiService && apiService.systemInfo.config ? apiService.systemInfo.config.models_dir : "./models" }
                        RowLayout {
                            AtlasButton { text: "Scan Models"; variant: "primary"; onClicked: if (llmModel) llmModel.rescanModels() }
                            AtlasButton { text: "Open Models"; variant: "secondary"; onClicked: root.openPanel(3) }
                        }
                    }
                }

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 190
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        Text { text: "3. Network"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                        DetailRow { label: "Primary"; value: apiService && apiService.networkStatus.primary_device ? apiService.networkStatus.primary_device : "Detecting" }
                        DetailRow { label: "Connectivity"; value: apiService && apiService.networkStatus.connectivity ? apiService.networkStatus.connectivity : "Unknown" }
                        RowLayout {
                            AtlasButton { text: "Scan Wi-Fi"; variant: "primary"; onClicked: if (wifiModel) wifiModel.scan() }
                            AtlasButton { text: "Open Network"; variant: "secondary"; onClicked: root.openPanel(5) }
                        }
                    }
                }

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 190
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        Text { text: "4. Voice, Memory, Plugins"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 15 }
                        DetailRow { label: "Memory"; value: root.memoryCount() + " entries" }
                        DetailRow { label: "Plugins"; value: root.pluginsReady() + " discovered" }
                        RowLayout {
                            AtlasButton { text: "Voice"; variant: "secondary"; onClicked: root.openPanel(6) }
                            AtlasButton { text: "Memory"; variant: "secondary"; onClicked: root.openPanel(7) }
                            AtlasButton { text: "Plugins"; variant: "secondary"; onClicked: root.openPanel(8) }
                        }
                    }
                }
            }
        }
    }
}
