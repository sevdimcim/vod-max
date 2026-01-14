import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Web sitesi kök adresi
BASE_URL = "https://www.startv.com.tr"
IMG_BASE_URL = "https://media.startv.com.tr/star-tv"
API_PATTERN = r'"apiUrl\\":\\"(.*?)\\"'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Yeniden deneme ayarları
MAX_RETRIES = 5  # Her URL için maksimum deneme sayısı
RETRY_DELAY = 2  # Denemeler arası bekleme süresi (saniye)

def get_soup(url, retry_count=0):
    """
    URL'den BeautifulSoup nesnesi döndürür.
    Timeout hatalarında otomatik olarak yeniden dener.
    """
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
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def extract_episode_number(name):
    """
    Bölüm adından numarayı çeker (Sıralama için).
    Örn: '131. Bölüm' -> 131 döner.
    Bulamazsa 9999 döndürür ki en sona gitsin.
    """
    match = re.search(r'(\d+)\.?\s*Bölüm', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Alternatif format: "Bölüm X" veya "X Bölüm"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Sayısal ifade ara
    match = re.search(r'\b(\d+)\b', name)
    if match:
        return int(match.group(1))
    
    return 9999

def extract_episode_number_only(name):
    """
    Bölüm adından sadece sayıyı çıkarır ve formatlar.
    Örn: '131. Bölüm' -> '131. Bölüm'
         'Gülperi 23. Bölüm' -> '23. Bölüm'
    """
    match = re.search(r'(\d+)\.\s*Bölüm', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # Alternatif format: "Bölüm X"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # "X. Bölüm" formatı
    match = re.search(r'(\d+)\.\s*B[oö]l[üu]m', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # Sadece sayı bulmaya çalış
    match = re.search(r'\b(\d+)\b', name)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # Hiçbir format bulunamazsa orijinal adı döndür
    return name

def clean_image_url(url):
    """Resim URL'sini temizle: ? işaretinden sonrasını at"""
    if not url:
        return ""
    
    # ? işaretini bul ve öncesini al
    if "?" in url:
        url = url.split("?")[0]
    
    return url.strip()

def get_series_list():
    """Ana sayfadan tüm dizi linklerini ve resimlerini al"""
    print("Diziler ve afişleri listeleniyor...")
    soup = get_soup(f"{BASE_URL}/dizi")
    if not soup:
        print("Ana sayfa yüklenemedi!")
        return []
    
    series_list = []
    seen = set()
    
    # Tüm dizi linklerini bul
    links = soup.find_all("a", href=re.compile(r'^/dizi/'))
    
    for link in links:
        href = link.get("href")
        if not href or href in seen:
            continue
        
        seen.add(href)
        
        # Dizi adını bul
        dizi_name = "Bilinmeyen Dizi"
        
        # Resim URL'sini bul ve temizle
        img_tag = link.find("img")
        poster_url = ""
        
        if img_tag:
            # Dizi adını al
            if img_tag.get("alt") and img_tag.get("alt") != "alt":
                dizi_name = img_tag.get("alt").strip()
            
            # Resim URL'sini al
            if img_tag.get("src"):
                poster_url = img_tag.get("src")
            elif img_tag.get("data-src"):
                poster_url = img_tag.get("data-src")
            
            # Resim URL'sini temizle
            poster_url = clean_image_url(poster_url)
        
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
    
    print(f"Toplam {len(series_list)} adet dizi bulundu.")
    return series_list

def get_api_url_from_page(url):
    """Dizi sayfasından apiUrl al"""
    print(f"    [i] API URL aranıyor...")
    soup = get_soup(url)
    if not soup:
        return None
    
    page_content = str(soup)
    results = re.findall(API_PATTERN, page_content)
    
    if results:
        api_path = results[0].replace('\\/', '/')
        print(f"    [✓] API URL bulundu")
        return api_path
    
    print(f"    [✗] API URL bulunamadı")
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
            print(f"    [i] API isteği yapılıyor (skip={skip})...")
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
            
            # Daha fazla veri var mı kontrol et
            if len(items) < 100:
                has_more = False
            else:
                skip += 100
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            print(f"    [✗] API hatası: {e}")
            has_more = False
    
    return episodes

def main():
    print("Star TV Dizileri ve Bölümleri taranıyor (Doğru Afişlerle)...")
    
    # Tüm dizileri al
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
            
            # 1. ÖNCE ANA SAYFADAKİ RESMİ KULLAN
            poster_url = series["poster"]
            
            # 2. Eğer ana sayfada yoksa, detay sayfasına bak
            if not poster_url:
                print(f"    [i] Ana sayfada resim bulunamadı, detay sayfası taranıyor...")
                detail_soup = get_soup(series["url"])
                if detail_soup:
                    # Resim ara
                    img_tag = detail_soup.find("img", src=re.compile(r'media\.startv\.com\.tr'))
                    if img_tag and img_tag.get("src"):
                        poster_url = img_tag.get("src")
                        poster_url = clean_image_url(poster_url)
                        print(f"    [✓] Detay sayfasından resim bulundu")
                    elif detail_soup.find("meta", property="og:image"):
                        poster_url = detail_soup.find("meta", property="og:image").get("content", "")
                        poster_url = clean_image_url(poster_url)
                        print(f"    [✓] Open Graph resmi bulundu")
            
            # 3. Hala resim yoksa, API'den ilk bölümün resmini kullan
            if not poster_url:
                print(f"    [i] Detay sayfasında da resim bulunamadı, API deneniyor...")
            
            # API URL'sini al
            api_path = get_api_url_from_page(series["detail_url"])
            
            if not api_path:
                print(f"    [✗] Bu dizi için API URL bulunamadı, atlanıyor.")
                continue
            
            # API'den bölümleri al
            print(f"    [i] Bölümler alınıyor...")
            episodes = get_episodes_from_api(api_path)
            
            if episodes:
                # Bölümleri sırala (küçükten büyüğe)
                episodes = sorted(episodes, key=lambda x: x['episode_num'])
                
                # HTML için temizle
                cleaned_episodes = []
                for ep in episodes:
                    cleaned_episodes.append({
                        "ad": ep["clean_name"],
                        "link": ep["link"]
                    })
                
                # 4. Hala resim yoksa, ilk bölümün resmini kullan
                if not poster_url and episodes and episodes[0]["img"]:
                    poster_url = episodes[0]["img"]
                    print(f"    [✓] İlk bölümün resmi kullanılıyor")
                
                # 5. SON ÇARE: Placeholder kullan
                if not poster_url:
                    poster_url = "https://via.placeholder.com/300x450/15161a/ffffff?text=STAR+TV"
                    print(f"    [!] Resim bulunamadı, placeholder kullanılıyor")
                else:
                    print(f"    [✓] Dizi afişi: {poster_url[:60]}...")
                
                # Dizi verisini kaydet
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
    json_str = json.dumps(data, ensure_ascii=False)
    
    # HTML içeriğini ayrı bir değişkende oluşturalım
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV STAR TV VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/js/splide.min.js"></script>
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
            background-color: #ff0000;
        }
        .slidefilmpanel:hover .filmresim img {
            transform: scale(1.2);
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
            color: #ff0000;
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
        .sliderfilmimdb {
            display: none;
        }
        .bos {
            width: 100%;
            height: 60px;
            background: #ff0000;
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
        .filmpanel:focus {
            outline: none;
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
        .filmpanel:focus .filmresim img {
            transform: none;
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
        .filmimdb {
            display: none;
        }
        .resimust {
            display: none;
        }
        .filmyil {
            display: none;
        }
        .filmdil {
            display: none;
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
            background: ;
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
        #dahafazla {
            background: #ff0000;
            color: #fff;
            padding: 10px;
            margin: 20px auto;
            width: 200px;
            text-align: center;
            transition: .35s;
        }
        #dahafazla:hover {
            background: #fff;
            color: #000;
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

        let currentScreen = 'anaSayfa';

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
            } else {
                listContainer.innerHTML = "<p>Bu dizi için bölüm bulunamadı.</p>";
            }
            
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";

            currentScreen = 'bolumler';
            history.replaceState({ page: 'bolumler', diziID: diziID }, '', '#bolumler-' + diziID);
        }

        function showPlayer(streamUrl, diziID) {
            document.getElementById("playerpanel").style.display = "flex"; 
            document.getElementById("bolumler").classList.add("hidden");

            currentScreen = 'player';
            history.pushState({ page: 'player', diziID: diziID, streamUrl: streamUrl }, '', '#player-' + diziID);

            document.getElementById("main-player").innerHTML = "";

            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;
        }

        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");

            document.getElementById("main-player").innerHTML = "";

            currentScreen = 'bolumler';
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            history.replaceState({ page: 'bolumler', diziID: currentDiziID }, '', '#bolumler-' + currentDiziID);
        }

        function geriDon() {
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
            
            currentScreen = 'anaSayfa';
            history.replaceState({ page: 'anaSayfa' }, '', '#anaSayfa');
        }

        window.addEventListener('popstate', function(event) {
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            
            if (event.state && event.state.page === 'player' && event.state.diziID && event.state.streamUrl) {
                showBolumler(event.state.diziID);
                showPlayer(event.state.streamUrl, event.state.diziID);
            } else if (event.state && event.state.page === 'bolumler' && event.state.diziID) {
                showBolumler(event.state.diziID);
            } else {
                sessionStorage.removeItem('currentDiziID');
                document.querySelector("#diziListesiContainer").classList.remove("hidden");
                document.getElementById("bolumler").classList.add("hidden");
                document.getElementById("playerpanel").style.display = "none";
                document.getElementById("geriBtn").style.display = "none";
                currentScreen = 'anaSayfa';
            }
        });

        function checkInitialState() {
            var hash = window.location.hash;
            if (hash.startsWith('#bolumler-')) {
                var diziID = hash.replace('#bolumler-', '');
                showBolumler(diziID);
            } else if (hash.startsWith('#player-')) {
                var parts = hash.split('-');
                var diziID = parts[1];
                var streamUrl = sessionStorage.getItem('lastStreamUrl');
                if (streamUrl) {
                    showBolumler(diziID);
                    setTimeout(() => { showPlayer(streamUrl, diziID); }, 100);
                }
            }
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

        // Yükleme tamamlandığında hash kontrolü yap
        window.addEventListener('load', function() {
            setTimeout(checkInitialState, 100);
        });
    </script>
</body>
</html>'''
    
    filename = "startv.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"HTML dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    main()
