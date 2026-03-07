import requests
import re
import json
from urllib.parse import urlparse

def find_valid_base_url():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("Scanning domains for a valid baseUrl...")
    for i in range(1010, 1100):
        domain = f"https://taraftarium{i}.xyz"
        try:
            response = requests.get(domain, headers=headers, timeout=3)
            if response.status_code == 200:
                print(f"Active domain found: {domain}, checking for baseUrl...")
                target_url = f"{domain}/channel.html?id=taraftarium"
                try:
                    source_response = requests.get(target_url, headers=headers, timeout=5)
                    match = re.search(r"const\s+CONFIG\s*=\s*\{.*?baseUrl:\s*['\"]([^'\"]+)['\"]", source_response.text, re.IGNORECASE)
                    
                    if match:
                        base_url = match.group(1).strip()
                        if base_url:
                            print(f"Valid Base URL found!: {base_url}")
                            return base_url
                        else:
                            print("Regex matched, but baseUrl is empty. Moving to next domain...")
                    else:
                        print("No baseUrl found in page source. Moving to next domain...")
                        
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch {target_url}: {e}. Moving to next domain...")
        except requests.exceptions.RequestException:
            continue
            
    print("No valid baseUrl found in the entire range.")
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
    valid_base_url = find_valid_base_url()
    if valid_base_url:
        update_json_data(valid_base_url)
    else:
        print("Process stopped: Could not find a working domain with a valid baseUrl.")

if __name__ == "__main__":
    main()
    
