from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re

options = Options()

# performance log aç
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)

url = "https://www.canlidizi14.com/kismetse-olur-askin-gucu-74-bolum-izle.html"
driver.get(url)

time.sleep(12)

logs = driver.get_log("performance")

m3u8_links = set()

for entry in logs:
    msg = entry["message"]
    if ".m3u8" in msg:
        found = re.findall(r'https?://[^"]+\.m3u8[^"]*', msg)
        for f in found:
            m3u8_links.add(f)

driver.quit()

print("\n🎯 BULUNAN M3U8 LİNKLERİ:\n")
for link in m3u8_links:
    print(link)
