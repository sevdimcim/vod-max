import requests
from bs4 import BeautifulSoup
import time
import json
import re
import concurrent.futures
from threading import Lock
import sqlite3

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmcehennemi.nl"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Thread-safe lock
print_lock = Lock()
DB_FILE = "filmler.db"

def init_database():
    """Veritabanını başlat"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filmler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_adi TEXT NOT NULL,
        poster_url TEXT,
        player_url TEXT NOT NULL,
        sayfa_no INTEGER,
        eklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(film_adi, player_url)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_film_to_db(film_adi, poster_url, player_url, sayfa_no):
    """Filmi veritabanına kaydet"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        clean_film_adi = film_adi.strip()
        
        cursor.execute("SELECT id FROM filmler WHERE film_adi = ? AND player_url = ?", 
                      (clean_film_adi, player_url))
        
        if cursor.fetchone() is None:
            cursor.execute('''
            INSERT INTO filmler (film_adi, poster_url, player_url, sayfa_no)
            VALUES (?, ?, ?, ?)
            ''', (clean_film_adi, poster_url, player_url, sayfa_no))
            
            conn.commit()
            return True
        return False
        
    except Exception as e:
        return False
    finally:
        conn.close()

def get_total_film_count():
    """Toplam film sayısını getir"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM filmler")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_random_films(limit=99):
    """Rastgele filmleri getir"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT film_adi, poster_url, player_url 
    FROM filmler 
    ORDER BY RANDOM() 
    LIMIT ?
    ''', (limit,))
    
    films = cursor.fetchall()
    conn.close()
    
    return [{"film_adi": f[0], "poster_url": f[1], "player_url": f[2]} for f in films]

def get_all_films_for_search():
    """Arama için tüm filmleri getir"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT film_adi, poster_url, player_url FROM filmler")
    
    films = cursor.fetchall()
    conn.close()
    
    return [{"film_adi": f[0], "poster_url": f[1], "player_url": f[2]} for f in films]

def process_film(film_link, film_adi, poster_url, sayfa_no):
    """Tek bir filmi işler"""
    try:
        target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
        
        film_sayfasi = requests.get(target_url, headers=HEADERS_FILM, timeout=5)
        film_soup = BeautifulSoup(film_sayfasi.text, 'html.parser')
        
        iframe = film_soup.find('iframe', {'class': 'close'})
        player_url = ""
        
        if iframe and iframe.get('data-src'):
            raw_iframe_url = iframe.get('data-src')
            
            player_url = raw_iframe_url
            
            if "/rplayer/" in raw_iframe_url:
                player_url = raw_iframe_url
            elif "rapidrame_id=" in raw_iframe_url:
                rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                player_url = f"https://www.hdfilmcehennemi.nl/rplayer/{rapid_id}"
        
        if not player_url:
            with print_lock:
                print(f"❌ ATLANDI: {film_adi[:50]}... (Link yok)")
            return None
        
        saved = save_film_to_db(film_adi, poster_url, player_url, sayfa_no)
        
        with print_lock:
            if saved:
                print(f"✅ {film_adi[:50]}...")
        
        return saved
        
    except Exception as e:
        with print_lock:
            print(f"❌ HATA: {film_adi[:30]}... - {str(e)[:50]}")
        return None

def process_page(sayfa):
    """Tek bir sayfayı işler"""
    try:
        api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
        
        with print_lock:
            print(f"📄 SAYFA {sayfa} ÇEKİLİYOR...")
        
        response = requests.get(api_page_url, headers=HEADERS_PAGE, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            html_chunk = data.get('html', '')
            soup = BeautifulSoup(html_chunk, 'html.parser')
            
            film_kutulari = soup.find_all('a', class_='poster')
            
            if not film_kutulari:
                return 0
            
            film_tasks = []
            
            for a_etiketi in film_kutulari:
                film_link = a_etiketi.get('href')
                film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
                
                poster_img = a_etiketi.find('img')
                poster_url = poster_img.get('data-src') if poster_img else ""
                
                if film_link:
                    film_tasks.append((film_link, film_adi, poster_url))
            
            saved_count = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for film_link, film_adi, poster_url in film_tasks:
                    future = executor.submit(process_film, film_link, film_adi, poster_url, sayfa)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        saved_count += 1
                
            with print_lock:
                print(f"✅ SAYFA {sayfa} TAMAMLANDI - {saved_count} yeni film")
            return saved_count
                
        else:
            with print_lock:
                print(f"⚠️ Sayfa {sayfa} hata: {response.status_code}")
            return 0
                
    except Exception as e:
        with print_lock:
            print(f"💥 Sayfa {sayfa} hatası: {str(e)[:50]}")
        return 0

def main_scraper():
    """Ana scrapper fonksiyonu"""
    print("🚀 BOT BAŞLATILDI!")
    print("⚡ 10 SAYFA ÇEKİLECEK")
    print("💾 Veritabanına kaydedilecek")
    print("🔍 Tüm filmlerde arama yapılabilecek")
    print("⏱️ Tahmini süre: 3-5 dakika\n")
    
    init_database()
    
    total_saved = 0
    TOTAL_PAGES = 10
    
    mevcut_filmler = get_total_film_count()
    print(f"📊 Başlangıç: {mevcut_filmler} film")
    
    completed = 0
    
    for sayfa in range(1, TOTAL_PAGES + 1):
        try:
            saved = process_page(sayfa)
            total_saved += saved
            
            completed += 1
            print(f"📊 İlerleme: {completed}/{TOTAL_PAGES} sayfa - Toplam {get_total_film_count()} film")
            
            if sayfa < TOTAL_PAGES:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Sayfa {sayfa} işlenirken hata: {e}")
    
    print(f"\n🎉 TAMAMLANDI!")
    print(f"📈 {total_saved} yeni film eklendi")
    print(f"💾 Toplam: {get_total_film_count()} film")
    
    create_html_file()

def create_html_file():
    """HTML dosyasını oluştur"""
    random_films = get_random_films(99)
    all_films = get_all_films_for_search()
    total_films = get_total_film_count()
    
    # Tüm filmleri JSON formatında JavaScript'e ekle
    films_json = json.dumps(all_films, ensure_ascii=False)
    
    # JavaScript kodu - TÜM filmlerde arama
    js_code = f'''<script>
