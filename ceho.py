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
chrome_options.add_argument("--headless")  # GitHub'da çalışması için ekranı kapat
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Sürücüyü Başlat
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 20)

def iframe_cek(film_link):
    """Film sayfasına girer ve iframe linkini alır"""
    # Yeni bir sekmede aç
    driver.execute_script(f"window.open('{film_link}', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    
    try:
        # Sayfanın ve iframe'in yüklenmesi için bekle
        time.sleep(3) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        iframe = soup.find('iframe', {'class': 'close'})
        
        if iframe and iframe.get('data-src'):
            res = iframe.get('data-src')
        else:
            res = "Iframe Bulunamadı"
            
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return res
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return "Hata Oluştu"

# --- ANA DÖNGÜ ---
try:
    print("🚀 Bot Başlatıldı...")
    driver.get("https://www.hdfilmcehennemi.nl/category/film-izle-2/")
    
    # Kaç sayfa tarasın? (range içini istediğin kadar artırabilirsin)
    for sayfa in range(1, 10): 
        print(f"\n--- 📄 SAYFA {sayfa} İŞLENİYOR ---")
        time.sleep(5) # Filmlerin yüklenmesi için bekle
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        film_listesi = soup.find_all('a', class_='poster')
        
        if not film_listesi:
            print("❌ Film bulunamadı, döngü kırılıyor.")
            break
            
        for film in film_listesi:
            adi = film.get('title')
            link = film.get('href')
            
            print(f"🎬 {adi}")
            v_link = iframe_cek(link)
            print(f"🔗 {v_link}")
            print("-" * 30)

        # "Sonraki" butonuna bas
        try:
            print("⏭️ Sonraki sayfaya geçiliyor...")
            # 'Sonraki' yazan veya > işareti olan butonu bul ve tıkla
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sonraki')]")))
            driver.execute_script("arguments[0].click();", next_btn)
        except Exception as e:
            print("❌ Sonraki sayfa butonu bulunamadı veya sayfalar bitti.")
            break

finally:
    print("\n✅ İşlem bitti, tarayıcı kapatılıyor.")
    driver.quit()
