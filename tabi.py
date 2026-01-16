import time
import json
from seleniumwire import webdriver  # Trafiği yakalamak için selenium-wire
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- KULLANICI BİLGİLERİ ---
EMAIL = "sonhan3087@gmail.com"
SIFRE = "996633Eko."
# İzlemek istediğin sayfanın linki
VIDEO_URL = "https://www.tabii.com/tr/watch/565323?trackId=566764"

def tabiyi_patlat():
    # Tarayıcı ayarları
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Arka planda çalışsın istersen bunu aç
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--mute-audio") # Sesi kapat

    print("[*] Tarayıcı başlatılıyor (IDM Modu Aktif)...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # 1. Tabii Giriş Sayfasına Git
        driver.get("https://www.tabii.com/tr/login")
        time.sleep(3)

        # 2. Giriş İşlemi (Manuel Taklit)
        print("[*] Giriş yapılıyor...")
        driver.find_element(By.NAME, "email").send_keys(EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SIFRE)
        
        # Giriş butonuna bas (Sayfa yapısına göre class değişebilir, en garanti yol selector)
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        
        time.sleep(5) # Girişin tamamlanmasını bekle

        # 3. Video Sayfasına Git
        print(f"[*] Video sayfasına gidiliyor: {VIDEO_URL}")
        driver.get(VIDEO_URL)
        time.sleep(10) # Videonun yüklenmesi ve trafiğin oluşması için süre ver

        # 4. IDM GİBİ TRAFİĞİ KOKLA
        print("[*] Trafik analiz ediliyor, video linki aranıyor...")
        
        found_url = None
        for request in driver.requests:
            if request.response:
                # Tabii'nin MP4 veya M3U8 linklerini yakalıyoruz
                # IDM'nin yakaladığı 'cms-tabii' veya 'video_' içeren linkleri süz
                if 'cms-tabii' in request.url or '.m3u8' in request.url or 'video_' in request.url:
                    if request.response.status_code == 200:
                        found_url = request.url
                        break # İlk kaliteli linki bulduğunda dur

        if found_url:
            print("\n" + "═"*60)
            print("🚀 BİNGO! IDM'NİN YAKALADIĞI LİNK BURADA:")
            print(f"\n{found_url}\n")
            print("═"*60)
            
            # Linki bir dosyaya kaydet
            with open("yakalanan_link.txt", "w") as f:
                f.write(found_url)
            print("[+] Link 'yakalanan_link.txt' dosyasına kaydedildi.")
        else:
            print("[-] Maalesef trafikten link cımbızlanamadı. Sayfayı yenileyip tekrar dene.")

    except Exception as e:
        print(f"[-] Hata çıktı: {e}")
    finally:
        print("[*] Tarayıcı kapatılıyor...")
        driver.quit()

if __name__ == "__main__":
    tabiyi_patlat()
