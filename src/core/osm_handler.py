"""
Gestionnaire OpenStreetMap (OSM) pour récupération de données de bâtiments
=========================================================================

Ce module gère toutes les interactions avec l'API Overpass d'OpenStreetMap
pour récupérer les données complètes des bâtiments d'une localité.
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

from config import OSM_CONFIG, MALAYSIA_ZONES
from src.models.building import Building


# Configuration du logger
logger = logging.getLogger(__name__)


@dataclass
class OSMQueryResult:
    """Résultat d'une requête OSM avec métadonnées"""
    
    buildings: List[Building]
    total_elements: int
    query_time_seconds: float
    zone_name: str
    bbox_used: List[float]
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = None


class OSMHandler:
    """
    Gestionnaire principal pour les requêtes OpenStreetMap
    
    Cette classe gère la récupération complète des bâtiments d'une localité
    avec gestion d'erreurs robuste et optimisation des requêtes.
    """
    
    def __init__(self):
        """Initialise le gestionnaire OSM"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Malaysia-Building-Generator/1.0 (contact: admin@example.com)'
        })
        
        # Statistiques de session
        self.total_requests = 0
        self.total_buildings_fetched = 0
        self.failed_requests = 0
        
        logger.info("✅ Gestionnaire OSM initialisé")
    
    def get_complete_locality_buildings(self, zone_name: str) -> OSMQueryResult:
        """
        Récupère TOUS les bâtiments d'une localité entière avec métadonnées
        
        Args:
            zone_name: Nom de la zone/ville (ex: 'kuala_lumpur')
            
        Returns:
            OSMQueryResult: Résultat complet avec bâtiments et métadonnées
        """
        start_time = time.time()
        
        try:
            # Récupération des données de zone
            zone_data = self._get_zone_configuration(zone_name)
            if not zone_data:
                return OSMQueryResult(
                    buildings=[],
                    total_elements=0,
                    query_time_seconds=time.time() - start_time,
                    zone_name=zone_name,
                    bbox_used=[],
                    success=False,
                    error_message=f"Zone '{zone_name}' non trouvée dans la configuration"
                )
            
            logger.info(f"🔄 Démarrage requête OSM pour {zone_data['name']}")
            logger.info(f"📊 Estimation: {zone_data.get('estimated_buildings', 'inconnue')} bâtiments")
            
            # Construction de la requête Overpass optimisée
            query = self._build_complete_overpass_query(zone_data)
            
            # Exécution de la requête avec retry
            osm_data = self._execute_overpass_query(query)
            
            # Traitement des données OSM en objets Building
            buildings = self._process_osm_elements(osm_data.get('elements', []), zone_name)
            
            # Validation et nettoyage
            valid_buildings, warnings = self._validate_and_clean_buildings(buildings)
            
            query_time = time.time() - start_time
            
            # Mise à jour des statistiques
            self.total_requests += 1
            self.total_buildings_fetched += len(valid_buildings)
            
            logger.info(f"✅ Requête OSM terminée en {query_time:.2f}s")
            logger.info(f"🏗️ {len(valid_buildings)} bâtiments valides récupérés")
            
            return OSMQueryResult(
                buildings=valid_buildings,
                total_elements=len(osm_data.get('elements', [])),
                query_time_seconds=query_time,
                zone_name=zone_name,
                bbox_used=zone_data.get('bbox', []),
                success=True,
                warnings=warnings
            )
            
        except Exception as e:
            self.failed_requests += 1
            query_time = time.time() - start_time
            
            logger.error(f"❌ Erreur requête OSM pour {zone_name}: {str(e)}")
            
            return OSMQueryResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=query_time,
                zone_name=zone_name,
                bbox_used=[],
                success=False,
                error_message=str(e)
            )
    
    def _get_zone_configuration(self, zone_name: str) -> Optional[Dict]:
            """
            Récupère la configuration d'une zone depuis les données Malaysia
            
            Args:
                zone_name: Nom de la zone
                
            Returns:
                Dict: Configuration de la zone ou None si non trouvée
            """
            # Chercher dans toutes les catégories de la nouvelle structure
            categories_to_search = []
            
            if hasattr(MALAYSIA_ZONES, 'COUNTRY'):
                categories_to_search.append(MALAYSIA_ZONES.COUNTRY)
            if hasattr(MALAYSIA_ZONES, 'STATES'):
                categories_to_search.append(MALAYSIA_ZONES.STATES)
            if hasattr(MALAYSIA_ZONES, 'FEDERAL_TERRITORIES'):
                categories_to_search.append(MALAYSIA_ZONES.FEDERAL_TERRITORIES)
            if hasattr(MALAYSIA_ZONES, 'MAJOR_CITIES'):
                categories_to_search.append(MALAYSIA_ZONES.MAJOR_CITIES)
            if hasattr(MALAYSIA_ZONES, 'SPECIAL_REGIONS'):
                categories_to_search.append(MALAYSIA_ZONES.SPECIAL_REGIONS)
            
            # Fallback vers l'ancienne structure si la nouvelle n'existe pas
            if not categories_to_search and hasattr(MALAYSIA_ZONES, 'MAJOR_ZONES'):
                categories_to_search.append(MALAYSIA_ZONES.MAJOR_ZONES)
            
            # Rechercher dans chaque catégorie
            for category in categories_to_search:
                zone_data = category.get(zone_name.lower())
                if zone_data:
                    # Ajouter le type de zone et faire une copie pour éviter de modifier l'original
                    zone_data = zone_data.copy()
                    if 'type' not in zone_data:
                        zone_data['type'] = 'unknown'
                    return zone_data
            
            logger.warning(f"⚠️ Zone {zone_name} non trouvée dans la configuration")
            return None
    
    def _build_complete_overpass_query(self, zone_data: Dict) -> str:
        """
        Construit une requête Overpass pour récupérer TOUS les bâtiments d'une zone
        
        Args:
            zone_data: Données de configuration de la zone
            
        Returns:
            str: Requête Overpass formatée
        """
        timeout = OSM_CONFIG.TIMEOUT_SECONDS
        
        # PRIORITÉ 1: Utiliser bbox directement (plus fiable que les relations)
        bbox = zone_data.get('bbox', [])
        if len(bbox) == 4:
            west, south, east, north = bbox
            query = f"""
            [out:json][timeout:{timeout}][maxsize:1073741824];
            (
                way["building"]({south},{west},{north},{east});
                relation["building"]({south},{west},{north},{east});
            );
            out geom;
            """
            logger.info(f"🗺️ Utilisation bbox: [{west}, {south}, {east}, {north}]")
            return query.strip()
        
        # PRIORITÉ 2: Fallback avec relation OSM si bbox non disponible
        elif zone_data.get('osm_relation_id'):
            relation_id = zone_data['osm_relation_id']
            query = f"""
            [out:json][timeout:{timeout}][maxsize:1073741824];
            (
                relation({relation_id});
                map_to_area -> .searchArea;
            );
            (
                way["building"](area.searchArea);
                relation["building"](area.searchArea);
            );
            out geom;
            """
            logger.info(f"🔗 Utilisation relation OSM: {relation_id}")
            return query.strip()
        
        else:
            raise ValueError(f"Aucune méthode de géolocalisation disponible pour {zone_data['name']}")
    
    def _execute_overpass_query(self, query: str) -> Dict:
        """
        Exécute une requête Overpass avec gestion d'erreurs et retry
        
        Args:
            query: Requête Overpass à exécuter
            
        Returns:
            Dict: Données JSON retournées par l'API
        """
        last_error = None
        
        # Essayer l'API principale puis la backup
        apis = [OSM_CONFIG.OVERPASS_API_URL, OSM_CONFIG.OVERPASS_BACKUP_URL]
        
        for api_url in apis:
            for attempt in range(OSM_CONFIG.MAX_RETRIES):
                try:
                    logger.info(f"🔄 Tentative {attempt + 1}/{OSM_CONFIG.MAX_RETRIES} sur {api_url}")
                    
                    response = self.session.post(
                        api_url,
                        data=query,
                        headers={'Content-Type': 'text/plain; charset=utf-8'},
                        timeout=OSM_CONFIG.TIMEOUT_SECONDS
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        # Rate limiting - attendre plus longtemps
                        wait_time = OSM_CONFIG.RETRY_DELAY * (attempt + 1) * 2
                        logger.warning(f"⏳ Rate limited, attente {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise requests.RequestException(f"HTTP {response.status_code}: {response.text[:200]}")
                
                except requests.RequestException as e:
                    last_error = e
                    if attempt < OSM_CONFIG.MAX_RETRIES - 1:
                        wait_time = OSM_CONFIG.RETRY_DELAY * (attempt + 1)
                        logger.warning(f"⏳ Erreur, nouvelle tentative dans {wait_time}s: {str(e)[:100]}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ Échec définitif sur {api_url}: {str(e)}")
        
        # Si toutes les tentatives ont échoué
        raise Exception(f"Échec de toutes les tentatives OSM: {str(last_error)}")
    
    def _process_osm_elements(self, elements: List[Dict], zone_name: str) -> List[Building]:
        """
        Traite les éléments OSM bruts en objets Building
        
        Args:
            elements: Liste des éléments OSM
            zone_name: Nom de la zone pour logging
            
        Returns:
            List[Building]: Liste des bâtiments traités
        """
        buildings = []
        processed_count = 0
        skipped_count = 0
        
        logger.info(f"📊 Traitement OSM: {len(elements)} éléments à traiter")
        
        for element in elements:
            try:
                processed_count += 1
                
                # Vérification du type d'élément
                if element.get('type') not in ['way', 'relation']:
                    skipped_count += 1
                    continue
                
                # Extraction des tags
                tags = element.get('tags', {})
                
                # Vérification tag building
                building_tag = tags.get('building')
                if not building_tag or building_tag in ['no', 'false']:
                    skipped_count += 1
                    continue
                
                # Extraction des coordonnées
                geometry = element.get('geometry', [])
                if not geometry:
                    skipped_count += 1
                    continue
                
                # Calcul du centre géométrique
                lats = [coord['lat'] for coord in geometry if 'lat' in coord]
                lons = [coord['lon'] for coord in geometry if 'lon' in coord]
                
                if not lats or not lons:
                    skipped_count += 1
                    continue
                
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                
                # Calcul de la surface approximative (polygone)
                surface_area = self._calculate_polygon_area(geometry)
                
                # Détermination du type de bâtiment
                building_type = self._normalize_building_type(building_tag, tags)
                
                # Estimation de la consommation de base
                base_consumption = self._estimate_base_consumption(building_type, surface_area)
                
                # Création de l'objet Building
                building = Building(
                    osm_id=str(element.get('id', '')),
                    latitude=center_lat,
                    longitude=center_lon,
                    building_type=building_type,
                    surface_area_m2=surface_area,
                    base_consumption_kwh=base_consumption,
                    osm_tags=tags,
                    zone_name=zone_name
                )
                
                buildings.append(building)
                
            except Exception as e:
                skipped_count += 1
                logger.warning(f"⚠️ Erreur traitement élément OSM: {str(e)}")
                continue
        
        created_count = len(buildings)
        logger.info(f"📊 Traitement OSM: {created_count} créés, {skipped_count} ignorés")
        
        return buildings
    
    def _calculate_polygon_area(self, geometry: List[Dict]) -> float:
        """
        Calcule l'aire d'un polygone à partir de ses coordonnées
        
        Args:
            geometry: Liste des coordonnées du polygone
            
        Returns:
            float: Aire en m²
        """
        if len(geometry) < 3:
            return 50.0  # Surface par défaut pour point/ligne
        
        try:
            # Conversion coords géographiques en mètres (approximation)
            coords_m = []
            for coord in geometry:
                lat = coord.get('lat', 0)
                lon = coord.get('lon', 0)
                
                # Conversion approximative à la latitude de Malaysia
                x = lon * 111320 * math.cos(math.radians(lat))  # longitude en mètres
                y = lat * 110540  # latitude en mètres
                coords_m.append((x, y))
            
            # Formule de Shoelace pour l'aire du polygone
            n = len(coords_m)
            area = 0.0
            
            for i in range(n):
                j = (i + 1) % n
                area += coords_m[i][0] * coords_m[j][1]
                area -= coords_m[j][0] * coords_m[i][1]
            
            area = abs(area) / 2.0
            
            # Validation de l'aire
            if area < 10:  # Minimum 10m²
                return 50.0
            elif area > 100000:  # Maximum 100,000m²
                return 1000.0
            
            return area
            
        except Exception:
            return 75.0  # Surface par défaut en cas d'erreur
    
    def _normalize_building_type(self, building_tag: str, tags: Dict) -> str:
        """
        Normalise le type de bâtiment OSM vers nos catégories
        
        Args:
            building_tag: Valeur du tag 'building'
            tags: Tous les tags OSM de l'élément
            
        Returns:
            str: Type de bâtiment normalisé
        """
        # Mapping OSM vers nos types
        type_mapping = {
            'residential': 'residential',
            'house': 'residential', 
            'apartment': 'residential',
            'apartments': 'residential',
            'detached': 'residential',
            'terrace': 'residential',
            'commercial': 'commercial',
            'retail': 'commercial',
            'shop': 'commercial',
            'office': 'office',
            'industrial': 'industrial',
            'factory': 'industrial',
            'warehouse': 'industrial',
            'hospital': 'hospital',
            'school': 'school',
            'university': 'school',
            'hotel': 'hotel',
            'yes': 'residential',  # Par défaut
            'true': 'residential'
        }
        
        # Vérification du tag building principal
        normalized = type_mapping.get(building_tag.lower(), 'residential')
        
        # Affinement avec d'autres tags
        if tags.get('amenity') == 'hospital':
            return 'hospital'
        elif tags.get('amenity') in ['school', 'university']:
            return 'school'
        elif tags.get('tourism') == 'hotel':
            return 'hotel'
        elif tags.get('shop'):
            return 'commercial'
        elif tags.get('office'):
            return 'office'
        elif tags.get('landuse') == 'industrial':
            return 'industrial'
        
        return normalized
    
    def _estimate_base_consumption(self, building_type: str, surface_area: float) -> float:
        """
        Estime la consommation électrique de base d'un bâtiment
        
        Args:
            building_type: Type de bâtiment
            surface_area: Surface en m²
            
        Returns:
            float: Consommation de base en kWh/jour
        """
        # Coefficients de consommation par type (kWh/m²/jour)
        consumption_coefficients = {
            'residential': 0.15,
            'commercial': 0.25,
            'office': 0.30,
            'industrial': 0.45,
            'hospital': 0.40,
            'school': 0.20,
            'hotel': 0.35
        }
        
        coefficient = consumption_coefficients.get(building_type, 0.15)
        base_consumption = surface_area * coefficient
        
        # Limites de validation
        min_consumption = 5.0   # 5 kWh/jour minimum
        max_consumption = 10000.0  # 10 MWh/jour maximum
        
        return max(min_consumption, min(base_consumption, max_consumption))
    
    def _validate_and_clean_buildings(self, buildings: List[Building]) -> Tuple[List[Building], List[str]]:
        """
        Valide et nettoie la liste des bâtiments
        
        Args:
            buildings: Liste des bâtiments à valider
            
        Returns:
            Tuple[List[Building], List[str]]: Bâtiments valides et warnings
        """
        valid_buildings = []
        warnings = []
        
        # Statistiques de validation
        original_count = len(buildings)
        duplicate_count = 0
        invalid_coord_count = 0
        invalid_data_count = 0
        
        # Set pour détecter les doublons (basé sur les coordonnées)
        seen_coords = set()
        
        for building in buildings:
            try:
                # Vérification des coordonnées uniques (arrondir à 6 décimales)
                coord_key = (round(building.latitude, 6), round(building.longitude, 6))
                if coord_key in seen_coords:
                    duplicate_count += 1
                    continue
                seen_coords.add(coord_key)
                
                # Validation des coordonnées Malaysia
                if not (0.5 <= building.latitude <= 7.5 and 99.0 <= building.longitude <= 120.0):
                    invalid_coord_count += 1
                    continue
                
                # Validation des données du bâtiment
                if building.surface_area_m2 <= 0 or building.base_consumption_kwh < 0:
                    invalid_data_count += 1
                    continue
                
                valid_buildings.append(building)
                
            except Exception as e:
                invalid_data_count += 1
                logger.warning(f"⚠️ Validation échouée pour bâtiment: {str(e)}")
        
        # Génération des warnings
        if duplicate_count > 0:
            warnings.append(f"{duplicate_count} bâtiments doublons supprimés")
        if invalid_coord_count > 0:
            warnings.append(f"{invalid_coord_count} bâtiments avec coordonnées invalides")
        if invalid_data_count > 0:
            warnings.append(f"{invalid_data_count} bâtiments avec données invalides")
        
        final_count = len(valid_buildings)
        removed_count = original_count - final_count
        
        if removed_count > 0:
            logger.info(f"🧹 Nettoyage: {removed_count}/{original_count} bâtiments supprimés")
        
        return valid_buildings, warnings
    
    def get_zone_estimation(self, zone_name: str) -> Dict:
        """
        Fournit une estimation de la complexité de requête pour une zone
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Dict: Estimation avec temps, taille, complexité
        """
        zone_data = self._get_zone_configuration(zone_name)
        
        if not zone_data:
            return {
                'zone_found': False,
                'error': f"Zone {zone_name} non trouvée"
            }
        
        estimated_buildings = zone_data.get('estimated_buildings', 1000)
        area_km2 = zone_data.get('area_km2', 100)
        
        # Calculs d'estimation
        estimated_time_minutes = max(1, estimated_buildings / 10000)  # ~10k bâtiments/minute
        estimated_size_mb = max(0.1, estimated_buildings * 0.002)     # ~2KB par bâtiment
        
        # Niveau de complexité
        if estimated_buildings < 5000:
            complexity = 'faible'
            recommendation = 'Requête rapide recommandée'
        elif estimated_buildings < 50000:
            complexity = 'moyenne'
            recommendation = 'Requête standard, quelques minutes'
        elif estimated_buildings < 200000:
            complexity = 'élevée'
            recommendation = 'Requête longue, soyez patient'
        else:
            complexity = 'très_élevée'
            recommendation = 'Requête très longue, considérer la subdivision'
        
        return {
            'zone_found': True,
            'zone_name': zone_data['name'],
            'zone_type': zone_data.get('type', 'unknown'),
            'estimated_buildings': estimated_buildings,
            'area_km2': area_km2,
            'estimated_time_minutes': round(estimated_time_minutes, 1),
            'estimated_size_mb': round(estimated_size_mb, 1),
            'complexity_level': complexity,
            'recommendation': recommendation,
            'bbox': zone_data.get('bbox', []),
            'has_osm_relation': bool(zone_data.get('osm_relation_id'))
        }
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques d'usage du gestionnaire OSM
        
        Returns:
            Dict: Statistiques de session
        """
        success_rate = 0
        if self.total_requests > 0:
            success_rate = ((self.total_requests - self.failed_requests) / self.total_requests) * 100
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.total_requests - self.failed_requests,
            'failed_requests': self.failed_requests,
            'success_rate_percent': round(success_rate, 1),
            'total_buildings_fetched': self.total_buildings_fetched,
            'average_buildings_per_request': round(
                self.total_buildings_fetched / max(1, self.total_requests - self.failed_requests), 1
            )
        }


