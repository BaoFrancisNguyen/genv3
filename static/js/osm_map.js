/**
 * Module de gestion de la carte OSM pour Malaysia Electricity Generator
 * VERSION OPTIMISÉE - Avec limitation automatique pour performance
 */

// Configuration de la carte
const MAP_CONFIG = {
    defaultCenter: [3.1390, 101.6869], // Kuala Lumpur
    defaultZoom: 11,
    maxZoom: 18,
    minZoom: 8,
    maxBuildings: 20000 // affichage max des bâtiments sur la carte
};

// État de la carte
let currentMap = null;
let buildingsLayer = null;
let currentBuildings = [];

/**
 * Initialise la carte OSM - VERSION CORRIGÉE
 */
function initializeMap(containerId = 'buildings-map') {
    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) {
        console.warn('❌ Conteneur de carte non trouvé:', containerId);
        return null;
    }
    
    // Vérification de Leaflet
    if (typeof L === 'undefined' || !L.map) {
        console.warn('⚠️ Leaflet non disponible - tentative de rechargement...');
        
        // Tentative de rechargement de Leaflet
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
        script.onload = () => {
            console.log('🔄 Leaflet rechargé, nouvelle tentative...');
            setTimeout(() => initializeMap(containerId), 500);
        };
        document.head.appendChild(script);
        
        showSimpleMapPlaceholder(mapContainer);
        return null;
    }
    
    try {
        // Nettoyage du conteneur
        mapContainer.innerHTML = '';
        
        // Vérification de la taille
        if (mapContainer.offsetHeight === 0) {
            mapContainer.style.height = '500px';
            console.log('📏 Hauteur de carte forcée à 500px');
        }
        
        // Création de la carte Leaflet
        currentMap = L.map(containerId, {
            zoomControl: true,
            scrollWheelZoom: true,
            doubleClickZoom: true,
            dragging: true
        }).setView(MAP_CONFIG.defaultCenter, MAP_CONFIG.defaultZoom);
        
        // Ajout de la couche de tuiles avec gestion d'erreur
        const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
            maxZoom: MAP_CONFIG.maxZoom,
            minZoom: MAP_CONFIG.minZoom,
            errorTileUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgZmlsbD0iI2Y5ZmFmYiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5Y2EzYWYiPkNhcnRlIG5vbiBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg=='
        });
        
        tileLayer.addTo(currentMap);
        
        // Création du groupe de couches pour les bâtiments
        buildingsLayer = L.layerGroup().addTo(currentMap);
        
        // Forcer un redimensionnement après initialisation
        setTimeout(() => {
            if (currentMap) {
                currentMap.invalidateSize();
                console.log('🔄 Taille de carte recalculée');
            }
        }, 100);
        
        console.log('✅ Carte OSM initialisée avec succès');
        return currentMap;
        
    } catch (error) {
        console.error('❌ Erreur initialisation carte:', error);
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
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border: 2px dashed #0891b2;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            color: #0f766e;
            min-height: 500px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: relative;
        ">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.7;">🗺️</div>
            <h3 style="margin: 0 0 0.5rem 0; color: #0f766e; font-size: 1.5rem;">Carte des Bâtiments</h3>
            <p style="margin: 0; max-width: 400px; line-height: 1.5;">
                <span id="map-buildings-count" style="font-weight: bold; color: #0891b2;">0</span> bâtiments chargés pour 
                <span id="map-zone-name" style="font-weight: bold; color: #0891b2;">zone sélectionnée</span>
            </p>
            <div style="margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: rgba(255,255,255,0.8); border-radius: 6px; border: 1px solid #67e8f9;">
                <small style="color: #0f766e; font-weight: 500;">
                    ⚠️ Carte interactive en cours de chargement...
                </small>
            </div>
            <button onclick="retryMapInitialization()" style="
                margin-top: 1rem;
                padding: 0.5rem 1rem;
                background: #0891b2;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9rem;
            ">
                🔄 Réessayer
            </button>
        </div>
    `;
}

/**
 * Retry de l'initialisation de carte
 */
function retryMapInitialization() {
    console.log('🔄 Nouvelle tentative d\'initialisation de carte...');
    const containerId = 'buildings-map';
    
    // Nettoyer l'état précédent
    if (currentMap) {
        try {
            currentMap.remove();
        } catch (e) {
            console.warn('Erreur nettoyage carte:', e);
        }
        currentMap = null;
        buildingsLayer = null;
    }
    
    // Nouvelle tentative
    setTimeout(() => {
        initializeMap(containerId);
    }, 500);
}

/**
 * Affiche les bâtiments sur la carte - VERSION OPTIMISÉE
 */
function displayBuildingsOnMap(buildings) {
    currentBuildings = buildings || [];
    
    console.log(`🏗️ Demande d'affichage de ${currentBuildings.length} bâtiments`);
    
    // OPTIMISATION: Limitation automatique pour performance
    if (currentBuildings.length > MAP_CONFIG.maxBuildings) {
        console.log(`🎯 Limitation automatique: ${currentBuildings.length} → échantillon de ~${MAP_CONFIG.maxBuildings}`);
        const step = Math.ceil(currentBuildings.length / MAP_CONFIG.maxBuildings);
        currentBuildings = currentBuildings.filter((_, index) => index % step === 0);
        console.log(`✅ Échantillon créé: ${currentBuildings.length} bâtiments (1 sur ${step})`);
        
        // Notification à l'utilisateur
        if (typeof showNotification === 'function') {
            showNotification(`Affichage optimisé: ${currentBuildings.length} bâtiments sur ${buildings.length} (échantillon)`, 'info');
        }
    }
    
    // Si pas de carte, essayer de l'initialiser
    if (!currentMap && typeof L !== 'undefined') {
        console.log('🔄 Initialisation de carte manquante, correction...');
        currentMap = initializeMap('buildings-map');
    }
    
    if (!currentMap || !buildingsLayer) {
        console.warn('⚠️ Carte non disponible, mise à jour placeholder');
        updateMapPlaceholder();
        return;
    }
    
    try {
        // Effacer les bâtiments existants
        buildingsLayer.clearLayers();
        
        if (!currentBuildings || currentBuildings.length === 0) {
            console.log('ℹ️ Aucun bâtiment à afficher');
            return;
        }
        
        // Couleurs par type de bâtiment
        const typeColors = {
            'residential': '#059669',    // Vert émeraude
            'commercial': '#2563eb',     // Bleu
            'office': '#7c3aed',         // Violet
            'industrial': '#dc2626',     // Rouge
            'hospital': '#ea580c',       // Orange
            'school': '#0891b2',         // Cyan
            'hotel': '#be185d',          // Rose
            'warehouse': '#65a30d',      // Lime
            'retail': '#0284c7',         // Bleu ciel
            'mixed_use': '#7c2d12',      // Marron
            'public': '#8b5cf6',         // Violet clair
            'default': '#6b7280'         // Gris
        };
        
        // Statistiques pour centrage et validation
        let bounds = [];
        let addedCount = 0;
        let validCoordinates = 0;
        let invalidCoordinates = 0;
        
        // Traitement des bâtiments avec gestion d'erreurs robuste
        currentBuildings.forEach((building, index) => {
            try {
                const lat = parseFloat(building.latitude);
                const lon = parseFloat(building.longitude);
                
                // Validation stricte des coordonnées
                if (isNaN(lat) || isNaN(lon) || 
                    lat < -90 || lat > 90 || 
                    lon < -180 || lon > 180) {
                    invalidCoordinates++;
                    return;
                }
                
                validCoordinates++;
                
                // Couleur selon le type
                const buildingType = building.building_type || 'default';
                const color = typeColors[buildingType] || typeColors.default;
                
                // Création du marqueur optimisé
                const marker = L.circleMarker([lat, lon], {
                    radius: 4,
                    fillColor: color,
                    color: 'white',
                    weight: 1,
                    opacity: 0.8,
                    fillOpacity: 0.6
                });
                
                // Popup optimisé (création à la demande)
                marker.on('click', function() {
                    const popupContent = createBuildingPopup(building, addedCount + 1);
                    marker.bindPopup(popupContent, {
                        maxWidth: 300,
                        className: 'building-popup'
                    }).openPopup();
                });
                
                // Ajout à la couche
                buildingsLayer.addLayer(marker);
                bounds.push([lat, lon]);
                addedCount++;
                
            } catch (error) {
                console.warn(`⚠️ Erreur affichage bâtiment ${index}:`, error);
                invalidCoordinates++;
            }
        });
        
        // Statistiques de traitement
        console.log(`📊 Traitement terminé:`);
        console.log(`   - Coordonnées valides: ${validCoordinates}`);
        console.log(`   - Coordonnées invalides: ${invalidCoordinates}`);
        console.log(`   - Marqueurs ajoutés: ${addedCount}`);
        
        // Centrage de la carte sur les bâtiments
        if (bounds.length > 0) {
            try {
                if (bounds.length === 1) {
                    // Un seul bâtiment
                    currentMap.setView(bounds[0], 16);
                } else {
                    // Plusieurs bâtiments - ajuster la vue
                    const group = new L.featureGroup(buildingsLayer.getLayers());
                    currentMap.fitBounds(group.getBounds(), { 
                        padding: [20, 20],
                        maxZoom: 15 
                    });
                }
                
                // Forcer le recalcul de taille
                setTimeout(() => {
                    if (currentMap) {
                        currentMap.invalidateSize();
                    }
                }, 200);
                
            } catch (error) {
                console.warn('⚠️ Erreur centrage carte:', error);
                // Fallback sur position par défaut
                currentMap.setView(MAP_CONFIG.defaultCenter, MAP_CONFIG.defaultZoom);
            }
        }
        
        console.log(`✅ ${addedCount} bâtiments affichés sur la carte`);
        
        // Ajout de la légende améliorée
        updateMapLegend(currentBuildings);
        
        // Afficher la section carte si masquée
        if (typeof showMapSection === 'function') {
            showMapSection();
        }
        
    } catch (error) {
        console.error('❌ Erreur affichage bâtiments sur carte:', error);
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
        
        // Animation du nombre
        countEl.style.transition = 'all 0.3s ease';
        countEl.style.transform = 'scale(1.1)';
        countEl.style.color = '#0891b2';
        setTimeout(() => {
            countEl.style.transform = 'scale(1)';
        }, 300);
    }
    
    if (zoneEl && window.currentZone) {
        zoneEl.textContent = window.currentZone.replace('_', ' ');
    }
}

