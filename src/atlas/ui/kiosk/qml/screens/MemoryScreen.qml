import QtQuick
import QtQuick.Controls
import AtlasUI 1.0
import "../components"

Item {
    id: root

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        // Header + search bar
        Row {
            width: parent.width
            height: 44
            spacing: 10

            SectionHeader {
                title: "Memory"
                subtitle: "Robot's persistent knowledge"
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - searchBox.width - 10
            }

            Rectangle {
                id: searchBox
                width: 260; height: 42; radius: Theme.radiusSm
                color: Theme.bgPanel
                border.color: searchField.activeFocus ? Theme.accentCyan : Theme.borderSubtle
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                Row {
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
                    spacing: 8

                    Text { text: "\uD83D\uDD0D"; font.pixelSize: 14; color: Theme.textMuted; anchors.verticalCenter: parent.verticalCenter }

                    TextField {
                        id: searchField
                        width: parent.width - 28
                        color: Theme.textPrimary; font.pixelSize: 13
                        placeholderText: "Search memories…"
                        placeholderTextColor: Theme.textMuted
                        background: Item {}
                        leftPadding: 0; rightPadding: 0
                        topPadding: 0; bottomPadding: 0
                        onTextChanged: memoryModel.search(text)
                    }
                }
            }
        }

        // Memory list
        ListView {
            id: memList
            width: parent.width
            height: parent.height - 44 - 14
            model: memoryModel
            spacing: 8
            clip: true

            delegate: Rectangle {
                width: memList.width
                height: 70
                radius: Theme.radiusMd
                color: Theme.bgPanel
                border.color: Theme.borderSubtle; border.width: 1

                Row {
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 14 }
                    spacing: 12

                    // Category pill
                    Rectangle {
                        width: catLabel.implicitWidth + 16; height: 24; radius: Theme.radiusSm
                        anchors.verticalCenter: parent.verticalCenter
                        color: {
                            if (category === "preference") return Qt.rgba(0.13, 0.83, 0.93, 0.15)
                            if (category === "fact") return Qt.rgba(0.96, 0.65, 0.14, 0.15)
                            return Qt.rgba(0.20, 0.83, 0.60, 0.15)
                        }
                        border.width: 1
                        border.color: {
                            if (category === "preference") return Theme.accentCyan
                            if (category === "fact") return Theme.accentAmber
                            return Theme.success
                        }

                        Text {
                            id: catLabel
                            anchors.centerIn: parent
                            text: category
                            font.pixelSize: 11
                            color: {
                                if (category === "preference") return Theme.accentCyan
                                if (category === "fact") return Theme.accentAmber
                                return Theme.success
                            }
                        }
                    }

                    Column {
                        spacing: 3
                        width: parent.width - 120 - 40
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            text: summary
                            color: Theme.textPrimary; font.pixelSize: 14
                            elide: Text.ElideRight; width: parent.width
                        }
                        Text {
                            text: timestamp
                            color: Theme.textMuted; font.pixelSize: 11
                        }
                    }

                    // Delete button
                    Rectangle {
                        width: 34; height: 34; radius: Theme.radiusSm
                        color: "transparent"
                        border.color: Theme.borderSubtle; border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "\u2715"
                            color: Theme.danger; font.pixelSize: 14
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: memoryModel.deleteEntry(index)
                        }
                    }
                }
            }

            // Empty state
            Text {
                anchors.centerIn: parent
                visible: memList.count === 0
                text: "No memories match your search."
                color: Theme.textMuted; font.pixelSize: 15
            }
        }
    }
}
