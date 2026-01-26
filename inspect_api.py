import requests
import json
import os

# Read from .env manually or just hardcode for this inspection script since I know the value
# But I should probably read from .env to be safe if it changes
# Parsing .env simply

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
url = "https://api.sportsgameodds.com/v2/events"

headers = {
    "X-Api-Key": api_key
}

# Also try query param if header fails, but header is standard
# or just print response text if json fails

try:
    print(f"Requesting {url} with key ...")
    response = requests.get(url, headers=headers)
    
    # If 401, try query param
    if response.status_code == 401:
        print("Header auth failed, trying query param 'apiKey'...")
        response = requests.get(url, params={"apiKey": api_key})

    response.raise_for_status()
    data = response.json()
    
    # Print first few items to understand structure
    print("Successfully fetched data!")
    print(json.dumps(data[:3], indent=2)) 
    
    # Also print keys of the first item to see what fields we have
    if data:
        print("\nKeys in first item:", data[0].keys())

except Exception as e:
    print(f"Error: {e}")
    if 'response' in locals():
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text[:500]}")
