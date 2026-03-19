import requests
import re
import sys
import urllib.parse
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

live_id = "UCoIUysIrvGxoDw-GkdOGjRw"
max_retries = 10
wait_time = 15

for attempt in range(1, max_retries + 1):
    print(f"Deneme {attempt}/{max_retries} başlatılıyor...")
    
    try:
        headers1 = {
            "User-Agent": "Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0)"
        }
        response1 = requests.get("https://ytdlp.online/", headers=headers1, verify=False, timeout=15)

        if "session" not in response1.cookies:
            print("Session alınamadı. Bekleniyor...")
            time.sleep(wait_time)
            continue

        token = response1.cookies.get("session")

        youtube_link = f"https://www.youtube.com/channel/{live_id}/live"
        encoded_command = urllib.parse.quote(f"--get-url {youtube_link}")
        stream_url = f"https://ytdlp.online/stream?command={encoded_command}"

        headers2 = {
            "User-Agent": "Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0)",
            "Accept": "text/event-stream",
            "Referer": "https://ytdlp.online/",
            "Cookie": f"session={token}"
        }

        response2 = requests.get(stream_url, headers=headers2, verify=False, timeout=20)
        text = response2.text

        manifest_match = re.search(r'data:\s*(https://manifest\.googlevideo\.com[^\s]+)', text)

        if manifest_match:
            final_link = manifest_match.group(1).strip()

            m3u8_content = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720\n" + final_link

            with open("kemal-sunal-filmleri.m3u8", "w", encoding="utf-8") as f:
                f.write(m3u8_content)
            
            print("Başarılı! Link bulundu ve dosyaya kaydedildi.")
            sys.exit(0)  # Link bulununca sistemi tamamen başarıyla kapatır
        else:
            print("Manifest linki bulunamadı. Bekleniyor...")

    except Exception as e:
        print(f"Bir hata oluştu: {e}")
    
    # Eğer son deneme değilse bekle
    if attempt < max_retries:
        time.sleep(wait_time)

# 10 denemenin sonunda hala bulamadıysa hata verip kapatır
sys.exit("10 deneme yapıldı ancak manifest linki bulunamadı.")
