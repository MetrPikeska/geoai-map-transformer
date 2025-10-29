"""
Pydantic modely pro GeoAI Map Transformation System
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

class MapStatus(str, Enum):
    """Status zpracování mapy"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MapElementType(str, Enum):
    """Typy mapových prvků"""
    ROAD = "road"
    WATER = "water"
    BUILDING = "building"
    TEXT = "text"
    LEGEND = "legend"
    SCALE = "scale"
    GREEN_AREA = "green_area"

class MapUploadRequest(BaseModel):
    """Request pro nahrání mapy"""
    filename: str = Field(..., description="Název souboru")
    description: Optional[str] = Field(None, description="Popis mapy")

class MapUploadResponse(BaseModel):
    """Response po nahrání mapy"""
    map_id: str = Field(..., description="Unikátní ID mapy")
    filename: str = Field(..., description="Název souboru")
    status: MapStatus = Field(..., description="Status zpracování")
    upload_time: datetime = Field(..., description="Čas nahrání")
    file_size: int = Field(..., description="Velikost souboru v bytech")

class MapProcessingRequest(BaseModel):
    """Request pro zpracování mapy"""
    map_id: str = Field(..., description="ID mapy k zpracování")
    enable_georeferencing: bool = Field(True, description="Povolit georeferencování")
    enable_ai_analysis: bool = Field(True, description="Povolit AI analýzu")
    target_crs: str = Field("EPSG:4326", description="Cílový souřadnicový systém")

class MapProcessingResponse(BaseModel):
    """Response po zpracování mapy"""
    map_id: str = Field(..., description="ID mapy")
    status: MapStatus = Field(..., description="Status zpracování")
    processing_time: Optional[float] = Field(None, description="Čas zpracování v sekundách")
    georeferencing_success: bool = Field(False, description="Úspěšnost georeferencování")
    ai_analysis_success: bool = Field(False, description="Úspěšnost AI analýzy")
    detected_elements: List[MapElementType] = Field(default_factory=list, description="Detekované prvky")
    accuracy_rmse: Optional[float] = Field(None, description="RMSE přesnost georeferencování")

class MapElement(BaseModel):
    """Mapový prvek"""
    element_id: str = Field(..., description="ID prvku")
    element_type: MapElementType = Field(..., description="Typ prvku")
    geometry: Dict[str, Any] = Field(..., description="Geometrie (GeoJSON)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Vlastnosti prvku")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Jistota detekce")

class MapExportRequest(BaseModel):
    """Request pro export mapy"""
    map_id: str = Field(..., description="ID mapy")
    format: str = Field(..., description="Formát exportu (geojson, tiff, png)")
    include_metadata: bool = Field(True, description="Zahrnout metadata")

class MapExportResponse(BaseModel):
    """Response pro export mapy"""
    map_id: str = Field(..., description="ID mapy")
    export_url: str = Field(..., description="URL pro stažení")
    format: str = Field(..., description="Formát exportu")
    file_size: int = Field(..., description="Velikost souboru")
    expires_at: datetime = Field(..., description="Expirace souboru")

class MapInfo(BaseModel):
    """Informace o mapě"""
    map_id: str = Field(..., description="ID mapy")
    filename: str = Field(..., description="Název souboru")
    status: MapStatus = Field(..., description="Status")
    upload_time: datetime = Field(..., description="Čas nahrání")
    processing_time: Optional[datetime] = Field(None, description="Čas zpracování")
    file_size: int = Field(..., description="Velikost souboru")
    image_dimensions: Optional[tuple] = Field(None, description="Rozměry obrázku")
    crs: Optional[str] = Field(None, description="Souřadnicový systém")
    bounds: Optional[Dict[str, float]] = Field(None, description="Hranice mapy")
    elements_count: int = Field(0, description="Počet detekovaných prvků")

class ErrorResponse(BaseModel):
    """Response pro chyby"""
    error_code: str = Field(..., description="Kód chyby")
    detail: str = Field(..., description="Detail chyby")
    timestamp: datetime = Field(default_factory=datetime.now, description="Čas chyby")
