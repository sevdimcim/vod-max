import requests
from bs4 import BeautifulSoup
import time
import json
import re

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

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def main():
    print("🚀 Filmler çekiliyor... Afişler ve Player linkleri toplanıyor...\n")
    
    filmler_data = {}
    
    try:
        # İlk 5 sayfa (istediğin kadar artırabilirsin)
        for sayfa in range(1, 6):
            api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
            
            print(f"📄 SAYFA {sayfa} İŞLENİYOR...")
            
            response = requests.get(api_page_url, headers=HEADERS_PAGE, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                html_chunk = data.get('html', '')
                soup = BeautifulSoup(html_chunk, 'html.parser')
                
                # Film kutularını bul
                film_kutulari = soup.find_all('a', class_='poster')

                if not film_kutulari:
                    continue

                for a_etiketi in film_kutulari:
                    film_link = a_etiketi.get('href')
                    film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
                    
                    # Film ID oluştur
                    film_id = slugify(film_adi)
                    
                    # --- POSTER ÇEKME ---
                    poster_img = a_etiketi.find('img')
                    poster_url = poster_img.get('data-src') if poster_img else ""
                    
                    if not film_link:
                        continue
                    
                    print(f"🎬 Film: {film_adi}")
                    print(f"🖼️ Afiş: {poster_url}")
                    
                    try:
                        target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
                        film_sayfasi = requests.get(target_url, headers=HEADERS_FILM, timeout=10)
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
                            
                            print(f"🔗 Player Link: {player_url}")
                        else:
                            print("⚠️ Player link bulunamadı.")
                            
                        # Film verisini kaydet
                        filmler_data[film_id] = {
                            "resim": poster_url,
                            "film_adi": film_adi,
                            "player_url": player_url
                        }
                        
                    except Exception as e:
                        print(f"❌ Hata (Film Sayfası): {e}")
                    
                    print("-" * 50)
                    time.sleep(0.8) # Ban riskine karşı hafif bekleme

            else:
                print(f"❌ Sayfa {sayfa} yüklenemedi. Durum Kodu: {response.status_code}")

    except Exception as e:
        print(f"💥 Ana hata oluştu: {e}")

    print(f"\n✅ Toplam {len(filmler_data)} film başarıyla çekildi!")
    
    create_html_file(filmler_data)

def create_html_file(data):
    # HTML içeriği - SENİN VERDİĞİN YAPIDA
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
    .playerpanel {
        width: 100%;
        height: 100vh;
        position: fixed;
        top: 0;
        left: 0;
        background: #0a0e17;
        z-index: 9999;
        display: none;
        flex-direction: column;
        overflow: hidden;
    }
    
    .player-geri-btn {
        background: #572aa7;
        color: white;
        padding: 10px;
        text-align: center;
        border-radius: 5px;
        cursor: pointer;
        margin: 10px;
        width: 100px;
        position: absolute;
        top: 10px;
        left: 10px;
        z-index: 10000;
    }
    
    #main-player {
        width: 100%;
        height: 100%;
        background: #000;
    }
    
    #film-frame {
        width: 100%;
        height: 100%;
        border: none;
    }
    
    @media(max-width:550px) {
        .filmpanel {
            width: 31.33%;
            height: 190px;
            margin: 1%;
        }
    }
</style>
</head>
<body>
<div class="aramapanel">
<div class="aramapanelsol">
<div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
<div class="logoisim">TITAN TV VOD</div>
</div>
<div class="aramapanelsag">
<form action="" name="ara" method="GET" onsubmit="return searchFilms()">
    <input type="text" id="filmSearch" placeholder="Film Adını Giriniz..!" class="aramapanelyazi" oninput="resetFilmSearch()">
    <input type="submit" value="ARA" class="aramapanelbuton">
</form>
</div>
</div>
<div class="filmpaneldis" id="filmListesiContainer">
    <div class="baslik">HDFİLMCEHENNEMİ VOD</div>
'''

    # Film panellerini ekle (SENİN VERDİĞİN YAPIDA)
    for film_id, film_info in data.items():
        if film_info["player_url"]:  # Sadece player linki olanları ekle
            html_template += f'''
    <a href="{film_info['player_url']}" target="_blank">
        <div class="filmpanel">
            <div class="filmresim"><img src="{film_info['resim']}" onerror="this.src='https://via.placeholder.com/300x450?text=Resim+Yok'"></div>
            <div class="filmisimpanel">
                <div class="filmisim">{film_info['film_adi']}</div>
            </div>
        </div>
    </a>
'''
        else:
            # Player linki yoksa boş panel
            html_template += f'''
    <a href="#">
        <div class="filmpanel">
            <div class="filmresim"><img src="{film_info['resim']}" onerror="this.src='https://via.placeholder.com/300x450?text=Resim+Yok'"></div>
            <div class="filmisimpanel">
                <div class="filmisim">{film_info['film_adi']} (Link Yok)</div>
            </div>
        </div>
    </a>
'''

    html_template += '''
</div>

<script>
function searchFilms() {
    var searchTerm = document.getElementById('filmSearch').value.toLowerCase();
    var container = document.getElementById('filmListesiContainer');
    var panels = container.querySelectorAll('.filmpanel');
    var found = false;

    panels.forEach(function(panel) {
        var filmName = panel.querySelector('.filmisim').textContent.toLowerCase();
        if (filmName.includes(searchTerm)) {
            panel.parentElement.style.display = 'block';
            found = true;
        } else {
            panel.parentElement.style.display = 'none';
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
            panel.parentElement.style.display = 'block';
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
    
    filename = "hdfilmcehennemi.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"HTML dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    main()
