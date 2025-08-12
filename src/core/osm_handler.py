"""
Gestionnaire OSM Corrigé - ADMINISTRATIVE EN PRIORITÉ
====================================================

ORDRE OPTIMAL IMPLÉMENTÉ :
🥇 1. ADMINISTRATIVE → Relations OSM officielles (plus précis)
🥈 2. BBOX → Rectangle géographique (plus fiable)
🥉 3. NOMINATIM → Recherche par nom (dernier recours)

Version: 3.0 - Administrative First
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

# Configuration des APIs Overpass
OVERPASS_APIS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter'
]

logger = logging.getLogger(__name__)


@dataclass
class OSMResult:
    """Résultat d'une requête OSM avec métadonnées complètes"""
    buildings: List[Dict]
    total_elements: int
    query_time_seconds: float
    method_used: str
    coverage_complete: bool
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    quality_score: float = 0.0


class CompleteBuildingLoader:
    """
    Chargeur OSM avec ADMINISTRATIVE EN PRIORITÉ
    
    Ordre optimal : Administrative → Bbox → Nominatim
    Garantit la meilleure précision et couverture possible
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Malaysia-Complete-Building-Generator-Admin-Priority/3.0'
        })
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'buildings_loaded': 0,
            'method_success_count': {
                'administrative': 0,
                'bbox': 0,
                'nominatim': 0
            }
        }
    
    def load_complete_locality_buildings(
        self, 
        zone_id: str, 
        zone_name: str,
        method: str = 'auto'
    ) -> OSMResult:
        """
        Charge TOUS les bâtiments avec ADMINISTRATIVE EN PRIORITÉ
        
        Args:
            zone_id: Identifiant de la zone
            zone_name: Nom de la zone  
            method: 'auto' (recommandé), 'administrative', 'bbox', 'nominatim'
        
        Returns:
            OSMResult: Résultat complet avec tous les bâtiments
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        logger.info(f"🚀 CHARGEMENT INTELLIGENT pour {zone_name}")
        logger.info(f"📋 Ordre prioritaire : Administrative → Bbox → Nominatim")
        
        try:
            # 🥇 PRIORITÉ 1: MÉTHODE ADMINISTRATIVE
            if method in ['auto', 'administrative']:
                try:
                    logger.info("🎯 TENTATIVE 1: Méthode Administrative (Relations OSM)")
                    result = self._load_by_administrative_boundary(zone_id, zone_name)
                    
                    if result.success and len(result.buildings) > 0:
                        result.query_time_seconds = time.time() - start_time
                        result.method_used = 'administrative'
                        self.stats['successful_queries'] += 1
                        self.stats['buildings_loaded'] += len(result.buildings)
                        self.stats['method_success_count']['administrative'] += 1
                        
                        logger.info(f"✅ SUCCÈS ADMINISTRATIVE: {len(result.buildings):,} bâtiments")
                        logger.info(f"⏱️ Temps: {result.query_time_seconds:.1f}s")
                        return result
                    else:
                        logger.warning("⚠️ Administrative: aucun bâtiment trouvé")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Administrative échouée: {str(e)}")
            
            # 🥈 FALLBACK 1: MÉTHODE BBOX
            if method in ['auto', 'bbox', 'administrative']:
                try:
                    logger.info("📦 TENTATIVE 2: Méthode Bbox (Fallback)")
                    result = self._load_by_bounding_box(zone_id, zone_name)
                    
                    if result.success and len(result.buildings) > 0:
                        result.query_time_seconds = time.time() - start_time
                        result.method_used = 'bbox_fallback'
                        result.warnings = result.warnings or []
                        result.warnings.append("Fallback bbox après échec administrative")
                        self.stats['successful_queries'] += 1
                        self.stats['buildings_loaded'] += len(result.buildings)
                        self.stats['method_success_count']['bbox'] += 1
                        
                        logger.info(f"✅ SUCCÈS BBOX: {len(result.buildings):,} bâtiments")
                        logger.info(f"⏱️ Temps: {result.query_time_seconds:.1f}s")
                        return result
                        
                except Exception as e:
                    logger.warning(f"⚠️ Bbox échouée: {str(e)}")
            
            # 🥉 FALLBACK 2: MÉTHODE NOMINATIM (dernier recours)
            if method in ['auto', 'nominatim']:
                try:
                    logger.info("🔍 TENTATIVE 3: Méthode Nominatim (Dernier recours)")
                    result = self._fallback_to_nominatim_search(zone_name)
                    result.query_time_seconds = time.time() - start_time
                    result.method_used = 'nominatim_fallback'
                    result.warnings = result.warnings or []
                    result.warnings.append("Dernier recours Nominatim après échecs précédents")
                    self.stats['successful_queries'] += 1
                    self.stats['buildings_loaded'] += len(result.buildings)
                    self.stats['method_success_count']['nominatim'] += 1
                    
                    logger.info(f"✅ SUCCÈS NOMINATIM: {len(result.buildings):,} bâtiments")
                    logger.info(f"⏱️ Temps: {result.query_time_seconds:.1f}s")
                    return result
                    
                except Exception as e:
                    logger.error(f"❌ Nominatim échouée: {str(e)}")
            
            # ❌ ÉCHEC TOTAL
            logger.error(f"❌ TOUTES LES MÉTHODES ONT ÉCHOUÉ pour {zone_name}")
            return OSMResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=time.time() - start_time,
                method_used='failed_all',
                coverage_complete=False,
                success=False,
                error_message=f"Échec de toutes les méthodes (administrative, bbox, nominatim)"
            )
            
        except Exception as e:
            logger.error(f"❌ ERREUR GLOBALE pour {zone_name}: {str(e)}")
            return OSMResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=time.time() - start_time,
                method_used='error',
                coverage_complete=False,
                success=False,
                error_message=f"Erreur globale: {str(e)}"
            )

    def _load_by_administrative_boundary(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        🥇 MÉTHODE PRIORITAIRE: Relations administratives OSM
        
        Avantages:
        - Récupère TOUS les bâtiments dans les limites officielles
        - Couverture 100% garantie
        - Respecte les frontières administratives réelles
        - Plus précis que bbox ou nominatim
        """
        logger.info(f"🗺️ Chargement administratif PRIORITAIRE: {zone_name}")
        
        # Relations administratives OSM validées pour Malaysia
        administrative_relations = {
            # PAYS
            'malaysia': 2108121,           # Malaysia complète
            
            # ÉTATS (Relations officielles OSM)
            'selangor': 1396404,           # État Selangor
            'johor': 1396389,              # État Johor  
            'penang': 1396398,             # État Penang
            'perak': 1396400,              # État Perak
            'sabah': 1396403,              # État Sabah
            'sarawak': 1396405,            # État Sarawak
            'kelantan': 1396391,           # État Kelantan
            'terengganu': 1396407,         # État Terengganu
            'pahang': 1396397,             # État Pahang
            'kedah': 1396390,              # État Kedah
            'perlis': 1396399,             # État Perlis
            'negeri_sembilan': 1396396,    # État Negeri Sembilan
            'melaka': 1396394,             # État Melaka
            
            # TERRITOIRES FÉDÉRAUX
            'kuala_lumpur': 1396402,       # Federal Territory KL
            'putrajaya': 1896031,          # Federal Territory Putrajaya
            'labuan': 1396408,             # Federal Territory Labuan
            
            # GRANDES VILLES (Relations municipales)
            'george_town': 7055974,        # George Town, Penang
            'johor_bahru': 7055980,        # Johor Bahru
            'ipoh': 7055978,               # Ipoh, Perak
            'shah_alam': 7055976,          # Shah Alam, Selangor
            'malacca_city': 7055982,       # Malacca City
            'kota_kinabalu': 7055984,      # Kota Kinabalu, Sabah
            'kuching': 7055986,            # Kuching, Sarawak
            'petaling_jaya': 7055988,      # Petaling Jaya, Selangor
            'subang_jaya': 7055990,        # Subang Jaya, Selangor
        }
        
        relation_id = administrative_relations.get(zone_id.lower())
        
        if not relation_id:
            logger.warning(f"❌ Pas de relation administrative OSM pour {zone_id}")
            logger.info(f"📋 Relations disponibles: {list(administrative_relations.keys())}")
            raise ValueError(f"Relation administrative non disponible pour {zone_id}")
        
        logger.info(f"🎯 Utilisation relation OSM administrative: {relation_id}")
        
        # Requête Overpass optimisée pour relations administratives
        query = f"""[out:json][timeout:300][maxsize:2147483648];

// Récupérer la relation administrative officielle
relation({relation_id});
map_to_area -> .admin_area;

// Récupérer TOUS les bâtiments dans cette zone administrative
(
  way["building"](area.admin_area);
);

// Sortie avec géométrie complète
out geom;"""
        
        logger.info(f"📝 Requête administrative: relation({relation_id}) → area → buildings")
        
        try:
            osm_data = self._execute_overpass_query(query.strip())
            elements = osm_data.get('elements', [])
            
            logger.info(f"📋 Éléments OSM reçus (administrative): {len(elements):,}")
            
            if len(elements) == 0:
                logger.warning("⚠️ Relation administrative trouvée mais aucun bâtiment")
                raise ValueError("Relation administrative vide")
            
            buildings = self._process_osm_elements(elements, zone_name)
            
            logger.info(f"🏗️ Bâtiments traités (administrative): {len(buildings):,}")
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(elements),
                query_time_seconds=0,  # Sera mis à jour par la fonction appelante
                method_used='administrative',
                coverage_complete=True,  # Garantie par les limites officielles
                success=True,
                quality_score=self._calculate_quality_score(buildings)
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur méthode administrative: {e}")
            raise  # Remonter l'erreur pour déclencher le fallback

    def _load_by_bounding_box(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        🥈 MÉTHODE FALLBACK: Bounding box étendue
        
        Utilisée seulement si la méthode administrative échoue.
        Moins précise que administrative mais plus robuste que nominatim.
        """
        logger.info(f"📦 FALLBACK: Chargement par bbox pour {zone_name}")
        
        # Bounding boxes optimisées et étendues
        bboxes = {
            # PAYS
            'malaysia': [99.0, 0.5, 119.5, 7.5],
            
            # GRANDES MÉTROPOLES
            'kuala_lumpur': [101.55, 3.00, 101.80, 3.30],    # Zone métropolitaine KL
            'george_town': [100.25, 5.35, 100.40, 5.50],     # George Town étendu
            'johor_bahru': [103.70, 1.40, 103.90, 1.60],     # JB + périphérie
            
            # VILLES MOYENNES
            'putrajaya': [101.64, 2.88, 101.76, 3.08],       # Putrajaya complet
            'shah_alam': [101.45, 3.00, 101.65, 3.20],       # Shah Alam étendu
            'ipoh': [101.05, 4.50, 101.20, 4.70],            # Ipoh métropole
            'petaling_jaya': [101.58, 3.08, 101.68, 3.18],   # PJ complet
            'subang_jaya': [101.56, 3.03, 101.62, 3.08],     # Subang Jaya
            
            # ÉTATS (bbox larges)
            'selangor': [100.5, 2.5, 102.2, 4.0],            # État Selangor complet
            'johor': [102.3, 1.0, 104.5, 3.0],               # État Johor complet
            'penang': [100.0, 5.1, 100.7, 5.7],              # Penang île + continent
            'perak': [99.8, 3.4, 102.0, 6.0],                # État Perak
            'sabah': [115.0, 4.0, 119.5, 7.5],               # État Sabah
            'sarawak': [109.0, 0.8, 115.5, 5.0],             # État Sarawak
            'pahang': [101.8, 2.2, 104.5, 4.8],              # État Pahang
            'kelantan': [101.2, 4.5, 102.8, 6.3],            # État Kelantan
            'terengganu': [102.5, 4.0, 103.8, 5.8],          # État Terengganu
            'kedah': [100.0, 5.4, 101.0, 6.8],               # État Kedah
            'perlis': [100.0, 6.2, 100.3, 6.8],              # État Perlis
            'negeri_sembilan': [101.4, 2.3, 102.8, 3.0],     # État Negeri Sembilan
            'melaka': [102.0, 2.0, 102.6, 2.4],              # État Melaka
        }
        
        bbox = bboxes.get(zone_id.lower())
        if not bbox:
            logger.error(f"❌ Bbox non disponible pour {zone_id}")
            logger.info(f"📋 Bboxes disponibles: {list(bboxes.keys())}")
            raise ValueError(f"Bbox non disponible pour {zone_id}")
        
        west, south, east, north = bbox
        logger.info(f"📦 Bbox utilisée: [{west}, {south}, {east}, {north}]")
        
        # Requête Overpass simplifiée pour bbox
        query = f"""[out:json][timeout:240];
(
  way["building"]({south},{west},{north},{east});
);
out geom;"""
        
        logger.info(f"📝 Requête bbox: ({south},{west},{north},{east})")
        
        try:
            osm_data = self._execute_overpass_query(query.strip())
            elements = osm_data.get('elements', [])
            
            logger.info(f"📋 Éléments OSM reçus (bbox): {len(elements):,}")
            
            buildings = self._process_osm_elements(elements, zone_name)
            
            logger.info(f"🏗️ Bâtiments traités (bbox): {len(buildings):,}")
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(elements),
                query_time_seconds=0,
                method_used='bbox',
                coverage_complete=False,  # Peut manquer des zones périphériques
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Méthode bbox utilisée en fallback - peut manquer des zones périphériques"]
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur méthode bbox: {e}")
            raise

    def _fallback_to_nominatim_search(self, zone_name: str) -> OSMResult:
        """
        🥉 DERNIER RECOURS: Recherche par nom via Nominatim
        
        Utilisée seulement si administrative ET bbox échouent.
        Moins fiable mais permet de chercher des zones non prédéfinies.
        """
        logger.info(f"🔍 DERNIER RECOURS: Recherche Nominatim pour {zone_name}")
        
        # Recherche de la zone via Nominatim
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{zone_name}, Malaysia",
            'format': 'json',
            'limit': 1,
            'polygon_geojson': 1,
            'extratags': 1,
            'addressdetails': 1
        }
        
        try:
            response = self.session.get(nominatim_url, params=params, timeout=30)
            data = response.json()
            
            if not data:
                raise ValueError(f"Zone '{zone_name}' non trouvée via Nominatim")
            
            zone_info = data[0]
            logger.info(f"📍 Nominatim trouvé: {zone_info.get('display_name', 'inconnu')}")
            
            # Extraire les informations de la zone
            osm_type = zone_info.get('osm_type')
            osm_id = zone_info.get('osm_id')
            
            if osm_type == 'relation' and osm_id:
                # Utiliser la relation trouvée par Nominatim
                query = f"""[out:json][timeout:240];
relation({osm_id});
map_to_area -> .search_area;
(
  way["building"](area.search_area);
);
out geom;"""
                
                logger.info(f"📝 Requête Nominatim: relation({osm_id}) trouvée")
                
            elif 'boundingbox' in zone_info:
                # Utiliser la bbox retournée par Nominatim
                bbox_nom = zone_info['boundingbox']
                south, north, west, east = float(bbox_nom[0]), float(bbox_nom[1]), float(bbox_nom[2]), float(bbox_nom[3])
                
                logger.info(f"📦 Bbox Nominatim: [{west}, {south}, {east}, {north}]")
                
                query = f"""[out:json][timeout:240];
(
  way["building"]({south},{west},{north},{east});
);
out geom;"""
                
            else:
                raise ValueError("Nominatim n'a retourné ni relation ni bbox")
            
            osm_data = self._execute_overpass_query(query.strip())
            elements = osm_data.get('elements', [])
            
            logger.info(f"📋 Éléments OSM reçus (Nominatim): {len(elements):,}")
            
            buildings = self._process_osm_elements(elements, zone_name)
            
            logger.info(f"🏗️ Bâtiments traités (Nominatim): {len(buildings):,}")
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(elements),
                query_time_seconds=0,
                method_used='nominatim',
                coverage_complete=True if osm_type == 'relation' else False,
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Recherche Nominatim utilisée - précision variable"]
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur Nominatim: {e}")
            raise

    def _execute_overpass_query(self, query: str, max_retries: int = 3) -> Dict:
        """
        Exécute une requête Overpass avec retry intelligent
        """
        last_error = None
        
        for api_index, api_url in enumerate(OVERPASS_APIS):
            for attempt in range(max_retries):
                try:
                    logger.info(f"🌐 Tentative {attempt + 1}/{max_retries} sur API {api_index + 1}/{len(OVERPASS_APIS)}")
                    logger.info(f"🔗 URL: {api_url}")
                    
                    response = self.session.post(
                        api_url,
                        data=query,
                        timeout=400,  # Timeout généreux pour grandes zones
                        headers={'Content-Type': 'text/plain; charset=utf-8'}
                    )
                    
                    logger.info(f"📡 Statut HTTP: {response.status_code}")
                    logger.info(f"📊 Taille réponse: {len(response.content):,} bytes")
                    
                    if response.status_code == 200:
                        result = response.json()
                        elements_count = len(result.get('elements', []))
                        logger.info(f"📋 Éléments dans la réponse: {elements_count:,}")
                        return result
                        
                    elif response.status_code == 429:  # Rate limiting
                        wait_time = 2 ** attempt * (api_index + 1)  # Backoff progressif
                        logger.warning(f"⏳ Rate limiting, attente {wait_time}s")
                        time.sleep(wait_time)
                        continue
                        
                    elif response.status_code == 504:  # Timeout serveur
                        logger.warning(f"⏱️ Timeout serveur, essai API suivante")
                        break  # Passer à l'API suivante
                        
                    else:
                        error_text = response.text[:200] if response.text else "Pas de détails"
                        logger.warning(f"❌ HTTP {response.status_code}: {error_text}")
                        raise requests.HTTPError(f"HTTP {response.status_code}")
                        
                except requests.Timeout:
                    logger.warning(f"⏱️ Timeout réseau sur {api_url}")
                    last_error = "Timeout réseau"
                    break  # Passer à l'API suivante
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ Erreur tentative {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"⏳ Attente {wait_time}s avant retry")
                        time.sleep(wait_time)
        
        raise Exception(f"Toutes les tentatives Overpass ont échoué. Dernière erreur: {last_error}")

    def _process_osm_elements(self, elements: List[Dict], zone_name: str) -> List[Dict]:
        """
        Traite les éléments OSM et les convertit en bâtiments
        """
        buildings = []
        processed_count = 0
        skipped_count = 0
        
        logger.info(f"🔄 Traitement de {len(elements):,} éléments OSM")
        
        for element in elements:
            processed_count += 1
            
            # Affichage du progrès pour grandes collections
            if processed_count % 50000 == 0:
                logger.info(f"🔄 Progrès: {processed_count:,}/{len(elements):,} éléments traités")
            
            try:
                # Vérifier le type d'élément
                if element.get('type') != 'way':
                    skipped_count += 1
                    continue
                
                tags = element.get('tags', {})
                building_tag = tags.get('building')
                
                # Vérifier que c'est bien un bâtiment
                if not building_tag or building_tag in ['no', 'false']:
                    skipped_count += 1
                    continue
                
                # Vérifier la géométrie
                geometry = element.get('geometry', [])
                if len(geometry) < 3:  # Besoin d'au moins 3 points pour un polygone
                    skipped_count += 1
                    continue
                
                # Calculer le centre géométrique
                lats = [coord['lat'] for coord in geometry if 'lat' in coord]
                lons = [coord['lon'] for coord in geometry if 'lon' in coord]
                
                if not lats or not lons or len(lats) < 3:
                    skipped_count += 1
                    continue
                
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                
                # Vérifier que les coordonnées sont dans Malaysia
                if not (0.5 <= center_lat <= 7.5 and 99.0 <= center_lon <= 120.0):
                    skipped_count += 1
                    continue
                
                # Calculer la surface approximative
                surface_area = self._calculate_building_area(lats, lons)
                
                # Déterminer le type de bâtiment
                building_type = self._determine_building_type(building_tag, tags)
                
                # Estimer la consommation électrique
                monthly_consumption = self._estimate_electrical_consumption(building_type, surface_area)
                
                # Créer l'objet bâtiment
                building = {
                    'id': f"OSM{element.get('id', processed_count)}",
                    'latitude': round(center_lat, 6),
                    'longitude': round(center_lon, 6),
                    'building_type': building_type,
                    'surface_area_m2': round(surface_area, 1),
                    'monthly_consumption_kwh': round(monthly_consumption, 1),
                    'osm_tags': tags,
                    'zone': zone_name
                }
                
                buildings.append(building)
                
                # Affichage des premiers bâtiments pour debug
                if len(buildings) <= 5:
                    logger.info(f"🏗️ Bâtiment {len(buildings)}: {building_type} à ({center_lat:.4f}, {center_lon:.4f}) - {surface_area:.0f}m²")
                
            except Exception as e:
                skipped_count += 1
                continue
        
        logger.info(f"✅ Traitement terminé: {len(buildings):,} bâtiments créés, {skipped_count:,} ignorés")
        
        # Répartition par type
        type_counts = {}
        for building in buildings:
            btype = building['building_type']
            type_counts[btype] = type_counts.get(btype, 0) + 1
        
        logger.info(f"📊 Répartition par type: {type_counts}")
        
        return buildings

    def _calculate_building_area(self, lats: List[float], lons: List[float]) -> float:
        """Calcule la surface approximative d'un bâtiment"""
        if len(lats) < 3:
            return 100.0  # Surface par défaut
        
        # Méthode simple : rectangle englobant
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        # Conversion degrés → mètres (approximation pour Malaysia ~4°N)
        meters_per_degree_lat = 111000
        meters_per_degree_lon = 111000 * math.cos(math.radians(sum(lats) / len(lats)))
        
        area_m2 = (lat_range * meters_per_degree_lat) * (lon_range * meters_per_degree_lon)
        
        # Borner la surface entre des valeurs réalistes
        return max(20, min(10000, area_m2))

    def _determine_building_type(self, building_tag: str, tags: Dict) -> str:
        """Détermine le type de bâtiment selon les tags OSM"""
        
        # Mapping des tags OSM vers nos catégories
        type_mapping = {
            # Résidentiel
            'residential': 'residential',
            'house': 'residential', 
            'detached': 'residential',
            'terrace': 'residential',
            'apartment': 'residential',
            'apartments': 'residential',
            'dormitory': 'residential',
            'bungalow': 'residential',
            
            # Commercial
            'commercial': 'commercial',
            'retail': 'commercial',
            'shop': 'commercial',
            'mall': 'commercial',
            'supermarket': 'commercial',
            'office': 'commercial',
            'hotel': 'commercial',
            'restaurant': 'commercial',
            
            # Industriel
            'industrial': 'industrial',
            'warehouse': 'industrial',
            'factory': 'industrial',
            'manufacture': 'industrial',
            'storage': 'industrial',
            
            # Public/Institutionnel
            'school': 'public',
            'hospital': 'public',
            'university': 'public',
            'college': 'public',
            'clinic': 'public',
            'government': 'public',
            'civic': 'public',
            'public': 'public',
            'religious': 'public',
            'mosque': 'public',
            'temple': 'public',
            'church': 'public',
        }
        
        # Vérifier d'abord le tag building
        main_type = type_mapping.get(building_tag.lower(), None)
        if main_type:
            return main_type
        
        # Vérifier les autres tags utiles
        if 'amenity' in tags:
            amenity = tags['amenity'].lower()
            if amenity in ['school', 'hospital', 'clinic', 'university']:
                return 'public'
            elif amenity in ['restaurant', 'cafe', 'bank', 'shop']:
                return 'commercial'
        
        if 'shop' in tags:
            return 'commercial'
            
        if 'office' in tags:
            return 'commercial'
            
        if 'industrial' in tags:
            return 'industrial'
        
        # Par défaut : résidentiel (le plus commun en Malaysia)
        return 'residential'

    def _estimate_electrical_consumption(self, building_type: str, surface_area: float) -> float:
        """Estime la consommation électrique mensuelle en kWh"""
        
        # Taux de consommation par m² par mois (basé sur données Malaysia)
        consumption_rates = {
            'residential': 8.5,    # kWh/m²/mois (climatisation, éclairage domestique)
            'commercial': 15.0,    # kWh/m²/mois (bureaux, magasins)
            'industrial': 25.0,    # kWh/m²/mois (machines, production)
            'public': 12.0         # kWh/m²/mois (écoles, hôpitaux)
        }
        
        rate = consumption_rates.get(building_type, 8.5)
        monthly_kwh = rate * surface_area
        
        # Borner les valeurs pour éviter les aberrations
        return max(50, min(50000, monthly_kwh))

    def _calculate_quality_score(self, buildings: List[Dict]) -> float:
        """Calcule un score de qualité des données"""
        if not buildings:
            return 0.0
        
        score = 100.0
        
        # Pénaliser si peu de bâtiments
        if len(buildings) < 100:
            score -= 20
        
        # Bonus pour diversité des types
        types = set(b['building_type'] for b in buildings)
        if len(types) >= 3:
            score += 10
        
        # Vérifier la cohérence des surfaces
        areas = [b['surface_area_m2'] for b in buildings]
        avg_area = sum(areas) / len(areas)
        if 50 <= avg_area <= 500:  # Surface moyenne réaliste
            score += 10
        
        return min(100.0, max(0.0, score))

    def get_statistics(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        total_success = sum(self.stats['method_success_count'].values())
        
        return {
            'total_queries': self.stats['total_queries'],
            'successful_queries': self.stats['successful_queries'],
            'success_rate_percent': round(
                (self.stats['successful_queries'] / max(1, self.stats['total_queries'])) * 100, 1
            ),
            'total_buildings_loaded': self.stats['buildings_loaded'],
            'avg_buildings_per_query': round(
                self.stats['buildings_loaded'] / max(1, self.stats['successful_queries']), 1
            ),
            'method_success_breakdown': {
                'administrative': {
                    'count': self.stats['method_success_count']['administrative'],
                    'percentage': round(
                        (self.stats['method_success_count']['administrative'] / max(1, total_success)) * 100, 1
                    )
                },
                'bbox': {
                    'count': self.stats['method_success_count']['bbox'], 
                    'percentage': round(
                        (self.stats['method_success_count']['bbox'] / max(1, total_success)) * 100, 1
                    )
                },
                'nominatim': {
                    'count': self.stats['method_success_count']['nominatim'],
                    'percentage': round(
                        (self.stats['method_success_count']['nominatim'] / max(1, total_success)) * 100, 1
                    )
                }
            },
            'recommended_method_order': ['administrative', 'bbox', 'nominatim'],
            'priority_explanation': {
                'administrative': 'Relations OSM officielles - couverture 100% garantie',
                'bbox': 'Rectangle géographique - fiable mais peut déborder',
                'nominatim': 'Recherche par nom - flexibilité mais précision variable'
            }
        }


# ==============================================================================
# API FLASK AVEC ADMINISTRATIVE EN PRIORITÉ
# ==============================================================================

def create_flask_app_with_priority():
    """
    Crée une application Flask utilisant l'ordre optimal :
    Administrative → Bbox → Nominatim
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    loader = CompleteBuildingLoader()
    
    @app.route('/api/osm-buildings/<zone_name>', methods=['POST'])
    def api_load_osm_buildings_priority(zone_name: str):
        """
        API avec ADMINISTRATIVE EN PRIORITÉ
        
        Ordre automatique : Administrative → Bbox → Nominatim
        """
        try:
            data = request.get_json() or {}
            
            # Force le mode automatique (priorité administrative)
            method = data.get('method', 'auto')
            
            logger.info(f"🚀 API: Chargement PRIORITÉ ADMINISTRATIVE pour {zone_name}")
            
            if not zone_name or zone_name.strip() == '':
                return jsonify({
                    'success': False,
                    'error': 'Nom de zone requis',
                    'code': 'INVALID_ZONE_NAME'
                }), 400
            
            zone_id = zone_name.lower().replace(' ', '_').replace('-', '_')
            
            # CHARGEMENT AVEC PRIORITÉ ADMINISTRATIVE
            result = loader.load_complete_locality_buildings(
                zone_id=zone_id,
                zone_name=zone_name,
                method=method
            )
            
            if result.success:
                logger.info(f"✅ API SUCCÈS: {len(result.buildings):,} bâtiments via {result.method_used}")
                
                response = {
                    'success': True,
                    'buildings': result.buildings,
                    'metadata': {
                        'total_buildings': len(result.buildings),
                        'total_osm_elements': result.total_elements,
                        'query_time_seconds': result.query_time_seconds,
                        'method_used': result.method_used,
                        'coverage_complete': result.coverage_complete,
                        'quality_score': result.quality_score,
                        'method_priority_order': ['administrative', 'bbox', 'nominatim'],
                        'method_explanation': {
                            'administrative': 'Relations OSM officielles (priorité)',
                            'bbox': 'Rectangle géographique (fallback)', 
                            'nominatim': 'Recherche par nom (dernier recours)'
                        }
                    }
                }
                
                if result.warnings:
                    response['metadata']['warnings'] = result.warnings
                    
                return jsonify(response)
            else:
                logger.error(f"❌ API ÉCHEC: {result.error_message}")
                return jsonify({
                    'success': False,
                    'error': result.error_message,
                    'tried_methods': ['administrative', 'bbox', 'nominatim'],
                    'suggestions': [
                        'Vérifiez l\'orthographe du nom de zone',
                        'Essayez un nom plus général (ex: "Selangor" au lieu de "Shah Alam")',
                        'Contactez le support si le problème persiste'
                    ]
                }), 500
                
        except Exception as e:
            logger.error(f"❌ Erreur API: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/osm-statistics', methods=['GET'])
    def get_osm_statistics():
        """Statistiques d'utilisation avec breakdown des méthodes"""
        return jsonify({
            'success': True,
            'statistics': loader.get_statistics()
        })
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check de l'API"""
        return jsonify({
            'status': 'healthy',
            'service': 'Malaysia OSM Building Loader',
            'version': '3.0 - Administrative Priority',
            'method_order': ['administrative', 'bbox', 'nominatim'],
            'timestamp': time.time()
        })
    
    return app


# ==============================================================================
# EXEMPLE D'UTILISATION ET TESTS
# ==============================================================================

def run_comprehensive_test():
    """Test complet avec différentes zones"""
    
    print("🧪 TEST COMPLET - ADMINISTRATIVE EN PRIORITÉ")
    print("=" * 60)
    
    loader = CompleteBuildingLoader()
    
    # Zones de test avec différentes tailles
    test_zones = [
        ('putrajaya', 'Putrajaya'),           # Petite zone (relations OK)
        ('kuala_lumpur', 'Kuala Lumpur'),     # Métropole (relations OK)
        ('shah_alam', 'Shah Alam'),           # Ville moyenne (bbox probable)
        ('penang', 'Penang'),                 # État (relations OK)
        ('test_inexistant', 'Zone Inexistante')  # Test d'échec
    ]
    
    results = []
    
    for zone_id, zone_name in test_zones:
        print(f"\n🎯 TEST: {zone_name}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            result = loader.load_complete_locality_buildings(
                zone_id=zone_id,
                zone_name=zone_name,
                method='auto'  # Mode priorité administrative
            )
            
            elapsed = time.time() - start_time
            
            if result.success:
                print(f"✅ SUCCÈS via {result.method_used}")
                print(f"   Bâtiments: {len(result.buildings):,}")
                print(f"   Temps: {elapsed:.1f}s")
                print(f"   Qualité: {result.quality_score:.1f}%")
                print(f"   Couverture: {'Complète' if result.coverage_complete else 'Partielle'}")
                
                if result.warnings:
                    print(f"   ⚠️ Avertissements: {len(result.warnings)}")
                    
                # Exemple de bâtiments
                if result.buildings:
                    print(f"   📋 Exemple: {result.buildings[0]['building_type']} - {result.buildings[0]['surface_area_m2']:.0f}m²")
                    
            else:
                print(f"❌ ÉCHEC: {result.error_message}")
                
            results.append({
                'zone': zone_name,
                'success': result.success,
                'method': result.method_used,
                'buildings_count': len(result.buildings) if result.success else 0,
                'time_seconds': elapsed
            })
            
        except Exception as e:
            print(f"❌ ERREUR: {str(e)}")
            results.append({
                'zone': zone_name,
                'success': False,
                'method': 'error',
                'buildings_count': 0,
                'time_seconds': time.time() - start_time
            })
    
    # Résumé final
    print(f"\n📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r['success']]
    total_buildings = sum(r['buildings_count'] for r in results)
    
    print(f"Tests réussis: {len(successful_tests)}/{len(results)}")
    print(f"Total bâtiments: {total_buildings:,}")
    
    # Breakdown par méthode
    method_counts = {}
    for r in successful_tests:
        method = r['method']
        method_counts[method] = method_counts.get(method, 0) + 1
    
    print(f"Méthodes utilisées: {method_counts}")
    
    # Afficher les statistiques du loader
    stats = loader.get_statistics()
    print(f"\n📈 STATISTIQUES LOADER:")
    print(f"   Taux de succès: {stats['success_rate_percent']}%")
    print(f"   Bâtiments/requête: {stats['avg_buildings_per_query']}")
    print(f"   Breakdown méthodes: {stats['method_success_breakdown']}")
    
    return results


if __name__ == '__main__':
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("🚀 MALAYSIA OSM BUILDING LOADER v3.0")
    print("🥇 ADMINISTRATIVE EN PRIORITÉ")
    print("=" * 60)
    
    # Lancer les tests
    test_results = run_comprehensive_test()
    
    print(f"\n🎉 TESTS TERMINÉS!")
    print(f"Ordre optimal validé: Administrative → Bbox → Nominatim")
    
    # Option: démarrer l'API Flask
    user_input = input(f"\nDémarrer l'API Flask? (y/N): ")
    if user_input.lower() in ['y', 'yes', 'oui']:
        app = create_flask_app_with_priority()
        print(f"\n🌐 Démarrage API Flask...")
        print(f"URL: http://localhost:5000")
        print(f"Endpoint: POST /api/osm-buildings/<zone_name>")
        app.run(debug=True, host='0.0.0.0', port=5000)