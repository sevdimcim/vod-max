import undetected_chromedriver as uc
import time
import sys

def save_page_source():
    options = uc.ChromeOptions()
    
    # GitHub Actions/Linux için gerekli argümanlar
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # Dil ayarını Türkçe yapalım ki site şüphelenmesin
    options.add_argument('--lang=tr')

    print("Tarayıcı başlatılıyor...")
    
    try:
        # headless=False bırakıyoruz çünkü xvfb-run ile çalıştırıyoruz. 
        # Bu, Cloudflare'i geçmek için en doğal yöntemdir.
        driver = uc.Chrome(options=options)
        
        url = "https://dizipal.uk/"
        print(f"Hedef siteye gidiliyor: {url}")
        
        driver.get(url)
        
        # Cloudflare "Verify you are human" ekranını geçmek için bekleme
        # Bu süre zarfında uc kütüphanesi arkada gerekli yamaları yapar.
        print("Cloudflare doğrulaması için 25 saniye bekleniyor...")
        time.sleep(25)
        
        # Sayfa kaynağını al
        source = driver.page_source
        
        if "Just a moment" in source or "Cloudflare" in driver.title:
            print("Uyarı: Cloudflare engeli hala aşılamadı. Süreyi uzatmayı deneyin.")
        else:
            print("Doğrulama başarılı gibi görünüyor.")

        # HTML olarak kaydet
        with open("dizipal_anasayfa.html", "w", encoding="utf-8") as f:
            f.write(source)
            
        print(f"Dosya başarıyla kaydedildi. Boyut: {len(source)} karakter.")

    except Exception as e:
        print(f"Hata meydana geldi: {e}")
        sys.exit(1) # Hata durumunda Actions'a hata bildir
        
    finally:
        if 'driver' in locals():
            driver.quit()
            print("Tarayıcı kapatıldı.")

if __name__ == "__main__":
    save_page_source()
    
