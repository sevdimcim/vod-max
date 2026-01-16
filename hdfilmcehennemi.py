import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys

# Komut satırı argümanları
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10  # 10 sayfa test için
DELAY_BETWEEN_FILMS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3

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
    try:
        response = requests.get(url, headers=headers, timeout=20)
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
    try:
        response = requests.get(url, headers=headers, timeout=20)
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
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def main():
    print(f"🚀 HDFilmCehennemi Botu Başlatıldı...")
    print(f"📊 {PAGES_TO_SCRAPE} sayfa taranacak")
    print(f"⏱️  Filmler arası bekleme: {DELAY_BETWEEN_FILMS} saniye\n")
    
    filmler_data = {}
    film_sayisi = 0
    
    try:
        for sayfa in range(1, PAGES_TO_SCRAPE + 1):
            api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
            
            print(f"📄 SAYFA {sayfa}/{PAGES_TO_SCRAPE} İŞLENİYOR...")
            
            data = get_json_response(api_page_url, HEADERS_PAGE)
            
            if data:
                html_chunk = data.get('html', '')
                soup = BeautifulSoup(html_chunk, 'html.parser')
                
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
                            poster_url = poster_img.get('data-src', '')
                            if not poster_url:
                                poster_url = poster_img.get('src', '')
                            
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
                                    iframe = film_soup.find('iframe', {'class': 'close'})
                                    
                                    if iframe and iframe.get('data-src'):
                                        raw_iframe_url = iframe.get('data-src')
                                        
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
                        
                        time.sleep(DELAY_BETWEEN_FILMS)
                        
                    except Exception as e:
                        print(f"    ❌ Film işlenirken hata: {e}")
                        continue
                
                print(f"\n📊 Sayfa {sayfa} tamamlandı. Toplam film: {film_sayisi}\n")
                time.sleep(1)
                
            else:
                print(f"❌ Sayfa {sayfa} yüklenemedi.")

    except Exception as e:
        print(f"💥 Ana hata oluştu: {e}")

    print("\n" + "="*50)
    print(f"✅ İşlem tamamlandı! Toplam {len(filmler_data)} film başarıyla işlendi!")
    print("="*50)
    
    create_files(filmler_data)

def create_files(data):
    # 1. JSON dosyasını oluştur
    json_filename = "hdfilmcehennemi.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON dosyası '{json_filename}' oluşturuldu!")
    print(f"📁 JSON boyutu: {os.path.getsize(json_filename) / 1024:.2f} KB")
    
    # 2. HTML dosyasını oluştur (ESKİ TASARIM AYNI KALSIN)
    create_html_file(data)

