import QtQuick
import QtQuick.Layouts
import AtlasUI 1.0
import "../components"

Item {
    id: root

    property var appState: null
    property var apiService: null
    property int modelCount: 0
    property int memoryCount: 0
    property int pluginCount: 0
    signal openRequested(int index)

    Rectangle {
        anchors.fill: parent
        color: Theme.bgPrimary
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.86, 760)
        height: Math.min(parent.height * 0.62, 500)
        radius: 34
        color: "#070a10"
        border.color: Qt.rgba(0, 229, 255, 0.24)
        border.width: 1
    }

    RobotFace {
        id: face
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.62, 560)
        height: Math.min(parent.height * 0.38, 340)
        mood: apiService && apiService.connected ? (appState ? appState.mood : "idle") : "error"
        micLevel: appState ? appState.micLevel : 0
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 34
        spacing: 10
        width: Math.min(parent.width - 48, 720)

        RowLayout {
            width: parent.width
            spacing: 10

            AtlasStatusBadge {
                label: apiService && apiService.connected ? "online" : "offline"
                status: apiService && apiService.connected ? "success" : "danger"
            }

            Text {
                Layout.fillWidth: true
                text: (appState ? appState.hostname : "atlas") + " / " + (appState ? appState.ipAddress : "127.0.0.1")
                color: Theme.textSecondary
                font.family: Theme.fontMono
                font.pixelSize: 13
                elide: Text.ElideRight
            }

            Text {
                text: modelCount + " models / " + memoryCount + " memories / " + pluginCount + " plugins"
                color: Theme.textMuted
                font.family: Theme.fontMono
                font.pixelSize: 12
            }
        }

        Text {
            width: parent.width
            text: "Swipe up for Dashboard. Swipe right for Setup. Swipe left for Network."
            color: Theme.textMuted
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.leftMargin: 26
        anchors.verticalCenter: parent.verticalCenter
        width: 110
        height: 36
        radius: Theme.radiusSm
        color: Qt.rgba(255,255,255,0.04)
        border.color: Theme.borderSubtle
        Text { anchors.centerIn: parent; text: "Network"; color: Theme.textSecondary; font.pixelSize: 12; font.family: Theme.fontMono }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.rightMargin: 26
        anchors.verticalCenter: parent.verticalCenter
        width: 110
        height: 36
        radius: Theme.radiusSm
        color: Qt.rgba(255,255,255,0.04)
        border.color: Theme.borderSubtle
        Text { anchors.centerIn: parent; text: "Setup"; color: Theme.textSecondary; font.pixelSize: 12; font.family: Theme.fontMono }
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 22
        width: 132
        height: 36
        radius: Theme.radiusSm
        color: Qt.rgba(255,255,255,0.04)
        border.color: Theme.borderSubtle
        Text { anchors.centerIn: parent; text: "Dashboard"; color: Theme.textSecondary; font.pixelSize: 12; font.family: Theme.fontMono }
    }
}
