import QtQuick

Rectangle {
    id: root
    property bool selected: false
    property var modelData: null
    signal clicked()

    width: parent.width
    height: 64
    color: selected ? "#bd93f9" : "transparent"
    opacity: selected ? 0.85 : 1.0
    radius: 6
    border.color: selected ? "#bd93f9" : "transparent"
    border.width: selected ? 2 : 0

    MouseArea {
        anchors.fill: parent
        onClicked: root.clicked()
    }

    Row {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Provider indicator
        Rectangle {
            width: 36
            height: 36
            radius: 18
            color: "#bd93f9"
            opacity: 0.2

            Text {
                anchors.centerIn: parent
                text: modelData && modelData.provider ? modelData.provider.charAt(0).toUpperCase() : "?"
                font.pixelSize: 14
                font.bold: true
                color: "#bd93f9"
            }
        }

        Column {
            spacing: 2
            anchors.verticalCenter: parent.verticalCenter

            Text {
                text: modelData ? (modelData.provider + " / " + modelData.model) : ""
                font.pixelSize: 13
                font.bold: true
                color: selected ? "#bd93f9" : "#f8f8f2"
            }

            Text {
                text: modelData ? (modelData.message_count + " messages") : ""
                font.pixelSize: 11
                color: selected ? "#bd93f9" : "#6272a4"
            }
        }
    }
}