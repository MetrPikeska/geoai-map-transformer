#!/usr/bin/env python3
"""
Test kontroly výsledků zpracování
"""

import requests
import json

def test_result_endpoint():
    """Test endpointu pro výsledky"""
    base_url = "http://localhost:8000"
    
    # Nejprve nahrát mapu
    from PIL import Image
    import numpy as np
    
    img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    img.save("test_map.png")
    
    with open("test_map.png", 'rb') as f:
        files = {'file': ("test_map.png", f, 'image/png')}
        response = requests.post(f"{base_url}/api/upload", files=files)
    
    if response.status_code != 200:
        print(f"Upload selhal: {response.status_code}")
        return
    
    map_id = response.json()['map_id']
    print(f"Map ID: {map_id}")
    
    # Spustit zpracování
    process_data = {
        "map_id": map_id,
        "enable_georeferencing": True,
        "enable_ai_analysis": True,
        "target_crs": "EPSG:4326"
    }
    
    response = requests.post(f"{base_url}/api/process", json=process_data)
    print(f"Process response: {response.status_code}")
    
    # Počkat na dokončení
    import time
    time.sleep(3)
    
    # Zkusit získat výsledky
    response = requests.get(f"{base_url}/api/process/{map_id}/result")
    print(f"\nResult response status: {response.status_code}")
    print(f"Result response headers: {response.headers}")
    print(f"Result response text: {response.text[:500]}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\nResult data: {json.dumps(data, indent=2, default=str)[:500]}")
        except:
            print("Cannot parse JSON")
    
    # Cleanup
    import os
    if os.path.exists("test_map.png"):
        os.remove("test_map.png")

if __name__ == "__main__":
    test_result_endpoint()

