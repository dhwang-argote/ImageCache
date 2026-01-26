import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
REPORT_FILE = BASE_DIR / "low_confidence_report.json"
CUSTOM_MAP_FILE = BASE_DIR / "custom_mappings.json"
IGNORE_LIST_FILE = BASE_DIR / "ignore_list.json"

def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    print("=== Low Confidence Logo Review Tool ===")
    
    report = load_json(REPORT_FILE, [])
    if not report:
        print("No low confidence report found or it is empty.")
        return

    custom_map = load_json(CUSTOM_MAP_FILE, {})
    ignore_list = set(load_json(IGNORE_LIST_FILE, []))
    
    # Filter out items already handled
    items_to_review = []
    for item in report:
        fpath = item['file']
        if fpath in custom_map or fpath in ignore_list:
            continue
        items_to_review.append(item)
        
    print(f"Found {len(items_to_review)} items pending review.\n")
    
    try:
        for i, item in enumerate(items_to_review):
            fpath = item['file']
            fname = Path(fpath).name
            sport = item['sport']
            suggested = item.get('suggested')
            reason = item.get('reason')
            
            print(f"[{i+1}/{len(items_to_review)}] {sport} : {fname}")
            print(f"    Reason: {reason}")
            if suggested:
                print(f"    AI Suggestion: {suggested}")
            
            print("    [1] Ignore (Permanently skip)")
            print("    [2] Rename Manually")
            if suggested:
                print("    [3] Accept AI Suggestion")
            print("    [s] Skip for now")
            print("    [q] Quit")
            
            choice = input("    > ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 's':
                continue
            elif choice == '1':
                ignore_list.add(fpath)
                print(f"    -> Added to Ignore List.")
            elif choice == '2':
                new_name = input("    Enter new filename (e.g. 'Team Name.gif'): ").strip()
                if new_name:
                    # Strip quotes if user added them
                    new_name = new_name.replace('"', '').replace("'", "")
                    custom_map[fpath] = new_name
                    print(f"    -> Mapped to '{new_name}'")
            elif choice == '3' and suggested:
                custom_map[fpath] = f"{suggested}{Path(fpath).suffix}"
                print(f"    -> Mapped to '{custom_map[fpath]}'")
            else:
                print("    Invalid choice, skipping.")
            
            print("-" * 50)
            
    except KeyboardInterrupt:
        print("\nExiting...")
        
    # Save results
    save_json(CUSTOM_MAP_FILE, custom_map)
    save_json(IGNORE_LIST_FILE, list(ignore_list))
    
    print("\nReview session saved.")
    print(f"Total Custom Mappings: {len(custom_map)}")
    print(f"Total Ignored Files: {len(ignore_list)}")

if __name__ == "__main__":
    main()
