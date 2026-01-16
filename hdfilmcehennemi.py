import requests
from bs4 import BeautifulSoup
import time
import json
import re
import concurrent.futures
from threading import Lock

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmcehennemi.nl"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Thread-safe lock
print_lock = Lock()

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def process_film(film_link, film_adi, poster_url):
    """Tek bir filmi işler ve veriyi döndürür"""
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
            
            # RPLAYER DÖNÜŞTÜRME
            if "rapidrame_id=" in raw_iframe_url:
                rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                player_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
            else:
                player_url = raw_iframe_url
        
        # EĞER PLAYER_URL YOKSA, BOŞ DÖNDÜR
        if not player_url:
            with print_lock:
                print(f"❌ ATLANDI: {film_adi[:50]}... (Link yok)")
            return None
        
        with print_lock:
            print(f"✅ {film_adi[:50]}...")
        
        return {
            "film_id": slugify(film_adi),
            "resim": poster_url,
            "film_adi": film_adi,
            "player_url": player_url
        }
            
    except Exception as e:
        with print_lock:
            print(f"❌ HATA: {film_adi[:30]}... - {str(e)[:50]}")
        return None

def process_page(sayfa):
    """Tek bir sayfayı işler ve film listesi döndürür"""
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
                return []
            
            film_tasks = []
            
            for a_etiketi in film_kutulari:
                film_link = a_etiketi.get('href')
                film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
                
                poster_img = a_etiketi.find('img')
                poster_url = poster_img.get('data-src') if poster_img else ""
                
                if film_link:
                    film_tasks.append((film_link, film_adi, poster_url))
            
            page_films = []
            
            # Thread pool ile paralel işleme
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for film_link, film_adi, poster_url in film_tasks:
                    future = executor.submit(process_film, film_link, film_adi, poster_url)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        page_films.append(result)
                
            with print_lock:
                print(f"✅ SAYFA {sayfa} TAMAMLANDI - {len(page_films)} film eklendi")
            return page_films
                
        else:
            with print_lock:
                print(f"⚠️ Sayfa {sayfa} hata: {response.status_code}")
            return []
                
    except Exception as e:
        with print_lock:
            print(f"💥 Sayfa {sayfa} hatası: {str(e)[:50]}")
        return []

def main():
    print("🚀 BOT BAŞLATILDI!")
    print("⚡ 5 Sayfa çekilecek...")
    print("🎬 Filmler sayfa içinde açılacak")
    print("⏱️ Tahmini süre: 2-3 dakika\n")
    
    filmler_data = {}
    
    # Sadece 5 sayfa çek
    TOPLAM_SAYFA = 5
    sayfa_listesi = list(range(1, TOPLAM_SAYFA + 1))
    
    # Sayfaları sırayla işle (çok hızlı olmayalım)
    completed = 0
    for sayfa in sayfa_listesi:
        try:
            page_films = process_page(sayfa)
            for film in page_films:
                filmler_data[film["film_id"]] = {
                    "resim": film["resim"],
                    "film_adi": film["film_adi"],
                    "player_url": film["player_url"]
                }
            
            completed += 1
            print(f"📊 İlerleme: {completed}/{TOPLAM_SAYFA} sayfa - Toplam {len(filmler_data)} film")
            
            # Sayfalar arası biraz bekle
            if sayfa < TOPLAM_SAYFA:
                time.sleep(1)
                
        except Exception as e:
            print(f"Sayfa {sayfa} işlenirken hata: {e}")
    
    print(f"\n🎉 TAMAMLANDI! Toplam {len(filmler_data)} film çekildi!")
    
    # HTML oluştur
    create_html_file(filmler_data)

