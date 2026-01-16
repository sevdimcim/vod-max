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

EMAIL = "sonhan3087@gmail.com"
SIFRE = "996633Eko."
VIDEO_URL = "https://www.tabii.com/tr/watch/565323?trackId=566764"

def botu_baslat():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Dil hatasını önlemek için Türkçe tarayıcı gibi davranıyoruz
    chrome_options.add_argument("--lang=tr-TR")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        print("[*] Tabii ana sayfasına gidiliyor...")
        driver.get("https://www.tabii.com/tr")
        time.sleep(5)
        
        # Eğer çerez onay butonu varsa tıkla (Genelde formu kapatır)
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Kabul') or contains(text(), 'Accept')]")
            cookie_btn.click()
            print("[+] Çerezler kabul edildi.")
        except:
            pass

        print("[*] Giriş sayfasına yönleniliyor...")
        driver.get("https://www.tabii.com/tr/login")
        
        # Formun yüklenmesi için bekle
        print("[*] Form aranıyor...")
        # Hem ID hem name hem tip olarak her şeyi deniyoruz
        email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email'], input[type='email']")))
        
        email_field.send_keys(EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(SIFRE)
        
        print("[+] Bilgiler girildi, giriş yapılıyor...")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        time.sleep(10) # Giriş sonrası bekleme
        
        print(f"[*] Hedef videoya gidiliyor: {VIDEO_URL}")
        driver.get(VIDEO_URL)
        time.sleep(20) # Trafiği yakalamak için bekle

        logs = driver.get_log("performance")
        found_url = "Bulunamadı"
        
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in log["method"]:
                url = log["params"]["request"]["url"]
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
