"""
Response modely pro API
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime

class SuccessResponse(BaseModel):
    """Základní response pro úspěšné operace"""
    success: bool = True
    message: str
    timestamp: datetime = datetime.now()
    data: Optional[Dict[str, Any]] = None

class ProcessingStatusResponse(BaseModel):
    """Response pro status zpracování"""
    map_id: str
    status: str
    progress: float = Field(..., ge=0.0, le=100.0, description="Progres v procentech")
    current_step: str
    estimated_time_remaining: Optional[int] = Field(None, description="Odhadovaný zbývající čas v sekundách")
