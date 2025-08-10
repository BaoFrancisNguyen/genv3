"""
Générateur de données électriques pour Malaysia
==============================================

Ce module génère des données de consommation électrique réalistes
pour les bâtiments de Malaysia en tenant compte du climat tropical.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

from src.models.building import Building
from config import GenerationConfig as GEN_CONFIG


# Configuration du logger
logger = logging.getLogger(__name__)


class ElectricityDataGenerator:
    """
    Générateur principal de données électriques pour Malaysia
    
    Génère des séries temporelles de consommation électrique réalistes
    en tenant compte des spécificités climatiques et culturelles de Malaysia.
    """
    
    def __init__(self):
        """Initialise le générateur avec les paramètres Malaysia"""
        self.generation_stats = {
            'total_buildings_generated': 0,
            'total_timeseries_generated': 0,
            'generation_start_time': datetime.now()
        }
        
        # Profils de consommation par type de bâtiment (Malaysia)
        self.consumption_profiles = {
            'residential': {
                'base_factor': 1.0,
                'peak_hours': [19, 20, 21],  # Soirée
                'peak_multiplier': 1.8,
                'night_factor': 0.4,
                'ac_dependency': 0.7  # Forte dépendance climatisation
            },
            'commercial': {
                'base_factor': 1.2,
                'peak_hours': [10, 11, 14, 15, 16],  # Heures d'activité
                'peak_multiplier': 2.2,
                'night_factor': 0.2,
                'ac_dependency': 0.8
            },
            'office': {
                'base_factor': 1.1,
                'peak_hours': [9, 10, 11, 14, 15, 16],  # Heures de bureau
                'peak_multiplier': 2.0,
                'night_factor': 0.1,
                'ac_dependency': 0.9
            },
            'industrial': {
                'base_factor': 2.5,
                'peak_hours': [8, 9, 10, 13, 14, 15],  # Heures production
                'peak_multiplier': 1.4,
                'night_factor': 0.6,
                'ac_dependency': 0.5
            },
            'hospital': {
                'base_factor': 2.0,
                'peak_hours': list(range(24)),  # 24h/24
                'peak_multiplier': 1.2,
                'night_factor': 0.8,
                'ac_dependency': 0.95
            },
            'school': {
                'base_factor': 0.8,
                'peak_hours': [8, 9, 10, 11, 14, 15],  # Heures scolaires
                'peak_multiplier': 1.6,
                'night_factor': 0.05,
                'ac_dependency': 0.6
            },
            'hotel': {
                'base_factor': 1.5,
                'peak_hours': [7, 8, 19, 20, 21, 22],  # Check-in/out + soirée
                'peak_multiplier': 1.7,
                'night_factor': 0.6,
                'ac_dependency': 0.85
            }
        }
        
        logger.info("✅ Générateur électrique Malaysia initialisé")
    
    def generate_building_metadata(self, buildings: List[Building]) -> pd.DataFrame:
        """
        Génère les métadonnées enrichies pour une liste de bâtiments
        
        Args:
            buildings: Liste des bâtiments
            
        Returns:
            pd.DataFrame: Métadonnées enrichies
        """
        logger.info(f"📋 Génération métadonnées pour {len(buildings)} bâtiments")
        
        building_data = []
        
        for building in buildings:
            # Enrichissement avec des données Malaysia-spécifiques
            metadata = {
                'building_id': building.building_id,
                'osm_id': building.osm_id,
                'latitude': building.latitude,
                'longitude': building.longitude,
                'building_type': building.building_type,
                'surface_area_m2': building.surface_area_m2,
                'base_consumption_kwh': building.base_consumption_kwh,
                'zone_name': building.zone_name,
                
                # Enrichissement climatique Malaysia
                'climate_zone': self._determine_climate_zone(building.latitude, building.longitude),
                'cooling_degree_days': self._calculate_cooling_degree_days(building.latitude),
                'humidity_factor': self._calculate_humidity_factor(building.latitude),
                
                # Enrichissement socio-économique
                'occupancy_level': self._estimate_occupancy(building.building_type, building.surface_area_m2),
                'energy_efficiency_rating': self._assign_efficiency_rating(building.building_type),
                'smart_meter_enabled': np.random.choice([True, False], p=[0.3, 0.7]),
                
                # Métadonnées techniques
                'voltage_level': self._determine_voltage_level(building.building_type, building.surface_area_m2),
                'backup_generator': self._has_backup_generator(building.building_type),
                'solar_panels': self._has_solar_panels(building.building_type),
                
                # Horodatage
                'metadata_generated_at': datetime.now().isoformat()
            }
            
            building_data.append(metadata)
        
        self.generation_stats['total_buildings_generated'] += len(buildings)
        
        df = pd.DataFrame(building_data)
        logger.info(f"✅ Métadonnées générées: {len(df)} bâtiments enrichis")
        
        return df
    
    def generate_timeseries_for_buildings(
        self,
        buildings: List[Building],
        start_date: str,
        end_date: str,
        frequency: str = '30T'
    ) -> pd.DataFrame:
        """
        Génère les séries temporelles de consommation pour tous les bâtiments
        
        Args:
            buildings: Liste des bâtiments
            start_date: Date de début
            end_date: Date de fin
            frequency: Fréquence d'échantillonnage
            
        Returns:
            pd.DataFrame: Séries temporelles complètes
        """
        logger.info(f"⏰ Génération séries temporelles: {len(buildings)} bâtiments")
        logger.info(f"📅 Période: {start_date} → {end_date}, fréquence: {frequency}")
        
        # Création de l'index temporel
        date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
        logger.info(f"📊 {len(date_range)} points temporels par bâtiment")
        
        all_timeseries = []
        
        for i, building in enumerate(buildings):
            if i % 1000 == 0:
                logger.info(f"🔄 Progression: {i}/{len(buildings)} bâtiments traités")
            
            building_timeseries = self._generate_single_building_timeseries(
                building, date_range
            )
            all_timeseries.append(building_timeseries)
        
        # Consolidation en DataFrame unique
        final_df = pd.concat(all_timeseries, ignore_index=True)
        
        self.generation_stats['total_timeseries_generated'] += len(final_df)
        
        logger.info(f"✅ Séries temporelles générées: {len(final_df)} observations")
        
        return final_df
    
    def _generate_single_building_timeseries(
        self,
        building: Building,
        date_range: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        Génère la série temporelle pour un bâtiment spécifique
        
        Args:
            building: Bâtiment cible
            date_range: Index temporel
            
        Returns:
            pd.DataFrame: Série temporelle du bâtiment
        """
        profile = self.consumption_profiles.get(building.building_type, 
                                               self.consumption_profiles['residential'])
        
        timeseries_data = []
        
        for timestamp in date_range:
            # Facteurs temporels
            hour_factor = self._calculate_hour_factor(timestamp.hour, profile)
            day_factor = self._calculate_day_factor(timestamp.weekday(), building.building_type)
            month_factor = self._calculate_month_factor(timestamp.month)
            
            # Facteurs climatiques Malaysia
            temperature_factor = self._calculate_temperature_factor(timestamp, building.latitude)
            humidity_factor = self._calculate_humidity_factor_temporal(timestamp)
            
            # Facteur aléatoire pour le réalisme
            random_factor = np.random.normal(1.0, 0.1)
            random_factor = max(0.5, min(1.5, random_factor))  # Limiter la variabilité
            
            # Calcul de la consommation finale
            final_consumption = (
                building.base_consumption_kwh *
                hour_factor *
                day_factor *
                month_factor *
                temperature_factor *
                humidity_factor *
                random_factor
            )
            
            # Assurer des valeurs positives
            final_consumption = max(0.1, final_consumption)
            
            timeseries_data.append({
                'building_id': building.building_id,
                'timestamp': timestamp,
                'consumption_kwh': round(final_consumption, 3),
                'hour': timestamp.hour,
                'day_of_week': timestamp.weekday(),
                'month': timestamp.month,
                'is_weekend': timestamp.weekday() >= 5,
                'temperature_factor': round(temperature_factor, 3),
                'humidity_factor': round(humidity_factor, 3)
            })
        
        return pd.DataFrame(timeseries_data)
    
    def _calculate_hour_factor(self, hour: int, profile: Dict) -> float:
        """Calcule le facteur horaire selon le profil du bâtiment"""
        if hour in profile['peak_hours']:
            return profile['peak_multiplier']
        elif 22 <= hour or hour <= 6:  # Nuit
            return profile['night_factor']
        else:  # Heures normales
            return profile['base_factor']
    
    def _calculate_day_factor(self, day_of_week: int, building_type: str) -> float:
        """Calcule le facteur selon le jour de la semaine"""
        is_weekend = day_of_week >= 5
        
        weekend_factors = {
            'residential': 1.2,  # Plus de consommation le weekend
            'commercial': 0.6,   # Moins d'activité
            'office': 0.2,       # Bureaux fermés
            'industrial': 0.8,   # Production réduite
            'hospital': 1.0,     # Pas de changement
            'school': 0.1,       # Écoles fermées
            'hotel': 1.1         # Plus d'activité touristique
        }
        
        if is_weekend:
            return weekend_factors.get(building_type, 1.0)
        else:
            return 1.0
    
    def _calculate_month_factor(self, month: int) -> float:
        """Calcule le facteur saisonnier pour Malaysia"""
        # Malaysia: mousson novembre-février, sec juin-août
        seasonal_factors = {
            1: 1.1,   # Janvier - mousson, plus de climatisation
            2: 1.1,   # Février - mousson
            3: 1.0,   # Mars - transition
            4: 1.2,   # Avril - chaud et humide
            5: 1.3,   # Mai - très chaud
            6: 1.2,   # Juin - saison sèche
            7: 1.2,   # Juillet - saison sèche
            8: 1.2,   # Août - saison sèche
            9: 1.1,   # Septembre - transition
            10: 1.0,  # Octobre - transition
            11: 1.1,  # Novembre - début mousson
            12: 1.1   # Décembre - mousson
        }
        
        return seasonal_factors.get(month, 1.0)
    
    def _calculate_temperature_factor(self, timestamp: pd.Timestamp, latitude: float) -> float:
        """Calcule le facteur de température selon l'heure et la localisation"""
        # Température typique Malaysia: 26-32°C
        base_temp = 28.0
        
        # Variation diurne
        hour_variation = 3 * math.sin((timestamp.hour - 6) * math.pi / 12)
        daily_temp = base_temp + hour_variation
        
        # Facteur de consommation basé sur la température
        # Plus il fait chaud, plus la climatisation consomme
        if daily_temp > 30:
            return 1.3
        elif daily_temp > 28:
            return 1.1
        else:
            return 1.0
    
    def _calculate_humidity_factor_temporal(self, timestamp: pd.Timestamp) -> float:
        """Calcule le facteur d'humidité temporel"""
        # Humidité Malaysia: 70-90%
        # Plus élevée tôt le matin et en soirée
        hour = timestamp.hour
        
        if 5 <= hour <= 8 or 18 <= hour <= 22:
            return 1.1  # Humidité élevée
        else:
            return 1.0
    
    def _determine_climate_zone(self, latitude: float, longitude: float) -> str:
        """Détermine la zone climatique Malaysia"""
        if latitude < 2.0:
            return 'equatorial'
        elif latitude < 4.0:
            return 'tropical_rainforest'
        else:
            return 'tropical_monsoon'
    
    def _calculate_cooling_degree_days(self, latitude: float) -> float:
        """Calcule les degrés-jours de refroidissement"""
        # Base 24°C pour Malaysia
        base_temp = 24.0
        avg_temp = 28.0 + (latitude - 3.0) * 0.5  # Variation selon latitude
        return max(0, avg_temp - base_temp) * 365
    
    def _calculate_humidity_factor(self, latitude: float) -> float:
        """Calcule le facteur d'humidité selon la localisation"""
        # Humidité plus élevée près de l'équateur
        if latitude < 2.0:
            return 1.2  # Très humide
        elif latitude < 4.0:
            return 1.1  # Humide
        else:
            return 1.0  # Modérément humide
    
    def _estimate_occupancy(self, building_type: str, surface_area: float) -> str:
        """Estime le niveau d'occupation"""
        occupancy_density = {
            'residential': 40,  # m²/personne
            'commercial': 20,   # m²/personne
            'office': 15,       # m²/personne
            'industrial': 100,  # m²/personne
            'hospital': 25,     # m²/personne
            'school': 10,       # m²/personne
            'hotel': 30         # m²/personne
        }
        
        density = occupancy_density.get(building_type, 30)
        estimated_people = surface_area / density
        
        if estimated_people < 5:
            return 'low'
        elif estimated_people < 20:
            return 'medium'
        else:
            return 'high'
    
    def _assign_efficiency_rating(self, building_type: str) -> str:
        """Assigne une classe d'efficacité énergétique"""
        # Distribution probabiliste selon le type
        ratings = ['A', 'B', 'C', 'D', 'E']
        
        probabilities = {
            'residential': [0.1, 0.2, 0.4, 0.2, 0.1],
            'commercial': [0.2, 0.3, 0.3, 0.1, 0.1],
            'office': [0.3, 0.3, 0.2, 0.1, 0.1],
            'industrial': [0.1, 0.2, 0.3, 0.3, 0.1],
            'hospital': [0.4, 0.3, 0.2, 0.1, 0.0],
            'school': [0.2, 0.3, 0.3, 0.2, 0.0],
            'hotel': [0.2, 0.3, 0.3, 0.1, 0.1]
        }
        
        probs = probabilities.get(building_type, [0.2, 0.2, 0.2, 0.2, 0.2])
        return np.random.choice(ratings, p=probs)
    
    def _determine_voltage_level(self, building_type: str, surface_area: float) -> str:
        """Détermine le niveau de tension"""
        if building_type in ['industrial', 'hospital'] or surface_area > 5000:
            return 'high_voltage'
        elif building_type in ['commercial', 'office'] or surface_area > 1000:
            return 'medium_voltage'
        else:
            return 'low_voltage'
    
    def _has_backup_generator(self, building_type: str) -> bool:
        """Détermine si le bâtiment a un générateur de secours"""
        probabilities = {
            'residential': 0.05,
            'commercial': 0.3,
            'office': 0.4,
            'industrial': 0.8,
            'hospital': 0.95,
            'school': 0.2,
            'hotel': 0.7
        }
        
        prob = probabilities.get(building_type, 0.1)
        return np.random.random() < prob
    
    def _has_solar_panels(self, building_type: str) -> bool:
        """Détermine si le bâtiment a des panneaux solaires"""
        probabilities = {
            'residential': 0.15,
            'commercial': 0.25,
            'office': 0.35,
            'industrial': 0.4,
            'hospital': 0.3,
            'school': 0.2,
            'hotel': 0.3
        }
        
        prob = probabilities.get(building_type, 0.2)
        return np.random.random() < prob
    
    def get_generation_summary(self, buildings: List[Building], timeseries_df: pd.DataFrame) -> Dict:
        """
        Génère un résumé statistique de la génération
        
        Args:
            buildings: Liste des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Résumé statistique
        """
        if timeseries_df.empty:
            return {'error': 'Aucune donnée générée'}
        
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'buildings_count': len(buildings),
            'total_observations': len(timeseries_df),
            'date_range': {
                'start': timeseries_df['timestamp'].min().isoformat(),
                'end': timeseries_df['timestamp'].max().isoformat(),
                'duration_days': (timeseries_df['timestamp'].max() - timeseries_df['timestamp'].min()).days
            },
            'consumption_statistics': {
                'total_kwh': round(timeseries_df['consumption_kwh'].sum(), 2),
                'mean_kwh_per_hour': round(timeseries_df['consumption_kwh'].mean(), 3),
                'median_kwh_per_hour': round(timeseries_df['consumption_kwh'].median(), 3),
                'std_kwh_per_hour': round(timeseries_df['consumption_kwh'].std(), 3),
                'min_kwh_per_hour': round(timeseries_df['consumption_kwh'].min(), 3),
                'max_kwh_per_hour': round(timeseries_df['consumption_kwh'].max(), 3),
                'percentile_95': round(timeseries_df['consumption_kwh'].quantile(0.95), 3)
            },
            'building_type_distribution': timeseries_df.groupby('building_id').first().groupby(
                lambda x: [b.building_type for b in buildings if b.building_id == x][0] 
                if [b.building_type for b in buildings if b.building_id == x] else 'unknown'
            ).size().to_dict(),
            'temporal_patterns': {
                'peak_hour': int(timeseries_df.groupby('hour')['consumption_kwh'].mean().idxmax()),
                'peak_day': int(timeseries_df.groupby('day_of_week')['consumption_kwh'].mean().idxmax()),
                'weekend_vs_weekday_ratio': round(
                    timeseries_df[timeseries_df['is_weekend']]['consumption_kwh'].mean() /
                    timeseries_df[~timeseries_df['is_weekend']]['consumption_kwh'].mean(), 2
                )
            },
            'quality_indicators': {
                'zero_values': int((timeseries_df['consumption_kwh'] == 0).sum()),
                'negative_values': int((timeseries_df['consumption_kwh'] < 0).sum()),
                'null_values': int(timeseries_df['consumption_kwh'].isnull().sum()),
                'outliers_count': int((timeseries_df['consumption_kwh'] > timeseries_df['consumption_kwh'].quantile(0.99)).sum())
            }
        }
        
        return summary
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques du générateur
        
        Returns:
            Dict: Statistiques de génération
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
            )
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
        
        # Vérifier que les dates ne sont pas dans le futur
        today = datetime.now().date()
        if start.date() > today:
            errors.append("Date de début ne peut pas être dans le futur")
        
        # Limite de période maximale
        max_days = getattr(GEN_CONFIG, 'MAX_DAYS', 365)
        if (end - start).days > max_days:
            errors.append(f"Période maximale autorisée: {max_days} jours")
            
    except (ValueError, TypeError) as e:
        errors.append(f"Format de dates invalide (utiliser YYYY-MM-DD): {str(e)}")
    
    # Validation de la fréquence
    valid_frequencies = {
        '15T': '15 minutes',
        '30T': '30 minutes', 
        '1H': '1 heure',
        '3H': '3 heures',
        'D': 'Quotidien'
    }
    
    if not frequency:
        errors.append("Fréquence requise")
    elif frequency not in valid_frequencies:
        errors.append(f"Fréquences supportées: {list(valid_frequencies.keys())}")
    
    # Validation du nombre de bâtiments
    min_buildings = getattr(GEN_CONFIG, 'MIN_BUILDINGS', 1)
    max_buildings = getattr(GEN_CONFIG, 'MAX_BUILDINGS', 50000)
    
    try:
        num_buildings = int(num_buildings)
        if not (min_buildings <= num_buildings <= max_buildings):
            errors.append(f"Nombre de bâtiments doit être entre {min_buildings} et {max_buildings}")
    except (ValueError, TypeError):
        errors.append("Nombre de bâtiments doit être un entier")
    
    # Validation de la charge de travail
    try:
        if len(errors) == 0:  # Seulement si les paramètres de base sont valides
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            # Calcul du nombre d'observations
            freq_minutes = {
                '15T': 15,
                '30T': 30,
                '1H': 60,
                '3H': 180,
                'D': 1440
            }
            
            if frequency in freq_minutes:
                total_minutes = (end - start).total_seconds() / 60
                observations_per_building = total_minutes / freq_minutes[frequency]
                total_observations = num_buildings * observations_per_building
                
                # Limite raisonnable pour éviter les surcharges
                max_observations = 10_000_000  # 10 millions
                if total_observations > max_observations:
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
        
        # Estimation du temps (calibré selon les performances)
        observations_per_second = 10000
        estimated_time_seconds = total_observations / observations_per_second
        
        # Estimation de la taille
        bytes_per_observation = 150  # Estimation avec métadonnées
        estimated_size_mb = (total_observations * bytes_per_observation) / (1024 * 1024)
        
        # Niveau de complexité
        if total_observations < 100000:
            complexity = 'simple'
            recommendation = 'Génération rapide (< 1 minute)'
        elif total_observations < 1000000:
            complexity = 'modéré'
            recommendation = 'Génération standard (1-5 minutes)'
        elif total_observations < 5000000:
            complexity = 'complexe'
            recommendation = 'Génération longue (5-15 minutes)'
        else:
            complexity = 'très_complexe'
            recommendation = 'Génération très longue (> 15 minutes)'
        
        return {
            'num_buildings': num_buildings,
            'date_range_days': (end - start).days,
            'frequency': frequency,
            'observations_per_building': len(date_range),
            'total_observations': total_observations,
            'estimated_time_seconds': round(estimated_time_seconds, 1),
            'estimated_time_minutes': round(estimated_time_seconds / 60, 1),
            'estimated_size_mb': round(estimated_size_mb, 1),
            'complexity_level': complexity,
            'recommendation': recommendation,
            'memory_usage_estimate_mb': round(estimated_size_mb * 2, 1)  # Buffer pour traitement
        }
        
    except Exception as e:
        return {
            'error': f"Erreur estimation: {str(e)}",
            'complexity_level': 'unknown'
        }


