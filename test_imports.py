#!/usr/bin/env python
"""Test script to verify imports work correctly."""

try:
    from atlas.ui.kiosk.models import ChatSession
    print("[PASS] ChatSession import successful")
except Exception as e:
    print(f"[FAIL] ChatSession import failed: {e}")

try:
    from atlas.ui.desktop.services import ApiService
    print("[PASS] ApiService import successful")
except Exception as e:
    print(f"[FAIL] ApiService import failed: {e}")

try:
    from atlas.api.sdk import AtlasSDK
    print("[PASS] AtlasSDK import successful")
except Exception as e:
    print(f"[FAIL] AtlasSDK import failed: {e}")

print("Import test completed.")