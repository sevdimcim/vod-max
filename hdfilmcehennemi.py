import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Komut satırı argümanları
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 790
TURBO_MODE = True if len(sys.argv) > 2 and sys.argv[2].lower() == 'turbo' else False
WORKERS = 100 if TURBO_MODE else 50  # Turbo modda 100 thread!
PAGE_WORKERS = 50 if TURBO_MODE else 20  # Sayfa işleme için

BASE_URL = "https://www.hdfilmcehennemi.nl"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

TIMEOUT = 5 if TURBO_MODE else 10
MAX_RETRIES = 1 if TURBO_MODE else 2

# Connection pooling için session
def create_session():
    session = requests.Session()
    try:
        # Yeni urllib3 versiyonu
        retry_strategy = Retry(
            total=1,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
    except TypeError:
        # Eski urllib3 versiyonu
        retry_strategy = Retry(
            total=1,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=200, pool_maxsize=200)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS_PAGE)
    return session

def get_json_response_turbo(url, session, retry_count=0):
    """Ultra hızlı JSON getter"""
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except:
        if retry_count < MAX_RETRIES:
            return get_json_response_turbo(url, session, retry_count + 1)
        return None

def get_soup_turbo(url, session, retry_count=0):
    """Ultra hızlı soup getter"""
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except:
        if retry_count < MAX_RETRIES:
            return get_soup_turbo(url, session, retry_count + 1)
        return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def process_film(a_etiketi, session):
    """Bir filmi işler (thread için) - ULTRA HIZLI"""
    try:
        film_link = a_etiketi.get('href')
        film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
        
        if not film_adi:
            return None
        
        film_id = slugify(film_adi)
        
        # POSTER
        poster_img = a_etiketi.find('img')
        poster_url = ""
        
        if poster_img:
            poster_url = poster_img.get('data-src', '')
            if not poster_url:
                poster_url = poster_img.get('src', '')
            
            if poster_url and "?" in poster_url:
                poster_url = poster_url.split("?")[0]
        
        # VIDEO LINK
        video_url = ""
        if film_link:
            try:
                target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
                film_soup = get_soup_turbo(target_url, session)
                
                if film_soup:
                    iframe = film_soup.find('iframe', {'class': 'close'})
                    
                    if iframe and iframe.get('data-src'):
                        raw_iframe_url = iframe.get('data-src')
                        
                        if "rapidrame_id=" in raw_iframe_url:
                            rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                            video_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                        else:
                            video_url = raw_iframe_url
            except:
                pass
        
        return {
            'id': film_id,
            'data': {
                "isim": film_adi,
                "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
                "link": video_url
            }
        }
    except:
        return None

def process_page(page_num, session):
    """Bir sayfayı işler - PARALEL FİLM İŞLEME"""
    try:
        api_page_url = f"{BASE_URL}/load/page/{page_num}/categories/film-izle-2/"
        data = get_json_response_turbo(api_page_url, session)
        
        if not data:
            return []
        
        html_chunk = data.get('html', '')
        soup = BeautifulSoup(html_chunk, 'html.parser')
        film_kutulari = soup.find_all('a', class_='poster')
        
        if not film_kutulari:
            return []
        
        # Sayfadaki filmleri paralel işle
        page_films = []
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = [executor.submit(process_film, film, session) for film in film_kutulari]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    page_films.append(result)
        
        print(f"✓ Sayfa {page_num}: {len(page_films)} film")
        return page_films
        
    except Exception as e:
        return []

def main():
    print("="*70)
    print("🚀 HDFİLMCEHENNEMİ TURBO SCRAPER - 100X HIZLI!")
    print(f"📊 Çekilecek Sayfa: {PAGES_TO_SCRAPE}")
    print(f"⚡ Turbo Mod: {'AKTİF 🔥' if TURBO_MODE else 'Kapalı'}")
    print(f"👷 Film Worker: {WORKERS} | Sayfa Worker: {PAGE_WORKERS}")
    print(f"⏱️  Timeout: {TIMEOUT}s | Retry: {MAX_RETRIES}x")
    print("="*70)
    
    filmler_data = {}
    total_films = 0
    start_time = time.time()
    
    # Session oluştur (connection pooling)
    session = create_session()
    
    try:
        # TÜM SAYFALARI PARALEL İŞLE
        with ThreadPoolExecutor(max_workers=PAGE_WORKERS) as page_executor:
            page_futures = {
                page_executor.submit(process_page, page_num, session): page_num 
                for page_num in range(1, PAGES_TO_SCRAPE + 1)
            }
            
            completed_pages = 0
            for future in as_completed(page_futures):
                page_num = page_futures[future]
                try:
                    page_results = future.result()
                    
                    for film in page_results:
                        if film['id'] not in filmler_data:
                            filmler_data[film['id']] = film['data']
                            total_films += 1
                    
                    completed_pages += 1
                    
                    # İlerleme (her 20 sayfada bir)
                    if completed_pages % 20 == 0:
                        elapsed = time.time() - start_time
                        pages_per_second = completed_pages / elapsed if elapsed > 0 else 0
                        remaining_pages = PAGES_TO_SCRAPE - completed_pages
                        estimated_time = remaining_pages / pages_per_second if pages_per_second > 0 else 0
                        
                        print(f"\n📈 İLERLEME: {completed_pages}/{PAGES_TO_SCRAPE} sayfa")
                        print(f"🎬 Toplam Film: {total_films}")
                        print(f"⏱️  Geçen Süre: {elapsed:.1f}s")
                        print(f"🚀 Hız: {pages_per_second:.1f} sayfa/s")
                        print(f"⏳ Tahmini Kalan: {estimated_time:.0f}s")
                        
                except Exception as e:
                    print(f"❌ Sayfa {page_num} hatası: {e}")
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*70)
        print(f"✅ IŞLEM TAMAMLANDI!")
        print(f"📊 Toplam Sayfa: {PAGES_TO_SCRAPE}")
        print(f"🎬 Toplam Film: {len(filmler_data)}")
        print(f"⏱️  Toplam Süre: {elapsed_time:.1f} saniye")
        print(f"🚀 Ortalama Hız: {PAGES_TO_SCRAPE/elapsed_time:.2f} sayfa/s")
        print(f"💾 Film Hızı: {len(filmler_data)/elapsed_time:.0f} film/s")
        print("="*70)
        
    except Exception as e:
        print(f"💥 Ana hata: {e}")
    finally:
        session.close()
    
    create_files(filmler_data)

