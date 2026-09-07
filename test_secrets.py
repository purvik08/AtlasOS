#!/usr/bin/env python
"""Test the secrets loading like the AuthManager does."""

from atlas.secrets import get_secrets_manager

def main():
    print("Getting secrets manager...")
    secrets_mgr = get_secrets_manager()
    
    print("Initializing secrets manager...")
    secrets_mgr.initialize()
    
    print("Checking for gemini API key...")
    key = secrets_mgr.get_secret("api_key.gemini")
    if key:
        print(f"Found gemini API key: {key[:20]}...")
    else:
        print("No gemini API key found")
        
    print("Listing all secrets:")
    all_secrets = secrets_mgr.list_secrets()
    print(all_secrets)

if __name__ == "__main__":
    main()