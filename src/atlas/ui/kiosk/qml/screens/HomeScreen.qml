import QtQuick
import AtlasUI 1.0
import "../components"

Item {
    id: root

    // Cycle through moods for demo; real backend sets these via appState.mood
    Timer {
        interval: 3800
        running: true
        repeat: true
        property var moods: ["idle", "listening", "thinking", "speaking", "idle", "idle"]
        property int idx: 0
        onTriggered: {
            idx = (idx + 1) % moods.length
            appState.setMood(moods[idx])
        }
    }

    // Background particle grid (static ambient texture)
    Canvas {
        id: grid
        anchors.fill: parent
        opacity: 0.06
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = Theme.accentCyan
            ctx.lineWidth = 0.5
            for (var x = 0; x < width; x += 40) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
            }
            for (var y = 0; y < height; y += 40) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
            }
        }
    }

    // Centre: animated face
    RobotFace {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -30
        mood: appState.mood
        micLevel: appState.micLevel
    }

    // Bottom ribbon: live stats
    Row {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 14

        StatCard {
            width: 160; label: "CPU"
            value: Math.round(appState.cpuPercent) + "%"
            accent: appState.cpuPercent > 85 ? Theme.danger : Theme.accentCyan
        }
        StatCard {
            width: 160; label: "RAM"
            value: Math.round(appState.ramPercent) + "%"
            accent: appState.ramPercent > 85 ? Theme.danger : Theme.accentCyan
        }
        StatCard {
            width: 160; label: "Temp"
            value: appState.tempCelsius.toFixed(1) + "°C"
            accent: appState.tempCelsius > 72 ? Theme.danger : Theme.accentCyan
        }
        StatCard {
            width: 180; label: "Uptime"
            value: {
                var s = appState.uptimeSeconds
                var h = Math.floor(s / 3600)
                var m = Math.floor((s % 3600) / 60)
                var sec = s % 60
                return (h > 0 ? h + "h " : "") + (m > 0 ? m + "m " : "") + sec + "s"
            }
            accent: Theme.textMuted
        }
    }

    // Mood badge top-right
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 16
        radius: Theme.radiusSm
        color: Theme.bgElevated
        border.color: Theme.borderSubtle
        border.width: 1
        width: moodLabel.implicitWidth + 20
        height: 30

        Text {
            id: moodLabel
            anchors.centerIn: parent
            text: appState.mood.toUpperCase()
            color: Theme.accentCyan
            font.pixelSize: 12
            font.family: Theme.fontMono
        }
    }
}
