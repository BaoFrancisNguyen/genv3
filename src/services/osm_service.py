"""
Service OSM - Couche métier pour OpenStreetMap
==============================================

Ce service fait l'interface entre l'application et le gestionnaire OSM,
en ajoutant la logique métier et la gestion d'erreurs de haut niveau.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.core.osm_handler import OSMHandler, OSMQueryResult
from src.models.building import Building
from config import MALAYSIA_ZONES


# Configuration du logger
logger = logging.getLogger(__name__)


class OSMService:
    """
    Service métier pour les opérations OpenStreetMap
    
    Encapsule la logique métier, la validation et la gestion d'erreurs
    pour toutes les opérations liées à OSM.
    """
    
    def __init__(self, osm_handler: OSMHandler):
        """
        Initialise le service OSM
        
        Args:
            osm_handler: Instance du gestionnaire OSM
        """
        self.osm_handler = osm_handler
        self.last_query_result = None
        self.service_statistics = {
            'successful_queries': 0,
            'failed_queries': 0,
            'total_buildings_loaded': 0,
            'service_start_time': datetime.now()
        }
        
        logger.info("✅ Service OSM initialisé")
    
    def get_available_zones(self) -> List[Dict]:
        """
        Retourne la liste complète des zones disponibles pour OSM
        
        Returns:
            List[Dict]: Zones disponibles avec métadonnées complètes
        """
        try:
            zones = []
            
            # Malaysia entière
            if hasattr(MALAYSIA_ZONES, 'COUNTRY'):
                for zone_id, zone_data in MALAYSIA_ZONES.COUNTRY.items():
                    zone_info = {
                        'zone_id': zone_id,
                        'name': zone_data['name'],
                        'type': zone_data.get('type', 'country'),
                        'population': zone_data.get('population', 0),
                        'estimated_buildings': zone_data.get('estimated_buildings', 0),
                        'area_km2': zone_data.get('area_km2', 0),
                        'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                        'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                        'recommended': False,  # Pays entier non recommandé
                        'warning': zone_data.get('warning', ''),
                        'bbox': zone_data.get('bbox', [])
                    }
                    zones.append(zone_info)
            
            # États
            if hasattr(MALAYSIA_ZONES, 'STATES'):
                for zone_id, zone_data in MALAYSIA_ZONES.STATES.items():
                    zone_info = {
                        'zone_id': zone_id,
                        'name': zone_data['name'],
                        'type': zone_data.get('type', 'state'),
                        'population': zone_data.get('population', 0),
                        'estimated_buildings': zone_data.get('estimated_buildings', 0),
                        'area_km2': zone_data.get('area_km2', 0),
                        'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                        'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                        'recommended': zone_data.get('estimated_buildings', 0) < 300000,
                        'capital': zone_data.get('capital', ''),
                        'bbox': zone_data.get('bbox', [])
                    }
                    zones.append(zone_info)
            
            # Territoires fédéraux
            if hasattr(MALAYSIA_ZONES, 'FEDERAL_TERRITORIES'):
                for zone_id, zone_data in MALAYSIA_ZONES.FEDERAL_TERRITORIES.items():
                    zone_info = {
                        'zone_id': zone_id,
                        'name': zone_data['name'],
                        'type': zone_data.get('type', 'federal_territory'),
                        'population': zone_data.get('population', 0),
                        'estimated_buildings': zone_data.get('estimated_buildings', 0),
                        'area_km2': zone_data.get('area_km2', 0),
                        'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                        'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                        'recommended': True,  # Territoires fédéraux recommandés
                        'bbox': zone_data.get('bbox', [])
                    }
                    zones.append(zone_info)
            
            # Villes principales
            if hasattr(MALAYSIA_ZONES, 'MAJOR_CITIES'):
                for zone_id, zone_data in MALAYSIA_ZONES.MAJOR_CITIES.items():
                    # Éviter les doublons (déjà dans territoires fédéraux)
                    if zone_id not in ['kuala_lumpur', 'putrajaya', 'labuan']:
                        zone_info = {
                            'zone_id': zone_id,
                            'name': zone_data['name'],
                            'type': 'city',
                            'state': zone_data.get('state', ''),
                            'population': zone_data.get('population', 0),
                            'estimated_buildings': zone_data.get('estimated_buildings', 0),
                            'area_km2': zone_data.get('area_km2', 0),
                            'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                            'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                            'recommended': zone_data.get('estimated_buildings', 0) < 100000,
                            'importance': zone_data.get('importance', ''),
                            'bbox': zone_data.get('bbox', [])
                        }
                        zones.append(zone_info)
            
            # Régions spéciales
            if hasattr(MALAYSIA_ZONES, 'SPECIAL_REGIONS'):
                for zone_id, zone_data in MALAYSIA_ZONES.SPECIAL_REGIONS.items():
                    zone_info = {
                        'zone_id': zone_id,
                        'name': zone_data['name'],
                        'type': zone_data.get('type', 'special'),
                        'description': zone_data.get('description', ''),
                        'population': zone_data.get('population', 0),
                        'estimated_buildings': zone_data.get('estimated_buildings', 0),
                        'area_km2': zone_data.get('area_km2', 0),
                        'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                        'has_osm_relation': False,  # Régions spéciales n'ont pas de relation OSM directe
                        'recommended': False,  # Régions complexes
                        'cities': zone_data.get('cities', []),
                        'bbox': zone_data.get('bbox', [])
                    }
                    zones.append(zone_info)
            
            # Fallback vers l'ancienne configuration si la nouvelle n'existe pas
            if not zones and hasattr(MALAYSIA_ZONES, 'MAJOR_ZONES'):
                logger.info("🔄 Utilisation de l'ancienne configuration MAJOR_ZONES")
                for zone_id, zone_data in MALAYSIA_ZONES.MAJOR_ZONES.items():
                    zone_info = {
                        'zone_id': zone_id,
                        'name': zone_data['name'],
                        'type': 'city',
                        'state': zone_data.get('state', ''),
                        'population': zone_data.get('population', 0),
                        'estimated_buildings': zone_data.get('estimated_buildings', 0),
                        'area_km2': zone_data.get('area_km2', 0),
                        'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 0)),
                        'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                        'recommended': zone_data.get('estimated_buildings', 0) < 100000,
                        'bbox': zone_data.get('bbox', [])
                    }
                    zones.append(zone_info)
            
            # Tri par complexité (simple en premier) puis par population
            zones.sort(key=lambda x: (
                {'simple': 1, 'modéré': 2, 'complexe': 3, 'très_complexe': 4, 'extrême': 5}.get(x['complexity_level'], 3),
                -x['population']
            ))
            
            logger.info(f"📍 {len(zones)} zones disponibles")
            return zones
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération zones: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_complexity_level(self, estimated_buildings: int) -> str:
        """Détermine le niveau de complexité selon le nombre de bâtiments"""
        if estimated_buildings < 10000:
            return 'simple'
        elif estimated_buildings < 50000:
            return 'modéré'
        elif estimated_buildings < 200000:
            return 'complexe'
        elif estimated_buildings < 1000000:
            return 'très_complexe'
        else:
            return 'extrême'
    
    def get_zone_estimation(self, zone_name: str) -> Dict:
        """
        Obtient l'estimation de complexité pour une zone
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Dict: Estimation détaillée avec recommandations
        """
        try:
            # Chercher la zone dans toutes les catégories
            zone_data = self._find_zone_in_all_categories(zone_name)
            
            if not zone_data:
                # Délégation au gestionnaire OSM pour compatibilité
                estimation = self.osm_handler.get_zone_estimation(zone_name)
                return estimation
            
            # Calculs d'estimation
            estimated_buildings = zone_data.get('estimated_buildings', 1000)
            area_km2 = zone_data.get('area_km2', 100)
            
            # Estimation du temps (base: 50000 bâtiments/minute)
            estimated_time_minutes = max(0.1, estimated_buildings / 50000)
            
            # Estimation de la taille (base: 200 bytes/bâtiment/jour)
            estimated_size_mb = max(0.1, (estimated_buildings * 200 * 31) / (1024 * 1024))  # 31 jours par défaut
            
            # Niveau de complexité
            complexity_level = self._get_complexity_level(estimated_buildings)
            
            # Recommandations selon la complexité
            recommendations = {
                'simple': 'Génération rapide recommandée',
                'modéré': 'Génération standard, quelques minutes',
                'complexe': 'Génération longue, soyez patient',
                'très_complexe': 'Génération très longue, considérer la subdivision en zones plus petites',
                'extrême': 'Génération extrêmement longue (plusieurs heures), fortement recommandé de subdiviser'
            }
            
            # Warnings spéciaux
            warnings = []
            if estimated_buildings > 1000000:
                warnings.append("ATTENTION: Volume très élevé - génération de plusieurs heures")
            if estimated_buildings > 500000:
                warnings.append("Assurez-vous d'avoir suffisamment de mémoire RAM")
            if complexity_level == 'extrême':
                warnings.append("Considérez utiliser une fréquence quotidienne plutôt qu'horaire")
            
            return {
                'zone_found': True,
                'zone_name': zone_data['name'],
                'zone_type': zone_data.get('type', 'unknown'),
                'estimated_buildings': estimated_buildings,
                'area_km2': area_km2,
                'estimated_time_minutes': round(estimated_time_minutes, 1),
                'estimated_size_mb': round(estimated_size_mb, 1),
                'complexity_level': complexity_level,
                'recommendation': recommendations.get(complexity_level, 'Complexité inconnue'),
                'warnings': warnings,
                'bbox': zone_data.get('bbox', []),
                'has_osm_relation': bool(zone_data.get('osm_relation_id'))
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur estimation zone {zone_name}: {str(e)}")
            return {
                'zone_found': False,
                'error': f"Erreur lors de l'estimation: {str(e)}"
            }
    
    def _find_zone_in_all_categories(self, zone_name: str) -> Optional[Dict]:
        """
        Cherche une zone dans toutes les catégories disponibles
        
        Args:
            zone_name: Nom de la zone à chercher
            
        Returns:
            Optional[Dict]: Données de la zone ou None si non trouvée
        """
        # Chercher dans toutes les catégories
        categories = []
        
        if hasattr(MALAYSIA_ZONES, 'COUNTRY'):
            categories.append(MALAYSIA_ZONES.COUNTRY)
        if hasattr(MALAYSIA_ZONES, 'STATES'):
            categories.append(MALAYSIA_ZONES.STATES)
        if hasattr(MALAYSIA_ZONES, 'FEDERAL_TERRITORIES'):
            categories.append(MALAYSIA_ZONES.FEDERAL_TERRITORIES)
        if hasattr(MALAYSIA_ZONES, 'MAJOR_CITIES'):
            categories.append(MALAYSIA_ZONES.MAJOR_CITIES)
        if hasattr(MALAYSIA_ZONES, 'SPECIAL_REGIONS'):
            categories.append(MALAYSIA_ZONES.SPECIAL_REGIONS)
        
        # Fallback vers MAJOR_ZONES si les nouvelles catégories n'existent pas
        if not categories and hasattr(MALAYSIA_ZONES, 'MAJOR_ZONES'):
            categories.append(MALAYSIA_ZONES.MAJOR_ZONES)
        
        for category in categories:
            if zone_name.lower() in category:
                return category[zone_name.lower()]
        
        return None
    
    def load_complete_zone_buildings(self, zone_name: str) -> Dict:
        """
        Charge tous les bâtiments OSM d'une zone complète
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Dict: Résultat du chargement avec bâtiments et métadonnées
        """
        try:
            logger.info(f"🔄 Début chargement zone complète: {zone_name}")
            
            # Validation du nom de zone
            is_valid, error = self._validate_zone_name(zone_name)
            if not is_valid:
                self.service_statistics['failed_queries'] += 1
                return {
                    'success': False,
                    'zone_name': zone_name,
                    'error': error,
                    'buildings': []
                }
            
            # Exécution de la requête OSM
            osm_result = self.osm_handler.get_complete_locality_buildings(zone_name)
            
            # Traitement du résultat
            if osm_result.success:
                self.service_statistics['successful_queries'] += 1
                self.service_statistics['total_buildings_loaded'] += len(osm_result.buildings)
                self.last_query_result = osm_result
                
                # Construction de la réponse de service
                service_response = {
                    'success': True,
                    'zone_name': zone_name,
                    'buildings': [building.to_dict() for building in osm_result.buildings],
                    'metadata': {
                        'total_buildings': len(osm_result.buildings),
                        'total_osm_elements': osm_result.total_elements,
                        'query_time_seconds': osm_result.query_time_seconds,
                        'bbox_used': osm_result.bbox_used,
                        'warnings': osm_result.warnings or []
                    },
                    'quality_metrics': self._calculate_quality_metrics(osm_result.buildings),
                    'statistics': self._generate_building_statistics(osm_result.buildings)
                }
                
                logger.info(f"✅ Zone chargée: {len(osm_result.buildings)} bâtiments en {osm_result.query_time_seconds:.1f}s")
                return service_response
                
            else:
                self.service_statistics['failed_queries'] += 1
                
                return {
                    'success': False,
                    'zone_name': zone_name,
                    'error': osm_result.error_message,
                    'buildings': [],
                    'fallback_available': True,
                    'suggestions': self._get_fallback_suggestions(zone_name)
                }
                
        except Exception as e:
            self.service_statistics['failed_queries'] += 1
            logger.error(f"❌ Erreur service chargement zone {zone_name}: {str(e)}")
            
            return {
                'success': False,
                'zone_name': zone_name,
                'error': f"Erreur service: {str(e)}",
                'buildings': []
            }
    
    def _validate_zone_name(self, zone_name: str) -> tuple:
        """Valide le nom d'une zone"""
        if not zone_name or not isinstance(zone_name, str):
            return False, "Nom de zone invalide"
        
        # Caractères autorisés
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz_-')
        if not all(c in allowed_chars for c in zone_name.lower()):
            return False, "Nom de zone contient des caractères non autorisés"
        
        return True, None
    
    def _calculate_quality_metrics(self, buildings: List[Building]) -> Dict:
        """Calcule les métriques de qualité pour une liste de bâtiments"""
        if not buildings:
            return {'quality_score': 0}
        
        total = len(buildings)
        
        # Métriques de base
        with_osm_tags = sum(1 for b in buildings if b.osm_tags)
        valid_coords = sum(1 for b in buildings if 0.5 <= b.latitude <= 7.5 and 99.0 <= b.longitude <= 120.0)
        valid_surface = sum(1 for b in buildings if b.surface_area_m2 > 0)
        
        # Score global
        completeness_score = (with_osm_tags / total) * 100
        coord_score = (valid_coords / total) * 100
        surface_score = (valid_surface / total) * 100
        
        overall_score = (completeness_score + coord_score + surface_score) / 3
        
        return {
            'quality_score': round(overall_score, 1),
            'completeness_percent': round(completeness_score, 1),
            'valid_coordinates_percent': round(coord_score, 1),
            'valid_surface_percent': round(surface_score, 1),
            'total_buildings': total
        }
    
    def _generate_building_statistics(self, buildings: List[Building]) -> Dict:
        """Génère des statistiques sur les bâtiments"""
        if not buildings:
            return {}
        
        # Comptage par type
        type_counts = {}
        total_surface = 0
        total_consumption = 0
        
        for building in buildings:
            # Type de bâtiment
            building_type = building.building_type or 'unknown'
            type_counts[building_type] = type_counts.get(building_type, 0) + 1
            
            # Totaux
            total_surface += building.surface_area_m2
            total_consumption += building.base_consumption_kwh
        
        return {
            'type_distribution': type_counts,
            'total_surface_m2': round(total_surface, 1),
            'average_surface_m2': round(total_surface / len(buildings), 1),
            'total_consumption_kwh_per_day': round(total_consumption, 1),
            'average_consumption_kwh_per_day': round(total_consumption / len(buildings), 1)
        }
    
    def _get_fallback_suggestions(self, zone_name: str) -> List[str]:
        """Génère des suggestions en cas d'échec"""
        suggestions = [
            "Vérifiez l'orthographe du nom de zone",
            "Essayez une zone plus petite",
            "Consultez la liste des zones disponibles"
        ]
        
        # Suggestions spécifiques selon le nom
        if 'malaysia' in zone_name.lower():
            suggestions.append("Le pays entier peut prendre plusieurs heures - essayez un état spécifique")
        
        return suggestions
    
    def test_connection(self) -> bool:
        """
        Teste la connexion aux services OSM
        
        Returns:
            bool: True si la connexion fonctionne
        """
        try:
            from src.core.osm_handler import test_osm_connection
            return test_osm_connection()
        except Exception as e:
            logger.error(f"❌ Erreur test connexion OSM: {str(e)}")
            return False
    
    def get_service_status(self) -> Dict:
        """
        Retourne le statut du service OSM
        
        Returns:
            Dict: Statut et statistiques du service
        """
        uptime = datetime.now() - self.service_statistics['service_start_time']
        
        success_rate = 0
        total_queries = self.service_statistics['successful_queries'] + self.service_statistics['failed_queries']
        if total_queries > 0:
            success_rate = (self.service_statistics['successful_queries'] / total_queries) * 100
        
        return {
            'service_name': 'OSM Service',
            'status': 'active',
            'connection_ok': self.test_connection(),
            'uptime_seconds': int(uptime.total_seconds()),
            'statistics': {
                'successful_queries': self.service_statistics['successful_queries'],
                'failed_queries': self.service_statistics['failed_queries'],
                'success_rate_percent': round(success_rate, 1),
                'total_buildings_loaded': self.service_statistics['total_buildings_loaded']
            }
        }
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques détaillées du service
        
        Returns:
            Dict: Statistiques complètes
        """
        return self.service_statistics.copy()