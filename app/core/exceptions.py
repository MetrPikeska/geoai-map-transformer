"""
Vlastní výjimky pro GeoAI Map Transformation System
"""

from fastapi import HTTPException
from typing import Optional

class GeoAIException(Exception):
    """Základní výjimka pro GeoAI aplikaci"""
    
    def __init__(
        self, 
        detail: str, 
        status_code: int = 500,
        error_code: Optional[str] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(detail)

class MapProcessingError(GeoAIException):
    """Chyba při zpracování mapy"""
    
    def __init__(self, detail: str, error_code: str = "MAP_PROCESSING_ERROR"):
        super().__init__(detail, status_code=422, error_code=error_code)

class GeoreferencingError(GeoAIException):
    """Chyba při georeferencování"""
    
    def __init__(self, detail: str, error_code: str = "GEOREF_ERROR"):
        super().__init__(detail, status_code=422, error_code=error_code)

class AIAnalysisError(GeoAIException):
    """Chyba při AI analýze"""
    
    def __init__(self, detail: str, error_code: str = "AI_ANALYSIS_ERROR"):
        super().__init__(detail, status_code=422, error_code=error_code)

class FileValidationError(GeoAIException):
    """Chyba při validaci souboru"""
    
    def __init__(self, detail: str, error_code: str = "FILE_VALIDATION_ERROR"):
        super().__init__(detail, status_code=400, error_code=error_code)

class ExportError(GeoAIException):
    """Chyba při exportu dat"""
    
    def __init__(self, detail: str, error_code: str = "EXPORT_ERROR"):
        super().__init__(detail, status_code=500, error_code=error_code)
