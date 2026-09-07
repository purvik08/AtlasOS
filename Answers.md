You are working on the existing AtlasOS project.

I have reviewed the proposed v1.3.0 architecture decisions. Implement the following decisions carefully WITHOUT breaking existing functionality, APIs, CLI commands, Web UI, Kiosk UI, AI providers, model management, memory system, voice system, or plugin system.

IMPORTANT:
- First inspect the existing project architecture and implementation.
- Do NOT rewrite working modules unnecessarily.
- Preserve existing public APIs and CLI behavior.
- Reuse existing abstractions wherever possible.
- Make the smallest architectural changes necessary.
- Do not introduce dummy/mock functionality into production code.
- Mocks are allowed ONLY in tests.
- Keep AtlasOS offline-first and Raspberry Pi 5 focused.
- Before modifying anything, identify which existing files/modules are affected.
- After implementation, run the existing test suite and add tests for every new behavior.
- Do not claim completion unless the implementation is actually functional.

==================================================
1. NETWORK — NETWORKMANAGER FIRST
==================================================

Make NetworkManager the PRIMARY network backend.

Architecture:

NetworkService
    ↓
NetworkManagerBackend
    ↓
NetworkManager DBus
    ↓
Wi-Fi / Ethernet

Do NOT implement NetworkManager and wpa_supplicant as equal primary backends.

Requirements:
- Preserve the existing NetworkService public API.
- Implement real NetworkManager DBus integration.
- Support real Wi-Fi scanning.
- Support listing available networks.
- Support connecting/disconnecting.
- Support connection status.
- Support Ethernet status where applicable.
- Handle authentication failures and connection failures properly.
- Provide useful error messages.
- Do not fake network state.
- Keep the architecture extensible so a direct wpa_supplicant backend can be added later without changing NetworkService.

wpa_supplicant direct integration is OUT OF SCOPE for v1.3.0 unless the existing architecture already depends on it.

==================================================
2. MEMORY — LOCAL EMBEDDINGS FIRST
==================================================

AtlasOS is offline-first.

Use local embeddings as the preferred implementation.

Preferred order:

Memory request
    ↓
Local sentence-transformers
    ↓
If unavailable → existing hashing embedder fallback
    ↓
MemoryService

Requirements:
- sentence-transformers must NOT become a mandatory requirement for basic AtlasOS operation.
- Preserve the existing hashing fallback.
- Do not require a GPU.
- Do not send memory data to cloud services by default.
- Keep cloud embeddings as an optional future/provider capability.
- Preserve the existing MemoryService API.
- Gracefully handle missing ML dependencies.
- Add tests for local embedding availability and fallback behavior.

==================================================
3. WEB DASHBOARD AUTHENTICATION
==================================================

For v1.3.0 use:

Local authentication
    ↓
JWT/session authentication
    ↓
Role/permission authorization
    ↓
AtlasOS API

Do NOT implement OAuth/OIDC yet.

Requirements:
- Secure authentication.
- Passwords must never be stored in plaintext.
- Secure password hashing.
- Proper token expiration.
- Secure token validation.
- Authentication middleware for protected endpoints.
- Authorization for administrative operations.
- Clearly separate authentication from authorization.
- Protect dangerous operations such as:
  - shutdown
  - reboot
  - model deletion
  - model download
  - configuration changes
  - plugin installation/removal
  - network configuration
  - system updates
- Preserve existing Web UI functionality.
- Do not expose admin APIs without authentication.

Design the authentication layer so OAuth/OIDC can be added later without replacing the existing authorization architecture.

==================================================
4. VOICE AUDIO BACKEND
==================================================

Keep the voice architecture hardware-independent.

Preferred approach:

AtlasOS VoiceService
    ↓
Audio abstraction
    ↓
sounddevice / PortAudio
    ↓
Linux audio subsystem
    ↓
PipeWire / ALSA

Do not tightly couple VoiceService to PipeWire or ALSA-specific APIs unless required.

Requirements:
- Real microphone input.
- Real speaker/output support.
- Device discovery.
- Device selection where supported.
- Graceful handling of missing audio devices.
- Preserve existing wake-word/STT/TTS architecture.
- Keep optional dependencies optional.
- Do not fake successful audio initialization.

Target modern Raspberry Pi OS / Linux environments.

==================================================
5. PLUGIN SECURITY
==================================================

For v1.3.0:

Use in-process plugins + permission checks.

Do NOT introduce seccomp, Firejail, containers, or process isolation unless the current architecture already supports them naturally.

