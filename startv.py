import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Web sitesi kök adresi
BASE_URL = "https://www.startv.com.tr"
IMG_BASE_URL = "https://media.startv.com.tr"
API_PATTERN = r'"apiUrl\\":\\"(.*?)\\"'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

MAX_RETRIES = 5
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
            return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def extract_episode_number(name):
    match = re.search(r'(\d+)\.?\s*Bölüm', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'\b(\d+)\b', name)
    if match:
        return int(match.group(1))
    
    return 9999

def extract_episode_number_only(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'(\d+)\.\s*B[oö]l[üu]m', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'\b(\d+)\b', name)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    return name

def clean_image_url(url):
    """Resim URL'sini temizle: ? işaretinden sonrasını at"""
    if not url:
        return ""
    
    # ? işaretini bul
    if "?" in url:
        url = url.split("?")[0]
    
    return url.strip()

def get_series_list():
    """Ana sayfadan tüm dizi linklerini ve resimlerini al"""
    print("Diziler ve resimleri listeleniyor...")
    soup = get_soup(f"{BASE_URL}/dizi")
    if not soup:
        print("Ana sayfa yüklenemedi!")
        return []
    
    series_list = []
    seen = set()
    
    # Tüm a tag'lerini bul (dizi linkleri)
    all_links = soup.find_all("a", href=re.compile(r'^/dizi/'))
    
    for link in all_links:
        href = link.get("href")
        if not href or href in seen:
            continue
        
        seen.add(href)
        
        # Dizi adını bul
        dizi_name = "Bilinmeyen Dizi"
        
        # Link içindeki img tag'ini ara
        img_tag = link.find("img")
        poster_url = ""
        
        if img_tag:
            # Önce src'ye bak
            if img_tag.get("src"):
                poster_url = img_tag.get("src")
            # Sonra data-src'ye bak
            elif img_tag.get("data-src"):
                poster_url = img_tag.get("data-src")
            
            # Resim URL'sini temizle
            poster_url = clean_image_url(poster_url)
            
            # Alt text'ten dizi adını al
            if img_tag.get("alt") and img_tag.get("alt") != "alt":
                dizi_name = img_tag.get("alt").strip()
        
        # Eğer hala isim yoksa, URL'den çıkart
        if dizi_name == "Bilinmeyen Dizi":
            parts = href.split("/")
            if len(parts) >= 3:
                slug = parts[-2]
                dizi_name = slug.replace("-", " ").title()
        
        series_list.append({
            "name": dizi_name,
            "slug": href.split("/")[-2] if "/" in href else "",
            "url": BASE_URL + href,
            "detail_url": BASE_URL + href + "/bolumler",
            "poster": poster_url
        })
        print(f"    [+] {dizi_name} -> {poster_url[:50]}...")
    
    print(f"\nToplam {len(series_list)} adet dizi bulundu.")
    return series_list

def get_api_url_from_page(url):
    """Dizi sayfasından apiUrl al"""
    soup = get_soup(url)
    if not soup:
        return None
    
    page_content = str(soup)
    results = re.findall(API_PATTERN, page_content)
    
    if results:
        api_path = results[0].replace('\\/', '/')
        return api_path
    
    return None

