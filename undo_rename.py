
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
