# dizipal_bot.py
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import json, time, re, os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# ============================================================================
# AYARLAR
# ============================================================================
BASE_URL = "https://dizipal.uk"
PAGES_TO_SCRAPE = 3  # Her kategoriden kaç sayfa
DELAY_BETWEEN_FILMS = 2.0  # Filmler arası bekleme (saniye)

# DiziPal film kategorileri
CATEGORIES = {
    "aksiyon": f"{BASE_URL}/kategori/aksiyon/page/",
    "dram": f"{BASE_URL}/kategori/dram/page/",
    "komedi": f"{BASE_URL}/kategori/komedi/page/",
    "macera": f"{BASE_URL}/kategori/macera/page/",
    "gerilim": f"{BASE_URL}/kategori/gerilim/page/",
}

# JSON dosya adı (HDFilmCehennemi ile aynı yapıda)
JSON_FILENAME = "dizipal.json"
HTML_FILENAME = "dizipal.html"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/dizipal.json"

# Thread ayarları
MAX_WORKERS = 2
data_lock = Lock()

# ============================================================================
# CHROME DRIVER - CLOUDFLARE BYPASS
# ============================================================================
def get_chrome_version():
    """Sistemdeki Chrome versiyonunu al"""
    try:
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        version = re.search(r'Google Chrome (\d+)', output).group(1)
        return int(version)
    except:
        return 120  # Varsayılan versiyon

def init_driver():
    """Chrome driver başlat (Cloudflare bypass için)"""
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')
    options.add_argument('--headless')  # GitHub için headless
    
    chrome_version = get_chrome_version()
    print(f"Chrome v{chrome_version} başlatılıyor...")
    
    driver = uc.Chrome(options=options, version_main=chrome_version)
    driver.set_page_load_timeout(30)
    return driver

# ============================================================================
# UTILITY FONKSİYONLAR
# ============================================================================
def slugify(text):
    """Film isminden slug oluştur (JSON key'i için)"""
    if not text:
        return ""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:100]

def extract_film_data(div_element):
    """Div elementinden film bilgilerini çıkar"""
    try:
        a_tag = div_element.find('a')
        if not a_tag or not a_tag.get('href'):
            return None
        
        film_link = a_tag['href']
        
        # SADECE FİLM (dizi değil)
        if '/dizi/' in film_link:
            return None
        
        # Film adı
        film_adi = a_tag.get('title', '').strip()
        if not film_adi:
            for tag in ['h4', 'h3', 'h2']:
                h_tag = div_element.find(tag)
                if h_tag and h_tag.text.strip():
                    film_adi = h_tag.text.strip()
                    break
        
        if not film_adi:
            return None
        
        # Poster URL
        poster_url = ""
        img_tag = div_element.find('img')
        if img_tag:
            poster_url = img_tag.get('data-src', '') or img_tag.get('src', '')
            if poster_url:
                if '?' in poster_url:
                    poster_url = poster_url.split('?')[0]
                if poster_url.startswith('//'):
                    poster_url = 'https:' + poster_url
        
        return {
            'film_adi': film_adi,
            'film_link': film_link,
            'poster_url': poster_url
        }
    except:
        return None

def extract_iframe_url(film_soup):
    """Film sayfasından iframe embed linkini çıkar"""
    if not film_soup:
        return ""
    
    # 1. Doğrudan iframe
    iframe = film_soup.find('iframe', {'src': True})
    if iframe:
        return iframe.get('src', '')
    
    # 2. Video player div içinde
    for class_name in ['video-player-area', 'responsive-player', 'player']:
        player_div = film_soup.find('div', class_=class_name)
        if player_div:
            iframe = player_div.find('iframe', {'src': True})
            if iframe:
                return iframe.get('src', '')
    
    return ""

