import os
import json

# Yapılandırma
TARGET_DIRECTORY = "./"  # JSON dosyalarının olduğu klasör (aynı klasörse ./ kalsın)
OLD_DOMAIN = "https://dizipal.cx"
NEW_DOMAIN = "https://dizipal.bar"

def update_json_domains():
    count = 0
    # Klasördeki tüm dosyaları tara
    for filename in os.listdir(TARGET_DIRECTORY):
        if filename.endswith(".json"):
            file_path = os.path.join(TARGET_DIRECTORY, filename)
            
            try:
                # Dosyayı oku
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Domain değişimi yap
                if OLD_DOMAIN in content:
                    new_content = content.replace(OLD_DOMAIN, NEW_DOMAIN)
                    
                    # Değişikliği dosyaya yaz
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print(f"Güncellendi: {filename}")
                    count += 1
                else:
                    print(f"Değişiklik gerekmiyor: {filename}")
                    
            except Exception as e:
                print(f"Hata oluştu ({filename}): {e}")

    print(f"\nİşlem tamam! Toplam {count} dosya güncellendi.")

if __name__ == "__main__":
    update_json_domains()
