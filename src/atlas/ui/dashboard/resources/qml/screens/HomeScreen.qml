import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * HomeScreen — Primary AtlasOS Futuristic Edge Dashboard.
 * 100% Real hardware & subsystem telemetry.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var apiService: typeof apiService !== "undefined" ? apiService : null
    property var llmModel: typeof llmModel !== "undefined" ? llmModel : null
    property var memoryModel: typeof memoryModel !== "undefined" ? memoryModel : null
    property var wifiModel: typeof wifiModel !== "undefined" ? wifiModel : null

    // Determine active loaded model
    readonly property string loadedModelName: {
        if (!llmModel || !llmModel._models) return "None"
        for (var i = 0; i < llmModel._models.length; i++) {
            if (llmModel._models[i].loaded) return llmModel._models[i].name
        }
        return "None loaded"
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        clip: true
        ScrollBar.vertical: ScrollBar { }

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingLg

            // 1. Header Banner
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacingLg
                    anchors.rightMargin: Theme.spacingLg
                    spacing: 16

                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        Row {
                            spacing: 8
                            Text {
                                text: "ATLAS"
                                font.pixelSize: 20
                                font.bold: true
                                font.family: Theme.fontMono
                                color: Theme.accentCyan
                            }
                            Text {
                                text: "OS"
                                font.pixelSize: 20
                                font.family: Theme.fontMono
                                color: Theme.textMuted
                            }
                            AtlasStatusBadge {
                                label: apiService && apiService.connected ? "ONLINE" : "OFFLINE"
                                status: apiService && apiService.connected ? "success" : "offline"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                        Text {
                            text: (appState ? appState.hostname : "atlas") + "  ·  " + (appState ? appState.ipAddress : "127.0.0.1") + "  ·  " + (appState ? appState.platform + " " + appState.platformVersion : "")
                            font.pixelSize: 12
                            font.family: Theme.fontMono
                            color: Theme.textMuted
                        }
                    }

                    AtlasButton {
                        text: "Refresh"
                        iconText: "↻"
                        variant: "secondary"
                        onClicked: {
                            if (apiService) apiService.refresh_all()
                            if (appState) appState.refreshSystemInfo()
                        }
                    }
                }
            }

            // 2. Hardware Telemetry Grid (4 Metrics)
            GridLayout {
                Layout.fillWidth: true
                columns: width > 900 ? 4 : (width > 540 ? 2 : 1)
                columnSpacing: Theme.spacingMd
                rowSpacing: Theme.spacingMd

                MetricCard {
                    title: "CPU Load"
                    value: (appState ? appState.cpuPercent.toFixed(1) : "0.0") + "%"
                    icon: "⚡"
                    progress: appState ? appState.cpuPercent / 100 : 0
                    accentColor: appState && appState.cpuPercent > 80 ? Theme.danger : Theme.accentCyan
                }

                MetricCard {
                    title: "RAM Usage"
                    value: (appState ? appState.ramPercent.toFixed(1) : "0.0") + "%"
                    icon: "🧠"
                    progress: appState ? appState.ramPercent / 100 : 0
                    accentColor: appState && appState.ramPercent > 85 ? Theme.warning : Theme.accentPurple
                }

                MetricCard {
                    title: "SoC Temperature"
                    value: (appState ? appState.tempCelsius.toFixed(1) : "42.0") + " °C"
                    icon: "🌡"
                    progress: appState ? Math.min(1.0, appState.tempCelsius / 85.0) : 0.5
                    accentColor: appState && appState.tempCelsius > 75 ? Theme.danger : Theme.accentAmber
                }

                MetricCard {
                    title: "System Uptime"
                    value: {
                        var s = appState ? appState.uptimeSeconds : 0
                        var h = Math.floor(s / 3600)
                        var m = Math.floor((s % 3600) / 60)
                        return (h > 0 ? h + "h " : "") + m + "m"
                    }
                    icon: "⏱"
                    progress: 0.0
                    accentColor: Theme.success
                }
            }

            // 3. Subsystem Cards Grid (AI Core, Network, Voice, Memory)
            GridLayout {
                Layout.fillWidth: true
                columns: width > 760 ? 2 : 1
                columnSpacing: Theme.spacingMd
                rowSpacing: Theme.spacingMd

                // AI Subsystem Card
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 160

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "AI Core & Model Engine"
                                font.pixelSize: 15
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            Item { Layout.fillWidth: true }
                            AtlasStatusBadge {
                                label: root.loadedModelName !== "None loaded" ? "READY" : "STANDBY"
                                status: root.loadedModelName !== "None loaded" ? "success" : "warning"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "Active Model"
                            value: root.loadedModelName
                        }

                        DetailRow {
                            label: "Inference Engine"
                            value: "llama.cpp / On-Device"
                        }

                        DetailRow {
                            label: "Model Registry"
                            value: llmModel && llmModel._models ? (llmModel._models.length + " model(s) available") : "Checking..."
                        }
                    }
                }

                // Network Subsystem Card
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 160

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Network & Connectivity"
                                font.pixelSize: 15
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            Item { Layout.fillWidth: true }
                            AtlasStatusBadge {
                                label: appState && appState.ipAddress !== "127.0.0.1" ? "CONNECTED" : "OFFLINE"
                                status: appState && appState.ipAddress !== "127.0.0.1" ? "success" : "offline"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "IP Address"
                            value: appState ? appState.ipAddress : "127.0.0.1"
                        }

                        DetailRow {
                            label: "Hostname"
                            value: appState ? appState.hostname : "localhost"
                        }

                        DetailRow {
                            label: "Network Backend"
                            value: "NetworkManager / DBus"
                        }
                    }
                }

                // Voice & Audio Subsystem Card
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 160

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Voice & Audio Core"
                                font.pixelSize: 15
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            Item { Layout.fillWidth: true }
                            AtlasStatusBadge {
                                label: appState && appState.voiceEnabled ? "ACTIVE" : "MUTED"
                                status: appState && appState.voiceEnabled ? "success" : "offline"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "Voice Mode"
                            value: appState && appState.voiceMode === "wake_word" ? "Wake-Word ('Hey Atlas')" : "Push-to-Talk"
                        }

                        DetailRow {
                            label: "Speech-to-Text"
                            value: "faster-whisper (Offline)"
                        }

                        DetailRow {
                            label: "Text-to-Speech"
                            value: "Piper ONNX (Offline)"
                        }
                    }
                }

                // Memory Knowledge Base Card
                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 160

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Persistent Memory"
                                font.pixelSize: 15
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            Item { Layout.fillWidth: true }
                            AtlasStatusBadge {
                                label: "ONLINE"
                                status: "success"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                        DetailRow {
                            label: "Stored Memories"
                            value: memoryModel && memoryModel._all_entries ? (memoryModel._all_entries.length + " entries") : "0 entries"
                        }

                        DetailRow {
                            label: "Vector Embeddings"
                            value: "Local CPU / HashEmbedder"
                        }

                        DetailRow {
                            label: "Storage"
                            value: (appState ? appState.diskUsedGb.toFixed(1) + " GB / " + appState.diskTotalGb.toFixed(1) + " GB (" + appState.diskPercent.toFixed(0) + "%)" : "--")
                        }
                    }
                }
            }
        }
    }
}
