"""
API endpoint pro zpracování map pomocí GeoAI
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import numpy as np

from app.models.map import MapProcessingRequest, MapProcessingResponse, MapStatus, MapElementType
from app.core.exceptions import MapProcessingError
from app.ai.geoai import geoai_analyzer
from app.gis.georef import georeferencer
from app.api.upload import maps_storage, get_map_info

def convert_numpy_types(obj):
    """
    Rekurzivně konvertuje NumPy typy na Python typy pro JSON serializaci
    
    Args:
        obj: Objekt k konverzi
        
    Returns:
        Objekt s konvertovanými NumPy typy
    """
    try:
        if isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif hasattr(obj, 'dtype'):  # NumPy array or scalar
            if np.issubdtype(obj.dtype, np.integer):
                return int(obj)
            elif np.issubdtype(obj.dtype, np.floating):
                return float(obj)
            elif np.issubdtype(obj.dtype, np.bool_):
                return bool(obj)
            else:
                return str(obj)
        elif str(type(obj)).startswith('<class \'numpy.'):
            # Catch any remaining numpy types
            return str(obj)
        else:
            return obj
    except Exception as e:
        # If conversion fails, return string representation
        return str(obj)

router = APIRouter()

# Storage pro výsledky zpracování
processing_results = {}

class ProcessingStatus(BaseModel):
    """Status zpracování mapy"""
    map_id: str
    status: str
    progress: float
    current_step: str
    error_message: Optional[str] = None

@router.post("/process", response_model=MapProcessingResponse)
async def process_map(
    request: MapProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Spuštění zpracování mapy pomocí GeoAI
    
    Args:
        request: Parametry zpracování
        background_tasks: Background úkoly
        
    Returns:
        Response s informacemi o zpracování
    """
    try:
        # Kontrola existence mapy
        if request.map_id not in maps_storage:
            raise HTTPException(status_code=404, detail="Mapa nebyla nalezena")
        
        map_info = maps_storage[request.map_id]
        
        if map_info["status"] != MapStatus.UPLOADED:
            raise HTTPException(
                status_code=400, 
                detail=f"Mapa není připravena ke zpracování. Status: {map_info['status']}"
            )
        
        # Aktualizace statusu
        map_info["status"] = MapStatus.PROCESSING
        map_info["processing_start_time"] = datetime.now()
        
        # Spuštění zpracování na pozadí
        background_tasks.add_task(
            _process_map_background,
            request.map_id,
            request.enable_georeferencing,
            request.enable_ai_analysis,
            request.target_crs
        )
        
        # Inicializace statusu zpracování
        processing_results[request.map_id] = ProcessingStatus(
            map_id=request.map_id,
            status="processing",
            progress=0.0,
            current_step="Inicializace zpracování"
        )
        
        return MapProcessingResponse(
            map_id=request.map_id,
            status=MapStatus.PROCESSING,
            processing_time=None,
            georeferencing_success=False,
            ai_analysis_success=False,
            detected_elements=[],
            accuracy_rmse=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při spuštění zpracování: {str(e)}")

@router.get("/process/{map_id}/status")
async def get_processing_status(map_id: str):
    """
    Získání statusu zpracování mapy
    
    Args:
        map_id: ID mapy
        
    Returns:
        Status zpracování
    """
    if map_id not in processing_results:
        raise HTTPException(status_code=404, detail="Zpracování nebylo nalezeno")
    
    return processing_results[map_id]

@router.get("/process/{map_id}/result")
async def get_processing_result(map_id: str):
    """
    Získání výsledků zpracování mapy
    
    Args:
        map_id: ID mapy
        
    Returns:
        Výsledky zpracování
    """
    try:
        print(f"DEBUG: Požadavek na výsledky pro map_id={map_id}")
        print(f"DEBUG: map_id in maps_storage: {map_id in maps_storage}")
        
        if map_id not in maps_storage:
            raise HTTPException(status_code=404, detail="Mapa nebyla nalezena")
        
        map_info = maps_storage[map_id]
        print(f"DEBUG: map_info keys: {list(map_info.keys())}")
        print(f"DEBUG: Status: {map_info.get('status')}")
        
        if map_info["status"] == MapStatus.FAILED:
            error_msg = map_info.get("error_message", "Neznámá chyba")
            # Vrátit výsledky s chybou místo vyhození výjimky
            return {
                "ai_analysis": {"error": error_msg, "processing_successful": False},
                "georeferencing": {"error": error_msg, "success": False},
                "processing_time": datetime.now().isoformat(),
                "parameters": {},
                "ai_success": False,
                "georef_success": False
            }
        
        if map_info["status"] != MapStatus.COMPLETED:
            # Vrátit výsledky s informací o stavu místo vyhození výjimky
            return {
                "ai_analysis": {"error": f"Zpracování není dokončeno. Status: {map_info['status']}", "processing_successful": False},
                "georeferencing": {"error": f"Zpracování není dokončeno. Status: {map_info['status']}", "success": False},
                "processing_time": datetime.now().isoformat(),
                "parameters": {},
                "ai_success": False,
                "georef_success": False
            }
        
        if "processing_result" not in map_info:
            # Vytvoření prázdných výsledků pokud neexistují
            map_info["processing_result"] = {
                "ai_analysis": {"error": "Výsledky nejsou k dispozici", "processing_successful": False},
                "georeferencing": {"error": "Výsledky nejsou k dispozici", "success": False},
                "processing_time": datetime.now().isoformat(),
                "parameters": {},
                "ai_success": False,
                "georef_success": False
            }
        
        # Konverze NumPy typů pomocí JSON encoder
        import json
        result = map_info["processing_result"]
        json_str = json.dumps(result, default=str)
        return json.loads(json_str)
        
    except HTTPException:
        raise
    except Exception as e:
        # Vrátit výsledky s chybou místo vyhození výjimky
        return {
            "ai_analysis": {"error": f"Chyba při načítání výsledků: {str(e)}", "processing_successful": False},
            "georeferencing": {"error": f"Chyba při načítání výsledků: {str(e)}", "success": False},
            "processing_time": datetime.now().isoformat(),
            "parameters": {},
            "ai_success": False,
            "georef_success": False
        }

async def _process_map_background(
    map_id: str,
    enable_georeferencing: bool,
    enable_ai_analysis: bool,
    target_crs: str
):
    """
    Zpracování mapy na pozadí
    
    Args:
        map_id: ID mapy
        enable_georeferencing: Povolit georeferencování
        enable_ai_analysis: Povolit AI analýzu
        target_crs: Cílový CRS
    """
    try:
        map_info = maps_storage[map_id]
        file_path = map_info["file_path"]
        
        # Aktualizace statusu
        if map_id in processing_results:
            processing_results[map_id].current_step = "AI analýza mapy"
            processing_results[map_id].progress = 10.0
        
        # AI analýza mapy
        ai_result = None
        ai_success = False
        
        if enable_ai_analysis:
            try:
                # Kontrola existence souboru
                if not os.path.exists(file_path):
                    raise Exception(f"Soubor neexistuje: {file_path}")
                
                ai_result = geoai_analyzer.analyze_map(file_path)
                ai_success = True
                
                if map_id in processing_results:
                    processing_results[map_id].progress = 50.0
                    processing_results[map_id].current_step = "Georeferencování"
                
            except Exception as e:
                print(f"Chyba při AI analýze: {str(e)}")
                ai_result = {"error": str(e), "processing_successful": False}
        
        # Georeferencování
        georef_result = None
        georef_success = False
        
        if enable_georeferencing:
            try:
                # Kontrola existence souboru
                if not os.path.exists(file_path):
                    raise Exception(f"Soubor neexistuje: {file_path}")
                
                georef_result = georeferencer.georeference_map(
                    file_path, ai_result or {}, target_crs
                )
                georef_success = georef_result.get("success", False)
                
                if map_id in processing_results:
                    processing_results[map_id].progress = 90.0
                    processing_results[map_id].current_step = "Finalizace"
                
            except Exception as e:
                print(f"Chyba při georeferencování: {str(e)}")
                georef_result = {"error": str(e), "success": False}
        
        # Kombinace výsledků s konverzí NumPy typů
        processing_result = {
            "ai_analysis": ai_result,
            "georeferencing": georef_result,
            "processing_time": datetime.now().isoformat(),
            "parameters": {
                "enable_georeferencing": enable_georeferencing,
                "enable_ai_analysis": enable_ai_analysis,
                "target_crs": target_crs
            },
            "ai_success": ai_success,
            "georef_success": georef_success
        }
        
        # Konverze NumPy typů pomocí JSON encoder
        json_str = json.dumps(processing_result, default=str)
        processing_result = json.loads(json_str)
        
        # Aktualizace informací o mapě
        map_info["status"] = MapStatus.COMPLETED
        map_info["processing_result"] = processing_result
        map_info["processing_end_time"] = datetime.now()
        
        print(f"DEBUG: processing_result uložen pro {map_id}")
        print(f"DEBUG: Klíče v map_info: {list(map_info.keys())}")
        print(f"DEBUG: Status: {map_info['status']}")
        
        # Výpočet času zpracování
        if "processing_start_time" in map_info:
            processing_time = (
                map_info["processing_end_time"] - map_info["processing_start_time"]
            ).total_seconds()
            map_info["processing_time_seconds"] = processing_time
        
        # Aktualizace statusu
        if map_id in processing_results:
            processing_results[map_id].status = "completed"
            processing_results[map_id].progress = 100.0
            processing_results[map_id].current_step = "Dokončeno"
        
        # Uložení výsledků do souboru
        results_dir = Path("results") / map_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = results_dir / "processing_result.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(processing_result, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Zpracování mapy {map_id} dokončeno úspěšně")
        
    except Exception as e:
        print(f"Chyba při zpracování mapy {map_id}: {str(e)}")
        
        # Aktualizace statusu na chybu
        if map_id in maps_storage:
            maps_storage[map_id]["status"] = MapStatus.FAILED
            maps_storage[map_id]["error_message"] = str(e)
            maps_storage[map_id]["processing_result"] = {
                "ai_analysis": {"error": str(e), "processing_successful": False},
                "georeferencing": {"error": str(e), "success": False},
                "processing_time": datetime.now().isoformat(),
                "parameters": {
                    "enable_georeferencing": enable_georeferencing,
                    "enable_ai_analysis": enable_ai_analysis,
                    "target_crs": target_crs
                },
                "ai_success": False,
                "georef_success": False
            }
        
        if map_id in processing_results:
            processing_results[map_id].status = "failed"
            processing_results[map_id].error_message = str(e)

def _extract_detected_elements(ai_result: dict) -> list:
    """
    Extrakce typů detekovaných prvků z AI výsledků
    
    Args:
        ai_result: Výsledky AI analýzy
        
    Returns:
        Seznam typů prvků
    """
    elements = []
    
    if ai_result and "elements" in ai_result:
        for element in ai_result["elements"]:
            if hasattr(element, 'element_type'):
                elements.append(element.element_type)
    
    return list(set(elements))  # Odstranění duplicit
