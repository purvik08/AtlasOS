import QtQuick
import AtlasUI 1.0

Column {
    property string title: ""
    property string subtitle: ""

    Text {
        text: title
        color: Theme.textPrimary
        font.pixelSize: 20
        font.bold: true
    }
    Text {
        visible: subtitle.length > 0
        text: subtitle
        color: Theme.textMuted
        font.pixelSize: 13
    }
}
