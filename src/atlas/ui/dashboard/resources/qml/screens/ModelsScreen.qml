import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

/**
 * ModelsScreen — Real-time AI model management, GGUF library, downloading, and runtime loading.
 */
Item {
    id: root

    property var appState: typeof appState !== "undefined" ? appState : null
    property var apiService: typeof apiService !== "undefined" ? apiService : null
    property var llmModel: typeof llmModel !== "undefined" ? llmModel : null

    property int expandedIndex: -1
    property bool showDownloadModal: false
    property bool isDownloading: false

    Connections {
        target: apiService
        function onModel_download_completed(model_id, success, message) {
            root.isDownloading = false
            root.showDownloadModal = false
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        // 1. Header & Actions
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
                    text: "📦"
                    font.pixelSize: 20
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "GGUF Model Registry"
                        font.pixelSize: 15
                        font.bold: true
                        color: Theme.textPrimary
                    }
                    Text {
                        text: (llmModel && llmModel.rowCount() > 0 ? (llmModel.rowCount() + " models available on device") : "No models registered")
                        font.pixelSize: 12
                        font.family: Theme.fontMono
                        color: Theme.textMuted
                    }
                }

                AtlasButton {
                    text: "+ Download Model"
                    iconText: "⬇"
                    variant: "primary"
                    onClicked: {
                        root.showDownloadModal = true
                    }
                }

                AtlasButton {
                    text: "Rescan Folder"
                    iconText: "↻"
                    variant: "secondary"
                    onClicked: {
                        if (llmModel) llmModel.rescanModels()
                    }
                }
            }
        }

        // 2. Model Cards List
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusMd
            color: Theme.bgPanel
            border.color: Theme.border
            border.width: 1
            clip: true

            ListView {
                id: modelListView
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingMd
                model: llmModel
                clip: true

                delegate: Rectangle {
                    id: modelCard
                    width: modelListView.width
                    height: expanded ? 180 : 80
                    radius: Theme.radiusMd
                    color: loaded ? Qt.rgba(0, 229, 255, 0.05) : Theme.bgSecondary
                    border.color: loaded ? Theme.accentCyan : Theme.borderSubtle
                    border.width: 1
                    clip: true

                    readonly property bool expanded: root.expandedIndex === index

                    Behavior on height { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: Theme.animFast } }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingMd
                        spacing: 8

                        // Summary Row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Rectangle {
                                width: 10; height: 10; radius: 5
                                color: loaded ? Theme.success : (status === "loading" ? Theme.warning : Theme.offline)
                            }

                            Column {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: name
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.family: Theme.fontSans
                                    color: Theme.textPrimary
                                }

                                Row {
                                    spacing: 8
                                    Text {
                                        text: quant + "  ·  " + (sizeGb > 0 ? sizeGb.toFixed(2) + " GB" : "Local") + "  ·  " + provider
                                        font.pixelSize: 12
                                        font.family: Theme.fontMono
                                        color: Theme.textMuted
                                    }
                                }
                            }

                            AtlasStatusBadge {
                                label: loaded ? "LOADED" : (status === "loading" ? "LOADING..." : "STANDBY")
                                status: loaded ? "success" : (status === "loading" ? "warning" : "offline")
                            }

                            AtlasButton {
                                text: loaded ? "Unload" : "Load"
                                variant: loaded ? "danger" : "primary"
                                implicitWidth: 90
                                implicitHeight: 38
                                onClicked: {
                                    if (llmModel) {
                                        if (loaded) {
                                            llmModel.unloadModel(name)
                                        } else {
                                            llmModel.loadModel(name)
                                        }
                                    }
                                }
                            }

                            AtlasIconButton {
                                iconText: "🗑"
                                iconColor: Theme.danger
                                tooltip: "Delete model"
                                implicitWidth: 38
                                implicitHeight: 38
                                visible: !loaded
                                onClicked: {
                                    if (llmModel) llmModel.deleteModel(name, true)
                                }
                            }

                            AtlasIconButton {
                                iconText: modelCard.expanded ? "▲" : "▼"
                                implicitWidth: 38
                                implicitHeight: 38
                                onClicked: {
                                    root.expandedIndex = modelCard.expanded ? -1 : index
                                }
                            }
                        }

                        // Expanded Parameters
                        Rectangle {
                            visible: modelCard.expanded
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.borderSubtle
                        }

                        RowLayout {
                            visible: modelCard.expanded
                            Layout.fillWidth: true
                            spacing: Theme.spacingLg

                            Column {
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: "Temperature: " + (temperature ? temperature.toFixed(2) : "0.70")
                                    font.pixelSize: 12
                                    font.family: Theme.fontMono
                                    color: Theme.textSecondary
                                }
                                Slider {
                                    width: parent.width
                                    from: 0.0; to: 1.5; value: temperature || 0.7; stepSize: 0.05
                                    onMoved: if (llmModel) llmModel.setTemperature(index, value)
                                }
                            }

                            Column {
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: "Context Size: " + (contextSize || 4096) + " tokens"
                                    font.pixelSize: 12
                                    font.family: Theme.fontMono
                                    color: Theme.textSecondary
                                }
                                Slider {
                                    width: parent.width
                                    from: 512; to: 16384; value: contextSize || 4096; stepSize: 512
                                    onMoved: if (llmModel) llmModel.setContextSize(index, value)
                                }
                            }
                        }
                    }
                }

                // Empty State
                AtlasEmptyState {
                    anchors.centerIn: parent
                    visible: !llmModel || llmModel.rowCount() === 0
                    iconText: "🤖"
                    title: "No AI Models Registered"
                    message: "Download a GGUF model from Hugging Face or place .gguf files in models/ directory."
                    actionText: "Download a Model"
                    onActionClicked: {
                        root.showDownloadModal = true
                    }
                }
            }
        }
    }

    // Download Model Modal Dialog
    Rectangle {
        visible: root.showDownloadModal
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.75)
        z: 60

        AtlasCard {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 540)
            height: 380

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Text {
                    text: "Download GGUF Model"
                    font.pixelSize: 17
                    font.bold: true
                    color: Theme.textPrimary
                }

                Text {
                    text: "Download models from Hugging Face or via direct URL into the models/ folder."
                    font.pixelSize: 12
                    font.family: Theme.fontSans
                    color: Theme.textMuted
                }

                AtlasTextField {
                    id: modelIdInput
                    Layout.fillWidth: true
                    placeholderText: "Model ID (e.g. tinyllama-1.1b)"
                }

                AtlasTextField {
                    id: repoInput
                    Layout.fillWidth: true
                    placeholderText: "Hugging Face Repo (e.g. TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF)"
                }

                AtlasTextField {
                    id: filenameInput
                    Layout.fillWidth: true
                    placeholderText: "Filename (e.g. tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf)"
                }

                AtlasTextField {
                    id: urlInput
                    Layout.fillWidth: true
                    placeholderText: "Or Direct Download URL (optional)"
                }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }

                    AtlasButton {
                        text: "Cancel"
                        variant: "ghost"
                        enabled: !root.isDownloading
                        onClicked: root.showDownloadModal = false
                    }

                    AtlasButton {
                        text: root.isDownloading ? "Downloading..." : "Start Download"
                        variant: "primary"
                        loading: root.isDownloading
                        enabled: modelIdInput.text.trim().length > 0 && ((repoInput.text.trim().length > 0 && filenameInput.text.trim().length > 0) || urlInput.text.trim().length > 0)
                        onClicked: {
                            root.isDownloading = true
                            if (llmModel) {
                                llmModel.downloadModel(
                                    modelIdInput.text.trim(),
                                    urlInput.text.trim(),
                                    repoInput.text.trim(),
                                    filenameInput.text.trim(),
                                    "",
                                    false
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
