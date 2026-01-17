import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
import concurrent.futures
from datetime import datetime
import logging

# Logging ayarı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Komut satırı argümanları
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
DELAY_BETWEEN_FILMS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
MAX_WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 20  # Paralel işlem sayısı

BASE_URL = "https://www.hdfilmcehennemi.nl"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_RETRIES = 2
RETRY_DELAY = 1
TIMEOUT = 15

# Session oluştur - connection reuse için
session = requests.Session()
session.headers.update(HEADERS_PAGE)

def get_json_response(url, retry_count=0):
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            logging.warning(f"Timeout, yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES}): {url}")
            time.sleep(RETRY_DELAY)
            return get_json_response(url, retry_count + 1)
        else:
            logging.error(f"Maksimum deneme sayısına ulaşıldı: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logging.warning(f"Hata: {e}, yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_json_response(url, retry_count + 1)
        else:
            logging.error(f"Maksimum deneme: {e}")
            return None

def get_soup(url, retry_count=0):
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser", features="lxml")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            logging.warning(f"Timeout, yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES}): {url}")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            logging.error(f"Maksimum deneme sayısına ulaşıldı: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logging.warning(f"Hata: {e}, yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            logging.error(f"Maksimum deneme: {e}")
            return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def extract_film_data(a_etiketi):
    """Tek bir film için veri çıkarır"""
    try:
        film_link = a_etiketi.get('href')
        film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
        
        if not film_adi:
            return None
        
        film_id = slugify(film_adi)
        
        # Poster URL'sini al
        poster_img = a_etiketi.find('img')
        poster_url = ""
        
        if poster_img:
            poster_url = poster_img.get('data-src', '')
            if not poster_url:
                poster_url = poster_img.get('src', '')
            
            if poster_url and "?" in poster_url:
                poster_url = poster_url.split("?")[0]
        
        # Video URL'sini al
        video_url = ""
        if film_link:
            try:
                target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
                film_soup = get_soup(target_url)
                
                if film_soup:
                    iframe = film_soup.find('iframe', {'class': 'close'})
                    
                    if iframe and iframe.get('data-src'):
                        raw_iframe_url = iframe.get('data-src')
                        
                        if "rapidrame_id=" in raw_iframe_url:
                            rapid_id = raw_iframe_url.split("rapidrame_id=")[1]
                            video_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                        else:
                            video_url = raw_iframe_url
            except Exception as e:
                logging.debug(f"Video URL alınamadı: {e}")
        
        return {
            "id": film_id,
            "data": {
                "isim": film_adi,
                "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
                "link": video_url
            }
        }
        
    except Exception as e:
        logging.error(f"Film verisi çıkarılamadı: {e}")
        return None

def process_page(sayfa):
    """Bir sayfayı işler ve film listesi döndürür"""
    logging.info(f"Sayfa {sayfa} işleniyor...")
    
    api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
    data = get_json_response(api_page_url)
    
    if not data:
        logging.warning(f"Sayfa {sayfa} yüklenemedi")
        return []
    
    html_chunk = data.get('html', '')
    soup = BeautifulSoup(html_chunk, "html.parser")
    
    film_kutulari = soup.find_all('a', class_='poster')
    
    if not film_kutulari:
        logging.warning(f"Sayfa {sayfa}'da film bulunamadı")
        return []
    
    # Paralel olarak film verilerini çıkar
    films = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_film = {executor.submit(extract_film_data, a_etiketi): a_etiketi for a_etiketi in film_kutulari}
        
        for future in concurrent.futures.as_completed(future_to_film):
            result = future.result()
            if result:
                films.append(result)
                logging.info(f"✓ {result['data']['isim']}")
                time.sleep(DELAY_BETWEEN_FILMS)
    
    logging.info(f"Sayfa {sayfa} tamamlandı, {len(films)} film bulundu")
    return films

def main():
    print(f"🚀 HDFilmCehennemi Botu Başlatıldı...")
    print(f"📊 {PAGES_TO_SCRAPE} sayfa taranacak")
    print(f"⚡ Paralel işlemler: {MAX_WORKERS}")
    print(f"⏱️  Filmler arası bekleme: {DELAY_BETWEEN_FILMS} saniye\n")
    
    start_time = time.time()
    all_films = {}
    
    try:
        # Tüm sayfaları paralel işle
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Sayfa numaralarını işle
            page_numbers = range(1, PAGES_TO_SCRAPE + 1)
            future_to_page = {executor.submit(process_page, sayfa): sayfa for sayfa in page_numbers}
            
            for future in concurrent.futures.as_completed(future_to_page):
                sayfa = future_to_page[future]
                try:
                    films = future.result()
                    for film in films:
                        all_films[film['id']] = film['data']
                except Exception as e:
                    logging.error(f"Sayfa {sayfa} işlenirken hata: {e}")
    
    except Exception as e:
        logging.error(f"Ana hata: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ İşlem tamamlandı! Toplam {len(all_films)} film başarıyla işlendi!")
    print(f"⏱️  Toplam süre: {elapsed_time:.2f} saniye")
    print(f"⚡ Saniyede {len(all_films)/elapsed_time:.2f} film")
    print(f"{'='*60}")
    
    create_files(all_films)

def create_files(data):
    # Tüm filmleri JSON'a kaydet
    json_filename = "hdfilmcehennemi.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON dosyası '{json_filename}' oluşturuldu!")
    print(f"📁 JSON boyutu: {os.path.getsize(json_filename) / 1024:.2f} KB")
    print(f"🎬 JSON'daki toplam film: {len(data)}")
    
    # HTML için sadece ilk 99 filmi seç
    html_films = dict(list(data.items())[:99])
    
    # HTML dosyasını oluştur
    create_html_file(html_films, len(data))

