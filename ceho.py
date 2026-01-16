import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- TARAYICI AYARLARI ---
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def iframe_cek(film_link):
    """Film sayfasına girer ve iframe linkini alır"""
    # Mevcut sekmeyi kullan (Hız için yeni sekme açmıyoruz)
    try:
        driver.get(film_link)
        time.sleep(3) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        iframe = soup.find('iframe', {'class': 'close'})
        return iframe.get('data-src') if iframe else "Iframe Bulunamadı"
    except:
        return "Hata"

# --- ANA DÖNGÜ ---
try:
    # 1'den 10. sayfaya kadar zorla (İstediğin kadar artır)
    for sayfa_no in range(1, 11):
        # DİKKAT: Site normalde ?page= kabul etmiyor gibi görünebilir 
        # ama Selenium ile direkt gidince genellikle veriyi döküyor.
        target_url = f"https://www.hdfilmcehennemi.nl/category/film-izle-2/?page={sayfa_no}"
        
        print(f"\n🚀 SAYFA {sayfa_no} ZORLANIYOR: {target_url}")
        driver.get(target_url)
        time.sleep(5) # Sayfanın yüklenmesi için bekle
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        film_listesi = soup.find_all('a', class_='poster')
        
        # Eğer sayfa boş gelirse bir de şu yöntemi dene (Slashlı yapı)
        if not film_listesi:
            print(f"⚠️ Sayfa {sayfa_no} ?page ile açılmadı, alternatif deneniyor...")
            target_url = f"https://www.hdfilmcehennemi.nl/category/film-izle-2/page/{sayfa_no}/"
            driver.get(target_url)
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            film_listesi = soup.find_all('a', class_='poster')

        if not film_listesi:
            print(f"❌ Sayfa {sayfa_no} hiçbir şekilde okunamadı. Durduruluyor.")
            break

        # Filmleri işle (Linkleri sakla çünkü iframe_cek sekmeyi değiştirecek)
        filmler = []
        for f in film_listesi:
            filmler.append({'adi': f.get('title'), 'link': f.get('href')})

        for film in filmler:
            print(f"🎬 {film['adi']}")
            v_link = iframe_cek(film['link'])
            print(f"🔗 {v_link}")
            print("-" * 30)

finally:
    print("\n✅ Tarama tamamlandı.")
    driver.quit()
