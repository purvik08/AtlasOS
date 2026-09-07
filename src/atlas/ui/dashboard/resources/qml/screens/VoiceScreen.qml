import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root

    property var appState: null
    property var apiService: null

    function voiceValue(group, key, fallback) {
        if (!apiService || !apiService.voiceStatus || !apiService.voiceStatus[group]) return fallback
        return apiService.voiceStatus[group][key] !== undefined ? apiService.voiceStatus[group][key] : fallback
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        clip: true

        ColumnLayout {
            width: parent.width
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
                        Text { anchors.centerIn: parent; text: "VO"; color: Theme.accentCyan; font.bold: true; font.family: Theme.fontMono }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 3
                        Text { text: "Voice & Speech Engine"; color: Theme.textPrimary; font.pixelSize: 18; font.bold: true }
                        Text { text: "Wake word, speech recognition, synthesis, and audio devices."; color: Theme.textMuted; font.pixelSize: 12 }
                    }

                    AtlasStatusBadge {
                        label: root.voiceValue("audio", "available", false) ? "audio ready" : "limited"
                        status: root.voiceValue("audio", "available", false) ? "success" : "warning"
                    }

                    AtlasButton {
                        text: appState && appState.voiceEnabled ? "Voice On" : "Voice Off"
                        variant: appState && appState.voiceEnabled ? "primary" : "secondary"
                        onClicked: if (appState) appState.toggleVoice()
                    }

                    AtlasButton {
                        text: "Refresh"
                        variant: "secondary"
                        onClicked: if (apiService) apiService.refresh_all()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 760 ? 3 : 1
                columnSpacing: Theme.spacingMd
                rowSpacing: Theme.spacingMd

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 140
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 7
                        Text { text: "Wake Word"; color: Theme.textPrimary; font.bold: true }
                        AtlasStatusBadge {
                            label: root.voiceValue("wake_word", "enabled", false) ? "enabled" : "disabled"
                            status: root.voiceValue("wake_word", "enabled", false) ? "success" : "offline"
                        }
                        Text { text: "Model: " + root.voiceValue("wake_word", "model", "openWakeWord"); color: Theme.textMuted; font.pixelSize: 12 }
                    }
                }

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 140
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 7
                        Text { text: "Speech To Text"; color: Theme.textPrimary; font.bold: true }
                        AtlasStatusBadge {
                            label: root.voiceValue("stt", "available", false) ? "ready" : "unavailable"
                            status: root.voiceValue("stt", "available", false) ? "success" : "offline"
                        }
                        Text { text: root.voiceValue("stt", "engine", "faster-whisper") + " / " + root.voiceValue("stt", "model", "base"); color: Theme.textMuted; font.pixelSize: 12 }
                    }
                }

                AtlasCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 140
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 7
                        Text { text: "Text To Speech"; color: Theme.textPrimary; font.bold: true }
                        AtlasStatusBadge {
                            label: root.voiceValue("tts", "available", false) ? "ready" : "unavailable"
                            status: root.voiceValue("tts", "available", false) ? "success" : "offline"
                        }
                        Text { text: root.voiceValue("tts", "engine", "piper") + " / " + root.voiceValue("tts", "voice", "default"); color: Theme.textMuted; font.pixelSize: 12 }
                    }
                }
            }

            AtlasCard {
                Layout.fillWidth: true
                Layout.minimumHeight: 132

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Input Level & Mode"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: appState ? Math.round(appState.micLevel * 100) + "%" : "0%"; color: Theme.accentCyan; font.family: Theme.fontMono }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 12
                        radius: 6
                        color: Theme.bgElevated
                        Rectangle {
                            width: Math.max(8, parent.width * (appState ? appState.micLevel : 0.04))
                            height: parent.height
                            radius: parent.radius
                            color: appState && appState.micLevel > 0.85 ? Theme.danger : Theme.accentCyan
                            Behavior on width { NumberAnimation { duration: 80 } }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Activation:"; color: Theme.textSecondary; font.pixelSize: 13 }
                        AtlasButton { text: "Wake Word"; variant: appState && appState.voiceMode === "wake_word" ? "primary" : "secondary"; onClicked: if (appState) appState.setVoiceMode("wake_word") }
                        AtlasButton { text: "Push To Talk"; variant: appState && appState.voiceMode === "push_to_talk" ? "primary" : "secondary"; onClicked: if (appState) appState.setVoiceMode("push_to_talk") }
                    }
                }
            }

            AtlasCard {
                Layout.fillWidth: true
                Layout.minimumHeight: 118

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    Text { text: "Speech Test"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                    RowLayout {
                        Layout.fillWidth: true
                        AtlasTextField {
                            id: ttsInput
                            Layout.fillWidth: true
                            placeholderText: "Text to speak through Atlas"
                            text: "Atlas OS voice is online."
                        }
                        AtlasButton {
                            text: "Speak"
                            variant: "primary"
                            enabled: ttsInput.text.trim().length > 0
                            onClicked: if (apiService) apiService.speak_text(ttsInput.text.trim())
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 250
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.border
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: Theme.spacingSm

                    Text { text: "Audio Devices"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                    ListView {
                        id: audioList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        model: {
                            if (!apiService) return []
                            var inputs = apiService.voiceDevices.inputs || []
                            var outputs = apiService.voiceDevices.outputs || []
                            var merged = []
                            for (var i = 0; i < inputs.length; i++) merged.push({kind: "input", data: inputs[i]})
                            for (var j = 0; j < outputs.length; j++) merged.push({kind: "output", data: outputs[j]})
                            return merged
                        }

                        delegate: Rectangle {
                            width: audioList.width
                            height: 56
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10
                                Text { text: modelData.kind === "input" ? "IN" : "OUT"; color: Theme.accentCyan; font.family: Theme.fontMono; font.bold: true }
                                Column {
                                    Layout.fillWidth: true
                                    Text { text: modelData.data.name || "Audio device"; color: Theme.textPrimary; font.pixelSize: 13; elide: Text.ElideRight; width: parent.width }
                                    Text { text: (modelData.data.channels || 0) + " channels / " + (modelData.data.default_sample_rate || "--") + " Hz"; color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontMono }
                                }
                                AtlasStatusBadge { label: modelData.data.is_default ? "default" : modelData.kind; status: modelData.data.is_default ? "success" : "offline" }
                            }
                        }

                        AtlasEmptyState {
                            anchors.centerIn: parent
                            visible: audioList.count === 0
                            iconText: "AU"
                            title: "No Audio Devices"
                            message: "Atlas could not enumerate audio devices from the backend."
                            actionText: "Refresh"
                            onActionClicked: if (apiService) apiService.refresh_all()
                        }
                    }
                }
            }
        }
    }
}
