/**
 * GeoAI Map Transformation System - JavaScript
 * 
 * Hlavní JavaScript soubor pro frontend aplikaci
 */

// Globální proměnné
let currentMapId = null;
let map = null;
let mapLayers = {};
let processingInterval = null;

// Inicializace při načtení stránky
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Inicializace aplikace
 */
function initializeApp() {
    setupFileUpload();
    setupProcessingControls();
    setupExportControls();
    showToast('Aplikace je připravena k použití', 'info');
}

/**
 * Nastavení nahrávání souborů
 */
function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    
    // Drag & Drop funkcionalita
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // Výběr souboru
    fileInput.addEventListener('change', handleFileSelect);
    
    // Nahrání souboru
    uploadBtn.addEventListener('click', uploadFile);
}

/**
 * Zpracování přetažení souboru
 */
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

/**
 * Výběr souboru
 */
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

/**
 * Zpracování vybraného souboru
 */
function handleFile(file) {
    // Validace souboru
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showToast('Nepodporovaný typ souboru. Použijte JPG, PNG nebo TIFF.', 'error');
        return;
    }
    
    // Kontrola velikosti (50MB)
    if (file.size > 50 * 1024 * 1024) {
        showToast('Soubor je příliš velký. Maximální velikost je 50MB.', 'error');
        return;
    }
    
    // Zobrazení informací o souboru
    document.getElementById('filename').textContent = file.name;
    document.getElementById('filesize').textContent = formatFileSize(file.size);
    document.getElementById('uploadInfo').style.display = 'block';
    
    // Uložení souboru pro nahrání
    window.selectedFile = file;
}

/**
 * Nahrání souboru na server
 */
async function uploadFile() {
    if (!window.selectedFile) {
        showToast('Nejprve vyberte soubor', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', window.selectedFile);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chyba při nahrávání');
        }
        
        const result = await response.json();
        currentMapId = result.map_id;
        
        showToast('Mapa byla úspěšně nahrána', 'success');
        showProcessingSection();
        
    } catch (error) {
        showToast(`Chyba při nahrávání: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Zobrazení sekce zpracování
 */
function showProcessingSection() {
    document.getElementById('processingSection').style.display = 'block';
    document.getElementById('processingSection').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Nastavení ovládacích prvků zpracování
 */
function setupProcessingControls() {
    const processBtn = document.getElementById('processBtn');
    processBtn.addEventListener('click', startProcessing);
}

/**
 * Spuštění zpracování mapy
 */
async function startProcessing() {
    if (!currentMapId) {
        showToast('Nejprve nahrajte mapu', 'warning');
        return;
    }
    
    const enableGeoreferencing = document.getElementById('enableGeoreferencing').checked;
    const enableAIAnalysis = document.getElementById('enableAIAnalysis').checked;
    const targetCRS = document.getElementById('targetCRS').value;
    
    showLoading(true);
    showProgressBar(true);
    
    try {
        const requestData = {
            map_id: currentMapId,
            enable_georeferencing: enableGeoreferencing,
            enable_ai_analysis: enableAIAnalysis,
            target_crs: targetCRS
        };
        
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chyba při spuštění zpracování');
        }
        
        showToast('Zpracování bylo spuštěno', 'success');
        
        // Spuštění sledování průběhu
        startProgressMonitoring();
        
    } catch (error) {
        showToast(`Chyba při spuštění zpracování: ${error.message}`, 'error');
        showLoading(false);
        showProgressBar(false);
    }
}

/**
 * Sledování průběhu zpracování
 */
function startProgressMonitoring() {
    processingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/process/${currentMapId}/status`);
            if (response.ok) {
                const status = await response.json();
                updateProgress(status);
                
                if (status.status === 'completed') {
                    clearInterval(processingInterval);
                    await loadProcessingResults();
                } else if (status.status === 'failed') {
                    clearInterval(processingInterval);
                    showToast(`Zpracování selhalo: ${status.error_message}`, 'error');
                    showLoading(false);
                    showProgressBar(false);
                }
            }
        } catch (error) {
            console.error('Chyba při sledování průběhu:', error);
        }
    }, 2000);
}

/**
 * Aktualizace progress baru
 */
