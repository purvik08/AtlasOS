import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * MemoryScreen — Persistent memory knowledge base with real semantic search and CRUD.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var memoryModel: typeof memoryModel !== "undefined" ? memoryModel : null
    property var apiService: typeof apiService !== "undefined" ? apiService : null

    property bool showAddDialog: false

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        // 1. Header & Search Bar
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
                    text: "🧠"
                    font.pixelSize: 20
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Persistent Knowledge Base"
                        font.pixelSize: 15
                        font.bold: true
                        color: Theme.textPrimary
                    }
                    Text {
                        text: (memoryModel ? memoryModel.count : 0) + " memories stored in local vector store"
                        font.pixelSize: 12
                        font.family: Theme.fontMono
                        color: Theme.textMuted
                    }
                }

                AtlasSearchField {
                    placeholderText: "Semantic memory search..."
                    onSearchChanged: function(query) {
                        if (memoryModel) memoryModel.search(query)
                    }
                }

                AtlasButton {
                    text: "+ Remember Fact"
                    variant: "primary"
                    onClicked: {
                        root.showAddDialog = true
                    }
                }
            }
        }

        // 2. Memory Items List
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border
            border.width: 1
            clip: true

            ListView {
                id: memoryListView
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingSm
                model: memoryModel
                clip: true

                delegate: Rectangle {
                    width: memoryListView.width
                    height: 72
                    radius: Theme.radiusSm
                    color: Theme.bgSecondary
                    border.color: Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        // Category badge
                        Rectangle {
                            implicitWidth: catLabel.implicitWidth + 16
                            implicitHeight: 24
                            radius: Theme.radiusXs
                            color: Qt.rgba(0, 229, 255, 0.1)
                            border.color: Theme.accentCyan
                            border.width: 1

                            Text {
                                id: catLabel
                                anchors.centerIn: parent
                                text: category.toUpperCase()
                                font.pixelSize: 10
                                font.bold: true
                                font.family: Theme.fontMono
                                color: Theme.accentCyan
                            }
                        }

                        // Summary Text
                        Column {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: summary
                                font.pixelSize: 14
                                font.family: Theme.fontSans
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: timestamp + "  ·  Source: " + source
                                font.pixelSize: 11
                                font.family: Theme.fontMono
                                color: Theme.textMuted
                            }
                        }

                        // Delete button
                        AtlasIconButton {
                            iconText: "✕"
                            iconColor: Theme.danger
                            tooltip: "Delete memory"
                            implicitWidth: 32
                            implicitHeight: 32
                            onClicked: {
                                if (memoryModel) memoryModel.deleteEntry(index)
                            }
                        }
                    }
                }

                AtlasEmptyState {
                    anchors.centerIn: parent
                    visible: !memoryModel || memoryModel.rowCount() === 0
                    iconText: "🧠"
                    title: "No Memories Found"
                    message: "AtlasOS stores assistant knowledge, preferences, and facts locally."
                    actionText: "Remember a Fact"
                    onActionClicked: {
                        root.showAddDialog = true
                    }
                }
            }
        }
    }

    // Add Memory Modal Dialog
    Rectangle {
        visible: root.showAddDialog
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.75)
        z: 50

        AtlasCard {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 500)
            height: 300

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Text {
                    text: "Store New Memory Fact"
                    font.pixelSize: 17
                    font.bold: true
                    color: Theme.textPrimary
                }

                Text {
                    text: "Saved facts are embedded and stored in the local vector database for LLM retrieval."
                    font.pixelSize: 12
                    color: Theme.textMuted
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: "Category:"
                        font.pixelSize: 13
                        font.family: Theme.fontMono
                        color: Theme.textSecondary
                    }

                    ComboBox {
                        id: categorySelector
                        Layout.fillWidth: true
                        implicitHeight: 38
                        model: ["Fact", "Preference", "Rule", "Note", "System"]
                    }
                }

                AtlasTextField {
                    id: factInput
                    Layout.fillWidth: true
                    placeholderText: "e.g. Raspberry Pi 5 runs offline local inference..."
                }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }

                    AtlasButton {
                        text: "Cancel"
                        variant: "ghost"
                        onClicked: {
                            factInput.text = ""
                            root.showAddDialog = false
                        }
                    }

                    AtlasButton {
                        text: "Save Memory"
                        variant: "primary"
                        enabled: factInput.text.trim().length > 0
                        onClicked: {
                            var txt = factInput.text.trim()
                            if (txt.length > 0) {
                                var cat = categorySelector.currentText ? categorySelector.currentText.toLowerCase() : "fact"
                                if (memoryModel) {
                                    memoryModel.addEntry(txt, cat, "user")
                                }
                                factInput.text = ""
                                root.showAddDialog = false
                            }
                        }
                    }
                }
            }
        }
    }
}
