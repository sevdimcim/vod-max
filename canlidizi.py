from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re

# -----------------------------
# Chrome ayarları (GitHub Actions uyumlu)
# -----------------------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

# -----------------------------
# Driver başlat
# -----------------------------
driver = webdriver.Chrome(options=options)

print("Tarayıcı açıldı")

# -----------------------------
# Site adresi
# -----------------------------
url = "https://canlidizi.site"
driver.get(url)

print("Site açıldı")
time.sleep(8)

# -----------------------------
# Sayfa kaynağını al
# -----------------------------
html = driver.page_source

# -----------------------------
# m3u8 yakalama
# -----------------------------
m3u8_list = re.findall(r"https?://[^\s\"']+\.m3u8[^\s\"']*", html)

print("\nBulunan M3U8 linkleri:\n")

if m3u8_list:
    for i, link in enumerate(set(m3u8_list), 1):
        print(f"{i}. {link}")
else:
    print("M3U8 bulunamadı")

# -----------------------------
# Kapat
# -----------------------------
driver.quit()
print("\nTarayıcı kapatıldı")
