from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import re

# -----------------------
# Chrome ayarları
# -----------------------
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--mute-audio")
chrome_options.add_argument("--headless=new")  # ister kapat

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

# -----------------------
# HEDEF SAYFA
# -----------------------
url = "https://www.canlidizi14.com/kismetse-olur-askin-gucu-74-bolum-izle.html"
driver.get(url)

# fireplayer yüklenmesi
time.sleep(8)

m3u8_links = set()

# -----------------------
# NETWORK DİNLE
# -----------------------
for request in driver.requests:
    if request.response:
        if ".m3u8" in request.url:
            m3u8_links.add(request.url)

driver.quit()

# -----------------------
# SONUÇ
# -----------------------
if m3u8_links:
    print("\n🎯 BULUNAN M3U8 LİNKLERİ:\n")
    for link in m3u8_links:
        print(link)
else:
    print("❌ m3u8 bulunamadı")
