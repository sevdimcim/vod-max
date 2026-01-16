import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- BİLGİLER ---
EMAIL = "sonhan3087@gmail.com"
SIFRE = "996633Eko."
VIDEO_URL = "https://www.tabii.com/tr/watch/565323?trackId=566764"

def botu_baslat():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    print("[*] Chrome başlatılıyor...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20) # 20 saniye bekleme süresi

    try:
        # 1. Giriş Sayfasına Git
        print("[*] Giriş sayfasına gidiliyor...")
        driver.get("https://www.tabii.com/tr/login")
        
        # E-posta kutusunun yüklenmesini bekle (CSS selector deniyoruz)
        print("[*] Giriş formu bekleniyor...")
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
        
        print("[+] Form bulundu, bilgiler giriliyor...")
        email_input.send_keys(EMAIL)
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        password_input.send_keys(SIFRE)
        
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()
        
        # Girişin tamamlanmasını ve ana sayfaya yönlendirmeyi bekle
        time.sleep(10)
        print("[+] Giriş yapıldı, video sayfasına geçiliyor...")
        
        # 2. Video Sayfasına Git
        driver.get(VIDEO_URL)
        print("[*] Video sayfası yüklendi, trafik izleniyor (20 sn)...")
        time.sleep(20) 

        # 3. Loglardan Linki Yakala
        logs = driver.get_log("performance")
        found_url = "Bulunamadı"
        
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in log["method"]:
                url = log["params"]["request"]["url"]
                # IDM'nin yakaladığı video yapılarını süz
                if "cms-tabii" in url or "video_" in url or ".m3u8" in url or ".mp4" in url:
                    found_url = url
                    break

        print(f"\n[🚀] SONUÇ: {found_url}\n")
        
        with open("yakalanan_link.txt", "w") as f:
            f.write(found_url)

    except Exception as e:
        print(f"[-] HATA OLUŞTU: {str(e)}")
        # Hata anında ne gördüğünü anlamak için ekran görüntüsü alalım
        driver.save_screenshot("hata_aninda_ekran.png")
        print("[!] Hata ekran görüntüsü kaydedildi (hata_aninda_ekran.png).")
    finally:
        driver.quit()

if __name__ == "__main__":
    botu_baslat()
    