def calculate_quality_score(buildings_df: pd.DataFrame, timeseries_df: pd.DataFrame) -> float:
    """
    Calcule un score de qualité pour les données générées
    
    Args:
        buildings_df: DataFrame des bâtiments
        timeseries_df: DataFrame des séries temporelles
        
    Returns:
        float: Score de qualité (0-100)
    """
    if timeseries_df.empty:
        return 0.0
    
    score = 100.0
    
    # Pénalités pour les valeurs négatives
    negative_count = (timeseries_df['consumption_kwh'] < 0).sum()
    if negative_count > 0:
        score -= (negative_count / len(timeseries_df)) * 30
    
    # Pénalités pour les valeurs nulles
    null_count = timeseries_df['consumption_kwh'].isnull().sum()
    if null_count > 0:
        score -= (null_count / len(timeseries_df)) * 40
    
    # Pénalités pour les valeurs aberrantes
    percentile_99_9 = timeseries_df['consumption_kwh'].quantile(0.999)
    mean_consumption = timeseries_df['consumption_kwh'].mean()
    
    if percentile_99_9 > mean_consumption * 10:  # Plus de 10x la moyenne
        score -= 10
    
    # Bonus pour variabilité réaliste
    cv = timeseries_df['consumption_kwh'].std() / timeseries_df['consumption_kwh'].mean()
    if 0.2 <= cv <= 0.8:  # Coefficient de variation réaliste
        score += 5
    
    # Pénalité pour manque de variation temporelle
    hourly_std = timeseries_df.groupby('hour')['consumption_kwh'].mean().std()
    if hourly_std < mean_consumption * 0.1:  # Variation horaire trop faible
        score -= 5
    
    return max(0.0, min(100.0, score))


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du générateur
    from src.models.building import Building
    
    # Création d'un générateur
    generator = ElectricityDataGenerator()
    
    # Test avec des bâtiments fictifs
    test_buildings = [
        Building(
            osm_id='test_1',
            latitude=3.15,
            longitude=101.7,
            building_type='residential',
            surface_area_m2=150,
            base_consumption_kwh=20,
            zone_name='test_zone'
        ),
        Building(
            osm_id='test_2',
            latitude=3.16,
            longitude=101.71,
            building_type='commercial',
            surface_area_m2=500,
            base_consumption_kwh=80,
            zone_name='test_zone'
        )
    ]
    
    # Test validation
    is_valid, errors = validate_generation_parameters(
        '2024-01-01', '2024-01-02', '1H', 2
    )
    print(f"Validation: {'✅' if is_valid else '❌'} {errors}")
    
    # Test estimation
    estimation = estimate_generation_time(2, '2024-01-01', '2024-01-02', '1H')
    print(f"Estimation: {estimation['total_observations']} observations, {estimation['estimated_time_seconds']}s")
    
    # Test génération métadonnées
    buildings_df = generator.generate_building_metadata(test_buildings)
    print(f"Métadonnées: {len(buildings_df)} bâtiments")
    
    # Test génération séries temporelles
    timeseries_df = generator.generate_timeseries_for_buildings(
        test_buildings, '2024-01-01', '2024-01-02', '1H'
    )
    print(f"Séries temporelles: {len(timeseries_df)} observations")
    
    # Test résumé
    summary = generator.get_generation_summary(test_buildings, timeseries_df)
    print(f"Résumé: {summary['total_observations']} observations générées")
    
    # Test score qualité
    quality_score = calculate_quality_score(buildings_df, timeseries_df)
    print(f"Score qualité: {quality_score}/100")
    
    print("✅ Tests du générateur terminés")