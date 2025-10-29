#!/usr/bin/env python3
"""
Debug test - přímá kontrola processing_result
"""

import sys
sys.path.insert(0, '.')

import asyncio
from app.api.upload import maps_storage
from app.models.map import MapStatus
from datetime import datetime
import json

async def main():
    # Simulace nahrání a zpracování
    test_map_id = "debug-test-123"
    maps_storage[test_map_id] = {
        "map_id": test_map_id,
        "status": MapStatus.COMPLETED,
        "file_path": "test.png",
        "processing_result": {
            "ai_analysis": {"processing_successful": True, "elements": []},
            "georeferencing": {"success": True},
            "ai_success": True,
            "georef_success": True,
            "parameters": {},
            "processing_time": datetime.now().isoformat()
        }
    }
    
    # Test serializace do JSON
    print("Test 1: JSON serializace processing_result")
    try:
        result = maps_storage[test_map_id]["processing_result"]
        json_str = json.dumps(result, default=str)
        print(f"OK: {json_str[:200]}")
    except Exception as e:
        print(f"CHYBA: {e}")
        import traceback
        traceback.print_exc()
    
    # Test volání get_processing_result
    print("\nTest 2: Volání get_processing_result")
    try:
        from app.api.process import get_processing_result
        result = await get_processing_result(test_map_id)
        print(f"Typ výsledku: {type(result)}")
        print(f"Výsledek: {result}")
        
        # Test JSON serializace výsledku
        json_str = json.dumps(result, default=str)
        print(f"JSON OK: {json_str[:200]}")
    except Exception as e:
        print(f"CHYBA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