# ============================================================================
# SCRAPING FONKSİYONLAR
# ============================================================================
def process_film(film_info, filmler_data, driver):
    """Tek filmi işle ve JSON'a ekle"""
    if not film_info:
        return None
    
    film_adi = film_info['film_adi']
    film_link = film_info['film_link']
    poster_url = film_info['poster_url']
    
    # JSON key'i oluştur
    film_id = slugify(film_adi)
    if not film_id:
        film_id = f"film_{hash(film_adi) % 1000000}"
    
    # Zaten ekli mi?
    with data_lock:
        if film_id in filmler_data:
            return film_id
    
    print(f"🎬 İşleniyor: {film_adi}")
    
    iframe_url = ""
    
    # Film sayfasına git ve iframe'i al
    if film_link:
        try:
            full_url = urljoin(BASE_URL, film_link)
            
            driver.get(full_url)
            time.sleep(3)  # Sayfa yüklenmesi için bekle
            
            film_soup = BeautifulSoup(driver.page_source, "html.parser")
            iframe_url = extract_iframe_url(film_soup)
            
            if iframe_url:
                # URL'yi normalize et
                if not iframe_url.startswith(('http://', 'https://')):
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    else:
                        iframe_url = urljoin(BASE_URL, iframe_url)
                print(f"   ✅ Iframe bulundu")
            else:
                print(f"   ❌ Iframe bulunamadı")
            
            time.sleep(DELAY_BETWEEN_FILMS)
            
        except Exception as e:
            print(f"   ⚠️ Hata: {e}")
    
    # JSON'a ekle (HDFilmCehennemi formatında)
    with data_lock:
        filmler_data[film_id] = {
            "isim": film_adi,
            "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
            "link": iframe_url,
            "kaynak": "DiziPal"
        }
    
    return film_id

def scrape_category_page(category_name, category_url, page_num, filmler_data, driver):
    """Bir kategori sayfasındaki tüm filmleri çek"""
    page_url = f"{category_url}{page_num}/"
    
    try:
        print(f"\n📂 Kategori: {category_name.upper()}, Sayfa: {page_num}")
        
        driver.get(page_url)
        time.sleep(5)  # Cloudflare için bekle
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Filmleri bul
        film_divs = soup.select("div.grid div.post-item")
        if not film_divs:
            film_divs = soup.find_all('div', class_=re.compile(r'post-item|film-item'))
        
        if not film_divs:
            print("   ⚠️ Film bulunamadı")
            return 0
        
        print(f"   ✅ {len(film_divs)} film bulundu")
        
        processed_count = 0
        
        # Her filmi işle
        for div in film_divs:
            film_info = extract_film_data(div)
            if film_info:
                result = process_film(film_info, filmler_data, driver)
                if result:
                    processed_count += 1
        
        print(f"   📊 {processed_count} film işlendi")
        return processed_count
        
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        return 0

