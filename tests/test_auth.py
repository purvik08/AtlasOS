#!/usr/bin/env python
"""Test the AuthManager like the backend does."""

from atlas.config.settings import AtlasConfig
from atlas.api.auth import AuthManager

def main():
    print("Creating AtlasConfig...")
    config = AtlasConfig()
    
    print("Creating AuthManager...")
    auth_manager = AuthManager(config)
    
    print("Getting API key from secrets...")
    from atlas.secrets import get_api_key
    api_key = get_api_key("gemini")
    print(f"API key: {api_key}")
    
    if api_key:
        print("Validating API key...")
        validated_key = auth_manager.validate_api_key(api_key)
        if validated_key:
            print(f"SUCCESS: API key is valid!")
            print(f"  Name: {validated_key.name}")
            print(f"  Scopes: {validated_key.scopes}")
        else:
            print("FAILED: API key is invalid or expired")
    else:
        print("No API key found in secrets")

if __name__ == "__main__":
    main()