import os

# Ayarlar - Resmindeki yapıya göre 'tenor' klasörüne bakıyoruz
TARGET_DIRECTORY = "tenor" 
OLD_DOMAIN = "dizipal.cx" # Başına https koymadan aratmak daha garantidir
NEW_DOMAIN = "dizipal.bar"

def update_json_domains():
    count = 0
    # Klasörün varlığını kontrol et
    if not os.path.exists(TARGET_DIRECTORY):
        print(f"Hata: {TARGET_DIRECTORY} klasörü bulunamadı!")
        return

    for filename in os.listdir(TARGET_DIRECTORY):
        if filename.endswith(".json"):
            file_path = os.path.join(TARGET_DIRECTORY, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Eğer eski domain içerikte varsa değiştir
            if OLD_DOMAIN in content:
                new_content = content.replace(OLD_DOMAIN, NEW_DOMAIN)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"Güncellendi: {filename}")
                count += 1
            else:
                # Debug için: Dosyada ne aradığını ve neden bulamadığını anlamak istersen
                print(f"Atlandı (Eski domain bulunamadı): {filename}")

    print(f"\nİşlem bitti! {count} dosya başarıyla güncellendi.")

if __name__ == "__main__":
    update_json_domains()
