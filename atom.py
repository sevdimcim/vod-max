import requests
import zlib
import brotli
import gzip
from io import BytesIO

def sayfa_kaydet():
    url = "https://atomsportv488.top/"
    dosya_adi = "atom.txt"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',  # Tüm sıkıştırmaları kabul et
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache'
    }
    
    try:
        # İstek gönder (sıkıştırmayı otomatik çözer)
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=30)
        
        # İçeriği manuel çöz (gerekirse)
        content = response.content
        
        # Sıkıştırılmış mı kontrol et
        content_encoding = response.headers.get('Content-Encoding', '')
        
        print(f"İçerik Kodlaması: {content_encoding}")
        print(f"İçerik Uzunluğu: {len(content)} bytes")
        
        # Sıkıştırmayı çöz
        if 'br' in content_encoding:
            # Brotli çöz
            content = brotli.decompress(content)
            print("Brotli çözüldü")
        elif 'gzip' in content_encoding:
            # Gzip çöz
            content = gzip.decompress(content)
            print("Gzip çözüldü")
        elif 'deflate' in content_encoding:
            # Deflate çöz
            content = zlib.decompress(content)
            print("Deflate çözüldü")
        
        # UTF-8'e çevir (hata varsa ignore et)
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # Latin-1 dene
            try:
                text_content = content.decode('latin-1')
            except:
                # Hiçbiri olmazsa, hex olarak kaydet
                text_content = content.hex()
        
        # Dosyaya kaydet
        with open(dosya_adi, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(text_content)
        
        print(f"✅ Kaydedildi: {dosya_adi}")
        print(f"📊 Boyut: {len(text_content)} karakter")
        
        # İlk 500 karakteri göster
        print("\n📄 İlk 500 karakter:")
        print("-" * 50)
        print(text_content[:500])
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        
        # Ham içeriği binary olarak kaydet
        if 'response' in locals():
            with open('atom_binary.bin', 'wb') as f:
                f.write(response.content)
            print("📁 Ham binary kaydedildi: atom_binary.bin")

if __name__ == "__main__":
    sayfa_kaydet()