def create_files(data):
    # JSON - TÜM FİLMLER
    json_filename = "hdfilmcehennemi.json"
    
    optimized_data = {}
    for film_id, film_info in data.items():
        optimized_data[film_id] = {
            "isim": film_info["isim"][:100],
            "resim": film_info["resim"] if film_info["resim"] else "",
            "link": film_info["link"] if film_info["link"] else ""
        }
    
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(optimized_data, f, ensure_ascii=False, separators=(',', ':'))
    
    file_size = os.path.getsize(json_filename) / 1024 / 1024
    print(f"✅ JSON dosyası oluşturuldu!")
    print(f"📁 Boyutu: {file_size:.2f} MB")
    print(f"🎬 Film Sayısı: {len(optimized_data)}")
    print(f"🔗 https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json")
    
    create_html_file(data)

def create_html_file(data):
    # İlk 99 filmi al
    films_list = list(data.items())[:99]
    first_99_films = {}
    
    for film_id, film_info in films_list:
        first_99_films[film_id] = {
            "isim": film_info["isim"][:100],
            "resim": film_info["resim"] if film_info["resim"] else "",
            "link": film_info["link"] if film_info["link"] else ""
        }
    
    json_str = json.dumps(first_99_films, ensure_ascii=False, separators=(',', ':'))
    
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
        }}
        .baslik {{
            width: 96%;
            color: #fff;
            padding: 15px 10px;
            box-sizing: border-box;
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
        }}
        .filmisimpanel {{
            width: 100%;
            height: 200px;
            position: relative;
            margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%);
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
            width: 120px;
            border: 1px solid #ccc;
            box-sizing: border-box;
            padding: 0px 10px;
            color: #000;
            margin: 0px 5px;
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
        }}
        .logoisim {{
            font-size: 15px;
            width: 70%;
            height: 40px;
            line-height: 40px;
            font-weight: 500;
            color: #fff;
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
            padding: 10px;
            box-sizing: border-box;
            border-radius: 10px;
        }}
        .hatayazi {{
            color: #fff;
            font-size: 15px;
            text-align: center;
            width: 100%;
            margin: 20px 0px;
        }}
        .loading {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #00040d;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            color: white;
            font-size: 20px;
            flex-direction: column;
        }}
        .spinner {{
            width: 50px;
            height: 50px;
            border: 5px solid #572aa7;
            border-top: 5px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        @media(max-width:550px) {{
            .filmpanel {{
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div id="loadingText">Filmler yükleniyor...</div>
    </div>
    
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchFilms()">
                <input type="text" id="filmSearch" placeholder="Film Ara..!" class="aramapanelyazi" oninput="liveSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik">HDFİLMCEHENNEMİ FİLM ARŞİVİ</div>
    </div>

    <script>
        // İlk 99 filmi (HTML'ye gömülü - hızlı yükleme)
        let filmler = {json_str};
        
        // JSON URL'si (kalan filmler)
        const JSON_URL = 'https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json';
        
        // Tüm filmler
        let tümFilmler = {{}};
        
        window.onload = function() {{
            console.log(`🎬 İlk 99 film yüklendi`);
            Object.assign(tümFilmler, filmler);
            renderFilms();
            loadExtraFilmsFromJSON();
            
            setTimeout(() => {{
                document.getElementById('loading').style.display = 'none';
            }}, 500);
        }};
        
        // JSON'dan kalan filmleri yükle
        function loadExtraFilmsFromJSON() {{
            fetch(JSON_URL)
                .then(response => response.json())
                .then(data => {{
                    console.log(`📥 JSON'dan ${{Object.keys(data).length}} film yükleniyor...`);
                    
                    let count = 0;
                    Object.keys(data).forEach(key => {{
                        if (!tümFilmler[key]) {{
                            tümFilmler[key] = data[key];
                            count++;
                        }}
                    }});
                    
                    console.log(`✅ ${{count}} yeni film eklendi`);
                    console.log(`🎬 Toplam Film: ${{Object.keys(tümFilmler).length}}`);
                    
                    updateBaslik();
                }})
                .catch(err => {{
                    console.error('JSON yükleme hatası:', err);
                }});
        }}
        
        // Filmleri ekrana bas
        function renderFilms() {{
            var container = document.getElementById("filmListesiContainer");
            
            Object.keys(filmler).forEach(function(key) {{
                var film = filmler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.setAttribute('data-film-name', film.isim.toLowerCase());
                
                item.onclick = function() {{ 
                    if (film.link) {{
                        window.open(film.link, '_blank');
                    }} else {{
                        alert("Bu film için video linki bulunamadı.");
                    }}
                }};
                
                item.innerHTML = `
                    <div class="filmresim"><img src="${{film.resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${{film.isim}}</div>
                    </div>
                `;
                container.appendChild(item);
            }});
            
            var baslik = document.querySelector('.baslik');
            baslik.textContent = `HDFİLMCEHENNEMİ FİLM ARŞİVİ (99 Film + JSON)`;
            
            console.log(`✅ ${{Object.keys(filmler).length}} film render edildi`);
        }}
        
        // Başlığı güncelle
        function updateBaslik() {{
            var baslik = document.querySelector('.baslik');
            baslik.textContent = `HDFİLMCEHENNEMİ FİLM ARŞİVİ (${{Object.keys(tümFilmler).length}} Film)`;
        }}
        
        // CANLI ARAMA (tüm filmler içinde)
        function liveSearch() {{
            var searchTerm = document.getElementById('filmSearch').value.toLowerCase().trim();
            var container = document.getElementById('filmListesiContainer');
            
            if (searchTerm.length === 0) {{
                resetFilmSearch();
                return;
            }}
            
            // DOM'da var olanları gizle/göster
            var panels = container.querySelectorAll('.filmpanel:not(.baslik)');
            var found = false;
            
            panels.forEach(function(panel) {{
                var filmName = panel.getAttribute('data-film-name');
                if (filmName.includes(searchTerm)) {{
                    panel.style.display = 'block';
                    found = true;
                }} else {{
                    panel.style.display = 'none';
                }}
            }});
            
            // JSON'daki filmlerde ara
            Object.keys(tümFilmler).forEach(key => {{
                if (!document.querySelector(`[data-film-id="${{key}}"]`)) {{
                    var film = tümFilmler[key];
                    var filmName = (film.isim || '').toLowerCase();
                    if (filmName.includes(searchTerm)) {{
                        found = true;
                        createAndAddFilmPanel(key, film);
                    }}
                }}
            }});
            
            // Sonuç bulunamadı mesajı
            if (!found && searchTerm) {{
                var existingError = container.querySelector('.hataekran');
                if (existingError) existingError.remove();
                
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">"${{searchTerm}}" için film bulunamadı!</div>';
                container.appendChild(noResults);
            }} else if (found && searchTerm) {{
                var existingError = container.querySelector('.hataekran');
                if (existingError) existingError.remove();
            }}
        }}
        
        // Film paneli oluştur ve ekle
        function createAndAddFilmPanel(key, film) {{
            var container = document.getElementById("filmListesiContainer");
            
            if (document.querySelector(`[data-film-id="${{key}}"]`)) {{
                return;
            }}
            
            var item = document.createElement("div");
            item.className = "filmpanel";
            item.setAttribute('data-film-id', key);
            item.setAttribute('data-film-name', (film.isim || '').toLowerCase());
            
            item.onclick = function() {{ 
                if (film.link) {{
                    window.open(film.link, '_blank');
                }} else {{
                    alert("Bu film için video linki bulunamadı.");
                }}
            }};
            
            item.innerHTML = `
                <div class="filmresim"><img src="${{film.resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'"></div>
                <div class="filmisimpanel">
                    <div class="filmisim">${{film.isim}}</div>
                </div>
            `;
            container.appendChild(item);
        }}
        
        // Arama sıfırla
        function resetFilmSearch() {{
            var container = document.getElementById('filmListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            
            panels.forEach(function(panel) {{
                if (panel.getAttribute('data-film-id')) {{
                    panel.remove();
                }} else {{
                    panel.style.display = 'block';
                }}
            }});
            
            var noResults = container.querySelector('.hataekran');
            if (noResults) {{
                noResults.remove();
            }}
        }}
    </script>
</body>
</html>'''
    
    html_filename = "hdfilmcehennemi.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    html_size = os.path.getsize(html_filename) / 1024 / 1024
    print(f"✅ HTML dosyası oluşturuldu!")
    print(f"📁 Boyutu: {html_size:.2f} MB")
    print(f"🎬 HTML: İlk 99 Film + JSON'dan Dinamik")
    print(f"🔗 https://sevdimcim.github.io/vod-max/hdfilmcehennemi.html")

if __name__ == "__main__":
    main()
