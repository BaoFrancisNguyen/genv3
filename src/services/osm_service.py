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
        Retourne la liste des zones disponibles pour OSM
        
        Returns:
            List[Dict]: Zones disponibles avec métadonnées
        """
        try:
            zones = []
            
            # Zones principales de Malaysia
            for zone_id, zone_data in MALAYSIA_ZONES.MAJOR_ZONES.items():
                zone_info = {
                    'zone_id': zone_id,
                    'name': zone_data['name'],
                    'state': zone_data['state'],
                    'population': zone_data['population'],
                    'estimated_buildings': zone_data.get('estimated_buildings', 'Unknown'),
                    'area_km2': zone_data.get('area_km2', 0),
                    'complexity_level': self._get_complexity_level(zone_data.get('estimated_buildings', 1000)),
                    'has_osm_relation': bool(zone_data.get('osm_relation_id')),
                    'recommended': zone_data.get('estimated_buildings', 1000) < 50000
                }
                zones.append(zone_info)
            
            # Tri par population (plus grande en premier)
            zones.sort(key=lambda x: x['population'], reverse=True)
            
            logger.info(f"📍 {len(zones)} zones disponibles")
            return zones
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération zones: {str(e)}")
            return []
    
    def get_zone_estimation(self, zone_name: str) -> Dict:
        """
        Obtient l'estimation de complexité pour une zone
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Dict: Estimation détaillée avec recommandations
        """
        try:
            # Délégation au gestionnaire OSM
            estimation = self.osm_handler.get_zone_estimation(zone_name)
            
            if not estimation.get('zone_found', False):
                return {
                    'success': False,
                    'error': f"Zone '{zone_name}' non trouvée",
                    'available_zones': [z['zone_id'] for z in self.get_available_zones()]
                }
            
            # Enrichissement avec logique métier
            estimated_buildings = estimation.get('estimated_buildings', 0)
            
            # Ajout de warnings et recommandations
            warnings = []
            recommendations = []
            
            if estimated_buildings > 100000:
                warnings.append("Très grande zone - temps de traitement long")
                recommendations.append("Considérer subdiviser la requête")
            elif estimated_buildings > 50000:
                warnings.append("Grande zone - soyez patient")
                recommendations.append("Prévoir 10-15 minutes de traitement")
            
            if estimation.get('estimated_time_minutes', 0) > 10:
                recommendations.append("Requête longue - ne pas fermer le navigateur")
            
            # Enrichissement de l'estimation
            enriched_estimation = estimation.copy()
            enriched_estimation.update({
                'success': True,
                'warnings': warnings,
                'recommendations': recommendations,
                'suitable_for_demo': estimated_buildings < 10000,
                'requires_patience': estimated_buildings > 25000,
                'risk_level': self._assess_risk_level(estimated_buildings)
            })
            
            return enriched_estimation
            
        except Exception as e:
            logger.error(f"❌ Erreur estimation zone {zone_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_complete_zone_buildings(self, zone_name: str) -> Dict:
        """
        Charge tous les bâtiments d'une zone avec gestion complète
        
        Args:
            zone_name: Nom de la zone à charger
            
        Returns:
            Dict: Résultats avec bâtiments et métadonnées
        """
        try:
            logger.info(f"🔄 Début chargement zone complète: {zone_name}")
            
            # Pré-validation de la zone
            estimation = self.get_zone_estimation(zone_name)
            if not estimation.get('success', False):
                return estimation
            
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
    
    def test_connection(self) -> bool:
        """
        Teste la connexion aux services OSM
        
        Returns:
            bool: True si la connexion fonctionne
        """
        try:
            # Test via une petite requête
            from src.core.osm_handler import test_osm_connection
            return test_osm_connection()
            
        except Exception as e:
            logger.error(f"❌ Test connexion OSM échoué: {str(e)}")
            return False
    
    def get_service_status(self) -> Dict:
        """
        Retourne l'état du service OSM
        
        Returns:
            Dict: État détaillé du service
        """
        uptime = datetime.now() - self.service_statistics['service_start_time']
        connection_ok = self.test_connection()
        
        total_queries = (
            self.service_statistics['successful_queries'] + 
            self.service_statistics['failed_queries']
        )
        
        success_rate = 0
        if total_queries > 0:
            success_rate = (self.service_statistics['successful_queries'] / total_queries) * 100
        
        return {
            'service_name': 'OSM Service',
            'status': 'active' if connection_ok else 'degraded',
            'connection_ok': connection_ok,
            'uptime_seconds': int(uptime.total_seconds()),
            'statistics': {
                'successful_queries': self.service_statistics['successful_queries'],
                'failed_queries': self.service_statistics['failed_queries'],
                'total_buildings_loaded': self.service_statistics['total_buildings_loaded'],
                'success_rate_percent': round(success_rate, 1)
            },
            'last_query': {
                'exists': self.last_query_result is not None,
                'buildings_count': len(self.last_query_result.buildings) if self.last_query_result else 0,
                'query_time': self.last_query_result.query_time_seconds if self.last_query_result else 0
            }
        }
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques détaillées du service
        
        Returns:
            Dict: Statistiques complètes
        """
        stats = self.service_statistics.copy()
        
        # Ajout des statistiques du gestionnaire OSM
        osm_stats = self.osm_handler.get_statistics()
        stats.update({
            'osm_handler_stats': osm_stats,
            'available_zones_count': len(self.get_available_zones())
        })
        
        return stats
    
    def _get_complexity_level(self, estimated_buildings: int) -> str:
        """
        Détermine le niveau de complexité d'une zone
        
        Args:
            estimated_buildings: Nombre estimé de bâtiments
            
        Returns:
            str: Niveau de complexité
        """
        if estimated_buildings < 5000:
            return 'simple'
        elif estimated_buildings < 25000:
            return 'modéré'
        elif estimated_buildings < 100000:
            return 'complexe'
        else:
            return 'très_complexe'
    
    def _assess_risk_level(self, estimated_buildings: int) -> str:
        """
        Évalue le niveau de risque d'une requête
        
        Args:
            estimated_buildings: Nombre estimé de bâtiments
            
        Returns:
            str: Niveau de risque
        """
        if estimated_buildings < 10000:
            return 'faible'
        elif estimated_buildings < 50000:
            return 'modéré'
        elif estimated_buildings < 200000:
            return 'élevé'
        else:
            return 'très_élevé'
    
    def _calculate_quality_metrics(self, buildings: List[Building]) -> Dict:
        """
        Calcule les métriques de qualité des bâtiments chargés
        
        Args:
            buildings: Liste des bâtiments
            
        Returns:
            Dict: Métriques de qualité
        """
        if not buildings:
            return {'quality_score': 0, 'issues': ['Aucun bâtiment chargé']}
        
        metrics = {
            'total_buildings': len(buildings),
            'buildings_with_osm_id': 0,
            'buildings_with_coordinates': 0,
            'buildings_with_type': 0,
            'buildings_with_surface': 0,
            'unique_types_count': 0,
            'coordinate_validity': 0,
            'quality_score': 0,
            'issues': []
        }
        
        # Analyse des bâtiments
        valid_coordinates = 0
        building_types = set()
        
        for building in buildings:
            # OSM ID
            if building.osm_id:
                metrics['buildings_with_osm_id'] += 1
            
            # Coordonnées
            if building.latitude and building.longitude:
                metrics['buildings_with_coordinates'] += 1
                
                # Validation coordonnées Malaysia
                if (0.5 <= building.latitude <= 7.5 and 
                    99.0 <= building.longitude <= 120.0):
                    valid_coordinates += 1
            
            # Type de bâtiment
            if building.building_type and building.building_type != 'unknown':
                metrics['buildings_with_type'] += 1
                building_types.add(building.building_type)
            
            # Surface
            if building.surface_area_m2 > 0:
                metrics['buildings_with_surface'] += 1
        
        # Calculs des pourcentages
        total = len(buildings)
        metrics['coordinate_validity'] = (valid_coordinates / total) * 100
        metrics['unique_types_count'] = len(building_types)
        
        # Calcul du score de qualité global
        completeness_score = (
            (metrics['buildings_with_coordinates'] / total) * 30 +
            (metrics['buildings_with_type'] / total) * 25 +
            (metrics['buildings_with_surface'] / total) * 20 +
            (metrics['buildings_with_osm_id'] / total) * 15 +
            (valid_coordinates / total) * 10
        )
        
        metrics['quality_score'] = round(completeness_score, 1)
        
        # Identification des problèmes
        if metrics['coordinate_validity'] < 95:
            metrics['issues'].append(f"Coordonnées invalides: {100 - metrics['coordinate_validity']:.1f}%")
        
        if metrics['unique_types_count'] < 3:
            metrics['issues'].append("Diversité de types de bâtiments faible")
        
        if metrics['buildings_with_surface'] < total * 0.8:
            metrics['issues'].append("Données de surface manquantes")
        
        return metrics
    
    def _generate_building_statistics(self, buildings: List[Building]) -> Dict:
        """
        Génère des statistiques sur les bâtiments chargés
        
        Args:
            buildings: Liste des bâtiments
            
        Returns:
            Dict: Statistiques des bâtiments
        """
        if not buildings:
            return {}
        
        # Distribution par type
        type_distribution = {}
        surface_stats = []
        
        for building in buildings:
            # Comptage par type
            building_type = building.building_type or 'unknown'
            type_distribution[building_type] = type_distribution.get(building_type, 0) + 1
            
            # Statistiques de surface
            if building.surface_area_m2 > 0:
                surface_stats.append(building.surface_area_m2)
        
        # Calculs statistiques de surface
        surface_statistics = {}
        if surface_stats:
            import statistics
            surface_statistics = {
                'moyenne_m2': round(statistics.mean(surface_stats), 1),
                'mediane_m2': round(statistics.median(surface_stats), 1),
                'min_m2': min(surface_stats),
                'max_m2': max(surface_stats),
                'total_m2': sum(surface_stats)
            }
        
        return {
            'distribution_types': type_distribution,
            'type_le_plus_commun': max(type_distribution.items(), key=lambda x: x[1])[0] if type_distribution else None,
            'surface_statistics': surface_statistics,
            'buildings_avec_surface': len(surface_stats),
            'pourcentage_avec_surface': (len(surface_stats) / len(buildings)) * 100
        }
    
    def _get_fallback_suggestions(self, zone_name: str) -> List[str]:
        """
        Génère des suggestions en cas d'échec de chargement
        
        Args:
            zone_name: Nom de la zone qui a échoué
            
        Returns:
            List[str]: Liste de suggestions
        """
        suggestions = [
            "Vérifier la connexion internet",
            "Réessayer dans quelques minutes",
            "Choisir une zone plus petite",
        ]
        
        # Suggestions spécifiques selon la zone
        available_zones = self.get_available_zones()
        smaller_zones = [z for z in available_zones if z.get('estimated_buildings', 0) < 25000]
        
        if smaller_zones:
            suggestions.append(f"Essayer une zone plus petite comme: {smaller_zones[0]['name']}")
        
        return suggestions