def create_html_file(data):
    # Film adlarını temizle
    cleaned_data = {}
    for film_id, film_info in data.items():
        # HTML için temizle
        cleaned_film_adi = film_info['film_adi'].replace("'", "").replace('"', '')
        cleaned_data[film_id] = {
            "resim": film_info["resim"],
            "film_adi": cleaned_film_adi,
            "player_url": film_info["player_url"]
        }
    
    # HTML içeriği - BASİT VE ETKİLİ
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
<title>TITAN TV VOD</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="referrer" content="no-referrer">
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        background: #000;
        font-family: Arial, sans-serif;
        color: white;
        overflow-x: hidden;
    }
    
    /* HEADER */
    .header {
        background: #15161a;
        padding: 10px 15px;
        border-bottom: 1px solid #333;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    
    .logo {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .logo img {
        width: 40px;
        height: 40px;
        border-radius: 5px;
    }
    
    .logo-text {
        font-size: 18px;
        font-weight: bold;
        color: #fff;
    }
    
    .search-box {
        display: flex;
        gap: 5px;
    }
    
    .search-box input {
        padding: 8px 12px;
        border: 1px solid #572aa7;
        border-radius: 5px;
        background: #222;
        color: white;
        width: 200px;
    }
    
    .search-box button {
        padding: 8px 15px;
        background: #572aa7;
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    
    /* FILM CONTAINER */
    .container {
        padding: 15px;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .section-title {
        font-size: 22px;
        margin: 20px 0 15px 0;
        color: #fff;
        border-left: 4px solid #572aa7;
        padding-left: 10px;
    }
    
    .movies-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 15px;
        margin-bottom: 30px;
    }
    
    /* FILM CARD */
    .movie-card {
        background: #15161a;
        border-radius: 10px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.3s, box-shadow 0.3s;
        border: 1px solid #333;
    }
    
    .movie-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(87, 42, 167, 0.3);
        border-color: #572aa7;
    }
    
    .movie-poster {
        width: 100%;
        height: 200px;
        overflow: hidden;
    }
    
    .movie-poster img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s;
    }
    
    .movie-card:hover .movie-poster img {
        transform: scale(1.05);
    }
    
    .movie-info {
        padding: 10px;
    }
    
    .movie-title {
        font-size: 14px;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-weight: 500;
    }
    
    /* PLAYER OVERLAY */
    .player-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 1000;
        display: none;
    }
    
    .player-container {
        width: 100%;
        height: 100%;
        position: relative;
    }
    
    .player-frame {
        width: 100%;
        height: 100%;
        border: none;
    }
    
    /* KAPATMA - SADECE OVERLAY'E TIKLAYINCA */
    .player-overlay {
        cursor: pointer;
    }
    
    /* RESPONSIVE */
    @media (max-width: 768px) {
        .movies-grid {
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }
        
        .movie-poster {
            height: 160px;
        }
        
        .header {
            flex-direction: column;
            gap: 10px;
            padding: 15px;
        }
        
        .search-box input {
            width: 100%;
        }
        
        .search-box {
            width: 100%;
        }
    }
    
    @media (max-width: 480px) {
        .movies-grid {
            grid-template-columns: repeat(3, 1fr);
        }
        
        .movie-poster {
            height: 140px;
        }
    }
</style>
</head>
<body>
    <!-- HEADER -->
    <div class="header">
        <div class="logo">
            <img src="https://i.hizliresim.com/t75soiq.png" alt="Logo">
            <div class="logo-text">TITAN TV ({TOTAL_FILMS} Film)</div>
        </div>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Film ara...">
            <button onclick="searchMovies()">ARA</button>
        </div>
    </div>

    <!-- PLAYER OVERLAY -->
    <div class="player-overlay" id="playerOverlay" onclick="closePlayer()">
        <div class="player-container">
            <iframe class="player-frame" id="playerFrame" allowfullscreen></iframe>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="container">
        <div class="section-title">HDFİLMCEHENNEMİ VOD</div>
        
        <div class="movies-grid" id="moviesGrid">
