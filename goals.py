import requests
import re
import json
from urllib.parse import urlparse

JSON_FILE = "trgoals_data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def find_valid_base_url():
    print("Scanning domains for a valid baseUrl...")

    for i in range(1067, 1100):
        domain = f"https://taraftarium{i}.xyz"

        try:
            response = requests.get(domain, headers=HEADERS, timeout=3)

            if response.status_code == 200:
                print(f"Active domain found: {domain}")

                target_url = f"{domain}/channel.html?id=taraftarium"

                try:
                    source_response = requests.get(
                        target_url,
                        headers=HEADERS,
                        timeout=5
                    )

                    match = re.search(
                        r"const\s+CONFIG\s*=\s*\{.*?baseUrl:\s*['\"]([^'\"]+)['\"]",
                        source_response.text,
                        re.IGNORECASE | re.DOTALL
                    )

                    if match:
                        base_url = match.group(1).strip()

                        if base_url:
                            print(f"Valid Base URL found!: {base_url}")
                            return base_url

                        else:
                            print("baseUrl empty, trying next domain...")

                    else:
                        print("No baseUrl found, trying next domain...")

                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch {target_url}: {e}")

        except requests.exceptions.RequestException:
            continue

    print("No valid baseUrl found in range.")
    return None


def update_json_data(new_domain):
    print("Updating JSON file...")

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    clean_new_domain = new_domain.rstrip("/")

    updated_count = 0

    items = data.get("list", {}).get("item", [])

    for item in items:

        # media_url güncelle
        if "media_url" in item and item["media_url"]:
            parsed_media = urlparse(item["media_url"])

            item["media_url"] = (
                f"{clean_new_domain}{parsed_media.path}"
            )

            updated_count += 1

        # url güncelle
        if "url" in item and item["url"]:
            parsed_url = urlparse(item["url"])

            item["url"] = (
                f"{clean_new_domain}{parsed_url.path}"
            )

        # h2Val güncelle
        item["h2Val"] = f"{clean_new_domain}/"

        # h3Val güncelle
        item["h3Val"] = clean_new_domain

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"JSON updated successfully.")
    print(f"Updated items: {updated_count}")
    print(f"h2Val -> {clean_new_domain}/")
    print(f"h3Val -> {clean_new_domain}")


def main():
    valid_base_url = find_valid_base_url()

    if valid_base_url:
        update_json_data(valid_base_url)

    else:
        print("Process stopped: No working domain found.")


if __name__ == "__main__":
    main()
