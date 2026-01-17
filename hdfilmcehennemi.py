import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys

# -----------------------------------------------------------------------------
# AYARLAR VE SABİTLER
# -----------------------------------------------------------------------------
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
DELAY_BETWEEN_FILMS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3

BASE_URL = "https://www.hdfilmcehennemi.nl"

# GitHub Raw JSON Linki (Senin verdiğin link)
GITHUB_JSON_URL = "https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_RETRIES = 3
RETRY_DELAY = 2

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# ANA İŞLEM (MAIN)
# -----------------------------------------------------------------------------

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
                        
                        poster_img = a_etiketi.find('img')
                        poster_url = ""
                        
                        if poster_img:
                            poster_url = poster_img.get('data-src', '')
                            if not poster_url:
                                poster_url = poster_img.get('src', '')
                            
                            if poster_url and "?" in poster_url:
                                poster_url = poster_url.split("?")[0]
                        
                        print(f"🎬 İşleniyor: {film_adi}")
                        
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
    # 1. TAM JSON DOSYASI (Tüm filmler burada)
    json_filename = "hdfilmcehennemi.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON dosyası '{json_filename}' oluşturuldu!")
    print(f"📁 JSON boyutu: {os.path.getsize(json_filename) / 1024:.2f} KB")
    
    # 2. OPTİMİZE EDİLMİŞ HTML DOSYASI
    # Sadece ilk 99 filmi alıp HTML içine gömeceğiz.
    first_99_keys = list(data.keys())[:99]
    first_99_data = {k: data[k] for k in first_99_keys}
    
    create_html_file(first_99_data, len(data))

def create_html_file(embedded_data, total_film_count):
    # Gömülecek veriyi JSON stringine çevir
    embedded_json_str = json.dumps(embedded_data, ensure_ascii=False)
    
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
            <div class="logoisim">TITAN TV</div>
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

    <div class="status-bar" id="dbStatus">Veriler yükleniyor...</div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik" id="baslikText">HDFİLMCEHENNEMİ FİLM ARŞİVİ</div>
        <div id="gridContainer"></div>
    </div>

    <script>
        // 1. ADIM: HTML İÇİNE GÖMÜLÜ İLK 99 FİLM (Python tarafından yazılır)
        // Bu sayede sayfa açılır açılmaz filmler görünür.
        var localDB = {embedded_json_str};

        // GitHub'daki tam liste URL'si
        const REMOTE_JSON_URL = "{GITHUB_JSON_URL}";

        // Tüm veritabanını tutacak değişken (Başlangıçta localDB ile başlar)
        var masterDB = {{ ...localDB }};
        var isFullDBLoaded = false;
        var totalRemoteCount = 0;

        // Sayfa yüklendiğinde
        window.onload = function() {{
            // 1. Önce eldeki 99 filmi ekrana bas
            renderFilms(localDB);
            document.getElementById('baslikText').innerText = "VİTRİN (İlk " + Object.keys(localDB).length + " Film)";
            
            // 2. Arkaplanda tüm listeyi çek
            fetchFullDatabase();
        }};

        // Arkaplanda GitHub'dan JSON çekme fonksiyonu
        async function fetchFullDatabase() {{
            try {{
                document.getElementById('dbStatus').innerText = "Tüm arşiv indiriliyor...";
                
                const response = await fetch(REMOTE_JSON_URL);
                if (!response.ok) throw new Error("Bağlantı hatası");
                
                const fullData = await response.json();
                
                // Gelen veriyi masterDB ile birleştir
                masterDB = {{ ...masterDB, ...fullData }};
                isFullDBLoaded = true;
                totalRemoteCount = Object.keys(masterDB).length;
                
                console.log("✅ Tam veritabanı yüklendi. Toplam Film: " + totalRemoteCount);
                document.getElementById('dbStatus').innerText = "Arşiv Güncel: " + totalRemoteCount + " Film";
                
                // Başlığı güncelle
                document.getElementById('baslikText').innerText = "FİLM ARŞİVİ (" + totalRemoteCount + " Film)";

            }} catch (error) {{
                console.error("❌ JSON çekilemedi:", error);
                document.getElementById('dbStatus').innerText = "Sadece Vitrin Modu (Bağlantı Hatası)";
            }}
        }}

        // Filmleri Ekrana Basma Fonksiyonu (Data Driven)
        // Artık DOM'u gizleyip açmıyoruz, veriyi filtreleyip yeniden çiziyoruz.
        function renderFilms(dataObj, isSearch = false) {{
            var container = document.getElementById("gridContainer");
            container.innerHTML = ""; // Önce temizle
            
            var keys = Object.keys(dataObj);
            
            // Eğer çok fazla sonuç varsa tarayıcıyı dondurmamak için limit koyalım (Arama değilse)
            var limit = isSearch ? 1000 : 99; 
            var count = 0;

            if (keys.length === 0) {{
                container.innerHTML = `
                    <div class="hataekran">
                        <i class="fas fa-search"></i>
                        <div class="hatayazi">Film bulunamadı!</div>
                    </div>
                `;
                return;
            }}

            for (var i = 0; i < keys.length; i++) {{
                if (count >= limit) break;
                
                var key = keys[i];
                var film = dataObj[key];
                
                var item = document.createElement("div");
                item.className = "filmpanel";
                
                // Tıklama olayı (Closure sorunu olmaması için IIFE veya let kullanımı, burada event atama)
                item.onclick = (function(link) {{
                    return function() {{
                        if (link) {{
                            window.open(link, '_blank');
                        }} else {{
                            alert("Link bulunamadı");
                        }}
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

        // Arama Fonksiyonu
        // DOM üzerinde değil, bellekteki (masterDB) JSON üzerinde arama yapar.
        function searchFilms(query) {{
            query = query.toLowerCase().trim();
            var container = document.getElementById("gridContainer");
            var baslik = document.getElementById("baslikText");

            // Arama kutusu boşsa varsayılan listeyi (ilk 99) göster
            if (!query) {{
                renderFilms(localDB);
                baslik.innerText = isFullDBLoaded ? "FİLM ARŞİVİ (" + totalRemoteCount + " Film)" : "VİTRİN";
                return;
            }}

            // MasterDB içinde arama yap
            var results = {{}};
            var resultCount = 0;
            
            for (var key in masterDB) {{
                var filmName = masterDB[key].isim.toLowerCase();
                if (filmName.includes(query)) {{
                    results[key] = masterDB[key];
                    resultCount++;
                }}
            }}

            console.log(`🔍 Arama: "${{query}}" - Bulunan: ${{resultCount}}`);
            baslik.innerText = `Arama Sonuçları: ${{resultCount}} Film`;
            
            renderFilms(results, true);
        }}
    </script>
</body>
</html>'''
    
    html_filename = "hdfilmcehennemi.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ HTML dosyası '{html_filename}' oluşturuldu!")
    print(f"📁 HTML boyutu: {os.path.getsize(html_filename) / 1024:.2f} KB")
    print(f"🔗 Arkaplan JSON Linki: {GITHUB_JSON_URL}")
    print(f"🎬 Gömülü Film: {len(embedded_data)}")
    print(f"🎬 Toplam Film: {total_film_count}")

if __name__ == "__main__":
    main()
