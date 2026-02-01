import undetected_chromedriver as uc
import time

def save_page_source():
    # Tarayıcı ayarları
    options = uc.ChromeOptions()
    # Cloudflare headless (arkaplanda çalışma) modunu bazen yakalar, 
    # bu yüzden tarayıcı açılacak şekilde bırakıyoruz.
    
    print("Tarayıcı başlatılıyor...")
    driver = uc.Chrome(options=options)

    try:
        url = "https://dizipal.uk/"
        print(f"{url} adresine gidiliyor...")
        
        # Siteye git
        driver.get(url)
        
        # Cloudflare "Just a moment" ekranını geçmesi için bekleme süresi.
        # İnternet hızına göre değişebilir ama 10-15 saniye genellikle yeterlidir.
        print("Cloudflare kontrolü için 15 saniye bekleniyor...")
        time.sleep(15)
        
        # Sayfa kaynağını al
        page_source = driver.page_source
        
        # Dosyaya kaydet
        file_name = "dizipal_anasayfa.html"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(page_source)
            
        print(f"Başarılı! Kaynak kod '{file_name}' dosyasına kaydedildi.")
        
    except Exception as e:
        print(f"Bir hata oluştu: {e}")
        
    finally:
        # Tarayıcıyı kapat
        driver.quit()

if __name__ == "__main__":
    save_page_source()
