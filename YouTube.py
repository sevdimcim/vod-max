import requests
import re
import sys
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

live_id = "UCoIUysIrvGxoDw-GkdOGjRw"

headers1 = {
    "User-Agent": "Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0)"
}
response1 = requests.get("https://ytdlp.online/", headers=headers1, verify=False)

if "session" not in response1.cookies:
    sys.exit("Session could not be retrieved.")

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

response2 = requests.get(stream_url, headers=headers2, verify=False)
text = response2.text

manifest_match = re.search(r'data:\s*(https://manifest\.googlevideo\.com[^\s]+)', text)

if not manifest_match:
    sys.exit("Manifest link not found.")

final_link = manifest_match.group(1).strip()

m3u8_content = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720\n" + final_link

with open("kemal-sunal-filmleri.m3u8", "w", encoding="utf-8") as f:
    f.write(m3u8_content)
  
