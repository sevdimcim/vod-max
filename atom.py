import requests
import os
from datetime import datetime

def sayfa_kaydet():
    """atomsportv488.top sitesinin kaynağını al ve kaydet"""
    
    # Hedef URL
    url = "https://atomsportv488.top/"
    
    # Kaydedilecek dosya adı
    dosya_adi = "atom.txt"
    
    # İşlem zamanı
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{zaman}] İşlem başlatıldı...")
    
    try:
        # Headers (bot engellemesini aşmak için)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print(f"📡 {url} adresine bağlanılıyor...")
        
        # İstek gönder
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        print(f"📊 HTTP Durum Kodu: {response.status_code}")
        
        if response.status_code == 200:
            # Sayfa kaynağını al
            sayfa_kaynagi = response.text
            
            # Dosyaya kaydet
            with open(dosya_adi, 'w', encoding='utf-8') as f:
                f.write(sayfa_kaynagi)
            
            # Dosya bilgileri
            dosya_boyutu = len(sayfa_kaynagi)
            satir_sayisi = len(sayfa_kaynagi.split('\n'))
            
            print(f"✅ Dosya kaydedildi: {dosya_adi}")
            print(f"📄 Boyut: {dosya_boyutu} karakter, {satir_sayisi} satır")
            
            # README için bilgi
            with open('README.md', 'a', encoding='utf-8') as readme:
                readme.write(f"\n## 📅 Son Güncelleme: {zaman}\n")
                readme.write(f"- **Dosya:** {dosya_adi}\n")
                readme.write(f"- **Boyut:** {dosya_boyutu} karakter\n")
                readme.write(f"- **Durum:** Başarılı ✅\n")
            
            return True
        else:
            hata_msg = f"Hata: {response.status_code}"
            print(f"❌ {hata_msg}")
            
            with open('README.md', 'a', encoding='utf-8') as readme:
                readme.write(f"\n## 📅 Son Güncelleme: {zaman}\n")
                readme.write(f"- **Durum:** Başarısız ❌\n")
                readme.write(f"- **Hata:** {hata_msg}\n")
            
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Hata: Bağlantı zaman aşımı")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Hata: Bağlantı hatası - Site kapalı olabilir")
        return False
    except Exception as e:
        print(f"❌ Beklenmedik hata: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("🚀 atom.py - Sayfa Kaynağı Alıcı")
    print("="*50)
    
    # Çalıştır
    basarili = sayfa_kaydet()
    
    if basarili:
        print("\n✨ İşlem başarıyla tamamlandı!")
    else:
        print("\n⚠️ İşlem sırasında hata oluştu!")
    
    print("="*50)
