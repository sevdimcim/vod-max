import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import re
import subprocess
import sys

def get_chrome_version():
    try:
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        return int(re.search(r'Google Chrome (\d+)', output).group(1))
    except: return None

def get_full_res_image(srcset):
    if not srcset: return None
    links = [s.strip().split(' ')[0] for s in srcset.split(',')]
    return links[-1]

def scrape_dizipal():
    version = get_chrome_version()
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Resim yüklemeyi kapatıp hızı artırmak istersen alttaki satırı açabilirsin
    # options.add_argument('--blink-settings=imagesEnabled=false')
    
    driver = uc.Chrome(options=options, version_main=version)
    results = {}

    try:
        # 1. ADIM: CLOUDFLARE BARAJI (Sadece bir kez)
        print("Cloudflare barajı aşılıyor...")
        driver.get("https://dizipal.uk/")
        time.sleep(15) # Bu ilk bekleme kritik, sonrası hızlı.

        for page_num in range(1, 135):
            url = f"https://dizipal.uk/filmler/page/{page_num}/"
            print(f"\nSayfa {page_num}/134 açılıyor...")
            
            driver.get(url)
            # Sayfa yüklendiği gibi elemanları bul (Beklemeyi 1 saniyeye indirdik)
            time.sleep(1) 
            
            items = driver.find_elements(By.CLASS_NAME, "post-item")
            
            # Bu sayfadaki filmlerin listesini hızlıca topla
            temp_movies = []
            for item in items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    temp_movies.append({
                        "isim": anchor.get_attribute("title"),
                        "resim": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                        "ana_link": anchor.get_attribute("href")
                    })
                except: continue

            # 2. ADIM: FİLM SAYFALARINA DAL (Hızlı Tur)
            for movie in temp_movies:
                try:
                    driver.get(movie['ana_link'])
                    # Iframe'i bulmak için yarım saniye yeterli olmalı
                    time.sleep(0.5) 
                    
                    iframe = driver.find_element(By.TAG_NAME, "iframe")
                    embed_link = iframe.get_attribute("src")
                    
                    key = movie['isim'].replace(" ", "-").replace("/", "-")
                    results[key] = {
                        "isim": movie['isim'],
                        "resim": movie['resim'],
                        "link": embed_link
                    }
                    print(f"Bitti: {movie['isim']}")
                except:
                    print(f"Hata: {movie['isim']}")
                    continue
            
            # Her 10 sayfada bir kaydet (Hız için kayıt sıklığını düşürdük)
            if page_num % 10 == 0:
                with open("dizipal.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Kritik durma: {e}")
    finally:
        with open("dizipal.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        driver.quit()
        print(f"İşlem bitti. Toplam: {len(results)}")

if __name__ == "__main__":
    scrape_dizipal()
