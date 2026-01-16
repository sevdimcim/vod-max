import requests
from bs4 import BeautifulSoup
import time
import json
import re
import concurrent.futures
from threading import Lock
import sqlite3
import os
from datetime import datetime

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
    
    # Filmler tablosu
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
    
    # Arama indeksi
    cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS film_search 
    USING fts5(film_adi, content='filmler', content_rowid='id')
    ''')
    
    conn.commit()
    conn.close()
    print("📁 Veritabanı hazır!")

def save_film_to_db(film_adi, poster_url, player_url, sayfa_no):
    """Filmi veritabanına kaydet"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Film adını temizle
        clean_film_adi = film_adi.strip()
        
        # Zaten var mı kontrol et
        cursor.execute("SELECT id FROM filmler WHERE film_adi = ? AND player_url = ?", 
                      (clean_film_adi, player_url))
        
        if cursor.fetchone() is None:
            # Yeni film ekle
            cursor.execute('''
            INSERT INTO filmler (film_adi, poster_url, player_url, sayfa_no)
            VALUES (?, ?, ?, ?)
            ''', (clean_film_adi, poster_url, player_url, sayfa_no))
            
            film_id = cursor.lastrowid
            
            # Arama indeksine ekle
            cursor.execute('''
            INSERT INTO film_search (rowid, film_adi)
            VALUES (?, ?)
            ''', (film_id, clean_film_adi))
            
            conn.commit()
            return True
        return False
        
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Veritabanı hatası: {e}")
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

def search_films_db(query, limit=100):
    """Filmleri veritabanında ara"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT f.film_adi, f.poster_url, f.player_url 
    FROM filmler f
    JOIN film_search fs ON f.id = fs.rowid
    WHERE film_adi MATCH ?
    ORDER BY rank
    LIMIT ?
    ''', (f'*{query}*', limit))
    
    films = cursor.fetchall()
    conn.close()
    
    return [{"film_adi": f[0], "poster_url": f[1], "player_url": f[2]} for f in films]

