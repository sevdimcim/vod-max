import requests
import re
import json
from urllib.parse import urlparse

def get_active_domain():
    print("Scanning domains...")
    for i in range(1011, 1100):
        url = f"https://taraftarium{i}.xyz"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"Active domain found: {url}")
                return url
        except requests.exceptions.RequestException:
            continue
    print("No active domain found in range.")
    return None

def fetch_base_url(domain):
    target_url = f"{domain}/channel.html?id=taraftarium"
    print(f"Fetching base URL from: {target_url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(target_url, headers=headers, timeout=5)
        match = re.search(r"const\s+CONFIG\s*=\s*\{.*?baseUrl:\s*['\"]([^'\"]+)['\"]", response.text, re.IGNORECASE)
        if match:
            base_url = match.group(1)
            print(f"Base URL found: {base_url}")
            return base_url
        else:
            print("Regex match failed.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return None

def update_json_data(new_domain):
    print("Updating JSON file...")
    with open("trgoals_data.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    clean_new_domain = new_domain.rstrip("/")
    updated_count = 0

    for item in data.get("list", {}).get("item", []):
        if "media_url" in item and item["media_url"]:
            parsed_media = urlparse(item["media_url"])
            item["media_url"] = f"{clean_new_domain}{parsed_media.path}"
            updated_count += 1
        
        if "url" in item and item["url"]:
            parsed_url = urlparse(item["url"])
            item["url"] = f"{clean_new_domain}{parsed_url.path}"

    with open("trgoals_data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    print(f"JSON updated successfully. Items modified: {updated_count}")

def main():
    active_domain = get_active_domain()
    if active_domain:
        base_url = fetch_base_url(active_domain)
        if base_url:
            update_json_data(base_url)
        else:
            print("Process stopped: Base URL not found.")
    else:
        print("Process stopped: Active domain not found.")

if __name__ == "__main__":
    main()
    
