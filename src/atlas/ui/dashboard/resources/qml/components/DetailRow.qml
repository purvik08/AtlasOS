import QtQuick
import QtQuick.Layouts

Rectangle {
    property string label
    property string value
    
    color: "transparent"
    height: 44
    border.color: "#44475a"
    border.width: 0
    
    Row {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        
        Text {
            text: label
            font.pixelSize: 14
            color: "#6272a4"
        }
        
        Item { Layout.fillWidth: true }
        
        Text {
            text: value
            font.pixelSize: 14
            font.bold: true
            color: "#f8f8f2"
        }
    }
}