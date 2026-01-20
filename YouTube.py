import requests
import re
import json

YOUTUBE_LIVE_URL = "https://www.youtube.com/live/nmY9i63t6qo"
OUTPUT_FILE = "ahaber.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_hls_manifest_url():
    r = requests.get(YOUTUBE_LIVE_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()

    html = r.text

    # ytInitialPlayerResponse JSON'unu yakala
    match = re.search(
        r"ytInitialPlayerResponse\s*=\s*({.+?});",
        html
    )

    if not match:
        raise Exception("ytInitialPlayerResponse bulunamadı")

    player_json = json.loads(match.group(1))

    hls_url = player_json["streamingData"].get("hlsManifestUrl")

    if not hls_url:
        raise Exception("hlsManifestUrl bulunamadı")

    return hls_url


def download_hls_playlist(hls_url):
    r = requests.get(hls_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text


def main():
    print("[+] HLS manifest URL alınıyor...")
    hls_url = get_hls_manifest_url()

    print("[+] HLS playlist indiriliyor...")
    playlist = download_hls_playlist(hls_url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"[✓] Güncellendi: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
