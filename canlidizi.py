from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import re

caps = DesiredCapabilities.CHROME
caps["goog:loggingPrefs"] = {"performance": "ALL"}

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options, desired_capabilities=caps)

url = "https://www.canlidizi14.com/kismetse-olur-askin-gucu-74-bolum-izle.html"
driver.get(url)

time.sleep(10)

logs = driver.get_log("performance")

m3u8_links = set()

for entry in logs:
    message = entry["message"]
    if ".m3u8" in message:
        found = re.findall(r'https?://[^"]+\.m3u8[^"]*', message)
        for f in found:
            m3u8_links.add(f)

driver.quit()

print("\n🎯 BULUNAN M3U8:\n")
for m in m3u8_links:
    print(m)
