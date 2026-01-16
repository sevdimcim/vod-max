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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
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
    print("🚀 ULTRA HIZLI BOT BAŞLATILDI!")
    print("⚡ Paralel çekim aktif (10 sayfa x 15 film thread)")
    print("🎬 Filmler sayfa içinde açılacak (yeni sekme yok)")
    print("⏱️ 790 sayfa için ~1-2 saat\n")
    
    filmler_data = {}
    
    # Kaç sayfa çekilecek (test için azalt, 790 çok uzun sürer)
    TOPLAM_SAYFA = 10  # Test için 10 sayfa, 790 yapmak istersen burayı değiştir
    sayfa_listesi = list(range(1, TOPLAM_SAYFA + 1))
    
    # Tüm sayfaları paralel işle
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as page_executor:
        futures = {page_executor.submit(process_page, sayfa): sayfa for sayfa in sayfa_listesi}
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            sayfa = futures[future]
            try:
                page_films = future.result()
                for film in page_films:
                    filmler_data[film["film_id"]] = {
                        "resim": film["resim"],
                        "film_adi": film["film_adi"],
                        "player_url": film["player_url"]
                    }
            except Exception as e:
                print(f"Sayfa {sayfa} işlenirken hata: {e}")
            
            completed += 1
            print(f"📊 İlerleme: {completed}/{TOPLAM_SAYFA} sayfa - Toplam {len(filmler_data)} film")
    
    print(f"\n🎉 TAMAMLANDI! Toplam {len(filmler_data)} film çekildi!")
    
    # HTML oluştur
    create_html_file(filmler_data)

def create_html_file(data):
    # Önce tüm film adlarını temizle (tek tırnak için)
    cleaned_data = {}
    for film_id, film_info in data.items():
        # Tek tırnakları escape et
        cleaned_film_adi = film_info['film_adi'].replace("'", "&#39;")
        cleaned_data[film_id] = {
            "resim": film_info["resim"],
            "film_adi": cleaned_film_adi,
            "player_url": film_info["player_url"]
        }
    
    # HTML içeriği - SAYFA İÇİNDE AÇILACAK ŞEKİLDE
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
<title>TITAN TV VOD</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
<script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
<script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
<style>
    body {
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
    }
    .filmpaneldis {
        background: #15161a;
        width: 100%;
        margin: 20px auto;
        overflow: hidden;
        padding: 10px 5px;
        box-sizing: border-box;
    }
    .baslik {
        width: 96%;
        color: #fff;
        padding: 15px 10px;
        box-sizing: border-box;
    }
    .filmpanel {
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
    }
    .filmisimpanel {
        width: 100%;
        height: 200px;
        position: relative;
        margin-top: -200px;
        background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%);
    }
    .filmpanel:hover {
        color: #fff;
        border: 3px solid #572aa7;
        box-shadow: 0 0 10px rgba(87, 42, 167, 0.5);
    }
    .filmpanel:focus {
        outline: none;
        border: 3px solid #572aa7;
        box-shadow: 0 0 10px rgba(87, 42, 167, 0.5);
    }
    .filmresim {
        width: 100%;
        height: 100%;
        margin-bottom: 0px;
        overflow: hidden;
        position: relative;
    }
    .filmresim img {
        width: 100%;
        height: 100%;
        transition: transform 0.4s ease;
    }
    .filmpanel:hover .filmresim img {
        transform: scale(1.1);
    }
    .filmisim {
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
    }
    .aramapanel {
        width: 100%;
        height: 60px;
        background: #15161a;
        border-bottom: 1px solid #323442;
        margin: 0px auto;
        padding: 10px;
        box-sizing: border-box;
        overflow: hidden;
        z-index: 11111;
    }
    .aramapanelsag {
        width: auto;
        height: 40px;
        box-sizing: border-box;
        overflow: hidden;
        float: right;
    }
    .aramapanelsol {
        width: 50%;
        height: 40px;
        box-sizing: border-box;
        overflow: hidden;
        float: left;
    }
    .aramapanelyazi {
        height: 40px;
        width: 120px;
        border: 1px solid #ccc;
        box-sizing: border-box;
        padding: 0px 10px;
        color: #000;
        margin: 0px 5px;
    }
    .aramapanelbuton {
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
    }
    .aramapanelbuton:hover {
        background-color: #fff;
        color: #000;
    }
    .logo {
        width: 40px;
        height: 40px;
        float: left;
    }
    .logo img {
        width: 100%;
    }
    .logoisim {
        font-size: 15px;
        width: 70%;
        height: 40px;
        line-height: 40px;
        font-weight: 500;
        color: #fff;
    }
    .hataekran i {
        color: #572aa7;
        font-size: 80px;
        text-align: center;
        width: 100%;
    }
    .hataekran {
        width: 80%;
        margin: 20px auto;
        color: #fff;
        background: #15161a;
        border: 1px solid #323442;
        padding: 10px;
        box-sizing: border-box;
        border-radius: 10px;
    }
    .hatayazi {
        color: #fff;
        font-size: 15px;
        text-align: center;
        width: 100%;
        margin: 20px 0px;
    }
    
    /* PLAYER STILLERİ */
    .player-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 9999;
        display: none;
        justify-content: center;
        align-items: center;
    }
    
    .player-container {
        width: 90%;
        height: 90%;
        background: #000;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
    }
    
    .player-close {
        position: absolute;
        top: 15px;
        right: 15px;
        background: #572aa7;
        color: white;
        border: none;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .player-close:hover {
        background: #ff0000;
    }
    
    .player-iframe {
        width: 100%;
        height: 100%;
        border: none;
    }
    
    .player-title {
        position: absolute;
        top: 15px;
        left: 15px;
        color: white;
        background: rgba(0, 0, 0, 0.7);
        padding: 5px 15px;
        border-radius: 5px;
        font-size: 14px;
        max-width: 60%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        z-index: 10000;
    }
    
    @media(max-width:550px) {
        .filmpanel {
            width: 31.33%;
            height: 190px;
            margin: 1%;
        }
        .player-container {
            width: 100%;
            height: 100%;
            border-radius: 0;
        }
    }
</style>
</head>
<body>
<div class="aramapanel">
<div class="aramapanelsol">
<div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
<div class="logoisim">TITAN TV VOD ({TOTAL_FILMS} Film)</div>
</div>
<div class="aramapanelsag">
<form action="" name="ara" method="GET" onsubmit="return searchFilms()">
    <input type="text" id="filmSearch" placeholder="Film Adını Giriniz..!" class="aramapanelyazi" oninput="resetFilmSearch()">
    <input type="submit" value="ARA" class="aramapanelbuton">
</form>
</div>
</div>

<!-- PLAYER OVERLAY (SAYFA İÇİNDE AÇILACAK) -->
<div class="player-overlay" id="playerOverlay">
    <div class="player-container">
        <button class="player-close" onclick="closePlayer()">×</button>
        <div class="player-title" id="playerTitle"></div>
        <iframe class="player-iframe" id="playerFrame" allowfullscreen></iframe>
    </div>
</div>

<div class="filmpaneldis" id="filmListesiContainer">
    <div class="baslik">HDFİLMCEHENNEMİ VOD - Tüm Filmler</div>
'''

    # Toplam film sayısını HTML'e ekle
    total_films = len(cleaned_data)
    html_template = html_template.replace("{TOTAL_FILMS}", str(total_films))
    
    # Film panellerini ekle - SADECE DIV OLARAK (A TAG'I YOK)
    film_counter = 0
    for film_id, film_info in cleaned_data.items():
        film_counter += 1
        
        # JavaScript için güvenli string
        safe_film_adi = film_info['film_adi'].replace("'", "\\'")
        
        html_template += f'''
    <div class="filmpanel" onclick="openPlayer('{film_info['player_url']}', '{safe_film_adi}')">
        <div class="filmresim"><img src="{film_info['resim']}" onerror="this.src='https://via.placeholder.com/300x450?text=Resim+Yok'"></div>
        <div class="filmisimpanel">
            <div class="filmisim">{film_info['film_adi']}</div>
        </div>
    </div>
'''
        
        if film_counter % 100 == 0:
            print(f"📝 HTML'e {film_counter}/{total_films} film eklendi...")

    html_template += '''
</div>

<script>
// PLAYER FONKSİYONLARI
function openPlayer(url, title) {
    document.getElementById('playerTitle').textContent = title;
    document.getElementById('playerFrame').src = url;
    document.getElementById('playerOverlay').style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Sayfa kaydırmayı engelle
}

function closePlayer() {
    document.getElementById('playerFrame').src = '';
    document.getElementById('playerOverlay').style.display = 'none';
    document.body.style.overflow = 'auto'; // Sayfa kaydırmayı geri aç
}

// ESC tuşu ile player'ı kapat
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closePlayer();
    }
});

