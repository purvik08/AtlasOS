import QtQuick
import AtlasUI 1.0

/**
 * AtlasStatusBadge — High-contrast semantic indicator pill.
 */
Rectangle {
    id: root

    property string label: "ONLINE"
    property string status: "success" // "success", "warning", "danger", "info", "offline"

    readonly property color statusColor: {
        if (status === "success" || status === "online" || status === "loaded" || status === "serving") return Theme.success
        if (status === "warning" || status === "degraded" || status === "downloading") return Theme.warning
        if (status === "danger" || status === "error" || status === "unhealthy" || status === "unreachable") return Theme.danger
        if (status === "info") return Theme.accentCyan
        return Theme.offline
    }

    implicitWidth: badgeRow.implicitWidth + 16
    implicitHeight: 24
    radius: Theme.radiusSm
    color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.12)
    border.color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.45)
    border.width: 1

    Row {
        id: badgeRow
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            width: 6; height: 6; radius: 3
            color: root.statusColor
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.label.toUpperCase()
            color: root.statusColor
            font.pixelSize: 11
            font.bold: true
            font.family: Theme.fontMono
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