# ==============================================================================
# FONCTIONS UTILITAIRES DU SERVICE
# ==============================================================================

def validate_zone_name(zone_name: str) -> tuple:
    """
    Valide qu'un nom de zone est acceptable
    
    Args:
        zone_name: Nom de la zone à valider
        
    Returns:
        tuple: (valid, error_message)
    """
    if not zone_name:
        return False, "Nom de zone requis"
    
    if not isinstance(zone_name, str):
        return False, "Nom de zone doit être une chaîne"
    
    if len(zone_name.strip()) < 2:
        return False, "Nom de zone trop court"
    
    # Vérification caractères autorisés
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz_-')
    if not all(c in allowed_chars for c in zone_name.lower()):
        return False, "Nom de zone contient des caractères non autorisés"
    
    return True, None


def format_building_summary(buildings: List[Building]) -> str:
    """
    Formate un résumé textuel des bâtiments
    
    Args:
        buildings: Liste des bâtiments
        
    Returns:
        str: Résumé formaté
    """
    if not buildings:
        return "Aucun bâtiment trouvé"
    
    # Comptage par type
    type_counts = {}
    for building in buildings:
        building_type = building.building_type or 'unknown'
        type_counts[building_type] = type_counts.get(building_type, 0) + 1
    
    # Tri par fréquence
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Construction du résumé
    summary_parts = [f"{len(buildings)} bâtiments total"]
    
    for building_type, count in sorted_types[:5]:  # Top 5 types
        percentage = (count / len(buildings)) * 100
        summary_parts.append(f"{building_type}: {count} ({percentage:.1f}%)")
    
    if len(sorted_types) > 5:
        remaining = sum(count for _, count in sorted_types[5:])
        summary_parts.append(f"autres: {remaining}")
    
    return " | ".join(summary_parts)


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du service OSM
    from src.core.osm_handler import OSMHandler
    
    # Initialisation
    osm_handler = OSMHandler()
    osm_service = OSMService(osm_handler)
    
    # Test connexion
    print(f"🔗 Connexion OSM: {'✅ OK' if osm_service.test_connection() else '❌ Échec'}")
    
    # Liste des zones
    zones = osm_service.get_available_zones()
    print(f"📍 {len(zones)} zones disponibles:")
    for zone in zones[:3]:
        print(f"  - {zone['name']}: {zone['estimated_buildings']} bâtiments estimés")
    
    # Estimation pour une zone
    estimation = osm_service.get_zone_estimation('kuala_lumpur')
    if estimation.get('success'):
        print(f"⏱️ Estimation KL: {estimation['estimated_time_minutes']} min, {estimation['estimated_size_mb']} MB")
    
    # Statut du service
    status = osm_service.get_service_status()
    print(f"📊 Service: {status['status']}, {status['statistics']['success_rate_percent']}% succès")
