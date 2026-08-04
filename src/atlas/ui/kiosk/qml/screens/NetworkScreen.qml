import QtQuick
import AtlasUI 1.0
import "../components"

Item {
    id: root

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 16

        SectionHeader {
            title: "Network"
            subtitle: "WiFi connections  ·  LAN model endpoints  ·  Mesh peers"
        }

        Row {
            width: parent.width
            height: parent.height - 70
            spacing: 14

            // -- WiFi panel --------------------------------------------------
            Rectangle {
                width: (parent.width - 14) * 0.42
                height: parent.height
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.borderSubtle; border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Row {
                        spacing: 10
                        Text { text: "WiFi"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true; anchors.verticalCenter: parent.verticalCenter }
                        Rectangle {
                            width: 60; height: 26; radius: Theme.radiusSm
                            color: Theme.bgElevated
                            border.color: Theme.borderSubtle; border.width: 1
                            anchors.verticalCenter: parent.verticalCenter
                            Text { anchors.centerIn: parent; text: "Scan"; color: Theme.accentCyan; font.pixelSize: 12 }
                            MouseArea { anchors.fill: parent; onClicked: {} }
                        }
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 50
                        model: wifiModel
                        spacing: 6
                        clip: true

                        delegate: Rectangle {
                            width: parent ? parent.width : 0
                            height: 58
                            radius: Theme.radiusSm
                            color: connected ? Theme.bgElevated : "transparent"
                            border.color: connected ? Theme.accentCyan : Theme.borderSubtle
                            border.width: 1

                            Row {
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                                spacing: 8

                                // Signal strength bars
                                Row {
                                    spacing: 2
                                    anchors.verticalCenter: parent.verticalCenter
                                    Repeater {
                                        model: 4
                                        Rectangle {
                                            width: 4
                                            height: 6 + index * 4
                                            radius: 2
                                            anchors.bottom: parent.bottom
                                            color: (signal > index * 25) ? Theme.accentCyan : Theme.bgElevated
                                        }
                                    }
                                }

                                Column {
                                    spacing: 2
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 90

                                    Text {
                                        text: ssid
                                        color: connected ? Theme.textPrimary : Theme.textMuted
                                        font.pixelSize: 14
                                        font.bold: connected
                                    }
                                    Text {
                                        text: (secured ? "\uD83D\uDD12 WPA2" : "Open") + "  ·  " + signal + "dBm"
                                        color: Theme.textMuted; font.pixelSize: 11
                                        font.family: Theme.fontMono
                                    }
                                }

                                Rectangle {
                                    width: 70; height: 28; radius: Theme.radiusSm
                                    color: connected ? "transparent" : Theme.accentCyan
                                    border.color: connected ? Theme.textMuted : "transparent"; border.width: 1
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: connected ? "Connected" : "Connect"
                                        color: connected ? Theme.textMuted : Theme.bgPrimary
                                        font.pixelSize: 11
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: if (!connected) wifiModel.connectTo(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // -- Mesh / model endpoints panel --------------------------------
            Rectangle {
                width: (parent.width - 14) * 0.58
                height: parent.height
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.borderSubtle; border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Row {
                        spacing: 10
                        Text { text: "LAN Model Endpoints"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: Theme.success
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text { text: "mDNS mesh active"; color: Theme.textMuted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }

                    // Column headers
                    Row {
                        width: parent.width
                        spacing: 0
                        Repeater {
                            model: ["Node", "Model", "Address:Port", "Status", ""]
                            Text {
                                width: index === 2 ? 170 : index === 4 ? 40 : (parent.width - 170 - 40) / 3
                                text: modelData
                                color: Theme.textMuted
                                font.pixelSize: 12
                                font.family: Theme.fontMono
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

                    ListView {
                        width: parent.width
                        height: parent.height - 100
                        model: meshModel
                        spacing: 6
                        clip: true

                        delegate: Rectangle {
                            id: meshRow
                            width: parent ? parent.width : 0
                            height: 52
                            radius: Theme.radiusSm
                            color: Theme.bgElevated
                            border.color: isLocal ? Theme.accentCyan : Theme.borderSubtle
                            border.width: 1

                            property bool editing: false

                            Row {
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
                                spacing: 0

                                // Node name
                                Row {
                                    width: (parent.width - 170 - 40) / 3
                                    spacing: 6
                                    Text {
                                        text: isLocal ? "\u2605" : "\u25E6"
                                        color: isLocal ? Theme.accentCyan : Theme.textMuted
                                        font.pixelSize: 14
                                    }
                                    Text {
                                        text: hostname
                                        color: Theme.textPrimary; font.pixelSize: 13
                                        elide: Text.ElideRight
                                        width: parent.width - 20
                                    }
                                }

                                // Model name
                                Text {
                                    width: (parent.width - 170 - 40) / 3
                                    text: modelName
                                    color: Theme.textMuted; font.pixelSize: 12
                                    font.family: Theme.fontMono
                                    elide: Text.ElideRight
                                }

                                // Address (editable for local rows)
                                Item {
                                    width: 170; height: parent.height

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: !meshRow.editing
                                        text: address
                                        color: Theme.accentCyan; font.pixelSize: 13
                                        font.family: Theme.fontMono
                                    }
                                    Rectangle {
                                        visible: meshRow.editing
                                        width: 150; height: 32; radius: Theme.radiusSm
                                        color: Theme.bgPanel
                                        border.color: Theme.accentCyan; border.width: 1
                                        anchors.verticalCenter: parent.verticalCenter

                                        TextInput {
                                            id: addrField
                                            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
                                            text: address
                                            color: Theme.textPrimary; font.pixelSize: 12; font.family: Theme.fontMono
                                            Keys.onReturnPressed: {
                                                meshModel.setAddress(index, text)
                                                meshRow.editing = false
                                            }
                                        }
                                    }
                                }

                                // Status
                                Text {
                                    width: (parent.width - 170 - 40) / 3
                                    text: status
                                    color: status === "serving" ? Theme.success : Theme.danger
                                    font.pixelSize: 12
                                }

                                // Edit icon (local only)
                                Item {
                                    width: 40; height: parent.height
                                    visible: isLocal

                                    Text {
                                        anchors.centerIn: parent
                                        text: meshRow.editing ? "\u2713" : "\u270E"
                                        color: Theme.textMuted; font.pixelSize: 16
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            if (meshRow.editing) {
                                                meshModel.setAddress(index, addrField.text)
                                            }
                                            meshRow.editing = !meshRow.editing
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