def create_html_file(data):
    # JSON verisini string'e çevir
    json_str = json.dumps(data, ensure_ascii=False)
    
    # HTML içeriği - TAMAMEN ESKİSİ GİBİ (SADECE JSON KISMI DEĞİŞECEK)
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV FİLM VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/js/splide.min.js"></script>
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
        .slider-slide {{
            background: #15161a;
            box-sizing: border-box;
        }}  
        .slidefilmpanel {{
            transition: .35s;
            box-sizing: border-box;
            background: #15161a;
            overflow: hidden;
        }}
        .slidefilmpanel:hover {{
            background-color: #572aa7;
        }}
        .slidefilmpanel:hover .filmresim img {{
            transform: scale(1.2);
        }}
        .slider {{
            position: relative;
            padding-bottom: 0px;
            width: 100%;
            overflow: hidden;
            --tw-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
            --tw-shadow-colored: 0 25px 50px -12px var(--tw-shadow-color);
            box-shadow: var(--tw-ring-offset-shadow, 0 0 #0000), var(--tw-ring-shadow, 0 0 #0000), var(--tw-shadow);
        }}
        .slider-container {{
            display: flex;
            width: 100%;
            scroll-snap-type: x var(--tw-scroll-snap-strictness);
            --tw-scroll-snap-strictness: mandatory;
            align-items: center;
            overflow: auto;
            scroll-behavior: smooth;
        }}
        .slider-container .slider-slide {{
            aspect-ratio: 9/13.5;
            display: flex;
            flex-shrink: 0;
            flex-basis: 14.14%;
            scroll-snap-align: start;
            flex-wrap: nowrap;
            align-items: center;
            justify-content: center;
        }}
        .slider-container::-webkit-scrollbar {{
            width: 0px;
        }}
        .clear {{
            clear: both;
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
        .filmpaneldis {{
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
        }}
        .aramafilmpaneldis {{
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
        }}
        .sliderfilmimdb {{
            display: none;
        }}
        .bos {{
            width: 100%;
            height: 60px;
            background: #572aa7;
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
        .filmpanel:focus {{
            outline: none;
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
        .filmpanel:focus .filmresim img {{
            transform: none;
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
        .filmimdb {{
            display: none;
        }}
        .resimust {{
            display: none;
        }}
        .filmyil {{
            display: none;
        }}
        .filmdil {{
            display: none;
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
            background: ;
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
        #dahafazla {{
            background: #572aa7;
            color: #fff;
            padding: 10px;
            margin: 20px auto;
            width: 200px;
            text-align: center;
            transition: .35s;
        }}
        #dahafazla:hover {{
            background: #fff;
            color: #000;
        }}
        .hidden {{ display: none; }}
        .bolum-container {{
            background: #15161a;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }}
        .geri-btn {{
            background: #572aa7;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
            margin-bottom: 10px;
            display: none;
            width: 100px;
        }}
        .geri-btn:hover {{
            background: #6b3ec7;
            transition: background 0.3s;
        }}
        .playerpanel {{
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
        }}
        
        #main-player {{
            width: 100%;
            height: 100%; 
            background: #000;
        }}
        
        #bradmax-iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}

        .player-geri-btn {{
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
        }}
        
        @media(max-width:550px) {{
            .filmpanel {{
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }}
            #main-player {{
                height: 100%; 
            }}
        }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchFilms()">
                <input type="text" id="filmSearch" placeholder="Film Ara..!" class="aramapanelyazi" oninput="resetFilmSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik">HDFİLMCEHENNEMİ FİLM ARŞİVİ</div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">Geri</div>
        <div id="main-player"></div>
    </div>

    <script>
        const BRADMAX_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const BRADMAX_PARAMS = "&autoplay=true&fs=true"; 
        const JSON_URL = "https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json";

        var filmler = {{}};

        async function loadFilms() {{
            try {{
                const response = await fetch(JSON_URL);
                
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                
                filmler = await response.json();
                console.log(`✅ ${{Object.keys(filmler).length}} film yüklendi`);
                
                // Filmleri yükle
                initApp();
            }} catch (error) {{
                console.error("❌ JSON yüklenemedi:", error);
                document.getElementById('filmListesiContainer').innerHTML = `
                    <div class="hataekran">
                        <i class="fas fa-exclamation-triangle"></i>
                        <div class="hatayazi">Filmler yüklenemedi!<br>${{error.message}}</div>
                    </div>
                `;
            }}
        }}

        function initApp() {{
            var container = document.getElementById("filmListesiContainer");
            
            Object.keys(filmler).forEach(function(key) {{
                var film = filmler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() {{ 
                    if (film.link) {{
                        showPlayer(film.link, key);
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

            // TOPLAM FİLM SAYISINI GÖSTER
            var baslik = document.querySelector('.baslik');
            baslik.textContent += ` (${{Object.keys(filmler).length}} Film)`;
        }}

        function showPlayer(streamUrl, filmID) {{
            document.getElementById("playerpanel").style.display = "flex"; 

            // Player'ı hazırla
            document.getElementById("main-player").innerHTML = "";

            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${{fullUrl}}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;

            history.pushState({{ page: 'player', filmID: filmID, streamUrl: streamUrl }}, '', '#player-' + filmID);
        }}

        function geriPlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("main-player").innerHTML = "";

            history.replaceState({{ page: 'anaSayfa' }}, '', '#anaSayfa');
        }}

        window.addEventListener('popstate', function(event) {{
            if (event.state && event.state.page === 'player' && event.state.filmID && event.state.streamUrl) {{
                showPlayer(event.state.streamUrl, event.state.filmID);
            }} else {{
                geriPlayer();
            }}
        }});

        function searchFilms() {{
            var searchTerm = document.getElementById('filmSearch').value.toLowerCase();
            var container = document.getElementById('filmListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;

            panels.forEach(function(panel) {{
                if (panel.classList.contains('baslik')) return;
                
                var filmName = "";
                var filmIsimDiv = panel.querySelector('.filmisim');
                if (filmIsimDiv) {{
                    filmName = filmIsimDiv.textContent.toLowerCase();
                }}
                
                if (filmName.includes(searchTerm)) {{
                    panel.style.display = 'block';
                    found = true;
                }} else {{
                    panel.style.display = 'none';
                }}
            }});

            if (!found && searchTerm) {{
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">"${{searchTerm}}" için film bulunamadı!</div>';
                container.appendChild(noResults);
            }}

            return false;
        }}

        function resetFilmSearch() {{
            var container = document.getElementById('filmListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            panels.forEach(function(panel) {{
                panel.style.display = 'block';
            }});
            var noResults = container.querySelector('.hataekran');
            if (noResults) {{
                noResults.remove();
            }}
        }}

        // Sayfa yüklendiğinde filmleri çek
        window.addEventListener('load', function() {{
            loadFilms();
            
            // URL'de player hash'i varsa
            var hash = window.location.hash;
            if (hash.startsWith('#player-')) {{
                var filmID = hash.replace('#player-', '');
                if (filmler[filmID] && filmler[filmID].link) {{
                    setTimeout(() => {{
                        showPlayer(filmler[filmID].link, filmID);
                    }}, 500);
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    html_filename = "hdfilmcehennemi.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ HTML dosyası '{html_filename}' oluşturuldu!")
    print(f"📁 HTML boyutu: {os.path.getsize(html_filename) / 1024:.2f} KB")
    print(f"🔗 JSON Linki: https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json")
    print(f"🎬 Film sayısı: {len(data)}")

if __name__ == "__main__":
    main()
