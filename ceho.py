import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def get_iframe(url):
    try:
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        iframe = soup.find('iframe', {'class': 'close'})
        return iframe.get('data-src') if iframe else "Link Yok"
    except: return "Hata"

try:
    # 970 sayfa taranabilir, test için range'i ayarla
    for sayfa in range(1, 20):
        # STRATEJİ: Site hangisine izin verirse oradan dalacağız
        denenecek_linkler = [
            f"https://www.hdfilmcehennemi.nl/category/film-izle-2/?page={sayfa}",
            f"https://www.hdfilmcehennemi.nl/kategori/film-izle-2/page/{sayfa}/",
            f"https://www.hdfilmcehennemi.nl/film-izle-2/page/{sayfa}/"
        ]
        
        film_listesi = []
        
        for link in denenecek_linkler:
            print(f"🔍 Deneniyor: {link}")
            driver.get(link)
            time.sleep(4)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Senin attığın kaynakta film linkleri 'poster' class'lı a etiketleriydi
            bulunanlar = soup.find_all('a', class_='poster')
            
            if bulunanlar:
                film_listesi = bulunanlar
                print(f"✅ Yol Bulundu! Sayfa {sayfa} üzerinden {len(bulunanlar)} film çekiliyor.")
                break
        
        if not film_listesi:
            print(f"❌ Sayfa {sayfa} için hiçbir kapı açılmadı. Engel var.")
            # Eğer ilk sayfada bile bulamazsa site yapısı kökten değişmiş olabilir
            if sayfa == 1: break 
            continue

        # Sayfa içindeki filmleri tara
        for film in film_listesi:
            f_adi = film.get('title') or "İsimsiz Film"
            f_link = film.get('href')
            
            if f_link:
                print(f"🎬 {f_adi}")
                # Mevcut sekmede git-gel yapıyoruz (Oturum ölmesin diye)
                v_link = get_iframe(f_link)
                print(f"🔗 {v_link}")
                print("-" * 30)

finally:
    driver.quit()
    
