import QtQuick
import AtlasUI 1.0

/**
 * NavBar — Left vertical navigation sidebar with active indicator and touch targets.
 */
Rectangle {
    id: root

    property int currentIndex: 0
    signal tabSelected(int index)

    color: Theme.bgSecondary
    border.color: Theme.borderSubtle
    border.width: 1

    property var navItems: [
        { label: "Dashboard", icon: "⊞", desc: "System Status" },
        { label: "AI Chat",   icon: "💬", desc: "Local Assistant" },
        { label: "Models",    icon: "📦", desc: "GGUF Registry" },
        { label: "Network",   icon: "📶", desc: "WiFi & Mesh" },
        { label: "Voice",     icon: "🎙", desc: "Audio & Wake" },
        { label: "Memory",    icon: "🧠", desc: "Knowledge Base" },
        { label: "System",    icon: "⚙", desc: "Diagnostics" },
        { label: "Terminal",  icon: "⌨", desc: "Atlas CLI" }
    ]

    Column {
        anchors.fill: parent
        anchors.topMargin: Theme.spacingMd
        anchors.bottomMargin: Theme.spacingMd
        spacing: 6

        Repeater {
            model: root.navItems

            Rectangle {
                id: navButton
                width: root.width - 16
                height: 64
                anchors.horizontalCenter: parent.horizontalCenter
                radius: Theme.radiusMd
                color: index === root.currentIndex ? Theme.bgElevated : (mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                border.color: index === root.currentIndex ? Theme.borderFocus : "transparent"
                border.width: 1

                Behavior on color { ColorAnimation { duration: Theme.animFast } }

                // Active left pill
                Rectangle {
                    visible: index === root.currentIndex
                    width: 3
                    height: 28
                    radius: 1.5
                    color: Theme.accentCyan
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        text: modelData.icon
                        font.pixelSize: 18
                        color: index === root.currentIndex ? Theme.accentCyan : Theme.textSecondary
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: modelData.label
                        font.pixelSize: 11
                        font.bold: index === root.currentIndex
                        font.family: Theme.fontSans
                        color: index === root.currentIndex ? Theme.textPrimary : Theme.textMuted
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.tabSelected(index)
                }
            }
        }
    }
}