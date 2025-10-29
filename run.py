#!/usr/bin/env python3
"""
Startovací skript pro GeoAI Map Transformation System
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """Hlavní funkce pro spuštění aplikace"""
    
    # Kontrola Python verze
    if sys.version_info < (3, 11):
        print("Chyba: Vyžaduje se Python 3.11 nebo novější")
        sys.exit(1)
    
    # Vytvoření potřebných adresářů
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    print("=" * 60)
    print("GeoAI Map Transformation System")
    print("=" * 60)
    print("Spouštím aplikaci na http://localhost:8000")
    print("API dokumentace: http://localhost:8000/docs")
    print("Pro zastavení stiskněte Ctrl+C")
    print("=" * 60)
    
    try:
        # Spuštění FastAPI aplikace
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nAplikace byla zastavena.")
    except Exception as e:
        print(f"Chyba při spuštění aplikace: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
