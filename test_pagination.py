import requests
import json

api_key = "43f558d0dc54d4e2b06a7b3139dea679"
url = "https://api.sportsgameodds.com/v2/teams"

headers = {"X-Api-Key": api_key}
sport_id = "BASEBALL"

# 1. Fetch First Page
print("Fetching Page 1...")
resp = requests.get(url, headers=headers, params={"sportID": sport_id})
data = resp.json()
cursor1 = data.get('nextCursor')
print(f"Page 1 Cursor: {cursor1}")

if not cursor1:
    print("No cursor returned, cannot test pagination.")
    exit()

# 2. Test 'nextCursor' param
print("\nTesting 'nextCursor' param...")
resp2 = requests.get(url, headers=headers, params={"sportID": sport_id, "nextCursor": cursor1})
data2 = resp2.json()
cursor2 = data2.get('nextCursor')
first_team_p2 = data2['data'][0]['teamID']
print(f"Page 2 (nextCursor) First Team: {first_team_p2}")
print(f"Page 2 (nextCursor) Cursor: {cursor2}")

if cursor1 == cursor2:
    print("FAIL: Cursor did not change with 'nextCursor' param.")
else:
    print("SUCCESS: Cursor changed with 'nextCursor' param.")

# 3. Test 'cursor' param (if above failed or just to check)
print("\nTesting 'cursor' param...")
resp3 = requests.get(url, headers=headers, params={"sportID": sport_id, "cursor": cursor1})
data3 = resp3.json()
cursor3 = data3.get('nextCursor')
first_team_p3 = data3['data'][0]['teamID']
print(f"Page 3 (cursor) First Team: {first_team_p3}")
print(f"Page 3 (cursor) Cursor: {cursor3}")

if cursor1 == cursor3:
    print("FAIL: Cursor did not change with 'cursor' param.")
else:
    print("SUCCESS: Cursor changed with 'cursor' param.")
