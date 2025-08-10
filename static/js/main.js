/**
 * JavaScript principal pour Malaysia Electricity Generator
 * Interface épurée et fonctionnelle - Version complète
 */

// ==============================================================================
// CONFIGURATION GLOBALE
// ==============================================================================

const API_BASE = '/api';
const APP_CONFIG = {
    maxBuildings: 10000,
    defaultFrequency: '30T',
    notificationTimeout: 5000,
    progressUpdateInterval: 500,
    apiTimeout: 300000, // 5 minutes
    retryAttempts: 3
};

// État global de l'application
let appState = {
    currentZone: null,
    currentBuildings: [],
    generatedData: null,
    isLoading: false,
    activeRequests: new Set()
};

// Cache simple pour éviter les requêtes répétées
const cache = new Map();

// ==============================================================================
// UTILITAIRES GÉNÉRAUX
// ==============================================================================

/**
 * Affiche une notification utilisateur
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notifications = document.getElementById('notifications');
    if (!notifications) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Icônes selon le type
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    notification.innerHTML = `
        <span>${icons[type] || ''} ${message}</span>
        <button onclick="this.parentElement.remove()" style="
            background: none; 
            border: none; 
            color: inherit; 
            font-size: 1.2em; 
            cursor: pointer; 
            margin-left: 1rem;
        ">×</button>
    `;
    
    notifications.appendChild(notification);
    
    // Auto-suppression
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
    
    // Animation d'entrée
    requestAnimationFrame(() => {
        notification.style.transform = 'translateX(0)';
        notification.style.opacity = '1';
    });
}

/**
 * Met à jour le statut global de l'application
 */
function updateStatus(message, isLoading = false) {
    const statusText = document.getElementById('status-text');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    if (statusText) {
        statusText.textContent = message;
    }
    
    if (loadingIndicator) {
        loadingIndicator.classList.toggle('hidden', !isLoading);
    }
    
    appState.isLoading = isLoading;
}

/**
 * Affiche/cache l'indicateur de chargement
 */
function showLoading(show = true) {
    updateStatus(show ? 'Chargement...' : 'Prêt', show);
}

/**
 * Formate un nombre avec séparateurs français
 */
function formatNumber(num) {
    if (typeof num !== 'number') return num;
    return new Intl.NumberFormat('fr-FR').format(num);
}

/**
 * Formate une taille de fichier
 */
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = bytes / Math.pow(1024, i);
    
    return `${size.toFixed(1)} ${sizes[i]}`;
}

/**
 * Formate une durée en secondes
 */
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (minutes < 60) {
        return `${minutes}m ${remainingSeconds}s`;
    }
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    return `${hours}h ${remainingMinutes}m`;
}

/**
 * Debounce pour limiter les appels de fonction
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Génère un ID unique pour les requêtes
 */
function generateRequestId() {
    return Math.random().toString(36).substr(2, 9);
}

// ==============================================================================
// GESTION DES REQUÊTES API
// ==============================================================================

/**
 * Effectue une requête API avec gestion d'erreurs complète
 */
async function apiRequest(url, options = {}) {
    const requestId = generateRequestId();
    const fullUrl = API_BASE + url;
    
    // Configuration par défaut
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        timeout: APP_CONFIG.apiTimeout
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    // Gestion du timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), finalOptions.timeout);
    finalOptions.signal = controller.signal;
    
    try {
        appState.activeRequests.add(requestId);
        
        console.log(`🔄 API Request: ${finalOptions.method || 'GET'} ${fullUrl}`);
        
        const response = await fetch(fullUrl, finalOptions);
        clearTimeout(timeoutId);
        
        // Vérification du type de contenu
        const contentType = response.headers.get('content-type');
        
        let data;
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            // Pour les téléchargements de fichiers
            data = response;
        }
        
        if (!response.ok) {
            const errorMessage = data?.error || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMessage);
        }
        
        console.log(`✅ API Success: ${fullUrl}`);
        return data;
        
    } catch (error) {
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            throw new Error('Requête interrompue - timeout dépassé');
        }
        
        console.error(`❌ API Error: ${fullUrl}`, error);
        throw error;
        
    } finally {
        appState.activeRequests.delete(requestId);
    }
}

/**
 * Requête avec retry automatique
 */
