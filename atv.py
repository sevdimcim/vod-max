import requests
import re
import time
import json

def get_all_series():
    """Hem güncel hem eski dizileri al"""
    base = "https://www.atv.com.tr"
    series_dict = {}
    
    for page_name, page_url in [("Güncel Diziler", "/diziler"), 
                                ("Eski Diziler", "/eski-diziler")]:
        try:
            print(f"{page_name} sayfası taranıyor...")
            r = requests.get(f"{base}{page_url}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            
            # ATV yapısı için pattern
            if page_url == "/eski-diziler":
                # category-classic-item yapısı
                pattern = r'<a href="/([^"]+)"[^>]*?class="[^"]*blankpage[^"]*"[^>]*?>.*?<img[^>]*?src="([^"]+)"[^>]*?alt="([^"]+)"'
            else:
                # güncel diziler yapısı
                pattern = r'<a href="/([^"]+)"[^>]*?class="[^"]*blankpage[^"]*"[^>]*?>([^<]+)</a>\s*<img src="([^"]+)"'
            
            matches = re.findall(pattern, r.text, re.DOTALL)
            
            for match in matches:
                if page_url == "/eski-diziler":
                    slug, logo, name = match
                else:
                    slug, name, logo = match
                
                # canli-yayin, fragman gibi şeyleri atla
                if any(x in slug.lower() for x in ['canli-yayin', 'fragman', 'programlar', 'haber']):
                    continue
                
                # Logo URL'sini temizle
                if '?u=' in logo:
                    clean_logo = logo.split('?u=')[1]
                else:
                    clean_logo = logo
                
                # Eski diziler için farklı group
                group = "ATV-Güncel-Diziler" if page_url == "/diziler" else "ATV-Eski-Diziler"
                
                if slug not in series_dict:
                    series_dict[slug] = {
                        'name': name.strip(),
                        'slug': slug,
                        'url': f"{base}/{slug}",
                        'logo': clean_logo,
                        'group': group
                    }
                elif page_url == "/eski-diziler":
                    # Eski diziler öncelikli
                    series_dict[slug]['group'] = "ATV-Eski-Diziler"
            
            print(f"  {len(matches)} dizi bulundu")
        except Exception as e:
            print(f"  Hata: {e}")
            continue
    
    return list(series_dict.values())

def get_episodes(series_slug, series_name):
    """Dizinin tüm bölümlerini al"""
    episodes = []
    
    try:
        # Önce /bolumler sayfasını dene
        bolumler_url = f"https://www.atv.com.tr/{series_slug}/bolumler"
        r = requests.get(bolumler_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        # Dropdown'dan bölümleri al
        dropdown_pattern = r'<option[^>]*value="/([^/]+)/(\d+)-bolum/izle"[^>]*>(\d+)\.'
        dropdown_matches = re.findall(dropdown_pattern, r.text)
        
        if dropdown_matches:
            for slug, ep_num_str in dropdown_matches:
                if slug == series_slug:
                    ep_url = f"https://www.atv.com.tr/{slug}/{ep_num_str}-bolum/izle"
                    episodes.append((ep_url, int(ep_num_str)))
        else:
            # Alternatif: direk bölüm linklerini ara
            link_pattern = r'href="/([^/]+)/(\d+)-bolum/izle"'
            link_matches = re.findall(link_pattern, r.text)
            
            for slug, ep_num_str in link_matches:
                if slug == series_slug:
                    ep_url = f"https://www.atv.com.tr/{slug}/{ep_num_str}-bolum/izle"
                    episodes.append((ep_url, int(ep_num_str)))
        
        # Eğer hala bölüm yoksa, 1'den başlayarak test et
        if not episodes:
            print(f"    ⚠️  Bölüm bulunamadı, test ediliyor...")
            
            # Diziye göre maksimum bölüm
            max_episodes_dict = {
                'karadayi': 115,
                'kara-para-ask': 100,
                'avrupa-yakasi': 300,
                'eskiya-dunyaya-hukmdar-olmaz': 200,
                'sen-anlat-karadeniz': 200,
                'abi': 20,
                'kurulus-orhan': 20,
                'ayni-yagmur-altinda': 20
            }
            
            max_to_check = max_episodes_dict.get(series_slug, 100)
            found_count = 0
            
            for i in range(1, max_to_check + 1):
                test_url = f"https://www.atv.com.tr/{series_slug}/{i}-bolum/izle"
                try:
                    test_r = requests.head(test_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2, allow_redirects=True)
                    if test_r.status_code < 400:
                        episodes.append((test_url, i))
                        found_count += 1
                except:
                    pass
                
                if i % 20 == 0:
                    time.sleep(0.1)
            
            if found_count > 0:
                print(f"    ✅ {found_count} bölüm bulundu")
        
        # Sırala ve döndür
        if episodes:
            episodes.sort(key=lambda x: x[1])
            return [ep[0] for ep in episodes]
            
    except Exception as e:
        print(f"    Hata: {e}")
    
    return []

def extract_video_url(episode_url):
    """Video URL'sini çıkar"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.atv.com.tr/'
        }
        
        r = requests.get(episode_url, headers=headers, timeout=15)
        
        # contentUrl ara
        pattern = r'"contentUrl"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, r.text)
        
        if matches:
            for url in matches:
                # MP4 veya M3U8 farketmez
                if any(x in url.lower() for x in ['.mp4', '.m3u8', '//']):
                    return url
        
        # Alternatif arama
        video_patterns = [
            r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'src="(https?://[^"]+\.(?:mp4|m3u8)[^"]*)"',
        ]
        
        for pattern in video_patterns:
            video_matches = re.findall(pattern, r.text, re.IGNORECASE)
            for url in video_matches:
                if 'fragman' not in url.lower():
                    return url
                
    except Exception as e:
        print(f"      Video URL hatası: {e}")
    
    return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
    text = text.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def extract_episode_number(name, episode_url):
    """
    Bölüm numarasını çıkar.
    Önce URL'den, sonra isimden dener.
    """
    # URL'den bölüm numarasını al
    match = re.search(r'/(\d+)-bolum', episode_url)
    if match:
        ep_num = match.group(1)
        return f"{ep_num}. Bölüm"
    
    # İsimden bölüm numarasını al
    match = re.search(r'(\d+)\.?\s*Bölüm', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # Hiçbir şey bulunamazsa
    return "Bölüm"

def clean_image_url(url):
    """Resim URL'sini temizle"""
    if not url:
        return ""
    
    if "?" in url:
        url = url.split("?")[0]
    
    return url.strip()

def main():
    print("ATV Dizileri HTML Oluşturucu")
    print("=" * 60)
    
    # Tüm dizileri al
    all_series = get_all_series()
    
    if not all_series:
        print("Hiç dizi bulunamadı!")
        return
    
    print(f"\nToplam {len(all_series)} dizi bulundu")
    print("-" * 40)
    
    # Dizi verilerini topla
    diziler_data = {}
    processed_count = 0
    
    for idx, series in enumerate(all_series, 1):
        try:
            series_name = series["name"]
            series_id = slugify(series_name)
            group_icon = "🆕" if series['group'] == "ATV-Güncel-Diziler" else "📼"
            
            print(f"\n[{idx}/{len(all_series)}] {group_icon} {series_name}")
            print(f"  Slug: {series['slug']}")
            
            # Bölümleri al
            episodes = get_episodes(series['slug'], series_name)
            
            if not episodes:
                print(f"  ⚠️  Bölüm bulunamadı")
                continue
            
            print(f"  📺 {len(episodes)} bölüm bulundu")
            
            # Bölüm verilerini işle
            bolum_list = []
            added_count = 0
            
            for ep_url in episodes:
                # Bölüm numarasını al
                ep_num_display = "Bölüm"
                match = re.search(r'/(\d+)-bolum', ep_url)
                if match:
                    ep_num_display = f"{match.group(1)}. Bölüm"
                
                # Video URL'sini al
                video_url = extract_video_url(ep_url)
                
                if video_url:
                    bolum_list.append({
                        "ad": ep_num_display,  # Sadece "1. Bölüm", "2. Bölüm" şeklinde
                        "link": video_url
                    })
                    added_count += 1
                
                time.sleep(0.05)  # Sunucu yükü için
            
            if added_count > 0:
                # Resim URL'sini temizle
                poster_url = clean_image_url(series['logo'])
                if not poster_url:
                    poster_url = f"https://via.placeholder.com/300x450/15161a/ffffff?text={series_name.replace(' ', '+')}"
                
                # Dizi verisini kaydet
                diziler_data[series_id] = {
                    "resim": poster_url,
                    "bolumler": bolum_list
                }
                
                processed_count += 1
                print(f"  ✅ {added_count} bölüm eklendi")
            else:
                print(f"  ⚠️  Video bulunamadı")
                
        except Exception as e:
            print(f"  Hata: {e}")
            continue
    
    print(f"\n" + "=" * 60)
    print(f"Toplam {processed_count} dizi başarıyla işlendi!")
    print("=" * 60)
    
    create_html_file(diziler_data)

def create_html_file(data):
    """HTML dosyasını oluştur"""
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV ATV VOD</title>
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
            background-color: #ff0000;
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
            color: #ff0000;
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
            background: #ff0000;
        }}
        .baslik {{
            width: 96%;
            color: #fff;
            padding: 15px 10px;
            box-sizing: border-box;
            font-size: 18px;
            font-weight: bold;
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
            border: 3px solid #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }}
        .filmpanel:focus {{
            outline: none;
            border: 3px solid #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
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
            text-align: center;
            font-weight: bold;
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
            background-color: #ff0000;
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
            background: #ff0000;
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
        }}
        .geri-btn:hover {{
            background: #ff3333;
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
            <div class="logoisim">TITAN TV ATV VOD</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchSeries()">
                <input type="text" id="seriesSearch" placeholder="Dizi Adını Giriniz..!" class="aramapanelyazi" oninput="resetSeriesSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer">
        <div class="baslik">ATV DİZİLERİ VOD BÖLÜMLER</div>
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

        var diziler = {json_str};

        document.addEventListener('DOMContentLoaded', function() {{
            var container = document.getElementById("diziListesiContainer");
            
            Object.keys(diziler).forEach(function(key) {{
                var dizi = diziler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() {{ showBolumler(key); }};
                item.innerHTML = `
                    <div class="filmresim"><img src="${{dizi.resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=ATV+TV'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${{key.replace(/-/g, ' ').toUpperCase()}}</div>
                    </div>
                `;
                container.appendChild(item);
            }});

            checkInitialState();
        }});

        let currentScreen = 'anaSayfa';

        function showBolumler(diziID) {{
            sessionStorage.setItem('currentDiziID', diziID);
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            
            if (diziler[diziID]) {{
                diziler[diziID].bolumler.forEach(function(bolum) {{
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    item.innerHTML = `
                        <div class="filmresim"><img src="${{diziler[diziID].resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=ATV+TV'"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${{bolum.ad}}</div>
                        </div>
                    `;
                    item.onclick = function() {{
                        showPlayer(bolum.link, diziID);
                    }};
                    listContainer.appendChild(item);
                }});
            }} else {{
                listContainer.innerHTML = "<p>Bu dizi için bölüm bulunamadı.</p>";
            }}
            
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";

            currentScreen = 'bolumler';
            history.replaceState({{ page: 'bolumler', diziID: diziID }}, '', '#bolumler-' + diziID);
        }}

        function showPlayer(streamUrl, diziID) {{
            document.getElementById("playerpanel").style.display = "flex"; 
            document.getElementById("bolumler").classList.add("hidden");

            currentScreen = 'player';
            history.pushState({{ page: 'player', diziID: diziID, streamUrl: streamUrl }}, '', '#player-' + diziID);

            document.getElementById("main-player").innerHTML = "";

            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${{fullUrl}}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;
        }}

        function geriPlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");

            document.getElementById("main-player").innerHTML = "";

            currentScreen = 'bolumler';
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            history.replaceState({{ page: 'bolumler', diziID: currentDiziID }}, '', '#bolumler-' + currentDiziID);
        }}

        function geriDon() {{
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
            
            currentScreen = 'anaSayfa';
            history.replaceState({{ page: 'anaSayfa' }}, '', '#anaSayfa');
        }}

        window.addEventListener('popstate', function(event) {{
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            
            if (event.state && event.state.page === 'player' && event.state.diziID && event.state.streamUrl) {{
                showBolumler(event.state.diziID);
                showPlayer(event.state.streamUrl, event.state.diziID);
            }} else if (event.state && event.state.page === 'bolumler' && event.state.diziID) {{
                showBolumler(event.state.diziID);
            }} else {{
                sessionStorage.removeItem('currentDiziID');
                document.querySelector("#diziListesiContainer").classList.remove("hidden");
                document.getElementById("bolumler").classList.add("hidden");
                document.getElementById("playerpanel").style.display = "none";
                document.getElementById("geriBtn").style.display = "none";
                currentScreen = 'anaSayfa';
            }}
        }});

        function checkInitialState() {{
            var hash = window.location.hash;
            if (hash.startsWith('#bolumler-')) {{
                var diziID = hash.replace('#bolumler-', '');
                showBolumler(diziID);
            }} else if (hash.startsWith('#player-')) {{
                var parts = hash.split('-');
                var diziID = parts[1];
                var streamUrl = sessionStorage.getItem('lastStreamUrl');
                if (streamUrl) {{
                    showBolumler(diziID);
                    setTimeout(() => {{ showPlayer(streamUrl, diziID); }}, 100);
                }}
            }}
        }}

        function searchSeries() {{
            var searchTerm = document.getElementById('seriesSearch').value.toLowerCase();
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;

            panels.forEach(function(panel) {{
                var seriesName = panel.querySelector('.filmisim').textContent.toLowerCase();
                if (seriesName.includes(searchTerm)) {{
                    panel.style.display = 'block';
                    found = true;
                }} else {{
                    panel.style.display = 'none';
                }}
            }});

            if (!found) {{
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Sonuç bulunamadı!</div>';
                container.appendChild(noResults);
            }}

            return false;
        }}

        function resetSeriesSearch() {{
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            panels.forEach(function(panel) {{
                panel.style.display = 'block';
            }});
            var noResults = container.querySelector('.hataekran');
            if (noResults) {{
                noResults.remove();
            }}
        }}

        // Yükleme tamamlandığında hash kontrolü yap
        window.addEventListener('load', function() {{
            setTimeout(checkInitialState, 100);
        }});
    </script>
</body>
</html>'''
    
    filename = "atv_diziler.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"HTML dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    main()