// Tüm film verileri
const allFilms = {films_json};

function searchFilms() {{
    const searchTerm = document.getElementById('filmSearch').value.trim().toLowerCase();
    
    if (searchTerm.length < 2) {{
        alert("En az 2 karakter girin!");
        return false;
    }}
    
    // Tüm filmlerde ara
    const filteredFilms = allFilms.filter(film => 
        film.film_adi.toLowerCase().includes(searchTerm)
    );
    
    displaySearchResults(filteredFilms, searchTerm);
    return false;
}}

function displaySearchResults(films, searchTerm) {{
    const container = document.getElementById('filmListesiContainer');
    
    if (films.length === 0) {{
        container.innerHTML = '<div class="baslik">"${{searchTerm}}" için sonuç yok</div><div class="hataekran"><i class="fas fa-search"></i><div class="hatayazi">Film bulunamadı!</div></div>';
        return;
    }}
    
    let html = '<div class="baslik">"${{searchTerm}}" için ${{films.length}} film</div>';
    
    films.forEach(film => {{
        const filmAdiClean = film.film_adi.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        html += '<a href="'+film.player_url+'"><div class="filmpanel"><div class="filmresim"><img src="'+film.poster_url+'" onerror="this.src=\\'https://via.placeholder.com/300x450?text=Resim+Yok\\'"></div><div class="filmisimpanel"><div class="filmisim">'+filmAdiClean+'</div></div></div></a>';
    }});
    
    container.innerHTML = html;
}}

function resetFilmSearch() {{
    const searchTerm = document.getElementById('filmSearch').value.toLowerCase();
    if (searchTerm === "") {{
        // Arama kutusu boşsa rastgele filmleri göster
        location.reload();
    }}
}}

// Enter tuşu ile arama
document.getElementById('filmSearch').addEventListener('keypress', function(e) {{
    if (e.key === 'Enter') {{
        searchFilms();
    }}
}});
</script>'''

    # HTML içeriği - ORJİNAL TASARIM
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<title>TITAN TV VOD</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
<script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
<script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
<style>
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
<div class="aramapanel">
<div class="aramapanelsol">
<div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
<div class="logoisim">TITAN TV ({total_films} Film)</div>
</div>
<div class="aramapanelsag">
<form action="" name="ara" method="GET" onsubmit="return searchFilms()">
    <input type="text" id="filmSearch" placeholder="Film ara..." class="aramapanelyazi" oninput="resetFilmSearch()">
    <input type="submit" value="ARA" class="aramapanelbuton">
</form>
</div>
</div>

<div class="filmpaneldis" id="filmListesiContainer">
    <div class="baslik">HDFİLMCEHENNEMİ VOD</div>
'''

    # Rastgele filmleri ekle
    for film in random_films:
        film_adi_clean = film['film_adi'].replace('"', '&quot;').replace("'", "&#39;")
        
        html_content += f'''
    <a href="{film['player_url']}">
        <div class="filmpanel">
            <div class="filmresim"><img src="{film['poster_url']}" onerror="this.src='https://via.placeholder.com/300x450?text=Resim+Yok'"></div>
            <div class="filmisimpanel">
                <div class="filmisim">{film_adi_clean}</div>
            </div>
        </div>
    </a>
'''

    html_content += '''
</div>
''' + js_code + '''
</body>
</html>'''

    filename = "hdfilmcehennemi.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n✅ HTML dosyası '{filename}' oluşturuldu!")
    print(f"🎬 Toplam {total_films} film")
    print(f"🔍 Arama özelliği aktif - Tüm {total_films} filmde arama yapabilirsiniz")
    print(f"💾 HTML boyutu: {len(html_content) // 1024} KB")

def show_statistics():
    """İstatistikleri göster"""
    total = get_total_film_count()
    print(f"\n📊 İSTATİSTİKLER:")
    print(f"   Toplam Film: {total}")
    print(f"   Veritabanı: {DB_FILE}")
    print(f"   HTML Dosyası: hdfilmcehennemi.html")

if __name__ == "__main__":
    print("=" * 50)
    print("🎬 HDFİLMCEHENNEMİ BOT")
    print("=" * 50)
    
    print("\n⏳ Otomatik başlatılıyor...")
    
    try:
        main_scraper()
    except Exception as e:
        print(f"❌ Hata: {e}")
        print("\n📋 HTML oluşturuluyor...")
        try:
            init_database()
            if get_total_film_count() > 0:
                create_html_file()
            else:
                print("❌ Veritabanında film yok!")
        except Exception as e2:
            print(f"❌ HTML hatası: {e2}")
