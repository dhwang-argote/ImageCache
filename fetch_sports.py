import requests
import json

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
url = "https://api.sportsgameodds.com/v2/sports"

headers = {
    "X-Api-Key": api_key
}

try:
    print(f"Requesting {url} ...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    print("Successfully fetched sports data!")
    print(json.dumps(data, indent=2))

except Exception as e:
    print(f"Error: {e}")
