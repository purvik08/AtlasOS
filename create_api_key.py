#!/usr/bin/env python
"""Create an API key for testing."""

import asyncio
from atlas.config.settings import AtlasConfig
from atlas.api.auth import AuthManager

async def main():
    # Create config
    config = AtlasConfig()
    
    # Create auth manager
    auth_manager = AuthManager(config)
    
    # Create an API key
    raw_key, api_key_record = auth_manager.create_api_key("test-key", ["chat", "models", "sessions"])
    
    print(f"Created API key: {raw_key}")
    print(f"Key hash: {api_key_record.key_hash}")
    print(f"Name: {api_key_record.name}")
    print(f"Scopes: {api_key_record.scopes}")
    
    # Save the key to a file so we can use it later
    with open("test_api_key.txt", "w") as f:
        f.write(raw_key)
    
    print("API key saved to test_api_key.txt")

if __name__ == "__main__":
    asyncio.run(main())