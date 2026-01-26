import os
import json
import requests
import shutil
from pathlib import Path

# ==================================================================================
# CONFIGURATION
# ==================================================================================
SPORTSGAMEODDS_API_KEY = os.environ.get("SPORTSGAMEODDS_API_KEY", "43f558d0dc54d4e2b06a7b3139dea679")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

BASE_DIR = Path(__file__).parent
LOGOS_DIR = BASE_DIR / "Logos"
UNDO_LOG_FILE = BASE_DIR / "undo_log.json"
UNDO_SCRIPT_FILE = BASE_DIR / "undo_rename.py"
REPORT_FILE = BASE_DIR / "low_confidence_report.json"

BATCH_SIZE = 20
CONFIDENCE_THRESHOLD = 0.90

# Map local directory names to API Sport IDs
SPORT_DIR_MAP = {
    "Baseball": "BASEBALL",
    "Basketball": "BASKETBALL",
    "Football": "FOOTBALL",
    "Hockey": "HOCKEY",
    "Soccer": "SOCCER",
    "Tennis": "TENNIS",
    "Mixed Martial Arts": "MMA",
    "Boxing": "BOXING",
    "College": "FOOTBALL" # Assuming College maps to Football for now, logic might need adjustment if it's NCAA specific
}

# ==================================================================================
# API HELPERS
# ==================================================================================
def fetch_all_teams(sport_id):
    """Fetches all teams for a given sportID, handling pagination."""
    url = "https://api.sportsgameodds.com/v2/teams"
    headers = {"X-Api-Key": SPORTSGAMEODDS_API_KEY}
    teams = []
    cursor = None
    
    print(f"Fetching teams for {sport_id}...")
    
    while True:
        params = {"sportID": sport_id}
        if cursor:
            params["cursor"] = cursor
            
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # Data structure handling
            batch = data.get('data', []) if isinstance(data, dict) else data
            teams.extend(batch)
            
            cursor = data.get('nextCursor') if isinstance(data, dict) else None
            if not cursor:
                break
            print(f"    Fetched {len(batch)} teams. Next cursor: {str(cursor)[:10]}...")
        except Exception as e:
            print(f"Error fetching teams for {sport_id}: {e}")
            break
            
    print(f"  -> Found {len(teams)} teams.")
    return teams

def fetch_leagues(sport_id):
    """Fetches leagues for a given sportID."""
    url = "https://api.sportsgameodds.com/v2/leagues"
    headers = {"X-Api-Key": SPORTSGAMEODDS_API_KEY}
    params = {"sportID": sport_id}
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        leagues = data.get('data', [])
        print(f"  -> Found {len(leagues)} leagues.")
        return leagues
    except Exception as e:
        print(f"Error fetching leagues for {sport_id}: {e}")
        return []

