/**
 * Module de gestion de la carte OSM pour Malaysia Electricity Generator
 * Interface épurée pour affichage des bâtiments
 */

// Configuration de la carte
const MAP_CONFIG = {
    defaultCenter: [3.1390, 101.6869], // Kuala Lumpur
    defaultZoom: 11,
    maxZoom: 18,
    minZoom: 8
};

// État de la carte
let currentMap = null;
let buildingsLayer = null;
let currentBuildings = [];

/**
 * Initialise la carte OSM simple
 */
function initializeMap(containerId = 'buildings-map') {
    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) {
        console.warn('Conteneur de carte non trouvé:', containerId);
        return null;
    }
    
    // Vérification si Leaflet est disponible (optionnel)
    if (typeof L === 'undefined') {
        console.info('Leaflet non disponible - affichage simplifié');
        showSimpleMapPlaceholder(mapContainer);
        return null;
    }
    
    try {
        // Création de la carte Leaflet
        currentMap = L.map(containerId).setView(MAP_CONFIG.defaultCenter, MAP_CONFIG.defaultZoom);
        
        // Ajout de la couche de tuiles OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: MAP_CONFIG.maxZoom,
            minZoom: MAP_CONFIG.minZoom
        }).addTo(currentMap);
        
        // Création du groupe de couches pour les bâtiments
        buildingsLayer = L.layerGroup().addTo(currentMap);
        
        console.log('✅ Carte OSM initialisée');
        return currentMap;
        
    } catch (error) {
        console.error('Erreur initialisation carte:', error);
        showSimpleMapPlaceholder(mapContainer);
        return null;
    }
}

/**
 * Affiche un placeholder simple sans carte interactive
 */
function showSimpleMapPlaceholder(container) {
    container.innerHTML = `
        <div style="
            background: var(--gray-100);
            border: 2px dashed var(--gray-200);
            border-radius: var(--border-radius);
            padding: 2rem;
            text-align: center;
            color: var(--gray-500);
            min-height: 300px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🗺️</div>
            <h3 style="margin: 0 0 0.5rem 0; color: var(--gray-700);">Carte des Bâtiments</h3>
            <p style="margin: 0; max-width: 400px;">
                <span id="map-buildings-count">0</span> bâtiments chargés pour 
                <span id="map-zone-name">zone sélectionnée</span>
            </p>
            <small style="margin-top: 1rem; color: var(--gray-400);">
                Carte interactive disponible avec Leaflet.js
            </small>
        </div>
    `;
}

/**
 * Affiche les bâtiments sur la carte
 */
function displayBuildingsOnMap(buildings) {
    currentBuildings = buildings || [];
    
    if (!currentMap || !buildingsLayer) {
        // Mise à jour du placeholder
        updateMapPlaceholder();
        return;
    }
    
    try {
        // Effacer les bâtiments existants
        buildingsLayer.clearLayers();
        
        if (!buildings || buildings.length === 0) {
            console.info('Aucun bâtiment à afficher');
            return;
        }
        
        // Couleurs par type de bâtiment
        const typeColors = {
            'residential': '#059669', // Vert
            'commercial': '#2563eb',  // Bleu
            'office': '#7c3aed',      // Violet
            'industrial': '#dc2626',  // Rouge
            'hospital': '#ea580c',    // Orange
            'school': '#0891b2',      // Cyan
            'hotel': '#be185d',       // Rose
            'warehouse': '#65a30d',   // Lime
            'default': '#6b7280'      // Gris
        };
        
        // Statistiques pour centrage
        let bounds = [];
        let addedCount = 0;
        
        buildings.forEach(building => {
            try {
                const lat = parseFloat(building.latitude);
                const lon = parseFloat(building.longitude);
                
                // Validation des coordonnées
                if (isNaN(lat) || isNaN(lon) || 
                    lat < -90 || lat > 90 || 
                    lon < -180 || lon > 180) {
                    return;
                }
                
                // Couleur selon le type
                const color = typeColors[building.building_type] || typeColors.default;
                
                // Création du marqueur
                const marker = L.circleMarker([lat, lon], {
                    radius: 4,
                    fillColor: color,
                    color: 'white',
                    weight: 1,
                    opacity: 0.8,
                    fillOpacity: 0.6
                });
                
                // Popup avec informations
                const popupContent = createBuildingPopup(building);
                marker.bindPopup(popupContent);
                
                // Ajout à la couche
                buildingsLayer.addLayer(marker);
                bounds.push([lat, lon]);
                addedCount++;
                
            } catch (error) {
                console.warn('Erreur affichage bâtiment:', error);
            }
        });
        
        // Centrage de la carte sur les bâtiments
        if (bounds.length > 0) {
            if (bounds.length === 1) {
                currentMap.setView(bounds[0], 15);
            } else {
                currentMap.fitBounds(bounds, { padding: [20, 20] });
            }
        }
        
        console.log(`✅ ${addedCount} bâtiments affichés sur la carte`);
        
        // Ajout de la légende
        updateMapLegend(buildings);
        
    } catch (error) {
        console.error('Erreur affichage bâtiments sur carte:', error);
    }
}