# ==============================================================================
# FONCTIONS UTILITAIRES OSM
# ==============================================================================

def test_osm_connection() -> bool:
    """
    Teste la connexion aux APIs Overpass
    
    Returns:
        bool: True si la connexion fonctionne
    """
    test_query = "[out:json][timeout:10]; area[name='Malaysia']; out;"
    
    try:
        response = requests.post(
            OSM_CONFIG.OVERPASS_API_URL,
            data=test_query,
            timeout=15
        )
        return response.status_code == 200
    except:
        return False


def calculate_bbox_area(bbox: List[float]) -> float:
    """
    Calcule l'aire approximative d'une bounding box en km²
    
    Args:
        bbox: [west, south, east, north] en degrés
        
    Returns:
        float: Aire en km²
    """
    if len(bbox) != 4:
        return 0
    
    west, south, east, north = bbox
    
    # Conversion approximative degrés -> km (à la latitude de Malaysia)
    lat_km_per_degree = 111.0
    lon_km_per_degree = 111.0 * math.cos(math.radians((south + north) / 2))
    
    width_km = (east - west) * lon_km_per_degree
    height_km = (north - south) * lat_km_per_degree
    
    return abs(width_km * height_km)


def get_zone_list() -> List[Dict]:
    """
    Retourne la liste de toutes les zones disponibles
    
    Returns:
        List[Dict]: Liste des zones avec métadonnées
    """
    zones = []
    
    for zone_id, zone_data in MALAYSIA_ZONES.MAJOR_ZONES.items():
        zones.append({
            'zone_id': zone_id,
            'name': zone_data['name'],
            'state': zone_data['state'],
            'population': zone_data['population'],
            'estimated_buildings': zone_data.get('estimated_buildings', 'unknown'),
            'area_km2': zone_data.get('area_km2', 0),
            'has_osm_relation': bool(zone_data.get('osm_relation_id'))
        })
    
    return sorted(zones, key=lambda x: x['population'], reverse=True)


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du gestionnaire OSM
    handler = OSMHandler()
    
    # Test de connexion
    if test_osm_connection():
        print("✅ Connexion OSM OK")
    else:
        print("❌ Connexion OSM échouée")
    
    # Estimation pour Kuala Lumpur
    estimation = handler.get_zone_estimation('kuala_lumpur')
    print(f"📊 Estimation KL: {estimation}")
    
    # Liste des zones
    zones = get_zone_list()
    print(f"🏙️ {len(zones)} zones disponibles")
    for zone in zones[:3]:
        print(f"  - {zone['name']}: {zone['estimated_buildings']} bâtiments estimés")