# ============================================================================
# ANA FONKSİYON
# ============================================================================
def main():
    print("=" * 60)
    print("🚀 DİZİPAL FİLM BOTU - CLOUDFLARE BYPASS")
    print("=" * 60)
    print(f"📊 Kategori Sayısı: {len(CATEGORIES)}")
    print(f"📄 Sayfa Başına: {PAGES_TO_SCRAPE} sayfa")
    print(f"⏱️  Film Arası Bekleme: {DELAY_BETWEEN_FILMS} sn")
    print("=" * 60)
    
    # Mevcut JSON'u yükle (eğer varsa)
    filmler_data = {}
    if os.path.exists(JSON_FILENAME):
        try:
            with open(JSON_FILENAME, "r", encoding="utf-8") as f:
                filmler_data = json.load(f)
            print(f"📁 Mevcut JSON yüklendi: {len(filmler_data)} film")
        except:
            print("📁 Yeni JSON oluşturulacak")
    
    film_counter = [len(filmler_data)]  # Başlangıç sayacı
    start_time = time.time()
    
    # Chrome driver başlat
    driver = init_driver()
    
    try:
        # Cloudflare testi
        print("\n🧪 Cloudflare test ediliyor...")
        test_url = f"{BASE_URL}/kategori/aksiyon/page/1/"
        driver.get(test_url)
        time.sleep(10)  # Cloudflare challenge için bekle
        
        if 'cloudflare' in driver.page_source.lower():
            print("⚠️ Cloudflare tespit edildi, ekstra bekleme...")
            time.sleep(15)
        
        print("✅ Cloudflare aşıldı!")
        
        # Her kategori için sayfaları tara
        print(f"\n📡 Filmler çekiliyor...")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for cat_name, cat_url in CATEGORIES.items():
                for sayfa in range(1, PAGES_TO_SCRAPE + 1):
                    future = executor.submit(
                        scrape_category_page, 
                        cat_name, cat_url, sayfa, 
                        filmler_data, driver
                    )
                    futures.append((future, cat_name, sayfa))
                    time.sleep(2)  # Rate limiting
            
            # Sonuçları bekle
            for future, cat_name, sayfa in futures:
                try:
                    count = future.result(timeout=60)
                    if count:
                        with data_lock:
                            film_counter[0] += count
                except Exception as e:
                    print(f"❌ {cat_name} sayfa {sayfa} hatası: {e}")
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("✅ İŞLEM TAMAMLANDI!")
        print(f"⏱️  Toplam Süre: {elapsed_time:.2f} saniye")
        print(f"🎬 Toplam Film: {len(filmler_data)}")
        
        if filmler_data:
            # 1. JSON dosyasını oluştur/güncelle
            with open(JSON_FILENAME, "w", encoding="utf-8") as f:
                json.dump(filmler_data, f, ensure_ascii=False, indent=2)
            
            json_size = os.path.getsize(JSON_FILENAME) / 1024
            print(f"📁 JSON kaydedildi: {JSON_FILENAME} ({json_size:.2f} KB)")
            
            # 2. HTML dosyasını oluştur (HDFilmCehennemi formatında)
            create_html_file(filmler_data)
        else:
            print("❌ Hiç film bulunamadı!")
        
    except KeyboardInterrupt:
        print("\n⚠️ İşlem kullanıcı tarafından durduruldu")
        if filmler_data:
            save_files(filmler_data)
    except Exception as e:
        print(f"\n💥 Ana hata: {e}")
        import traceback
        traceback.print_exc()
        if filmler_data:
            save_files(filmler_data)
    finally:
        if driver:
            driver.quit()