def create_html_file(html_data, total_films):
    """HTML dosyasını oluşturur (sadece 99 film ile)"""
    
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
            font-size: 18px;
            font-weight: bold;
        }
        .baslik small {
            font-size: 14px;
            color: #aaa;
            margin-left: 10px;
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
            width: 200px;
            border: 1px solid #ccc;
            box-sizing: border-box;
            padding: 0px 15px;
            color: #000;
            margin: 0px 5px;
            border-radius: 20px;
            background: #fff;
            font-size: 14px;
        }
        .aramapanelbuton {
            height: 40px;
            width: 80px;
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
            text-align: center;
        }
        .hatayazi {
            color: #fff;
            font-size: 15px;
            text-align: center;
            width: 100%;
            margin: 20px 0px;
        }
        .json-info {
            background: #572aa7;
            color: white;
            padding: 10px;
            margin: 10px auto;
            width: 96%;
            border-radius: 10px;
            text-align: center;
            font-size: 14px;
        }
        .json-info a {
            color: #fff;
            text-decoration: underline;
            font-weight: bold;
        }
        
        @media(max-width:768px) {
            .filmpanel {
                width: 23%;
                height: 180px;
                margin: 1%;
            }
            .aramapanelyazi {
                width: 150px;
            }
        }
        
        @media(max-width:550px) {
            .filmpanel {
                width: 31.33%;
                height: 160px;
                margin: 1%;
            }
            .aramapanelsol {
                width: 40%;
            }
            .aramapanelsag {
                width: 60%;
            }
        }
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV</div>
        </div>
        <div class="aramapanelsag">
            <input type="text" id="filmSearch" placeholder="Film Ara (JSON'dan yüklenecek)..!" class="aramapanelyazi">
            <button onclick="searchFromJson()" class="aramapanelbuton">ARA</button>
        </div>
    </div>

    <div class="json-info">
        🔗 JSON Bağlantısı: <a href="https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json" target="_blank">https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json</a><br>
        📊 Toplam <strong>''' + str(total_films) + '''</strong> film JSON'da bulunuyor (HTML'de sadece 99 film gösteriliyor)
    </div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik">HDFİLMCEHENNEMİ FİLM ARŞİVİ <small>(HTML: 99 film, Tüm filmler için JSON'dan ara)</small></div>
    </div>

    <script>
        const JSON_URL = "https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json";
        let allFilms = {};
        let jsonLoaded = false;
        
        // HTML'deki filmleri yükle
        function loadHtmlFilms() {
            const htmlFilms = ''' + json.dumps(html_data, ensure_ascii=False) + ''';
            
            Object.keys(htmlFilms).forEach(function(key) {
                var film = htmlFilms[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                
                item.onclick = function() { 
                    if (film.link) {
                        window.open(film.link, '_blank');
                    } else {
                        alert("Bu film için video linki bulunamadı.");
                    }
                };
                
                item.innerHTML = `
                    <div class="filmresim"><img src="${film.resim}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${film.isim}</div>
                    </div>
                `;
                document.getElementById('filmListesiContainer').appendChild(item);
            });
        }
        
        // JSON'dan tüm filmleri yükle
        async function loadJsonFilms() {
            try {
                const response = await fetch(JSON_URL + '?t=' + new Date().getTime());
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                allFilms = await response.json();
                jsonLoaded = true;
                console.log(`✅ JSON'dan ${Object.keys(allFilms).length} film yüklendi`);
                
            } catch (error) {
                console.error("❌ JSON yüklenemedi:", error);
            }
        }
        
        // JSON'dan arama yap
        async function searchFromJson() {
            const searchTerm = document.getElementById('filmSearch').value.toLowerCase().trim();
            
            if (!searchTerm) {
                alert("Lütfen bir film adı girin!");
                return;
            }
            
            if (!jsonLoaded) {
                alert("JSON yükleniyor, lütfen bekleyin...");
                await loadJsonFilms();
            }
            
            // Arama sonuçlarını filtrele
            const results = Object.keys(allFilms).filter(key => {
                const film = allFilms[key];
                return film.isim.toLowerCase().includes(searchTerm);
            });
            
            if (results.length === 0) {
                alert(`"${searchTerm}" için film bulunamadı!`);
                return;
            }
            
            // Arama sonuçlarını göster
            showSearchResults(results.slice(0, 50), searchTerm); // İlk 50 sonucu göster
        }
        
        // Arama sonuçlarını göster
        function showSearchResults(filmKeys, searchTerm) {
            const container = document.getElementById('filmListesiContainer');
            
            // Önceki içeriği temizle
            container.innerHTML = `
                <div class="baslik">"${searchTerm}" ARAMA SONUÇLARI <small>(${filmKeys.length} film bulundu)</small></div>
                <div style="text-align: center; margin: 10px;">
                    <button onclick="loadHtmlFilms()" style="background: #572aa7; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer;">HTML Filmlerine Dön</button>
                </div>
            `;
            
            // Sonuçları göster
            filmKeys.forEach(function(key) {
                var film = allFilms[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                
                item.onclick = function() { 
                    if (film.link) {
                        window.open(film.link, '_blank');
                    } else {
                        alert("Bu film için video linki bulunamadı.");
                    }
                };
                
                item.innerHTML = `
                    <div class="filmresim"><img src="${film.resim}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${film.isim}</div>
                    </div>
                `;
                container.appendChild(item);
            });
        }
        
        // Sayfa yüklenince çalıştır
        window.onload = function() {
            // HTML filmlerini yükle
            loadHtmlFilms();
            
            // JSON filmlerini arka planda yükle
            loadJsonFilms();
            
            // Enter tuşu ile arama
            document.getElementById('filmSearch').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchFromJson();
                }
            });
        };
    </script>
</body>
</html>'''
    
    html_filename = "hdfilmcehennemi.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    html_size = os.path.getsize(html_filename) / 1024
    print(f"✅ HTML dosyası '{html_filename}' oluşturuldu!")
    print(f"📁 HTML boyutu: {html_size:.2f} KB")
    print(f"🎬 HTML'deki film sayısı: {len(html_data)}")
    print(f"🔗 JSON Linki: https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json")

if __name__ == "__main__":
    main()
