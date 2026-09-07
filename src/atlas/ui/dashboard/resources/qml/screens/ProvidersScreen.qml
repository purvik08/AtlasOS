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
                Text { text: "Provider Registry"; color: Theme.textPrimary; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true }
                AtlasStatusBadge { label: apiService ? apiService.providerList.length + " providers" : "offline"; status: apiService && apiService.connected ? "success" : "offline" }
                AtlasButton { text: "Refresh"; variant: "secondary"; onClicked: if (apiService) apiService.refresh_all() }
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
                id: providerList
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingSm
                model: apiService ? apiService.providerList : []

                delegate: Rectangle {
                    width: providerList.width
                    height: 82
                    radius: Theme.radiusSm
                    color: Theme.bgSecondary
                    border.color: Theme.borderSubtle

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Rectangle {
                            width: 34
                            height: 34
                            radius: 8
                            color: Qt.rgba(0, 229, 255, 0.12)
                            Text { anchors.centerIn: parent; text: "AI"; color: Theme.accentCyan; font.bold: true; font.family: Theme.fontMono }
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: modelData.name || "provider"; color: Theme.textPrimary; font.pixelSize: 15; font.bold: true }
                            Text { text: (modelData.message || modelData.error || "Provider registered") + " / loaded: " + ((modelData.loaded_models || []).join(", ") || "none"); color: Theme.textMuted; font.pixelSize: 12; elide: Text.ElideRight; width: parent.width }
                        }

                        AtlasStatusBadge {
                            label: modelData.status || "unknown"
                            status: modelData.status || "offline"
                        }
                    }
                }

                AtlasEmptyState {
                    anchors.centerIn: parent
                    visible: !apiService || apiService.providerList.length === 0
                    iconText: "AI"
                    title: "No Providers Reported"
                    message: "Start or refresh the Atlas backend to populate provider health."
                    actionText: "Refresh"
                    onActionClicked: if (apiService) apiService.refresh_all()
                }
            }
        }
    }
}
