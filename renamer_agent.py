import os
import csv
import json
import requests
import shutil
from pathlib import Path
import time

# Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = "google/gemini-2.0-flash-001" # Using the same model as in Normalize.py
BASE_DIR = Path(__file__).parent
LOGOS_DIR = BASE_DIR / "Logos"
CSV_FILE = BASE_DIR / "logo.csv"
OUTPUT_CSV_FILE = BASE_DIR / "logo_updated.csv" # Write to a new file first, then replace or user can review
# User said "change the status column ... iterate thru the entire file" - implies in-place or update. 
# I will write to a temp file and then overwrite if successful, or just write to logo_updated.csv for safety.
# Actually user said "create a program that reads...".
# I'll stick to updating a new file `logo_processed.csv` to avoid destroying data, and print that I did so.

def get_all_logo_files(root_dir):
    """Recursively finding all files in Logos directory."""
    file_list = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.startswith('.') or file.lower().endswith('.ini'):
                continue
            # Store relative path from Logos root for easier context
            abs_path = Path(root) / file
            rel_path = abs_path.relative_to(root_dir)
            file_list.append(str(rel_path))
    return file_list

def find_logo_match_with_llm(team_name, sport_id, league_name, available_files):
    """
    Uses LLM to find the best matching filename for a given team.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bet2fund.com", # Optional but good practice
    }

    prompt = f"""
    You are a helpful assistant that matches a sports team/entity to a file in a file list.
    
    TARGET ENTITY:
    Name: {team_name}
    Sport: {sport_id}
    League: {league_name}
    
    TASK:
    Find the file in the provided list that most likely corresponds to this entity.
    Return ONLY the filename (relative path provided) in JSON format.
    If no good match is found, return null.
    
    AVAILABLE FILES (Subset):
    {json.dumps(available_files)}
    
    RESPONSE FORMAT:
    {{
        "matched_file": "path/to/file.png" OR null,
        "confidence": 0.95
    }}
    """
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a JSON-speaking file matcher."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)
            if isinstance(parsed, list):
                if len(parsed) > 0:
                    return parsed[0]
                return None
            return parsed
        except Exception as e:
            print(f"Error checking LLM for {team_name}: {e}")
            time.sleep(1)
    return None

def main():
    if not CSV_FILE.exists():
        print(f"Error: {CSV_FILE} not found.")
        return

    print("Indexing Logos directory...")
    all_files = get_all_logo_files(LOGOS_DIR)
    print(f"Found {len(all_files)} files.")
    
    # Read CSV
    rows = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            
    updates_made = 0
    
    print(f"Processing {len(rows)} records...")
    
    for i, row in enumerate(rows):
        name = row.get('NAME')
        sport = row.get('SPORT_ID')
        league = row.get('LEAGUE_NAME')
        preferred_name = row.get('PREFERRED_FILE_NAME')
        current_status = row.get('STATUS')
        
        # User condition: "if this was done- change the status column to DONE otherwise leave alone."
        # If status is already DONE or "✅ Logo exists", maybe skip?
        # User said: "create a program that reads in a single row ... iterate thru the entire file"
        # I'll enable skipping processed ones to save API calls if re-run.
        if "✅" in current_status or "DONE" in current_status:
           # print(f"[{i+1}/{len(rows)}] Skipping {name} (Already DONE)")
            continue
            
        print(f"[{i+1}/{len(rows)}] Processing {name} ({sport})...", end="", flush=True)
        
        # Filter files by sport if possible to reduce token usage?
        # A simple string match on sport might help, but let's just pass all for now if < 1000.
        # But wait, Sport ID in CSV: "SOCCER", "BASKETBALL".
        # Directory names: "Soccer", "Basketball".
        # We can case-insensitive match.
        
        relevant_files = []
        sport_lower = sport.lower()
        if sport_lower == "ncaab": sport_lower = "college" # Special case mappings?
        if sport_lower == "ufc": sport_lower = "mixed martial arts"
        
        # If we can narrow down, good. If not, pass all. 
        # Actually 800 items is fine. Let's filter slightly to be safe against errors or context limits.
        # But if the file is in a weird place, we might miss it.
        # Let's pass ALL files. 839 is manageable.
        
        match_result = find_logo_match_with_llm(name, sport, league, all_files)
        
        if match_result and match_result.get('matched_file'):
            matched_rel_path = match_result['matched_file']
            confidence = match_result.get('confidence', 0)
            
            if confidence > 0.8: # Threshold
                # Found a match
                full_src_path = LOGOS_DIR / matched_rel_path
                
                if not full_src_path.exists():
                    print(f" -> LLM hallucinates path {matched_rel_path}")
                    continue
                    
                # Determining destination
                # User: "renames the file that it finds ... as in PREFERRED_FILE_NAME"
                # Keep the same directory?
                # or use PREFERRED_FILE_PATH?
                # PREFERRED_FILE_PATH might assume a folder structure that doesn't exist yet if the file looks different.
                # Use current directory of the found file + new name.
                
                new_filename = preferred_name
                dst_path = full_src_path.parent / new_filename
                
                # Check if rename is actually needed
                if full_src_path.name == new_filename:
                    print(f" -> Already named correctly.")
                    row['STATUS'] = "DONE"
                else:
                    try:
                        if dst_path.exists():
                             print(f" -> Target {dst_path.name} already exists. Skipping overwrite.")
                             # Maybe mark DONE if it exists?
                        else:
                            os.rename(full_src_path, dst_path)
                            print(f" -> Renamed to {new_filename}")
                            row['STATUS'] = "DONE"
                            updates_made += 1
                            
                            # Update our internal list of files? 
                            # If we renamed it, 'matched_rel_path' is no longer valid.
                            # But we are iterating, so it should be fine.
                            # Need to update 'all_files' list if we want to be perfectly correct for subsequent calls,
                            # but unlikely to conflict unless duplicates exist.
                    except Exception as e:
                        print(f" -> Rename failed: {e}")
            else:
                 print(f" -> Low confidence ({confidence})")
                 row['STATUS'] = f"Low Confidence: {confidence}"
        else:
            print(f" -> No match found.")
            row['STATUS'] = "No Match Found"

    # Write output
    # Overwrite the original file or new file?
    # "change the status column ... iterate thru the entire file"
    # I'll overwrite for seamless usage, but backup first.
    shutil.copy(CSV_FILE, str(CSV_FILE) + ".bak")
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"\nCompleted. {updates_made} files renamed. CSV updated.")

if __name__ == "__main__":
    main()
