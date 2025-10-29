#!/usr/bin/env python3
"""
Test skript pro ověření funkčnosti GeoAI Map Transformation System
"""

import requests
import time
import os
from pathlib import Path

def test_api():
    """Test základních API endpointů"""
    base_url = "http://localhost:8000"
    
    print("Testovani GeoAI Map Transformation System")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testovani health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("OK - Health check")
        else:
            print(f"CHYBA - Health check: {response.status_code}")
            return False
    except Exception as e:
        print(f"CHYBA - Health check: {e}")
        return False
    
    # Test 2: Hlavní stránka
    print("2. Testovani hlavni stranky...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("OK - Hlavni stranka")
        else:
            print(f"CHYBA - Hlavni stranka: {response.status_code}")
    except Exception as e:
        print(f"CHYBA - Hlavni stranka: {e}")
    
    # Test 3: API dokumentace
    print("3. Testovani API dokumentace...")
    try:
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("OK - API dokumentace")
        else:
            print(f"CHYBA - API dokumentace: {response.status_code}")
    except Exception as e:
        print(f"CHYBA - API dokumentace: {e}")
    
    print("\nZakladni testy dokonceny!")
    print(f"Aplikace je dostupna na: {base_url}")
    print(f"API dokumentace: {base_url}/docs")
    
    return True

if __name__ == "__main__":
    test_api()
