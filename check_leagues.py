import requests
import json

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
base_url = "https://api.sportsgameodds.com/v2/"
endpoints = ["leagues", "sports"]

headers = {"X-Api-Key": api_key}

for ep in endpoints:
    url = f"{base_url}{ep}"
    print(f"Checking {url}...")
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            print(f"SUCCESS ({ep}):")
            try:
                data = resp.json()
                print(json.dumps(data, indent=2)[:500]) # First 500 chars
            except:
                print("Could not parse JSON")
        else:
            print(f"FAILED ({ep}): Status {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
