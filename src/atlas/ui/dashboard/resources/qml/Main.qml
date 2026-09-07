import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import AtlasUI 1.0
import "components"
import "screens"

ApplicationWindow {
    id: root

    width: 1280
    height: 800
    minimumWidth: 860
    minimumHeight: 620
    visible: true
    title: "Atlas OS"
    color: Theme.bgPrimary

    property int panelIndex: -1
    property bool isKioskMode: typeof kioskMode !== "undefined" ? kioskMode : false
    property bool isFullscreen: typeof fullscreenMode !== "undefined" ? fullscreenMode : false
    property var atlasAppState: typeof appState !== "undefined" ? appState : null
    property var atlasApiService: typeof apiService !== "undefined" ? apiService : null
    property var atlasChatModel: typeof chatModel !== "undefined" ? chatModel : null
    property var atlasLlmModel: typeof llmModel !== "undefined" ? llmModel : null
    property var atlasMemoryModel: typeof memoryModel !== "undefined" ? memoryModel : null
    property var atlasWifiModel: typeof wifiModel !== "undefined" ? wifiModel : null
    property var atlasMeshModel: typeof meshModel !== "undefined" ? meshModel : null
    property var atlasTerminalModel: typeof terminalModel !== "undefined" ? terminalModel : null
    property var panelNames: [
        "Setup", "Dashboard", "Chat", "Models", "Providers", "Network",
        "Voice", "Memory", "Plugins", "System", "Terminal"
    ]

    function openPanel(index) {
        panelIndex = Math.max(0, Math.min(index, panelNames.length - 1))
        panelSwipe.currentIndex = panelIndex
    }

    function closeToIdle() {
        panelIndex = -1
        if (atlasAppState) atlasAppState.setMood("idle")
    }

    function handleIdleSwipe(dx, dy) {
        if (Math.abs(dx) < 70 && Math.abs(dy) < 70) return
        if (Math.abs(dy) > Math.abs(dx) && dy < -70) {
            openPanel(1)
        } else if (dx > 70) {
            openPanel(0)
        } else if (dx < -70) {
            openPanel(5)
        }
    }

    Component.onCompleted: {
        if (atlasApiService) atlasApiService.startAutoRefresh()
        if (atlasMemoryModel) atlasMemoryModel.fetchRequested()
        if (atlasApiService) atlasApiService.fetch_plugins()
        if (isKioskMode && isFullscreen) root.visibility = Window.FullScreen
    }

    onClosing: {
        if (atlasApiService) atlasApiService.shutdown()
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.bgPrimary
    }

    IdleEyesScreen {
        id: idleScreen
        anchors.fill: parent
        visible: root.panelIndex < 0
        opacity: visible ? 1 : 0
        appState: root.atlasAppState
        apiService: root.atlasApiService
        modelCount: root.atlasLlmModel ? root.atlasLlmModel.rowCount() : 0
        memoryCount: root.atlasMemoryModel ? root.atlasMemoryModel.count : 0
        pluginCount: root.atlasApiService ? root.atlasApiService.pluginList.length : 0
        onOpenRequested: function(index) { root.openPanel(index) }

        Behavior on opacity { NumberAnimation { duration: 180 } }
    }

    MouseArea {
        id: idleGesture
        anchors.fill: parent
        enabled: root.panelIndex < 0
        property real startX: 0
        property real startY: 0
        onPressed: function(mouse) {
            startX = mouse.x
            startY = mouse.y
        }
        onReleased: function(mouse) {
            root.handleIdleSwipe(mouse.x - startX, mouse.y - startY)
        }
    }

    Item {
        id: panelShell
        anchors.fill: parent
        visible: root.panelIndex >= 0
        opacity: visible ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: 180 } }

        Rectangle {
            id: topBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 62
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingLg
                anchors.rightMargin: Theme.spacingLg
                spacing: 14

                AtlasButton {
                    text: "Eyes"
                    variant: "secondary"
                    implicitWidth: 78
                    implicitHeight: 38
                    onClicked: root.closeToIdle()
                }

                Rectangle {
                    width: 1
                    height: 26
                    color: Theme.borderSubtle
                }

                Text {
                    text: root.panelIndex >= 0 ? root.panelNames[root.panelIndex] : "Atlas OS"
                    color: Theme.textPrimary
                    font.pixelSize: 17
                    font.bold: true
                    Layout.preferredWidth: 130
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: panelTabs.width
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true

                    Row {
                        id: panelTabs
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 7

                        Repeater {
                            model: root.panelNames
                            delegate: Rectangle {
                                width: Math.max(74, tabText.implicitWidth + 24)
                                height: 34
                                radius: Theme.radiusSm
                                color: index === root.panelIndex ? Qt.rgba(0, 229, 255, 0.14) : Theme.bgPanel
                                border.color: index === root.panelIndex ? Theme.accentCyan : Theme.border
                                border.width: 1

                                Text {
                                    id: tabText
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: index === root.panelIndex ? Theme.accentCyan : Theme.textSecondary
                                    font.pixelSize: 12
                                    font.bold: index === root.panelIndex
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.openPanel(index)
                                }
                            }
                        }
                    }
                }

                AtlasStatusBadge {
                    label: root.atlasApiService && root.atlasApiService.connected ? "online" : "offline"
                    status: root.atlasApiService && root.atlasApiService.connected ? "success" : "offline"
                }

                Text {
                    id: clockText
                    color: Theme.textSecondary
                    font.family: Theme.fontMono
                    font.pixelSize: 13

                    Timer {
                        interval: 1000
                        running: true
                        repeat: true
                        triggeredOnStart: true
                        onTriggered: clockText.text = Qt.formatTime(new Date(), "HH:mm:ss")
                    }
                }
            }
        }

        SwipeView {
            id: panelSwipe
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: topBar.bottom
            anchors.bottom: hintBar.top
            currentIndex: Math.max(root.panelIndex, 0)
            clip: true
            interactive: true
            onCurrentIndexChanged: root.panelIndex = currentIndex

            SetupScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                llmModel: root.atlasLlmModel
                memoryModel: root.atlasMemoryModel
                wifiModel: root.atlasWifiModel
                onOpenPanel: function(index) { root.openPanel(index) }
            }

            HomeScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                llmModel: root.atlasLlmModel
                memoryModel: root.atlasMemoryModel
                wifiModel: root.atlasWifiModel
            }

            ChatScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                chatModel: root.atlasChatModel
                llmModel: root.atlasLlmModel
            }

            ModelsScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                llmModel: root.atlasLlmModel
            }

            ProvidersScreen {
                apiService: root.atlasApiService
            }

            NetworkScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                wifiModel: root.atlasWifiModel
                meshModel: root.atlasMeshModel
            }

            VoiceScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
            }

            MemoryScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
                memoryModel: root.atlasMemoryModel
            }

            PluginsScreen {
                apiService: root.atlasApiService
            }

            SystemScreen {
                appState: root.atlasAppState
                apiService: root.atlasApiService
            }

            TerminalScreen {
                appState: root.atlasAppState
                terminalModel: root.atlasTerminalModel
            }
        }

        Rectangle {
            id: hintBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 34
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle

            Text {
                anchors.centerIn: parent
                text: "Swipe left or right to move between OS panels. Tap Eyes to return to idle."
                color: Theme.textMuted
                font.pixelSize: 12
            }
        }
    }

    ToastOverlay {
        id: toastOverlay
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.panelIndex < 0 ? 24 : 48
        z: 100
    }

    Connections {
        target: root.atlasAppState
        function onToastRequested(message, type) {
            toastOverlay.show(message, type)
        }
    }

    Connections {
        target: root.atlasApiService
        function onError_occurred(err) {
            toastOverlay.show(err, "error")
        }
        function onModel_operation_result(modelId, success, message) {
            toastOverlay.show(message, success ? "success" : "error")
        }
        function onModel_download_completed(modelId, success, message) {
            toastOverlay.show(message, success ? "success" : "error")
        }
        function onWifi_connect_completed(ssid, success, message) {
            toastOverlay.show(message || (success ? "Network operation complete" : "Network operation failed"), success ? "success" : "error")
        }
        function onSpeak_completed(success, message) {
            toastOverlay.show(message, success ? "success" : "warning")
        }
    }
}