/**
 * Met à jour le placeholder de carte
 */
function updateMapPlaceholder() {
    const countEl = document.getElementById('map-buildings-count');
    const zoneEl = document.getElementById('map-zone-name');
    
    if (countEl) {
        countEl.textContent = currentBuildings.length.toLocaleString('fr-FR');
    }
    
    if (zoneEl && window.currentZone) {
        zoneEl.textContent = window.currentZone.replace('_', ' ');
    }
}

/**
 * Crée le contenu du popup pour un bâtiment
 */
function createBuildingPopup(building) {
    const type = building.building_type || 'Non spécifié';
    const surface = building.surface_area_m2 ? 
        `${building.surface_area_m2.toFixed(0)} m²` : 'Non spécifiée';
    const consumption = building.base_consumption_kwh ? 
        `${building.base_consumption_kwh.toFixed(3)} kWh/h` : 'Non calculée';
    
    return `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">
                🏗️ Bâtiment
            </h4>
            <div style="font-size: 0.9rem;">
                <p style="margin: 0.25rem 0;"><strong>Type:</strong> ${type}</p>
                <p style="margin: 0.25rem 0;"><strong>Position:</strong> ${building.latitude?.toFixed(4)}, ${building.longitude?.toFixed(4)}</p>
                <p style="margin: 0.25rem 0;"><strong>Surface:</strong> ${surface}</p>
                <p style="margin: 0.25rem 0;"><strong>Consommation base:</strong> ${consumption}</p>
                ${building.floors_count ? `<p style="margin: 0.25rem 0;"><strong>Étages:</strong> ${building.floors_count}</p>` : ''}
            </div>
        </div>
    `;
}

/**
 * Met à jour la légende de la carte
 */
function updateMapLegend(buildings) {
    if (!currentMap) return;
    
    // Supprimer la légende existante
    if (currentMap.legendControl) {
        currentMap.removeControl(currentMap.legendControl);
    }
    
    // Comptage par type
    const typeCounts = {};
    buildings.forEach(building => {
        const type = building.building_type || 'unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    
    // Création de la légende
    const legend = L.control({ position: 'bottomright' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.style.cssText = `
            background: white;
            padding: 0.75rem;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            font-size: 0.85rem;
            max-width: 200px;
        `;
        
        let html = '<h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">Types de bâtiments</h4>';
        
        // Couleurs (même que dans displayBuildingsOnMap)
        const typeColors = {
            'residential': '#059669',
            'commercial': '#2563eb',
            'office': '#7c3aed',
            'industrial': '#dc2626',
            'hospital': '#ea580c',
            'school': '#0891b2',
            'hotel': '#be185d',
            'warehouse': '#65a30d',
            'default': '#6b7280'
        };
        
        Object.entries(typeCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 8) // Top 8 types
            .forEach(([type, count]) => {
                const color = typeColors[type] || typeColors.default;
                html += `
                    <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                        <div style="
                            width: 12px; 
                            height: 12px; 
                            background: ${color}; 
                            border-radius: 50%; 
                            margin-right: 0.5rem;
                            border: 1px solid white;
                        "></div>
                        <span style="font-size: 0.8rem;">${type} (${count})</span>
                    </div>
                `;
            });
        
        div.innerHTML = html;
        return div;
    };
    
    currentMap.legendControl = legend;
    legend.addTo(currentMap);
}

/**
 * Centre la carte sur une position
 */
function centerMap(lat, lon, zoom = 13) {
    if (!currentMap) {
        console.info('Carte non disponible pour centrage');
        return;
    }
    
    try {
        currentMap.setView([lat, lon], zoom);
    } catch (error) {
        console.error('Erreur centrage carte:', error);
    }
}

/**
 * Efface tous les bâtiments de la carte
 */
function clearBuildings() {
    if (buildingsLayer) {
        buildingsLayer.clearLayers();
    }
    
    if (currentMap && currentMap.legendControl) {
        currentMap.removeControl(currentMap.legendControl);
    }
    
    currentBuildings = [];
    updateMapPlaceholder();
}

/**
 * Retourne les informations de la carte
 */