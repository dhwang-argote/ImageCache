import requests
import json

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
url = "https://api.sportsgameodds.com/v2/teams"
headers = {"X-Api-Key": api_key}

def traverse_teams(sport_id, query):
    print(f"Searching {sport_id} for '{query}'...")
    cursor = None
    found = False
    
    while True:
        params = {"sportID": sport_id}
        if cursor:
            params["cursor"] = cursor
            
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            batch = data.get('data', [])
            
            for team in batch:
                # Check names
                names = team.get('names', {})
                full_text = f"{names.get('short')} {names.get('medium')} {names.get('long')}".lower()
                
                if query.lower() in full_text:
                    print("\nFOUND MATCH:")
                    print(json.dumps(team, indent=2))
                    found = True
            
            cursor = data.get('nextCursor')
            if not cursor:
                break
        except Exception as e:
            print(f"Error: {e}")
            break
            
    if not found:
        print(f"No match found for '{query}' in {sport_id}.")

# Search in Basketball (Trail Blazers are NBA)
traverse_teams("BASKETBALL", "Portland")