def process_film(film_link, film_adi, poster_url, sayfa_no):
    """Tek bir filmi işler"""
    try:
        target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
        
        # Film detay sayfasını çek
        film_sayfasi = requests.get(target_url, headers=HEADERS_FILM, timeout=5)
        film_soup = BeautifulSoup(film_sayfasi.text, 'html.parser')
        
        # Iframe bulma
        iframe = film_soup.find('iframe', {'class': 'close'})
        player_url = ""
        
        if iframe and iframe.get('data-src'):
            raw_iframe_url = iframe.get('data-src')
            
            # .nl DOMAIN KULLAN
            player_url = raw_iframe_url
            
            if "/rplayer/" in raw_iframe_url:
                player_url = raw_iframe_url
            elif "rapidrame_id=" in raw_iframe_url:
                rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                player_url = f"https://www.hdfilmcehennemi.nl/rplayer/{rapid_id}"
        
        # EĞER PLAYER_URL YOKSA, ATLA
        if not player_url:
            with print_lock:
                print(f"❌ ATLANDI: {film_adi[:50]}... (Link yok)")
            return None
        
        # Veritabanına kaydet
        saved = save_film_to_db(film_adi, poster_url, player_url, sayfa_no)
        
        with print_lock:
            if saved:
                print(f"✅ {film_adi[:50]}...")
            else:
                print(f"🔁 ZATEN VAR: {film_adi[:50]}...")
        
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
            
            # Thread pool ile paralel işleme
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for film_link, film_adi, poster_url in film_tasks:
                    future = executor.submit(process_film, film_link, film_adi, poster_url, sayfa)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        saved_count += 1
                
            with print_lock:
                print(f"✅ SAYFA {sayfa} TAMAMLANDI - {saved_count} yeni film eklendi")
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
    print("🚀 MEGA BOT BAŞLATILDI!")
    print("⚡ TÜM 790 SAYFA ÇEKİLECEK!")
    print("💾 Veritabanına kaydedilecek")
    print("🎲 Ekranda 99 rastgele film gösterilecek")
    print("🔍 Geri kalanı arama ile bulunacak")
    print("⏱️ Tahmini süre: 3-4 saat\n")
    
    # Veritabanını başlat
    init_database()
    
    total_saved = 0
    TOTAL_PAGES = 790
    
    # Önce mevcut film sayısını kontrol et
    mevcut_filmler = get_total_film_count()
    print(f"📊 Veritabanında {mevcut_filmler} film bulunuyor.")
    
    # Kullanıcıya seçenek sun
    print("\n1. Tüm sayfaları çek (790 sayfa)")
    print("2. Sadece eksik sayfaları çek")
    print("3. Belirli sayfa aralığı çek")
    
    secim = input("\nSeçiminiz (1/2/3): ").strip()
    
    if secim == "1":
        # Tüm sayfalar
        baslangic = 1
        bitis = TOTAL_PAGES
    elif secim == "2":
        # Eksik sayfaları bul
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sayfa_no FROM filmler")
        mevcut_sayfalar = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        tum_sayfalar = set(range(1, TOTAL_PAGES + 1))
        eksik_sayfalar = tum_sayfalar - mevcut_sayfalar
        
        if not eksik_sayfalar:
            print("✅ Tüm sayfalar zaten çekilmiş!")
            return
        
        baslangic = min(eksik_sayfalar)
        bitis = max(eksik_sayfalar)
        print(f"📊 {len(eksik_sayfalar)} eksik sayfa çekilecek: {baslangic}-{bitis}")
    elif secim == "3":
        baslangic = int(input("Başlangıç sayfası: "))
        bitis = int(input("Bitiş sayfası: "))
    else:
        print("❌ Geçersiz seçim!")
        return
    
    # Sayfaları işle
    completed = 0
    toplam_sayfa = bitis - baslangic + 1
    
    for sayfa in range(baslangic, bitis + 1):
        try:
            saved = process_page(sayfa)
            total_saved += saved
            
            completed += 1
            print(f"📊 İlerleme: {completed}/{toplam_sayfa} sayfa - Toplam {get_total_film_count()} film")
            
            # Her 10 sayfada bir istatistik göster
            if completed % 10 == 0:
                print(f"\n📈 İstatistik: {total_saved} yeni film eklendi")
                print(f"💾 Toplam: {get_total_film_count()} film")
            
            # Sayfalar arası bekle
            if sayfa < bitis:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Sayfa {sayfa} işlenirken hata: {e}")
    
    # İstatistikleri göster
    print(f"\n🎉 TAMAMLANDI!")
    print(f"📈 {total_saved} yeni film eklendi")
    print(f"💾 Toplam: {get_total_film_count()} film")
    
    # HTML oluştur
    create_html_file()

