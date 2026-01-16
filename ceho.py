import requests
from bs4 import BeautifulSoup
import time

# --- AYARLAR ---
# Site bu bilgileri görmezse 404 veriyor
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest", # 'Ben bir AJAX isteğiyim' diyoruz
    "Referer": "https://www.hdfilmcehennemi.nl/category/film-izle-2/", # 'Kategori sayfasından geliyorum' diyoruz
    "Accept": "*/*"
}

def video_linki_bul(film_url):
    """Film sayfasına girip o meşhur iframe linkini çeker"""
    try:
        # Film sayfasına giderken normal header kullanıyoruz
        r = requests.get(film_url, headers={"User-Agent": headers["User-Agent"]}, timeout=10)
        s = BeautifulSoup(r.text, 'html.parser')
        iframe = s.find('iframe', {'class': 'close'})
        return iframe.get('data-src') if iframe else "Link Bulunamadı"
    except:
        return "Bağlantı Hatası"

# --- ANA DÖNGÜ ---
# 1'den 970'e kadar (veya kaç sayfa istersen)
for sayfa_no in range(1, 10): 
    # Senin yakaladığın o gizli yükleme linki:
    load_url = f"https://www.hdfilmcehennemi.nl/load/page/{sayfa_no}/categories/film-izle-2/"
    
    print(f"\n🚀 {sayfa_no}. SAYFA ÇEKİLİYOR: {load_url}")
    
    try:
        # requests.get ile o gizli linke 'X-Requested-With' ile sızıyoruz
        response = requests.get(load_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Site cevap vermedi. Kod: {response.status_code}")
            continue
            
        soup = BeautifulSoup(response.text, 'html.parser')
        filmler = soup.find_all('a', class_='poster')
        
        if not filmler:
            print("⚠️ Bu sayfada film bulunamadı.")
            break

        for film in filmler:
            f_adi = film.get('title')
            f_link = film.get('href')
            
            if f_link:
                print(f"🎬 {f_adi}")
                v_link = video_linki_bul(f_link)
                print(f"🔗 {v_link}")
                print("-" * 30)
                
                # Saniyede 1 film çekerek ban riskini sıfıra indiriyoruz
                time.sleep(0.5)

    except Exception as e:
        print(f"💥 Sayfa {sayfa_no} taranırken hata: {e}")
        time.sleep(2)

print("\n✅ İşlem tamamlandı!")
