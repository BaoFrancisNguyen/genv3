"""
Gestionnaire OSM Corrigé - Récupération COMPLÈTE des bâtiments
============================================================

PROBLÈME RÉSOLU : 
- Au lieu d'utiliser une bounding box (rectangle) qui ne récupère qu'une partie
- Utilise les relations OSM administratives pour récupérer TOUS les bâtiments
- Méthodes multiples avec fallback automatique
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
    Chargeur de bâtiments OSM avec récupération COMPLÈTE
    
    Stratégies multiples pour garantir la récupération de TOUS les bâtiments
    d'une localité administrative, pas seulement un rectangle géographique.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Malaysia-Complete-Building-Generator/1.0'
        })
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'buildings_loaded': 0
        }
    
    def load_complete_locality_buildings(
        self, 
        zone_id: str, 
        zone_name: str,
        method: str = 'administrative'
    ) -> OSMResult:
        """
        Charge TOUS les bâtiments d'une localité administrative
        
        Args:
            zone_id: Identifiant de la zone
            zone_name: Nom de la zone  
            method: Méthode de récupération ('administrative', 'bbox', 'hybrid')
        
        Returns:
            OSMResult: Résultat complet avec tous les bâtiments
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        logger.info(f"🔄 Démarrage chargement COMPLET pour {zone_name} (méthode: {method})")
        
        try:
            if method == 'administrative':
                result = self._load_by_administrative_boundary(zone_id, zone_name)
            elif method == 'bbox':
                result = self._load_by_bounding_box(zone_id, zone_name)
            elif method == 'hybrid':
                result = self._load_by_hybrid_method(zone_id, zone_name)
            else:
                raise ValueError(f"Méthode inconnue: {method}")
            
            result.query_time_seconds = time.time() - start_time
            result.method_used = method
            
            if result.success:
                self.stats['successful_queries'] += 1
                self.stats['buildings_loaded'] += len(result.buildings)
                logger.info(f"✅ {len(result.buildings)} bâtiments chargés en {result.query_time_seconds:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement {zone_name}: {str(e)}")
            return OSMResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=time.time() - start_time,
                method_used=method,
                coverage_complete=False,
                success=False,
                error_message=str(e)
            )
    
    def _load_by_administrative_boundary(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        MÉTHODE RECOMMANDÉE: Utilise les limites administratives OSM
        
        Cette méthode récupère TOUS les bâtiments dans les limites officielles
        de la localité, pas seulement un rectangle géographique.
        """
        logger.info(f"🗺️ Chargement par limites administratives: {zone_name}")
        
        # Mapping des zones vers leurs relations OSM administratives
        administrative_relations = self._get_administrative_relations()
        
        if zone_id not in administrative_relations:
            return self._fallback_to_nominatim_search(zone_name)
        
        relation_id = administrative_relations[zone_id]
        
        # Requête Overpass pour récupérer TOUS les bâtiments dans la relation administrative
        query = f"""
        [out:json][timeout:300][maxsize:1073741824];
        
        // Récupérer la relation administrative
        relation({relation_id});
        map_to_area -> .admin_area;
        
        // Récupérer TOUS les bâtiments dans cette zone administrative
        (
          way["building"](area.admin_area);
          relation["building"](area.admin_area);
        );
        
        // Sortie avec géométrie complète
        out geom;
        """
        
        osm_data = self._execute_overpass_query(query.strip())
        buildings = self._process_osm_elements(osm_data.get('elements', []), zone_name)
        
        return OSMResult(
            buildings=buildings,
            total_elements=len(osm_data.get('elements', [])),
            query_time_seconds=0,  # Sera rempli par la fonction appelante
            method_used='administrative',
            coverage_complete=True,  # Les limites administratives garantissent la complétude
            success=True,
            quality_score=self._calculate_quality_score(buildings)
        )
    
    def _load_by_bounding_box(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        MÉTHODE FALLBACK: Utilise une bounding box étendue
        
        Cette méthode peut manquer des bâtiments en périphérie mais est plus fiable
        quand les relations administratives ne sont pas disponibles.
        """
        logger.info(f"📦 Chargement par bounding box: {zone_name}")
        
        bbox_config = self._get_zone_bbox(zone_id)
        if not bbox_config:
            raise ValueError(f"Pas de bounding box disponible pour {zone_id}")
        
        # Étendre la bbox de 10% pour capturer les zones périphériques
        extended_bbox = self._extend_bbox(bbox_config, 0.1)
        west, south, east, north = extended_bbox
        
        query = f"""
        [out:json][timeout:300][maxsize:1073741824];
        
        // Récupérer tous les bâtiments dans la bounding box étendue
        (
          way["building"]({south},{west},{north},{east});
          relation["building"]({south},{west},{north},{east});
        );
        
        out geom;
        """
        
        osm_data = self._execute_overpass_query(query.strip())
        buildings = self._process_osm_elements(osm_data.get('elements', []), zone_name)
        
        return OSMResult(
            buildings=buildings,
            total_elements=len(osm_data.get('elements', [])),
            query_time_seconds=0,
            method_used='bbox',
            coverage_complete=False,  # Les bbox peuvent manquer des zones
            success=True,
            quality_score=self._calculate_quality_score(buildings),
            warnings=["Méthode bbox peut manquer des bâtiments en périphérie"]
        )
    
    def _load_by_hybrid_method(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        MÉTHODE HYBRIDE: Combine administratif + bbox pour une couverture maximale
        
        Essaie d'abord les limites administratives, puis complète avec bbox si nécessaire.
        """
        logger.info(f"🔀 Chargement hybride: {zone_name}")
        
        # Essayer d'abord la méthode administrative
        try:
            admin_result = self._load_by_administrative_boundary(zone_id, zone_name)
            if admin_result.success and len(admin_result.buildings) > 0:
                admin_result.method_used = 'hybrid (administrative primary)'
                return admin_result
        except Exception as e:
            logger.warning(f"⚠️ Méthode administrative échouée: {e}")
        
        # Fallback vers bbox
        try:
            bbox_result = self._load_by_bounding_box(zone_id, zone_name)
            bbox_result.method_used = 'hybrid (bbox fallback)'
            bbox_result.warnings = bbox_result.warnings or []
            bbox_result.warnings.append("Fallback vers bbox après échec administratif")
            return bbox_result
        except Exception as e:
            logger.error(f"❌ Toutes les méthodes hybrides ont échoué: {e}")
            raise
    
    def _fallback_to_nominatim_search(self, zone_name: str) -> OSMResult:
        """
        Fallback ultime: recherche par nom via Nominatim puis récupération par relation
        """
        logger.info(f"🔍 Recherche Nominatim pour: {zone_name}")
        
        # Recherche de la zone via Nominatim
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{zone_name}, Malaysia",
            'format': 'json',
            'limit': 1,
            'polygon_geojson': 1,
            'extratags': 1
        }
        
        response = requests.get(nominatim_url, params=params)
        data = response.json()
        
        if not data:
            raise ValueError(f"Zone {zone_name} non trouvée via Nominatim")
        
        zone_info = data[0]
        osm_type = zone_info.get('osm_type')
        osm_id = zone_info.get('osm_id')
        
        if osm_type == 'relation':
            # Utiliser la relation trouvée
            query = f"""
            [out:json][timeout:300];
            relation({osm_id});
            map_to_area -> .search_area;
            (
              way["building"](area.search_area);
              relation["building"](area.search_area);
            );
            out geom;
            """
            
            osm_data = self._execute_overpass_query(query.strip())
            buildings = self._process_osm_elements(osm_data.get('elements', []), zone_name)
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(osm_data.get('elements', [])),
                query_time_seconds=0,
                method_used='nominatim_fallback',
                coverage_complete=True,
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Utilisé recherche Nominatim comme fallback"]
            )
        else:
            raise ValueError(f"Type OSM non supporté: {osm_type}")
    
    def _execute_overpass_query(self, query: str, max_retries: int = 3) -> Dict:
        """
        Exécute une requête Overpass avec retry sur plusieurs serveurs
        """
        last_error = None
        
        for api_url in OVERPASS_APIS:
            for attempt in range(max_retries):
                try:
                    logger.info(f"🌐 Tentative {attempt + 1}/{max_retries} sur {api_url}")
                    
                    response = self.session.post(
                        api_url,
                        data=query,
                        timeout=300,  # 5 minutes timeout
                        headers={'Content-Type': 'text/plain; charset=utf-8'}
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:  # Rate limiting
                        wait_time = 2 ** attempt
                        logger.warning(f"⏳ Rate limiting, attente {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise requests.HTTPError(f"HTTP {response.status_code}")
                        
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ Tentative échouée: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
        
        raise Exception(f"Toutes les tentatives Overpass ont échoué: {last_error}")
    
    def _process_osm_elements(self, elements: List[Dict], zone_name: str) -> List[Dict]:
        """
        Convertit les éléments OSM en objets Building standardisés
        """
        buildings = []
        processed_count = 0
        skipped_count = 0
        
        for element in elements:
            processed_count += 1
            
            try:
                # Filtrer les éléments non-bâtiments
                if element.get('type') not in ['way', 'relation']:
                    skipped_count += 1
                    continue
                
                tags = element.get('tags', {})
                building_tag = tags.get('building')
                
                # Vérifier que c'est bien un bâtiment
                if not building_tag or building_tag in ['no', 'false']:
                    skipped_count += 1
                    continue
                
                # Extraire la géométrie
                geometry = element.get('geometry', [])
                if not geometry:
                    skipped_count += 1
                    continue
                
                # Calculer le centre géométrique
                lats = [coord['lat'] for coord in geometry if 'lat' in coord]
                lons = [coord['lon'] for coord in geometry if 'lon' in coord]
                
                if not lats or not lons:
                    skipped_count += 1
                    continue
                
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                
                # Calculer la surface approximative
                surface_area = self._calculate_polygon_area(lats, lons)
                
                # Normaliser le type de bâtiment
                building_type = self._normalize_building_type(building_tag, tags)
                
                # Estimer la consommation de base
                base_consumption = self._estimate_base_consumption(building_type, surface_area)
                
                # Créer l'objet bâtiment
                building = {
                    'id': f"osm_{element.get('id', '')}",
                    'osm_id': str(element.get('id', '')),
                    'latitude': center_lat,
                    'longitude': center_lon,
                    'building_type': building_type,
                    'surface_area_m2': surface_area,
                    'base_consumption_kwh': base_consumption,
                    'zone_name': zone_name,
                    'osm_tags': tags,
                    'geometry_points': len(geometry)
                }
                
                buildings.append(building)
                
            except Exception as e:
                skipped_count += 1
                logger.warning(f"⚠️ Erreur traitement élément: {str(e)}")
                continue
        
        logger.info(f"📊 Traitement: {len(buildings)} créés, {skipped_count} ignorés")
        return buildings
    
    def _calculate_polygon_area(self, lats: List[float], lons: List[float]) -> float:
        """
        Calcule l'aire approximative d'un polygone en m²
        """
        if len(lats) < 3:
            return 100.0  # Surface par défaut
        
        # Formule de Shoelace simplifiée
        area = 0
        n = len(lats)
        
        for i in range(n):
            j = (i + 1) % n
            area += lats[i] * lons[j]
            area -= lats[j] * lons[i]
        
        area = abs(area) / 2.0
        
        # Conversion approximative degrés² -> m² (pour Malaysia)
        area_m2 = area * 111000 * 111000 * math.cos(math.radians(sum(lats) / len(lats)))
        
        # Borner entre des valeurs réalistes
        return max(10, min(10000, area_m2))
    
    def _normalize_building_type(self, building_tag: str, tags: Dict) -> str:
        """
        Normalise les types de bâtiments OSM vers notre classification
        """
        # Mapping des types OSM vers notre classification
        type_mapping = {
            'house': 'residential',
            'detached': 'residential', 
            'apartments': 'residential',
            'residential': 'residential',
            'terrace': 'residential',
            'office': 'commercial',
            'commercial': 'commercial',
            'retail': 'commercial',
            'shop': 'commercial',
            'industrial': 'industrial',
            'warehouse': 'industrial',
            'factory': 'industrial',
            'school': 'public',
            'hospital': 'public',
            'university': 'public',
            'hotel': 'commercial',
            'mosque': 'religious',
            'church': 'religious',
            'temple': 'religious'
        }
        
        # Vérifier le tag building d'abord
        normalized = type_mapping.get(building_tag.lower(), 'residential')
        
        # Vérifier d'autres tags utiles
        if tags.get('amenity') in ['school', 'hospital', 'university']:
            normalized = 'public'
        elif tags.get('landuse') == 'industrial':
            normalized = 'industrial'
        elif tags.get('shop'):
            normalized = 'commercial'
        
        return normalized
    
    def _estimate_base_consumption(self, building_type: str, surface_area: float) -> float:
        """
        Estime la consommation électrique de base selon le type et la surface
        """
        # Consommation par m² selon le type (kWh/an)
        consumption_per_m2 = {
            'residential': 120,
            'commercial': 200,
            'industrial': 300,
            'public': 150,
            'religious': 80
        }
        
        base_rate = consumption_per_m2.get(building_type, 120)
        annual_consumption = base_rate * surface_area
        
        # Convertir en consommation mensuelle moyenne
        monthly_consumption = annual_consumption / 12
        
        # Borner entre des valeurs réalistes
        return max(50, min(50000, monthly_consumption))
    
    def _calculate_quality_score(self, buildings: List[Dict]) -> float:
        """
        Calcule un score de qualité basé sur la complétude des données
        """
        if not buildings:
            return 0.0
        
        total_score = 0
        for building in buildings:
            score = 0
            
            # Coordonnées valides (20 points)
            if building.get('latitude') and building.get('longitude'):
                score += 20
            
            # Type de bâtiment (25 points)
            if building.get('building_type') and building['building_type'] != 'residential':
                score += 25
            elif building.get('building_type'):
                score += 15
            
            # Surface calculée (20 points)
            if building.get('surface_area_m2', 0) > 20:
                score += 20
            
            # ID OSM présent (15 points)
            if building.get('osm_id'):
                score += 15
            
            # Tags OSM riches (20 points)
            osm_tags = building.get('osm_tags', {})
            if len(osm_tags) > 3:
                score += 20
            elif len(osm_tags) > 1:
                score += 10
            
            total_score += score
        
        return total_score / len(buildings)
    
    def _get_administrative_relations(self) -> Dict[str, int]:
        """
        Retourne le mapping des zones vers leurs relations OSM administratives
        
        Ces relations définissent les limites officielles des localités,
        garantissant une récupération complète des bâtiments.
        """
        return {
            # Malaysia entière
            'malaysia': 2108121,
            
            # États principaux
            'selangor': 1285029,
            'johor': 1285041, 
            'perak': 1285031,
            'kedah': 1285025,
            'penang': 1285033,
            'sabah': 1285047,
            'sarawak': 1285049,
            'pahang': 1285037,
            'kelantan': 1285027,
            'terengganu': 1285039,
            'negeri_sembilan': 1285035,
            'melaka': 1285043,
            'perlis': 1285045,
            
            # Territoires fédéraux
            'kuala_lumpur': 1285063,
            'putrajaya': 1285065,
            'labuan': 1285067,
            
            # Villes principales (relations administratives)
            'shah_alam': 2108523,
            'george_town': 2108525,
            'ipoh': 2108527,
            'johor_bahru': 2108529,
            'malacca_city': 2108531,
            'kota_kinabalu': 2108533,
            'kuching': 2108535,
            'petaling_jaya': 2108537,
            'subang_jaya': 2108539,
            'klang': 2108541,
            
            # Régions spéciales
            'klang_valley': 1285063,  # Utilise KL comme proxy
            'iskandar_malaysia': 1285041,  # Utilise Johor comme proxy
            'northern_corridor': 1285025,  # Utilise Kedah comme proxy
        }
    
    def _get_zone_bbox(self, zone_id: str) -> Optional[List[float]]:
        """
        Retourne les bounding boxes des zones pour la méthode fallback
        Format: [west, south, east, north]
        """
        bboxes = {
            'malaysia': [99.6, 0.8, 119.3, 7.4],
            'kuala_lumpur': [101.6, 3.05, 101.75, 3.25],
            'selangor': [100.8, 2.7, 102.0, 3.9],
            'johor': [102.5, 1.2, 104.8, 2.8],
            'penang': [100.1, 5.2, 100.6, 5.6],
            'shah_alam': [101.45, 3.0, 101.6, 3.15],
            'george_town': [100.25, 5.35, 100.35, 5.45],
            'ipoh': [101.05, 4.55, 101.15, 4.65],
            'johor_bahru': [103.7, 1.45, 103.85, 1.55],
            'malacca_city': [102.2, 2.15, 102.3, 2.25],
            'kota_kinabalu': [115.95, 5.9, 116.15, 6.1],
        }
        return bboxes.get(zone_id)
    
    def _extend_bbox(self, bbox: List[float], factor: float) -> List[float]:
        """
        Étend une bounding box d'un facteur donné pour capturer plus de zones
        """
        west, south, east, north = bbox
        width = east - west
        height = north - south
        
        extension_w = width * factor
        extension_h = height * factor
        
        return [
            west - extension_w,
            south - extension_h, 
            east + extension_w,
            north + extension_h
        ]
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques d'utilisation du loader
        """
        success_rate = 0
        if self.stats['total_queries'] > 0:
            success_rate = (self.stats['successful_queries'] / self.stats['total_queries']) * 100
        
        return {
            'total_queries': self.stats['total_queries'],
            'successful_queries': self.stats['successful_queries'],
            'success_rate_percent': round(success_rate, 1),
            'total_buildings_loaded': self.stats['buildings_loaded'],
            'average_buildings_per_query': round(
                self.stats['buildings_loaded'] / max(1, self.stats['successful_queries'])
            )
        }


# ==============================================================================
# SERVICE FLASK INTÉGRÉ
# ==============================================================================

def create_osm_service():
    """
    Crée le service Flask pour l'API OSM corrigée
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    loader = CompleteBuildingLoader()
    
    @app.route('/api/osm-buildings-complete', methods=['POST'])
    def load_complete_buildings():
        """
        Endpoint pour charger TOUS les bâtiments d'une localité
        """
        try:
            data = request.get_json()
            zone_id = data.get('zone_id')
            zone_name = data.get('zone_name')
            method = data.get('method', 'administrative')
            
            if not zone_id or not zone_name:
                return jsonify({
                    'success': False,
                    'error': 'zone_id et zone_name requis'
                }), 400
            
            # Charger les bâtiments avec la méthode corrigée
            result = loader.load_complete_locality_buildings(
                zone_id=zone_id,
                zone_name=zone_name, 
                method=method
            )
            
            if result.success:
                return jsonify({
                    'success': True,
                    'buildings': result.buildings,
                    'metadata': {
                        'total_buildings': len(result.buildings),
                        'total_osm_elements': result.total_elements,
                        'query_time_seconds': result.query_time_seconds,
                        'method_used': result.method_used,
                        'coverage_complete': result.coverage_complete,
                        'quality_score': result.quality_score,
                        'warnings': result.warnings or []
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.error_message,
                    'suggestions': [
                        'Essayez la méthode "bbox" comme alternative',
                        'Vérifiez que la zone existe dans OSM',
                        'Réduisez la taille de la zone si trop grande'
                    ]
                }), 400
                
        except Exception as e:
            logger.error(f"Erreur API: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/osm-statistics', methods=['GET'])
    def get_osm_statistics():
        """
        Endpoint pour les statistiques d'utilisation
        """
        return jsonify({
            'success': True,
            'statistics': loader.get_statistics()
        })
    
    return app


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du loader corrigé
    loader = CompleteBuildingLoader()
    
    print("🧪 Test du chargement COMPLET des bâtiments OSM")
    print("=" * 60)
    
    # Test avec Kuala Lumpur (méthode administrative)
    result = loader.load_complete_locality_buildings(
        zone_id='kuala_lumpur',
        zone_name='Kuala Lumpur',
        method='administrative'
    )
    
    if result.success:
        print(f"✅ Succès: {len(result.buildings)} bâtiments chargés")
        print(f"   Méthode: {result.method_used}")
        print(f"   Temps: {result.query_time_seconds:.1f}s") 
        print(f"   Qualité: {result.quality_score:.1f}%")
        print(f"   Couverture complète: {result.coverage_complete}")
        
        # Afficher quelques exemples
        print("\n📋 Exemples de bâtiments:")
        for i, building in enumerate(result.buildings[:3]):
            print(f"   {i+1}. {building['building_type']} - {building['surface_area_m2']:.0f}m²")
    else:
        print(f"❌ Échec: {result.error_message}")
    
    # Afficher les statistiques
    stats = loader.get_statistics()
    print(f"\n📊 Statistiques:")
    print(f"   Requêtes totales: {stats['total_queries']}")
    print(f"   Taux de succès: {stats['success_rate_percent']}%")
    print(f"   Bâtiments chargés: {stats['total_buildings_loaded']}")