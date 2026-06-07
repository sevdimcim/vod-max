import os
import shutil

OLD_DIR = "image"
NEW_DIR = "images"

if os.path.exists(OLD_DIR):
    os.makedirs(NEW_DIR, exist_ok=True)

    for root, dirs, files in os.walk(OLD_DIR):
        rel_path = os.path.relpath(root, OLD_DIR)
        target_root = os.path.join(NEW_DIR, rel_path) if rel_path != "." else NEW_DIR

        os.makedirs(target_root, exist_ok=True)

        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(target_root, file)
            shutil.move(src, dst)

    shutil.rmtree(OLD_DIR)

    print(f"'{OLD_DIR}' klasörü '{NEW_DIR}' olarak taşındı.")
else:
    print(f"'{OLD_DIR}' klasörü bulunamadı.")
