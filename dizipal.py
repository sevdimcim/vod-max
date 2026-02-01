import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import subprocess

def get_chrome_version():
    try:
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        return int(re.search(r'Google Chrome (\d+)', output).group(1))
    except: return None

def get_full_res_image(srcset):
    # srcset içindeki en yüksek çözünürlüklü (genelde en sondaki) linki alır
    if not srcset: return None
    links = [s.strip().split(' ')[0] for s in srcset.split(',')]
    return links[-1]

def scrape_dizipal():
    version = get_chrome_version()
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, version_main=version)
    results = {}

    try:
        # Test için ilk 5 sayfa
        for page_num in range(1, 6):
            url = f"https://dizipal.uk/filmler/page/{page_num}/"
            print(f"--- Sayfa {page_num} taranıyor: {url} ---")
            driver.get(url)
            
            # İlk sayfada Cloudflare için ekstra bekleme
            if page_num == 1: time.sleep(15)
            
            # Film kutularını yakala
            items = driver.find_elements(By.CLASS_NAME, "post-item")
            
            page_data = []
            for item in items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    
                    title = anchor.get_attribute("title")
                    movie_url = anchor.get_attribute("href")
                    # En yüksek kalite afişi srcset içinden çekiyoruz
                    poster_url = get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src")
                    
                    page_data.append({
                        "isim": title,
                        "resim": poster_url,
                        "ana_link": movie_url
                    })
                except: continue

            # Her filmin içine girip iframe çekme
            for movie in page_data:
                try:
                    print(f"Detay çekiliyor: {movie['isim']}")
                    driver.get(movie['ana_link'])
                    time.sleep(2) # Sayfanın yüklenmesi için kısa bekleme
                    
                    # iframe içindeki src'yi al
                    iframe = driver.find_element(By.TAG_NAME, "iframe")
                    embed_link = iframe.get_attribute("src")
                    
                    # JSON formatına uygun anahtar ismi oluştur (Boşlukları tire yap)
                    key = movie['isim'].replace(" ", "-")
                    results[key] = {
                        "isim": movie['isim'],
                        "resim": movie['resim'],
                        "link": embed_link
                    }
                except:
                    print(f"Hata: {movie['isim']} linki çekilemedi.")
                    continue

        # JSON dosyasına kaydet
        with open("dizipal.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"İşlem tamam! Toplam {len(results)} film kaydedildi.")

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_dizipal()
