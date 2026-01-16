import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys

# Komut satırı argümanları
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5  # Test için 5 sayfa
DELAY_BETWEEN_FILMS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

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
    "Connection": "keep-alive"
}

def get_json_response(url):
    try:
        response = requests.get(url, headers=HEADERS_PAGE, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ JSON alınamadı: {e}")
        return None

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS_FILM, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"❌ Sayfa alınamadı: {e}")
        return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def extract_video_link(soup):
    """Film sayfasından video linkini çıkar - EN BASİT VE ETKİLİ YÖNTEM"""
    try:
        # 1. EN GARANTİ YOL: iframe'de data-src'yi ara
        iframe = soup.find('iframe', {'class': 'close'})
        if iframe:
            data_src = iframe.get('data-src', '')
            if data_src:
                print(f"   🔍 data-src bulundu: {data_src[:50]}...")
                
                # RPlayer dönüşümü
                if "rapidrame_id=" in data_src:
                    rapid_id = data_src.split("rapidrame_id=")[1]
                    # & işaretinden önceki kısmı al
                    if '&' in rapid_id:
                        rapid_id = rapid_id.split('&')[0]
                    video_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                    print(f"   ✅ RPlayer linki oluşturuldu")
                    return video_url
                else:
                    print(f"   ✅ Direkt link kullanılıyor")
                    return data_src
        
        # 2. ALTERNATİF: iframe src'si
        if iframe and iframe.get('src'):
            src = iframe.get('src')
            print(f"   🔍 iframe src bulundu: {src[:50]}...")
            return src
        
        # 3. SCRIPT TAG'LERİNDE ARA
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'rapidrame' in script.string:
                content = script.string
                # rapidrame_id ara
                if 'rapidrame_id' in content:
                    import re
                    match = re.search(r'rapidrame_id["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', content)
                    if match:
                        rapid_id = match.group(1)
                        video_url = f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                        print(f"   ✅ Script'ten RPlayer linki bulundu")
                        return video_url
        
        print("   ⚠️ Video linki bulunamadı")
        return ""
        
    except Exception as e:
        print(f"   ❌ Link çıkarılırken hata: {e}")
        return ""

def main():
    print("="*60)
    print("🚀 HDFİLMCEHENNEMİ SCRAPER BAŞLATILDI!")
    print(f"📊 Çekilecek Sayfa Sayısı: {PAGES_TO_SCRAPE}")
    print(f"⏱️  Filmler arası bekleme: {DELAY_BETWEEN_FILMS} saniye")
    print("="*60)
    
    filmler_data = {}
    total_films = 0
    start_time = time.time()
    
    try:
        for sayfa in range(1, PAGES_TO_SCRAPE + 1):
            api_page_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
            
            print(f"\n📄 SAYFA {sayfa}/{PAGES_TO_SCRAPE} İŞLENİYOR...")
            
            data = get_json_response(api_page_url)
            
            if data:
                html_chunk = data.get('html', '')
                soup = BeautifulSoup(html_chunk, 'html.parser')
                film_kutulari = soup.find_all('a', class_='poster')
                
                if not film_kutulari:
                    print(f"    ⚠️ Sayfa {sayfa}'da film bulunamadı.")
                    continue
                
                print(f"    📊 Sayfada {len(film_kutulari)} film bulundu")
                
                for a_etiketi in film_kutulari:
                    try:
                        film_link = a_etiketi.get('href')
                        film_adi = a_etiketi.get('title') or a_etiketi.text.strip()
                        
                        if not film_adi:
                            continue
                        
                        film_id = slugify(film_adi)
                        
                        # POSTER
                        poster_img = a_etiketi.find('img')
                        poster_url = ""
                        
                        if poster_img:
                            poster_url = poster_img.get('data-src', '')
                            if not poster_url:
                                poster_url = poster_img.get('src', '')
                            
                            if poster_url and "?" in poster_url:
                                poster_url = poster_url.split("?")[0]
                        
                        print(f"\n🎬 İşleniyor: {film_adi}")
                        print(f"   📍 Poster: {poster_url[:50]}..." if poster_url else "   📍 Poster: Yok")
                        
                        # VIDEO LINK - EN ÖNEMLİ KISIM!
                        video_url = ""
                        if film_link:
                            try:
                                target_url = BASE_URL + film_link if not film_link.startswith('http') else film_link
                                print(f"   🔗 Film sayfasına gidiliyor...")
                                
                                film_soup = get_soup(target_url)
                                
                                if film_soup:
                                    video_url = extract_video_link(film_soup)
                                    
                                    if video_url:
                                        print(f"   ✅ Link: {video_url[:80]}...")
                                    else:
                                        print(f"   ❌ Link bulunamadı!")
                                else:
                                    print(f"   ❌ Film sayfası yüklenemedi")
                                    
                            except Exception as e:
                                print(f"   ❌ Hata: {str(e)[:100]}")
                        
                        # Veriyi kaydet
                        filmler_data[film_id] = {
                            "isim": film_adi,
                            "resim": poster_url if poster_url else "https://via.placeholder.com/300x450/15161a/ffffff?text=No+Image",
                            "link": video_url
                        }
                        
                        total_films += 1
                        print(f"   ✓ Kaydedildi ({total_films}. film)")
                        
                        time.sleep(DELAY_BETWEEN_FILMS)
                        
                    except Exception as e:
                        print(f"   ❌ Film işlenirken hata: {e}")
                        continue
                
                print(f"\n📊 Sayfa {sayfa} tamamlandı. Toplam film: {total_films}")
                time.sleep(1)
                
            else:
                print(f"❌ Sayfa {sayfa} yüklenemedi.")
    
    except Exception as e:
        print(f"💥 Ana hata oluştu: {e}")
    
    elapsed_time = time.time() - start_time
    
    # İstatistikler
    links_found = sum(1 for film in filmler_data.values() if film['link'])
    
    print("\n" + "="*60)
    print(f"✅ İŞLEM TAMAMLANDI!")
    print(f"📊 Toplam Sayfa: {PAGES_TO_SCRAPE}")
    print(f"🎬 Toplam Film: {len(filmler_data)}")
    print(f"🔗 Link Bulunan: {links_found} film")
    print(f"⚠️  Link Yok: {len(filmler_data) - links_found} film")
    print(f"📈 Başarı Oranı: {links_found/len(filmler_data)*100:.1f}%" if filmler_data else "0%")
    print(f"⏱️  Toplam Süre: {elapsed_time:.1f} saniye")
    print("="*60)
    
    # Örnek filmleri göster
    print("\n🎬 İLK 5 FİLM ÖRNEĞİ:")
    for i, (film_id, film_info) in enumerate(list(filmler_data.items())[:5]):
        print(f"   {i+1}. {film_info['isim'][:50]}...")
        print(f"      Link: {'✅ VAR' if film_info['link'] else '❌ YOK'}")
        if film_info['link']:
            print(f"      URL: {film_info['link'][:80]}...")
    
    # Dosyaları oluştur
    create_files(filmler_data)

