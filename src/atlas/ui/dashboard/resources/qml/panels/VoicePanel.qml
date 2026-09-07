import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root
    property var apiService
    property var appState
    
    Connections {
        target: apiService
        function onError_occurred(error) {
            console.log("Voice error:", error)
        }
    }
    
    Component.onCompleted: {
        apiService.refresh_all()
    }

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 16

        SectionHeader {
            title: "Voice"
            subtitle: "Offline STT / TTS — no cloud dependency"
        }

        // Master toggle card
        Rectangle {
            width: parent.width
            height: 90
            radius: Theme.radiusMd
            color: appState.voiceEnabled ? Theme.bgElevated : Theme.bgPanel
            border.color: appState.voiceEnabled ? Theme.accentCyan : Theme.borderSubtle
            border.width: 1

            Row {
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 20 }
                spacing: 16

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    width: parent.width - 120
                    Text {
                        text: "Voice Control"
                        color: Theme.textPrimary; font.pixelSize: 17; font.bold: true
                    }
                    Text {
                        text: appState.voiceEnabled ? "Active  ·  " + (appState.voiceMode === "wake_word" ? "Wake-word mode" : "Push-to-talk mode") : "Disabled"
                        color: Theme.textMuted; font.pixelSize: 13
                    }
                }

                Item { width: parent.width - 120 - toggleSwitch.width - 32; height: 1 }

                // Toggle switch
                Rectangle {
                    id: toggleSwitch
                    width: 64; height: 34; radius: 17
                    color: appState.voiceEnabled ? Theme.accentCyan : Theme.bgElevated
                    border.color: Theme.borderSubtle; border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Behavior on color { ColorAnimation { duration: 200 } }

                    Rectangle {
                        id: knob
                        width: 26; height: 26; radius: 13
                        color: "white"
                        anchors.verticalCenter: parent.verticalCenter
                        x: appState.voiceEnabled ? parent.width - width - 4 : 4
                        Behavior on x { NumberAnimation { duration: 200 } }
                    }

                    MouseArea { anchors.fill: parent; onClicked: appState.toggleVoice() }
                }
            }
        }

        // Mode selector
        Row {
            width: parent.width
            spacing: 10
            enabled: appState.voiceEnabled

            Repeater {
                model: [
                    { id: "wake_word", label: "Wake Word", desc: "\"Hey Atlas\" to activate" },
                    { id: "push_to_talk", label: "Push to Talk", desc: "Hold button to speak" }
                ]

                Rectangle {
                    width: (parent.width - 10) / 2; height: 80
                    radius: Theme.radiusMd
                    color: Theme.bgPanel
                    border.color: appState.voiceMode === modelData.id ? Theme.accentCyan : Theme.borderSubtle
                    border.width: 1
                    opacity: appState.voiceEnabled ? 1 : 0.4

                    Column {
                        anchors.centerIn: parent; spacing: 6
                        Text { text: modelData.label; color: Theme.textPrimary; font.pixelSize: 15; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: modelData.desc; color: Theme.textMuted; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
                    }

                    MouseArea { anchors.fill: parent; onClicked: if (appState.voiceEnabled) appState.setVoiceMode(modelData.id) }
                }
            }
        }

        // Mic level meter
        Column {
            width: parent.width
            spacing: 10

            Text { text: "Microphone Level"; color: Theme.textMuted; font.pixelSize: 13 }

            Rectangle {
                width: parent.width; height: 22; radius: 11
                color: Theme.bgPanel
                border.color: Theme.borderSubtle; border.width: 1

                Rectangle {
                    id: micBar
                    width: parent.width * appState.micLevel
                    height: parent.height; radius: parent.radius
                    color: appState.micLevel > 0.85 ? Theme.danger : Theme.accentCyan
                    Behavior on width { NumberAnimation { duration: 80 } }
                    Behavior on color { ColorAnimation { duration: 120 } }
                }
            }
        }

        // Last reply preview
        Rectangle {
            width: parent.width
            height: 90
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.borderSubtle; border.width: 1

            Column {
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
                spacing: 6

                Text { text: "Last spoken reply"; color: Theme.textMuted; font.pixelSize: 12 }
                Text {
                    text: "Atlas OS is online. Ask me anything — everything runs locally."
                    color: Theme.textPrimary; font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
            }
        }

        // Quick mood test buttons (developer aid)
        Column {
            width: parent.width
            spacing: 8

            Text { text: "Mood test"; color: Theme.textMuted; font.pixelSize: 12 }
            Row {
                spacing: 8
                Repeater {
                    model: ["idle", "listening", "thinking", "speaking", "error"]
                    Rectangle {
                        width: 110; height: 34; radius: Theme.radiusSm
                        color: appState.mood === modelData ? Theme.accentCyan : Theme.bgElevated
                        border.color: Theme.borderSubtle; border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: appState.mood === modelData ? Theme.bgPrimary : Theme.textMuted
                            font.pixelSize: 13
                        }
                        MouseArea { anchors.fill: parent; onClicked: appState.setMood(modelData) }
                    }
                }
            }
        }
    }
}