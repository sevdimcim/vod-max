import requests
from bs4 import BeautifulSoup
import re

def yayin_linki_yakala():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        ana_site = "https://www.selcuksportshd.is/"
        r1 = requests.get(ana_site, headers=headers, timeout=15)
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        
        giris_butonu = soup1.find('a', class_='site-button') or soup1.find('a', href=re.compile(r'selcuk'))

        if giris_butonu:
            guncel_giris_adresi = giris_butonu['href']
            
            r2 = requests.get(guncel_giris_adresi, headers=headers, timeout=15)
            # Regex güncellendi: id kısmından sonrasını (reklamları) atar
            player_match = re.search(r'src="(https://[a-zA-Z0-9.-]+\.click/index\.php\?id=)[^"#]+"', r2.text)
            
            if player_match:
                final_player_link = player_match.group(1)
                
                with open("Slck-player.txt", "w", encoding="utf-8") as f:
                    f.write(final_player_link)
                print(final_player_link)
            else:
                print("fail_player")
        else:
            print("fail_entry")
            
    except Exception as e:
        print(f"error: {e}")

if __name__ == "__main__":
    yayin_linki_yakala()
    
