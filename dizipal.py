import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import re
import subprocess
import os

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
    links = [s.strip().split(' ')[0] for s in srcset.split(',')]
    return links[-1]

def scrape_dizipal_series():
    version = get_chrome_version()
    print(f"Sistem Chrome Versiyonu: {version}")

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')

    json_filename = "dizipal-tod.json"
    results = {}
    
    # Mevcut dosya varsa yükle
    if os.path.exists(json_filename):
        try:
            with open(json_filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except:
            results = {}

    driver = uc.Chrome(options=options, version_main=version)

    try:
        # Taranacak sayfalar listesi (TOD için 2 sayfa var)
        pages_to_scrape = [
            "https://dizipal.uk/platform/tod/page/1/",
            "https://dizipal.uk/platform/tod/page/2/"
        ]

        series_list = []

        print("TOD platformu taranıyor...")

        # 1. ADIM: Önce iki sayfadaki tüm dizileri listeye toplayalım
        for page_url in pages_to_scrape:
            print(f"Sayfa taranıyor: {page_url}")
            driver.get(page_url)
            time.sleep(5) # Sayfa yüklenmesi için bekleme

            series_items = driver.find_elements(By.CLASS_NAME, "post-item")
            
            for item in series_items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    series_data = {
                        "isim": anchor.get_attribute("title"),
                        "resim": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                        "ana_link": anchor.get_attribute("href")
                    }
                    series_list.append(series_data)
                except:
                    continue
        
        print(f"Toplam {len(series_list)} içerik bulundu. Bölümler çekilmeye başlanıyor...")

        # 2. ADIM: Toplanan dizilerin içini gez
        for index, series in enumerate(series_list):
            series_name = series['isim']
            series_key = series_name.replace(" ", "-").replace("/", "-")
            
            print(f"[{index+1}/{len(series_list)}] İşleniyor: {series_name}")

            if series_key not in results:
                results[series_key] = {
                    "isim": series_name,
                    "resim": series['resim'],
                    "bolumler": [] 
                }

            try:
                driver.get(series['ana_link'])
                time.sleep(2)

                season_urls = [driver.current_url]
                try:
                    season_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '?sezon=')]")
                    for s_el in season_elements:
                        s_link = s_el.get_attribute("href")
                        if s_link not in season_urls:
                            season_urls.append(s_link)
                except:
                    pass
                
                season_urls.sort()

                master_episode_list = []
                seen_episodes = set()
                
                # Sezonları gez ve bölüm linklerini topla
                for s_url in season_urls:
                    if s_url != driver.current_url:
                        driver.get(s_url)
                        time.sleep(1.5)
                    
                    ep_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/bolum/')]")
                    for ep in ep_elements:
                        l = ep.get_attribute("href")
                        if l not in seen_episodes:
                            master_episode_list.append(l)
                            seen_episodes.add(l)

                # Bölüm içlerine gir ve embed linkini al
                for ep_num, ep_link in enumerate(master_episode_list, 1):
                    custom_title = f"{series_name} {ep_num}. Bölüm"

                    # Zaten kayıtlıysa atla
                    already_saved = any(d.get('bolum_baslik') == custom_title for d in results[series_key]["bolumler"])
                    
                    if already_saved:
                        continue

                    try:
                        driver.get(ep_link)
                        time.sleep(1.2)

                        iframe = driver.find_element(By.TAG_NAME, "iframe")
                        embed_link = iframe.get_attribute("src")

                        episode_data = {
                            "bolum_baslik": custom_title,
                            "link": embed_link
                        }
                        
                        results[series_key]["bolumler"].append(episode_data)
                        print(f"   -> Eklendi: {custom_title}")

                        # Her bölüm eklendiğinde kaydet (Veri kaybını önlemek için)
                        with open(json_filename, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)

                    except Exception as e:
                        print(f"   -> Hata: {custom_title} alınamadı.")
                        continue
                
            except Exception as e:
                print(f"Dizi hatası: {series_name}")
                continue

    finally:
        driver.quit()
        print("İşlem tamamlandı.")

if __name__ == "__main__":
    scrape_dizipal_series()
