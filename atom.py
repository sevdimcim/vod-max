import cloudscraper
import json
import re
import os
import time
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

# --- AYARLAR ---
BASE_URL = "https://dizipal.cx"
MAX_WORKERS = 15
OUTPUT_FOLDER = "atom"

# Platform Listesi (URL slug : Dosya Adı)
# TV'yi turkcelltv olarak kaydetmek istediğin için mapping yaptık.
PLATFORMS = {
    "netflix": "netflix",
    "exxen": "exxen",
    "prime-video": "prime-video",
    "tabii": "tabii",
    "apple-tv": "apple-tv",
    "disney": "disney",
    "hbomax": "hbomax",
    "gain": "gain",
    "mubi": "mubi",
    "tod": "tod",
    "hulu": "hulu",
    "tv": "turkcelltv"  # URL'de 'tv', dosyada 'turkcelltv' olacak
}

# Tarayıcı simülasyonu
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def get_source(url):
    try:
        # Sayfa geçişlerinde çok seri istek atıp ban yememek için minik bekleme
        time.sleep(0.5) 
        res = scraper.get(url, timeout=10)
        return res.text if res.status_code == 200 else None
    except:
        return None

def get_highest_res_image(srcset_content):
    """srcset içindeki en yüksek kaliteli resim linkini ayıklar."""
    if not srcset_content:
        return ""
    parts = [s.strip().split(' ')[0] for s in srcset_content.split(',')]
    return parts[-1] if parts else ""

def fetch_iframe_only(ep_url):
    html = get_source(ep_url)
    if html:
        iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        if iframe:
            return iframe.group(1)
    return None

def clean_key(text):
    text = re.sub(r'[\s\:\,\']+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def scrape_platform(slug, filename_base):
    """Tek bir platformu baştan sona tarar ve kaydeder."""
    
    json_path = os.path.join(OUTPUT_FOLDER, f"{filename_base}.json")
    
    # Eğer dosya varsa üzerine yazmak yerine mevcut veriyi okuyup devam edebilirsin
    # Şimdilik sıfırdan başlatalım ki temiz olsun:
    results = {} 
    
    print(f"\n🌍 PLATFORM TARANIYOR: {slug.upper()} -> {filename_base}.json")
    
    page_num = 1
    found_any_on_platform = False

    while True:
        page_url = f"{BASE_URL}/platform/{slug}/page/{page_num}/"
        print(f"   📄 Sayfa {page_num} kontrol ediliyor...")
        
        html = get_source(page_url)
        
        # Sayfa boşsa veya içerik yoksa döngüyü kır (Otomatik Sayfa Algılama)
        if not html:
            print(f"   ⛔ Sayfa {page_num} yüklenemedi, platform tamamlandı sanırım.")
            break
        
        # İçerik var mı kontrolü (post-item class'ı var mı?)
        items = re.findall(r'<div class="post-item">.*?href="(.*?)".*?title="(.*?)".*?data-srcset="(.*?)"', html, re.S)
        
        if not items:
            print(f"   🚫 Sayfa {page_num} içinde içerik bulunamadı. Platform sonu.")
            break
            
        found_any_on_platform = True
        
        # Bu sayfadaki içerikleri işle
        for link, title, srcset in items:
            original_name = title
            json_key = clean_key(original_name)
            
            # Eğer zaten eklediysek atla
            if json_key in results:
                continue
                
            poster_url = get_highest_res_image(srcset)
            main_link = urljoin(BASE_URL, link)
            
            print(f"      💎 İşleniyor: {original_name}")
            
            results[json_key] = {
                "isim": original_name,
                "resim": poster_url,
                "bolumler": []
            }
            
            # İçerik detayına git
            source = get_source(main_link)
            if not source: continue

            # Sezon ve Bölüm Toplama
            seasons = re.findall(r'href=["\']([^"\']+\?sezon=\d+)["\']', source)
            season_urls = sorted(list(set([urljoin(BASE_URL, s) for s in seasons])))
            
            if not season_urls: 
                season_urls = [main_link]
            else:
                if main_link not in season_urls: 
                    season_urls.insert(0, main_link)

            all_ep_links = []
            for s_url in season_urls:
                s_html = get_source(s_url)
                if s_html:
                    eps = re.findall(r'href=["\']([^"\']+(?:bolum|anime-bolum)/[^"\']+)["\']', s_html)
                    # Bölüm sıralaması
                    eps = sorted(list(set(eps)), key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
                    for e in eps:
                        full_e = urljoin(BASE_URL, e)
                        if full_e not in all_ep_links:
                            all_ep_links.append(full_e)

            if all_ep_links:
                # Thread ile hızlıca iframe çek
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    iframe_list = list(executor.map(fetch_iframe_only, all_ep_links))
                
                count = 1
                for iframe_link in iframe_list:
                    if iframe_link:
                        results[json_key]["bolumler"].append({
                            "bolum_baslik": f"{original_name} {count}. Bölüm",
                            "link": iframe_link
                        })
                        count += 1
            else:
                # Film durumu
                iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', source)
                if iframe:
                    results[json_key]["bolumler"].append({
                        "bolum_baslik": f"{original_name} (Film)",
                        "link": iframe.group(1)
                    })

            # Her içerik eklendiğinde dosyayı güncelle (Crash olursa veri kaybı olmasın)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Bir sonraki sayfaya geç
        page_num += 1

def main():
    # 1. Klasör oluştur
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"📁 '{OUTPUT_FOLDER}' klasörü oluşturuldu.")

    # 2. Her platformu sırayla tara
    for slug, filename in PLATFORMS.items():
        try:
            scrape_platform(slug, filename)
        except Exception as e:
            print(f"❌ {slug} platformunda hata oluştu: {str(e)}")
            continue

    print("\n🏁 TÜM İŞLEMLER TAMAMLANDI! 🏁")

if __name__ == "__main__":
    main()
