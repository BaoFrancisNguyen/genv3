"""
Service de Génération - Couche métier pour la génération de données électriques
==============================================================================

Ce service orchestre la génération complète des données électriques.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from src.core.generator import ElectricityDataGenerator
from src.models.building import Building


# Configuration du logger
logger = logging.getLogger(__name__)


class GenerationService:
    """
    Service métier pour la génération de données électriques
    
    Coordonne la génération complète en gérant la validation,
    l'optimisation et la qualité des données produites.
    """
    
    def __init__(self, generator: ElectricityDataGenerator):
        """
        Initialise le service de génération
        
        Args:
            generator: Instance du générateur de données électriques
        """
        self.generator = generator
        self.service_statistics = {
            'total_generations': 0,
            'successful_generations': 0,
            'total_buildings_processed': 0,
            'total_observations_created': 0,
            'service_start_time': datetime.now()
        }
        
        logger.info("✅ Service de génération initialisé")
    
    def generate_complete_dataset(
        self,
        zone_name: str,
        buildings_osm: List[Dict],
        start_date: str,
        end_date: str,
        frequency: str = '30T'
    ) -> Dict:
        """
        Génère un dataset complet avec bâtiments et séries temporelles
        
        Args:
            zone_name: Nom de la zone
            buildings_osm: Données des bâtiments OSM
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            frequency: Fréquence d'échantillonnage
            
        Returns:
            Dict: Dataset complet avec métadonnées
        """
        try:
            logger.info(f"🔄 Génération dataset complet - Zone: {zone_name}")
            logger.info(f"📊 {len(buildings_osm)} bâtiments, période: {start_date} → {end_date}")
            
            # Mise à jour des statistiques
            self.service_statistics['total_generations'] += 1
            
            # Phase 1: Validation des paramètres
            validation_result = self._validate_generation_request(
                buildings_osm, start_date, end_date, frequency
            )
            
            if not validation_result['valid']:
                logger.error(f"❌ Validation échouée: {validation_result['errors']}")
                return {
                    'success': False,
                    'error': 'Paramètres invalides',
                    'validation_errors': validation_result['errors']
                }
            
            # Phase 2: Conversion des bâtiments OSM en objets Building
            logger.info("🏗️ Conversion des bâtiments OSM...")
            buildings_conversion = self._convert_osm_to_buildings(buildings_osm, zone_name)
            
            if not buildings_conversion['success']:
                logger.error(f"❌ Conversion OSM échouée: {buildings_conversion.get('error')}")
                return buildings_conversion
            
            buildings = buildings_conversion['buildings']
            self.service_statistics['total_buildings_processed'] += len(buildings)
            
            # Phase 3: Génération des métadonnées de bâtiments
            logger.info("📋 Génération des métadonnées...")
            buildings_df = self.generator.generate_building_metadata(buildings)
            
            # Phase 4: Génération des séries temporelles
            logger.info("⏰ Génération des séries temporelles...")
            timeseries_df = self.generator.generate_timeseries_for_buildings(
                buildings, start_date, end_date, frequency
            )
            
            self.service_statistics['total_observations_created'] += len(timeseries_df)
            
            # Phase 5: Validation et nettoyage des données générées
            logger.info("🧹 Contrôle qualité...")
            quality_check = self._perform_quality_check(buildings_df, timeseries_df)
            
            # Phase 6: Génération du résumé statistique
            summary = self.generator.get_generation_summary(buildings, timeseries_df)
            
            # Mise à jour des statistiques de succès
            self.service_statistics['successful_generations'] += 1
            
            # Construction de la réponse complète
            response = {
                'success': True,
                'zone_name': zone_name,
                'generation_timestamp': datetime.now().isoformat(),
                'buildings_data': buildings_df.to_dict('records'),
                'timeseries_data': timeseries_df.to_dict('records'),
                'statistics': {
                    'total_buildings': len(buildings),
                    'total_observations': len(timeseries_df),
                    'date_range': {
                        'start': start_date,
                        'end': end_date,
                        'frequency': frequency
                    },
                    'generation_summary': summary,
                    'quality_metrics': quality_check
                },
                'conversion_info': buildings_conversion['conversion_info'],
                'validation_warnings': validation_result.get('warnings', [])
            }
            
            logger.info(f"✅ Génération terminée: {len(timeseries_df)} observations créées")
            return response
            
        except Exception as e:
            self.service_statistics['total_generations'] += 1  # Compter les échecs aussi
            logger.error(f"❌ Erreur génération dataset: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f"Erreur de génération: {str(e)}",
                'zone_name': zone_name
            }
    
    def _validate_generation_request(
        self,
        buildings_osm: List[Dict],
        start_date: str,
        end_date: str,
        frequency: str
    ) -> Dict:
        """
        Valide une requête de génération complète
        
        Args:
            buildings_osm: Données des bâtiments OSM
            start_date: Date de début
            end_date: Date de fin
            frequency: Fréquence
            
        Returns:
            Dict: Résultats de validation
        """
        errors = []
        warnings = []
        
        # Validation des bâtiments OSM
        if not buildings_osm:
            errors.append("Aucun bâtiment OSM fourni")
        elif len(buildings_osm) > 50000:
            errors.append("Trop de bâtiments (max 50000)")
        elif len(buildings_osm) > 10000:
            warnings.append("Grand nombre de bâtiments - génération longue")
        
        # Validation des paramètres temporels
        try:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            if start >= end:
                errors.append("Date de fin doit être après date de début")
            
            if (end - start).days > 365:
                errors.append("Période maximale: 365 jours")
                
        except Exception as e:
            errors.append(f"Format de dates invalide: {str(e)}")
        
        # Validation fréquence
        valid_frequencies = ['15T', '30T', '1H', '3H', 'D']
        if frequency not in valid_frequencies:
            errors.append(f"Fréquence invalide. Supportées: {valid_frequencies}")
        
        # Validation de la cohérence des données OSM
        osm_validation = self._validate_osm_data_quality(buildings_osm)
        if osm_validation['warnings']:
            warnings.extend(osm_validation['warnings'])
        if osm_validation['critical_errors']:
            errors.extend(osm_validation['critical_errors'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'osm_quality_score': osm_validation['quality_score']
        }
    
    def _validate_osm_data_quality(self, buildings_osm: List[Dict]) -> Dict:
        """
        Valide la qualité des données OSM
        
        Args:
            buildings_osm: Données des bâtiments OSM
            
        Returns:
            Dict: Évaluation de qualité
        """
        if not buildings_osm:
            return {
                'quality_score': 0,
                'warnings': [],
                'critical_errors': ['Aucune donnée OSM']
            }
        
        warnings = []
        critical_errors = []
        quality_metrics = {
            'has_coordinates': 0,
            'has_building_type': 0,
            'has_valid_coordinates': 0,
            'has_osm_id': 0
        }
        
        for i, building_data in enumerate(buildings_osm):
            # Vérification coordonnées
            lat = building_data.get('latitude') or building_data.get('lat')
            lon = building_data.get('longitude') or building_data.get('lon')
            
            if lat is not None and lon is not None:
                quality_metrics['has_coordinates'] += 1
                
                # Validation coordonnées Malaysia
                try:
                    lat_f, lon_f = float(lat), float(lon)
                    if 0.5 <= lat_f <= 7.5 and 99.0 <= lon_f <= 120.0:
                        quality_metrics['has_valid_coordinates'] += 1
                    else:
                        warnings.append(f"Bâtiment {i}: coordonnées hors Malaysia")
                except:
                    warnings.append(f"Bâtiment {i}: coordonnées non numériques")
            
            # Vérification type de bâtiment
            building_type = building_data.get('building_type')
            if building_type:
                quality_metrics['has_building_type'] += 1
            
            # Vérification ID OSM
            osm_id = building_data.get('osm_id') or building_data.get('id')
            if osm_id:
                quality_metrics['has_osm_id'] += 1
        
        # Calcul du score de qualité
        total_buildings = len(buildings_osm)
        coord_score = (quality_metrics['has_valid_coordinates'] / total_buildings) * 40
        type_score = (quality_metrics['has_building_type'] / total_buildings) * 30
        id_score = (quality_metrics['has_osm_id'] / total_buildings) * 30
        
        quality_score = coord_score + type_score + id_score
        
        return {
            'quality_score': round(quality_score, 1),
            'warnings': warnings,
            'critical_errors': critical_errors,
            'metrics': quality_metrics
        }
    
    def _convert_osm_to_buildings(self, buildings_osm: List[Dict], zone_name: str) -> Dict:
        """
        Convertit les données OSM en objets Building
        
        Args:
            buildings_osm: Données OSM des bâtiments
            zone_name: Nom de la zone
            
        Returns:
            Dict: Résultat de conversion
        """
        try:
            buildings = []
            conversion_stats = {
                'processed': 0,
                'converted': 0,
                'skipped': 0,
                'errors': []
            }
            
            for i, osm_data in enumerate(buildings_osm):
                conversion_stats['processed'] += 1
                
                try:
                    # Extraction des coordonnées
                    lat = osm_data.get('latitude') or osm_data.get('lat')
                    lon = osm_data.get('longitude') or osm_data.get('lon')
                    
                    if lat is None or lon is None:
                        conversion_stats['skipped'] += 1
                        continue
                    
                    # Création de l'objet Building
                    building = Building(
                        osm_id=str(osm_data.get('osm_id', osm_data.get('id', f'gen_{i}'))),
                        latitude=float(lat),
                        longitude=float(lon),
                        building_type=osm_data.get('building_type', 'residential'),
                        surface_area_m2=osm_data.get('surface_area_m2', 100.0),
                        base_consumption_kwh=osm_data.get('base_consumption_kwh', 15.0),
                        zone_name=zone_name,
                        osm_tags=osm_data.get('osm_tags', {})
                    )
                    
                    buildings.append(building)
                    conversion_stats['converted'] += 1
                    
                except Exception as e:
                    conversion_stats['skipped'] += 1
                    conversion_stats['errors'].append(f"Bâtiment {i}: {str(e)}")
            
            success_rate = (conversion_stats['converted'] / conversion_stats['processed']) * 100
            
            return {
                'success': conversion_stats['converted'] > 0,
                'buildings': buildings,
                'conversion_info': {
                    'success_rate_percent': round(success_rate, 1),
                    'statistics': conversion_stats
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Erreur conversion OSM: {str(e)}",
                'buildings': []
            }
    
    def _perform_quality_check(self, buildings_df: pd.DataFrame, timeseries_df: pd.DataFrame) -> Dict:
        """
        Effectue un contrôle qualité sur les données générées
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Métriques de qualité
        """
        quality_metrics = {
            'overall_score': 100.0,
            'buildings_quality': {},
            'timeseries_quality': {},
            'issues': []
        }
        
        # Contrôle qualité des bâtiments
        if not buildings_df.empty:
            # Vérification des doublons
            duplicates = buildings_df.duplicated(subset=['latitude', 'longitude']).sum()
            if duplicates > 0:
                quality_metrics['overall_score'] -= 5
                quality_metrics['issues'].append(f"{duplicates} bâtiments doublons")
            
            # Vérification des coordonnées
            invalid_coords = ((buildings_df['latitude'] < 0.5) | 
                            (buildings_df['latitude'] > 7.5) |
                            (buildings_df['longitude'] < 99.0) | 
                            (buildings_df['longitude'] > 120.0)).sum()
            
            if invalid_coords > 0:
                quality_metrics['overall_score'] -= 10
                quality_metrics['issues'].append(f"{invalid_coords} coordonnées invalides")
            
            quality_metrics['buildings_quality'] = {
                'total_buildings': len(buildings_df),
                'duplicates': duplicates,
                'invalid_coordinates': invalid_coords
            }
        
        # Contrôle qualité des séries temporelles
        if not timeseries_df.empty:
            # Vérification des valeurs négatives
            negative_values = (timeseries_df['consumption_kwh'] < 0).sum()
            if negative_values > 0:
                quality_metrics['overall_score'] -= 15
                quality_metrics['issues'].append(f"{negative_values} valeurs négatives")
            
            # Vérification des valeurs nulles
            null_values = timeseries_df['consumption_kwh'].isnull().sum()
            if null_values > 0:
                quality_metrics['overall_score'] -= 20
                quality_metrics['issues'].append(f"{null_values} valeurs nulles")
            
            # Vérification de la cohérence temporelle
            if 'timestamp' in timeseries_df.columns:
                time_gaps = timeseries_df['timestamp'].duplicated().sum()
                if time_gaps > 0:
                    quality_metrics['overall_score'] -= 5
                    quality_metrics['issues'].append(f"{time_gaps} doublons temporels")
            
            quality_metrics['timeseries_quality'] = {
                'total_observations': len(timeseries_df),
                'negative_values': negative_values,
                'null_values': null_values,
                'mean_consumption': timeseries_df['consumption_kwh'].mean(),
                'std_consumption': timeseries_df['consumption_kwh'].std()
            }
        
        quality_metrics['overall_score'] = max(0.0, quality_metrics['overall_score'])
        return quality_metrics
    
    def estimate_generation_resources(
        self,
        num_buildings: int,
        start_date: str,
        end_date: str,
        frequency: str
    ) -> Dict:
        """
        Estime les ressources nécessaires pour la génération
        
        Args:
            num_buildings: Nombre de bâtiments
            start_date: Date de début
            end_date: Date de fin
            frequency: Fréquence
            
        Returns:
            Dict: Estimation des ressources
        """
        try:
            # Calcul du nombre d'observations
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            date_range = pd.date_range(start=start, end=end, freq=frequency)
            
            total_observations = num_buildings * len(date_range)
            
            # Estimation du temps (approximatif)
            observations_per_second = 10000  # Calibré selon les performances
            estimated_time_seconds = total_observations / observations_per_second
            
            # Estimation de la taille mémoire (approximatif)
            bytes_per_observation = 100  # Estimation
            estimated_memory_mb = (total_observations * bytes_per_observation) / (1024 * 1024)
            
            # Niveau de complexité
            if total_observations < 50000:
                complexity = 'simple'
                recommendation = 'Génération rapide'
            elif total_observations < 500000:
                complexity = 'modéré'
                recommendation = 'Génération standard'
            elif total_observations < 2000000:
                complexity = 'complexe'
                recommendation = 'Génération longue - soyez patient'
            else:
                complexity = 'très_complexe'
                recommendation = 'Génération très longue - considérer la réduction'
            
            return {
                'num_buildings': num_buildings,
                'date_range_days': (end - start).days,
                'frequency': frequency,
                'total_observations': total_observations,
                'estimated_time_seconds': round(estimated_time_seconds, 1),
                'estimated_time_minutes': round(estimated_time_seconds / 60, 1),
                'estimated_memory_mb': round(estimated_memory_mb, 1),
                'complexity_level': complexity,
                'recommendation': recommendation
            }
            
        except Exception as e:
            return {
                'error': f"Erreur estimation: {str(e)}",
                'num_buildings': num_buildings,
                'complexity_level': 'unknown'
            }
    
    def get_service_status(self) -> Dict:
        """
        Retourne le statut du service de génération
        
        Returns:
            Dict: Statut et statistiques du service
        """
        uptime = datetime.now() - self.service_statistics['service_start_time']
        
        success_rate = 0
        if self.service_statistics['total_generations'] > 0:
            success_rate = (
                self.service_statistics['successful_generations'] / 
                self.service_statistics['total_generations']
            ) * 100
        
        return {
            'service_name': 'Generation Service',
            'status': 'active',
            'uptime_seconds': int(uptime.total_seconds()),
            'statistics': {
                'total_generations': self.service_statistics['total_generations'],
                'successful_generations': self.service_statistics['successful_generations'],
                'success_rate_percent': round(success_rate, 1),
                'total_buildings_processed': self.service_statistics['total_buildings_processed'],
                'total_observations_created': self.service_statistics['total_observations_created']
            }
        }
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques détaillées du service
        
        Returns:
            Dict: Statistiques complètes
        """
        return self.service_statistics.copy()


