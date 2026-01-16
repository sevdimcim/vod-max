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
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 15)

def iframe_cek(film_link):
    """Film sayfasına girip iframe linkini alır"""
    try:
        # Mevcut pencereyi kullanıyoruz
        driver.get(film_link)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        iframe = soup.find('iframe', {'class': 'close'})
        return iframe.get('data-src') if iframe else "Link Bulunamadı"
    except:
        return "Hata"

# İşlenen filmleri takip etmek için (Tekrar çekmemek için)
islenen_linkler = set()

try:
    print("🚀 Film Robotu Başlatılıyor...")
    driver.get("https://www.hdfilmcehennemi.nl/film-robotu-1/")
    time.sleep(5)

    # Kaç kere "Daha Fazla" butonuna basılsın? (Örn: 20 kere)
    for i in range(1, 21):
        print(f"🔄 {i}. kez 'Daha Fazla' butonuna basılıyor...")
        
        try:
            # 1. Sayfayı en aşağı kaydır (Butonun görünmesi için)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 2. "Daha Fazla" butonunu bul ve JS ile tıkla (ElementClickIntercepted hatasını önler)
            # Butonun metni 'Daha Fazla' veya class'ı üzerinden yakalıyoruz
            more_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Daha Fazla')]")))
            driver.execute_script("arguments[0].click();", more_btn)
            
            # 3. Yeni filmlerin yüklenmesi için bekle
            time.sleep(4)
        except Exception as e:
            print(f"⚠️ Daha fazla butonuna basılamadı (Belki bitti): {e}")
            break

    # Tüm tıklamalar bittikten sonra sayfa kaynağını bir kerede alalım
    print("📑 Tüm filmler yüklendi, veriler toplanıyor...")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    film_listesi = soup.find_all('a', class_='poster')

    for film in film_listesi:
        link = film.get('href')
        adi = film.get('title') or film.text.strip()
        
        if link and link not in islenen_linkler:
            islenen_linkler.add(link)
            print(f"🎬 {adi}")
            # Şimdi film sayfasına gidip linki al
            v_link = iframe_cek(link)
            print(f"🔗 {v_link}")
            print("-" * 30)
            
            # Ana listeye geri dönmeliyiz ki bir sonraki filmi işleyebilelim
            # Ama driver.get(link) yapınca sayfa değişiyor. 
            # Bu yüzden her filmden sonra Film Robotuna geri dönmek yerine 
            # önce tüm linkleri bir listeye alıp sonra gezmek daha mantıklı.

finally:
    print(f"✅ Toplam {len(islenen_linkler)} film linki toplandı.")
    driver.quit()
