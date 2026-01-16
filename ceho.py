import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- TARAYICI AYARLARI ---
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 30) # Bekleme süresini 30 saniyeye çıkardım

def iframe_cek(film_link):
    """Film sayfasına girer ve iframe linkini alır"""
    try:
        driver.execute_script(f"window.open('{film_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(4) # Sayfanın tam oturması için
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        iframe = soup.find('iframe', {'class': 'close'})
        res = iframe.get('data-src') if iframe else "Iframe Bulunamadı"
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return res
    except:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return "Hata"

# İşlenen filmleri takip etmek için bir liste (Aynı filmleri tekrar çekmesin)
islenen_linkler = set()

try:
    print("🚀 Bot Başlatıldı...")
    driver.get("https://www.hdfilmcehennemi.nl/category/film-izle-2/")
    
    for sayfa in range(1, 15): # 15 sayfa dene bakalım
        print(f"\n--- 📄 ŞU AN SAYFA {sayfa} İÇERİĞİ ÇEKİLİYOR ---")
        
        # Sayfadaki mevcut tüm posterleri çek
        time.sleep(5) # Yeni içeriklerin gelmesi için bekle
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        film_listesi = soup.find_all('a', class_='poster')

        yeni_film_var_mi = False
        for film in film_listesi:
            link = film.get('href')
            adi = film.get('title')
            
            if link not in islenen_linkler:
                print(f"🎬 {adi}")
                v_link = iframe_cek(link)
                print(f"🔗 {v_link}")
                print("-" * 30)
                islenen_linkler.add(link)
                yeni_film_var_mi = True

        # --- SONRAKİ SAYFAYA GEÇİŞ KISMI ---
        try:
            print(f"⏭️ {sayfa}. sayfa bitti, 'Sonraki' butonuna basılıyor...")
            # Butonu bulmak için sayfayı en aşağı kaydır
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # XPATH'i hem 'Sonraki' yazısına hem de pagination yapısına göre güncelledim
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sonraki')] | //a[contains(@class, 'next')]")))
            
            driver.execute_script("arguments[0].click();", next_btn)
            print("✅ Butona basıldı, yeni filmler bekleniyor...")
            time.sleep(6) # Sayfa yükleme hızına göre esnetilebilir
        except Exception as e:
            print(f"❌ Sonraki sayfa yüklenemedi: {e}")
            break

finally:
    print(f"\n✅ Toplam {len(islenen_linkler)} film işlendi. Bitti.")
    driver.quit()
