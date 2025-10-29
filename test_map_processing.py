#!/usr/bin/env python3
"""
Test skript pro upload a zpracování mapy
"""

import requests
import time
import os
from pathlib import Path

def test_map_upload():
    """Test uploadu a zpracování mapy"""
    base_url = "http://localhost:8000"
    
    print("Testovani uploadu a zpracovani mapy")
    print("=" * 50)
    
    # Test 1: Upload mapy
    print("1. Testovani uploadu mapy...")
    
    # Vytvoření testovacího souboru
    test_file_path = "test_map.png"
    if not os.path.exists(test_file_path):
        # Vytvoření jednoduchého PNG souboru
        from PIL import Image
        import numpy as np
        
        # Vytvoření jednoduchého obrázku
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img.save(test_file_path)
        print(f"Vytvoren testovaci soubor: {test_file_path}")
    
    try:
        # Upload souboru
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path, f, 'image/png')}
            response = requests.post(f"{base_url}/api/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            map_id = data['map_id']
            print(f"OK - Upload: {map_id}")
            
            # Test 2: Spuštění zpracování
            print("2. Testovani spusteni zpracovani...")
            
            process_data = {
                "map_id": map_id,
                "enable_georeferencing": True,
                "enable_ai_analysis": True,
                "target_crs": "EPSG:4326"
            }
            
            response = requests.post(f"{base_url}/api/process", json=process_data)
            
            if response.status_code == 200:
                print("OK - Spusteni zpracovani")
                
                # Test 3: Monitoring zpracování
                print("3. Testovani monitoringu zpracovani...")
                
                for i in range(10):  # Max 10 pokusů
                    time.sleep(2)
                    
                    # Kontrola statusu
                    status_response = requests.get(f"{base_url}/api/process/{map_id}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"Status: {status_data['status']} - {status_data['current_step']} ({status_data['progress']}%)")
                        
                        if status_data['status'] == 'completed':
                            print("OK - Zpracovani dokonceno")
                            break
                        elif status_data['status'] == 'failed':
                            print("CHYBA - Zpracovani selhalo")
                            break
                    else:
                        print(f"CHYBA - Status: {status_response.status_code}")
                        break
                
                # Test 4: Načtení výsledků
                print("4. Testovani nacteni vysledku...")
                
                result_response = requests.get(f"{base_url}/api/process/{map_id}/result")
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    print("OK - Vysledky nacteny")
                    print(f"AI analýza: {'OK' if result_data.get('ai_success') else 'CHYBA'}")
                    print(f"Georeferencování: {'OK' if result_data.get('georef_success') else 'CHYBA'}")
                else:
                    print(f"CHYBA - Vysledky: {result_response.status_code}")
                    print(f"Response: {result_response.text}")
            
            else:
                print(f"CHYBA - Spusteni zpracovani: {response.status_code}")
                print(f"Response: {response.text}")
        
        else:
            print(f"CHYBA - Upload: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"CHYBA - Exception: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"Smazan testovaci soubor: {test_file_path}")

if __name__ == "__main__":
    test_map_upload()
