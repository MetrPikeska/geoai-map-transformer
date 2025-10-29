"""
GeoAI Map Transformation System - Main FastAPI Application

Tento modul obsahuje hlavní FastAPI aplikaci pro transformaci statických map
do dynamických interaktivních map pomocí metod GeoAI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path

from app.core.config import settings
from app.api import upload, process, export
from app.core.exceptions import GeoAIException

# Vytvoření FastAPI aplikace
app = FastAPI(
    title="GeoAI Map Transformation System",
    description="Transformace statických map do dynamických interaktivních map pomocí GeoAI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware pro frontend komunikaci
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V produkci omezte na konkrétní domény
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount statických souborů
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Registrace API routerů
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(export.router, prefix="/api", tags=["export"])

# Vytvoření potřebných adresářů
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Hlavní stránka aplikace"""
    try:
        with open("app/static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>GeoAI Map Transformation</title></head>
            <body>
                <h1>GeoAI Map Transformation System</h1>
                <p>Aplikace je připravena k použití.</p>
                <p><a href="/docs">API Dokumentace</a></p>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "GeoAI Map Transformation System je funkční"
    }

@app.exception_handler(GeoAIException)
async def geoai_exception_handler(request, exc: GeoAIException):
    """Handler pro GeoAI výjimky"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.detail
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
