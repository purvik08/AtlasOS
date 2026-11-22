import QtQuick
import AtlasUI 1.0
import "../components"

Item {
    id: root

    // Dummy log lines cycling to simulate a live tail
    property var logLines: [
        "[INFO]  atlas.runtime: heartbeat #42",
        "[INFO]  atlas.ai: model qwen2.5:3b loaded — 2.1 GB RSS",
        "[INFO]  atlas.network: mDNS advertisement refreshed",
        "[DEBUG] atlas.voice: RMS = 0.012, below threshold",
        "[INFO]  atlas.api: GET /health 200 OK (2ms)",
        "[INFO]  atlas.runtime: heartbeat #43",
        "[DEBUG] atlas.ai: queue depth = 0",
        "[INFO]  atlas.network: peer atlas-livingroom.local seen",
    ]
    property int logIndex: 0

    Timer {
        interval: 1800; running: true; repeat: true
        onTriggered: {
            logIndex = (logIndex + 1) % logLines.length
            logView.positionViewAtEnd()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 16

        SectionHeader {
            title: "System"
            subtitle: appState.hostname + "  ·  " + appState.ipAddress
        }

        // Stat cards row
        Row {
            width: parent.width
            spacing: 10

            StatCard {
                width: (parent.width - 30) / 4
                label: "CPU"
                value: Math.round(appState.cpuPercent) + "%"
                accent: appState.cpuPercent > 85 ? Theme.danger : Theme.accentCyan
            }
            StatCard {
                width: (parent.width - 30) / 4
                label: "RAM"
                value: Math.round(appState.ramPercent) + "%"
                accent: appState.ramPercent > 85 ? Theme.danger : Theme.accentCyan
            }
            StatCard {
                width: (parent.width - 30) / 4
                label: "Temp"
                value: appState.tempCelsius.toFixed(1) + "°C"
                accent: appState.tempCelsius > 72 ? Theme.danger : Theme.accentCyan
            }
            StatCard {
                width: (parent.width - 30) / 4
                label: "Uptime"
                value: {
                    var s = appState.uptimeSeconds
                    var h = Math.floor(s / 3600)
                    var m = Math.floor((s % 3600) / 60)
                    return (h > 0 ? h + "h " : "") + m + "m"
                }
                accent: Theme.textMuted
            }
        }

        // Lower section: log tail (left) + controls (right)
        Row {
            width: parent.width
            height: parent.height - 92 - 16 - 44 - 16
            spacing: 14

            // Log tail
            Rectangle {
                width: parent.width * 0.62
                height: parent.height
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.borderSubtle; border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Row {
                        spacing: 8
                        Text { text: "Runtime Log"; color: Theme.textPrimary; font.pixelSize: 15; font.bold: true }
                        Rectangle {
                            width: 8; height: 8; radius: 4; color: Theme.success
                            anchors.verticalCenter: parent.verticalCenter
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { to: 0.2; duration: 900 }
                                NumberAnimation { to: 1.0; duration: 900 }
                            }
                        }
                        Text { text: "live"; color: Theme.textMuted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }

                    ListView {
                        id: logView
                        width: parent.width
                        height: parent.height - 36
                        clip: true
                        model: logIndex + 1

                        delegate: Text {
                            width: logView.width
                            text: root.logLines[index % root.logLines.length]
                            color: text.indexOf("[DEBUG]") >= 0 ? Theme.textMuted : Theme.textPrimary
                            font.pixelSize: 12
                            font.family: Theme.fontMono
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }

            // Controls column
            Column {
                width: parent.width * 0.38 - 14
                height: parent.height
                spacing: 12

                // Brightness
                Rectangle {
                    width: parent.width; height: 90
                    radius: Theme.radiusMd
                    color: Theme.bgPanel; border.color: Theme.borderSubtle; border.width: 1

                    Column {
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
                        spacing: 8

                        Row {
                            spacing: 6
                            Text { text: "Brightness"; color: Theme.textMuted; font.pixelSize: 13 }
                            Text { text: appState.brightness + "%"; color: Theme.accentCyan; font.pixelSize: 13; font.family: Theme.fontMono }
                        }

                        // Brightness drag track
                        Item {
                            width: parent.width; height: 24

                            Rectangle {
                                width: parent.width; height: 6; radius: 3; y: 9
                                color: Theme.bgElevated

                                Rectangle {
                                    width: parent.width * (appState.brightness / 100)
                                    height: parent.height; radius: parent.radius
                                    color: Theme.accentAmber
                                }
                            }

                            Rectangle {
                                id: brightnessKnob
                                width: 20; height: 20; radius: 10
                                color: Theme.bgElevated
                                border.color: Theme.accentAmber; border.width: 2
                                y: 2
                                x: (parent.width - width) * (appState.brightness / 100)

                                MouseArea {
                                    anchors.fill: parent; anchors.margins: -6
                                    drag.target: brightnessKnob
                                    drag.axis: Drag.XAxis
                                    drag.minimumX: 0
                                    drag.maximumX: parent.parent.width - brightnessKnob.width
                                    onPositionChanged: {
                                        if (drag.active)
                                            appState.setBrightness(Math.round(
                                                brightnessKnob.x / (parent.parent.width - brightnessKnob.width) * 100))
                                    }
                                }
                            }
                        }
                    }
                }

                // Storage mock
                Rectangle {
                    width: parent.width; height: 90
                    radius: Theme.radiusMd
                    color: Theme.bgPanel; border.color: Theme.borderSubtle; border.width: 1

                    Column {
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
                        spacing: 8

                        Row {
                            spacing: 6
                            Text { text: "Storage"; color: Theme.textMuted; font.pixelSize: 13 }
                            Text { text: "14.2 / 64 GB"; color: Theme.accentCyan; font.pixelSize: 13; font.family: Theme.fontMono }
                        }
                        Rectangle {
                            width: parent.width; height: 8; radius: 4
                            color: Theme.bgElevated
                            Rectangle {
                                width: parent.width * 0.22; height: parent.height; radius: parent.radius
                                color: Theme.accentCyan
                            }
                        }
                    }
                }

                // Power actions
                Column {
                    width: parent.width
                    spacing: 8

                    Text { text: "Power"; color: Theme.textMuted; font.pixelSize: 13 }

                    Row {
                        spacing: 8
                        width: parent.width

                        Rectangle {
                            width: (parent.width - 8) / 2; height: 42; radius: Theme.radiusSm
                            color: Theme.bgElevated
                            border.color: Theme.borderSubtle; border.width: 1

                            Text { anchors.centerIn: parent; text: "Reboot"; color: Theme.accentAmber; font.pixelSize: 14 }
                            MouseArea { anchors.fill: parent; onClicked: appState.requestReboot() }
                        }

                        Rectangle {
                            width: (parent.width - 8) / 2; height: 42; radius: Theme.radiusSm
                            color: Theme.bgElevated
                            border.color: Theme.danger; border.width: 1

                            Text { anchors.centerIn: parent; text: "Shutdown"; color: Theme.danger; font.pixelSize: 14 }
                            MouseArea { anchors.fill: parent; onClicked: appState.requestShutdown() }
                        }
                    }
                }
            }
        }
    }
}
