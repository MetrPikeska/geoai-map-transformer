"""
Konfigurace aplikace GeoAI Map Transformation System
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Nastavení aplikace"""
    
    # Základní nastavení
    app_name: str = "GeoAI Map Transformation System"
    debug: bool = False
    
    # Cesty k souborům
    upload_dir: str = "uploads"
    results_dir: str = "results"
    
    # Podporované formáty
    supported_image_formats: list = [".jpg", ".jpeg", ".png", ".tiff", ".tif"]
    supported_export_formats: list = [".geojson", ".tiff", ".png"]
    
    # GIS nastavení
    default_crs: str = "EPSG:5514"  # S-JTSK pro Českou republiku
    web_crs: str = "EPSG:3857"       # Web Mercator pro vizualizaci
    
    # AI nastavení
    ai_model_path: Optional[str] = None
    ocr_language: str = "ces"  # Český jazyk pro OCR
    
    # Mapové služby
    osm_base_url: str = "https://api.openstreetmap.org"
    
    # Limity
    max_file_size_mb: int = 50
    max_image_dimension: int = 4096
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Globální instance nastavení
settings = Settings()