async function apiRequestWithRetry(url, options = {}, maxRetries = 3) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            return await apiRequest(url, options);
        } catch (error) {
            lastError = error;
            
            if (attempt < maxRetries) {
                const delay = Math.pow(2, attempt) * 1000; // Backoff exponentiel
                console.warn(`⚠️ Tentative ${attempt}/${maxRetries} échouée, retry dans ${delay}ms`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw lastError;
}

/**
 * Annule toutes les requêtes en cours
 */
function cancelAllRequests() {
    appState.activeRequests.clear();
    console.log('🛑 Toutes les requêtes annulées');
}

// ==============================================================================
// GESTION DU CACHE
// ==============================================================================

/**
 * Met en cache une réponse API
 */
function setCacheValue(key, value, ttl = 300000) { // 5 minutes par défaut
    cache.set(key, {
        value,
        expires: Date.now() + ttl
    });
}

/**
 * Récupère une valeur du cache
 */
function getCacheValue(key) {
    const cached = cache.get(key);
    
    if (!cached) return null;
    
    if (Date.now() > cached.expires) {
        cache.delete(key);
        return null;
    }
    
    return cached.value;
}

/**
 * Vide le cache
 */
function clearCache() {
    cache.clear();
    console.log('🗑️ Cache vidé');
}

// ==============================================================================
// GESTION DU SÉLECTEUR DE ZONE
// ==============================================================================

/**
 * Initialise le sélecteur de zone Malaysia
 */
function initializeZoneSelector() {
    const zoneSelect = document.getElementById('zone-select');
    const zoneInfo = document.getElementById('zone-info');
    const loadOsmBtn = document.getElementById('load-osm-btn');
    
    if (!zoneSelect) return;
    
    // Gestionnaire de changement de zone
    zoneSelect.addEventListener('change', handleZoneChange);
    
    // Gestionnaire de chargement OSM
    if (loadOsmBtn) {
        loadOsmBtn.addEventListener('click', handleLoadOSMBuildings);
    }
    
    console.log('✅ Sélecteur de zone initialisé');
}

/**
 * Gère le changement de zone
 */
async function handleZoneChange(event) {
    const zoneName = event.target.value;
    const zoneInfo = document.getElementById('zone-info');
    const loadOsmBtn = document.getElementById('load-osm-btn');
    
    // Reset de l'état
    hideAllSections(['osm-section', 'generation-section', 'results-section', 'export-section']);
    
    if (!zoneName) {
        zoneInfo?.classList.add('hidden');
        return;
    }
    
    try {
        showLoading(true);
        updateStatus('Récupération des informations de zone...');
        
        // Vérifier le cache d'abord
        const cacheKey = `zone_estimation_${zoneName}`;
        let data = getCacheValue(cacheKey);
        
        if (!data) {
            data = await apiRequest(`/zone-estimation/${zoneName}`);
            setCacheValue(cacheKey, data);
        }
        
        if (data.success) {
            const estimation = data.estimation;
            
            // Mise à jour de l'interface
            updateZoneInfo(estimation);
            displayZoneWarnings(estimation);
            
            // Activation des contrôles
            zoneInfo?.classList.remove('hidden');
            if (loadOsmBtn) {
                loadOsmBtn.disabled = false;
            }
            
            appState.currentZone = zoneName;
            updateStatus(`Zone "${estimation.zone_name}" sélectionnée`);
            
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
        
    } catch (error) {
        console.error('Erreur sélection zone:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
        updateStatus('Erreur de sélection de zone');
    } finally {
        showLoading(false);
    }
}

/**
 * Met à jour les informations de zone dans l'interface
 */
function updateZoneInfo(estimation) {
    const elements = {
        'zone-buildings': formatNumber(estimation.estimated_buildings),
        'zone-time': `${estimation.estimated_time_minutes} min`,
        'zone-size': `${estimation.estimated_size_mb} MB`,
        'zone-complexity': estimation.complexity_level
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            
            // Animation de mise à jour
            element.style.transition = 'color 0.3s ease';
            element.style.color = 'var(--primary-color)';
            setTimeout(() => {
                element.style.color = '';
            }, 1000);
        }
    });
}

/**
 * Affiche les avertissements pour une zone
 */
function displayZoneWarnings(estimation) {
    const warningsDiv = document.getElementById('zone-warnings');
    if (!warningsDiv) return;
    
    const warnings = estimation.warnings || [];
    const recommendations = estimation.recommendations || [];
    
    if (warnings.length === 0 && recommendations.length === 0) {
        warningsDiv.classList.add('hidden');
        return;
    }
    
    let html = '';
    
    warnings.forEach(warning => {
        html += `<div class="warning">⚠️ ${warning}</div>`;
    });
    
    recommendations.forEach(rec => {
        html += `<div class="warning" style="background: #e0f2fe; border-color: #0288d1; color: #0277bd;">💡 ${rec}</div>`;
    });
    
    warningsDiv.innerHTML = html;
    warningsDiv.classList.remove('hidden');
}

// ==============================================================================
// GESTION DES BÂTIMENTS OSM
// ==============================================================================

/**
 * Charge les bâtiments OSM pour la zone sélectionnée
 */
async function handleLoadOSMBuildings() {
    if (!appState.currentZone) {
        showNotification('Aucune zone sélectionnée', 'error');
        return;
    }
    
    const loadBtn = document.getElementById('load-osm-btn');
    
    try {
        showLoading(true);
        updateStatus('Chargement des bâtiments OSM...');
        if (loadBtn) loadBtn.disabled = true;
        
        // Afficher le progress
        showProgress('Chargement des données OpenStreetMap...', 0);
        
        // Simulation du progrès
        const progressInterval = setInterval(() => {
            updateProgress(Math.random() * 30 + 10, 'Récupération des bâtiments...');
        }, 1000);
        
        const data = await apiRequestWithRetry(`/osm-buildings/${appState.currentZone}`, {
            method: 'POST'
        });
        
        clearInterval(progressInterval);
        hideProgress();
        
        if (data.success) {
            appState.currentBuildings = data.buildings;
            
            // Mise à jour de l'interface OSM
            updateOSMInterface(data);
            
            // Notification du succès avec carte OSM
            if (window.OSMMap) {
                window.OSMMap.onBuildingsLoaded(data.buildings, appState.currentZone);
            }
            
            // Affichage des sections suivantes
            showSection('osm-section');
            showSection('generation-section');
            
            showNotification(
                `${formatNumber(data.buildings.length)} bâtiments chargés avec succès!`, 
                'success'
            );
            updateStatus(`${data.buildings.length} bâtiments OSM chargés`);
            
            // Estimation automatique de génération
            updateGenerationEstimate();
            
        } else {
            throw new Error(data.error || 'Erreur de chargement OSM');
        }
        
    } catch (error) {
        hideProgress();
        console.error('Erreur chargement OSM:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
        updateStatus('Erreur de chargement OSM');
    } finally {
        showLoading(false);
        if (loadBtn) loadBtn.disabled = false;
    }
}

/**
 * Met à jour l'interface après chargement OSM
 */
function updateOSMInterface(data) {
    // Mise à jour des statistiques
    const elements = {
        'buildings-count': formatNumber(data.buildings.length),
        'building-types': new Set(data.buildings.map(b => b.building_type)).size,
        'data-quality': data.metadata?.quality_metrics?.quality_score ? 
                       `${data.metadata.quality_metrics.quality_score}%` : 'N/A'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Mise à jour de la distribution des types
    updateBuildingDistribution(data.buildings);
    
    // Mise à jour de la carte si disponible
    updateMapCenter(data.buildings);
}

/**
 * Met à jour la visualisation de distribution des bâtiments
 */
function updateBuildingDistribution(buildings) {
    const distributionDiv = document.getElementById('building-distribution');
    if (!distributionDiv) return;
    
    // Comptage par type
    const typeCounts = {};
    buildings.forEach(building => {
        const type = building.building_type || 'unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    
    // Tri par fréquence
    const sortedTypes = Object.entries(typeCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 8); // Top 8
    
    const total = buildings.length;
    
    // Génération du HTML
    let html = '<h4>📊 Répartition par type de bâtiment</h4>';
    
    sortedTypes.forEach(([type, count]) => {
        const percentage = ((count / total) * 100).toFixed(1);
        const color = getTypeColor(type);
        
        html += `
            <div class="type-bar" style="margin-bottom: 0.75rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span style="font-weight: 500; display: flex; align-items: center;">
                        <div style="
                            width: 12px; 
                            height: 12px; 
                            background: ${color}; 
                            border-radius: 50%; 
                            margin-right: 0.5rem;
                        "></div>
                        ${type}
                    </span>
                    <span style="color: var(--gray-500); font-size: 0.9rem;">
                        ${formatNumber(count)} (${percentage}%)
                    </span>
                </div>
                <div style="background: var(--gray-200); height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="
                        background: ${color}; 
                        height: 100%; 
                        width: ${percentage}%; 
                        border-radius: 3px;
                        transition: width 0.5s ease;
                    "></div>
                </div>
            </div>
        `;
    });
    
    distributionDiv.innerHTML = html;
}

/**
 * Retourne une couleur pour un type de bâtiment
 */
function getTypeColor(type) {
    const colors = {
        'residential': '#059669',
        'commercial': '#2563eb',
        'office': '#7c3aed',
        'industrial': '#dc2626',
        'hospital': '#ea580c',
        'school': '#0891b2',
        'hotel': '#be185d',
        'warehouse': '#65a30d',
        'retail': '#0284c7',
        'mixed_use': '#7c2d12'
    };
    return colors[type] || '#6b7280';
}

/**
 * Met à jour le centre de la carte
 */
function updateMapCenter(buildings) {
    if (!buildings.length) return;
    
    // Calcul du centroïde
    let totalLat = 0, totalLon = 0, validCount = 0;
    
    buildings.forEach(building => {
        if (building.latitude && building.longitude) {
            totalLat += building.latitude;
            totalLon += building.longitude;
            validCount++;
        }
    });
    
    if (validCount > 0) {
        const centerLat = totalLat / validCount;
        const centerLon = totalLon / validCount;
        
        // Mise à jour du placeholder de carte
        const mapCenter = document.getElementById('map-center');
        if (mapCenter) {
            mapCenter.textContent = `${centerLat.toFixed(4)}, ${centerLon.toFixed(4)}`;
        }
        
        // Mise à jour de la carte interactive si disponible
        if (window.OSMMap) {
            window.OSMMap.centerMap(centerLat, centerLon);
        }
    }
}

// ==============================================================================
// GESTION DE LA GÉNÉRATION
// ==============================================================================

/**
 * Initialise le formulaire de génération
 */
function initializeGenerationForm() {
    const form = document.getElementById('generation-form');
    const estimateBtn = document.getElementById('estimate-btn');
    
    if (!form) return;
    
    // Gestionnaire d'estimation
    if (estimateBtn) {
        estimateBtn.addEventListener('click', updateGenerationEstimate);
    }
    
    // Mise à jour automatique lors des changements
    const fieldsToWatch = ['start-date', 'end-date', 'frequency'];
    fieldsToWatch.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', debounce(updateGenerationEstimate, 500));
        }
    });
    
    // Gestionnaire de soumission du formulaire
    form.addEventListener('submit', handleGeneration);
    
    console.log('✅ Formulaire de génération initialisé');
}

/**
 * Met à jour l'estimation de génération
 */
async function updateGenerationEstimate() {
    if (!appState.currentBuildings.length) {
        console.log('Pas de bâtiments pour estimation');
        return;
    }
    
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const frequency = document.getElementById('frequency')?.value;
    
    if (!startDate || !endDate) {
        console.log('Dates manquantes pour estimation');
        return;
    }
    
    try {
        const params = {
            num_buildings: appState.currentBuildings.length,
            start_date: startDate,
            end_date: endDate,
            frequency: frequency || 'D'
        };
        
        const cacheKey = `estimation_${JSON.stringify(params)}`;
        let data = getCacheValue(cacheKey);
        
        if (!data) {
            data = await apiRequest('/estimate-generation', {
                method: 'POST',
                body: JSON.stringify(params)
            });
            setCacheValue(cacheKey, data, 60000); // Cache 1 minute
        }
        
        if (data.success && data.estimation) {
            updateEstimationDisplay(data.estimation);
            enableGenerationButton(true);
        }
        
    } catch (error) {
        console.error('Erreur estimation:', error);
        showNotification('Erreur lors de l\'estimation', 'warning');
    }
}

/**
 * Met à jour l'affichage de l'estimation
 */
function updateEstimationDisplay(estimation) {
    const elements = {
        'estimate-observations': formatNumber(estimation.total_data_points),
        'estimate-time': estimation.estimated_duration_formatted || formatDuration(estimation.estimated_duration_seconds || 0),
        'estimate-size': `${estimation.estimated_size_mb} MB`
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            // Animation de mise à jour
            element.classList.add('updated');
            setTimeout(() => element.classList.remove('updated'), 500);
        }
    });
    
    // Affichage de la complexité
    const complexity = estimation.complexity_level;
    if (complexity === 'très_complexe') {
        showNotification('Génération complexe - prévoir du temps', 'warning', 3000);
    }
}

/**
 * Active/désactive le bouton de génération
 */
function enableGenerationButton(enabled) {
    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.disabled = !enabled;
        
        if (enabled) {
            generateBtn.classList.add('ready');
        } else {
            generateBtn.classList.remove('ready');
        }
    }
}

