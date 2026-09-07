import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * SystemScreen — Comprehensive diagnostics, hardware specs, service health, and power controls.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var apiService: typeof apiService !== "undefined" ? apiService : null

    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        clip: true
        ScrollBar.vertical: ScrollBar { }

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingMd

            // 1. Header & Quick Power Actions
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacingMd
                    anchors.rightMargin: Theme.spacingMd
                    spacing: 12

                    Text {
                        text: "⚙"
                        font.pixelSize: 22
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Atlas OS System Diagnostics"
                            font.pixelSize: 15
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Text {
                            text: (appState ? appState.hostname : "atlas") + "  ·  " + (appState ? appState.platform + " " + appState.platformVersion : "")
                            font.pixelSize: 12
                            font.family: Theme.fontMono
                            color: Theme.textMuted
                        }
                    }

                    AtlasButton {
                        text: "Reboot"
                        iconText: "↻"
                        variant: "secondary"
                        implicitWidth: 100
                        onClicked: {
                            if (appState) appState.requestReboot()
                        }
                    }

                    AtlasButton {
                        text: "Shutdown"
                        iconText: "⏻"
                        variant: "danger"
                        implicitWidth: 110
                        onClicked: {
                            if (appState) appState.requestShutdown()
                        }
                    }
                }
            }

            // 2. Hardware Telemetry Cards Grid
            GridLayout {
                Layout.fillWidth: true
                columns: width > 700 ? 2 : 1
                columnSpacing: Theme.spacingMd
                rowSpacing: Theme.spacingMd

                // Hardware & OS Specs
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 220

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 6

                        Text {
                            text: "Platform & Hardware Specifications"
                            font.pixelSize: 14
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "Operating System"
                            value: appState ? appState.platform + " " + appState.platformVersion : "Linux"
                        }
                        DetailRow {
                            label: "Architecture"
                            value: "ARM64 (Raspberry Pi 5 target)"
                        }
                        DetailRow {
                            label: "Python Runtime"
                            value: appState ? appState.pythonVersion : "3.12"
                        }
                        DetailRow {
                            label: "Host IP"
                            value: appState ? appState.ipAddress : "127.0.0.1"
                        }
                    }
                }

                // Subsystem Service Health
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 220

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 6

                        Text {
                            text: "AtlasOS Subsystem Health"
                            font.pixelSize: 14
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "API Gateway (FastAPI)"
                            value: apiService && apiService.connected ? "Active (:8000)" : "Offline"
                        }
                        DetailRow {
                            label: "Inference Engine (llama.cpp)"
                            value: "Ready (Local CPU)"
                        }
                        DetailRow {
                            label: "Memory Store (Vector DB)"
                            value: "Active"
                        }
                        DetailRow {
                            label: "Network Subsystem (NetworkManager)"
                            value: "Active (DBus)"
                        }
                    }
                }
            }

            // 3. Display Settings & Brightness
            AtlasCard {
                Layout.fillWidth: true
                Layout.minimumHeight: 120

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Embedded Display & Brightness"
                            font.pixelSize: 14
                            font.bold: true
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: (appState ? appState.brightness : 80) + "%"
                            font.pixelSize: 13
                            font.family: Theme.fontMono
                            color: Theme.accentCyan
                        }
                    }

                    Slider {
                        width: parent.width
                        from: 10; to: 100; value: appState ? appState.brightness : 80; stepSize: 5
                        onMoved: if (appState) appState.setBrightness(Math.round(value))
                    }
                }
            }
        }
    }
}
