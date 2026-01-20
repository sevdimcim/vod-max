import requests
import re
import json
import html

YOUTUBE_LIVE_URL = "https://www.youtube.com/live/nmY9i63t6qo"
OUTPUT_FILE = "ahaber.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_hls_from_html(html_text):
    # Direkt hlsManifestUrl ara (en sağlam yol)
    match = re.search(
        r'"hlsManifestUrl":"([^"]+)"',
        html_text
    )
    if not match:
        return None

    hls_url = match.group(1)
    hls_url = html.unescape(hls_url)
    hls_url = hls_url.replace("\\u0026", "&")

    return hls_url


def get_hls_manifest_url():
    r = requests.get(YOUTUBE_LIVE_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()

    html_text = r.text

    # 1️⃣ Yöntem: ytInitialPlayerResponse dene
    try:
        match = re.search(
            r"ytInitialPlayerResponse\s*=\s*({.+?});",
            html_text
        )
        if match:
            player_json = json.loads(match.group(1))
            streaming = player_json.get("streamingData", {})
            hls = streaming.get("hlsManifestUrl")
            if hls:
                return hls
    except Exception:
        pass

    # 2️⃣ Yöntem: HTML içinden direkt çek
    hls = extract_hls_from_html(html_text)
    if hls:
        return hls

    raise Exception("HLS manifest bulunamadı (yayın kapalı olabilir)")


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
