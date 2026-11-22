import QtQuick
import QtQuick.Controls
import AtlasUI 1.0
import "../components"

Item {
    id: root

    // Which model row is expanded (showing the param sliders)
    property int expandedRow: -1

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        // Header + download bar
        Row {
            width: parent.width
            height: 44
            spacing: 10

            SectionHeader {
                title: "Models"
                subtitle: "Local GGUF library"
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - dlInput.width - dlBtn.width - 20
            }

            Rectangle {
                id: dlInput
                width: 260; height: 42; radius: Theme.radiusSm
                color: Theme.bgPanel
                border.color: repoField.activeFocus ? Theme.accentCyan : Theme.borderSubtle
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                TextField {
                    id: repoField
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 4 }
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    placeholderText: "HF repo or model id…"
                    placeholderTextColor: Theme.textMuted
                    font.family: Theme.fontMono
                    background: Item {}
                    leftPadding: 8; rightPadding: 8
                }
            }

            Rectangle {
                id: dlBtn
                width: 120; height: 42; radius: Theme.radiusSm
                color: Theme.accentAmber
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "Download"
                    color: Theme.bgPrimary
                    font.pixelSize: 14
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (repoField.text.trim() === "") return
                        llmModel.startDownload(repoField.text.trim())
                        repoField.text = ""
                    }
                }
            }
        }

        // Model cards list
        ListView {
            id: modelList
            width: parent.width
            height: parent.height - 44 - 14
            spacing: 8
            model: llmModel
            clip: true

            delegate: Rectangle {
                id: card
                width: modelList.width
                height: expanded ? 220 : 76
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: status === "loaded" ? Theme.accentCyan : Theme.borderSubtle
                border.width: 1
                clip: true

                readonly property bool expanded: root.expandedRow === index

                Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

                // Summary row
                Row {
                    id: summaryRow
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
                    height: 48
                    spacing: 10

                    // Status dot
                    Rectangle {
                        width: 10; height: 10; radius: 5
                        anchors.verticalCenter: parent.verticalCenter
                        color: status === "loaded" ? Theme.success
                             : status === "downloading" ? Theme.accentAmber
                             : Theme.textMuted
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        width: parent.width - 190

                        Text {
                            text: name
                            color: Theme.textPrimary
                            font.pixelSize: 15
                            font.bold: true
                        }
                        Text {
                            text: quant + "  ·  " + sizeGb.toFixed(1) + " GB  ·  :" + port
                            color: Theme.textMuted
                            font.pixelSize: 12
                            font.family: Theme.fontMono
                        }
                    }

                    // Progress bar (download only)
                    Rectangle {
                        visible: status === "downloading"
                        width: 120; height: 6; radius: 3
                        color: Theme.bgElevated
                        anchors.verticalCenter: parent.verticalCenter

                        Rectangle {
                            width: parent.width * (progress / 100)
                            height: parent.height; radius: parent.radius
                            color: Theme.accentAmber
                            Behavior on width { NumberAnimation { duration: 400 } }
                        }
                    }

                    // Load / Unload button
                    Rectangle {
                        visible: status !== "downloading"
                        width: 100; height: 34; radius: Theme.radiusSm
                        anchors.verticalCenter: parent.verticalCenter
                        color: status === "loaded" ? Theme.danger : Theme.accentCyan

                        Text {
                            anchors.centerIn: parent
                            text: status === "loaded" ? "Unload" : "Load"
                            color: Theme.bgPrimary
                            font.pixelSize: 13; font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: llmModel.toggleLoad(index)
                        }
                    }

                    // Expand / collapse params
                    Rectangle {
                        visible: status !== "downloading"
                        width: 34; height: 34; radius: Theme.radiusSm
                        color: card.expanded ? Theme.bgElevated : "transparent"
                        border.color: Theme.borderSubtle; border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: card.expanded ? "\u25B4" : "\u25BE"
                            color: Theme.textMuted
                            font.pixelSize: 16
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.expandedRow = card.expanded ? -1 : index
                        }
                    }
                }

                // Expanded param panel
                Column {
                    anchors { left: parent.left; right: parent.right; top: summaryRow.bottom; margins: 14 }
                    spacing: 12
                    visible: card.expanded
                    opacity: card.expanded ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 180 } }

                    Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

                    // Temperature slider
                    Column {
                        width: parent.width
                        spacing: 4
                        Row {
                            spacing: 8
                            Text { text: "Temperature"; color: Theme.textMuted; font.pixelSize: 13 }
                            Text {
                                text: temperature.toFixed(2)
                                color: Theme.accentCyan; font.pixelSize: 13; font.family: Theme.fontMono
                            }
                        }
                        Slider {
                            width: parent.width
                            from: 0; to: 2; value: temperature; stepSize: 0.01
                            onMoved: llmModel.setTemperature(index, value)
                        }
                    }

                    // Context size slider
                    Column {
                        width: parent.width
                        spacing: 4
                        Row {
                            spacing: 8
                            Text { text: "Context size"; color: Theme.textMuted; font.pixelSize: 13 }
                            Text {
                                text: contextSize + " tokens"
                                color: Theme.accentCyan; font.pixelSize: 13; font.family: Theme.fontMono
                            }
                        }
                        Slider {
                            width: parent.width
                            from: 512; to: 32768; value: contextSize; stepSize: 512
                            onMoved: llmModel.setContextSize(index, value)
                        }
                    }
                }
            }
        }
    }

    // We use the built-in QML Slider from Qt Quick Controls. It needs no extra import
    // because it is available as just "Slider" in the scope where Qt Quick Controls
    // 2 is enabled (which Material style activates at the app level).
    component Slider: Item {
        property real from: 0
        property real to: 1
        property real value: 0
        property real stepSize: 0.01
        signal moved()
        height: 28

        Rectangle {
            width: parent.width; height: 4; radius: 2; y: 12
            color: Theme.bgElevated

            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, (parent.parent.value - parent.parent.from) / (parent.parent.to - parent.parent.from)))
                height: parent.height; radius: parent.radius
                color: Theme.accentCyan
            }
        }

        Rectangle {
            id: handle
            width: 22; height: 22; radius: 11
            color: Theme.bgElevated
            border.color: Theme.accentCyan; border.width: 2
            y: 3
            x: (parent.width - width) * Math.max(0, Math.min(1, (parent.value - parent.from) / (parent.to - parent.from)))
            Behavior on x { NumberAnimation { duration: 80 } }

            MouseArea {
                id: ma
                anchors.fill: parent
                anchors.margins: -6
                drag.target: handle
                drag.axis: Drag.XAxis
                drag.minimumX: 0
                drag.maximumX: parent.parent.width - handle.width
                onPositionChanged: {
                    if (!drag.active) return
                    var fraction = Math.max(0, Math.min(1, handle.x / (parent.parent.width - handle.width)))
                    var raw = parent.from + fraction * (parent.to - parent.from)
                    parent.value = parent.stepSize > 0
                        ? Math.round(raw / parent.stepSize) * parent.stepSize
                        : raw
                    parent.moved()
                }
            }
        }
    }
}
