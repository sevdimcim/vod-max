import undetected_chromedriver as uc
import time
import sys
import subprocess
import re

def get_chrome_version():
    try:
        # Sistemdeki Chrome versiyonunu çek (Linux/GitHub Actions)
        output = subprocess.check_output(['google-chrome', '--version']).decode('utf-8')
        version = re.search(r'Google Chrome (\d+)', output).group(1)
        return int(version)
    except Exception:
        return None

def save_page_source():
    chrome_version = get_chrome_version()
    print(f"Tespit edilen Chrome ana sürümü: {chrome_version}")

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=tr')

    try:
        # version_main parametresi ile sürücüyü Chrome sürümüne sabitliyoruz
        print("Tarayıcı başlatılıyor...")
        driver = uc.Chrome(options=options, version_main=chrome_version)
        
        url = "https://dizipal.uk/"
        print(f"Hedef: {url}")
        
        driver.get(url)
        
        # Cloudflare'in geçilmesi için bekleme
        print("Cloudflare için bekleniyor (30 saniye)...")
        time.sleep(30)
        
        source = driver.page_source
        
        # Dosyayı kaydet
        with open("dizipal_anasayfa.html", "w", encoding="utf-8") as f:
            f.write(source)
            
        print(f"Bitti! Kaydedilen boyut: {len(source)} karakter.")

        # Eğer kaynak çok kısaysa muhtemelen hala Cloudflare ekranındayızdır
        if len(source) < 5000:
            print("Uyarı: Sayfa kaynağı çok kısa, engel aşılmamış olabilir.")

    except Exception as e:
        print(f"Hata: {e}")
        sys.exit(1)
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    save_page_source()
