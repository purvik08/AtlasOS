import QtQuick
import QtQuick.Controls
import AtlasUI 1.0

/**
 * AtlasButton — Modern tactile button for desktop & touch kiosk.
 * Supports primary, secondary, ghost, danger variants and loading/disabled states.
 */
Rectangle {
    id: root

    property string text: ""
    property string iconText: ""
    property string variant: "primary"  // "primary", "secondary", "ghost", "danger"
    property bool loading: false
    signal clicked()

    implicitWidth: Math.max(buttonRow.implicitWidth + 32, 96)
    implicitHeight: 44
    radius: Theme.radiusSm

    // Variant color calculation
    color: {
        if (!enabled) return Theme.bgSurface
        if (variant === "primary") return mouseArea.pressed ? Qt.darker(Theme.accent, 1.15) : (mouseArea.containsMouse ? Theme.accentHover : Theme.accent)
        if (variant === "danger") return mouseArea.pressed ? Qt.darker(Theme.danger, 1.2) : (mouseArea.containsMouse ? Qt.lighter(Theme.danger, 1.1) : Theme.danger)
        if (variant === "secondary") return mouseArea.pressed ? Theme.bgSurface : (mouseArea.containsMouse ? Theme.bgElevated : Theme.bgPanel)
        // ghost
        return mouseArea.pressed ? Qt.rgba(1, 1, 1, 0.08) : (mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
    }

    border.color: {
        if (variant === "secondary") return mouseArea.containsMouse ? Theme.borderFocus : Theme.border
        if (variant === "ghost") return mouseArea.containsMouse ? Theme.borderSubtle : "transparent"
        return "transparent"
    }
    border.width: 1

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on scale { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutQuad } }

    scale: mouseArea.pressed && enabled ? 0.97 : 1.0

    Row {
        id: buttonRow
        anchors.centerIn: parent
        spacing: 8
        opacity: root.loading ? 0 : (root.enabled ? 1.0 : 0.45)

        Text {
            visible: root.iconText !== ""
            text: root.iconText
            font.pixelSize: 16
            color: root.variant === "primary" || root.variant === "danger" ? Theme.textPrimary : Theme.accentCyan
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.text
            font.pixelSize: 14
            font.bold: true
            font.family: Theme.fontSans
            color: root.variant === "primary" || root.variant === "danger" ? Theme.textPrimary : (root.variant === "ghost" ? Theme.textPrimary : Theme.textPrimary)
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // Loading spinner
    AtlasLoadingIndicator {
        anchors.centerIn: parent
        visible: root.loading
        size: 20
        color: root.variant === "primary" || root.variant === "danger" ? Theme.textPrimary : Theme.accentCyan
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled && !root.loading
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