function updateProgress(status) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = `${status.progress}%`;
    progressText.textContent = status.current_step;
}

/**
 * Načtení výsledků zpracování
 */
async function loadProcessingResults() {
    try {
        const response = await fetch(`/api/process/${currentMapId}/result`);
        if (!response.ok) {
            throw new Error('Nelze načíst výsledky zpracování');
        }
        
        const results = await response.json();
        displayResults(results);
        showResultsSection();
        
        // Inicializace mapy pokud jsou výsledky dostupné
        if (results.ai_analysis || results.georeferencing) {
            try {
                initializeMap(results);
            } catch (error) {
                console.error('Chyba při inicializaci mapy:', error);
            }
        }
        
        // Načtení dostupných formátů pro export
        await loadExportFormats();
        
    } catch (error) {
        showToast(`Chyba při načítání výsledků: ${error.message}`, 'error');
    } finally {
        showLoading(false);
        showProgressBar(false);
    }
}

/**
 * Zobrazení výsledků zpracování
 */
function displayResults(results) {
    const resultsInfo = document.getElementById('resultsInfo');
    
    const aiResult = results.ai_analysis || {};
    const georefResult = results.georeferencing || {};
    
    // Kontrola, zda jsou výsledky validní
    const aiSuccess = results.ai_success || (aiResult.processing_successful !== false && !aiResult.error);
    const georefSuccess = results.georef_success || (georefResult.success !== false && !georefResult.error);
    
    const html = `
        <div class="result-item">
            <span class="result-label">AI analýza:</span>
            <span class="result-value ${aiSuccess ? 'success' : 'error'}">
                ${aiSuccess ? 'Úspěšná' : 'Selhala'}
            </span>
        </div>
        <div class="result-item">
            <span class="result-label">Georeferencování:</span>
            <span class="result-value ${georefSuccess ? 'success' : 'error'}">
                ${georefSuccess ? 'Úspěšné' : 'Selhalo'}
            </span>
        </div>
        <div class="result-item">
            <span class="result-label">Detekované prvky:</span>
            <span class="result-value">${aiResult.elements ? aiResult.elements.length : 0}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Kontrolní body:</span>
            <span class="result-value">${georefResult.control_points_count || 0}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Přesnost (RMSE):</span>
            <span class="result-value">${georefResult.accuracy_rmse ? georefResult.accuracy_rmse.toFixed(2) + ' m' : 'N/A'}</span>
        </div>
        ${aiResult.error ? `<div class="result-item"><span class="result-label">AI chyba:</span><span class="result-value error">${aiResult.error}</span></div>` : ''}
        ${georefResult.error ? `<div class="result-item"><span class="result-label">Georef chyba:</span><span class="result-value error">${georefResult.error}</span></div>` : ''}
    `;
    
    resultsInfo.innerHTML = html;
}

/**
 * Zobrazení sekce výsledků
 */
