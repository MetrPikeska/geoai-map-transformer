#!/usr/bin/env python3
"""
Přímý test API bez requests
"""

import sys
sys.path.insert(0, '.')

from app.api.process import maps_storage, processing_results, get_processing_result
from app.models.map import MapStatus

# Simulace dat
test_map_id = "test-123"
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
        "processing_time": "2025-10-28"
    }
}

print("Test 1: Získání výsledků pro existující mapu s výsledky")
try:
    result = get_processing_result(test_map_id)
    print(f"OK: {result}")
except Exception as e:
    print(f"CHYBA: {e}")
    import traceback
    traceback.print_exc()

print("\nTest 2: Získání výsledků pro mapu bez processing_result")
test_map_id2 = "test-456"
maps_storage[test_map_id2] = {
    "map_id": test_map_id2,
    "status": MapStatus.COMPLETED,
    "file_path": "test.png"
}

try:
    result = get_processing_result(test_map_id2)
    print(f"OK: {result}")
except Exception as e:
    print(f"CHYBA: {e}")
    import traceback
    traceback.print_exc()