def create_html_file():
    """HTML dosyasını oluştur"""
    # Rastgele 99 film al
    random_films = get_random_films(99)
    total_films = get_total_film_count()
    
    # JavaScript kodu (hatasız)
    js_code = '''
<script>
let allFilms = [];

// Tüm filmleri yükle (arama için)
function loadAllFilms() {
    console.log("Tüm filmler yüklenecek...");
}

// AJAX ile film ara
function searchFilms() {
    const searchTerm = document.getElementById('filmSearch').value.trim().toLowerCase();
    
    if (searchTerm.length < 2) {
        alert("Lütfen en az 2 karakter girin!");
        return false;
    }
    
    // Loading göster
    const container = document.getElementById('filmListesiContainer');
    container.innerHTML = '<div class="hataekran"><i class="fas fa-spinner fa-spin"></i><div class="hatayazi">Aranıyor...</div></div>';
    
    // AJAX isteği (gerçek uygulamada backend'den veri çekmeli)
    setTimeout(() => {
        showSearchResults(searchTerm);
    }, 500);
    
    return false;
}

// Arama sonuçlarını göster (demo)
function showSearchResults(searchTerm) {
    const container = document.getElementById('filmListesiContainer');
    
    // Demo filmler (gerçek uygulamada AJAX ile gelmeli)
    const demoFilms = [];
    
    // Tüm filmleri veritabanından çek (demo)
    const storedFilms = localStorage.getItem('all_films');
    if (storedFilms) {
        const films = JSON.parse(storedFilms);
        const filteredFilms = films.filter(film => 
            film.film_adi.toLowerCase().includes(searchTerm)
        );
        
        if (filteredFilms.length === 0) {
            container.innerHTML = '<div class="baslik">Arama Sonuçları: "' + searchTerm + '"</div>' +
                                 '<div class="hataekran">' +
                                 '<i class="fas fa-search"></i>' +
                                 '<div class="hatayazi">Film bulunamadı!</div>' +
                                 '</div>';
            return;
        }
        
        let html = '<div class="baslik">Arama Sonuçları: "' + searchTerm + '" (' + filteredFilms.length + ' film)</div>';
        
        filteredFilms.forEach(film => {
            const filmAdiClean = film.film_adi.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
            html += '<a href="' + film.player_url + '">' +
                    '<div class="filmpanel">' +
                    '<div class="filmresim"><img src="' + film.poster_url + '" onerror="this.src=\'https://via.placeholder.com/300x450?text=Resim+Yok\'"></div>' +
                    '<div class="filmisimpanel">' +
                    '<div class="filmisim">' + filmAdiClean + '</div>' +
                    '</div>' +
                    '</div>' +
                    '</a>';
        });
        
        container.innerHTML = html;
    } else {
        container.innerHTML = '<div class="hataekran">' +
                             '<i class="fas fa-exclamation-triangle"></i>' +
                             '<div class="hatayazi">Film veritabanı yüklenmemiş!</div>' +
                             '</div>';
    }
}

// Arama input'u değiştiğinde
function handleSearchInput() {
    const searchTerm = document.getElementById('filmSearch').value.trim();
    
    if (searchTerm === '') {
        // Arama kutusu boşsa rastgele filmleri göster
        location.reload();
    }
}

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', function() {
    loadAllFilms();
    
    // Tüm filmleri localStorage'a kaydet (demo)
    fetch('/api/films')
        .then(response => response.json())
        .then(films => {
            localStorage.setItem('all_films', JSON.stringify(films));
        })
        .catch(error => {
            console.log('API hatası:', error);
        });
});

// Enter tuşu ile arama
document.getElementById('filmSearch').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchFilms();
    }
});
</script>
'''

    # HTML içeriği
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
        width: 200px;
        border: 1px solid #ccc;
        box-sizing: border-box;
        padding: 0px 10px;
        color: #000;
        margin: 0px 5px;
        font-size: 14px;
    }}
    .aramapanelbuton {{
        height: 40px;
        width: 60px;
        text-align: center;
        background-color: #572aa7;
        border: none;
        color: #fff;
        box-sizing: border-box;
        overflow: hidden;
        float: right;
        transition: .35s;
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
    }}
    .logoisim {{
        font-size: 15px;
        width: 70%;
        height: 40px;
        line-height: 40px;
        font-weight: 500;
        color: #fff;
    }}
    .info-bar {{
        background: #572aa7;
        color: white;
        padding: 10px;
        text-align: center;
        font-size: 14px;
        margin: 10px 0;
        border-radius: 5px;
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
        .aramapanelyazi {{
            width: 150px;
        }}
    }}
</style>
</head>
<body>
<div class="aramapanel">
<div class="aramapanelsol">
<div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
<div class="logoisim">TITAN TV VOD ({total_films} Film)</div>
</div>
<div class="aramapanelsag">
<div class="info-bar">🎲 Ekranda 99 rastgele film gösteriliyor. Arama yaparak tüm {total_films} filmi bulabilirsiniz.</div>
<form action="" name="ara" method="GET" onsubmit="return searchFilms()">
    <input type="text" id="filmSearch" placeholder="Film ara (tüm {total_films} filmde ara)" class="aramapanelyazi" oninput="handleSearchInput()">
    <input type="submit" value="ARA" class="aramapanelbuton">
