import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIG AYARLARI ---
EMAIL = "sonhan3087@gmail.com"
SIFRE = "996633Eko."
VIDEO_URL = "https://www.tabii.com/tr/watch/565323?trackId=566764"

def botu_baslat():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Config'deki eski UA yerine güncel bir tane kullanıyoruz
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--lang=tr-TR")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        # 1. Giriş Sayfasına Git
        print("[*] Tabii Giriş Sayfası Yükleniyor...")
        driver.get("https://www.tabii.com/tr/login")
        
        # Sayfanın bot korumasına takılıp takılmadığını anlamak için başlığı kontrol et
        print(f"[*] Sayfa Başlığı: {driver.title}")
        
        # vE1 hatasını önlemek için formu bulmadan önce kısa bir bekleme (insan taklidi)
        time.sleep(5)
        
        # Email kutusunu config'deki mantıkla ama Selenium seçicisiyle bul
        email_field = wait.until(EC.element_to_be_clickable((By.NAME, "email")))
        email_field.send_keys(EMAIL)
        
        pass_field = driver.find_element(By.NAME, "password")
        pass_field.send_keys(SIFRE)
        
        print("[+] Bilgiler girildi. Giriş butonuna basılıyor...")
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()
        
        # Giriş sonrası trafiği izlemek için video sayfasına geç
        time.sleep(10)
        driver.get(VIDEO_URL)
        print("[*] Video trafiği koklanıyor...")
        time.sleep(20)

        logs = driver.get_log("performance")
        found_url = "LİNK BULUNAMADI (vE1 veya Bölge Engeli)"
        
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in log["method"]:
                url = log["params"]["request"]["url"]
                # Config'deki mp4/m3u8 yapılarını yakala
                if any(x in url for x in ["cms-tabii", "video_", ".m3u8", ".mp4"]):
                    found_url = url
                    break

        print(f"\n[🚀] SONUÇ: {found_url}\n")
        with open("yakalanan_link.txt", "w") as f:
            f.write(found_url)

    except Exception as e:
        print(f"[-] Hata: {str(e)}")
        driver.save_screenshot("hata_aninda_ekran.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    botu_baslat()
