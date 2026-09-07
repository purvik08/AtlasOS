# AtlasOS Hardware & Integration Test Suite (Raspberry Pi 5)

This directory contains integration and hardware test scripts intended for execution on physical Raspberry Pi 5 hardware running the AtlasOS Yocto build.

## Prerequisites

1. **Hardware**: Raspberry Pi 5 (4GB or 8GB) with official power supply.
2. **OS**: AtlasOS v1.3.0 Yocto build (`scarthgap`, ARM64).
3. **Peripherals**:
   - Wi-Fi antenna / onboard wireless chip (`wlan0`)
   - USB or I2S Microphone (for Voice input)
   - Speaker / 3.5mm DAC / HDMI audio (for Voice output)
4. **Network**: A test Wi-Fi 2.4GHz / 5GHz access point.

---

## Test Checklist

### 1. Network Subsystem (NetworkManager DBus)
- [ ] Scan Wi-Fi access points:
  ```bash
  atlas network scan
  ```
- [ ] Connect to Wi-Fi:
  ```bash
  atlas network connect --ssid "<SSID>" --password "<PASS>"
  ```
- [ ] Verify connection and IP assignment:
  ```bash
  atlas network status
  ```
- [ ] Disconnect:
  ```bash
  atlas network disconnect
  ```

### 2. Audio & Voice Subsystem
- [ ] List detected hardware audio devices:
  ```bash
  atlas voice devices
  ```
- [ ] Test wake word detection:
  ```bash
  atlas voice test-wake --model alexa
  ```
- [ ] Test STT microphone capture and transcription:
  ```bash
  atlas voice test-stt -d 5.0
  ```
- [ ] Test TTS speaker output:
  ```bash
  atlas voice test-tts "Hello Atlas OS on Raspberry Pi 5"
  ```

### 3. Memory Subsystem
- [ ] Verify local embeddings (SentenceTransformers on CPU / HashEmbedder fallback):
  ```bash
  python -c "from atlas.memory import MemoryService; m = MemoryService(); m.remember('RPI5 Edge Node'); print(m.recall('edge node'))"
  ```

### 4. Web Dashboard & Local Auth
- [ ] Start AtlasOS runtime:
  ```bash
  atlas runtime start
  ```
- [ ] Verify login endpoint returns JWT:
  ```bash
  curl -s -X POST http://localhost:8000/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"<ADMIN_PW>"}'
  ```
- [ ] Verify `/v1/shutdown` and `/v1/models/...` require admin Bearer JWT.

### 5. Plugin Permissions
- [ ] Load a sample plugin with declared capabilities:
  ```bash
  atlas plugins load sample-plugin
  ```
- [ ] Verify undeclared resource access triggers `PermissionDeniedError` in the logs.
