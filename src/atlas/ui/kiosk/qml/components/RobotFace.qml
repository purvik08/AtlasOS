import QtQuick
import AtlasUI 1.0

// The always-on ambient "face" shown on the Home screen. Driven entirely by
// two bound properties (mood, micLevel) so it reacts to real state later
// without any changes here -- Voice/Chat just need to set appState.mood.
Item {
    id: root
    width: 360
    height: 360

    property string mood: "idle"      // idle | listening | thinking | speaking | error
    property real micLevel: 0.0

    readonly property color eyeColor: {
        if (mood === "error") return Theme.danger
        if (mood === "thinking" || mood === "speaking") return Theme.accentAmber
        return Theme.accentCyan
    }

    Item {
        id: faceRoot
        anchors.centerIn: parent
        width: 300
        height: 300

        // Gentle idle bob. Suspended during the error shake so the two
        // transforms never fight, and reset to a clean baseline when it stops.
        SequentialAnimation {
            id: bobAnim
            running: root.mood !== "error"
            loops: Animation.Infinite
            onRunningChanged: if (!running) faceRoot.y = 0
            NumberAnimation { target: faceRoot; property: "y"; to: -8; duration: 1600; easing.type: Easing.InOutSine }
            NumberAnimation { target: faceRoot; property: "y"; to: 0; duration: 1600; easing.type: Easing.InOutSine }
        }

        // Outer glow ring, brighter while actively listening. A plain
        // binding (not an "animation on property") so it never gets stuck
        // at an interpolated value when the mood changes.
        Rectangle {
            id: glow
            anchors.centerIn: parent
            width: 260
            height: 220
            radius: 110
            color: "transparent"
            border.width: 2
            border.color: root.eyeColor
            property bool pulseHigh: false
            opacity: root.mood === "listening" ? (pulseHigh ? 0.75 : 0.25) : 0.15

            Behavior on opacity { NumberAnimation { duration: 900; easing.type: Easing.InOutSine } }
            Behavior on border.color { ColorAnimation { duration: 300 } }

            Timer {
                interval: 900
                running: root.mood === "listening"
                repeat: true
                onTriggered: glow.pulseHigh = !glow.pulseHigh
            }
        }

        Row {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -20
            spacing: 46

            Repeater {
                model: 2
                Rectangle {
                    id: eye
                    width: 46
                    height: 60
                    radius: 20
                    color: root.eyeColor
                    transformOrigin: Item.Center

                    Behavior on color { ColorAnimation { duration: 300 } }

                    Timer {
                        interval: 2600 + Math.random() * 2600
                        running: true
                        repeat: true
                        onTriggered: blink.start()
                    }

                    SequentialAnimation {
                        id: blink
                        NumberAnimation { target: eye; property: "scale"; to: 0.08; duration: 70 }
                        NumberAnimation { target: eye; property: "scale"; to: 1.0; duration: 110 }
                    }
                }
            }
        }

        // Thinking indicator: three dots pulsing in sequence.
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.verticalCenter
            anchors.topMargin: 34
            spacing: 10
            visible: root.mood === "thinking"

            Repeater {
                model: 3
                Rectangle {
                    width: 12; height: 12; radius: 6
                    color: Theme.accentAmber
                    opacity: 0.3

                    SequentialAnimation on opacity {
                        running: root.mood === "thinking"
                        loops: Animation.Infinite
                        PauseAnimation { duration: index * 160 }
                        NumberAnimation { to: 1.0; duration: 260 }
                        NumberAnimation { to: 0.3; duration: 260 }
                        PauseAnimation { duration: (2 - index) * 160 }
                    }
                }
            }
        }

        // Speaking indicator: a small equalizer-style mouth driven by micLevel.
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.verticalCenter
            anchors.topMargin: 34
            spacing: 6
            visible: root.mood === "speaking"

            Repeater {
                model: 5
                Rectangle {
                    id: bar
                    width: 8
                    radius: 4
                    color: Theme.accentAmber
                    property real barPhase: index * 0.9
                    height: 6 + (root.micLevel * 40 * (0.5 + Math.abs(Math.sin(barPhase))))

                    Behavior on height { NumberAnimation { duration: 90 } }

                    Timer {
                        interval: 90
                        running: root.mood === "speaking"
                        repeat: true
                        onTriggered: bar.barPhase += 0.6
                    }
                }
            }
        }
    }

    // Quick horizontal shake when an error state is entered.
    SequentialAnimation {
        id: errorShake
        NumberAnimation { target: faceRoot; property: "x"; to: -10; duration: 60 }
        NumberAnimation { target: faceRoot; property: "x"; to: 10; duration: 60 }
        NumberAnimation { target: faceRoot; property: "x"; to: -6; duration: 60 }
        NumberAnimation { target: faceRoot; property: "x"; to: 0; duration: 60 }
    }

    onMoodChanged: if (mood === "error") errorShake.start()
}
