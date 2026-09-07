import QtQuick
import AtlasUI 1.0

Item {
    id: root

    property string mood: "idle"
    property real micLevel: 0.0

    readonly property color activeColor: {
        if (mood === "error") return Theme.danger
        if (mood === "thinking") return Theme.accentAmber
        if (mood === "speaking") return Theme.accentGreen
        if (mood === "listening") return Theme.accentCyan
        return Theme.accentCyan
    }

    width: 520
    height: 320

    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: parent.width * 0.86
        height: parent.height * 0.78
        radius: 42
        color: Qt.rgba(root.activeColor.r, root.activeColor.g, root.activeColor.b, 0.035)
        border.color: Qt.rgba(root.activeColor.r, root.activeColor.g, root.activeColor.b, pulse.high ? 0.55 : 0.22)
        border.width: 1

        Behavior on border.color { ColorAnimation { duration: 260 } }
    }

    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.72
        height: parent.height * 0.52
        radius: 34
        color: "#06090e"
        border.color: Qt.rgba(root.activeColor.r, root.activeColor.g, root.activeColor.b, 0.34)
        border.width: 1
    }

    Row {
        id: eyes
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -8
        spacing: 58

        Repeater {
            model: 2

            Rectangle {
                id: eye
                width: 112
                height: blink.closed ? 12 : (root.mood === "thinking" ? 38 : 72)
                radius: height / 2
                color: root.activeColor
                opacity: pulse.high ? 1.0 : 0.78
                y: root.mood === "thinking" ? Math.sin(sweep.phase + index) * 10 : 0

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.34
                    height: Math.max(4, parent.height * 0.22)
                    radius: height / 2
                    color: "white"
                    opacity: root.mood === "idle" && !blink.closed ? 0.18 : 0.06
                }

                Behavior on height { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
                Behavior on y { NumberAnimation { duration: 180; easing.type: Easing.InOutSine } }
                Behavior on color { ColorAnimation { duration: 220 } }
            }
        }
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: eyes.bottom
        anchors.topMargin: 32
        spacing: 8
        visible: root.mood === "speaking" || root.mood === "listening"

        Repeater {
            model: 9
            Rectangle {
                property real wave: Math.abs(Math.sin(sweep.phase + index * 0.7))
                width: 8
                height: 8 + (root.mood === "speaking" ? wave * 34 : root.micLevel * 30)
                radius: 4
                color: root.activeColor
                opacity: 0.8
                anchors.verticalCenter: parent.verticalCenter

                Behavior on height { NumberAnimation { duration: 80 } }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        text: root.mood.toUpperCase()
        color: Qt.rgba(root.activeColor.r, root.activeColor.g, root.activeColor.b, 0.82)
        font.family: Theme.fontMono
        font.pixelSize: 12
        font.bold: true
        font.letterSpacing: 1.4
    }

    QtObject {
        id: blink
        property bool closed: false
    }

    QtObject {
        id: pulse
        property bool high: false
    }

    QtObject {
        id: sweep
        property real phase: 0
    }

    SequentialAnimation {
        running: true
        loops: Animation.Infinite
        PauseAnimation { duration: 2200 }
        PropertyAction { target: blink; property: "closed"; value: true }
        PauseAnimation { duration: 90 }
        PropertyAction { target: blink; property: "closed"; value: false }
        PauseAnimation { duration: 4200 }
        PropertyAction { target: blink; property: "closed"; value: true }
        PauseAnimation { duration: 80 }
        PropertyAction { target: blink; property: "closed"; value: false }
    }

    SequentialAnimation {
        running: true
        loops: Animation.Infinite
        PropertyAction { target: pulse; property: "high"; value: true }
        PauseAnimation { duration: 900 }
        PropertyAction { target: pulse; property: "high"; value: false }
        PauseAnimation { duration: 900 }
    }

    NumberAnimation {
        target: sweep
        property: "phase"
        from: 0
        to: 6.283
        duration: 1600
        loops: Animation.Infinite
        running: root.mood === "thinking" || root.mood === "speaking"
    }
}
