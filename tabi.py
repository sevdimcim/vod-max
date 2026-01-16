import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- BİLGİLER ---
EMAIL = "sonhan3087@gmail.com"
SIFRE = "996633Eko."
VIDEO_URL = "https://www.tabii.com/tr/watch/565323?trackId=566764"

def botu_baslat():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Ekransız mod (ŞART)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Network loglarını okumak için gerekli ayar
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    print("[*] Chrome başlatılıyor...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # 1. Giriş Yap
        driver.get("https://www.tabii.com/tr/login")
        time.sleep(5)
        driver.find_element(By.NAME, "email").send_keys(EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SIFRE)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        print("[+] Giriş yapıldı, video sayfasına gidiliyor...")
        
        time.sleep(7)
        
        # 2. Video Sayfasına Git
        driver.get(VIDEO_URL)
        print("[*] Sayfa yüklendi, trafik koklanıyor (15 sn bekle)...")
        time.sleep(15) # Videonun başlaması için süre tanı

        # 3. Loglardan Linki Cımbızla
        logs = driver.get_log("performance")
        found_url = "Bulunamadı"
        
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in log["method"]:
                url = log["params"]["request"]["url"]
                # IDM'nin yakaladığı yapıları filtrele
                if "cms-tabii" in url or "video_" in url or ".m3u8" in url:
                    found_url = url
                    break

        print(f"\n[🚀] SONUÇ: {found_url}\n")
        
        with open("yakalanan_link.txt", "w") as f:
            f.write(found_url)

    except Exception as e:
        print(f"[-] Hata: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    botu_baslat()
