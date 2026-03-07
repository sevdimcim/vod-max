import requests
import re
import json
from urllib.parse import urlparse

def get_active_domain():
    for i in range(1010, 1100):
        url = f"https://taraftarium{i}.xyz"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return url
        except requests.exceptions.RequestException:
            continue
    return None

def fetch_base_url(domain):
    target_url = f"{domain}/channel.html?id=taraftarium"
    try:
        response = requests.get(target_url, timeout=5)
        match = re.search(r"const\s+CONFIG\s*=\s*\{.*?baseUrl:\s*['\"]([^'\"]+)['\"]", response.text, re.IGNORECASE)
        if match:
            return match.group(1)
    except requests.exceptions.RequestException:
        return None
    return None

def update_json_data(new_domain):
    with open("trgoals_data.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    clean_new_domain = new_domain.rstrip("/")

    for item in data.get("list", {}).get("item", []):
        if "media_url" in item and item["media_url"]:
            parsed_media = urlparse(item["media_url"])
            item["media_url"] = f"{clean_new_domain}{parsed_media.path}"
        
        if "url" in item and item["url"]:
            parsed_url = urlparse(item["url"])
            item["url"] = f"{clean_new_domain}{parsed_url.path}"

    with open("trgoals_data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def main():
    active_domain = get_active_domain()
    if active_domain:
        base_url = fetch_base_url(active_domain)
        if base_url:
            update_json_data(base_url)

if __name__ == "__main__":
    main()
  
