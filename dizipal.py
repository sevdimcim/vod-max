# DiziPal - Tüm Sayfaları Çeken Versiyon (Düzeltilmiş Sayfalama)
# Orjinal kod: @keyiflerolsun | @KekikAkademi

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os

class DiziPal:
    def __init__(self):
        self.name = "DiziPal"
        self.main_url = "https://dizipal.bar"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.kategoriler = {
            f"{self.main_url}/kategori/aile/": "Aile",
            f"{self.main_url}/kategori/aksiyon/": "Aksiyon",
            f"{self.main_url}/kategori/animasyon/": "Animasyon",
            f"{self.main_url}/kategori/belgesel/": "Belgesel",
            f"{self.main_url}/kategori/bilim-kurgu/": "Bilim Kurgu",
            f"{self.main_url}/kategori/dram/": "Dram",
            f"{self.main_url}/kategori/fantastik/": "Fantastik",
            f"{self.main_url}/kategori/gerilim/": "Gerilim",
            f"{self.main_url}/kategori/gizem/": "Gizem",
            f"{self.main_url}/kategori/komedi/": "Komedi",
            f"{self.main_url}/kategori/korku/": "Korku",
            f"{self.main_url}/kategori/macera/": "Macera",
            f"{self.main_url}/kategori/muzik/": "Müzik",
            f"{self.main_url}/kategori/romantik/": "Romantik",
            f"{self.main_url}/kategori/savas/": "Savaş",
            f"{self.main_url}/kategori/suc/": "Suç",
            f"{self.main_url}/kategori/tarih/": "Tarih",
            f"{self.main_url}/kategori/vahsi-bati/": "Vahşi Batı",
            f"{self.main_url}/kategori/yerli/": "Yerli",
        }
    
    def fix_url(self, url):
        if not url: return ""
        if url.startswith("http"): return url
        if url.startswith("//"): return f"https:{url}"
        return f"{self.main_url}{url}"
    
    def get_soup(self, url):
        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Hata: {e}")
            return None
    
    def toplam_sayfa_bul(self, kategori_url):
        """Kategorideki toplam sayfa sayısını bul - DÜZELTİLDİ"""
        soup = self.get_soup(kategori_url)
        if not soup:
            return 1
        
        # Sayfalama linklerini bul - son sayfa linkine bak
        sayfalama = soup.select("a.page-numbers")
        en_buyuk = 1
        
        for link in sayfalama:
            href = link.get('href', '')
            # /page/X/ formatını yakala
            match = re.search(r'/page/(\d+)/', href)
            if match:
                sayfa_no = int(match.group(1))
                if sayfa_no > en_buyuk:
                    en_buyuk = sayfa_no
        
        # Eğer hiç sayfalama linki yoksa ama "Sonraki" varsa, tahmin et
        if en_buyuk == 1:
            sonraki = soup.select_one("a.next.page-numbers")
            if sonraki:
                # En az 2 sayfa var
                en_buyuk = 2
                
                # Linkten sayı çekmeyi dene
                href = sonraki.get('href', '')
                match = re.search(r'/page/(\d+)/', href)
                if match:
                    en_buyuk = int(match.group(1))
        
        # Alternatif: sayfa numaralarının metinlerine bak
        for link in sayfalama:
            try:
                sayi = int(link.text.strip())
                if sayi > en_buyuk:
                    en_buyuk = sayi
            except:
                pass
        
        # Emin olmak için 50'ye kadar dene (site mantığına göre)
        if en_buyuk <= 2:
            # Test et: 5. sayfa var mı?
            test_url = f"{kategori_url}page/5/"
            try:
                test_resp = self.session.get(test_url, timeout=5)
                if test_resp.status_code == 200:
                    en_buyuk = 10  # En az 10 sayfa var
                    
                    # Daha da ileri git, 20'yi dene
                    test_url = f"{kategori_url}page/20/"
                    test_resp = self.session.get(test_url, timeout=5)
                    if test_resp.status_code == 200:
                        en_buyuk = 30
            except:
                pass
        
        print(f"    Toplam {en_buyuk} sayfa bulundu")
        return en_buyuk
    
    def ana_sayfa(self, sayfa=1, kategori_url=None, kategori_adi=None):
        if not kategori_url:
            kategori_url = list(self.kategoriler.keys())[0]
            kategori_adi = list(self.kategoriler.values())[0]
        
        # Sayfa URL'sini oluştur
        if sayfa == 1:
            url = kategori_url
        else:
            url = f"{kategori_url}page/{sayfa}/"
        
        soup = self.get_soup(url)
        
        if not soup:
            return []
        
        sonuclar = []
        for veri in soup.select("div.grid div.post-item, article"):
            title_elem = veri.select_one("a")
            if title_elem:
                title = title_elem.get('title', '') or title_elem.text.strip()
                href = title_elem.get('href', '')
                
                if title and href:
                    sonuclar.append({
                        'kategori': kategori_adi,
                        'baslik': title,
                        'url': self.fix_url(href)
                    })
        
        return sonuclar
    
    def _embed_link_al(self, soup):
        iframe = soup.select_one("div.video-player-area iframe")
        if not iframe:
            iframe = soup.select_one("div.responsive-player iframe")
        if not iframe:
            iframe = soup.select_one("iframe")
        
        if iframe:
            src = iframe.get('src') or iframe.get('data-src')
            if src:
                return self.fix_url(src)
        return None
    
    def _thumbnail_al(self, soup, html_text=None):
        """Sayfadan thumbnailUrl'i bul (JSON-LD içinden)"""
        # Önce JSON-LD'den bul
        if html_text:
            pattern = r'"thumbnailUrl":"(https:[^"]+)"'
            match = re.search(pattern, html_text)
            if match:
                return match.group(1)
        
        # meta tag'lerden bul
        meta_img = soup.select_one("meta[property='og:image']")
        if meta_img:
            return meta_img.get('content', '')
        
        # link tag'lerinden bul
        link_img = soup.select_one("link[rel='image_src']")
        if link_img:
            return link_img.get('href', '')
        
        return None
    
    def tum_filmleri_topla(self, max_sayfa_limiti=50):
        """Tüm kategorilerdeki TÜM sayfaları tara"""
        print("="*60)
        print("🎬 DİZİPAL - TÜM FİLMLER TARANIYOR")
        print("="*60)
        
        tum_filmler = {}
        film_id = 1
        toplam_kategori = len(self.kategoriler)
        kategori_sayac = 0
        
        for kategori_url, kategori_adi in self.kategoriler.items():
            kategori_sayac += 1
            print(f"\n[{kategori_sayac}/{toplam_kategori}] 📁 {kategori_adi}")
            
            # Toplam sayfa sayısını bul
            toplam_sayfa = self.toplam_sayfa_bul(kategori_url)
            
            # Maksimum limiti aşma
            if toplam_sayfa > max_sayfa_limiti:
                print(f"   ⚠️  {toplam_sayfa} sayfa var ama {max_sayfa_limiti} ile sınırlandırıldı")
                toplam_sayfa = max_sayfa_limiti
            
            print(f"   {toplam_sayfa} sayfa taranacak")
            
            kategori_film = 0
            
            for sayfa in range(1, toplam_sayfa + 1):
                print(f"   Sayfa {sayfa}/{toplam_sayfa}...", end=" ")
                
                sonuclar = self.ana_sayfa(sayfa, kategori_url, kategori_adi)
                print(f"{len(sonuclar)} film", end="")
                
                if len(sonuclar) == 0:
                    print(" (boş, durduruluyor)")
                    break
                
                print(" -> ", end="")
                
                for film in sonuclar:
                    print(".", end="", flush=True)
                    
                    try:
                        # Film sayfasına git
                        response = self.session.get(film['url'], timeout=10)
                        response.encoding = 'utf-8'
                        html_text = response.text
                        soup = BeautifulSoup(html_text, 'html.parser')
                        
                        # Embed linkini al
                        embed = self._embed_link_al(soup)
                        
                        # Thumbnail/afişi al
                        poster = self._thumbnail_al(soup, html_text)
                        
                        # Eğer poster bulunamadıysa alternatif dene
                        if not poster:
                            meta_img = soup.select_one("meta[property='og:image']")
                            if meta_img:
                                poster = meta_img.get('content', '')
                        
                        tum_filmler[str(film_id)] = {
                            'isim': film['baslik'],
                            'resim': self.fix_url(poster) if poster else "",
                            'link': film['url'],
                            'embed': embed if embed else "",
                            'kategori': film['kategori']
                        }
                        film_id += 1
                        kategori_film += 1
                        
                    except Exception as e:
                        print("X", end="", flush=True)
                    
                    time.sleep(0.3)  # Filmler arası bekle
                
                print(f" ✓ (toplam {kategori_film})")
                time.sleep(1)  # Sayfalar arası bekle
            
            print(f"   ✅ {kategori_adi}: {kategori_film} film toplandı")
        
        print(f"\n{'='*60}")
        print(f"✅ TOPLAM {len(tum_filmler)} FİLM TOPLANDI")
        print(f"{'='*60}")
        return tum_filmler
    
    def html_olustur(self, filmler):
        """Görsel HTML çıktısı oluştur (TV uyumlu)"""
        print("\n📝 HTML oluşturuluyor...")
        
        # Filmleri JSON'a çevir
        filmler_json = {}
        for id, film in filmler.items():
            filmler_json[id] = {
                'isim': film['isim'] or '',
                'resim': film['resim'] or '',
                'link': film['link'] or '',
                'embed': film['embed'] or '',
                'kategori': film['kategori'] or 'Diğer'
            }
        
        filmler_str = json.dumps(filmler_json, ensure_ascii=False)
        
        html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>DiziPal TV Arşiv - {len(filmler)} Film</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* TV ve kumanda uyumu */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
            outline: none;
        }}
        
        body {{
            background: #0a0c0f;
            font-family: 'Segoe UI', Roboto, sans-serif;
            color: #fff;
            padding-bottom: 30px;
        }}
        
        /* Odaklanma efekti - kumanda için */
        .focusable:focus,
        .category-btn:focus,
        .film-card:focus,
        .load-more-btn:focus {{
            transform: scale(1.02);
            border: 3px solid #ffd700 !important;
            box-shadow: 0 0 20px #ffd700;
            outline: none;
            z-index: 10;
        }}
        
        .header {{
            background: #15161a;
            padding: 15px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 2px solid #572aa7;
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }}
        
        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .logo i {{
            font-size: 30px;
            color: #572aa7;
        }}
        
        .logo span {{
            font-size: 24px;
            font-weight: bold;
        }}
        
        .search-box {{
            flex: 1;
            max-width: 500px;
            display: flex;
            gap: 10px;
        }}
        
        .search-box input {{
            flex: 1;
            height: 45px;
            background: #1e1f26;
            border: 1px solid #323442;
            border-radius: 8px;
            padding: 0 15px;
            color: white;
            font-size: 16px;
        }}
        
        .search-box input:focus {{
            border-color: #ffd700;
            box-shadow: 0 0 10px #ffd700;
        }}
        
        .search-box button {{
            width: 45px;
            height: 45px;
            background: #572aa7;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 18px;
            cursor: pointer;
            transition: 0.3s;
        }}
        
        .search-box button:focus {{
            background: #ffd700;
            color: #000;
        }}
        
        .stats {{
            color: #888;
            font-size: 14px;
        }}
        
        .categories {{
            background: #0f1015;
            padding: 15px 20px;
            border-bottom: 1px solid #323442;
            overflow-x: auto;
            white-space: nowrap;
            -webkit-overflow-scrolling: touch;
        }}
        
        .categories::-webkit-scrollbar {{
            height: 5px;
        }}
        
        .categories::-webkit-scrollbar-thumb {{
            background: #572aa7;
            border-radius: 5px;
        }}
        
        .category-btn {{
            display: inline-block;
            padding: 10px 25px;
            margin-right: 10px;
            background: #1e1f26;
            border: 2px solid #323442;
            border-radius: 30px;
            color: #fff;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
            text-decoration: none;
        }}
        
        .category-btn.active {{
            background: #572aa7;
            border-color: #572aa7;
        }}
        
        .category-btn:hover {{
            background: #2a2b33;
        }}
        
        .main {{
            max-width: 1400px;
            margin: 20px auto;
            padding: 0 20px;
        }}
        
        .film-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .film-card {{
            background: #15161a;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid #323442;
            cursor: pointer;
            transition: 0.3s;
            position: relative;
            aspect-ratio: 2/3;
        }}
        
        .film-card:hover,
        .film-card:focus {{
            transform: translateY(-5px);
            border-color: #ffd700;
            box-shadow: 0 5px 20px #ffd700;
        }}
        
        .film-card img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .film-title {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 40px 10px 10px;
            background: linear-gradient(to top, #000, transparent);
            color: white;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .category-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: #572aa7;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
        }}
        
        .load-more {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .load-more-btn {{
            background: #572aa7;
            color: white;
            border: none;
            padding: 15px 50px;
            border-radius: 40px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
            border: 2px solid #572aa7;
        }}
        
        .load-more-btn:hover,
        .load-more-btn:focus {{
            background: #ffd700;
            color: #000;
            border-color: #ffd700;
        }}
        
        .load-more-btn:disabled {{
            background: #323442;
            border-color: #323442;
            cursor: not-allowed;
        }}
        
        .no-result {{
            text-align: center;
            padding: 50px;
            color: #888;
            font-size: 18px;
        }}
        
        /* TV için büyük ekran */
        @media (min-width: 1200px) {{
            .film-grid {{
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 25px;
            }}
        }}
        
        /* Mobil için */
        @media (max-width: 768px) {{
            .film-grid {{
                grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                gap: 10px;
            }}
            
            .logo span {{
                font-size: 18px;
            }}
            
            .category-btn {{
                padding: 8px 16px;
                font-size: 13px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <i class="fas fa-film"></i>
                <span>DiziPal TV</span>
            </div>
            <div class="search-box">
                <input type="text" id="searchInput" class="focusable" placeholder="Film ara...">
                <button class="focusable" onclick="searchFilms()"><i class="fas fa-search"></i></button>
            </div>
            <div class="stats" id="stats">
                <i class="fas fa-database"></i> <span id="filmCount">{len(filmler)}</span> Film
            </div>
        </div>
    </div>
    
    <div class="categories" id="categories"></div>
    
    <div class="main">
        <div class="film-grid" id="filmGrid"></div>
        <div class="load-more">
            <button class="load-more-btn focusable" id="loadMoreBtn" onclick="loadMore()">Daha Fazla Göster</button>
        </div>
    </div>
    
    <script>
        // Film veritabanı
        var filmDatabase = {filmler_str};
        
        // Kategorileri hesapla
        var categories = {{}};
        var filmList = Object.values(filmDatabase);
        for (var i = 0; i < filmList.length; i++) {{
            var film = filmList[i];
            if (!categories[film.kategori]) {{
                categories[film.kategori] = 0;
            }}
            categories[film.kategori]++;
        }}
        
        // Kategori butonlarını oluştur
        var categoriesHtml = '<button class="category-btn focusable active" onclick="filterCategory(\\'all\\')">Tümü (' + Object.keys(filmDatabase).length + ')</button>';
        var catNames = Object.keys(categories).sort();
        for (var i = 0; i < catNames.length; i++) {{
            var cat = catNames[i];
            categoriesHtml += '<button class="category-btn focusable" onclick="filterCategory(\\'' + cat + '\\')">' + cat + ' (' + categories[cat] + ')</button>';
        }}
        document.getElementById('categories').innerHTML = categoriesHtml;
        
        // Global değişkenler
        var currentPage = 1;
        var itemsPerPage = 50;
        var currentCategory = 'all';
        var currentSearch = '';
        var filteredFilms = [];
        var allFilms = Object.values(filmDatabase);
        
        function filterFilms() {{
            var films = allFilms;
            
            // Kategori filtresi
            if (currentCategory !== 'all') {{
                var temp = [];
                for (var i = 0; i < films.length; i++) {{
                    if (films[i].kategori === currentCategory) {{
                        temp.push(films[i]);
                    }}
                }}
                films = temp;
            }}
            
            // Arama filtresi
            if (currentSearch && currentSearch.length > 0) {{
                var search = currentSearch.toLowerCase();
                var temp = [];
                for (var i = 0; i < films.length; i++) {{
                    if (films[i].isim.toLowerCase().indexOf(search) > -1) {{
                        temp.push(films[i]);
                    }}
                }}
                films = temp;
            }}
            
            filteredFilms = films;
            currentPage = 1;
            document.getElementById('filmGrid').innerHTML = '';
            renderFilms();
            document.getElementById('filmCount').innerHTML = filteredFilms.length;
        }}
        
        function renderFilms() {{
            var grid = document.getElementById('filmGrid');
            var start = 0;
            var end = currentPage * itemsPerPage;
            
            for (var i = 0; i < filteredFilms.length; i++) {{
                if (i >= start && i < end) {{
                    var film = filteredFilms[i];
                    var card = document.createElement('div');
                    card.className = 'film-card focusable';
                    card.setAttribute('tabindex', '0');
                    
                    // Tıklama olayı
                    card.onclick = (function(embed, link) {{
                        return function() {{
                            if (embed && embed.length > 0) {{
                                window.open(embed, '_blank');
                            }} else if (link && link.length > 0) {{
                                window.open(link, '_blank');
                            }}
                        }};
                    }})(film.embed, film.link);
                    
                    // Enter tuşu ile tıklama
                    card.onkeydown = function(e) {{
                        if (e.key === 'Enter' || e.keyCode === 13) {{
                            this.click();
                        }}
                    }};
                    
                    // Afiş URL'si
                    var imgSrc = film.resim;
                    
                    // Eğer resim yoksa veya hatalıysa placeholder
                    if (!imgSrc || imgSrc.length === 0 || imgSrc.indexOf('no-thumbnail') > -1) {{
                        imgSrc = 'https://via.placeholder.com/300x450/1e1f26/572aa7?text=' + encodeURIComponent(film.isim);
                    }}
                    
                    card.innerHTML = '<img src="' + imgSrc + '" loading="lazy" onerror="this.src=\\'https://via.placeholder.com/300x450/1e1f26/572aa7?text=No+Image\\'">' +
                                   '<div class="film-title">' + film.isim + '</div>' +
                                   '<div class="category-badge">' + film.kategori + '</div>';
                    
                    grid.appendChild(card);
                }}
            }}
            
            // Daha fazla butonu
            var loadMoreBtn = document.getElementById('loadMoreBtn');
            if (end >= filteredFilms.length) {{
                loadMoreBtn.disabled = true;
            }} else {{
                loadMoreBtn.disabled = false;
            }}
        }}
        
        function loadMore() {{
            currentPage++;
            renderFilms();
        }}
        
        function filterCategory(category) {{
            currentCategory = category;
            
            // Aktif butonu güncelle
            var btns = document.querySelectorAll('.category-btn');
            for (var i = 0; i < btns.length; i++) {{
                btns[i].classList.remove('active');
            }}
            event.target.classList.add('active');
            
            filterFilms();
        }}
        
        function searchFilms() {{
            currentSearch = document.getElementById('searchInput').value;
            
            // Kategori butonlarını sıfırla
            currentCategory = 'all';
            var btns = document.querySelectorAll('.category-btn');
            for (var i = 0; i < btns.length; i++) {{
                btns[i].classList.remove('active');
            }}
            if (btns.length > 0) {{
                btns[0].classList.add('active');
            }}
            
            filterFilms();
        }}
        
        // Arama kutusu değiştiğinde
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            searchFilms();
        }});
        
        // Enter tuşu ile arama
        document.getElementById('searchInput').addEventListener('keyup', function(e) {{
            if (e.key === 'Enter') {{
                searchFilms();
            }}
        }});
        
        // İlk yükleme
        filterFilms();
        
        // TV/kumanda için otomatik odaklama
        setTimeout(function() {{
            var firstCard = document.querySelector('.film-card');
            if (firstCard) {{
                firstCard.focus();
            }}
        }}, 500);
    </script>
</body>
</html>'''
        
        with open('dizipal_tv.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        with open('dizipal.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ HTML dosyaları oluşturuldu")
        print(f"📁 dizipal.html ve dizipal_tv.html")
        
        # İstatistikler
        resimli = sum(1 for f in filmler.values() if f['resim'] and 'no-thumbnail' not in f['resim'])
        embedli = sum(1 for f in filmler.values() if f['embed'])
        
        print(f"\n📊 İSTATİSTİKLER:")
        print(f"   Toplam film: {len(filmler)}")
        print(f"   Afişli film: {resimli}")
        print(f"   Embed linkli: {embedli}")
        
        # Kategori dağılımı
        print(f"\n📊 KATEGORİ DAĞILIMI:")
        kat_say = {}
        for f in filmler.values():
            kat = f['kategori']
            kat_say[kat] = kat_say.get(kat, 0) + 1
        
        for kat, say in sorted(kat_say.items()):
            print(f"   {kat}: {say} film")

# Ana çalıştırma
if __name__ == "__main__":
    print("="*60)
    print("🎬 DİZİPAL - TÜM SAYFALARI ÇEKEN VERSİYON")
    print("="*60)
    
    dizi = DiziPal()
    
    print("\n⏳ Bu işlem UZUN SÜREBİLİR! (Tüm kategoriler, tüm sayfalar)")
    print("   Her film ayrı ayrı taranıyor...\n")
    
    basla = time.time()
    # max_sayfa_limiti=50 diyerek en fazla 50 sayfa tarar (sonsuz döngüyü engeller)
    filmler = dizi.tum_filmleri_topla(max_sayfa_limiti=50)
    bitis = time.time()
    
    if filmler:
        dizi.html_olustur(filmler)
        
        sure = bitis - basla
        saat = int(sure // 3600)
        dakika = int((sure % 3600) // 60)
        saniye = int(sure % 60)
        
        print("\n" + "="*60)
        print("✅ İŞLEM TAMAM!")
        print(f"⏱️  Geçen süre: {saat} saat {dakika} dakika {saniye} saniye")
        print(f"📊 Toplam {len(filmler)} film bulundu")
        print("="*60)
        print("\n📁 dizipal.html dosyasını aç, izle keyfine bak")
    else:
        print("❌ Film bulunamadı!")
