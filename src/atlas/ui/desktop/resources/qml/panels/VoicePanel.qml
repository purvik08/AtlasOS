import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.1

Item {
    property var apiService
    
    property var voiceDevices: []
    property bool wakeWordListening: false
    property bool transcribing: false
    property string ttsText: ""
    property string ttsVoice: ""
    property bool speaking: false
    property string lastTranscript: ""
    
    // Voice Device Item Component (must be defined before use)
    Component {
        id: voiceDeviceItemComponent
        ItemDelegate {
            width: parent.width
            height: 100
            
            contentItem: Rectangle {
                anchors.fill: parent
                color: "transparent"
                radius: 6
                border.color: "#44475a"
                border.width: 1
                
                Column {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8
                    
                    Row {
                        spacing: 12
                        
                        Rectangle {
                            width: 48
                            height: 48
                            radius: 12
                            color: "#bd93f9"
                            opacity: 0.2
                            border.color: "#bd93f9"
                            border.width: 2
                            
                            Text {
                                anchors.centerIn: parent
                                text: modelData.is_input ? "🎤" : "🔊"
                                font.pixelSize: 20
                            }
                        }
                        
                        Column {
                            spacing: 2
                            
                            Text {
                                text: modelData.name
                                font.pixelSize: 16
                                font.bold: true
                                color: "#f8f8f2"
                            }
                            
                            Row {
                                spacing: 16
                                
                                Text {
                                    text: modelData.is_input ? "Input" : "Output"
                                    font.pixelSize: 12
                                    color: "#bd93f9"
                                }
                                
                                Text {
                                    text: modelData.sample_rate + " Hz"
                                    font.pixelSize: 11
                                    color: "#6272a4"
                                }
                                
                                Text {
                                    text: modelData.channels + " ch"
                                    font.pixelSize: 11
                                    color: "#6272a4"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
// Tab Button Component
    Component {
        id: tabButtonComponent
        Button {
            property bool active: false
            
            Layout.fillWidth: true
            height: 40
            flat: true
            font.pixelSize: 13
            font.bold: active
            
            background: Rectangle {
                color: active ? "#bd93f9" : "transparent"
                opacity: active ? 0.15 : 0
                radius: 6
                border.color: active ? "#bd93f9" : "transparent"
                border.width: active ? 2 : 0
            }
            
            contentItem: Text {
                text: parent.text
                font.pixelSize: 13
                font.bold: active
                color: active ? "#bd93f9" : "#f8f8f2"
                verticalAlignment: Text.AlignVCenter
            }
            
            onClicked: parent.clicked()
        }
    }
        
        Connections {
        target: apiService
        onVoiceDevicesChanged: {
            voiceDevices = apiService.voice_devices
        }
        onWakeWordDetected: {
            lastTranscript = "Wake word detected!"
        }
        onTranscriptReceived: {
            lastTranscript = transcript
        }
    }
    
    Component.onCompleted: {
        apiService.fetch_voice_devices()
    }
    
    property int currentTab: 0
    
    // Devices Tab - uses parent apiService and voiceDevices
    Component {
        id: voiceDevicesTabComponent
        Item {
            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.vertical: ScrollBar { }
                
                Column {
                    width: parent.width
                    spacing: 20
                    anchors.margins: 24
                    
                    // Header
                    Row {
                        width: parent.width
                        spacing: 16
                        
                        Text {
                            text: "Audio Devices"
                            font.pixelSize: 22
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        Text {
                            verticalAlignment: Text.AlignVCenter
                            text: voiceDevices.length + " devices"
                            font.pixelSize: 14
                            color: "#6272a4"
                        }
                        
                        Button {
                            text: "Refresh"
                            onClicked: apiService.fetch_voice_devices()
                        }
                    }
                    
                    // Devices list
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#282a36"
                        radius: 8
                        border.color: "#44475a"
                        border.width: 1
                        
                        ListView {
                            anchors.fill: parent
                            clip: true
                            model: voiceDevices
                            spacing: 4
                            anchors.margins: 8
                            
                            delegate: Component {
                                ItemDelegate {
                                    width: parent.width
                                    height: 100
                                    
                                    contentItem: Rectangle {
                                        anchors.fill: parent
                                        color: "transparent"
                                        radius: 6
                                        border.color: "#44475a"
                                        border.width: 1
                                        
                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 16
                                            spacing: 8
                                            
                                            Row {
                                                spacing: 12
                                                
                                                Rectangle {
                                                    width: 48
                                                    height: 48
                                                    radius: 12
                                                    color: "#bd93f9"
                                                    opacity: 0.2
                                                    border.color: "#bd93f9"
                                                    border.width: 2
                                                    
                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: modelData.is_input ? "🎤" : "🔊"
                                                        font.pixelSize: 20
                                                    }
                                                }
                                                
                                                Column {
                                                    spacing: 2
                                                    
                                                    Text {
                                                        text: modelData.name
                                                        font.pixelSize: 16
                                                        font.bold: true
                                                        color: "#f8f8f2"
                                                    }
                                                    
                                                    Row {
                                                        spacing: 16
                                                        
                                                        Text {
                                                            text: modelData.is_input ? "Input" : "Output"
                                                            font.pixelSize: 12
                                                            color: "#bd93f9"
                                                        }
                                                        
                                                        Text {
                                                            text: modelData.sample_rate + " Hz"
                                                            font.pixelSize: 11
                                                            color: "#6272a4"
                                                        }
                                                        
                                                        Text {
                                                            text: modelData.channels + " ch"
                                                            font.pixelSize: 11
                                                            color: "#6272a4"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Empty state
                            footer: Item {
                                width: parent.width
                                height: voiceDevices.length === 0 ? 200 : 0
                                visible: voiceDevices.length === 0
                                
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 16
                                    
                                    Text {
                                        text: "No audio devices found"
                                        font.pixelSize: 16
                                        color: "#6272a4"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Wake Word Tab
    Component {
        id: wakeWordTabComponent
        Item {
            // Uses parent apiService, wakeWordListening, lastTranscript
            signal start()
            signal stop()
            
            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.vertical: ScrollBar { }
                
                Column {
                    width: parent.width
                    spacing: 20
                    anchors.margins: 24
                    
                    // Header
                    Row {
                        width: parent.width
                        spacing: 16
                        
                        Text {
                            text: "Wake Word Detection"
                            font.pixelSize: 22
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Item { Layout.fillWidth: true }
                    }
                    
                    // Main card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#282a36"
                        radius: 8
                        border.color: "#44475a"
                        border.width: 1
                        
                        Column {
                            anchors.fill: parent
                            anchors.margins: 32
                            spacing: 24
                            
                            // Wake word indicator
                            Rectangle {
                                width: 120
                                height: 120
                                radius: 60
                                color: wakeWordListening ? "#50fa7b" : "#282a36"
                                border.color: wakeWordListening ? "#50fa7b" : "#44475a"
                                border.width: 3
                                Behavior on color { ColorAnimation { duration: 300 } }
                                
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 8
                                    
                                    Text {
                                        text: "🎤"
                                        font.pixelSize: 48
                                    }
                                    
                                    Text {
                                        text: wakeWordListening ? "Listening..." : "Click to Start"
                                        font.pixelSize: 18
                                        font.bold: true
                                        color: wakeWordListening ? "#50fa7b" : "#f8f8f2"
                                    }
                                }
                            }
                            
                            // Status text
                            Text {
                                text: wakeWordListening ? "Say \"Atlas\" to activate" : "Click the button to start listening for wake word"
                                font.pixelSize: 14
                                color: "#6272a4"
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            
                            // Start/Stop button
                            Button {
                                text: wakeWordListening ? "Stop Listening" : "Start Wake Word Detection"
                                Layout.fillWidth: true
                                height: 48
                                onClicked: {
                                    if (wakeWordListening) {
                                        // Stop
                                    } else {
                                        start()
                                    }
                                }
                            }
                            
                            // Last transcript
                            Rectangle {
                                visible: lastTranscript.length > 0
                                Layout.fillWidth: true
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                                
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 8
                                    
                                    Text {
                                        text: "Last Detection"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: "#6272a4"
                                    }
                                    
                                    Text {
                                        text: lastTranscript
                                        font.pixelSize: 14
                                        color: "#f8f8f2"
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // STT Tab
    Component {
        id: sttTabComponent
        Item {
            signal start()
            signal stop()
            
            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.vertical: ScrollBar { }
                
                Column {
                    width: parent.width
                    spacing: 20
                    anchors.margins: 24
                    
                    // Header
                    Row {
                        width: parent.width
                        spacing: 16
                        
                        Text {
                            text: "Speech-to-Text"
                            font.pixelSize: 22
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Item { Layout.fillWidth: true }
                    }
                    
                    // Main card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#282a36"
                        radius: 8
                        border.color: "#44475a"
                        border.width: 1
                        
                        Column {
                            anchors.fill: parent
                            anchors.margins: 32
                            
                            // Recording indicator
                            Rectangle {
                                width: 120
                                height: 120
                                radius: 60
                                color: transcribing ? "#ff5555" : "#282a36"
                                border.color: transcribing ? "#ff5555" : "#44475a"
                                border.width: 3
                                Behavior on color { ColorAnimation { duration: 300 } }
                                
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 8
                                    
                                    Text {
                                        text: transcribing ? "⏺" : "🎤"
                                        font.pixelSize: 48
                                    }
                                    
                                    Text {
                                        text: transcribing ? "Recording..." : "Click to Record"
                                        font.pixelSize: 18
                                        font.bold: true
                                        color: transcribing ? "#ff5555" : "#f8f8f2"
                                    }
                                }
                            }
                            
                            // Status text
                            Text {
                                text: transcribing ? "Speak now... (5 seconds)" : "Click to start recording (5 seconds)"
                                font.pixelSize: 14
                                color: "#6272a4"
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            
                            // Start/Stop button
                            Button {
                                text: transcribing ? "Stop Recording" : "Start Recording (5s)"
                                Layout.fillWidth: true
                                height: 48
                                onClicked: {
                                    if (transcribing) {
                                        // Stop
                                    } else {
                                        start()
                                    }
                                }
                            }
                            
                            // Transcript
                            Rectangle {
                                visible: lastTranscript.length > 0
                                Layout.fillWidth: true
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                                
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 8
                                    
                                    Row {
                                        spacing: 8
                                        Text {
                                            text: "Transcript"
                                            font.pixelSize: 13
                                            font.bold: true
                                            color: "#6272a4"
                                        }
                                        
                                        Button {
                                            text: "Copy"
                                            flat: true
                                            onClicked: {
                                                // Copy to clipboard
                                                QtGui.QGuiApplication.clipboard().setText(lastTranscript)
                                            }
                                        }
                                    }
                                    
                                    Text {
                                        text: lastTranscript
                                        font.pixelSize: 14
                                        color: "#f8f8f2"
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // TTS Tab
    Component {
        id: ttsTabComponent
        Item {
            signal textChanged(string text)
            signal voiceChanged(string voice)
            signal speak(string text, string voice)
            signal stop()
            
            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.vertical: ScrollBar { }
                
                Column {
                    width: parent.width
                    spacing: 20
                    anchors.margins: 24
                    
                    // Header
                    Row {
                        width: parent.width
                        spacing: 16
                        
                        Text {
                            text: "Text-to-Speech"
                            font.pixelSize: 22
                            font.bold: true
                            color: "#f8f8f2"
                        }
                        
                        Item { Layout.fillWidth: true }
                    }
                    
                    // Input area
Rectangle {
                                Layout.fillWidth: true
                                color: "#1e1e2e"
                                radius: 8
                                border.color: "#44475a"
                                border.width: 1
                                
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 16
                            
                            Text {
                                text: "Enter text to synthesize"
                                font.pixelSize: 13
                                color: "#6272a4"
                            }
                            
                            TextArea {
                                id: ttsInput
                                Layout.fillWidth: true
                                height: 120
                                placeholderText: "Enter text to speak..."
                                font.pixelSize: 14
                                color: "#f8f8f2"
                                placeholderTextColor: "#6272a4"
                                onTextChanged: textChanged(text)
                                
                                background: Rectangle {
                                    color: "#1e1e2e"
                                    radius: 6
                                    border.color: "#44475a"
                                    border.width: 1
                                }
                            }
                            
                            Row {
                                spacing: 12
                                
                                // Voice selector
                                Column {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    
                                    Text {
                                        text: "Voice"
                                        font.pixelSize: 12
                                        color: "#6272a4"
                                    }
                                    
                                    ComboBox {
                                        id: voiceCombo
                                        width: parent.width
                                        height: 40
                                        model: ["Default", "Female", "Male", "Robotic"]
                                        currentIndex: 0
                                        onActivated: voiceChanged(model[index])
                                        
                                        Binding {
                                            target: voiceCombo
                                            property: "currentIndex"
                                            value: voiceCombo.model.indexOf(ttsVoice)
                                        }
                                        
                                        Binding {
                                            target: ttsVoice
                                            property: "value"
                                            value: voiceCombo.currentText
                                        }
                                        
                                        background: Rectangle {
                                            color: "#1e1e2e"
                                            radius: 6
                                            border.color: "#44475a"
                                            border.width: 1
                                        }
                                    }
                                }
                                
                                // Speak button
                                Button {
                                    text: speaking ? "Speaking..." : "Speak"
                                    Layout.fillWidth: true
                                    height: 44
                                    enabled: ttsInput.text.trim().length > 0 && !speaking
                                    onClicked: {
                                        speak(ttsInput.text, ttsVoice)
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Preview/Status
Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#282a36"
                        radius: 8
                        border.color: "#44475a"
                        border.width: 1
                        
                        Column {
                            anchors.centerIn: parent
                            spacing: 16
                        
                        Rectangle {
                            width: 80
                            height: 80
                            radius: 40
                            color: speaking ? "#bd93f9" : "#282a36"
                            border.color: speaking ? "#bd93f9" : "#44475a"
                            border.width: 2
                            Behavior on color { ColorAnimation { duration: 300 } }
                            
                            Text {
                                anchors.centerIn: parent
                                text: speaking ? "🔊" : "🔇"
                                font.pixelSize: 32
                            }
                        }
                        
                        Text {
                            text: speaking ? "Speaking..." : "Ready"
                            font.pixelSize: 18
                            font.bold: true
                            color: speaking ? "#bd93f9" : "#f8f8f2"
                        }
                    }
                }
            }
        }
    }
    
    }