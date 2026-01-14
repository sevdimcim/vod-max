import requests
from bs4 import BeautifulSoup
import json
import time
import re

# Web sitesi kök adresi
BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"Hata oluştu ({url}): {e}")
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
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return int(match.group(1))
    return 9999

def main():
    print("Diziler ve Bölümler taranıyor... (Sadece Bölüm Numarası Modu)")
    soup = get_soup(f"{BASE_URL}/diziler")
    if not soup:
        return

    diziler_data = {}
    dizi_kutulari = soup.find_all("div", attrs={"data-name": "box-type6"})
    
    print(f"Toplam {len(dizi_kutulari)} adet dizi bulundu.")

    for kutu in dizi_kutulari:
        try:
            link_tag = kutu.find("a", class_="group")
            if not link_tag:
                continue
                
            dizi_link = BASE_URL + link_tag.get("href")
            dizi_adi = link_tag.get("title")
            dizi_id = slugify(dizi_adi)
            
            # Afiş Linki
            img_tag = kutu.find("img")
            poster_url = img_tag.get("src") if img_tag else ""
            if img_tag and img_tag.get("data-src"):
                poster_url = img_tag.get("data-src")
            if "?" in poster_url:
                poster_url = poster_url.split("?")[0]

            print(f"--> İşleniyor: {dizi_adi}")

            # Son Bölüm Tespiti
            son_bolum_url = None
            son_bolum_span = kutu.find("span", string="Son Bölüm")
            if son_bolum_span:
                parent_a = son_bolum_span.find_parent("a")
                if parent_a and parent_a.get("href"):
                    href = parent_a.get("href")
                    if "/tum_bolumler/" in href:
                        son_bolum_url = BASE_URL + href

            # Dizi Detay Sayfasına Git
            detail_soup = get_soup(dizi_link)
            if not detail_soup:
                continue

            raw_links = []
            seen_urls = set()

            # 1. YÖNTEM: Dropdown
            options = detail_soup.find_all("option", attrs={"data-href": True})
            for opt in options:
                rel_link = opt.get("data-href")
                bolum_adi = opt.text.strip()
                if "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": bolum_adi, "page_url": full})
                        seen_urls.add(full)

            # 2. YÖNTEM: Son Bölüm Ekleme
            if son_bolum_url and son_bolum_url not in seen_urls:
                raw_links.append({"ad": "Yeni Bölüm", "page_url": son_bolum_url})
                seen_urls.add(son_bolum_url)

            print(f"    - {len(raw_links)} adet sayfa linki bulundu. Videolar çekiliyor...")

            final_bolumler = []
            
            # Linkleri gez ve Video çek
            for item in raw_links: 
                video_soup = get_soup(item["page_url"])
                if not video_soup:
                    continue
                
                # Bölüm adını title'dan çekip düzeltelim
                page_title = video_soup.title.string if video_soup.title else item["ad"]
                clean_name = page_title.replace("İzle", "").replace("Show TV", "").strip()
                
                # --- DEĞİŞİKLİK BURADA BAŞLIYOR ---
                # Bölüm numarasını çekiyoruz
                ep_num = extract_episode_number(clean_name)
                
                if ep_num != 9999:
                    # Eğer bir sayı bulduysak, ismi sadece "X. Bölüm" yapıyoruz
                    display_name = f"{ep_num}. Bölüm"
                else:
                    # Sayı bulamadıysak (Örn: "Final", "Özel Bölüm") orijinal ismi kullanıyoruz
                    display_name = clean_name
                # --- DEĞİŞİKLİK BURADA BİTİYOR ---

                # Video JSON verisi
                video_div = video_soup.find("div", class_="hope-video")
                if video_div and video_div.get("data-hope-video"):
                    try:
                        v_data = json.loads(video_div.get("data-hope-video"))
                        video_url = ""
                        format_type = ""

                        if "media" in v_data:
                            media = v_data["media"]
                            if "m3u8" in media and len(media["m3u8"]) > 0:
                                video_url = media["m3u8"][0]["src"]
                                format_type = "M3U8"
                            elif "mp4" in media and len(media["mp4"]) > 0:
                                video_url = media["mp4"][0]["src"]
                                format_type = "MP4"
                        
                        if video_url:
                            video_url = video_url.replace("//ht/", "/ht/").replace("com//", "com/")
                            
                            final_bolumler.append({
                                "ad": display_name,  # Artık burada kısa isim var
                                "link": video_url,
                                "episode_num": ep_num
                            })
                            print(f"      + {display_name} [{format_type}] OK")
                        else:
                            print(f"      - {display_name} Video Kaynağı Bulunamadı.")

                    except Exception as e:
                        print(f"      ! Video JSON hatası: {e}")
                
                time.sleep(0.05) 

            # SIRALAMA
            if final_bolumler:
                final_bolumler = sorted(final_bolumler, key=lambda x: x['episode_num'])
                cleaned_final = [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]

                diziler_data[dizi_id] = {
                    "resim": poster_url,
                    "bolumler": cleaned_final
                }

        except Exception as e:
            print(f"Hata: {e}")

    create_html_file(diziler_data)

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <title>TITAN TV YERLİ VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        *:not(input):not(textarea) {{ -moz-user-select: none; -webkit-user-select: none; user-select: none }}
        body {{ margin: 0; padding: 0; background: #00040d; font-family: sans-serif; font-size: 15px; color: #fff; }}
        .filmpaneldis {{ background: #15161a; width: 100%; margin: 20px auto; overflow: hidden; padding: 10px 5px; box-sizing: border-box; }}
        .baslik {{ width: 96%; color: #fff; padding: 15px 10px; box-sizing: border-box; font-size: 18px; }}
        .filmpanel {{ width: 12%; height: 200px; background: #15161a; float: left; margin: 1.14%; border-radius: 15px; border: 1px solid #323442; cursor: pointer; position: relative; overflow: hidden; transition: 0.3s; }}
        .filmpanel:hover {{ border: 3px solid #572aa7; }}
        .filmresim {{ width: 100%; height: 100%; }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; transition: 0.4s; }}
        .filmpanel:hover .filmresim img {{ transform: scale(1.1); }}
        .filmisimpanel {{ width: 100%; position: absolute; bottom: 0; background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.9)); padding: 20px 5px 5px 5px; box-sizing: border-box; }}
        .filmisim {{ width: 100%; font-size: 14px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff; }}
        
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; box-sizing: border-box; }}
        .aramapanelsol {{ float: left; display: flex; align-items: center; }}
        .aramapanelsag {{ float: right; }}
        .logo img {{ height: 40px; }}
        .logoisim {{ margin-left: 10px; font-weight: bold; font-size: 18px; }}
        .aramapanelyazi {{ height: 40px; padding: 0 10px; border: 1px solid #ccc; width: 200px; }}
        .aramapanelbuton {{ height: 40px; width: 60px; background: #572aa7; border: none; color: #fff; cursor: pointer; }}
        
        .hidden {{ display: none; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; display: inline-block; margin: 10px; }}
        
        .playerpanel {{ width: 100%; height: 100vh; position: fixed; top: 0; left: 0; background: #000; z-index: 9999; display: none; flex-direction: column; }}
        #main-player {{ width: 100%; height: 100%; }}
        #bradmax-iframe {{ width: 100%; height: 100%; border: none; }}
        .player-geri-btn {{ position: absolute; top: 20px; left: 20px; z-index: 10000; background: #572aa7; color: #fff; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}

        @media(max-width:550px) {{
            .filmpanel {{ width: 31.33%; height: 190px; margin: 1%; }}
            .aramapanelyazi {{ width: 120px; }}
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
            <input type="text" id="seriesSearch" placeholder="Dizi Ara..." class="aramapanelyazi" oninput="searchSeries()">
        </div>
    </div>

    <div id="diziListesiContainer" class="filmpaneldis">
        <div class="baslik">YERLİ DİZİLER VOD BÖLÜM</div>
    </div>

    <div id="bolumler" class="hidden">
        <div class="geri-btn" onclick="geriDon()">Geri</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">Kapat</div>
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
                item.innerHTML = `<div class="filmresim"><img src="${{dizi.resim}}"></div><div class="filmisimpanel"><div class="filmisim">${{key.replace(/-/g, ' ').toUpperCase()}}</div></div>`;
                container.appendChild(item);
            }});
            
            // Eğer URL'de hash varsa durumu kontrol et (Geri tuşu desteği için basit kontrol)
            if(window.location.hash.includes('bolumler-')) {{
                 // Basit reload senaryosu için ana sayfaya atar
                 window.location.hash = '';
            }}
        }});

        function showBolumler(diziID) {{
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            
            if (diziler[diziID]) {{
                diziler[diziID].bolumler.forEach(function(bolum) {{
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    // Bölüm adı artık kısa (Örn: 55. Bölüm) olarak geliyor
                    item.innerHTML = `<div class="filmresim"><img src="${{diziler[diziID].resim}}"></div><div class="filmisimpanel"><div class="filmisim">${{bolum.ad}}</div></div>`;
                    item.onclick = function() {{ showPlayer(bolum.link); }};
                    listContainer.appendChild(item);
                }});
            }}
            
            document.getElementById("diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            window.location.hash = 'bolumler-' + diziID;
        }}

        function showPlayer(streamUrl) {{
            document.getElementById("playerpanel").style.display = "flex"; 
            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            document.getElementById("main-player").innerHTML = `<iframe id="bradmax-iframe" src="${{fullUrl}}" allowfullscreen></iframe>`;
        }}

        function geriPlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("main-player").innerHTML = "";
        }}

        function geriDon() {{
            document.getElementById("diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            window.location.hash = '';
        }}

        function searchSeries() {{
            var query = document.getElementById('seriesSearch').value.toLowerCase();
            var series = document.querySelectorAll('#diziListesiContainer .filmpanel');
            series.forEach(function(serie) {{
                var title = serie.querySelector('.filmisim').textContent.toLowerCase();
                serie.style.display = title.includes(query) ? "block" : "none";
            }});
        }}
    </script>
</body>
</html>"""
    
    with open("show.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("show.html dosyası başarıyla oluşturuldu!")

if __name__ == "__main__":
    main()
