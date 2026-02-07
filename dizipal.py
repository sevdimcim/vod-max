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
        # Taranacak sayfalar listesi (TOD)
        pages_to_scrape = [
            "https://dizipal.uk/platform/prime-video/page/1/",
            "https://dizipal.uk/platform/prime-video/page/2/",
            "https://dizipal.uk/platform/prime-video/page/3/",
            "https://dizipal.uk/platform/prime-video/page/4/",
            "https://dizipal.uk/platform/prime-video/page/5/",
            "https://dizipal.uk/platform/prime-video/page/6/",
            "https://dizipal.uk/platform/prime-video/page/7/",
            "https://dizipal.uk/platform/prime-video/page/8/",
            "https://dizipal.uk/platform/prime-video/page/9/",
            "https://dizipal.uk/platform/prime-video/page/10/",
            "https://dizipal.uk/platform/prime-video/page/11/",
            "https://dizipal.uk/platform/prime-video/page/12/",
            "https://dizipal.uk/platform/prime-video/page/13/",
            "https://dizipal.uk/platform/prime-video/page/14/",
            "https://dizipal.uk/platform/prime-video/page/15/"
        ]

        series_list = []

        print("TOD platformu (Diziler ve Filmler) taranıyor...")

        # 1. ADIM: Listeleri Topla
        for page_url in pages_to_scrape:
            print(f"Sayfa taranıyor: {page_url}")
            driver.get(page_url)
            time.sleep(5)

            items = driver.find_elements(By.CLASS_NAME, "post-item")
            
            for item in items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    data = {
                        "isim": anchor.get_attribute("title"),
                        "resim": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                        "ana_link": anchor.get_attribute("href")
                    }
                    series_list.append(data)
                except:
                    continue
        
        print(f"Toplam {len(series_list)} içerik bulundu. İşlem başlıyor...")

        # 2. ADIM: İçerikleri işle (Dizi mi Film mi kontrol et)
        for index, item in enumerate(series_list):
            name = item['isim']
            key = name.replace(" ", "-").replace("/", "-")
            
            print(f"[{index+1}/{len(series_list)}] İnceleniyor: {name}")

            if key not in results:
                results[key] = {
                    "isim": name,
                    "resim": item['resim'],
                    "bolumler": [] 
                }

            try:
                driver.get(item['ana_link'])
                time.sleep(2)

                # --- DİZİ Mİ FİLM Mİ KONTROLÜ ---
                # Sayfada bölüm veya sezon linki var mı diye bakıyoruz
                is_series = False
                try:
                    season_check = driver.find_elements(By.XPATH, "//a[contains(@href, '?sezon=')]")
                    episode_check = driver.find_elements(By.XPATH, "//a[contains(@href, '/bolum/')]")
                    
                    if len(season_check) > 0 or len(episode_check) > 0:
                        is_series = True
                except:
                    is_series = False

                # --- SENARYO 1: DİZİ İSE ---
                if is_series:
                    print(f"   -> Tür: Dizi tespit edildi.")
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
                    
                    # Sezonları gez
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

                    # Bölümlere gir
                    for ep_num, ep_link in enumerate(master_episode_list, 1):
                        custom_title = f"{name} {ep_num}. Bölüm"
                        
                        if any(d.get('bolum_baslik') == custom_title for d in results[key]["bolumler"]):
                            continue

                        try:
                            driver.get(ep_link)
                            time.sleep(1.2)
                            iframe = driver.find_element(By.TAG_NAME, "iframe")
                            embed_link = iframe.get_attribute("src")
                            
                            results[key]["bolumler"].append({
                                "bolum_baslik": custom_title,
                                "link": embed_link
                            })
                            print(f"      + Eklendi: {custom_title}")
                            
                            # Her kayıtta json güncelle
                            with open(json_filename, "w", encoding="utf-8") as f:
                                json.dump(results, f, ensure_ascii=False, indent=2)

                        except:
                            print(f"      ! Hata: {custom_title}")
                            continue

                # --- SENARYO 2: FİLM İSE ---
                else:
                    print(f"   -> Tür: Film tespit edildi.")
                    movie_title = f"{name} (Film)"
                    
                    # Eğer daha önce eklenmişse geç
                    if any(d.get('bolum_baslik') == movie_title for d in results[key]["bolumler"]):
                        print("      - Zaten listede var.")
                        continue
                    
                    try:
                        # Film olduğu için iframe direk bu sayfadadır
                        iframe = driver.find_element(By.TAG_NAME, "iframe")
                        embed_link = iframe.get_attribute("src")
                        
                        results[key]["bolumler"].append({
                            "bolum_baslik": movie_title,
                            "link": embed_link
                        })
                        print(f"      + Film Eklendi: {name}")

                        with open(json_filename, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)

                    except Exception as e:
                        print(f"      ! Hata: Film iframe'i bulunamadı. {e}")

            except Exception as e:
                print(f"Genel Hata ({name}): {e}")
                continue

    finally:
        driver.quit()
        print("Tüm işlemler bitti.")

if __name__ == "__main__":
    scrape_dizipal_series()