def get_episodes_from_api(api_path):
    """API'den bölümleri çek"""
    episodes = []
    
    api_params = {
        "sort": "episodeNo asc",
        "limit": "100"
    }
    
    skip = 0
    has_more = True
    
    url = BASE_URL + api_path
    
    while has_more:
        api_params["skip"] = skip
        
        try:
            response = requests.get(url, params=api_params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            
            for item in items:
                # Bölüm adını oluştur
                heading = item.get("heading", "")
                title = item.get("title", "")
                
                if heading and title:
                    name = f"{heading} {title}"
                elif title:
                    name = title
                elif heading:
                    name = heading
                else:
                    name = "Bilinmeyen Bölüm"
                
                # Resim URL'si
                img = ""
                if item.get("image") and item["image"].get("fullPath"):
                    img = IMG_BASE_URL + item["image"]["fullPath"]
                    img = clean_image_url(img)  # Temizle
                
                # Video URL'si
                stream_url = ""
                if "video" in item and item["video"].get("referenceId"):
                    stream_url = f'https://dygvideo.dygdigital.com/api/redirect?PublisherId=1&ReferenceId=StarTV_{item["video"]["referenceId"]}&SecretKey=NtvApiSecret2014*&.m3u8'
                
                if stream_url:
                    episodes.append({
                        "name": name,
                        "clean_name": extract_episode_number_only(name),
                        "img": img,
                        "link": stream_url,
                        "episode_num": extract_episode_number(name)
                    })
            
            if len(items) < 100:
                has_more = False
            else:
                skip += 100
                time.sleep(0.3)
                
        except Exception as e:
            print(f"    [✗] API hatası: {e}")
            has_more = False
    
    return episodes

def main():
    print("Star TV Dizileri ve Bölümleri taranıyor (Güncel Resimlerle)...")
    
    series_list = get_series_list()
    if not series_list:
        print("Hiç dizi bulunamadı!")
        return
    
    diziler_data = {}
    
    for idx, series in enumerate(series_list, 1):
        try:
            dizi_adi = series["name"]
            dizi_id = slugify(dizi_adi)
            
            print(f"\n[{idx}/{len(series_list)}] --> İşleniyor: {dizi_adi}")
            
            # Poster URL'si (ana sayfadan temizlenmiş)
            poster_url = series["poster"]
            
            # Eğer poster yoksa, placeholder kullan
            if not poster_url:
                poster_url = "https://via.placeholder.com/300x450/15161a/ffffff?text=STAR+TV"
                print(f"    [!] Resim bulunamadı, placeholder kullanılıyor")
            else:
                print(f"    [✓] Resim: {poster_url[:60]}...")
            
            # API URL'sini al
            api_path = get_api_url_from_page(series["detail_url"])
            
            if not api_path:
                print(f"    [✗] API URL bulunamadı, atlanıyor.")
                continue
            
            # Bölümleri al
            print(f"    [i] Bölümler alınıyor...")
            episodes = get_episodes_from_api(api_path)
            
            if episodes:
                episodes = sorted(episodes, key=lambda x: x['episode_num'])
                
                cleaned_episodes = []
                for ep in episodes:
                    cleaned_episodes.append({
                        "ad": ep["clean_name"],
                        "link": ep["link"]
                    })
                
                diziler_data[dizi_id] = {
                    "resim": poster_url,
                    "bolumler": cleaned_episodes
                }
                
                print(f"    [✓] {len(cleaned_episodes)} bölüm eklendi.")
            else:
                print(f"    [✗] Hiç bölüm bulunamadı.")
                
        except Exception as e:
            print(f"    [HATA] Dizi işlenirken hata: {e}")
            continue
    
    print("\n" + "="*50)
    print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
    print("="*50)
    
    create_html_file(diziler_data)

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV STAR TV VOD</title>
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
            border: 3px solid #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
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
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 0px 5px;
            box-sizing: border-box;
            color: #fff;
            position: absolute;
            bottom: 5px;
            text-align: center;
            font-weight: bold;
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
            background-color: #ff0000;
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
        .hidden { display: none; }
        .bolum-container {
            background: #15161a;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }
        .geri-btn {
            background: #ff0000;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
            margin-bottom: 10px;
            display: none;
            width: 100px;
        }
        .geri-btn:hover {
            background: #ff3333;
            transition: background 0.3s;
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
            background: #ff0000;
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
        
        @media(max-width:550px) {
            .filmpanel {
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }
            #main-player {
                height: 100%; 
            }
        }
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t75soiq.png"></div>
            <div class="logoisim">TITAN TV STAR TV</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchSeries()">
                <input type="text" id="seriesSearch" placeholder="Dizi Adını Giriniz..!" class="aramapanelyazi" oninput="resetSeriesSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer">
        <div class="baslik">STAR TV DİZİLERİ VOD BÖLÜMLER</div>
    </div>

    <div id="bolumler" class="bolum-container hidden">
        <div id="geriBtn" class="geri-btn" onclick="geriDon()">Geri</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">Geri</div>
        <div id="main-player"></div>
    </div>

    <script>
        const BRADMAX_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const BRADMAX_PARAMS = "&autoplay=true&fs=true"; 

        var diziler = ''' + json_str + ''';

        document.addEventListener('DOMContentLoaded', function() {
            var container = document.getElementById("diziListesiContainer");
            
            Object.keys(diziler).forEach(function(key) {
                var dizi = diziler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() { showBolumler(key); };
                item.innerHTML = `
                    <div class="filmresim"><img src="${dizi.resim}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=STAR+TV'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${key.replace(/-/g, ' ').toUpperCase()}</div>
                    </div>
                `;
                container.appendChild(item);
            });

            checkInitialState();
        });

        function showBolumler(diziID) {
            sessionStorage.setItem('currentDiziID', diziID);
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            
            if (diziler[diziID]) {
                diziler[diziID].bolumler.forEach(function(bolum) {
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    item.innerHTML = `
                        <div class="filmresim"><img src="${diziler[diziID].resim}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=STAR+TV'"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${bolum.ad}</div>
                        </div>
                    `;
                    item.onclick = function() {
                        showPlayer(bolum.link, diziID);
                    };
                    listContainer.appendChild(item);
                });
            }
            
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";
        }

        function showPlayer(streamUrl, diziID) {
            document.getElementById("playerpanel").style.display = "flex"; 
            document.getElementById("bolumler").classList.add("hidden");

            document.getElementById("main-player").innerHTML = "";

            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;
        }

        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("main-player").innerHTML = "";
        }

        function geriDon() {
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
        }

        function searchSeries() {
            var searchTerm = document.getElementById('seriesSearch').value.toLowerCase();
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;

            panels.forEach(function(panel) {
                var seriesName = panel.querySelector('.filmisim').textContent.toLowerCase();
                if (seriesName.includes(searchTerm)) {
                    panel.style.display = 'block';
                    found = true;
                } else {
                    panel.style.display = 'none';
                }
            });

            if (!found) {
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Sonuç bulunamadı!</div>';
                container.appendChild(noResults);
            }

            return false;
        }

        function resetSeriesSearch() {
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            panels.forEach(function(panel) {
                panel.style.display = 'block';
            });
            var noResults = container.querySelector('.hataekran');
            if (noResults) {
                noResults.remove();
            }
        }

        function checkInitialState() {
            // Sayfa yüklendiğinde hash kontrolü
        }
    </script>
</body>
</html>'''
    
    filename = "startv.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"HTML dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    main()
