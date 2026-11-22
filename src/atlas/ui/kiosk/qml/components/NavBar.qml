import QtQuick
import AtlasUI 1.0

Rectangle {
    id: root
    color: Theme.bgPanel
    border.color: Theme.borderSubtle
    border.width: 1

    property int currentIndex: 0
    signal tabSelected(int index)

    readonly property var items: [
        { label: "Home", icon: "\u25CF" },
        { label: "Chat", icon: "\u2318" },
        { label: "Models", icon: "\u25A6" },
        { label: "Network", icon: "\u25C8" },
        { label: "Voice", icon: "\u25B2" },
        { label: "Memory", icon: "\u25C7" },
        { label: "System", icon: "\u2699" }
    ]

    Column {
        anchors.fill: parent
        anchors.topMargin: 18
        spacing: 4

        Repeater {
            model: root.items

            Rectangle {
                width: root.width - 12
                height: 76
                anchors.horizontalCenter: parent.horizontalCenter
                radius: Theme.radiusMd
                color: index === root.currentIndex ? Theme.bgElevated : "transparent"
                border.color: index === root.currentIndex ? Theme.accentCyan : "transparent"
                border.width: 1

                Behavior on color { ColorAnimation { duration: 150 } }

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        text: modelData.icon
                        color: index === root.currentIndex ? Theme.accentCyan : Theme.textMuted
                        font.pixelSize: 22
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: modelData.label
                        color: index === root.currentIndex ? Theme.textPrimary : Theme.textMuted
                        font.pixelSize: 12
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.tabSelected(index)
                }
            }
        }
    }
}
