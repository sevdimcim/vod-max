from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Tarayıcı Ayarları
chrome_options = Options()
# chrome_options.add_argument("--headless") # Arkada gizli çalışsın istersen bunu aç

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 20)

def iframe_al(link):
    """Film sayfasına gidip iframe'i çeker"""
    # Yeni sekmede açalım ki ana sayfayı kaybetmeyelim
    driver.execute_script(f"window.open('{link}', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    try:
        # Iframe'in yüklenmesini bekle
        iframe_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "close")))
        src = iframe_element.get_attribute("data-src")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return src
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return None

try:
    url = "https://www.hdfilmcehennemi.nl/category/film-izle-2/"
    driver.get(url)

    for sayfa in range(1, 5): # Kaç sayfa istersen
        print(f"\n🚀 {sayfa}. SAYFA İŞLENİYOR...")
        
        # Sayfa kaynağını BeautifulSoup'a ver
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        filmler = soup.find_all('a', class_='poster')

        for film in filmler:
            f_adi = film.get('title')
            f_link = film.get('href')
            
            print(f"🎬 Film: {f_adi}")
            video = iframe_al(f_link)
            print(f"🔗 Link: {video}")
            print("-" * 30)

        # "Sonraki Sayfa" butonuna tıklama (Sitedeki butonun ID veya Class'ına göre)
        print("⏭️ Sonraki sayfaya geçiliyor...")
        try:
            # Sitedeki pagination kısmında '2', '3' yazan butonlara veya 'Sonraki' butonuna tıkla
            # Bu kısım site yapısına göre 'a[data-page]' şeklinde olabilir
            next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Sonraki')]")
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3) # İçeriğin yüklenmesi için bekle
        except:
            print("❌ Daha fazla sayfa bulunamadı veya tıklanamadı.")
            break

finally:
    driver.quit()
