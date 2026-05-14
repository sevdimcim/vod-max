import requests
import re
import json
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JSON_FILE = "trgoals_data.json"

START_URL = "https://inattv1303.xyz"

BASE_URL_SOURCE = "https://data-reality.com/domain.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_dynamic_base_url():
    """
    Inat sistemindeki gerçek yayın base URL'sini çeker.
    """

    try:
        print(f"📡 Base URL çekiliyor: {BASE_URL_SOURCE}")

        r = requests.get(
            BASE_URL_SOURCE,
            headers=HEADERS,
            timeout=10,
            verify=False
        )

        data = r.json()

        base_url = data.get(
            "baseurl",
            ""
        ).replace("\\/", "/")

        if base_url:
            print(f"✅ Base URL bulundu: {base_url}")
            return base_url.rstrip("/")

    except Exception as e:
        print(f"⚠️ Base URL alınamadı: {e}")

    return "https://hz8.d72577a9dd0ec62.cfd"


def find_active_domain(start_url):
    """
    Aktif inattv domainini bulur.
    """

    print("🔍 Aktif domain aranıyor...")

    try:
        r = requests.get(
            start_url,
            headers=HEADERS,
            timeout=5,
            verify=False
        )

        if r.status_code == 200:
            print(f"✅ Aktif domain: {start_url}")
            return start_url.rstrip("/")

    except:
        pass

    match = re.search(
        r'(https?://inattv)(\.?[0-9]+)(\.xyz|\.link|\.pw)',
        start_url
    )

    if match:

        base, num, tld = match.groups()

        num_val = int(num.replace('.', ''))

        for i in range(1, 20):

            test_url = f"{base}{num_val + i}{tld}"

            try:
                print(f"🔄 Deneniyor: {test_url}")

                r = requests.get(
                    test_url,
                    headers=HEADERS,
                    timeout=3,
                    verify=False
                )

                if r.status_code == 200:
                    print(f"✅ Yeni domain bulundu: {test_url}")
                    return test_url.rstrip("/")

            except:
                continue

    return None


def update_json():

    active_domain = find_active_domain(START_URL)

    if not active_domain:
        print("❌ Aktif domain bulunamadı.")
        return

    base_url = get_dynamic_base_url()

    print("📡 JSON güncelleniyor...")

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0

    # EKSTRA kanal aliasları
    extra_alias = {
        "zirve": "BeIN Sports 1",
        "patron": "BeIN Sports 1"
    }

    items = data.get("list", {}).get("item", [])

    existing_urls = set()

    for item in items:

        media_url = item.get("media_url", "")

        if media_url:
            existing_urls.add(media_url)

        # ref/origin güncelle
        item["h2Val"] = f"{active_domain}/"
        item["h3Val"] = active_domain

        # media_url varsa yeni baseurl ile güncelle
        match = re.search(
            r'/([^/]+)/mono\.m3u8',
            media_url
        )

        if match:

            cid = match.group(1)

            item["media_url"] = (
                f"{base_url}/{cid}/mono.m3u8"
            )

            updated += 1

    # patron + zirve ekle
    for cid, channel_name in extra_alias.items():

        new_url = f"{base_url}/{cid}/mono.m3u8"

        if new_url in existing_urls:
            continue

        new_item = {
            "name": channel_name,
            "media_url": new_url,
            "url": new_url,
            "h2Val": f"{active_domain}/",
            "h3Val": active_domain
        }

        items.append(new_item)

        print(f"➕ Extra kanal eklendi: {cid}")

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"✅ JSON güncellendi. ({updated} kanal)")


if __name__ == "__main__":
    update_json()