'''

    # Toplam film sayısını HTML'e ekle
    total_films = len(cleaned_data)
    html_template = html_template.replace("{TOTAL_FILMS}", str(total_films))
    
    # Film kartlarını ekle
    film_counter = 0
    for film_id, film_info in cleaned_data.items():
        film_counter += 1
        
        # JavaScript için güvenli string
        safe_film_adi = film_info['film_adi'].replace("'", "").replace('"', '')
        
        html_template += f'''
            <!-- Film {film_counter} -->
            <div class="movie-card" onclick="openPlayer('{film_info['player_url']}')">
                <div class="movie-poster">
                    <img src="{film_info['resim']}" alt="{safe_film_adi}" onerror="this.src='https://via.placeholder.com/300x450/15161a/FFFFFF?text=Film'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{film_info['film_adi']}</div>
                </div>
            </div>
'''
        
        if film_counter % 20 == 0:
            print(f"📝 HTML'e {film_counter}/{total_films} film eklendi...")

    html_template += '''
        </div>
    </div>

    <script>
    // PLAYER FONKSİYONLARI
    function openPlayer(url) {
        console.log("Film açılıyor:", url);
        
        // Iframe'i ayarla - REFERRER POLICY EKLE
        const iframe = document.getElementById('playerFrame');
        iframe.src = url;
        
        // Overlay'i göster
        document.getElementById('playerOverlay').style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        // ESC tuşu ile kapatma
        document.addEventListener('keydown', function escClose(e) {
            if (e.key === 'Escape') {
                closePlayer();
                document.removeEventListener('keydown', escClose);
            }
        });
    }
    
    function closePlayer() {
        // Iframe'i temizle
        const iframe = document.getElementById('playerFrame');
        iframe.src = '';
        
        // Overlay'i gizle
        document.getElementById('playerOverlay').style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    // ARAMA FONKSİYONU
    function searchMovies() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const movieCards = document.querySelectorAll('.movie-card');
        let found = false;
        
        movieCards.forEach(card => {
            const title = card.querySelector('.movie-title').textContent.toLowerCase();
            if (title.includes(searchTerm)) {
                card.style.display = 'block';
                found = true;
            } else {
                card.style.display = 'none';
            }
        });
        
        // Arama sonucu yoksa mesaj göster
        const existingMessage = document.querySelector('.no-results');
        if (!found) {
            if (!existingMessage) {
                const message = document.createElement('div');
                message.className = 'no-results';
                message.style.cssText = `
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 40px;
                    color: #888;
                    font-size: 18px;
                `;
                message.textContent = 'Film bulunamadı!';
                document.getElementById('moviesGrid').appendChild(message);
            }
        } else {
            if (existingMessage) {
                existingMessage.remove();
            }
        }
    }
    
    // ENTER TUŞU İLE ARAMA
    document.getElementById('searchInput').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            searchMovies();
        }
        
        // Input temizlenince tüm filmleri göster
        if (this.value === '') {
            const movieCards = document.querySelectorAll('.movie-card');
            movieCards.forEach(card => {
                card.style.display = 'block';
            });
            
            const existingMessage = document.querySelector('.no-results');
            if (existingMessage) {
                existingMessage.remove();
            }
        }
    });
    
    // SAYFA YÜKLENDİĞİNDE
    document.addEventListener('DOMContentLoaded', function() {
        console.log('VOD Sayfası hazır!');
    });
    </script>
</body>
</html>'''
    
    filename = "hdfilmcehennemi.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML dosyası '{filename}' oluşturuldu!")
    print(f"🎬 Toplam {len(cleaned_data)} film eklendi")
    print(f"🎥 Filmler sayfa içinde açılacak (Overlay'e tıkla kapat)")
    print(f"🔍 Arama özelliği aktif")
    print(f"📱 Mobil uyumlu tasarım")
    print(f"💾 Dosya boyutu: {len(html_template) // 1024} KB")

if __name__ == "__main__":
    main()
