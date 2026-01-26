import requests
import json

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
url = "https://api.sportsgameodds.com/v2/teams"

headers = {
    "X-Api-Key": api_key
}

params = {
    "sportID": "SOCCER" # Adding required filter
}

try:
    print(f"Requesting {url} with sportID=SOCCER ...")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    
    print("Successfully fetched teams data!")
    
    # Handle if data is list or dict with 'data' key
    teams_list = data.get('data') if isinstance(data, dict) and 'data' in data else data
    
    if teams_list:
        print(f"Found {len(teams_list)} teams.")
        first_team = teams_list[0]
        print(json.dumps(first_team, indent=2))
        
        # Explicit check for common image keys
        keys = first_team.keys()
        potential_logo_keys = [k for k in keys if 'logo' in k.lower() or 'image' in k.lower() or 'url' in k.lower()]
        if potential_logo_keys:
            print(f"Potential logo fields found: {potential_logo_keys}")
        else:
            print("No obvious logo/image fields found in the top level of team object.")
            
    else:
        print("No teams found in response.")

except Exception as e:
    print(f"Error: {e}")
    if 'response' in locals():
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text[:500]}")