# ==============================================================================
# FONCTIONS UTILITAIRES DU SERVICE
# ==============================================================================

def calculate_generation_complexity(
    num_buildings: int,
    date_range_days: int,
    frequency_minutes: int
) -> str:
    """
    Calcule le niveau de complexité d'une génération
    
    Args:
        num_buildings: Nombre de bâtiments
        date_range_days: Nombre de jours
        frequency_minutes: Fréquence en minutes
        
    Returns:
        str: Niveau de complexité
    """
    points_per_day = (24 * 60) / frequency_minutes
    total_points = num_buildings * date_range_days * points_per_day
    
    if total_points < 10000:
        return 'simple'
    elif total_points < 100000:
        return 'modéré'
    elif total_points < 1000000:
        return 'complexe'
    else:
        return 'très_complexe'


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du service de génération
    from src.core.generator import ElectricityDataGenerator
    
    # Initialisation
    generator = ElectricityDataGenerator()
    generation_service = GenerationService(generator)
    
    # Données OSM de test
    test_osm_buildings = [
        {
            'osm_id': '12345',
            'latitude': 3.15,
            'longitude': 101.7,
            'building_type': 'residential',
            'tags': {'building': 'residential'}
        },
        {
            'osm_id': '12346',
            'latitude': 3.16,
            'longitude': 101.71,
            'building_type': 'commercial',
            'tags': {'building': 'commercial'}
        }
    ]
    
    # Test de génération
    result = generation_service.generate_complete_dataset(
        zone_name='test_zone',
        buildings_osm=test_osm_buildings,
        start_date='2024-01-01',
        end_date='2024-01-02',
        frequency='1H'
    )
    
    if result['success']:
        print(f"✅ Génération test réussie:")
        print(f"📊 {result['statistics']['total_buildings']} bâtiments")
        print(f"⏰ {result['statistics']['total_observations']} observations")
        print(f"🎯 Score qualité: {result['statistics']['quality_metrics']['overall_score']}")
    else:
        print(f"❌ Génération échouée: {result['error']}")
    
    # Statut du service
    status = generation_service.get_service_status()
    print(f"📈 Service: {status['statistics']['success_rate_percent']}% succès")