/**
 * Gère la génération des données électriques
 */
async function handleGeneration(event) {
    event.preventDefault();
    
    if (!appState.currentBuildings.length) {
        showNotification('Aucun bâtiment chargé pour la génération', 'error');
        return;
    }
    
    const formData = new FormData(event.target);
    const params = {
        zone_name: appState.currentZone,
        buildings_osm: appState.currentBuildings,
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        freq: formData.get('frequency')
    };
    
    const generateBtn = document.getElementById('generate-btn');
    
    try {
        showLoading(true);
        updateStatus('Génération des données électriques...');
        if (generateBtn) generateBtn.disabled = true;
        
        // Affichage du progress avec estimation
        const estimatedTime = getEstimatedGenerationTime(params);
        showProgress('Génération des données électriques en cours...', 0);
        
        // Simulation du progrès basée sur l'estimation
        const progressInterval = startProgressSimulation(estimatedTime);
        
        const data = await apiRequestWithRetry('/generate', {
            method: 'POST',
            body: JSON.stringify(params)
        });
        
        clearInterval(progressInterval);
        hideProgress();
        
        if (data.success) {
            // Stockage des données générées
            appState.generatedData = {
                buildings: data.buildings_data,
                timeseries: data.timeseries_data,
                metadata: data.statistics
            };
            
            // Mise à jour de l'interface des résultats
            updateResultsInterface(data);
            
            // Affichage des sections résultats et export
            showSection('results-section');
            showSection('export-section');
            
            showNotification('Génération terminée avec succès!', 'success');
            updateStatus(`${formatNumber(data.statistics.total_observations)} observations générées`);
            
        } else {
            throw new Error(data.error || 'Erreur de génération');
        }
        
    } catch (error) {
        hideProgress();
        console.error('Erreur génération:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
        updateStatus('Erreur de génération');
    } finally {
        showLoading(false);
        if (generateBtn) generateBtn.disabled = false;
    }
}

/**
 * Estime le temps de génération
 */
function getEstimatedGenerationTime(params) {
    const buildings = params.buildings_osm.length;
    const startDate = new Date(params.start_date);
    const endDate = new Date(params.end_date);
    const days = (endDate - startDate) / (1000 * 60 * 60 * 24);
    
    // Estimation approximative : 1000 bâtiments * 30 jours = 30 secondes
    const estimatedSeconds = (buildings * days) / 1000;
    return Math.max(10, Math.min(estimatedSeconds, 300)); // Entre 10s et 5min
}

/**
 * Démarre la simulation de progression
 */
function startProgressSimulation(estimatedSeconds) {
    let progress = 0;
    const increment = 100 / (estimatedSeconds * 2); // 2 updates per second
    
    return setInterval(() => {
        progress += increment * (0.5 + Math.random() * 0.5); // Variation réaliste
        progress = Math.min(progress, 95); // Ne jamais atteindre 100%
        
        const stages = [
            'Préparation des bâtiments...',
            'Génération des patterns climatiques...',
            'Calcul des consommations...',
            'Optimisation des données...',
            'Finalisation...'
        ];
        
        const stage = stages[Math.floor(progress / 20)] || stages[stages.length - 1];
        updateProgress(progress, stage);
    }, 500);
}

// ==============================================================================
// GESTION DES RÉSULTATS
// ==============================================================================

/**
 * Met à jour l'interface des résultats
 */
function updateResultsInterface(data) {
    const stats = data.statistics;
    
    // Mise à jour des cartes de statistiques
    const elements = {
        'result-buildings': formatNumber(stats.total_buildings),
        'result-observations': formatNumber(stats.total_observations),
        'result-quality': stats.quality_metrics?.overall_score ? 
                         `${stats.quality_metrics.overall_score}%` : 'N/A',
        'result-duration': stats.generation_summary ? 'Complété' : 'N/A'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            
            // Animation de révélation
            element.style.opacity = '0';
            element.style.transform = 'scale(0.8)';
            setTimeout(() => {
                element.style.transition = 'all 0.5s ease';
                element.style.opacity = '1';
                element.style.transform = 'scale(1)';
            }, 100);
        }
    });
    
    // Mise à jour des aperçus de données
    updateDataPreviews(data);
    
    // Animation d'apparition des sections
    animateResultsAppearance();
}

/**
 * Met à jour les aperçus de données dans les onglets
 */
function updateDataPreviews(data) {
    // Aperçu des bâtiments
    updateBuildingsPreview(data.buildings_data);
    
    // Aperçu des séries temporelles
    updateTimeseriesPreview(data.timeseries_data);
    
    // Résumé statistique
    updateSummaryContent(data.statistics);
}

/**
 * Met à jour l'aperçu des bâtiments
 */
function updateBuildingsPreview(buildings) {
    const previewDiv = document.getElementById('buildings-preview');
    if (!previewDiv || !buildings.length) return;
    
    const sample = buildings.slice(0