Requirements:
- Preserve the existing PluginService API.
- Define/enforce plugin permissions.
- Plugins must explicitly declare requested capabilities.
- Deny unauthorized operations.
- Log permission violations.
- Prevent plugins from silently accessing protected AtlasOS functionality.
- Clearly document that v1.3.0 plugins are trusted/in-process code.

Prepare the architecture for future process isolation in v1.4.0.

Do not pretend permission checks provide OS-level sandboxing.

==================================================
6. YOCTO TARGET
==================================================

Target:

Raspberry Pi 5
ARM64 / aarch64
64-bit only

Do NOT add 32-bit Raspberry Pi support in v1.3.0.

Keep the Yocto architecture clean and extensible for future hardware targets.

Do not allow 32-bit compatibility work to complicate the current implementation.

==================================================
7. TEST INFRASTRUCTURE
==================================================

Unit tests must NOT require real NetworkManager or wpa_supplicant services.

Use mocks/fakes for:
- NetworkManager DBus
- network state
- unavailable dependencies
- authentication
- audio devices
- plugin permissions

However, do NOT use mocks in production code.

Add integration tests where practical.

Testing strategy:

Unit tests
    ↓
Mock external Linux services
    ↓
AtlasOS integration tests
    ↓
Raspberry Pi hardware tests

If CI does not provide NetworkManager DBus, keep CI tests mocked.

Create a separate hardware/integration test suite that can be executed on a real Raspberry Pi.

==================================================
8. BACKWARD COMPATIBILITY
==================================================

This is critical.

Before changing anything:

1. Inspect the existing architecture.
2. Identify current interfaces.
3. Identify existing CLI commands.
4. Identify Web API contracts.
5. Identify Kiosk/backend interfaces.
6. Identify service lifecycle behavior.
7. Identify existing tests.

Do not change public APIs unless absolutely necessary.

Existing functionality must continue to work:

atlas provider ...
atlas models ...
atlas chat
atlas network ...
atlas doctor
atlas runtime ...
atlas plugins ...
atlas voice ...
Web UI
Kiosk UI
AI providers
llama.cpp
memory
MQTT
plugin system

==================================================
9. IMPLEMENTATION PROCESS
==================================================

Do NOT immediately start editing files.

First produce:

A. Current architecture analysis
B. Files that need modification
C. Files that need creation
D. Existing functionality that will remain unchanged
E. Potential compatibility risks
F. Implementation order
G. Test plan

Then implement incrementally.

Recommended order:

Phase 1:
NetworkManager backend

Phase 2:
Memory embedding provider/fallback cleanup

Phase 3:
Web authentication and authorization

Phase 4:
Voice audio abstraction

Phase 5:
Plugin permissions

Phase 6:
Yocto Raspberry Pi 5 ARM64 configuration

Phase 7:
Unit/integration/hardware tests

After each phase:
- run relevant tests
- verify existing behavior
- fix regressions
- update documentation

==================================================
10. ACCEPTANCE CRITERIA
==================================================

Do not report success simply because the code compiles.

The implementation is complete only when:

[ ] NetworkManager performs real network operations.
[ ] Wi-Fi scanning works.
[ ] Wi-Fi connection/disconnection works.
[ ] Network failures are handled correctly.
[ ] Local embeddings work when sentence-transformers is installed.
[ ] Hashing fallback works without sentence-transformers.
[ ] MemoryService remains functional offline.
[ ] Web authentication is secure and functional.
[ ] Admin authorization works.
[ ] Sensitive APIs are protected.
[ ] Voice audio uses the real audio backend.
[ ] Missing voice dependencies fail gracefully.
[ ] Plugin permissions are enforced.
[ ] No false sandboxing claims are made.
[ ] Raspberry Pi 5 ARM64 is the supported Yocto target.
[ ] Existing CLI commands still work.
[ ] Existing Web UI functionality still works.
[ ] Existing Kiosk functionality still works.
[ ] Existing AI/model functionality still works.
[ ] Existing tests pass.
[ ] New functionality has automated tests.
[ ] No production dummy data was introduced.
[ ] No unnecessary architecture rewrite was performed.

Finally provide:

1. Files changed
2. Files added
3. Architectural changes
4. Backward-compatibility verification
5. Tests executed
6. Test results
7. Remaining limitations
8. Any recommended v1.4.0 work

Do not modify unrelated functionality.
Do not silently remove existing features.
Do not mark a feature as complete if it is only mocked or partially implemented.