def create_files(data):
    # 1. JSON DOSYASI (TÜM FİLMLER)
    json_filename = "hdfilmcehennemi.json"
    
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    file_size_kb = os.path.getsize(json_filename) / 1024
    links_found = sum(1 for film in data.values() if film['link'])
    
    print(f"\n📁 JSON DOSYASI OLUŞTURULDU:")
    print(f"✅ Dosya Adı: {json_filename}")
    print(f"📊 Toplam Film: {len(data)}")
    print(f"🔗 Link Bulunan: {links_found} film")
    print(f"💾 Boyut: {file_size_kb:.1f} KB")
    print(f"🔗 GitHub RAW Linki: https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json")
    
    # 2. HTML DOSYASI (SADECE İLK 99 FİLM)
    create_html_file(data)

def create_html_file(all_data):
    # İlk 99 filmi seç
    first_99_films = {}
    count = 0
    for film_id, film_info in all_data.items():
        if count >= 99:
            break
        first_99_films[film_id] = film_info
        count += 1
    
    # Link istatistiği
    links_in_html = sum(1 for film in first_99_films.values() if film['link'])
    
    # JSON linki
    json_url = "https://raw.githubusercontent.com/sevdimcim/vod-max/refs/heads/main/hdfilmcehennemi.json"
    
    # HTML içeriği
    html_content = f'''<!DOCTYPE html>
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
        .search-results {{
            background: #15161a;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }}
        
        @media(max-width:550px) {{
            .filmpanel {{
                width: 31.33%;
                height: 190px;
                margin: 1%;
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
            <form action="" name="ara" method="GET" onsubmit="return searchFilms(event)">
                <input type="text" id="filmSearch" placeholder="Film Ara..!" class="aramapanelyazi" oninput="resetFilmSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="filmListesiContainer">
        <div class="baslik">HDFİLMCEHENNEMİ - İLK 99 FİLM ({links_in_html} filmde link var)</div>
        <div id="filmListesi"></div>
    </div>

    <div id="searchResultsContainer" class="search-results" style="display: none;">
        <div class="baslik">ARAMA SONUÇLARI</div>
        <div id="searchResults"></div>
    </div>

    <script>
        // HTML'deki 99 film
        const htmlFilms = {json.dumps(first_99_films, ensure_ascii=False)};
        
        // Tüm filmlerin JSON linki
        const ALL_FILMS_JSON_URL = "{json_url}";
        
        // Tüm filmler (başta boş, arama yapınca yüklenecek)
        let allFilms = {{}};
        
        // Sayfa yüklendiğinde HTML'deki 99 filmi göster
        document.addEventListener('DOMContentLoaded', function() {{
            renderFilms(htmlFilms, 'filmListesi');
        }});
        
        // Filmleri ekrana bas
        function renderFilms(films, containerId) {{
            var container = document.getElementById(containerId);
            container.innerHTML = '';
            
            Object.keys(films).forEach(function(key) {{
                var film = films[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                
                // FİLME TIKLAYINCA DİREKT IFRAME AÇ
                item.onclick = function() {{ 
                    if (film.link) {{
                        // Yeni sekmede iframe aç
                        window.open(film.link, '_blank');
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
        }}
        
        // ARAMA FONKSİYONU
        async function searchFilms(event) {{
            event.preventDefault();
            
            var searchTerm = document.getElementById('filmSearch').value.toLowerCase().trim();
            
            if (!searchTerm) {{
                resetFilmSearch();
                return false;
            }}
            
            // 1. Önce HTML'deki 99 filmde ara
            var foundInHtml = {{}};
            Object.keys(htmlFilms).forEach(function(key) {{
                if (htmlFilms[key].isim.toLowerCase().includes(searchTerm)) {{
                    foundInHtml[key] = htmlFilms[key];
                }}
            }});
            
            if (Object.keys(foundInHtml).length > 0) {{
                // HTML'de bulundu, göster
                document.getElementById('filmListesiContainer').style.display = 'none';
                document.getElementById('searchResultsContainer').style.display = 'block';
                renderFilms(foundInHtml, 'searchResults');
                document.querySelector('#searchResultsContainer .baslik').textContent = 
                    `ARAMA SONUÇLARI (HTML'de bulundu: ${{Object.keys(foundInHtml).length}} film)`;
                return false;
            }}
            
            // 2. HTML'de yoksa JSON'dan yükle ve ara
            try {{
                if (Object.keys(allFilms).length === 0) {{
                    // JSON henüz yüklenmemiş, yükle
                    document.getElementById('searchResults').innerHTML = 
                        '<div class="hataekran"><i class="fas fa-spinner fa-spin"></i><div class="hatayazi">Tüm filmler yükleniyor...</div></div>';
                    
                    const response = await fetch(ALL_FILMS_JSON_URL);
                    allFilms = await response.json();
                    console.log(`✅ Tüm filmler yüklendi: ${{Object.keys(allFilms).length}} film`);
                }}
                
                // JSON'da ara
                var foundInJson = {{}};
                Object.keys(allFilms).forEach(function(key) {{
                    if (allFilms[key].isim.toLowerCase().includes(searchTerm)) {{
                        foundInJson[key] = allFilms[key];
                    }}
                }});
                
                if (Object.keys(foundInJson).length > 0) {{
                    // JSON'da bulundu, göster
                    document.getElementById('filmListesiContainer').style.display = 'none';
                    document.getElementById('searchResultsContainer').style.display = 'block';
                    renderFilms(foundInJson, 'searchResults');
                    document.querySelector('#searchResultsContainer .baslik').textContent = 
                        `ARAMA SONUÇLARI (JSON'da bulundu: ${{Object.keys(foundInJson).length}} film)`;
                }} else {{
                    // Hiçbir yerde bulunamadı
                    document.getElementById('filmListesiContainer').style.display = 'none';
                    document.getElementById('searchResultsContainer').style.display = 'block';
                    document.getElementById('searchResults').innerHTML = `
                        <div class="hataekran">
                            <i class="fas fa-search"></i>
                            <div class="hatayazi">"${{searchTerm}}" için film bulunamadı!<br>
                            Toplam ${{Object.keys(allFilms).length}} film arasından</div>
                        </div>`;
                }}
                
            }} catch (error) {{
                console.error("JSON yüklenemedi:", error);
                document.getElementById('searchResults').innerHTML = `
                    <div class="hataekran">
                        <i class="fas fa-exclamation-triangle"></i>
                        <div class="hatayazi">Filmler yüklenemedi!<br>${{error.message}}</div>
                    </div>`;
            }}
            
            return false;
        }}
        
        function resetFilmSearch() {{
            document.getElementById('filmSearch').value = '';
            document.getElementById('filmListesiContainer').style.display = 'block';
            document.getElementById('searchResultsContainer').style.display = 'none';
            renderFilms(htmlFilms, 'filmListesi');
        }}
        
        // ESC tuşu ile aramayı resetle
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                resetFilmSearch();
            }}
        }});
    </script>
</body>
</html>'''
    
    html_filename = "hdfilmcehennemi.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    html_size_kb = os.path.getsize(html_filename) / 1024
    
    print(f"\n🌐 HTML DOSYASI OLUŞTURULDU:")
    print(f"✅ Dosya Adı: {html_filename}")
    print(f"🎬 HTML'deki film sayısı: {len(first_99_films)}")
    print(f"🔗 HTML'de link olan filmler: {links_in_html}")
    print(f"💾 Boyut: {html_size_kb:.1f} KB")
    print(f"\n🎉 SİSTEM HAZIR!")
    print(f"   ✅ Link Çekme: ÇALIŞIYOR")
    print(f"   ✅ HTML'de: İlk 99 film")
    print(f"   ✅ JSON'da: Tüm {len(all_data)} film")
    print(f"   ✅ Arama: Önce HTML'de, yoksa JSON'dan getir")

if __name__ == "__main__":
    main()
