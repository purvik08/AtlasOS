import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * TerminalScreen — Embedded interactive Atlas CLI terminal.
 * Real-time command execution, command history, and quick Atlas actions.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var terminalModel: typeof terminalModel !== "undefined" ? terminalModel : null

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        // 1. Top Header Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
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
                    text: "⌨"
                    font.pixelSize: 20
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Atlas CLI Terminal"
                        font.pixelSize: 15
                        font.bold: true
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "Direct command-line control of AtlasOS subsystems and edge runtime"
                        font.pixelSize: 12
                        font.family: Theme.fontMono
                        color: Theme.textMuted
                    }
                }

                // Quick Action Chips
                Row {
                    spacing: 8

                    AtlasButton {
                        text: "status"
                        variant: "secondary"
                        implicitHeight: 32
                        onClicked: {
                            if (terminalModel) terminalModel.executeCommand("atlas status")
                        }
                    }

                    AtlasButton {
                        text: "models list"
                        variant: "secondary"
                        implicitHeight: 32
                        onClicked: {
                            if (terminalModel) terminalModel.executeCommand("atlas models list")
                        }
                    }

                    AtlasButton {
                        text: "wifi status"
                        variant: "secondary"
                        implicitHeight: 32
                        onClicked: {
                            if (terminalModel) terminalModel.executeCommand("atlas wifi status")
                        }
                    }

                    AtlasButton {
                        text: "Clear"
                        variant: "ghost"
                        implicitHeight: 32
                        onClicked: {
                            if (terminalModel) terminalModel.clear()
                        }
                    }
                }
            }
        }

        // 2. Terminal Console Display Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: "#05070a"
            border.color: Theme.border
            border.width: 1
            clip: true

            Flickable {
                id: terminalFlickable
                anchors.fill: parent
                anchors.margins: 14
                contentWidth: terminalText.paintedWidth
                contentHeight: terminalText.paintedHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    id: vScroll
                    active: true
                    policy: ScrollBar.AsNeeded
                }

                TextEdit {
                    id: terminalText
                    width: terminalFlickable.width
                    readOnly: true
                    selectByMouse: true
                    text: terminalModel ? terminalModel.output : ""
                    font.family: Theme.fontMono
                    font.pixelSize: 13
                    color: "#00e5ff"
                    wrapMode: TextEdit.WrapAnywhere

                    // Auto-scroll on content changes
                    onTextChanged: {
                        Qt.callLater(function() {
                            terminalFlickable.contentY = Math.max(0, terminalFlickable.contentHeight - terminalFlickable.height)
                        })
                    }
                }
            }
        }

        // 3. Command Input Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.borderFocus
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                spacing: 8

                Text {
                    text: terminalModel ? terminalModel.prompt : "atlas@os:~$ "
                    font.family: Theme.fontMono
                    font.pixelSize: 13
                    font.bold: true
                    color: Theme.accentCyan
                }

                TextField {
                    id: cmdInput
                    Layout.fillWidth: true
                    placeholderText: "Type a command... (e.g. 'atlas status', 'atlas models list', 'help')"
                    font.family: Theme.fontMono
                    font.pixelSize: 13
                    color: Theme.textPrimary
                    placeholderTextColor: Theme.textMuted
                    background: null
                    focus: true

                    Keys.onReturnPressed: {
                        runCurrentCommand()
                    }

                    Keys.onUpPressed: {
                        if (terminalModel) {
                            var prev = terminalModel.getHistory(-1)
                            if (prev) cmdInput.text = prev
                        }
                    }

                    Keys.onDownPressed: {
                        if (terminalModel) {
                            var next = terminalModel.getHistory(1)
                            cmdInput.text = next
                        }
                    }
                }

                AtlasButton {
                    text: terminalModel && terminalModel.isBusy ? "Running..." : "Run ↵"
                    variant: "primary"
                    implicitHeight: 36
                    enabled: cmdInput.text.trim().length > 0 && (!terminalModel || !terminalModel.isBusy)
                    onClicked: {
                        runCurrentCommand()
                    }
                }
            }
        }
    }

    function runCurrentCommand() {
        var raw = cmdInput.text.trim()
        if (!raw) return
        if (terminalModel) {
            terminalModel.executeCommand(raw)
        }
        cmdInput.text = ""
    }
}
