import requests
import json
import re
import sys

START_NUM = 1071
END_NUM = 1199
BASE_DOMAIN_PATTERN = "taraftarium{}.xyz"
CHECK_PATH = "/channel.html?id=taraftarium"
JSON_FILE = "trgoals_data.json"

def find_active_taraftarium_domain():
    print(f"Taranıyor: {START_NUM}-{END_NUM}")
    for num in range(START_NUM, END_NUM + 1):
        domain = BASE_DOMAIN_PATTERN.format(num)
        url = f"https://{domain}{CHECK_PATH}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"Aktif domain: {domain}")
                return domain
        except:
            continue
    print("Aktif domain bulunamadı!")
    return None

def extract_base_url(active_domain):
    url = f"https://{active_domain}{CHECK_PATH}"
    print(f"baseUrl çekiliyor: {url}")
    try:
        response = requests.get(url, timeout=10)
        match = re.search(r"baseUrl:\s*'([^']*)'", response.text)
        if match:
            base_url = match.group(1).rstrip('/')
            print(f"baseUrl: {base_url}")
            return base_url
        else:
            print("baseUrl bulunamadı!")
            return None
    except Exception as e:
        print(f"Hata: {e}")
        return None

def update_json_file(base_url_domain, taraftarium_domain):
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        print(f"{JSON_FILE} okunamadı!")
        return False

    channels = data[0]["data"]
    updated = 0

    for channel in channels:
        for key in ["media_url", "url"]:
            if key in channel and channel[key]:
                if '/' in channel[key]:
                    path = channel[key].split('/', 3)[-1] if channel[key].startswith('http') else channel[key]
                    channel[key] = f"{base_url_domain}/{path}"
                else:
                    channel[key] = base_url_domain
                updated += 1

        for key in ["h2Val", "h3Val"]:
            if key in channel:
                channel[key] = f"https://{taraftarium_domain}/"
                updated += 1

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Güncellendi: {updated} alan")
    return True

def main():
    active_domain = find_active_taraftarium_domain()
    if not active_domain:
        sys.exit(1)

    base_url = extract_base_url(active_domain)
    if not base_url:
        sys.exit(1)

    base_url_domain = f"https://{base_url.split('//')[-1].split('/')[0]}"

    if update_json_file(base_url_domain, active_domain):
        print("Tamamlandı.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
