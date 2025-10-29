"""
API endpoint pro nahrávání map
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import uuid
import os
from datetime import datetime
from pathlib import Path
import shutil
from typing import Optional

from app.models.map import MapUploadRequest, MapUploadResponse, MapStatus
from app.core.exceptions import FileValidationError
from app.core.config import settings

router = APIRouter()

# In-memory storage pro mapy (v produkci použijte databázi)
maps_storage = {}

@router.post("/upload", response_model=MapUploadResponse)
async def upload_map(file: UploadFile = File(...)):
    """
    Nahrání mapy pro zpracování
    
    Args:
        file: Soubor s mapou (JPG, PNG, TIFF)
        
    Returns:
        Informace o nahrané mapě
    """
    try:
        # Validace souboru
        await _validate_upload_file(file)
        
        # Generování unikátního ID
        map_id = str(uuid.uuid4())
        
        # Vytvoření adresáře pro mapu
        map_dir = Path(settings.upload_dir) / map_id
        map_dir.mkdir(parents=True, exist_ok=True)
        
        # Uložení souboru
        file_path = map_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Získání informací o souboru
        file_size = file_path.stat().st_size
        
        # Uložení informací o mapě
        map_info = {
            "map_id": map_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": MapStatus.UPLOADED,
            "upload_time": datetime.now(),
            "file_size": file_size,
            "processing_result": None
        }
        
        maps_storage[map_id] = map_info
        
        response = MapUploadResponse(
            map_id=map_id,
            filename=file.filename,
            status=MapStatus.UPLOADED,
            upload_time=map_info["upload_time"],
            file_size=file_size
        )
        
        return response
        
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při nahrávání: {str(e)}")

@router.get("/upload/{map_id}")
async def get_map_info(map_id: str):
    """
    Získání informací o nahrané mapě
    
    Args:
        map_id: ID mapy
        
    Returns:
        Informace o mapě
    """
    if map_id not in maps_storage:
        raise HTTPException(status_code=404, detail="Mapa nebyla nalezena")
    
    return maps_storage[map_id]

@router.delete("/upload/{map_id}")
async def delete_map(map_id: str):
    """
    Smazání nahrané mapy
    
    Args:
        map_id: ID mapy
    """
    if map_id not in maps_storage:
        raise HTTPException(status_code=404, detail="Mapa nebyla nalezena")
    
    try:
        # Smazání souborů
        map_info = maps_storage[map_id]
        file_path = Path(map_info["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Smazání adresáře
        map_dir = file_path.parent
        if map_dir.exists():
            map_dir.rmdir()
        
        # Odstranění ze storage
        del maps_storage[map_id]
        
        return {"message": "Mapa byla úspěšně smazána"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání: {str(e)}")

async def _validate_upload_file(file: UploadFile) -> None:
    """
    Validace nahraného souboru
    
    Args:
        file: Nahraný soubor
        
    Raises:
        FileValidationError: Pokud soubor není validní
    """
    # Kontrola přípony souboru
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.supported_image_formats:
        raise FileValidationError(
            f"Nepodporovaný formát souboru: {file_extension}. "
            f"Podporované formáty: {', '.join(settings.supported_image_formats)}"
        )
    
    # Kontrola velikosti souboru
    if file.size and file.size > settings.max_file_size_mb * 1024 * 1024:
        raise FileValidationError(
            f"Soubor je příliš velký: {file.size / (1024*1024):.1f}MB. "
            f"Maximální velikost: {settings.max_file_size_mb}MB"
        )
    
    # Kontrola MIME typu
    if file.content_type and not file.content_type.startswith("image/"):
        raise FileValidationError("Soubor není obrázek")

def get_map_info(map_id: str) -> dict:
    """
    Pomocná funkce pro získání informací o mapě
    
    Args:
        map_id: ID mapy
        
    Returns:
        Informace o mapě
        
    Raises:
        HTTPException: Pokud mapa nebyla nalezena
    """
    if map_id not in maps_storage:
        raise HTTPException(status_code=404, detail="Mapa nebyla nalezena")
    
    return maps_storage[map_id]
