import QtQuick
import QtQuick.Layouts

Item {
    property string label: ""
    property var value: ""

    Layout.fillWidth: true
    implicitHeight: statColumn.implicitHeight

    Column {
        id: statColumn
        spacing: 2

        Text {
            text: label
            font.pixelSize: 11
            color: "#6272a4"
        }

        Text {
            text: value !== null && value !== undefined ? String(value) : ""
            font.pixelSize: 16
            font.bold: true
            color: "#f8f8f2"
        }
    }
}