/**
 * Crée le contenu du popup pour un bâtiment - VERSION ENRICHIE
 */
function createBuildingPopup(building, index) {
    const type = building.building_type || 'Non spécifié';
    const surface = building.surface_area_m2 ? 
        `${building.surface_area_m2.toFixed(0)} m²` : 'Non spécifiée';
    const consumption = building.base_consumption_kwh ? 
        `${building.base_consumption_kwh.toFixed(3)} kWh/h` : 'Non calculée';
    
    // Icône selon le type
    const typeIcons = {
        'residential': '🏠',
        'commercial': '🏪',
        'office': '🏢',
        'industrial': '🏭',
        'hospital': '🏥',
        'school': '🏫',
        'hotel': '🏨',
        'warehouse': '🏬',
        'retail': '🛍️',
        'mixed_use': '🏗️',
        'public': '🏛️',
        'default': '🏗️'
    };
    
    const icon = typeIcons[building.building_type] || typeIcons.default;
    
    return `
        <div style="min-width: 250px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
            <div style="
                background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%);
                color: white;
                padding: 0.75rem;
                margin: -10px -10px 0.75rem -10px;
                border-radius: 6px 6px 0 0;
                text-align: center;
            ">
                <h4 style="margin: 0; font-size: 1.1rem;">
                    ${icon} Bâtiment #${index}
                </h4>
            </div>
            
            <div style="font-size: 0.9rem; line-height: 1.4;">
                <div style="display: grid; gap: 0.5rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: #374151;">Type:</strong> 
                        <span style="color: #059669; font-weight: 500;">${type}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: #374151;">Position:</strong> 
                        <span style="font-family: monospace; font-size: 0.8rem; color: #6b7280;">
                            ${building.latitude?.toFixed(4)}, ${building.longitude?.toFixed(4)}
                        </span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: #374151;">Surface:</strong> 
                        <span style="color: #2563eb; font-weight: 500;">${surface}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: #374151;">Consommation:</strong> 
                        <span style="color: #dc2626; font-weight: 500;">${consumption}</span>
                    </div>
                    
                    ${building.floors_count ? `
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color: #374151;">Étages:</strong> 
                        <span style="color: #7c3aed; font-weight: 500;">${building.floors_count}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            <div style="
                margin-top: 0.75rem;
                padding-top: 0.5rem;
                border-top: 1px solid #e5e7eb;
                text-align: center;
                font-size: 0.75rem;
                color: #9ca3af;
            ">
                Cliquez pour fermer
            </div>
        </div>
    `;
}

/**
 * Met à jour la légende de la carte - VERSION AMÉLIORÉE
 */
function updateMapLegend(buildings) {
    if (!currentMap) return;
    
    // Supprimer la légende existante
    if (currentMap.legendControl) {
        currentMap.removeControl(currentMap.legendControl);
    }
    
    // Comptage par type avec gestion des erreurs
    const typeCounts = {};
    const typeColors = {
        'residential': '#059669',
        'commercial': '#2563eb',
        'office': '#7c3aed',
        'industrial': '#dc2626',
        'hospital': '#ea580c',
        'school': '#0891b2',
        'hotel': '#be185d',
        'warehouse': '#65a30d',
        'retail': '#0284c7',
        'mixed_use': '#7c2d12',
        'public': '#8b5cf6',
        'default': '#6b7280'
    };
    
    buildings.forEach(building => {
        const type = building.building_type || 'default';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    
    // Création de la légende enrichie
    const legend = L.control({ position: 'bottomright' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.style.cssText = `
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            font-size: 0.85rem;
            max-width: 250px;
            max-height: 400px;
            overflow-y: auto;
        `;
        
        let html = `
            <div style="
                text-align: center;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 0.75rem;
                margin-bottom: 0.75rem;
            ">
                <h4 style="
                    margin: 0;
                    font-size: 1rem;
                    color: #1f2937;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                ">
                    🏗️ Types de Bâtiments
                </h4>
                <p style="
                    margin: 0.25rem 0 0 0;
                    font-size: 0.75rem;
                    color: #6b7280;
                ">
                    ${buildings.length.toLocaleString()} bâtiments affichés
                </p>
            </div>
        `;
        
        // Tri et affichage des types
        Object.entries(typeCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 8)
            .forEach(([type, count]) => {
                const color = typeColors[type] || typeColors.default;
                const percentage = ((count / buildings.length) * 100).toFixed(1);
                
                // Noms français des types
                const typeNames = {
                    'residential': 'Résidentiel',
                    'commercial': 'Commercial',
                    'office': 'Bureau',
                    'industrial': 'Industriel',
                    'hospital': 'Médical',
                    'school': 'Scolaire',
                    'hotel': 'Hôtellerie',
                    'warehouse': 'Entrepôt',
                    'retail': 'Commerce',
                    'mixed_use': 'Mixte',
                    'public': 'Public',
                    'default': 'Non spécifié'
                };
                
                const displayName = typeNames[type] || type;
                
                html += `
                    <div style="
                        display: flex;
                        align-items: center;
                        margin-bottom: 0.5rem;
                        padding: 0.25rem;
                        border-radius: 4px;
                        background: rgba(0,0,0,0.02);
                        transition: all 0.2s ease;
                    "
                    onmouseover="this.style.background='rgba(0,0,0,0.05)'"
                    onmouseout="this.style.background='rgba(0,0,0,0.02)'"
                    >
                        <div style="
                            width: 16px;
                            height: 16px;
                            background: ${color};
                            border-radius: 50%;
                            margin-right: 0.75rem;
                            border: 2px solid white;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                        "></div>
                        <div style="flex: 1;">
                            <div style="
                                font-size: 0.8rem;
                                color: #374151;
                                font-weight: 500;
                                line-height: 1.2;
                            ">${displayName}</div>
                            <div style="
                                font-size: 0.7rem;
                                color: #6b7280;
                            ">${count} (${percentage}%)</div>
                        </div>
                    </div>
                `;
            });
        
        div.innerHTML = html;
        
        // Empêcher la propagation des clics sur la légende
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        
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
        console.info('ℹ️ Carte non disponible pour centrage');
        return;
    }
    
    try {
        currentMap.setView([lat, lon], zoom);
        
        // Forcer recalcul après centrage
        setTimeout(() => {
            if (currentMap) {
                currentMap.invalidateSize();
            }
        }, 100);
        
        console.log(`🎯 Carte centrée sur ${lat}, ${lon} (zoom: ${zoom})`);
        
    } catch (error) {
        console.error('❌ Erreur centrage carte:', error);
    }
}

/**
 * Efface tous les bâtiments de la carte
 */
function clearBuildings() {
    if (buildingsLayer) {
        buildingsLayer.clearLayers();
        console.log('🧹 Bâtiments effacés de la carte');
    }
    
    if (currentMap && currentMap.legendControl) {
        currentMap.removeControl(currentMap.legendControl);
        currentMap.legendControl = null;
    }
    
    currentBuildings = [];
    updateMapPlaceholder();
}

/**
 * Retourne les informations de la carte
 */
function getMapInfo() {
    return {
        initialized: !!currentMap,
        buildingsCount: currentBuildings.length,
        center: currentMap ? currentMap.getCenter() : null,
        zoom: currentMap ? currentMap.getZoom() : null,
        bounds: currentMap && buildingsLayer ? buildingsLayer.getBounds() : null,
        maxBuildings: MAP_CONFIG.maxBuildings
    };
}

/**
 * Diagnostic de la carte
 */
function diagnoseMap() {
    const info = {
        leafletAvailable: typeof L !== 'undefined',
        leafletVersion: typeof L !== 'undefined' ? L.version : 'N/A',
        mapInitialized: !!currentMap,
        mapContainer: !!document.getElementById('buildings-map'),
        buildingsLayer: !!buildingsLayer,
        buildingsCount: currentBuildings.length,
        maxBuildings: MAP_CONFIG.maxBuildings
    };
    
    console.table(info);
    return info;
}

/**
 * Change la limite de bâtiments affichés
 */
function setMaxBuildings(newLimit) {
    const oldLimit = MAP_CONFIG.maxBuildings;
    MAP_CONFIG.maxBuildings = newLimit;
    
    console.log(`🔧 Limite changée: ${oldLimit} → ${newLimit} bâtiments`);
    
    // Réafficher si nécessaire
    if (currentBuildings.length > 0) {
        displayBuildingsOnMap(currentBuildings);
    }
}

// Export global des fonctions pour l'accès depuis d'autres scripts
if (typeof window !== 'undefined') {
    window.MapFunctions = {
        initializeMap,
        displayBuildingsOnMap,
        centerMap,
        clearBuildings,
        getMapInfo,
        diagnoseMap,
        retryMapInitialization,
        setMaxBuildings
    };
}

console.log('✅ Module osm_map.js chargé - Version optimisée avec limitation automatique');
console.log(`📊 Limite actuelle: ${MAP_CONFIG.maxBuildings} bâtiments max`);