
import os
import re
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_logos():
    url = "https://www.sportslogos.net/teams/list_by_league/8/Canadian-Football-League-Logos/CFL-Logos/"
    
    # Headers to mimic a browser request to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.sportslogos.net/"
    }

    # Create a session with retry logic to handle SSL/Connection errors
    session = requests.Session()
    retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    print(f"Fetching {url}...")
    try:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the container for the logos. On sportslogos.net, this is typically <ul class="logoWall">
    logo_wall = soup.find(class_="logoWall")
    images = []

    if logo_wall:
        images = logo_wall.find_all("img")
    else:
        print("Could not find class='logoWall'. Attempting fallback search...")
        # Fallback: look for images that contain '/logos/' in their src
        for img in soup.find_all("img"):
            if "/logos/" in img.get("src", ""):
                images.append(img)

    if not images:
        print("No images found.")
        if soup.title:
            print(f"Page title: {soup.title.text.strip()}")
        return

    # Create a directory for the logos
    # Use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(script_dir, "Logos")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Found {len(images)} logos. Downloading to '{save_dir}'...")

    for img in images:
        src = img.get("src")
        # Use title or alt for the team name
        name_raw = img.get("title") or img.get("alt")

        if not src or not name_raw:
            continue

        # Handle protocol-relative URLs if present
        if src.startswith("//"):
            src = "https:" + src

        # Clean up the team name for the filename
        # Remove " Logos" suffix which is common on this site (e.g., "Baltimore Orioles Logos")
        team_name = name_raw.replace(" Logos", "").strip()
        
        # Sanitize filename (remove illegal characters)
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', team_name)
        
        if not safe_filename:
            continue

        # Determine file extension from URL
        ext = "gif" # Default fallback
        if "." in src:
            # Extract extension and remove any query parameters
            ext = src.split(".")[-1].split("?")[0]

        file_path = os.path.join(save_dir, f"{safe_filename}.{ext}")

        try:
            img_response = session.get(src, headers=headers, verify=False)
            img_response.raise_for_status()
            img_data = img_response.content
            with open(file_path, "wb") as f:
                f.write(img_data)
            print(f"Downloaded: {safe_filename}")
        except Exception as e:
            print(f"Failed to download {team_name}: {e}")

    print("Done.")

if __name__ == "__main__":
    download_logos()
