"""
Georeferencovací modul pro automatické přiřazení souřadnic k mapám

Tento modul obsahuje funkcionalitu pro:
- Automatické georeferencování statických map
- Detekci kontrolních bodů
- Výpočet transformačních matic
- Validaci přesnosti georeferencování
"""

import cv2
import numpy as np
try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    print("GDAL není dostupný - některé funkce budou omezené")
import geopandas as gpd
from shapely.geometry import Point, Polygon
import requests
import json
from typing import List, Dict, Any, Tuple, Optional
import logging
from pathlib import Path

from app.core.exceptions import GeoreferencingError
from app.core.config import settings

logger = logging.getLogger(__name__)

class Georeferencer:
    """
    Hlavní třída pro georeferencování map
    """
    
    def __init__(self):
        """Inicializace georeferenceru"""
        self.osm_base_url = settings.osm_base_url
        if GDAL_AVAILABLE:
            try:
                self.default_crs = CRS.from_string(settings.default_crs)
                self.web_crs = CRS.from_string(settings.web_crs)
            except Exception as e:
                logger.warning(f"Chyba při inicializaci CRS: {e}")
                self.default_crs = settings.default_crs
                self.web_crs = settings.web_crs
        else:
            self.default_crs = settings.default_crs
            self.web_crs = settings.web_crs
        
        logger.info("Georeferencer inicializován")
    
    def georeference_map(
        self, 
        image_path: str, 
        analysis_result: Dict[str, Any],
        target_crs: str = "EPSG:4326"  # WGS84 pro Leaflet
    ) -> Dict[str, Any]:
        """
        Hlavní metoda pro georeferencování mapy
        
        Args:
            image_path: Cesta k obrázku mapy
            analysis_result: Výsledky AI analýzy
            target_crs: Cílový souřadnicový systém
            
        Returns:
            Slovník s výsledky georeferencování
        """
        try:
            logger.info(f"Začínám georeferencování mapy: {image_path}")
            
            # Načtení obrázku
            image = cv2.imread(image_path)
            if image is None:
                raise GeoreferencingError(f"Nelze načíst obrázek: {image_path}")
            
            # Detekce kontrolních bodů
            control_points = self._detect_control_points(image, analysis_result)
            
            if len(control_points) < 4:
                logger.warning("Nedostatek kontrolních bodů pro georeferencování")
                # Fallback na jednoduché georeferencování
                return self._simple_georeferencing(image_path, analysis_result, target_crs)
            
            # Výpočet transformační matice
            transform_matrix = self._calculate_transform_matrix(control_points)
            
            # Validace přesnosti
            accuracy = self._validate_accuracy(control_points, transform_matrix)
            
            # Vytvoření georeferencovaného rastru
            georef_result = self._create_georeferenced_raster(
                image_path, transform_matrix, target_crs
            )
            
            result = {
                "success": True,
                "control_points_count": len(control_points),
                "transform_matrix": transform_matrix.tolist(),
                "accuracy_rmse": accuracy,
                "target_crs": target_crs,
                "bounds": georef_result["bounds"],
                "transform": georef_result["transform"]
            }
            
            logger.info(f"Georeferencování dokončeno s RMSE: {accuracy:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Chyba při georeferencování: {str(e)}")
            raise GeoreferencingError(f"Chyba při georeferencování: {str(e)}")
    
    def _detect_control_points(
        self, 
        image: np.ndarray, 
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detekce kontrolních bodů na mapě
        
        Args:
            image: Vstupní obrázek
            analysis_result: Výsledky AI analýzy
            
        Returns:
            Seznam kontrolních bodů
        """
        try:
            control_points = []
            
            # Použití textových prvků jako kontrolních bodů
            text_elements = analysis_result.get("text_elements", [])
            
            for text_elem in text_elements:
                text = text_elem.properties.get("text", "")
                confidence = text_elem.properties.get("confidence", 0)
                
                # Filtrace relevantních textů (názvy měst, ulic, atd.)
                if confidence > 0.7 and self._is_relevant_text(text):
                    # Získání souřadnic z geometrie
                    coords = text_elem.geometry["coordinates"][0]
                    center_x = sum([p[0] for p in coords]) / len(coords)
                    center_y = sum([p[1] for p in coords]) / len(coords)
                    
                    # Pokus o nalezení geografických souřadnic
                    geo_coords = self._find_geographic_coordinates(text)
                    
                    if geo_coords:
                        control_points.append({
                            "image_x": center_x,
                            "image_y": center_y,
                            "geo_x": geo_coords[0],
                            "geo_y": geo_coords[1],
                            "text": text,
                            "confidence": confidence
                        })
            
            logger.info(f"Detekováno {len(control_points)} kontrolních bodů")
            return control_points
            
        except Exception as e:
            logger.warning(f"Chyba při detekci kontrolních bodů: {str(e)}")
            return []
    
    def _is_relevant_text(self, text: str) -> bool:
        """
        Kontrola, zda je text relevantní pro georeferencování
        
        Args:
            text: Text k ověření
            
        Returns:
            True pokud je text relevantní
        """
        # Filtrace čísel, krátkých textů a nepodstatných slov
        if len(text) < 3 or text.isdigit():
            return False
        
        # Seznam relevantních klíčových slov pro Olomouc a okolí
        relevant_keywords = [
            "olomouc", "olomouci", "olomouce",
            "přerov", "prostějov", "šumperk",
            "ulice", "náměstí", "třída", "nádraží",
            "řeka", "most", "kostel", "náměstí"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in relevant_keywords)
    
    def _find_geographic_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """
        Nalezení geografických souřadnic pro text pomocí OSM API
        
        Args:
            text: Text k vyhledání
            
        Returns:
            Tuple (x, y) souřadnic nebo None
        """
        try:
            # Nominatim API pro geokódování
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                "q": text,
                "format": "json",
                "limit": 1,
                "countrycodes": "cz",  # Omezení na Českou republiku
                "addressdetails": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    result = data[0]
                    lon = float(result["lon"])
                    lat = float(result["lat"])
                    
                    # Transformace do cílového CRS
                    from pyproj import Transformer
                    transformer = Transformer.from_crs("EPSG:4326", settings.default_crs)
                    x, y = transformer.transform(lat, lon)
                    
                    return (x, y)
            
            return None
            
        except Exception as e:
            logger.warning(f"Chyba při geokódování '{text}': {str(e)}")
            return None
    
    def _calculate_transform_matrix(self, control_points: List[Dict[str, Any]]) -> np.ndarray:
        """
        Výpočet transformační matice z kontrolních bodů
        
        Args:
            control_points: Seznam kontrolních bodů
            
        Returns:
            Transformační matice
        """
        try:
            if len(control_points) < 4:
                raise GeoreferencingError("Potřebujeme minimálně 4 kontrolní body")
            
            # Příprava dat pro výpočet homografie
            src_points = []
            dst_points = []
            
            for cp in control_points:
                src_points.append([cp["image_x"], cp["image_y"]])
                dst_points.append([cp["geo_x"], cp["geo_y"]])
            
            src_points = np.array(src_points, dtype=np.float32)
            dst_points = np.array(dst_points, dtype=np.float32)
            
            # Výpočet homografie
            transform_matrix, mask = cv2.findHomography(
                src_points, dst_points, 
                cv2.RANSAC, 
                ransacReprojThreshold=5.0
            )
            
            if transform_matrix is None:
                raise GeoreferencingError("Nelze vypočítat transformační matici")
            
            logger.info("Transformační matice vypočítána")
            return transform_matrix
            
        except Exception as e:
            raise GeoreferencingError(f"Chyba při výpočtu transformační matice: {str(e)}")
    
    def _validate_accuracy(
        self, 
        control_points: List[Dict[str, Any]], 
        transform_matrix: np.ndarray
    ) -> float:
        """
        Validace přesnosti georeferencování
        
        Args:
            control_points: Kontrolní body
            transform_matrix: Transformační matice
            
        Returns:
            RMSE přesnost
        """
        try:
            errors = []
            
            for cp in control_points:
                # Transformace obrazových souřadnic
                img_point = np.array([[cp["image_x"], cp["image_y"]]], dtype=np.float32)
                img_point = np.array([img_point])
                
                transformed = cv2.perspectiveTransform(img_point, transform_matrix)
                pred_x, pred_y = transformed[0][0]
                
                # Skutečné geografické souřadnice
                true_x, true_y = cp["geo_x"], cp["geo_y"]
                
                # Výpočet chyby
                error = np.sqrt((pred_x - true_x)**2 + (pred_y - true_y)**2)
                errors.append(error)
            
            rmse = np.sqrt(np.mean(np.array(errors)**2))
            logger.info(f"RMSE přesnost: {rmse:.2f} metrů")
            return rmse
            
        except Exception as e:
            logger.warning(f"Chyba při validaci přesnosti: {str(e)}")
            return float('inf')
    
    def _create_georeferenced_raster(
        self, 
        image_path: str, 
        transform_matrix: np.ndarray, 
        target_crs: str
    ) -> Dict[str, Any]:
        """
        Vytvoření georeferencovaného rastru
        
        Args:
            image_path: Cesta k obrázku
            transform_matrix: Transformační matice
            target_crs: Cílový CRS
            
        Returns:
            Informace o georeferencovaném rastru
        """
        try:
            # Načtení obrázku
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            # Výpočet hranic v cílovém CRS
            corners = np.array([
                [0, 0],
                [width, 0],
                [width, height],
                [0, height]
            ], dtype=np.float32)
            
            # Transformace rohů
            transformed_corners = cv2.perspectiveTransform(
                corners.reshape(-1, 1, 2), transform_matrix
            )
            
            # Výpočet bounding boxu
            min_x = np.min(transformed_corners[:, 0, 0])
            max_x = np.max(transformed_corners[:, 0, 0])
            min_y = np.min(transformed_corners[:, 0, 1])
            max_y = np.max(transformed_corners[:, 0, 1])
            
            # Vytvoření transformace pro rasterio
            transform = from_bounds(min_x, min_y, max_x, max_y, width, height)
            
            result = {
                "bounds": [min_x, min_y, max_x, max_y],
                "transform": transform,
                "width": width,
                "height": height
            }
            
            logger.info("Georeferencovaný rastr vytvořen")
            return result
            
        except Exception as e:
            raise GeoreferencingError(f"Chyba při vytváření georeferencovaného rastru: {str(e)}")
    
    def _simple_georeferencing(
        self, 
        image_path: str, 
        analysis_result: Dict[str, Any], 
        target_crs: str
    ) -> Dict[str, Any]:
        """
        Jednoduché georeferencování bez kontrolních bodů
        
        Args:
            image_path: Cesta k obrázku
            analysis_result: Výsledky analýzy
            target_crs: Cílový CRS
            
        Returns:
            Základní georeferencovací informace
        """
        try:
            logger.info("Používám jednoduché georeferencování")
            
            # Odhad rozsahu pro Olomouc a okolí (WGS84)
            # Správné souřadnice pro Olomouc v WGS84
            olomouc_bounds = {
                "min_x": 17.2,   # Západní hranice Olomouce
                "max_x": 17.3,   # Východní hranice Olomouce  
                "min_y": 49.5,   # Jižní hranice Olomouce
                "max_y": 49.7    # Severní hranice Olomouce
            }
            
            # Načtení obrázku pro získání rozměrů
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            # Výpočet pixel size
            pixel_size_x = (olomouc_bounds["max_x"] - olomouc_bounds["min_x"]) / width
            pixel_size_y = (olomouc_bounds["max_y"] - olomouc_bounds["min_y"]) / height
            
            # Vytvoření transformace (from_bounds očekává west, south, east, north)
            if GDAL_AVAILABLE:
                transform = from_bounds(
                    olomouc_bounds["min_x"],  # west (lng)
                    olomouc_bounds["min_y"],  # south (lat)
                    olomouc_bounds["max_x"],  # east (lng)
                    olomouc_bounds["max_y"],  # north (lat)
                    width, 
                    height
                )
            else:
                # Fallback transformace bez GDAL
                transform = [
                    pixel_size_x, 0, olomouc_bounds["min_x"],
                    0, -pixel_size_y, olomouc_bounds["max_y"]
                ]
            
            result = {
                "success": True,
                "control_points_count": 0,
                "transform_matrix": None,
                "accuracy_rmse": None,
                "target_crs": "EPSG:4326",  # WGS84 pro Leaflet
                "bounds": [
                    olomouc_bounds["min_x"],
                    olomouc_bounds["min_y"],
                    olomouc_bounds["max_x"],
                    olomouc_bounds["max_y"]
                ],
                "transform": transform,
                "pixel_size": [pixel_size_x, pixel_size_y],
                "method": "simple_estimation"
            }
            
            logger.info("Jednoduché georeferencování dokončeno")
            return result
            
        except Exception as e:
            raise GeoreferencingError(f"Chyba při jednoduchém georeferencování: {str(e)}")

# Globální instance georeferenceru
georeferencer = Georeferencer()
