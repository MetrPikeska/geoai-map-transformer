"""
GeoAI modul pro analýzu map pomocí umělé inteligence

Tento modul obsahuje hlavní funkcionalitu pro:
- Detekci a segmentaci mapových prvků
- Rozpoznávání textů pomocí OCR
- Analýzu měřítka a legendy
- Klasifikaci objektů na mapě
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import torch
import torchvision.transforms as transforms
from typing import List, Dict, Any, Tuple, Optional
import logging
from pathlib import Path

from app.models.map import MapElement, MapElementType
from app.core.exceptions import AIAnalysisError
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeoAIAnalyzer:
    """
    Hlavní třída pro GeoAI analýzu map
    """
    
    def __init__(self):
        """Inicializace GeoAI analyzátoru"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"GeoAI Analyzer inicializován na zařízení: {self.device}")
        
        # Nastavení OCR
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def analyze_map(self, image_path: str) -> Dict[str, Any]:
        """
        Hlavní metoda pro analýzu mapy
        
        Args:
            image_path: Cesta k obrázku mapy
            
        Returns:
            Slovník s výsledky analýzy
        """
        try:
            logger.info(f"Začínám analýzu mapy: {image_path}")
            
            # Načtení obrázku
            image = self._load_image(image_path)
            
            # Předzpracování obrázku
            processed_image = self._preprocess_image(image)
            
            # Detekce měřítka
            scale_info = self._detect_scale(processed_image)
            
            # Detekce legendy
            legend_info = self._detect_legend(processed_image)
            
            # Segmentace mapových prvků
            elements = self._segment_map_elements(processed_image)
            
            # OCR analýza textů
            text_elements = self._extract_text_elements(processed_image)
            
            # Kombinace výsledků
            analysis_result = {
                "scale_info": scale_info,
                "legend_info": legend_info,
                "elements": elements,
                "text_elements": text_elements,
                "image_dimensions": image.shape[:2],
                "processing_successful": True
            }
            
            logger.info(f"Analýza mapy dokončena úspěšně")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Chyba při analýze mapy: {str(e)}")
            raise AIAnalysisError(f"Chyba při AI analýze mapy: {str(e)}")
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """Načtení obrázku z disku"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise AIAnalysisError(f"Nelze načíst obrázek: {image_path}")
            
            # Konverze z BGR na RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            logger.info(f"Obrázek načten: {image.shape}")
            return image
            
        except Exception as e:
            raise AIAnalysisError(f"Chyba při načítání obrázku: {str(e)}")
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Předzpracování obrázku pro lepší analýzu
        
        Args:
            image: Vstupní obrázek
            
        Returns:
            Předzpracovaný obrázek
        """
        try:
            # Redukce šumu
            denoised = cv2.bilateralFilter(image, 9, 75, 75)
            
            # Zvýšení kontrastu
            lab = cv2.cvtColor(denoised, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
            
            logger.info("Obrázek předzpracován")
            return enhanced
            
        except Exception as e:
            logger.warning(f"Chyba při předzpracování: {str(e)}")
            return image
    
    def _detect_scale(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Detekce měřítkové čáry na mapě
        
        Args:
            image: Vstupní obrázek
            
        Returns:
            Informace o měřítku
        """
        try:
            # Konverze do grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detekce hran
            edges = cv2.Canny(gray, 50, 150)
            
            # Detekce čar pomocí Hough transformace
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                   minLineLength=50, maxLineGap=10)
            
            scale_info = {
                "detected": False,
                "scale_line_length_px": 0,
                "scale_value": None,
                "unit": None,
                "confidence": 0.0
            }
            
            if lines is not None:
                # Najdi nejdelší horizontální čáru (pravděpodobně měřítko)
                horizontal_lines = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                    angle = np.arctan2(y2-y1, x2-x1) * 180 / np.pi
                    
                    # Horizontální čáry (úhel blízko 0 nebo 180 stupňů)
                    if abs(angle) < 15 or abs(angle - 180) < 15:
                        horizontal_lines.append((line[0], length))
                
                if horizontal_lines:
                    # Seřaď podle délky a vezmi nejdelší
                    horizontal_lines.sort(key=lambda x: x[1], reverse=True)
                    longest_line = horizontal_lines[0][0]
                    
                    scale_info.update({
                        "detected": True,
                        "scale_line_length_px": horizontal_lines[0][1],
                        "confidence": min(horizontal_lines[0][1] / 200, 1.0)
                    })
            
            logger.info(f"Měřítko detekováno: {scale_info['detected']}")
            return scale_info
            
        except Exception as e:
            logger.warning(f"Chyba při detekci měřítka: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    def _detect_legend(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Detekce legendy na mapě
        
        Args:
            image: Vstupní obrázek
            
        Returns:
            Informace o legendě
        """
        try:
            # Detekce oblastí s vysokou hustotou textu (pravděpodobně legenda)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detekce textových oblastí pomocí MSER
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            legend_info = {
                "detected": False,
                "bbox": None,
                "confidence": 0.0
            }
            
            if len(regions) > 0:
                # Najdi oblast s nejvyšší hustotou textových regionů
                # (zjednodušená implementace)
                legend_info.update({
                    "detected": True,
                    "confidence": min(len(regions) / 1000, 1.0)
                })
            
            logger.info(f"Legenda detekována: {legend_info['detected']}")
            return legend_info
            
        except Exception as e:
            logger.warning(f"Chyba při detekci legendy: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    def _segment_map_elements(self, image: np.ndarray) -> List[MapElement]:
        """
        Segmentace mapových prvků pomocí počítačového vidění
        
        Args:
            image: Vstupní obrázek
            
        Returns:
            Seznam detekovaných prvků
        """
        try:
            elements = []
            
            # Detekce silnic (tmavé čáry)
            roads = self._detect_roads(image)
            elements.extend(roads)
            
            # Detekce vodních toků (modré oblasti)
            water = self._detect_water(image)
            elements.extend(water)
            
            # Detekce budov (geometrické tvary)
            buildings = self._detect_buildings(image)
            elements.extend(buildings)
            
            # Detekce zelených ploch
            green_areas = self._detect_green_areas(image)
            elements.extend(green_areas)
            
            logger.info(f"Detekováno {len(elements)} mapových prvků")
            return elements
            
        except Exception as e:
            logger.warning(f"Chyba při segmentaci prvků: {str(e)}")
            return []
    
    def _detect_roads(self, image: np.ndarray) -> List[MapElement]:
        """Detekce silnic na mapě"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detekce hran
            edges = cv2.Canny(gray, 50, 150)
            
            # Detekce čar pomocí Hough transformace
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                   minLineLength=30, maxLineGap=10)
            
            roads = []
            if lines is not None:
                for i, line in enumerate(lines):
                    x1, y1, x2, y2 = line[0]
                    
                    # Vytvoření GeoJSON LineString
                    geometry = {
                        "type": "LineString",
                        "coordinates": [[x1, y1], [x2, y2]]
                    }
                    
                    road = MapElement(
                        element_id=f"road_{i}",
                        element_type=MapElementType.ROAD,
                        geometry=geometry,
                        properties={"width": 1, "type": "road"},
                        confidence=0.7
                    )
                    roads.append(road)
            
            return roads
            
        except Exception as e:
            logger.warning(f"Chyba při detekci silnic: {str(e)}")
            return []
    
    def _detect_water(self, image: np.ndarray) -> List[MapElement]:
        """Detekce vodních toků na mapě"""
        try:
            # Konverze do HSV pro lepší detekci barev
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            
            # Definice rozsahu modré barvy
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])
            
            # Vytvoření masky pro modré oblasti
            mask = cv2.inRange(hsv, lower_blue, upper_blue)
            
            # Najdi kontury
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            water_elements = []
            for i, contour in enumerate(contours):
                if cv2.contourArea(contour) > 100:  # Minimální velikost
                    # Převod kontury na GeoJSON Polygon
                    points = contour.reshape(-1, 2).tolist()
                    points.append(points[0])  # Uzavření polygonu
                    
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [points]
                    }
                    
                    water = MapElement(
                        element_id=f"water_{i}",
                        element_type=MapElementType.WATER,
                        geometry=geometry,
                        properties={"type": "water_body"},
                        confidence=0.8
                    )
                    water_elements.append(water)
            
            return water_elements
            
        except Exception as e:
            logger.warning(f"Chyba při detekci vodních toků: {str(e)}")
            return []
    
    def _detect_buildings(self, image: np.ndarray) -> List[MapElement]:
        """Detekce budov na mapě"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detekce hran
            edges = cv2.Canny(gray, 50, 150)
            
            # Najdi kontury
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            buildings = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if 500 < area < 10000:  # Rozumná velikost budovy
                    # Aproximace kontury na polygon
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if len(approx) >= 4:  # Minimálně čtyřúhelník
                        points = approx.reshape(-1, 2).tolist()
                        points.append(points[0])  # Uzavření polygonu
                        
                        geometry = {
                            "type": "Polygon",
                            "coordinates": [points]
                        }
                        
                        building = MapElement(
                            element_id=f"building_{i}",
                            element_type=MapElementType.BUILDING,
                            geometry=geometry,
                            properties={"area": area, "type": "building"},
                            confidence=0.6
                        )
                        buildings.append(building)
            
            return buildings
            
        except Exception as e:
            logger.warning(f"Chyba při detekci budov: {str(e)}")
            return []
    
    def _detect_green_areas(self, image: np.ndarray) -> List[MapElement]:
        """Detekce zelených ploch na mapě"""
        try:
            # Konverze do HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            
            # Definice rozsahu zelené barvy
            lower_green = np.array([40, 50, 50])
            upper_green = np.array([80, 255, 255])
            
            # Vytvoření masky pro zelené oblasti
            mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Najdi kontury
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            green_areas = []
            for i, contour in enumerate(contours):
                if cv2.contourArea(contour) > 200:  # Minimální velikost
                    points = contour.reshape(-1, 2).tolist()
                    points.append(points[0])  # Uzavření polygonu
                    
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [points]
                    }
                    
                    green_area = MapElement(
                        element_id=f"green_{i}",
                        element_type=MapElementType.GREEN_AREA,
                        geometry=geometry,
                        properties={"type": "green_area"},
                        confidence=0.7
                    )
                    green_areas.append(green_area)
            
            return green_areas
            
        except Exception as e:
            logger.warning(f"Chyba při detekci zelených ploch: {str(e)}")
            return []
    
    def _extract_text_elements(self, image: np.ndarray) -> List[MapElement]:
        """
        Extrakce textových prvků pomocí OCR
        
        Args:
            image: Vstupní obrázek
            
        Returns:
            Seznam textových prvků
        """
        try:
            # Konverze na PIL Image pro Tesseract
            pil_image = Image.fromarray(image)
            
            # OCR analýza
            ocr_data = pytesseract.image_to_data(
                pil_image, 
                lang=settings.ocr_language,
                output_type=pytesseract.Output.DICT
            )
            
            text_elements = []
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                if text and conf > 30:  # Minimální jistota
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Vytvoření bounding boxu jako polygon
                    bbox_coords = [
                        [x, y],
                        [x + w, y],
                        [x + w, y + h],
                        [x, y + h],
                        [x, y]
                    ]
                    
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [bbox_coords]
                    }
                    
                    text_element = MapElement(
                        element_id=f"text_{i}",
                        element_type=MapElementType.TEXT,
                        geometry=geometry,
                        properties={
                            "text": text,
                            "confidence": conf / 100.0,
                            "font_size": h
                        },
                        confidence=conf / 100.0
                    )
                    text_elements.append(text_element)
            
            logger.info(f"Detekováno {len(text_elements)} textových prvků")
            return text_elements
            
        except Exception as e:
            logger.warning(f"Chyba při OCR analýze: {str(e)}")
            return []

# Globální instance analyzátoru
geoai_analyzer = GeoAIAnalyzer()
