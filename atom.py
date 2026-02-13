import requests
import os

def source_cek():
    url = "https://atomsportv488.top/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"Baglaniliyor: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Hata varsa yakala
        
        # Sayfa kaynagini al
        source_code = response.text
        
        # atom.txt olarak kaydet
        with open("atom.txt", "w", encoding="utf-8") as f:
            f.write(source_code)
        
        print("Basarili: Sayfa kaynagi atom.txt dosyasina yazildi.")
        
    except Exception as e:
        print(f"Hata olustu: {e}")

if __name__ == "__main__":
    source_cek()