</form>
</div>
</div>

<div class="filmpaneldis" id="filmListesiContainer">
    <div class="baslik">HDFİLMCEHENNEMİ VOD - Rastgele 99 Film</div>
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

    # JavaScript'i ekle
    html_content += '''
</div>
''' + js_code + '''

<!-- Demo API endpoint için -->
<script>
// Demo API - localStorage kullanıyoruz
window.API = {{
    getFilms: function() {{
        return new Promise((resolve) => {{
            // Gerçek uygulamada burada AJAX ile veritabanından çekilmeli
            const films = JSON.parse(localStorage.getItem('all_films') || '[]');
            resolve(films);
        }});
    }}
}};

// Sayfa yüklendiğinde demo filmleri localStorage'a yükle
window.addEventListener('load', function() {{
    // Demo filmler (ilk 100 film)
    const demoFilms = [
        // Buraya filmler otomatik doldurulacak
    ];
    
    // Eğer localStorage'da film yoksa demo filmleri yükle
    if (!localStorage.getItem('all_films')) {{
        localStorage.setItem('all_films', JSON.stringify(demoFilms));
    }}
}});
</script>

</body>
</html>'''

    filename = "hdfilmcehennemi.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n✅ HTML dosyası '{filename}' oluşturuldu!")
    print(f"🎲 Ekranda 99 rastgele film gösteriliyor")
    print(f"📊 Toplam {total_films} film veritabanında")
    print(f"🔍 Arama ile tüm filmler bulunabilir")
    print(f"💾 HTML boyutu: {len(html_content) // 1024} KB")
    print(f"💿 Veritabanı: {DB_FILE}")
    print(f"\n⚠️ NOT: Tam arama için backend API gerekiyor.")
    print(f"     Şu an localStorage ile demo modunda çalışıyor.")

def show_statistics():
    """İstatistikleri göster"""
    total = get_total_film_count()
    print(f"\n📊 İSTATİSTİKLER:")
    print(f"   Toplam Film: {total}")
    print(f"   Veritabanı: {DB_FILE}")
    print(f"   HTML Dosyası: hdfilmcehennemi.html")
    
    # Sayfa bazlı istatistik
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT sayfa_no) FROM filmler")
    sayfa_sayisi = cursor.fetchone()[0]
    conn.close()
    
    print(f"   Çekilen Sayfa: {sayfa_sayisi}/790")

def create_json_export():
    """JSON export oluştur (arama için)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT film_adi, poster_url, player_url FROM filmler")
    films = cursor.fetchall()
    conn.close()
    
    films_list = [
        {"film_adi": f[0], "poster_url": f[1], "player_url": f[2]}
        for f in films
    ]
    
    with open("filmler.json", "w", encoding="utf-8") as f:
        json.dump(films_list, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON export oluşturuldu: filmler.json")
    print(f"   Toplam {len(films_list)} film export edildi")

if __name__ == "__main__":
    print("=" * 50)
    print("🎬 HDFİLMCEHENNEMİ MEGA BOT")
    print("=" * 50)
    
    print("\n1. Filmleri Çek (Scraper)")
    print("2. HTML Oluştur")
    print("3. JSON Export Oluştur (arama için)")
    print("4. İstatistikleri Göster")
    print("5. Çıkış")
    
    secim = input("\nSeçiminiz (1/2/3/4/5): ").strip()
    
    if secim == "1":
        main_scraper()
    elif secim == "2":
        create_html_file()
    elif secim == "3":
        create_json_export()
    elif secim == "4":
        show_statistics()
    elif secim == "5":
        print("👋 Çıkılıyor...")
    else:
        print("❌ Geçersiz seçim!")
