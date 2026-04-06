import os
import re

def rename_transport_pictograms():
    transport_dir = 'transport'
    if not os.path.exists(transport_dir):
        print(f"Ordner '{transport_dir}' existiert nicht.")
        return

    print(f"Überprüfe Piktogramme im Ordner '{transport_dir}'...")
    for filename in os.listdir(transport_dir):
        # Umbenennung nur bei .png oder .svg Dateien
        if not (filename.lower().endswith('.png') or filename.lower().endswith('.svg')):
            continue
        
        # Überspringe env_hazard.png und bereits korrekte Dateien (z.B. class3.png)
        if not filename.lower().startswith('class') and filename.lower() != 'env_hazard.png':
            # Extrahiere die Ziffer aus dem Dateinamen (z.B. bei "3.png" oder "UN4.1.png")
            match = re.search(r'(\d+(?:\.\d+)?)', filename)
            if match:
                class_num = match.group(1)
                ext = os.path.splitext(filename)[1].lower()
                new_name = f"class{class_num}{ext}"
                
                old_path = os.path.join(transport_dir, filename)
                new_path = os.path.join(transport_dir, new_name)
                
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"Umbenannt: {filename} -> {new_name}")

if __name__ == '__main__':
    rename_transport_pictograms()