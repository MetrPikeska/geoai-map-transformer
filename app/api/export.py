"""
API endpoint pro export výsledků zpracování map
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import json
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import geopandas as gpd
from shapely.geometry import shape
try:
    import rasterio
    from rasterio.transform import from_bounds
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    print("GDAL není dostupný - export GeoTIFF bude omezený")
import cv2
import numpy as np

from app.models.map import MapExportRequest, MapExportResponse
from app.core.exceptions import ExportError
from app.api.upload import maps_storage, get_map_info

router = APIRouter()

@router.post("/export", response_model=MapExportResponse)
async def export_map_data(request: MapExportRequest):
    """
    Export výsledků zpracování mapy
    
    Args:
        request: Parametry exportu
        
    Returns:
        Informace o exportovaném souboru
    """
    try:
        # Kontrola existence mapy
        map_info = get_map_info(request.map_id)
        
        if map_info["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Mapa není připravena k exportu. Status: {map_info['status']}"
            )
        
        processing_result = map_info.get("processing_result")
        if not processing_result:
            raise HTTPException(status_code=400, detail="Nejsou k dispozici výsledky zpracování")
        
        # Vytvoření adresáře pro export
        export_dir = Path("results") / request.map_id / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Generování názvu souboru
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.map_id}_{timestamp}.{request.format}"
        file_path = export_dir / filename
        
        # Export podle formátu
        if request.format == "geojson":
            await _export_geojson(processing_result, file_path, request.include_metadata)
        elif request.format == "tiff":
            await _export_geotiff(map_info, processing_result, file_path)
        elif request.format == "png":
            await _export_png(map_info, processing_result, file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Nepodporovaný formát: {request.format}")
        
        # Informace o souboru
        file_size = file_path.stat().st_size
        expires_at = datetime.now() + timedelta(hours=24)  # Soubor expiruje za 24 hodin
        
        response = MapExportResponse(
            map_id=request.map_id,
            export_url=f"/api/export/download/{request.map_id}/{filename}",
            format=request.format,
            file_size=file_size,
            expires_at=expires_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise ExportError(f"Chyba při exportu: {str(e)}")

@router.get("/export/download/{map_id}/{filename}")
async def download_export_file(map_id: str, filename: str):
    """
    Stažení exportovaného souboru
    
    Args:
        map_id: ID mapy
        filename: Název souboru
        
    Returns:
        Soubor k stažení
    """
    try:
        file_path = Path("results") / map_id / "export" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Exportovaný soubor nebyl nalezen")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při stažení: {str(e)}")

@router.get("/export/{map_id}/formats")
async def get_available_formats(map_id: str):
    """
    Získání dostupných formátů pro export
    
    Args:
        map_id: ID mapy
        
    Returns:
        Seznam dostupných formátů
    """
    try:
        map_info = get_map_info(map_id)
        
        if map_info["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Mapa není připravena k exportu. Status: {map_info['status']}"
            )
        
        processing_result = map_info.get("processing_result", {})
        
        formats = []
        
        # GeoJSON je vždy dostupný pokud jsou detekované prvky
        if processing_result.get("ai_analysis", {}).get("elements"):
            formats.append({
                "format": "geojson",
                "description": "GeoJSON s detekovanými prvky",
                "available": True
            })
        
        # GeoTIFF je dostupný pokud bylo georeferencování úspěšné a GDAL je dostupný
        if GDAL_AVAILABLE and processing_result.get("georeferencing", {}).get("success"):
            formats.append({
                "format": "tiff",
                "description": "GeoTIFF s georeferencovanou mapou",
                "available": True
            })
        
        # PNG je vždy dostupný
        formats.append({
            "format": "png",
            "description": "PNG s anotovanými prvky",
            "available": True
        })
        
        return {"formats": formats}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při získávání formátů: {str(e)}")

async def _export_geojson(processing_result: dict, file_path: Path, include_metadata: bool):
    """
    Export výsledků do GeoJSON formátu
    
    Args:
        processing_result: Výsledky zpracování
        file_path: Cesta k výstupnímu souboru
        include_metadata: Zahrnout metadata
    """
    try:
        features = []
        
        # Zpracování AI výsledků
        ai_result = processing_result.get("ai_analysis", {})
        elements = ai_result.get("elements", [])
        
        for element in elements:
            if hasattr(element, 'geometry') and hasattr(element, 'properties'):
                feature = {
                    "type": "Feature",
                    "geometry": element.geometry,
                    "properties": {
                        **element.properties,
                        "element_type": element.element_type.value if hasattr(element.element_type, 'value') else str(element.element_type),
                        "confidence": element.confidence
                    }
                }
                features.append(feature)
        
        # Vytvoření FeatureCollection
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Přidání metadat
        if include_metadata:
            geojson_data["metadata"] = {
                "processing_time": processing_result.get("processing_time"),
                "parameters": processing_result.get("parameters", {}),
                "ai_analysis_success": ai_result.get("processing_successful", False),
                "georeferencing_success": processing_result.get("georeferencing", {}).get("success", False)
            }
        
        # Uložení do souboru
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False, default=str)
        
    except Exception as e:
        raise ExportError(f"Chyba při exportu GeoJSON: {str(e)}")

async def _export_geotiff(map_info: dict, processing_result: dict, file_path: Path):
    """
    Export georeferencované mapy do GeoTIFF formátu
    
    Args:
        map_info: Informace o mapě
        processing_result: Výsledky zpracování
        file_path: Cesta k výstupnímu souboru
    """
    if not GDAL_AVAILABLE:
        raise ExportError("GDAL není dostupný - nelze exportovat GeoTIFF")
    
    try:
        # Načtení původního obrázku
        original_image = cv2.imread(map_info["file_path"])
        if original_image is None:
            raise ExportError("Nelze načíst původní obrázek")
        
        # Informace o georeferencování
        georef_result = processing_result.get("georeferencing", {})
        if not georef_result.get("success"):
            raise ExportError("Georeferencování nebylo úspěšné")
        
        bounds = georef_result.get("bounds")
        transform = georef_result.get("transform")
        target_crs = georef_result.get("target_crs", "EPSG:5514")
        
        if not bounds or not transform:
            raise ExportError("Chybí informace o georeferencování")
        
        # Konverze obrázku do správného formátu
        height, width = original_image.shape[:2]
        
        # Konverze z BGR na RGB
        rgb_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        
        # Uložení jako GeoTIFF
        with rasterio.open(
            file_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=3,
            dtype=rgb_image.dtype,
            crs=target_crs,
            transform=transform
        ) as dst:
            # Zápis jednotlivých kanálů
            for i in range(3):
                dst.write(rgb_image[:, :, i], i + 1)
        
    except Exception as e:
        raise ExportError(f"Chyba při exportu GeoTIFF: {str(e)}")

async def _export_png(map_info: dict, processing_result: dict, file_path: Path):
    """
    Export mapy s anotovanými prvky do PNG formátu
    
    Args:
        map_info: Informace o mapě
        processing_result: Výsledky zpracování
        file_path: Cesta k výstupnímu souboru
    """
    try:
        # Načtení původního obrázku
        image = cv2.imread(map_info["file_path"])
        if image is None:
            raise ExportError("Nelze načíst původní obrázek")
        
        # Vytvoření kopie pro anotace
        annotated_image = image.copy()
        
        # Přidání anotací pro detekované prvky
        ai_result = processing_result.get("ai_analysis", {})
        elements = ai_result.get("elements", [])
        
        # Barvy pro různé typy prvků
        colors = {
            "road": (0, 0, 255),      # Červená
            "water": (255, 0, 0),     # Modrá
            "building": (0, 255, 0),  # Zelená
            "text": (255, 255, 0),    # Žlutá
            "green_area": (0, 255, 0), # Zelená
        }
        
        for element in elements:
            element_type = element.element_type.value if hasattr(element.element_type, 'value') else str(element.element_type)
            color = colors.get(element_type, (128, 128, 128))  # Šedá jako výchozí
            
            # Kreslení geometrie podle typu
            geometry = element.geometry
            if geometry["type"] == "Polygon":
                coords = np.array(geometry["coordinates"][0], dtype=np.int32)
                cv2.polylines(annotated_image, [coords], True, color, 2)
            elif geometry["type"] == "LineString":
                coords = np.array(geometry["coordinates"], dtype=np.int32)
                cv2.polylines(annotated_image, [coords], False, color, 2)
        
        # Uložení anotovaného obrázku
        cv2.imwrite(str(file_path), annotated_image)
        
    except Exception as e:
        raise ExportError(f"Chyba při exportu PNG: {str(e)}")
