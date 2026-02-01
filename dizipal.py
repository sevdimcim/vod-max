import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import re
import subprocess
import os
import sys

def get_chrome_version():
    try:
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        version = re.search(r'Google Chrome (\d+)', output).group(1)
        return int(version)
    except:
        return None

def get_full_res_image(srcset):
    if not srcset:
        return None
    # srcset içindeki virgülle ayrılmış en yüksek çözünürlüğü seçer
    links = [s.strip().split(' ')[0] for s in srcset.split(',')]
    return links[-1]

def scrape_dizipal():
    version = get_chrome_version()
    print(f"Sistem Chrome Versiyonu: {version}")

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')

    # Eğer dosya varsa içindekileri yükle (kaldığı yerden devam etmesi için değil, veriyi korumak için)
    results = {}
    if os.path.exists("dizipal.json"):
        try:
            with open("dizipal.json", "r", encoding="utf-8") as f:
                results = json.load(f)
        except:
            results = {}

    driver = uc.Chrome(options=options, version_main=version)

    try:
        # 1. ADIM: CLOUDFLARE GEÇİŞİ
        print("Giriş yapılıyor, Cloudflare bekleniyor...")
        driver.get("https://dizipal.uk/")
        time.sleep(20)

        # 2. ADIM: SAYFALARI DÖN
        for page_num in range(1, 135):
            print(f"\n--- Sayfa {page_num}/134 taranıyor ---")
            driver.get(f"https://dizipal.uk/filmler/page/{page_num}/")
            time.sleep(2) # Liste sayfasının yüklenmesi

            items = driver.find_elements(By.CLASS_NAME, "post-item")
            if not items:
                print(f"Uyarı: Sayfa {page_num} boş veya erişim engellendi.")
                continue

            page_movies = []
            for item in items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    page_movies.append({
                        "isim": anchor.get_attribute("title"),
                        "resim": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                        "ana_link": anchor.get_attribute("href")
                    })
                except:
                    continue

            # 3. ADIM: FİLM DETAYLARINA GİR
            for movie in page_movies:
                try:
                    driver.get(movie['ana_link'])
                    # Hız ayarı: 1.2 saniye bekleme bloklanmayı önler
                    time.sleep(1.2) 
                    
                    iframe = driver.find_element(By.TAG_NAME, "iframe")
                    embed_link = iframe.get_attribute("src")
                    
                    # JSON Key oluştur (Tireli format)
                    key = movie['isim'].replace(" ", "-").replace("/", "-")
                    results[key] = {
                        "isim": movie['isim'],
                        "resim": movie['resim'],
                        "link": embed_link
                    }
                    print(f"Başarılı: {movie['isim']}")
                except Exception as e:
                    print(f"Hata: {movie['isim']} - Detay: {str(e)[:50]}")
                    time.sleep(2) # Hata alınca siteyi dinlendir
                    continue

            # Her 5 sayfada bir JSON dosyasını yerel olarak güncelle
            if page_num % 5 == 0:
                with open("dizipal.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f">>> Ara kayıt yapıldı. Toplam film: {len(results)}")

    except Exception as e:
        print(f"Kritik çalışma hatası: {e}")
    finally:
        # Çıkarken son kez kaydet
        with open("dizipal.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        driver.quit()
        print(f"Bot durduruldu. Toplam toplanan veri: {len(results)}")

if __name__ == "__main__":
    scrape_dizipal()
