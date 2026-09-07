#!/usr/bin/env python
"""Store an API key in secure storage for backend to use."""

from atlas.secrets import set_api_key

def main():
    # Read the API key from file
    with open(r"D:\AtlasOS\test_api_key.txt", "r") as f:
        api_key = f.read().strip()
    
    # Store it as a gemini API key (the backend loads gemini, deepseek, kimi, qwen)
    success = set_api_key("gemini", api_key)
    
    if success:
        print(f"Successfully stored API key for gemini provider")
        print(f"Key: {api_key[:20]}...")
    else:
        print("Failed to store API key")

if __name__ == "__main__":
    main()