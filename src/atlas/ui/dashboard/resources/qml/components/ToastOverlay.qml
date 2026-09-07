import QtQuick
import AtlasUI 1.0

/**
 * ToastOverlay — Notification banner supporting semantic statuses.
 */
Item {
    id: root

    property string messageType: "info" // "info", "success", "warning", "danger", "error"

    readonly property color toastBorder: {
        if (messageType === "success") return Theme.success
        if (messageType === "warning") return Theme.warning
        if (messageType === "danger" || messageType === "error") return Theme.danger
        return Theme.accentCyan
    }

    width: Math.min(toastRow.implicitWidth + 36, 480)
    height: 48
    opacity: 0
    y: 20
    visible: opacity > 0

    function show(message, type) {
        label.text = message
        messageType = type || "info"
        opacity = 1
        y = 0
        hideTimer.restart()
    }

    Behavior on opacity { NumberAnimation { duration: Theme.animNormal } }
    Behavior on y { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutBack } }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.color: root.toastBorder
        border.width: 1

        Row {
            id: toastRow
            anchors.centerIn: parent
            spacing: 10

            Text {
                text: {
                    if (root.messageType === "success") return "✓"
                    if (root.messageType === "warning") return "⚠"
                    if (root.messageType === "danger" || root.messageType === "error") return "✕"
                    return "ℹ"
                }
                color: root.toastBorder
                font.pixelSize: 14
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                id: label
                text: ""
                color: Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
                font.family: Theme.fontSans
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    Timer {
        id: hideTimer
        interval: 3200
        onTriggered: {
            root.opacity = 0
            root.y = 20
        }
    }
}