def save_files(data):
    """JSON ve HTML dosyalarını kaydet"""
    # JSON kaydet
    with open(JSON_FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # HTML oluştur
    create_html_file(data)

def create_html_file(film_data):
    """HDFilmCehennemi formatında HTML oluştur"""
    # İlk 99 filmi al
    first_99_keys = list(film_data.keys())[:99]
    first_99_data = {k: film_data[k] for k in first_99_keys}
    
    embedded_json_str = json.dumps(first_99_data, ensure_ascii=False)
    
    # HDFilmCehennemi'nin tam HTML şablonu (sadece URL'ler değişti)
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV FİLM VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) {{
            -moz-user-select: -moz-none;
            -khtml-user-select: none;
            -webkit-user-select: none;
            -o-user-select: none;
            -ms-user-select: none;
            user-select: none
        }}
        body {{
            margin: 0;
            padding: 0;
            background: #00040d;
            font-family: sans-serif;
            font-size: 15px;
            -webkit-tap-highlight-color: transparent;
            font-style: italic;
            line-height: 20px;
            -webkit-text-size-adjust: 100%;
            text-decoration: none;
            -webkit-text-decoration: none;
            overflow-x: hidden;
        }}
        .filmpaneldis {{
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
            min-height: 500px;
        }}
        .baslik {{
            width: 96%;
            color: #fff;
            padding: 15px 10px;
            box-sizing: border-box;
            border-bottom: 2px solid #572aa7;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .filmpanel {{
            width: 12%;
            height: 200px;
            background: #15161a;
            float: left;
            margin: 1.14%;
            color: #fff;
            border-radius: 15px;
            box-sizing: border-box;
            box-shadow: 1px 5px 10px rgba(0,0,0,0.1);
            border: 1px solid #323442;
            padding: 0px;
            overflow: hidden;
            transition: border 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
            position: relative;
        }}
        .filmisimpanel {{
            width: 100%;
            height: 200px;
            position: relative;
            margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%);
            pointer-events: none;
        }}
        .filmpanel:hover {{
            color: #fff;
            border: 3px solid #572aa7;
            box-shadow: 0 0 10px rgba(87, 42, 167, 0.5);
        }}
        .filmresim {{
            width: 100%;
            height: 100%;
            margin-bottom: 0px;
            overflow: hidden;
            position: relative;
        }}
        .filmresim img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        .filmpanel:hover .filmresim img {{
            transform: scale(1.1);
        }}
        .filmisim {{
            width: 100%;
            font-size: 14px;
            text-decoration: none;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 0px 5px;
            box-sizing: border-box;
            color: #fff;
            position: absolute;
            bottom: 5px;
            text-align: center;
        }}
        .aramapanel {{
            width: 100%;
            height: 60px;
            background: #15161a;
            border-bottom: 1px solid #323442;
            margin: 0px auto;
            padding: 10px;
            box-sizing: border-box;
            overflow: hidden;
            z-index: 11111;
            position: sticky;
            top: 0;
        }}
        .aramapanelsag {{
            width: auto;
            height: 40px;
            box-sizing: border-box;
            overflow: hidden;
            float: right;
        }}
        .aramapanelsol {{
            width: 50%;
            height: 40px;
            box-sizing: border-box;
            overflow: hidden;
            float: left;
        }}
        .aramapanelyazi {{
            height: 40px;
            width: 180px;
            border: 1px solid #323442;
            background: #000;
            box-sizing: border-box;
            padding: 0px 10px;
            color: #fff;
            margin: 0px 5px;
            border-radius: 5px;
        }}
        .aramapanelbuton {{
            height: 40px;
            width: 40px;
            text-align: center;
            background-color: #572aa7;
            border: none;
            color: #fff;
            box-sizing: border-box;
            overflow: hidden;
            float: right;
            transition: .35s;
            border-radius: 5px;
            cursor: pointer;
        }}
        .aramapanelbuton:hover {{
            background-color: #fff;
            color: #000;
        }}
        .logo {{
            width: 40px;
            height: 40px;
            float: left;
        }}
        .logo img {{
            width: 100%;
            border-radius: 50%;
        }}
        .logoisim {{
            font-size: 15px;
            width: auto;
            height: 40px;
            line-height: 40px;
            font-weight: 500;
            color: #fff;
            margin-left: 10px;
            float: left;
        }}
        .hataekran i {{
            color: #572aa7;
            font-size: 80px;
            text-align: center;
            width: 100%;
        }}
        .hataekran {{
            width: 80%;
            margin: 20px auto;
            color: #fff;
            background: #15161a;
            border: 1px solid #323442;
            padding: 20px;
            box-sizing: border-box;
            border-radius: 10px;
            text-align: center;
        }}
        .hatayazi {{
            color: #fff;
            font-size: 15px;
            text-align: center;
            width: 100%;
            margin: 20px 0px;
        }}
        .status-bar {{
            color: #888;
            font-size: 12px;
            padding: 5px 10px;
            text-align: right;
        }}
        @media(max-width:550px) {{
            .filmpanel {{
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }}
            .aramapanelyazi {{
                width: 120px;
            }}
            .logoisim {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV - DiziPal</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return false;">
                <input type="text" id="filmSearch" placeholder="Film Ara..." class="aramapanelyazi" onkeyup="searchFilms(this.value)">
                <button type="button" class="aramapanelbuton" onclick="searchFilms(document.getElementById('filmSearch').value)">
                    <i class="fas fa-search"></i>
                </button>
            </form>
        </div>
    </div>

    <div class="status-bar" id="dbStatus">DiziPal Film Arşivi Yükleniyor...</div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik" id="baslikText">DİZİPAL FİLM ARŞİVİ</div>
        <div id="gridContainer"></div>
    </div>

    <script>
        var localDB = {embedded_json_str};
        const REMOTE_JSON_URL = "{GITHUB_JSON_URL}";
        var masterDB = {{ ...localDB }};
        var isFullDBLoaded = false;
        var totalRemoteCount = 0;

        window.onload = function() {{
            renderFilms(localDB);
            document.getElementById('baslikText').innerText = "VİTRİN (İlk " + Object.keys(localDB).length + " Film)";
            fetchFullDatabase();
        }};

        async function fetchFullDatabase() {{
            try {{
                document.getElementById('dbStatus').innerText = "Tüm DiziPal arşivi indiriliyor...";
                const response = await fetch(REMOTE_JSON_URL);
                if (!response.ok) throw new Error("Bağlantı hatası");
                const fullData = await response.json();
                masterDB = {{ ...masterDB, ...fullData }};
                isFullDBLoaded = true;
                totalRemoteCount = Object.keys(masterDB).length;
                document.getElementById('dbStatus').innerText = "Arşiv Güncel: " + totalRemoteCount + " Film";
                document.getElementById('baslikText').innerText = "FİLM ARŞİVİ (" + totalRemoteCount + " Film)";
            }} catch (error) {{
                console.error("❌ JSON çekilemedi:", error);
                document.getElementById('dbStatus').innerText = "Sadece Vitrin Modu (Bağlantı Hatası)";
            }}
        }}

        function renderFilms(dataObj, isSearch = false) {{
            var container = document.getElementById("gridContainer");
            container.innerHTML = "";
            var keys = Object.keys(dataObj);
            var limit = isSearch ? 1000 : 99;
            var count = 0;

            if (keys.length === 0) {{
                container.innerHTML = `<div class="hataekran"><i class="fas fa-search"></i><div class="hatayazi">Film bulunamadı!</div></div>`;
                return;
            }}

            for (var i = 0; i < keys.length; i++) {{
                if (count >= limit) break;
                var key = keys[i];
                var film = dataObj[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = (function(link) {{
                    return function() {{
                        if (link) window.open(link, '_blank');
                        else alert("Link bulunamadı");
                    }}
                }})(film.link);
                item.innerHTML = `
                    <div class="filmresim">
                        <img src="${{film.resim}}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'">
                    </div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${{film.isim}}</div>
                    </div>
                `;
                container.appendChild(item);
                count++;
            }}
        }}

        function searchFilms(query) {{
            query = query.toLowerCase().trim();
            var baslik = document.getElementById("baslikText");
            if (!query) {{
                renderFilms(localDB);
                baslik.innerText = isFullDBLoaded ? "FİLM ARŞİVİ (" + totalRemoteCount + " Film)" : "VİTRİN";
                return;
            }}
            var results = {{}};
            var resultCount = 0;
            for (var key in masterDB) {{
                var filmName = masterDB[key].isim.toLowerCase();
                if (filmName.includes(query)) {{
                    results[key] = masterDB[key];
                    resultCount++;
                }}
            }}
            baslik.innerText = `Arama Sonuçları: ${{resultCount}} Film`;
            renderFilms(results, true);
        }}
    </script>
</body>
</html>'''
    
    with open(HTML_FILENAME, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    html_size = os.path.getsize(HTML_FILENAME) / 1024
    print(f"📁 HTML oluşturuldu: {HTML_FILENAME} ({html_size:.2f} KB)")
    print(f"🎬 Gömülü Film: {len(first_99_data)} | Toplam: {len(film_data)}")

# ============================================================================
# GITHUB ACTIONS İÇİN GEREKLİ KONTROLLER
# ============================================================================
if __name__ == "__main__":
    # Kütüphane kontrolü
    try:
        import undetected_chromedriver as uc
    except ImportError:
        print("❌ undetected_chromedriver kurulu değil!")
        print("📦 Kurulum: pip install undetected-chromedriver")
        sys.exit(1)
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ beautifulsoup4 kurulu değil!")
        print("📦 Kurulum: pip install beautifulsoup4")
        sys.exit(1)
    
    # Ana programı çalıştır
    main()
