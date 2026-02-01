import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import json, time, re, os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# AYARLAR
BASE_URL = "https://dizipal.uk"
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 3
DELAY_BETWEEN_FILMS = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

# Kategoriler (film)
CATEGORIES = {
    "aksiyon": f"{BASE_URL}/kategori/aksiyon/page/",
    "dram": f"{BASE_URL}/kategori/dram/page/",
    "komedi": f"{BASE_URL}/kategori/komedi/page/",
}

# Thread
MAX_WORKERS = 2
data_lock = Lock()

def get_chrome_version():
    """Chrome versiyonunu al"""
    try:
        import re
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        version = re.search(r'Google Chrome (\d+)', output).group(1)
        return int(version)
    except:
        return 120  # Varsayılan

def init_driver():
    """Chrome driver başlat (Cloudflare bypass)"""
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')
    options.add_argument('--headless')  # GitHub için
    
    chrome_version = get_chrome_version()
    print(f"Chrome v{chrome_version} başlatılıyor...")
    
    driver = uc.Chrome(options=options, version_main=chrome_version)
    driver.set_page_load_timeout(30)
    return driver

def get_soup_with_driver(url, driver=None):
    """Driver ile sayfa al"""
    try:
        if driver:
            driver.get(url)
            time.sleep(5)  # Cloudflare bekleme
            return BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        print(f"Driver hatası: {e}")
    return None

def slugify(text):
    """Slug oluştur"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:100]

def extract_film_data(div_element):
    """Film bilgisi çıkar"""
    try:
        a_tag = div_element.find('a')
        if not a_tag or not a_tag.get('href'):
            return None
        
        film_link = a_tag['href']
        if '/dizi/' in film_link:  # Dizi değil
            return None
        
        film_adi = a_tag.get('title', '').strip()
        if not film_adi:
            for tag in ['h4', 'h3', 'h2']:
                h_tag = div_element.find(tag)
                if h_tag and h_tag.text.strip():
                    film_adi = h_tag.text.strip()
                    break
        
        if not film_adi:
            return None
        
        # Poster
        poster_url = ""
        img_tag = div_element.find('img')
        if img_tag:
            poster_url = img_tag.get('data-src', '') or img_tag.get('src', '')
            if poster_url and '?' in poster_url:
                poster_url = poster_url.split('?')[0]
            if poster_url and poster_url.startswith('//'):
                poster_url = 'https:' + poster_url
        
        return {
            'film_adi': film_adi,
            'film_link': film_link,
            'poster_url': poster_url
        }
    except:
        return None

def extract_iframe_url(film_soup):
    """Iframe URL'sini çıkar"""
    if not film_soup:
        return ""
    
    # Iframe bul
    iframe = film_soup.find('iframe', {'src': True})
    if iframe:
        return iframe.get('src', '')
    
    # Alternatif
    player_div = film_soup.find('div', class_='video-player-area')
    if player_div:
        iframe = player_div.find('iframe', {'src': True})
        if iframe:
            return iframe.get('src', '')
    
    return ""

def process_film(film_info, filmler_data, driver=None):
    """Film işle"""
    if not film_info:
        return None
    
    film_adi = film_info['film_adi']
    film_link = film_info['film_link']
    poster_url = film_info['poster_url']
    
    film_id = slugify(film_adi)
    if not film_id:
        film_id = f"film_{hash(film_adi) % 1000000}"
    
    # Zaten var mı?
    with data_lock:
        if film_id in filmler_data:
            return film_id
    
    print(f"İşleniyor: {film_adi}")
    
    iframe_url = ""
    if film_link:
        try:
            full_url = urljoin(BASE_URL, film_link)
            print(f"  Sayfa: {full_url}")
            
            # Driver ile sayfayı al
            if driver:
                driver.get(full_url)
                time.sleep(3)
                film_soup = BeautifulSoup(driver.page_source, "html.parser")
                iframe_url = extract_iframe_url(film_soup)
                
                if iframe_url:
                    if not iframe_url.startswith(('http://', 'https://')):
                        if iframe_url.startswith('//'):
                            iframe_url = 'https:' + iframe_url
                        else:
                            iframe_url = urljoin(BASE_URL, iframe_url)
                    print(f"  Iframe: {iframe_url[:80]}...")
                else:
                    print(f"  Iframe yok")
            
            time.sleep(DELAY_BETWEEN_FILMS)
            
        except Exception as e:
            print(f"  Hata: {e}")
    
    # Kaydet
    with data_lock:
        filmler_data[film_id] = {
            "isim": film_adi,
            "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
            "link": iframe_url,
            "kaynak": "DiziPal"
        }
    
    return film_id

