import QtQuick
import QtQuick.Window
import AtlasUI 1.0
import "components"
import "screens"

// Root window. Targets 1280x720 (Raspberry Pi Touch Display 2).
Window {
    id: root
    width: 1280
    height: 720
    visible: true
    title: "Atlas OS"
    color: Theme.bgPrimary

    // Header bar (top)
    Rectangle {
        id: header
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 48
        color: Theme.bgPanel
        border.color: Theme.borderSubtle; border.width: 1
        z: 10

        Row {
            anchors { left: parent.left; verticalCenter: parent.verticalCenter; leftMargin: 18 }
            spacing: 10

            // Atlas logotype
            Text {
                text: "ATLAS"
                color: Theme.accentCyan
                font.pixelSize: 18; font.bold: true; font.family: Theme.fontMono
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "OS"
                color: Theme.textMuted
                font.pixelSize: 18; font.family: Theme.fontMono
                anchors.verticalCenter: parent.verticalCenter
            }

            Rectangle { width: 1; height: 20; color: Theme.borderSubtle; anchors.verticalCenter: parent.verticalCenter }

            // Mood / state indicator
            Rectangle {
                width: moodText.implicitWidth + 16; height: 22; radius: Theme.radiusSm
                color: Theme.bgElevated
                border.color: Theme.accentCyan; border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    id: moodText
                    anchors.centerIn: parent
                    text: appState.mood.toUpperCase()
                    color: Theme.accentCyan; font.pixelSize: 11; font.family: Theme.fontMono
                }
            }
        }

        // Right: IP + hostname + time
        Row {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter; rightMargin: 18 }
            spacing: 20

            Text { text: appState.ipAddress; color: Theme.textMuted; font.pixelSize: 13; font.family: Theme.fontMono; anchors.verticalCenter: parent.verticalCenter }
            Text { text: appState.hostname; color: Theme.textMuted; font.pixelSize: 13; font.family: Theme.fontMono; anchors.verticalCenter: parent.verticalCenter }

            Rectangle { width: 1; height: 20; color: Theme.borderSubtle; anchors.verticalCenter: parent.verticalCenter }

            Text {
                id: clock
                color: Theme.textPrimary; font.pixelSize: 14; font.family: Theme.fontMono
                anchors.verticalCenter: parent.verticalCenter
                Timer {
                    interval: 1000; running: true; repeat: true; triggeredOnStart: true
                    onTriggered: {
                        var d = new Date()
                        clock.text = Qt.formatTime(d, "HH:mm:ss")
                    }
                }
            }
        }
    }

    // Nav bar (left)
    NavBar {
        id: navBar
        anchors { left: parent.left; top: header.bottom; bottom: parent.bottom }
        width: 110
        currentIndex: stack.currentIndex
        onTabSelected: stack.currentIndex = index
    }

    // Screen content area
    Item {
        anchors { left: navBar.right; right: parent.right; top: header.bottom; bottom: parent.bottom }

        // All seven screens live in the StackLayout-equivalent ItemGroup.
        // Only the active screen is visible; the rest are hidden (not
        // destroyed) so models retain their live state while off-screen.
        Repeater {
            model: 7
            Item {
                anchors.fill: parent
                visible: index === stack.currentIndex
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 160 } }

                Loader {
                    anchors.fill: parent
                    source: [
                        "screens/HomeScreen.qml",
                        "screens/ChatScreen.qml",
                        "screens/ModelsScreen.qml",
                        "screens/NetworkScreen.qml",
                        "screens/VoiceScreen.qml",
                        "screens/MemoryScreen.qml",
                        "screens/SystemScreen.qml"
                    ][index]
                }
            }
        }

        // This invisible Item holds the currentIndex used to select the active screen
        Item { id: stack; property int currentIndex: 0 }
    }

    // Toast overlay — sits above everything
    ToastOverlay {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        z: 100
    }

    Component.onCompleted: {
        if (typeof fullscreenMode !== "undefined" && fullscreenMode)
            root.visibility = Window.FullScreen
    }

    // Forward appState.toastRequested to the overlay
    Connections {
        target: appState
        function onToastRequested(message) { toast.show(message) }
    }
}
