import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Web sitesi kök adresi
BASE_URL = "https://www.hdfilmcehennemi.nl"

# --- HEADERS AYARLARI ---
HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Yeniden deneme ayarları
MAX_RETRIES = 3
RETRY_DELAY = 2

def get_json_response(url, headers, retry_count=0):
    """JSON yanıtı alır, timeout hatalarında yeniden dener."""
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_json_response(url, headers, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_json_response(url, headers, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
            return None

def get_soup(url, headers, retry_count=0):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, headers, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, headers, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
            return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def main():
    print("🚀 HDFilmCehennemi Botu Başlatıldı...")
    print("🎬 Filmler ve Afişler Çekiliyor...\n")
    
    filmler_data = {}
    film_sayisi = 0
    
    try:
        # İlk 5 sayfa (İstediğin kadar artırabilirsin)
        for sayfa in range(1, 6):
            api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
            
            print(f"📄 SAYFA {sayfa} İŞLENİYOR...")
            
            data = get_json_response(api_page_url, HEADERS_PAGE)
            
            if data:
                html_chunk = data.get('html', '')
                soup = BeautifulSoup(html_chunk, 'html.parser')
                
                # Film kutularını bul
                film_kutulari = soup.find_all('a', class_='poster')

                if not film_kutulari:
                    print(f"    ⚠ Sayfa {sayfa}'da film bulunamadı.")
                    continue

                for a_etiketi in film_kutulari:
                    try:
                        film_link = a_etiketi.get('href')
                        film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
                        
                        if not film_adi:
                            continue
                        
                        film_id = slugify(film_adi)
                        
                        # --- POSTER ÇEKME ---
                        poster_img = a_etiketi.find('img')
                        poster_url = ""
                        
                        if poster_img:
                            # Önce data-src'ye bak
                            poster_url = poster_img.get('data-src', '')
                            if not poster_url:
                                # data-src yoksa src'ye bak
                                poster_url = poster_img.get('src', '')
                            
                            # Poster URL'sini temizle
                            if poster_url and "?" in poster_url:
                                poster_url = poster_url.split("?")[0]
                        
                        print(f"🎬 İşleniyor: {film_adi}")
                        
                        # --- FİLM DETAY SAYFASINA GİT ve LİNK ÇEK ---
                        video_url = ""
                        if film_link:
                            try:
                                target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
                                film_soup = get_soup(target_url, HEADERS_FILM)
                                
                                if film_soup:
                                    # Iframe bulma
                                    iframe = film_soup.find('iframe', {'class': 'close'})
                                    
                                    if iframe and iframe.get('data-src'):
                                        raw_iframe_url = iframe.get('data-src')
                                        
                                        # RPLAYER DÖNÜŞTÜRME
                                        if "rapidrame_id=" in raw_iframe_url:
                                            rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                                            video_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                                        else:
                                            video_url = raw_iframe_url
                                        
                                        print(f"    ✓ Link bulundu")
                                    else:
                                        print(f"    ⚠ Iframe bulunamadı")
                                else:
                                    print(f"    ⚠ Film sayfası yüklenemedi")
                                    
                            except Exception as e:
                                print(f"    ⚠ Hata (Film Sayfası): {e}")
                        
                        # Veriyi kaydet
                        filmler_data[film_id] = {
                            "isim": film_adi,
                            "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
                            "link": video_url
                        }
                        
                        film_sayisi += 1
                        print(f"    ✓ Kaydedildi ({film_sayisi}. film)")
                        print("-" * 50)
                        
                        time.sleep(0.5) # Rate limiting
                        
                    except Exception as e:
                        print(f"    ❌ Film işlenirken hata: {e}")
                        continue
                
                print(f"\n📊 Sayfa {sayfa} tamamlandı. Toplam film: {film_sayisi}\n")
                time.sleep(1) # Sayfalar arası bekleme
                
            else:
                print(f"❌ Sayfa {sayfa} yüklenemedi.")

    except Exception as e:
        print(f"💥 Ana hata oluştu: {e}")

    print("\n" + "="*50)
    print(f"✅ İşlem tamamlandı! Toplam {len(filmler_data)} film başarıyla işlendi!")
    print("="*50)
    
    create_html_file(filmler_data)

def create_html_file(data):
    # JSON verisini HTML için uygun formatta hazırla
    json_data = {}
    
    for film_id, film_info in data.items():
        json_data[film_id] = {
            "resim": film_info["resim"],
            "link": film_info["link"],
            "isim": film_info["isim"]  # HTML'de göstermek için ismi de sakla
        }
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    
    # HTML içeriği
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV FİLM VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) {
            -moz-user-select: -moz-none;
            -khtml-user-select: none;
            -webkit-user-select: none;
            -o-user-select: none;
            -ms-user-select: none;
            user-select: none
        }
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
        .slider-slide {
            background: #15161a;
            box-sizing: border-box;
        }  
        .slidefilmpanel {
            transition: .35s;
            box-sizing: border-box;
            background: #15161a;
            overflow: hidden;
        }
        .slidefilmpanel:hover {
            background-color: #572aa7;
        }
        .slider {
            position: relative;
            padding-bottom: 0px;
            width: 100%;
            overflow: hidden;
            --tw-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
            --tw-shadow-colored: 0 25px 50px -12px var(--tw-shadow-color);
            box-shadow: var(--tw-ring-offset-shadow, 0 0 #0000), var(--tw-ring-shadow, 0 0 #0000), var(--tw-shadow);
        }
        .slider-container {
            display: flex;
            width: 100%;
            scroll-snap-type: x var(--tw-scroll-snap-strictness);
            --tw-scroll-snap-strictness: mandatory;
            align-items: center;
            overflow: auto;
            scroll-behavior: smooth;
        }
        .slider-container .slider-slide {
            aspect-ratio: 9/13.5;
            display: flex;
            flex-shrink: 0;
            flex-basis: 14.14%;
            scroll-snap-align: start;
            flex-wrap: nowrap;
            align-items: center;
            justify-content: center;
        }
        .slider-container::-webkit-scrollbar {
            width: 0px;
        }
        .clear {
            clear: both;
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
        .filmpaneldis {
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
        }
        .aramafilmpaneldis {
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
        }
        .bos {
            width: 100%;
            height: 60px;
            background: #572aa7;
        }
        .baslik {
            width: 96%;
            color: #fff;
            padding: 15px 10px;
            box-sizing: border-box;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            border-bottom: 2px solid #572aa7;
            margin-bottom: 20px;
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
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }
        .filmisimpanel {
            width: 100%;
            height: 200px;
            position: relative;
            margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.8) 100%);
            display: flex;
            align-items: flex-end;
            padding: 10px;
            box-sizing: border-box;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .filmpanel:hover {
            border: 3px solid #572aa7;
            box-shadow: 0 0 20px rgba(87, 42, 167, 0.7);
            transform: translateY(-5px);
        }
        .filmpanel:hover .filmisimpanel {
            opacity: 1;
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
            object-fit: cover;
            transition: transform 0.4s ease;
        }
        .filmpanel:hover .filmresim img {
            transform: scale(1.1);
        }
        .filmisim {
            width: 100%;
            font-size: 14px;
            text-decoration: none;
            padding: 5px;
            box-sizing: border-box;
            color: #fff;
            text-align: center;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
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
            position: sticky;
            top: 0;
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
            width: 200px;
            border: 1px solid #572aa7;
            box-sizing: border-box;
            padding: 0px 15px;
            background: #0a0e17;
            color: #fff;
            margin: 0px 5px;
            border-radius: 20px;
            outline: none;
        }
        .aramapanelbuton {
            height: 40px;
            width: 100px;
            text-align: center;
            background-color: #572aa7;
            border: none;
            color: #fff;
            box-sizing: border-box;
            overflow: hidden;
            float: right;
            transition: .35s;
            border-radius: 20px;
            cursor: pointer;
            font-weight: bold;
        }
        .aramapanelbuton:hover {
            background-color: #6b3ec7;
            transform: scale(1.05);
        }
        .logo {
            width: 40px;
            height: 40px;
            float: left;
        }
        .logo img {
            width: 100%;
            border-radius: 50%;
        }
        .logoisim {
            font-size: 18px;
            width: 70%;
            height: 40px;
            line-height: 40px;
            font-weight: bold;
            color: #fff;
            margin-left: 10px;
            float: left;
        }
        #dahafazla {
            background: #572aa7;
            color: #fff;
            padding: 10px;
            margin: 20px auto;
            width: 200px;
            text-align: center;
            transition: .35s;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
        }
        #dahafazla:hover {
            background: #6b3ec7;
            transform: scale(1.05);
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
        
        #main-player {
            width: 100%;
            height: 100%; 
            background: #000;
        }
        
        #bradmax-iframe {
            width: 100%;
            height: 100%;
            border: none;
        }

        .player-geri-btn {
            background: #572aa7;
            color: white;
            padding: 12px 20px;
            text-align: center;
            border-radius: 25px;
            cursor: pointer;
            margin: 20px;
            width: auto;
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 10000;
            font-weight: bold;
            border: 2px solid #fff;
            transition: all 0.3s ease;
        }
        
        .player-geri-btn:hover {
            background: #6b3ec7;
            transform: scale(1.05);
        }
        
        /* YÜKLEME ANİMASYONU */
        .loading {
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
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #572aa7;
            border-top: 5px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* MESAJ KUTUSU */
        .message-box {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #15161a;
            border: 2px solid #572aa7;
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            z-index: 99998;
            display: none;
            box-shadow: 0 0 30px rgba(87, 42, 167, 0.5);
        }
        
        @media(max-width:550px) {
            .filmpanel {
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }
            
            .filmisimpanel {
                padding: 5px;
            }
            
            .filmisim {
                font-size: 12px;
            }
            
            .aramapanelyazi {
                width: 150px;
            }
            
            .aramapanelbuton {
                width: 70px;
            }
            
            .logoisim {
                font-size: 16px;
            }
            
            #main-player {
                height: 100%; 
            }
            
            .player-geri-btn {
                padding: 10px 15px;
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
    <!-- YÜKLEME EKRANI -->
    <div class="loading" id="loading">
        <div class="spinner"></div>
    </div>
    
    <!-- MESAJ KUTUSU -->
    <div class="message-box" id="messageBox">
        <div id="messageText"></div>
        <button onclick="hideMessage()" style="margin-top: 15px; padding: 8px 20px; background: #572aa7; color: white; border: none; border-radius: 20px; cursor: pointer;">Tamam</button>
    </div>
    
    <!-- ANA PANEL -->
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV FİLM</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchFilms()">
                <input type="text" id="filmSearch" placeholder="Film ara..." class="aramapanelyazi" oninput="resetFilmSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <!-- FİLM LİSTESİ -->
    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik">HDFİLMCEHENNEMİ FİLM ARŞİVİ</div>
    </div>

    <!-- PLAYER -->
    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">
            <i class="fas fa-arrow-left"></i> Geri Dön
        </div>
        <div id="main-player"></div>
    </div>

    <script>
        const BRADMAX_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const BRADMAX_PARAMS = "&autoplay=true&fs=true&controls=true";
        
        var filmler = ''' + json_str + ''';
        
        // YÜKLEME BİTTİĞİNDE
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
            initApp();
        }, 1000);
        
        function initApp() {
            var container = document.getElementById("filmListesiContainer");
            
            Object.keys(filmler).forEach(function(key) {
                var film = filmler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() { 
                    if (film.link) {
                        showPlayer(film.link, key);
                    } else {
                        showMessage("Bu film için video linki bulunamadı.");
                    }
                };
                item.innerHTML = `
                    <div class="filmresim">
                        <img src="${film.resim}" alt="${film.isim}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'">
                    </div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${film.isim}</div>
                    </div>
                `;
                container.appendChild(item);
            });
            
            // TOPLAM FİLM SAYISINI GÖSTER
            var baslik = document.querySelector('.baslik');
            baslik.textContent += ` (${Object.keys(filmler).length} Film)`;
        }
        
        function showPlayer(streamUrl, filmID) {
            document.getElementById("playerpanel").style.display = "flex"; 
            
            // Player'ı hazırla
            document.getElementById("main-player").innerHTML = "";
            
            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;
            
            // Sayfa hash'ini güncelle
            history.pushState({ page: 'player', filmID: filmID, streamUrl: streamUrl }, '', '#player-' + filmID);
        }
        
        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("main-player").innerHTML = "";
            
            // Ana sayfaya dön
            history.replaceState({ page: 'anaSayfa' }, '', '#anaSayfa');
        }
        
        // MESAJ FONKSİYONLARI
        function showMessage(text) {
            document.getElementById('messageText').textContent = text;
            document.getElementById('messageBox').style.display = 'block';
        }
        
        function hideMessage() {
            document.getElementById('messageBox').style.display = 'none';
        }
        
        // ARAMA FONKSİYONLARI
        function searchFilms() {
            var searchTerm = document.getElementById('filmSearch').value.toLowerCase();
            var container = document.getElementById('filmListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;
            
            // Başlık hariç tüm panelleri kontrol et
            panels.forEach(function(panel) {
                if (panel.classList.contains('baslik')) return;
                
                var filmName = "";
                var filmIsimDiv = panel.querySelector('.filmisim');
                if (filmIsimDiv) {
                    filmName = filmIsimDiv.textContent.toLowerCase();
                }
                
                if (filmName.includes(searchTerm)) {
                    panel.style.display = 'block';
                    found = true;
                } else {
                    panel.style.display = 'none';
                }
            });
            
            if (!found && searchTerm) {
                showMessage(`"${searchTerm}" için film bulunamadı.`);
            }
            
            return false;
        }
        
        function resetFilmSearch() {
            var container = document.getElementById('filmListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            
            panels.forEach(function(panel) {
                panel.style.display = 'block';
            });
        }
        
        // BROWSER HISTORY YÖNETİMİ
        window.addEventListener('popstate', function(event) {
            if (event.state && event.state.page === 'player') {
                // Player'da kalmaya devam et
                return;
            } else {
                // Ana sayfaya dön
                geriPlayer();
            }
        });
        
        // SAYFA YÜKLENDİĞİNDE HASH KONTROLÜ
        window.addEventListener('load', function() {
            var hash = window.location.hash;
            if (hash.startsWith('#player-')) {
                var filmID = hash.replace('#player-', '');
                if (filmler[filmID] && filmler[filmID].link) {
                    setTimeout(() => {
                        showPlayer(filmler[filmID].link, filmID);
                    }, 500);
                }
            }
        });
        
        // ESC TUŞU İLE PLAYER'DAN ÇIK
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                geriPlayer();
            }
        });
    </script>
</body>
</html>'''
    
    filename = "hdfilmcehennemi.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML dosyası '{filename}' oluşturuldu!")
    print(f"📁 Dosya boyutu: {os.path.getsize(filename) / 1024:.2f} KB")
    print(f"🎬 Film sayısı: {len(data)}")

if __name__ == "__main__":
    main()