def scrape_category(category_name, category_url, page_num, filmler_data, film_counter, driver):
    """Kategori sayfasını tara"""
    page_url = f"{category_url}{page_num}/"
    
    try:
        print(f"\nKategori: {category_name.upper()}, Sayfa: {page_num}")
        
        driver.get(page_url)
        time.sleep(5)  # Cloudflare bekle
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Filmleri bul
        film_divs = soup.select("div.grid div.post-item")
        if not film_divs:
            film_divs = soup.find_all('div', class_=re.compile(r'post-item|film-item'))
        
        if not film_divs:
            print("Film bulunamadı")
            return 0
        
        print(f"{len(film_divs)} film bulundu")
        
        processed_count = 0
        film_infos = []
        
        for div in film_divs:
            info = extract_film_data(div)
            if info:
                film_infos.append(info)
        
        print(f"{len(film_infos)} film bilgisi çıkarıldı")
        
        # İşle
        for film_info in film_infos:
            result = process_film(film_info, filmler_data, driver)
            if result:
                processed_count += 1
                with data_lock:
                    film_counter[0] += 1
        
        print(f"{category_name} sayfa {page_num}: {processed_count} film işlendi")
        return processed_count
        
    except Exception as e:
        print(f"Hata: {e}")
        return 0

# ANA PROGRAM
def main():
    print("DiziPal Film Botu Başlatıldı (Cloudflare Bypass)")
    print(f"Her kategoriden {PAGES_TO_SCRAPE} sayfa taranacak")
    
    filmler_data = {}
    film_counter = [0]
    start_time = time.time()
    
    # Driver başlat
    driver = init_driver()
    
    try:
        # Test
        test_url = f"{BASE_URL}/kategori/aksiyon/page/1/"
        print(f"Test: {test_url}")
        driver.get(test_url)
        time.sleep(10)  # Cloudflare için uzun bekle
        
        # Cloudflare kontrolü
        if 'cloudflare' in driver.page_source.lower():
            print("Cloudflare tespit edildi, bekleniyor...")
            time.sleep(15)
        
        print("Cloudflare aşıldı!")
        
        # Kategorileri tara
        all_futures = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for cat_name, cat_url in CATEGORIES.items():
                for sayfa in range(1, PAGES_TO_SCRAPE + 1):
                    future = executor.submit(
                        scrape_category, cat_name, cat_url, sayfa, 
                        filmler_data, film_counter, driver
                    )
                    all_futures.append((future, cat_name, sayfa))
                    time.sleep(2)
            
            for future, cat_name, sayfa in all_futures:
                try:
                    future.result(timeout=60)
                except:
                    pass
        
        elapsed_time = time.time() - start_time
        
        print(f"\nİşlem tamamlandı!")
        print(f"Süre: {elapsed_time:.2f} saniye")
        print(f"Toplam Film: {len(filmler_data)}")
        
        if filmler_data:
            # JSON kaydet
            json_filename = "dizipal.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(filmler_data, f, ensure_ascii=False, indent=2)
            print(f"JSON: {json_filename} ({os.path.getsize(json_filename)/1024:.2f} KB)")
            
            # HTML oluştur (ilk 99 film)
            first_99 = dict(list(filmler_data.items())[:99])
            create_html_file(first_99, len(filmler_data))
        
    except KeyboardInterrupt:
        print("\nİşlem durduruldu")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if driver:
            driver.quit()

