import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root
    property var apiService: null

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                Text { text: "Plugin System"; color: Theme.textPrimary; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true }
                AtlasStatusBadge { label: apiService ? apiService.pluginList.length + " plugins" : "offline"; status: apiService && apiService.connected ? "success" : "offline" }
                AtlasButton { text: "Refresh"; variant: "secondary"; onClicked: if (apiService) apiService.fetch_plugins() }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border
            clip: true

            ListView {
                id: pluginList
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingSm
                model: apiService ? apiService.pluginList : []

                delegate: Rectangle {
                    width: pluginList.width
                    height: 92
                    radius: Theme.radiusSm
                    color: modelData.enabled ? Qt.rgba(0, 230, 118, 0.06) : Theme.bgSecondary
                    border.color: modelData.enabled ? Qt.rgba(0, 230, 118, 0.35) : Theme.borderSubtle

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Rectangle {
                            width: 34
                            height: 34
                            radius: 8
                            color: Qt.rgba(0, 229, 255, 0.12)
                            Text { anchors.centerIn: parent; text: "PL"; color: Theme.accentCyan; font.bold: true; font.family: Theme.fontMono }
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: modelData.name || "plugin"; color: Theme.textPrimary; font.pixelSize: 15; font.bold: true }
                            Text { text: (modelData.description || "No description") + " / v" + (modelData.version || ""); color: Theme.textMuted; font.pixelSize: 12; elide: Text.ElideRight; width: parent.width }
                            Text { text: modelData.error || "Permissions: " + ((modelData.permissions || []).join(", ") || "none"); color: modelData.error ? Theme.danger : Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                        }

                        AtlasStatusBadge {
                            label: modelData.enabled ? "enabled" : "disabled"
                            status: modelData.enabled ? "success" : "offline"
                        }

                        AtlasButton {
                            text: modelData.enabled ? "Disable" : "Enable"
                            variant: modelData.enabled ? "secondary" : "primary"
                            implicitWidth: 96
                            onClicked: {
                                if (!apiService) return
                                if (modelData.enabled) apiService.disable_plugin(modelData.name)
                                else apiService.enable_plugin(modelData.name)
                            }
                        }
                    }
                }

                AtlasEmptyState {
                    anchors.centerIn: parent
                    visible: !apiService || apiService.pluginList.length === 0
                    iconText: "PL"
                    title: "No Plugins Discovered"
                    message: "Plugins appear here after Atlas scans the plugins directory."
                    actionText: "Refresh"
                    onActionClicked: if (apiService) apiService.fetch_plugins()
                }
            }
        }
    }
}
