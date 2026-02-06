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

        print("--- Dizi Listesi Toplanıyor ---")
        series_items = driver.find_elements(By.CLASS_NAME, "post-item")
        series_list = []
        
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
        
        print(f"Toplam {len(series_list)} dizi bulundu.")

        # HER BİR DİZİ İÇİN
        for index, series in enumerate(series_list):
            series_name = series['isim']
            print(f"\n[{index+1}/{len(series_list)}] İşleniyor: {series_name}")
            
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

                # --- SEZON URL'LERİNİ TOPLA ---
                # Set kullanarak aynı linki iki kere eklemeyi önleyelim ama sıralamayı korumak için list kullanalım
                season_urls = [driver.current_url] 
                
                try:
                    # Sezon linklerini bul (URL'de ?sezon= geçenler)
                    season_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '?sezon=')]")
                    for s_el in season_elements:
                        s_link = s_el.get_attribute("href")
                        if s_link not in season_urls:
                            season_urls.append(s_link)
                except:
                    pass
                
                # Sezon linklerini sıralayalım ki 1. sezon, 2. sezon diye sırayla gitsin
                # Link yapısı genelde ...?sezon=2 şeklindedir. String sıralaması iş görür.
                season_urls.sort() 

                # --- TÜM BÖLÜM LİNKLERİNİ TEK BİR LİSTEDE BİRLEŞTİR ---
                master_episode_list = []
                seen_episodes = set()

                print("   > Bölüm linkleri toplanıyor (Sezonlar taranıyor)...")
                
                for s_url in season_urls:
                    if s_url != driver.current_url:
                        driver.get(s_url)
                        time.sleep(1.5)
                    
                    # Sayfadaki bölüm linklerini al
                    # DİKKAT: Sayfada bölümler genelde 1'den sona doğru sıralıdır.
                    # Eğer site tersten sıralıyorsa (en yeni en üstteyse) burada `ep_elements` listesini reverse() etmek gerekebilir.
                    # Dizipal genelde düz sıralar varsayıyoruz.
                    ep_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/bolum/')]")
                    
                    for ep in ep_elements:
                        l = ep.get_attribute("href")
                        if l not in seen_episodes:
                            master_episode_list.append(l)
                            seen_episodes.add(l)

                print(f"   > Toplam {len(master_episode_list)} bölüm bulundu. Sırayla çekiliyor...")

                # --- LİNKLERİ İŞLE VE NUMARALANDIR (Mutlak Numaralandırma) ---
                # enumerate(list, 1) -> Sayacı 1'den başlatır.
                for ep_num, ep_link in enumerate(master_episode_list, 1):
                    
                    # JSON'da oluşturacağımız başlık formatı: "Ayşe 16. Bölüm"
                    custom_title = f"{series_name} {ep_num}. Bölüm"

                    # Bu başlık zaten var mı kontrol et (Tekrar çekmemek için)
                    already_saved = False
                    for saved_ep in results[series_key]["bolumler"]:
                        # Sadece başlık kontrolü yapmak riskli olabilir (isim değiştiği için), link kontrolü daha sağlıklı
                        if saved_ep.get("sayfa_link") == ep_link:
                            already_saved = True
                            break
                    
                    if already_saved:
                        print(f"      (Atlandı) Zaten var: {custom_title}")
                        continue

                    try:
                        driver.get(ep_link)
                        time.sleep(1.2)

                        iframe = driver.find_element(By.TAG_NAME, "iframe")
                        embed_link = iframe.get_attribute("src")

                        episode_data = {
                            "bolum_baslik": custom_title, # İsteğine uygun format
                            "sayfa_link": ep_link,
                            "embed_link": embed_link
                        }
                        
                        results[series_key]["bolumler"].append(episode_data)
                        print(f"      OK: {custom_title}")

                    except Exception as e:
                        print(f"      Hata: {custom_title} - {e}")
                        continue
                
                # Her dizi bitiminde kaydet
                with open("dizipal-tabi.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"   Dizi Hatası: {series_name} - {e}")
                continue

    except Exception as e:
        print(f"Genel Hata: {e}")
    finally:
        driver.quit()
        print("İşlem bitti.")

if __name__ == "__main__":
    scrape_dizipal_series()