def create_html_file(data, total):
    """HTML oluştur"""
    json_str = json.dumps(data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>TITAN TV - DiziPal</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin:0; padding:0; background:#00040d; font-family:sans-serif; color:#fff; }}
        .filmpaneldis {{ background:#15161a; width:100%; margin:20px auto; padding:10px 5px; }}
        .baslik {{ color:#fff; padding:15px 10px; border-bottom:2px solid #572aa7; margin-bottom:15px; }}
        .filmpanel {{ width:12%; height:200px; background:#15161a; float:left; margin:1.14%; border-radius:15px; 
                     border:1px solid #323442; cursor:pointer; position:relative; overflow:hidden; }}
        .filmresim {{ width:100%; height:100%; }}
        .filmresim img {{ width:100%; height:100%; object-fit:cover; }}
        .filmisim {{ position:absolute; bottom:5px; width:100%; text-align:center; color:#fff; font-size:14px; 
                   padding:0 5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        @media(max-width:550px) {{ .filmpanel {{ width:31.33%; height:190px; margin:1%; }} }}
    </style>
</head>
<body>
    <div style="background:#15161a; padding:10px; border-bottom:1px solid #323442;">
        <div style="float:left;">
            <img src="https://i.hizliresim.com/t75soiq.png" style="width:40px; border-radius:50%;">
            <span style="color:#fff; line-height:40px; margin-left:10px;">TITAN TV - DiziPal</span>
        </div>
        <div style="float:right;">
            <input type="text" id="filmSearch" placeholder="Film Ara..." 
                   style="height:40px; width:180px; border:1px solid #323442; background:#000; color:#fff; padding:0 10px; border-radius:5px;">
            <button onclick="searchFilms()" style="height:40px; width:40px; background:#572aa7; border:none; color:#fff; border-radius:5px; cursor:pointer;">
                🔍
            </button>
        </div>
    </div>
    
    <div id="statusBar" style="color:#888; font-size:12px; padding:5px 10px; text-align:right;">
        DiziPal Film Arşivi ({total} Film)
    </div>
    
    <div class="filmpaneldis">
        <div class="baslik" id="baslikText">DİZİPAL FİLM ARŞİVİ ({total} Film)</div>
        <div id="gridContainer"></div>
    </div>
    
    <script>
        var localDB = {json_str};
        function renderFilms(data) {{
            var container = document.getElementById("gridContainer");
            container.innerHTML = "";
            var keys = Object.keys(data);
            
            for (var i = 0; i < Math.min(keys.length, 99); i++) {{
                var film = data[keys[i]];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() {{ if(film.link) window.open(film.link, '_blank'); else alert("Link yok"); }};
                item.innerHTML = `
                    <div class="filmresim">
                        <img src="${{film.resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'">
                    </div>
                    <div class="filmpanel">
                        <div class="filmisim">${{film.isim}}</div>
                    </div>
                `;
                container.appendChild(item);
            }}
        }}
        
        function searchFilms() {{
            var query = document.getElementById("filmSearch").value.toLowerCase();
            var results = {{}};
            for (var key in localDB) {{
                if (localDB[key].isim.toLowerCase().includes(query)) {{
                    results[key] = localDB[key];
                }}
            }}
            document.getElementById("baslikText").innerText = "Arama: " + Object.keys(results).length + " Film";
            renderFilms(results);
        }}
        
        window.onload = function() {{ renderFilms(localDB); }};
    </script>
</body>
</html>'''
    
    with open("dizipal.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML: dizipal.html ({os.path.getsize('dizipal.html')/1024:.2f} KB)")

if __name__ == "__main__":
    # Kontrol
    try:
        import undetected_chromedriver as uc
    except:
        print("undetected_chromedriver kurulu değil!")
        print("Kur: pip install undetected-chromedriver")
        sys.exit(1)
    
    main()
