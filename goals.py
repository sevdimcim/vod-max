import requests
import re
import json
from urllib.parse import urlparse

JSON_FILE = "trgoals_data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def find_valid_domain():
    print("Scanning domains for active taraftarium domain...")

    for i in range(1067, 1100):

        domain = f"https://taraftarium{i}.xyz"

        try:
            response = requests.get(
                domain,
                headers=HEADERS,
                timeout=3
            )

            if response.status_code == 200:

                print(f"Active domain found: {domain}")

                target_url = f"{domain}/channel.html?id=taraftarium"

                try:
                    source_response = requests.get(
                        target_url,
                        headers=HEADERS,
                        timeout=5
                    )

                    # baseUrl kontrolü
                    match = re.search(
                        r"const\s+CONFIG\s*=\s*\{.*?baseUrl:\s*['\"]([^'\"]+)['\"]",
                        source_response.text,
                        re.IGNORECASE | re.DOTALL
                    )

                    if match:

                        base_url = match.group(1).strip()

                        if base_url:
                            print(f"Valid baseUrl found: {base_url}")

                            # aktif site domaini + yayın domaini döndür
                            return domain, base_url

                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch source: {e}")

        except requests.exceptions.RequestException:
            continue

    print("No valid domain found.")
    return None, None


def update_json_data(site_domain, stream_domain):

    print("Updating JSON file...")

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    clean_stream_domain = stream_domain.rstrip("/")
    clean_site_domain = site_domain.rstrip("/")

    updated_count = 0

    items = data.get("list", {}).get("item", [])

    for item in items:

        # media_url güncelle
        if "media_url" in item and item["media_url"]:

            parsed_media = urlparse(item["media_url"])

            item["media_url"] = (
                f"{clean_stream_domain}{parsed_media.path}"
            )

            updated_count += 1

        # url güncelle
        if "url" in item and item["url"]:

            parsed_url = urlparse(item["url"])

            item["url"] = (
                f"{clean_stream_domain}{parsed_url.path}"
            )

        # BURASI ÖNEMLİ
        # h2Val ve h3Val aktif taraftarium sitesi olacak

        item["h2Val"] = f"{clean_site_domain}/"
        item["h3Val"] = clean_site_domain

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("JSON updated successfully.")
    print(f"Updated media items: {updated_count}")
    print(f"h2Val -> {clean_site_domain}/")
    print(f"h3Val -> {clean_site_domain}")


def main():

    site_domain, stream_domain = find_valid_domain()

    if site_domain and stream_domain:

        update_json_data(
            site_domain,
            stream_domain
        )

    else:
        print("Process stopped: No working domain found.")


if __name__ == "__main__":
    main()