function showResultsSection() {
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Nastavení ovládacích prvků exportu
 */
function setupExportControls() {
    document.getElementById('exportGeoJSON').addEventListener('click', () => exportData('geojson'));
    document.getElementById('exportGeoTIFF').addEventListener('click', () => exportData('tiff'));
    document.getElementById('exportPNG').addEventListener('click', () => exportData('png'));
}

/**
 * Export dat
 */
async function exportData(format) {
    if (!currentMapId) {
        showToast('Nejprve zpracujte mapu', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const requestData = {
            map_id: currentMapId,
            format: format,
            include_metadata: true
        };
        
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chyba při exportu');
        }
        
        const result = await response.json();
        
        // Stažení souboru
        const downloadUrl = `/api/export/download/${currentMapId}/${result.export_url.split('/').pop()}`;
        window.open(downloadUrl, '_blank');
        
        showToast(`Export ${format.toUpperCase()} byl úspěšný`, 'success');
        
    } catch (error) {
        showToast(`Chyba při exportu: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Načtení dostupných formátů pro export
 */
async function loadExportFormats() {
    try {
        const response = await fetch(`/api/export/${currentMapId}/formats`);
        if (response.ok) {
            const data = await response.json();
            updateExportButtons(data.formats);
        }
    } catch (error) {
        console.error('Chyba při načítání formátů:', error);
    }
}

/**
 * Aktualizace tlačítek exportu
 */
function updateExportButtons(formats) {
    const buttons = {
        'geojson': document.getElementById('exportGeoJSON'),
        'tiff': document.getElementById('exportGeoTIFF'),
        'png': document.getElementById('exportPNG')
    };
    
    if (!formats || !Array.isArray(formats)) {
        console.log('Formáty nejsou dostupné');
        return;
    }
    
    formats.forEach(format => {
        const button = buttons[format.format];
        if (button) {
            button.disabled = !format.available;
            button.title = format.available ? format.description : 'Formát není dostupný';
        }
    });
}

/**
 * Inicializace Leaflet mapy
 */
function initializeMap(results) {
    if (map) {
        map.remove();
    }
    
    const georefResult = results.georeferencing || {};
    const bounds = georefResult.bounds;
    
    // Výchozí centrum pro Olomouc
    let center = [49.5937, 17.2509];
    let zoom = 13;
    
    // Pokud máme bounds z georeferencování, použijeme je
    if (bounds && bounds.length === 4) {
        const southWest = [bounds[1], bounds[0]]; // [lat, lng]
        const northEast = [bounds[3], bounds[2]]; // [lat, lng]
        const mapBounds = L.latLngBounds(southWest, northEast);
        
        // Vytvoření mapy s bounds
        map = L.map('map').fitBounds(mapBounds);
        
        // Přidání základní vrstvy
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        console.log('Mapa inicializována s bounds:', bounds);
    } else {
        // Vytvoření mapy s výchozím centrem
        map = L.map('map').setView(center, zoom);
        
        // Přidání základní vrstvy
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        console.log('Mapa inicializována s výchozím centrem:', center);
    }
    
    // Přidání měřítka
    L.control.scale().addTo(map);
    
    // Načtení dat z AI analýzy pouze pokud jsou dostupná
    if (results.ai_analysis && results.ai_analysis.elements && !results.ai_analysis.error) {
        loadMapLayers(results.ai_analysis);
        
        // Po načtení vrstev přizpůsobíme viewport podle dat
        setTimeout(() => {
            fitMapToData();
        }, 100);
    } else {
        console.log('AI analýza není dostupná nebo neobsahuje prvky:', results.ai_analysis);
    }
    
    // Nastavení informací o mapě
    if (georefResult && !georefResult.error) {
        updateMapInfo(georefResult);
    } else {
        console.log('Georeferencování není dostupné nebo obsahuje chybu:', georefResult);
    }
    
    // Zobrazení sekce mapy
    document.getElementById('mapSection').style.display = 'block';
    document.getElementById('mapSection').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Přizpůsobení mapy podle načtených dat
 */
function fitMapToData() {
    if (!map) return;
    
    const bounds = L.latLngBounds();
    let hasData = false;
    
    // Projít všechny vrstvy a najít bounds
    Object.values(mapLayers).forEach(layerGroup => {
        layerGroup.eachLayer(layer => {
            if (layer.getBounds) {
                bounds.extend(layer.getBounds());
                hasData = true;
            } else if (layer.getLatLng) {
                bounds.extend(layer.getLatLng());
                hasData = true;
            }
        });
    });
    
    if (hasData) {
        // Přizpůsobit viewport podle dat s malým paddingem
        map.fitBounds(bounds, { padding: [20, 20] });
        console.log('Mapa přizpůsobena podle dat:', bounds);
    } else {
        console.log('Žádná data pro přizpůsobení mapy');
    }
}

/**
 * Načtení vrstev do mapy
 */
function loadMapLayers(aiResult) {
    if (!aiResult || !aiResult.elements || aiResult.error) {
        console.log('AI výsledky neobsahují prvky nebo obsahují chybu:', aiResult);
        return;
    }
    
    const elements = aiResult.elements;
    const layerGroups = {};
    
    // Skupinování prvků podle typu
    elements.forEach(element => {
        if (!element || !element.element_type) {
            console.log('Prvek bez typu:', element);
            return;
        }
        
        const type = element.element_type;
        if (!layerGroups[type]) {
            layerGroups[type] = [];
        }
        layerGroups[type].push(element);
    });
    
    // Kontrola, zda byly nalezeny nějaké prvky
    if (Object.keys(layerGroups).length === 0) {
        console.log('Nebyly nalezeny žádné prvky pro zobrazení');
        return;
    }
    
    // Barvy pro různé typy prvků
    const colors = {
        'road': '#e74c3c',
        'water': '#3498db',
        'building': '#27ae60',
        'text': '#f39c12',
        'green_area': '#2ecc71'
    };
    
    // Vytvoření vrstev
    Object.keys(layerGroups).forEach(type => {
        const group = L.layerGroup();
        const color = colors[type] || '#95a5a6';
        
        layerGroups[type].forEach(element => {
            const geometry = element.geometry;
            let layer = null;
            
            console.log(`Zpracovávám element typu ${type}:`, geometry);
            
            if (geometry.type === 'Point') {
                layer = L.circleMarker([geometry.coordinates[1], geometry.coordinates[0]], {
                    radius: 5,
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.7
                });
            } else if (geometry.type === 'Polygon') {
                const coords = geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                layer = L.polygon(coords, {
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.3,
                    weight: 2
                });
            } else if (geometry.type === 'LineString') {
                const coords = geometry.coordinates.map(coord => [coord[1], coord[0]]);
                layer = L.polyline(coords, {
                    color: color,
                    weight: 3
                });
            }
            
            if (layer) {
                layer.bindPopup(`
                    <strong>Typ:</strong> ${type}<br>
                    <strong>Jistota:</strong> ${(element.confidence * 100).toFixed(1)}%<br>
                    <strong>Vlastnosti:</strong> ${JSON.stringify(element.properties)}
                `);
                group.addLayer(layer);
            }
        });
        
        mapLayers[type] = group;
    });
    
    // Přidání ovládání vrstev
    addLayerControl();
    
    // Přizpůsobit mapu podle načtených dat
    setTimeout(() => {
        fitMapToData();
    }, 100);
}

/**
 * Přidání ovládání vrstev
 */
function addLayerControl() {
    const layerList = document.getElementById('layerList');
    layerList.innerHTML = '';
    
    Object.keys(mapLayers).forEach(type => {
        const layerItem = document.createElement('div');
        layerItem.className = 'layer-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                map.addLayer(mapLayers[type]);
            } else {
                map.removeLayer(mapLayers[type]);
            }
        });
        
        const colorBox = document.createElement('div');
        colorBox.className = 'layer-color';
        colorBox.style.backgroundColor = getLayerColor(type);
        
        const label = document.createElement('label');
        label.textContent = getLayerName(type);
        
        layerItem.appendChild(checkbox);
        layerItem.appendChild(colorBox);
        layerItem.appendChild(label);
        layerList.appendChild(layerItem);
        
        // Přidání vrstvy do mapy
        map.addLayer(mapLayers[type]);
    });
}

/**
 * Získání barvy pro vrstvu
 */
function getLayerColor(type) {
    const colors = {
        'road': '#e74c3c',
        'water': '#3498db',
        'building': '#27ae60',
        'text': '#f39c12',
        'green_area': '#2ecc71'
    };
    return colors[type] || '#95a5a6';
}

/**
 * Získání názvu vrstvy
 */
function getLayerName(type) {
    const names = {
        'road': 'Silnice',
        'water': 'Vodní toky',
        'building': 'Budovy',
        'text': 'Texty',
        'green_area': 'Zelené plochy'
    };
    return names[type] || type;
}

/**
 * Aktualizace informací o mapě
 */
function updateMapInfo(georefResult) {
    if (!georefResult) {
        console.log('Georeferencování není dostupné');
        return;
    }
    
    document.getElementById('mapCRS').textContent = georefResult.target_crs || 'N/A';
    document.getElementById('mapAccuracy').textContent = 
        georefResult.accuracy_rmse ? `${georefResult.accuracy_rmse.toFixed(2)} m` : 'N/A';
}

/**
 * Zobrazení/skrytí progress baru
 */
function showProgressBar(show) {
    document.getElementById('progressContainer').style.display = show ? 'block' : 'none';
}

/**
 * Zobrazení/skrytí loading overlay
 */
function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

/**
 * Zobrazení toast notifikace
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Automatické odstranění po 5 sekundách
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

/**
 * Formátování velikosti souboru
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