def get_ai_matches(filenames, official_entities, sport_name):
    """Asks AI to match filenames to official teams or leagues."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Simplify official data for the prompt to save tokens
    simplified_list = []
    for t in official_entities:
        # Handle Team vs League differences
        if 'teamID' in t:
            # It's a Team
            names = t.get('names', {})
            entry = {
                "type": "Team",
                "name": names.get('medium'),
                "full_name": names.get('long'),
                "league": t.get('leagueID', 'Unknown')
            }
        else:
            # It's a League
            entry = {
                "type": "League",
                "name": t.get('name'),
                "short_name": t.get('shortName')
            }
        simplified_list.append(entry)
    
    prompt = f"""
    You are a sports image expert. Match local filenames to official TEAMS or LEAGUES.
    
    SPORT: {sport_name}
    OFFICIAL ENTITIES: {json.dumps(simplified_list[:600])}
    
    LOCAL FILES: {json.dumps(filenames)}

    RULES:
    1. Match local filenames to one of the OFFICIAL ENTITIES.
    2. Can be a Team OR a League (e.g. "NBA.gif" -> "National Basketball Association").
    3. Return a CONFIDENCE score (0.0 to 1.0).
    4. If no good match, return null.

    RESPONSE FORMAT (JSON ONLY):
    {{
      "matches": [
        {{
          "filename": "file1.gif",
          "official_name": "Official Name",
          "confidence": 0.95,
          "reasoning": "Exact match to league short name"
        }}
      ]
    }}
    """
    
    # Payload
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content).get('matches', [])
    except Exception as e:
        print(f"  -> AI Request Failed: {e}")
        return []

# ==================================================================================
# CORE LOGIC
# ==================================================================================
def normalize_name(name):
    """Lowercases and removes common suffixes/extensions."""
    name = name.lower()
    root = Path(name).stem
    root = root.replace(" logo", "").strip()
    return root

def sanitize_filename(name):
    """Ensures filename is safe for Windows."""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '')
    return name

def main():
    print("Starting Normalization Process...")
    print(f"Model: {OPENROUTER_MODEL}")
    print(f"Threshold: {CONFIDENCE_THRESHOLD}")
    
    all_renames = []    # List of (old_path, new_name)
    low_confidence_log = [] # List of dicts for report
    
    # 1. Iterate Sports
    for local_dir_name, sport_id in SPORT_DIR_MAP.items():
        local_sport_path = LOGOS_DIR / local_dir_name
        if not local_sport_path.exists():
            continue
            
        print(f"\nProcessing {local_dir_name} ({sport_id})...")
        
        # Fetch Official Data (Teams + Leagues)
        official_teams = fetch_all_teams(sport_id)
        official_leagues = fetch_leagues(sport_id)
        
        # Combine into one list for AI
        official_entities = official_teams + official_leagues
        
        if not official_entities:
            print("  -> No teams or leagues found, skipping.")
            continue
            
        # Build Lookup Map (Normalized Name -> Official Name)
        # We index multiple variations (short, medium, long) pointing to the BEST official name (Long > Medium)
        name_map = {}
        
        # 1. Add Teams
        for t in official_teams:
            names = t.get('names', {})
            
            # Determine the Target Name (what we want to rename TO)
            target_name = names.get('long') or names.get('medium') or names.get('short')
            if not target_name:
                continue
                
            # Map ALL variations to this target
            if names.get('medium'):
                name_map[normalize_name(names['medium'])] = target_name
            
            if names.get('long'):
                name_map[normalize_name(names['long'])] = target_name
                
            if names.get('short'):
                 name_map[normalize_name(names['short'])] = target_name
            # location can sometimes help too
            if names.get('location') and names.get('medium'): # e.g. "Portland" + "Trail Blazers"
                 combined = f"{names['location']} {names['medium']}"
                 name_map[normalize_name(combined)] = target_name

        # 2. Add Leagues
        for l in official_leagues:
            target_name = l.get('name') # e.g. "National Basketball Association"
            if not target_name: 
                continue
                
            name_map[normalize_name(target_name)] = target_name
            
            if l.get('shortName'):
                name_map[normalize_name(l['shortName'])] = target_name
            if l.get('leagueID'): # e.g. "NBA"
                name_map[normalize_name(l['leagueID'])] = target_name
            
        # Load Manual Overrides
        try:
            with open("custom_mappings.json", 'r') as f:
                custom_map = json.load(f)
        except:
            custom_map = {}
            
        try:
            with open("ignore_list.json", 'r') as f:
                ignore_list = set(json.load(f))
        except:
            ignore_list = set()

        # Walk Local Directory
        local_files = []
        for root, dirs, files in os.walk(local_sport_path):
            for file in files:
                if file.startswith('.') or file.lower().endswith('.ini'):
                    continue
                    
                path_obj = Path(root) / file
                str_path = str(path_obj)
                
                # Check Manual Ignore
                if str_path in ignore_list:
                    print(f"  [Ignored] {file}")
                    continue
                    
                # Check Manual Rename
                if str_path in custom_map:
                    new_name = custom_map[str_path]
                    # Add to renames immediately, skip further matching
                    all_renames.append({
                        "path": path_obj,
                        "new_stem": Path(new_name).stem,
                        "reason": "Manual Override"
                    })
                    continue
                    
                local_files.append(path_obj)
                
        if not local_files:
            print("  -> No local files found (or all ignored/mapped).")
            continue
            
        unmatched_files = []
        
        # 2. Simple String Matching
        for file_path in local_files:
            norm_file = normalize_name(file_path.name)
            
            if norm_file in name_map:
                official = name_map[norm_file]
                if official != Path(file_path).stem: # Only rename if different
                    all_renames.append({
                        "path": file_path, 
                        "new_stem": official,
                        "reason": "Exact Text Match"
                    })
            else:
                unmatched_files.append(file_path)
                
        print(f"  -> {len(all_renames)} exact matches found so far.")
        print(f"  -> {len(unmatched_files)} files require AI matching.")
        
        # 3. AI Matching (Batched)
        for i in range(0, len(unmatched_files), BATCH_SIZE):
            batch = unmatched_files[i:i+BATCH_SIZE]
            batch_names = [p.name for p in batch]
            
            print(f"  -> AI Batch {i//BATCH_SIZE + 1}...")
            ai_results = get_ai_matches(batch_names, official_entities, local_dir_name)
            
            # Process AI Results
            for res in ai_results:
                fname = res.get('filename')
                official = res.get('official_name')
                conf = res.get('confidence') or 0.0
                reason = res.get('reasoning', '')
                
                # Find the full path object for this filename
                # (Simple lookup, assuming unique filenames in batch or relying on order if names duplicated)
                # To be safe, let's look it up in the batch list
                original_path = next((p for p in batch if p.name == fname), None)
                
                if not original_path:
                    continue
                    
                if conf >= CONFIDENCE_THRESHOLD and official:
                    all_renames.append({
                        "path": original_path,
                        "new_stem": official,
                        "reason": f"AI Match ({conf}): {reason}"
                    })
                else:
                    low_confidence_log.append({
                        "sport": local_dir_name,
                        "file": str(original_path),
                        "suggested": official,
                        "confidence": conf,
                        "reason": reason
                    })

    # ==============================================================================
    # EXECUTION PHASE
    # ==============================================================================
    
    # 1. Report Low Confidence
    with open(REPORT_FILE, 'w') as f:
        json.dump(low_confidence_log, f, indent=2)
    print(f"\nReport generated: {REPORT_FILE} ({len(low_confidence_log)} items)")
        
    # 2. Generate Undo Logic & Execute Renames
    if not all_renames:
        print("No renames to perform.")
        return

    print(f"\nExecuting {len(all_renames)} renames...")
    undo_map = {}
    
    for item in all_renames:
        old_path = item['path']
        new_stem = sanitize_filename(item['new_stem'])
        new_name = f"{new_stem}{old_path.suffix}"
        new_path = old_path.parent / new_name
        
        # Skip if identical
        if old_path == new_path:
            continue
            
        # Handle Collisions
        if new_path.exists():
            counter = 1
            while new_path.exists():
                new_name = f"{new_stem}_{counter}{old_path.suffix}"
                new_path = old_path.parent / new_name
                counter += 1
        
        try:
            # Record for Undo
            undo_map[str(new_path)] = str(old_path)
            
            # Rename
            old_path.rename(new_path)
            print(f"  [OK] {old_path.name} -> {new_path.name}")
        except Exception as e:
            print(f"  [ERR] Failed to rename {old_path.name}: {e}")
            
    # Save Undo Log
    with open(UNDO_LOG_FILE, 'w') as f:
        json.dump(undo_map, f, indent=2)
        
    # Write Undo Script
    undo_script_content = """
import json
import os
import shutil
from pathlib import Path

LOG_FILE = Path("undo_log.json")

def main():
    if not LOG_FILE.exists():
        print("No undo log found.")
        return
        
    with open(LOG_FILE, 'r') as f:
        data = json.load(f)
        
    print(f"Reverting {len(data)} files...")
    
    for new_path_str, old_path_str in data.items():
        new_path = Path(new_path_str)
        old_path = Path(old_path_str)
        
        if new_path.exists():
            try:
                new_path.rename(old_path)
                print(f" reverted: {new_path.name} -> {old_path.name}")
            except Exception as e:
                print(f" failed: {new_path.name} -> {e}")
        else:
            print(f" missing: {new_path.name}")
            
if __name__ == "__main__":
    main()
"""
    with open(UNDO_SCRIPT_FILE, 'w') as f:
        f.write(undo_script_content)
        
    print(f"\nDone! Undo script saved to {UNDO_SCRIPT_FILE}")

if __name__ == "__main__":
    main()
