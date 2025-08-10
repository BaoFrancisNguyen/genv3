"""
Générateur de données électriques pour Malaysia - VERSION CORRIGÉE
=================================================================

Générateur complet avec patterns officiels Malaysia :
✅ Patterns climatiques tropicaux
✅ Facteurs saisonniers Malaysia  
✅ Patterns hebdomadaires
✅ Facteurs Ramadan
✅ Consommations conformes aux spécifications

Version: 3.0 - Patterns Malaysia officiels
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
import random

# Configuration du logger
logger = logging.getLogger(__name__)


class ElectricityDataGenerator:
    """
    Générateur de données électriques réalistes pour Malaysia
    
    Utilise les patterns officiels de consommation électrique
    selon les spécifications climatiques et culturelles Malaysia.
    """
    
    def __init__(self):
        """Initialise le générateur avec les statistiques"""
        self.generation_stats = {
            'total_buildings_generated': 0,
            'total_timeseries_generated': 0,
            'generation_start_time': datetime.now()
        }
        
        logger.info("✅ Générateur électrique Malaysia initialisé")
    
    def generate_timeseries_data(
        self, 
        buildings: List[Dict], 
        start_date: str, 
        end_date: str, 
        frequency: str = '1H'
    ) -> Dict:
        """
        Génère des données de consommation électrique pour les bâtiments
        
        Args:
            buildings: Liste des bâtiments OSM
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD) 
            frequency: Fréquence d'échantillonnage ('15T', '30T', '1H', '3H', 'D')
            
        Returns:
            Dict: Résultat avec données générées et métadonnées
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"⚡ Génération données électriques pour {len(buildings)} bâtiments")
            logger.info(f"📅 Période: {start_date} → {end_date} (fréquence: {frequency})")
            
            # Créer l'index temporel
            date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
            logger.info(f"📊 {len(date_range)} points temporels à générer")
            
            # Générer les données pour chaque bâtiment
            all_data = []
            
            for i, building in enumerate(buildings):
                if i % 10000 == 0 and i > 0:
                    logger.info(f"📈 Progression: {i}/{len(buildings)} bâtiments traités")
                
                building_data = self._generate_building_timeseries(building, date_range)
                all_data.extend(building_data)
            
            # Créer le DataFrame final
            df = pd.DataFrame(all_data)
            
            # Métadonnées de génération
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Mise à jour des statistiques
            self.generation_stats['total_buildings_generated'] += len(buildings)
            self.generation_stats['total_timeseries_generated'] += len(all_data)
            
            logger.info(f"✅ Génération terminée en {generation_time:.1f}s")
            logger.info(f"📋 {len(all_data)} points de données générés")
            
            return {
                'success': True,
                'data': df,
                'metadata': {
                    'total_points': len(all_data),
                    'buildings_count': len(buildings),
                    'date_range': {
                        'start': start_date,
                        'end': end_date,
                        'frequency': frequency,
                        'total_periods': len(date_range)
                    },
                    'generation_time_seconds': generation_time,
                    'patterns_used': 'Malaysia Official Specifications',
                    'climate_factors': 'Tropical Malaysia',
                    'cultural_factors': 'Ramadan, Friday prayers, Weekend patterns'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur génération: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _estimate_base_consumption(self, building_type: str, surface_area: float) -> float:
        """
        Estime la consommation de base selon les spécifications Malaysia officielles
        
        SPÉCIFICATIONS OFFICIELLES (kWh/heure base pour 100m²):
        - Residential: 0.5 kWh (base) → 12.0 kWh (pic)
        - Commercial: 5.0 kWh (base) → 80.0 kWh (pic)
        - Industrial: 20.0 kWh (base) → 200.0 kWh (pic)
        - Office: 3.0 kWh (base) → 45.0 kWh (pic)
        - Hospital: 25.0 kWh (base) → 70.0 kWh (pic)
        - School: 1.0 kWh (base) → 25.0 kWh (pic)
        - Hotel: 8.0 kWh (base) → 40.0 kWh (pic)
        """
        # Spécifications officielles Malaysia
        specs = {
            'residential': {'base': 0.5, 'peak': 12.0, 'night': 0.3},
            'commercial': {'base': 5.0, 'peak': 80.0, 'night': 0.2},
            'industrial': {'base': 20.0, 'peak': 200.0, 'night': 0.7},
            'office': {'base': 3.0, 'peak': 45.0, 'night': 0.1},
            'hospital': {'base': 25.0, 'peak': 70.0, 'night': 0.8},
            'school': {'base': 1.0, 'peak': 25.0, 'night': 0.05},
            'hotel': {'base': 8.0, 'peak': 40.0, 'night': 0.6},
            'public': {'base': 3.0, 'peak': 45.0, 'night': 0.1},
            'religious': {'base': 1.0, 'peak': 15.0, 'night': 0.05}
        }
        
        building_spec = specs.get(building_type, specs['residential'])
        base_unit_consumption = building_spec['base']  # kWh/heure pour 100m²
        
        # Facteur de surface (référence 100m²)
        surface_factor = surface_area / 100.0
        surface_factor = max(0.1, min(surface_factor, 10.0))  # Limiter 10m² à 1000m²
        
        # Consommation de base finale (kWh/heure)
        base_consumption = base_unit_consumption * surface_factor
        
        return max(0.1, min(base_consumption, 500.0))  # Limites de sécurité
    
    def _get_hourly_factor(self, hour: int, building_type: str) -> float:
        """
        Facteurs horaires selon le climat tropical Malaysia
        
        PATTERNS CLIMATIQUES TROPICAUX:
        - 6h-8h : Pic matinal (avant la chaleur)
        - 11h-16h : Maximum de climatisation (heures les plus chaudes)
        - 17h-21h : Activité élevée (après-midi/soirée)
        - 22h-5h : Consommation nocturne réduite
        """
        # Facteurs nocturnes par type (selon spécifications)
        night_factors = {
            'residential': 0.3, 'commercial': 0.2, 'industrial': 0.7,
            'office': 0.1, 'hospital': 0.8, 'school': 0.05,
            'hotel': 0.6, 'public': 0.1, 'religious': 0.05
        }
        
        night_factor = night_factors.get(building_type, 0.3)
        
        if building_type == 'residential':
            if 6 <= hour <= 8:  # Pic matinal (avant chaleur)
                return 1.4
            elif 11 <= hour <= 16:  # Maximum climatisation
                return 2.0  # Vers peak (12.0 kWh)
            elif 17 <= hour <= 21:  # Activité élevée soirée
                return 1.6
            elif 22 <= hour <= 23 or 0 <= hour <= 5:  # Nuit
                return night_factor  # 0.3
            else:
                return 1.0
                
        elif building_type == 'commercial':
            if 9 <= hour <= 21:  # Heures d'ouverture
                if 11 <= hour <= 16:  # Pic climatisation
                    return 2.5  # Vers peak (80.0 kWh)
                else:
                    return 1.8
            else:  # Fermé
                return night_factor  # 0.2
                
        elif building_type == 'office':
            if 8 <= hour <= 18:  # Heures de bureau
                if 11 <= hour <= 16:  # Pic climatisation
                    return 3.0  # Vers peak (45.0 kWh)
                else:
                    return 2.0
            else:  # Fermé
                return night_factor  # 0.1
                
        elif building_type == 'school':
            if 7 <= hour <= 15:  # Heures scolaires
                if 11 <= hour <= 14:  # Pic climatisation
                    return 5.0  # Vers peak (25.0 kWh)
                else:
                    return 3.0
            else:  # École fermée
                return night_factor  # 0.05
                
        elif building_type == 'hospital':
            if 11 <= hour <= 16:  # Pic climatisation
                return 1.8  # Vers peak (70.0 kWh)
            elif 6 <= hour <= 22:  # Activité diurne
                return 1.4
            else:  # Nuit (mais activité 24h/24)
                return night_factor  # 0.8 (élevé pour hôpital)
                
        elif building_type == 'industrial':
            if 11 <= hour <= 16:  # Pic climatisation
                return 2.0  # Vers peak (200.0 kWh)
            elif 6 <= hour <= 22:  # Heures de production
                return 1.5
            else:  # Nuit
                return night_factor  # 0.7
                
        elif building_type in ['hotel', 'public']:
            if building_type == 'hotel':
                if 11 <= hour <= 16:  # Pic climatisation
                    return 1.8  # Vers peak (40.0 kWh)
                elif 6 <= hour <= 23:  # Activité hôtelière
                    return 1.3
                else:
                    return night_factor  # 0.6
            else:  # public
                if 8 <= hour <= 17:  # Heures d'ouverture
                    if 11 <= hour <= 16:
                        return 3.0
                    else:
                        return 2.0
                else:
                    return night_factor  # 0.1
        
        return 1.0
    
    def _get_seasonal_factor(self, month: int) -> float:
        """
        Facteurs saisonniers Malaysia selon le document officiel
        
        FACTEURS SAISONNIERS:
        - Nov-Fév: Mousson NE (0.9-1.1×) - Moins de climatisation
        - Mar-Avr: Transition (1.2-1.5×) - Période chaude + Ramadan
        - Mai-Août: Saison sèche (1.3-1.7×) - Maximum de climatisation
        - Sep-Oct: Variable (1.0-1.3×) - Climat changeant
        """
        seasonal_factors = {
            # Mousson NE - Moins de climatisation
            11: 0.95, 12: 0.9, 1: 0.9, 2: 1.0,
            
            # Transition - Période chaude + Ramadan
            3: 1.3, 4: 1.4,
            
            # Saison sèche - Maximum de climatisation
            5: 1.5, 6: 1.6, 7: 1.7, 8: 1.6,
            
            # Variable - Climat changeant
            9: 1.2, 10: 1.1
        }
        
        return seasonal_factors.get(month, 1.0)
    
    def _get_daily_factor(self, weekday: int, building_type: str) -> float:
        """
        Facteurs hebdomadaires Malaysia
        
        PATTERNS HEBDOMADAIRES:
        - Vendredi après-midi : Réduction d'activité (prière du vendredi)
        - Weekend : Plus de consommation résidentielle
        - Jours ouvrables : Pics dans les bureaux/commerces
        
        Args:
            weekday: 0=Lundi, 4=Vendredi, 5=Samedi, 6=Dimanche
        """
        is_weekend = weekday >= 5  # Samedi-Dimanche
        
        if building_type == 'residential':
            return 1.2 if is_weekend else 1.0  # Plus de consommation week-end
            
        elif building_type in ['office', 'commercial']:
            if is_weekend:
                return 0.4  # Bureaux/commerces fermés
            else:
                return 1.0
                
        elif building_type == 'school':
            return 0.05 if is_weekend else 1.0  # École fermée week-end
            
        elif building_type in ['hospital', 'hotel']:
            return 1.0  # Pas d'impact majeur
            
        elif building_type == 'industrial':
            return 0.7 if is_weekend else 1.0  # Production réduite week-end
            
        else:
            return 1.0
    
    def _get_ramadan_factor(self, month: int, hour: int, building_type: str) -> float:
        """
        Facteurs Ramadan Malaysia (Mar-Avr approximatif)
        
        PÉRIODE DE RAMADAN:
        - 4h-17h : Consommation réduite de 40% (jeûne)
        - 18h-23h : Consommation augmentée de 40% (Iftar, activités nocturnes)
        """
        # Ramadan approximatif en Mars-Avril
        if month not in [3, 4]:
            return 1.0
            
        if building_type in ['residential', 'commercial']:
            if 4 <= hour <= 17:  # Période de jeûne
                return 0.6  # Réduction de 40%
            elif 18 <= hour <= 23:  # Iftar et activités nocturnes
                return 1.4  # Augmentation de 40%
            else:
                return 1.0
        else:
            return 1.0  # Hôpitaux, industriel moins affectés
    
    def _get_friday_prayer_factor(self, weekday: int, hour: int, building_type: str) -> float:
        """
        Facteur spécial pour la prière du vendredi
        
        VENDREDI APRÈS-MIDI:
        - Réduction d'activité (prière du vendredi) 12h-15h
        """
        if weekday == 4 and 12 <= hour <= 15:  # Vendredi 12h-15h
            if building_type in ['office', 'commercial']:
                return 0.6  # Réduction pour prière
        return 1.0
    
    def _generate_building_timeseries(self, building: Dict, date_range: pd.DatetimeIndex) -> List[Dict]:
        """
        Génère la série temporelle avec TOUS les patterns Malaysia
        
        Args:
            building: Données du bâtiment OSM
            date_range: Plage temporelle pandas
            
        Returns:
            List[Dict]: Points de données avec patterns Malaysia complets
        """
        building_id = building['id']
        building_type = building['building_type']
        surface_area = building.get('surface_area_m2', 100)
        
        # Consommation de base (kWh/heure) selon spécifications Malaysia
        base_consumption_hourly = self._estimate_base_consumption(building_type, surface_area)
        
        data_points = []
        
        for timestamp in date_range:
            # 1. Facteur horaire tropical Malaysia
            hour_factor = self._get_hourly_factor(timestamp.hour, building_type)
            
            # 2. Facteur hebdomadaire Malaysia
            day_factor = self._get_daily_factor(timestamp.weekday(), building_type)
            
            # 3. Facteur saisonnier Malaysia
            seasonal_factor = self._get_seasonal_factor(timestamp.month)
            
            # 4. Facteur Ramadan Malaysia
            ramadan_factor = self._get_ramadan_factor(timestamp.month, timestamp.hour, building_type)
            
            # 5. Facteur prière du vendredi
            friday_factor = self._get_friday_prayer_factor(timestamp.weekday(), timestamp.hour, building_type)
            
            # 6. Variation aléatoire réaliste
            random_factor = np.random.normal(1.0, 0.05)  # ±5% seulement
            random_factor = max(0.8, min(random_factor, 1.2))  # Limiter ±20%
            
            # 7. Calcul de la durée de l'intervalle
            if len(date_range) > 1:
                interval_hours = (date_range[1] - date_range[0]).total_seconds() / 3600
            else:
                interval_hours = 1.0
            
            # 8. CALCUL FINAL avec tous les patterns Malaysia
            consumption = (base_consumption_hourly *      # Base kWh/h (specs Malaysia)
                          hour_factor *                   # Pattern tropical
                          day_factor *                    # Pattern hebdomadaire
                          seasonal_factor *               # Pattern saisonnier
                          ramadan_factor *                # Pattern Ramadan
                          friday_factor *                 # Pattern vendredi
                          random_factor *                 # Variation réaliste
                          interval_hours)                 # Durée de l'intervalle
            
            # 9. Limites de sécurité
            consumption = max(0.001, consumption)  # Minimum technique
            
            # 10. Debug pour les premiers points
            if len(data_points) < 3:
                logger.info(f"🔍 Point {len(data_points)+1} - {building_type} {surface_area}m²:")
                logger.info(f"   Base: {base_consumption_hourly:.3f} kWh/h")
                logger.info(f"   Facteurs: hour={hour_factor:.2f}, day={day_factor:.2f}, season={seasonal_factor:.2f}")
                logger.info(f"   Ramadan={ramadan_factor:.2f}, vendredi={friday_factor:.2f}, random={random_factor:.2f}")
                logger.info(f"   Intervalle: {interval_hours:.2f}h")
                logger.info(f"   Final: {consumption:.4f} kWh")
            
            data_points.append({
                'building_id': building_id,
                'timestamp': timestamp,
                'consumption_kwh': round(consumption, 4),
                'building_type': building_type,
                'latitude': building['latitude'],
                'longitude': building['longitude'],
                'zone_name': building['zone_name']
            })
        
        return data_points
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques du générateur
        
        Returns:
            Dict: Statistiques de génération complètes
        """
        uptime = datetime.now() - self.generation_stats['generation_start_time']
        
        return {
            'total_buildings_generated': self.generation_stats['total_buildings_generated'],
            'total_timeseries_generated': self.generation_stats['total_timeseries_generated'],
            'uptime_seconds': int(uptime.total_seconds()),
            'generation_rate_buildings_per_second': round(
                self.generation_stats['total_buildings_generated'] / max(uptime.total_seconds(), 1), 2
            ),
            'generation_rate_observations_per_second': round(
                self.generation_stats['total_timeseries_generated'] / max(uptime.total_seconds(), 1), 2
            ),
            'patterns_implemented': [
                'Malaysia Tropical Climate',
                'Seasonal Variations (Monsoon/Dry)',
                'Weekly Patterns (Weekend/Weekday)',
                'Ramadan Adjustments',
                'Friday Prayer Reductions',
                'Building Type Specific Profiles'
            ]
        }


# ==============================================================================
# FONCTIONS UTILITAIRES DE VALIDATION
# ==============================================================================

def validate_generation_parameters(
    start_date: str, 
    end_date: str, 
    frequency: str, 
    num_buildings: int
) -> Tuple[bool, List[str]]:
    """
    Valide les paramètres de génération
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        frequency: Fréquence d'échantillonnage
        num_buildings: Nombre de bâtiments
        
    Returns:
        Tuple[bool, List[str]]: Validité et liste d'erreurs
    """
    errors = []
    
    # Validation des dates
    try:
        if not start_date or not end_date:
            errors.append("Dates de début et fin requises")
            return False, errors
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        if start >= end:
            errors.append("Date de fin doit être après date de début")
        
        # Limite de période maximale
        if (end - start).days > 365:
            errors.append("Période maximale autorisée: 365 jours")
            
    except (ValueError, TypeError) as e:
        errors.append(f"Format de dates invalide (utiliser YYYY-MM-DD): {str(e)}")
    
    # Validation de la fréquence
    valid_frequencies = ['15T', '30T', '1H', '3H', 'D']
    
    if not frequency:
        errors.append("Fréquence requise")
    elif frequency not in valid_frequencies:
        errors.append(f"Fréquences supportées: {valid_frequencies}")
    
    # Validation du nombre de bâtiments (LIMITES AUGMENTÉES)
    try:
        num_buildings = int(num_buildings)
        if not (1 <= num_buildings <= 1000000):  # 1 million max
            errors.append("Nombre de bâtiments doit être entre 1 et 1,000,000")
    except (ValueError, TypeError):
        errors.append("Nombre de bâtiments doit être un entier")
    
    # Validation de la charge de travail
    try:
        if len(errors) == 0:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            # Calcul du nombre d'observations
            freq_minutes = {'15T': 15, '30T': 30, '1H': 60, '3H': 180, 'D': 1440}
            
            if frequency in freq_minutes:
                total_minutes = (end - start).total_seconds() / 60
                observations_per_building = total_minutes / freq_minutes[frequency]
                total_observations = num_buildings * observations_per_building
                
                # Limite technique: 100 millions de points
                if total_observations > 100_000_000:
                    errors.append(f"Trop d'observations estimées ({int(total_observations):,}). Réduisez la période ou le nombre de bâtiments.")
    
    except Exception as e:
        errors.append(f"Erreur de validation: {str(e)}")
    
    return len(errors) == 0, errors


def estimate_generation_time(
    num_buildings: int, 
    start_date: str, 
    end_date: str, 
    frequency: str
) -> Dict:
    """
    Estime le temps et les ressources de génération
    
    Args:
        num_buildings: Nombre de bâtiments
        start_date: Date de début
        end_date: Date de fin
        frequency: Fréquence
        
    Returns:
        Dict: Estimation détaillée
    """
    try:
        # Calcul du nombre d'observations
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start, end=end, freq=frequency)
        
        total_observations = num_buildings * len(date_range)
        
        # Estimation du temps (calibré selon les performances Malaysia)
        observations_per_second = 15000  # Optimisé
        estimated_time_seconds = total_observations / observations_per_second
        
        # Estimation de la taille
        bytes_per_observation = 150  # Avec métadonnées
        estimated_size_mb = (total_observations * bytes_per_observation) / (1024 * 1024)
        
        # Niveau de complexité
        if total_observations < 100000:
            complexity = 'simple'
            recommendation = 'Génération rapide (< 1 minute)'
        elif total_observations < 1000000:
            complexity = 'modéré'
            recommendation = 'Génération standard (1-5 minutes)'
        elif total_observations < 10000000:
            complexity = 'complexe'
            recommendation = 'Génération longue (5-30 minutes)'
        else:
            complexity = 'très_complexe'
            recommendation = 'Génération très longue (> 30 minutes)'
        
        return {
            'total_observations': int(total_observations),
            'estimated_time_seconds': round(estimated_time_seconds, 1),
            'estimated_time_minutes': round(estimated_time_seconds / 60, 1),
            'estimated_size_mb': round(estimated_size_mb, 1),
            'complexity': complexity,
            'recommendation': recommendation,
            'buildings_count': num_buildings,
            'time_periods': len(date_range)
        }
        
    except Exception as e:
        return {
            'error': f'Erreur estimation: {str(e)}',
            'total_observations': 0
        }


# ==============================================================================
# EXEMPLE D'UTILISATION ET TESTS
# ==============================================================================

if __name__ == '__main__':
    # Test du générateur Malaysia
    generator = ElectricityDataGenerator()
    
    print("🇲🇾 TEST GÉNÉRATEUR MALAYSIA")
    print("=" * 50)
    
    # Test avec bâtiment exemple
    test_buildings = [
        {
            'id': 'test_residential',
            'building_type': 'residential',
            'surface_area_m2': 150,
            'latitude': 4.576,
            'longitude': 101.112,
            'zone_name': 'Ipoh'
        }
    ]
    
    # Test validation
    is_valid, errors = validate_generation_parameters(
        '2024-01-25', '2024-01-26', '30T', 1
    )
    print(f"Validation: {'✅' if is_valid else '❌'} {errors}")
    
    # Test estimation
    estimation = estimate_generation_time(1, '2024-01-25', '2024-01-26', '30T')
    print(f"Estimation: {estimation['total_observations']} observations, {estimation['estimated_time_seconds']}s")
    
    # Test génération
    result = generator.generate_timeseries_data(
        test_buildings, '2024-01-25', '2024-01-25', '30T'
    )
    
    if result['success']:
        df = result['data']
        print(f"✅ Génération réussie: {len(df)} points")
        print(f"📊 Exemple: {df.iloc[0]['consumption_kwh']:.4f} kWh")
        print(f"📈 Plage: {df['consumption_kwh'].min():.4f} - {df['consumption_kwh'].max():.4f} kWh")
    else:
        print(f"❌ Erreur: {result['error']}")
    
    # Statistiques
    stats = generator.get_statistics()
    print(f"📊 Statistiques: {stats['total_buildings_generated']} bâtiments générés")
    
    print("✅ Tests terminés - Générateur Malaysia prêt!")