// Overlay'e tıklayınca kapat (player dışına)
document.getElementById('playerOverlay').addEventListener('click', function(event) {
    if (event.target === this) {
        closePlayer();
    }
});

// ARAMA FONKSİYONLARI
function searchFilms() {
    var searchTerm = document.getElementById('filmSearch').value.toLowerCase();
    var container = document.getElementById('filmListesiContainer');
    var panels = container.querySelectorAll('.filmpanel');
    var found = false;

    panels.forEach(function(panel) {
        var filmName = panel.querySelector('.filmisim').textContent.toLowerCase();
        if (filmName.includes(searchTerm)) {
            panel.style.display = 'block';
            found = true;
        } else {
            panel.style.display = 'none';
        }
    });

    if (!found) {
        var existingNoResults = container.querySelector('.hataekran');
        if (!existingNoResults) {
            var noResults = document.createElement('div');
            noResults.className = 'hataekran';
            noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Film bulunamadı!</div>';
            container.appendChild(noResults);
        }
    } else {
        var noResults = container.querySelector('.hataekran');
        if (noResults) {
            noResults.remove();
        }
    }

    return false;
}

function resetFilmSearch() {
    var searchTerm = document.getElementById('filmSearch').value.toLowerCase();
    if (searchTerm === "") {
        var container = document.getElementById('filmListesiContainer');
        var panels = container.querySelectorAll('.filmpanel');
        panels.forEach(function(panel) {
            panel.style.display = 'block';
        });
        
        var noResults = container.querySelector('.hataekran');
        if (noResults) {
            noResults.remove();
        }
    }
}
</script>
</body>
</html>'''
    
    filename = "hdfilmcehennemi_INLINE.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML dosyası '{filename}' oluşturuldu!")
    print(f"🎬 Toplam {len(cleaned_data)} film eklendi")
    print(f"🎥 Filmler SAYFA İÇİNDE açılacak (yeni sekme yok)")
    print(f"💾 Dosya boyutu: {len(html_template) // 1024} KB")

if __name__ == "__main__":
    main()
