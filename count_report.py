import json
from collections import Counter
from pathlib import Path

report_path = Path('c:/Users/dhwan/Desktop/ImageCache/low_confidence_report.json')

try:
    with open(report_path, 'r') as f:
        data = json.load(f)
        
    counts = Counter(item.get('sport', 'Unknown') for item in data)
    
    print("Counts by Sport:")
    for sport, count in counts.most_common():
        print(f"{sport}: {count}")
        
    print(f"\nTotal: {len(data)}")

except Exception as e:
    print(f"Error: {e}")
