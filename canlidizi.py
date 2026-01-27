from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

driver.get("https://www.canlidizi14.com/kismetse-olur-askin-gucu-74-bolum-izle.html")

time.sleep(10)

html = driver.page_source

links = re.findall(r"https?://[^\s\"']+\.m3u8[^\s\"']*", html)

print("\n=== M3U8 BULUNAN ===\n")
for l in set(links):
    print(l)

driver.quit()
