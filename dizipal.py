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

    results = {}
    
    if os.path.exists("dizipal-tabi.json"):
        try:
            with open("dizipal-tabi.json", "r", encoding="utf-8") as f:
                results = json.load(f)
        except:
            results = {}

    driver = uc.Chrome(options=options, version_main=version)

    try:
        base_url = "https://dizipal.uk/platform/tabii/"
        print("Giriş yapılıyor...")
        driver.get(base_url)
        time.sleep(10)

        series_items = driver.find_elements(By.CLASS_NAME, "post-item")
        series_list = []
        
        for item in series_items:
            try:
                anchor = item.find_element(By.TAG_NAME, "a")
                img = item.find_element(By.TAG_NAME, "img")
                series_list.append({
                    "isim": anchor.get_attribute("title"),
                    "resim": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                    "ana_link": anchor.get_attribute("href")
                })
            except:
                continue

        for index, series in enumerate(series_list):
            series_name = series['isim']
            series_key = series_name.replace(" ", "-").replace("/", "-")
            
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

                # ŞİMDİ İŞLEME VE TEMİZLEME
                for ep_num, ep_link in enumerate(master_episode_list, 1):
                    custom_title = f"{series_name} {ep_num}. Bölüm"

                    # Kontrolü embed linki veya başlık üzerinden yapıyoruz
                    already_saved = any(d.get('bolum_baslik') == custom_title for d in results[series_key]["bolumler"])
                    
                    if already_saved:
                        continue

                    try:
                        driver.get(ep_link)
                        time.sleep(1.2)

                        iframe = driver.find_element(By.TAG_NAME, "iframe")
                        embed_link = iframe.get_attribute("src")

                        # JSON'a eklenecek veri (SAYFA LİNKİ YOK)
                        episode_data = {
                            "bolum_baslik": custom_title,
                            "link": embed_link  # "embed_link" ismini de kısalttım istersen
                        }
                        
                        results[series_key]["bolumler"].append(episode_data)
                        print(f"Eklendi: {custom_title}")

                    except Exception as e:
                        continue
                
                with open("dizipal-tabi.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

            except Exception as e:
                continue

    finally:
        driver.quit()
        print("Bitti.")

if __name__ == "__main__":
    scrape_dizipal_series()
