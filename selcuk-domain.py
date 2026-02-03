import requests
from bs4 import BeautifulSoup
import re
import os

def yayin_linki_yakala():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        ana_site = "https://www.selcuksportshd.is/"
        r1 = requests.get(ana_site, headers=headers, timeout=15)
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        
        # Giriş butonunu bul
        giris_butonu = soup1.find('a', class_='site-button') or soup1.find('a', href=re.compile(r'selcuk'))

        if giris_butonu:
            guncel_giris_adresi = giris_butonu['href']
            print(f"Giris Adresi: {guncel_giris_adresi}")
            
            r2 = requests.get(guncel_giris_adresi, headers=headers, timeout=15)
            html_content = r2.text
            
            # Daha esnek Regex: src=' veya src=" fark etmez, id'den sonrasını almaz
            # Pattern: src içindeki .click/index.php?id= kısmını arar
            player_match = re.search(r'src=["\'](https://[a-zA-Z0-9.-]+\.click/index\.php\?id=)[^"\'#]+["\']', html_content)
            
            if player_match:
                final_player_link = player_match.group(1)
                
                file_path = os.path.join(os.getcwd(), "Slck-player.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_player_link)
                print(f"SUCCESS: {final_player_link}")
            else:
                print("FAIL: Player link bulunamadı. Sayfa kaynağı kontrol ediliyor...")
                # Hata ayıklama için sayfa içinde 'click' geçen yerleri yazdır
                debug_match = re.findall(r'https?://[a-zA-Z0-9.-]+\.click[^\s"\'<>]*', html_content)
                print(f"Bulunan benzer linkler: {debug_match}")
        else:
            print("FAIL: Giris butonu bulunamadi.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    yayin_linki_yakala()
    
