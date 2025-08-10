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
        # Recherche dans les zones principales
        zone_data = MALAYSIA_ZONES.MAJOR_ZONES.get(zone_name.lower())
        
        if zone_data:
            # Ajouter le type de zone
            zone_data['type'] = 'major_city'
            return zone_data
        
        # TODO: Ajouter recherche dans d'autres sources (API, fichiers JSON)
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
        
        # Utiliser la relation OSM si disponible (plus précis)
        if zone_data.get('osm_relation_id'):
            query = f"""
            [out:json][timeout:{timeout}][maxsize:1073741824];
            (
                rel({zone_data['osm_relation_id']});
                map_to_area -> .searchArea;
            );
            (
                way["building"](area.searchArea);
                relation["building"](area.searchArea);
            );
            out geom;
            """
        else:
            # Fallback avec bounding box
            bbox = zone_data.get('bbox', [])
            if len(bbox) != 4:
                raise ValueError(f"Bounding box invalide pour {zone_data['name']}")
            
            west, south, east, north = bbox
            query = f"""
            [out:json][timeout:{timeout}][maxsize:1073741824];
            (
                way["building"]({south},{west},{north},{east});
                relation["building"]({south},{west},{north},{east});
            );
            out geom;
            """
        
        return query.strip()
    
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
            zone_name: Nom de la zone
            
        Returns:
            List[Building]: Liste des bâtiments créés
        """
        buildings = []
        processed_count = 0
        skipped_count = 0
        
        for element in elements:
            try:
                # Vérifier que l'élément a une géométrie valide
                if not element.get('geometry') or len(element.get('geometry', [])) < 3:
                    skipped_count += 1
                    continue
                
                # Créer le bâtiment depuis les données OSM
                building = Building.from_osm_data(element, zone_name)
                buildings.append(building)
                processed_count += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur traitement élément OSM {element.get('id', 'unknown')}: {str(e)}")
                skipped_count += 1
                continue
        
        logger.info(f"📊 Traitement OSM: {processed_count} créés, {skipped_count} ignorés")
        return buildings
    
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
    lon_km_per_degree = 111.0 * abs(sum([south, north]) / 2) / 90  # correction latitude
    
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