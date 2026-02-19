import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import subprocess
import os
import html

# --- AYARLAR ---
BASE_URL = "https://dizipal.bar" # Çalışan domain (değişirse buradan güncelle)
PLATFORM_SLUG = "hbomax"
OUTPUT_FILE = "hbomax.json"

def get_chrome_version():
    """Chrome versiyonunu tespit eder (Linux/GitHub Actions için önemli)"""
    try:
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        version = re.search(r'Google Chrome (\d+)', output).group(1)
        return int(version)
    except:
        return None

def clean_key(text):
    """JSON keyleri için temizleme yapar"""
    text = html.unescape(text)
    text = re.sub(r'[\s\:\,\'’"”]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def get_full_res_image(srcset):
    """Resim kalitesini seçer"""
    if not srcset:
        return ""
    links = [s.strip().split(' ')[0] for s in srcset.split(',')]
    return links[-1] if links else ""

def scrape_hbomax():
    version = get_chrome_version()
    print(f"Sistem Chrome Versiyonu: {version}")

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')
    # GitHub Actions'da 'xvfb' kullanıyorsan headless yapmana gerek yok.
    # Eğer hata alırsan '--headless=new' ekleyebilirsin ama CF bazen yakalar.

    # Mevcut veriyi yükle
    results = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
            print(f"Mevcut dosya yüklendi. {len(results)} içerik var.")
        except:
            pass

    driver = uc.Chrome(options=options, version_main=version)

    try:
        # 1. ADIM: ANASAYFAYA GİT VE BEKLE (CF GEÇİŞİ)
        print("Cloudflare geçişi için bekleniyor...")
        driver.get(BASE_URL)
        time.sleep(15) 

        page_num = 1
        
        while True:
            platform_url = f"{BASE_URL}/platform/{PLATFORM_SLUG}/page/{page_num}/"
            print(f"\n--- Sayfa {page_num} Taranıyor: {platform_url} ---")
            
            driver.get(platform_url)
            time.sleep(3)

            # Sayfa boş mu veya bitti mi kontrolü
            if "Sayfa bulunamadı" in driver.title or len(driver.find_elements(By.CLASS_NAME, "post-item")) == 0:
                print("Sayfa boş veya bitti. İşlem tamamlandı.")
                break

            # Sayfadaki içerikleri topla
            items = driver.find_elements(By.CLASS_NAME, "post-item")
            page_contents = []
            
            for item in items:
                try:
                    anchor = item.find_element(By.TAG_NAME, "a")
                    img = item.find_element(By.TAG_NAME, "img")
                    title = anchor.get_attribute("title")
                    
                    # Key kontrolü (Zaten varsa atla - Vakit kazan)
                    key = clean_key(title)
                    if key in results:
                        continue

                    page_contents.append({
                        "title": title,
                        "url": anchor.get_attribute("href"),
                        "img": get_full_res_image(img.get_attribute("srcset")) or img.get_attribute("src"),
                        "key": key
                    })
                except:
                    continue
            
            print(f"Bu sayfada işlenecek yeni içerik sayısı: {len(page_contents)}")

            # İçerik detaylarına gir
            for content in page_contents:
                try:
                    print(f"> İnceleniyor: {content['title']}")
                    driver.get(content['url'])
                    time.sleep(2) # Yükleme beklemesi

                    key = content['key']
                    results[key] = {
                        "isim": content['title'],
                        "resim": content['img'],
                        "bolumler": []
                    }

                    # --- SENARYO 1: FİLM Mİ? (Direkt Iframe var mı?) ---
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    has_episodes = False
                    
                    # Sayfada bölüm listesi var mı kontrol et
                    # Genelde 'bölümler' listesi varsa dizidir.
                    episode_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='bolum']")
                    
                    if not episode_elements and iframes:
                        # Bu bir FİLM
                        embed_src = iframes[0].get_attribute("src")
                        results[key]["bolumler"].append({
                            "bolum_baslik": f"{content['title']} (Film)",
                            "link": embed_src
                        })
                        print(f"  + Film eklendi.")
                    
                    else:
                        # --- SENARYO 2: DİZİ (Sezon ve Bölümler) ---
                        print("  + Dizi tespit edildi, bölümler taranıyor...")
                        
                        # 1. Sezon Linklerini Bul
                        season_links = []
                        # URL yapısında ?sezon=X arıyoruz
                        season_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='?sezon=']")
                        
                        temp_season_urls = set()
                        for s in season_elements:
                            href = s.get_attribute("href")
                            temp_season_urls.add(href)
                        
                        # Eğer sezon linki bulamadıysak ama bölüm linkleri varsa (Tek sezonluk dizi)
                        if not temp_season_urls:
                            season_links.append(content['url']) # Mevcut sayfa tek sezon
                        else:
                            season_links = sorted(list(temp_season_urls))

                        # Tüm Sezonları Gez
                        all_episode_urls = []
                        
                        for s_link in season_links:
                            if s_link != driver.current_url:
                                driver.get(s_link)
                                time.sleep(1.5)
                            
                            # Bölüm linklerini topla (Regex ile daha güvenli)
                            # href içinde 'bolum' geçenleri al
                            eps = driver.find_elements(By.CSS_SELECTOR, "a[href*='bolum']")
                            for ep in eps:
                                ep_url = ep.get_attribute("href")
                                if ep_url not in all_episode_urls:
                                    all_episode_urls.append(ep_url)

                        # Bölüm linklerini sırala (opsiyonel, genelde site sırayla verir)
                        print(f"  + Toplam {len(all_episode_urls)} bölüm bulundu. Linkler alınıyor...")

                        # Her bölüme gir ve iframe al (En yavaş kısım burası)
                        ep_count = 1
                        for ep_url in all_episode_urls:
                            try:
                                driver.get(ep_url)
                                # Iframe yüklenene kadar bekle (max 5 sn)
                                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                                
                                ep_iframe = driver.find_element(By.TAG_NAME, "iframe")
                                src = ep_iframe.get_attribute("src")
                                
                                results[key]["bolumler"].append({
                                    "bolum_baslik": f"{content['title']} {ep_count}. Bölüm", # İstersen başlığı sayfadan da çekebilirsin
                                    "link": src
                                })
                                ep_count += 1
                                # Çok hızlı yaparsak IP ban yiyebiliriz
                                time.sleep(0.5) 
                            except Exception as e_ep:
                                print(f"    ! Bölüm hatası: {e_ep}")
                                continue

                    # İçerik bittiğinde anlık kaydet
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)

                except Exception as e:
                    print(f"Hata oluştu ({content['title']}): {e}")
                    continue

            page_num += 1

    except Exception as e:
        print(f"Kritik Hata: {e}")

    finally:
        driver.quit()
        print(f"Bot durdu. Toplam {len(results)} içerik kaydedildi.")

if __name__ == "__main__":
    scrape_hbomax()
