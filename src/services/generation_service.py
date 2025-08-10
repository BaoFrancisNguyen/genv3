"""
Service de Génération - Couche métier pour la génération de données électriques
==============================================================================

Ce service orchestre la génération complète des données électriques
en coordonnant les différents composants et en ajoutant la logique métier.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from src.core.generator import ElectricityDataGenerator, validate_generation_parameters, estimate_generation_time
from src.models.building import Building, validate_building_list
from src.models.timeseries import TimeSeries, timeseries_to_dataframe, validate_timeseries_data


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
                return {
                    'success': False,
                    'error': 'Paramètres invalides',
                    'validation_errors': validation_result['errors']
                }
            
            # Phase 2: Conversion des bâtiments OSM en objets Building
            buildings_conversion = self._convert_osm_to_buildings(buildings_osm, zone_name)
            
            if not buildings_conversion['success']:
                return buildings_conversion
            
            buildings = buildings_conversion['buildings']
            self.service_statistics['total_buildings_processed'] += len(buildings)
            
            # Phase 3: Génération des métadonnées de bâtiments
            buildings_df = self.generator.generate_building_metadata(buildings)
            
            # Phase 4: Génération des séries temporelles
            timeseries_df = self.generator.generate_timeseries_for_buildings(
                buildings, start_date, end_date, frequency
            )
            
            self.service_statistics['total_observations_created'] += len(timeseries_df)
            
            # Phase 5: Validation et nettoyage des données générées
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
            logger.error(f"❌ Erreur génération dataset: {str(e)}")
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
        elif len(buildings_osm) > 10000:
            errors.append("Trop de bâtiments (max 10000)")
        elif len(buildings_osm) > 5000:
            warnings.append("Grand nombre de bâtiments - génération longue")
        
        # Validation des paramètres temporels
        params_valid, param_errors = validate_generation_parameters(
            start_date, end_date, frequency, len(buildings_osm)
        )
        
        if not params_valid:
            errors.extend(param_errors)
        
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
                if 0.5 <= float(lat) <= 7.5 and 99.0 <= float(lon) <= 120.0:
                    quality_metrics['has_valid_coordinates'] += 1
                else:
                    warnings.append(f"Bâtiment {i}: coordonnées hors Malaysia")
            else:
                warnings.append(f"Bâtiment {i}: coordonnées manquantes")
            
            # Vérification type de bâtiment
            building_type = building_data.get('building_type') or building_data.get('type')
            if building_type and building_type != 'yes':
                quality_metrics['has_building_type'] += 1
            
            # Vérification ID OSM
            osm_id = building_data.get('osm_id') or building_data.get('id')
            if osm_id:
                quality_metrics['has_osm_id'] += 1
        
        # Calcul du score de qualité
        total = len(buildings_osm)
        quality_score = (
            (quality_metrics['has_valid_coordinates'] / total) * 40 +
            (quality_metrics['has_building_type'] / total) * 30 +
            (quality_metrics['has_osm_id'] / total) * 20 +
            (quality_metrics['has_coordinates'] / total) * 10
        )
        
        # Détection d'erreurs critiques
        if quality_metrics['has_coordinates'] == 0:
            critical_errors.append("Aucun bâtiment avec coordonnées")
        
        if quality_metrics['has_valid_coordinates'] / total < 0.5:
            critical_errors.append("Moins de 50% des coordonnées sont valides")
        
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
            buildings_osm: Données OSM brutes
            zone_name: Nom de la zone
            
        Returns:
            Dict: Résultats de conversion
        """
        try:
            buildings = []
            conversion_stats = {
                'attempted': len(buildings_osm),
                'successful': 0,
                'failed': 0,
                'warnings': []
            }
            
            for i, osm_data in enumerate(buildings_osm):
                try:
                    # Normalisation des données OSM
                    normalized_data = self._normalize_osm_data(osm_data)
                    
                    # Création du bâtiment
                    building = Building.from_osm_data(normalized_data, zone_name)
                    buildings.append(building)
                    conversion_stats['successful'] += 1
                    
                except Exception as e:
                    conversion_stats['failed'] += 1
                    conversion_stats['warnings'].append(
                        f"Bâtiment {i}: conversion échouée ({str(e)})"
                    )
                    logger.warning(f"⚠️ Conversion échouée bâtiment {i}: {str(e)}")
            
            # Validation des bâtiments créés
            valid_buildings, validation_errors = validate_building_list(buildings)
            
            if validation_errors:
                conversion_stats['warnings'].extend(validation_errors)
            
            logger.info(f"🏗️ Conversion OSM: {len(valid_buildings)}/{len(buildings_osm)} réussies")
            
            return {
                'success': True,
                'buildings': valid_buildings,
                'conversion_info': conversion_stats
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur conversion OSM: {str(e)}")
            return {
                'success': False,
                'error': f"Erreur conversion: {str(e)}",
                'buildings': []
            }
    
    def _normalize_osm_data(self, osm_data: Dict) -> Dict:
        """
        Normalise les données OSM pour la création de Building
        
        Args:
            osm_data: Données OSM brutes
            
        Returns:
            Dict: Données normalisées
        """
        # Mapping des champs alternatifs
        normalized = {
            'id': osm_data.get('osm_id') or osm_data.get('id'),
            'lat': osm_data.get('latitude') or osm_data.get('lat'),
            'lon': osm_data.get('longitude') or osm_data.get('lon'),
            'tags': osm_data.get('tags', {}),
            'geometry': osm_data.get('geometry', [])
        }
        
        # Normalisation du type de bâtiment
        building_type = (
            osm_data.get('building_type') or 
            osm_data.get('type') or 
            normalized['tags'].get('building', 'residential')
        )
        
        if building_type == 'yes':
            building_type = 'residential'
        
        normalized['tags']['building'] = building_type
        
        # Normalisation de la géométrie
        if not normalized['geometry'] and normalized['lat'] and normalized['lon']:
            normalized['geometry'] = [{'lat': normalized['lat'], 'lon': normalized['lon']}]
        
        return normalized
    
    def _perform_quality_check(self, buildings_df: pd.DataFrame, timeseries_df: pd.DataFrame) -> Dict:
        """
        Effectue un contrôle qualité des données générées
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Métriques de qualité
        """
        quality_metrics = {
            'buildings_quality': {},
            'timeseries_quality': {},
            'overall_score': 0
        }
        
        # Qualité des bâtiments
        if not buildings_df.empty:
            buildings_quality = {
                'total_buildings': len(buildings_df),
                'complete_coordinates': (buildings_df[['latitude', 'longitude']].notna().all(axis=1)).sum(),
                'valid_types': (buildings_df['building_type'] != 'unknown').sum(),
                'positive_consumption': (buildings_df['base_consumption_kwh'] > 0).sum()
            }
            
            buildings_score = (
                (buildings_quality['complete_coordinates'] / buildings_quality['total_buildings']) * 40 +
                (buildings_quality['valid_types'] / buildings_quality['total_buildings']) * 35 +
                (buildings_quality['positive_consumption'] / buildings_quality['total_buildings']) * 25
            )
            
            quality_metrics['buildings_quality'] = {
                **buildings_quality,
                'score': round(buildings_score, 1)
            }
        
        # Qualité des séries temporelles
        if not timeseries_df.empty:
            timeseries_quality = {
                'total_observations': len(timeseries_df),
                'positive_consumption': (timeseries_df['consumption_kwh'] > 0).sum(),
                'realistic_temperature': ((timeseries_df['temperature_c'] >= 20) & 
                                        (timeseries_df['temperature_c'] <= 45)).sum(),
                'valid_humidity': ((timeseries_df['humidity'] >= 0.3) & 
                                 (timeseries_df['humidity'] <= 1.0)).sum()
            }
            
            timeseries_score = (
                (timeseries_quality['positive_consumption'] / timeseries_quality['total_observations']) * 50 +
                (timeseries_quality['realistic_temperature'] / timeseries_quality['total_observations']) * 25 +
                (timeseries_quality['valid_humidity'] / timeseries_quality['total_observations']) * 25
            )
            
            quality_metrics['timeseries_quality'] = {
                **timeseries_quality,
                'score': round(timeseries_score, 1)
            }
        
        # Score global
        building_score = quality_metrics['buildings_quality'].get('score', 0)
        timeseries_score = quality_metrics['timeseries_quality'].get('score', 0)
        quality_metrics['overall_score'] = round((building_score + timeseries_score) / 2, 1)
        
        return quality_metrics
    
    def estimate_generation_resources(
        self,
        num_buildings: int,
        start_date: str,
        end_date: str,
        frequency: str
    ) -> Dict:
        """
        Estime les ressources nécessaires pour une génération
        
        Args:
            num_buildings: Nombre de bâtiments
            start_date: Date de début
            end_date: Date de fin
            frequency: Fréquence
            
        Returns:
            Dict: Estimations détaillées
        """
        try:
            # Estimation de base via le générateur
            base_estimation = estimate_generation_time(
                num_buildings, start_date, end_date, frequency
            )
            
            # Enrichissement avec logique métier
            enhanced_estimation = base_estimation.copy()
            
            # Facteurs d'ajustement selon la complexité
            if num_buildings > 1000:
                enhanced_estimation['memory_usage_mb'] = num_buildings * 0.5
                enhanced_estimation['recommended_ram_gb'] = max(4, num_buildings / 2000)
            else:
                enhanced_estimation['memory_usage_mb'] = 50
                enhanced_estimation['recommended_ram_gb'] = 2
            
            # Recommandations de performance
            recommendations = []
            
            if enhanced_estimation.get('total_data_points', 0) > 100000:
                recommendations.append("Génération en plusieurs étapes recommandée")
            
            if enhanced_estimation.get('estimated_duration_seconds', 0) > 300:
                recommendations.append("Prévoir 5+ minutes - ne pas fermer le navigateur")
            
            enhanced_estimation['performance_recommendations'] = recommendations
            
            return {
                'success': True,
                'estimation': enhanced_estimation
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur estimation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_service_status(self) -> Dict:
        """
        Retourne l'état du service de génération
        
        Returns:
            Dict: État détaillé du service
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


def optimize_generation_parameters(
    num_buildings: int,
    start_date: str,
    end_date: str,
    frequency: str
) -> Dict:
    """
    Optimise les paramètres de génération selon les contraintes
    
    Args:
        num_buildings: Nombre de bâtiments
        start_date: Date de début
        end_date: Date de fin
        frequency: Fréquence
        
    Returns:
        Dict: Paramètres optimisés et suggestions
    """
    suggestions = {
        'optimized_frequency': frequency,
        'batch_size': num_buildings,
        'recommendations': []
    }
    
    # Calcul de la complexité
    date_range = pd.to_datetime(end_date) - pd.to_datetime(start_date)
    days = date_range.days
    
    freq_minutes = {'15T': 15, '30T': 30, '1H': 60, '3H': 180, 'D': 1440}.get(frequency, 30)
    complexity = calculate_generation_complexity(num_buildings, days, freq_minutes)
    
    # Optimisations selon la complexité
    if complexity == 'très_complexe':
        if freq_minutes < 60:
            suggestions['optimized_frequency'] = '1H'
            suggestions['recommendations'].append("Fréquence réduite pour améliorer les performances")
        
        if num_buildings > 5000:
            suggestions['batch_size'] = 2500
            suggestions['recommendations'].append("Traitement par lots recommandé")
    
    elif complexity == 'complexe':
        if num_buildings > 3000:
            suggestions['batch_size'] = 1500
            suggestions['recommendations'].append("Traitement en lots pour optimiser")
    
    return suggestions


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
