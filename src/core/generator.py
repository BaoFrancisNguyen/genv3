"""
Générateur principal de données électriques pour Malaysia
========================================================

Ce module contient la logique principale de génération des séries temporelles
de consommation électrique basées sur les données de bâtiments OSM.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import random

from config import GEN_CONFIG, MALAYSIA_ZONES
from src.models.building import Building
from src.models.timeseries import TimeSeries


# Configuration du logger
logger = logging.getLogger(__name__)


class ElectricityDataGenerator:
    """
    Générateur principal de données électriques pour Malaysia
    
    Génère des séries temporelles réalistes de consommation électrique
    basées sur les caractéristiques des bâtiments et le climat tropical.
    """
    
    def __init__(self):
        """Initialise le générateur avec la configuration Malaysia"""
        self.malaysia_climate = GEN_CONFIG.MALAYSIA_CLIMATE
        self.building_distributions = MALAYSIA_ZONES.URBAN_BUILDING_DISTRIBUTION
        
        # Cache pour les patterns climatiques
        self._weather_cache = {}
        self._seasonal_cache = {}
        
        logger.info("✅ Générateur de données électriques initialisé")
    
    def generate_timeseries_for_buildings(
        self, 
        buildings: List[Building], 
        start_date: str, 
        end_date: str, 
        frequency: str = '30T'
    ) -> pd.DataFrame:
        """
        Génère les séries temporelles de consommation pour une liste de bâtiments
        
        Args:
            buildings: Liste des bâtiments
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            frequency: Fréquence d'échantillonnage (30T, 1H, etc.)
            
        Returns:
            pd.DataFrame: Séries temporelles complètes
        """
        if not buildings:
            raise ValueError("Liste de bâtiments vide")
        
        logger.info(f"🔄 Génération séries temporelles pour {len(buildings)} bâtiments")
        logger.info(f"📅 Période: {start_date} → {end_date}, fréquence: {frequency}")
        
        # Création de l'index temporel
        date_range = pd.date_range(
            start=start_date,
            end=end_date,
            freq=frequency,
            tz='Asia/Kuala_Lumpur'
        )
        
        logger.info(f"⏰ {len(date_range)} points temporels générés")
        
        # Génération des données météo pour la période
        weather_data = self._generate_weather_patterns(date_range)
        
        # Génération des séries temporelles par bâtiment
        all_timeseries = []
        
        for i, building in enumerate(buildings):
            if (i + 1) % 100 == 0:
                logger.info(f"📊 Traitement bâtiment {i + 1}/{len(buildings)}")
            
            building_timeseries = self._generate_building_timeseries(
                building, date_range, weather_data
            )
            all_timeseries.extend(building_timeseries)
        
        # Conversion en DataFrame
        df = pd.DataFrame([ts.to_dict() for ts in all_timeseries])
        
        logger.info(f"✅ {len(df)} observations générées")
        return df
    
    def _generate_weather_patterns(self, date_range: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Génère les patterns météorologiques pour Malaysia
        
        Args:
            date_range: Index temporel
            
        Returns:
            pd.DataFrame: Données météo par timestamp
        """
        weather_data = []
        
        for timestamp in date_range:
            # Température de base selon le mois
            base_temp = self._get_base_temperature(timestamp.month)
            
            # Variation diurne (pic vers 14h-15h)
            hour_factor = self._get_hourly_temperature_factor(timestamp.hour)
            temperature = base_temp + hour_factor
            
            # Humidité selon la saison
            humidity = self._get_humidity(timestamp.month)
            
            # Index de chaleur (heat index) pour la climatisation
            heat_index = self._calculate_heat_index(temperature, humidity)
            
            weather_data.append({
                'timestamp': timestamp,
                'temperature_c': temperature,
                'humidity': humidity,
                'heat_index': heat_index,
                'is_monsoon': timestamp.month in self.malaysia_climate['monsoon_months'],
                'is_dry_season': timestamp.month in self.malaysia_climate['dry_months']
            })
        
        return pd.DataFrame(weather_data)
    
    def _get_base_temperature(self, month: int) -> float:
        """
        Retourne la température de base selon le mois en Malaysia
        
        Args:
            month: Mois (1-12)
            
        Returns:
            float: Température en Celsius
        """
        # Températures moyennes mensuelles Malaysia
        monthly_temps = {
            1: 27.5,   # Janvier (mousson)
            2: 28.0,   # Février (mousson)
            3: 28.5,   # Mars (transition)
            4: 29.0,   # Avril (chaud)
            5: 29.5,   # Mai (chaud)
            6: 28.5,   # Juin (sec)
            7: 28.0,   # Juillet (sec)
            8: 28.0,   # Août (sec)
            9: 28.5,   # Septembre (transition)
            10: 28.5,  # Octobre (transition)
            11: 27.5,  # Novembre (mousson)
            12: 27.0   # Décembre (mousson)
        }
        
        return monthly_temps.get(month, self.malaysia_climate['base_temperature'])
    
    def _get_hourly_temperature_factor(self, hour: int) -> float:
        """
        Facteur de variation horaire de la température
        
        Args:
            hour: Heure (0-23)
            
        Returns:
            float: Facteur de température (-3 à +5°C)
        """
        # Courbe de température diurne tropicale
        if 0 <= hour <= 5:      # Nuit fraîche
            return -2.5 + (hour * 0.5)
        elif 6 <= hour <= 11:   # Montée matinale
            return -2.0 + ((hour - 6) * 1.2)
        elif 12 <= hour <= 15:  # Pic de chaleur
            return 4.0 + np.sin((hour - 12) * np.pi / 6)
        elif 16 <= hour <= 19:  # Descente soirée
            return 3.0 - ((hour - 16) * 0.8)
        else:                   # Nuit
            return 0.5 - ((hour - 19) * 0.6)
    
    def _get_humidity(self, month: int) -> float:
        """
        Retourne l'humidité selon le mois
        
        Args:
            month: Mois (1-12)
            
        Returns:
            float: Humidité relative (0-1)
        """
        if month in self.malaysia_climate['monsoon_months']:
            return 0.85 + np.random.normal(0, 0.05)  # Très humide
        elif month in self.malaysia_climate['dry_months']:
            return 0.70 + np.random.normal(0, 0.05)  # Moins humide
        else:
            return 0.80 + np.random.normal(0, 0.05)  # Humidité standard
    
    def _calculate_heat_index(self, temperature: float, humidity: float) -> float:
        """
        Calcule l'index de chaleur (ressenti thermique)
        
        Args:
            temperature: Température en Celsius
            humidity: Humidité relative (0-1)
            
        Returns:
            float: Index de chaleur
        """
        # Conversion en Fahrenheit pour la formule standard
        temp_f = (temperature * 9/5) + 32
        humidity_percent = humidity * 100
        
        # Formule simplifiée du heat index
        if temp_f < 80:
            return temperature
        
        hi_f = (
            -42.379 + 
            2.04901523 * temp_f +
            10.14333127 * humidity_percent -
            0.22475541 * temp_f * humidity_percent -
            6.83783e-3 * temp_f**2 -
            5.481717e-2 * humidity_percent**2 +
            1.22874e-3 * temp_f**2 * humidity_percent +
            8.5282e-4 * temp_f * humidity_percent**2 -
            1.99e-6 * temp_f**2 * humidity_percent**2
        )
        
        # Reconversion en Celsius
        return (hi_f - 32) * 5/9
    
    def _generate_building_timeseries(
        self, 
        building: Building, 
        date_range: pd.DatetimeIndex, 
        weather_data: pd.DataFrame
    ) -> List[TimeSeries]:
        """
        Génère la série temporelle pour un bâtiment spécifique
        
        Args:
            building: Bâtiment à traiter
            date_range: Index temporel
            weather_data: Données météo
            
        Returns:
            List[TimeSeries]: Points de données temporelles
        """
        timeseries = []
        
        for i, timestamp in enumerate(date_range):
            weather = weather_data.iloc[i]
            
            # Calcul de la consommation de base
            base_consumption = self._calculate_base_consumption(building, timestamp, weather)
            
            # Application des facteurs correctifs
            final_consumption = self._apply_consumption_factors(
                base_consumption, building, timestamp, weather
            )
            
            # Ajout de bruit réaliste
            final_consumption = self._add_realistic_noise(final_consumption)
            
            # Création du point de données
            timeseries_point = TimeSeries(
                building_id=building.building_id,
                timestamp=timestamp,
                consumption_kwh=final_consumption,
                temperature_c=weather['temperature_c'],
                humidity=weather['humidity'],
                heat_index=weather['heat_index'],
                building_type=building.building_type,
                zone_name=building.zone_name
            )
            
            timeseries.append(timeseries_point)
        
        return timeseries
    
    def _calculate_base_consumption(
        self, 
        building: Building, 
        timestamp: pd.Timestamp, 
        weather: Dict
    ) -> float:
        """
        Calcule la consommation de base d'un bâtiment
        
        Args:
            building: Bâtiment
            timestamp: Moment temporel
            weather: Données météo
            
        Returns:
            float: Consommation de base en kWh
        """
        # Consommation de base du bâtiment
        base = building.base_consumption_kwh
        
        # Facteur d'efficacité énergétique
        efficiency_factor = building.get_efficiency_factor()
        
        # Facteur d'occupation
        occupancy_factor = building.get_occupancy_factor()
        
        # Vérifier si le bâtiment est actif à cette heure
        is_weekend = timestamp.dayofweek >= 5
        if not building.is_active_at_hour(timestamp.hour, is_weekend):
            # Consommation réduite (veille)
            base *= 0.2
        
        return base * efficiency_factor * occupancy_factor
    
    def _apply_consumption_factors(
        self, 
        base_consumption: float, 
        building: Building, 
        timestamp: pd.Timestamp, 
        weather: Dict
    ) -> float:
        """
        Applique les facteurs de correction climatiques et temporels
        
        Args:
            base_consumption: Consommation de base
            building: Bâtiment
            timestamp: Moment temporel
            weather: Données météo
            
        Returns:
            float: Consommation ajustée
        """
        consumption = base_consumption
        
        # Facteur climatique (climatisation)
        if building.has_air_conditioning:
            heat_factor = max(0, weather['heat_index'] - 26) / 10  # Seuil de confort
            climate_sensitivity = building.get_climate_sensitivity()
            consumption += consumption * heat_factor * climate_sensitivity
        
        # Facteur saisonnier (mousson = moins de climatisation extérieure)
        if weather['is_monsoon']:
            consumption *= 0.95
        elif weather['is_dry_season']:
            consumption *= 1.1
        
        # Facteur horaire (pics de consommation)
        hour_factor = self._get_hourly_consumption_factor(timestamp.hour, building.building_type)
        consumption *= hour_factor
        
        # Facteur jour de semaine vs weekend
        if timestamp.dayofweek >= 5:  # Weekend
            weekend_factor = self._get_weekend_factor(building.building_type)
            consumption *= weekend_factor
        
        return max(0, consumption)
    
    def _get_hourly_consumption_factor(self, hour: int, building_type: str) -> float:
        """
        Facteur de consommation selon l'heure et le type de bâtiment
        
        Args:
            hour: Heure (0-23)
            building_type: Type de bâtiment
            
        Returns:
            float: Facteur multiplicateur
        """
        # Patterns par type de bâtiment
        patterns = {
            'residential': {
                # Pics matin et soirée
                0: 0.3, 1: 0.2, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.3,
                6: 0.6, 7: 0.8, 8: 0.6, 9: 0.4, 10: 0.4, 11: 0.5,
                12: 0.7, 13: 0.8, 14: 0.9, 15: 1.0, 16: 1.1, 17: 1.2,
                18: 1.3, 19: 1.4, 20: 1.2, 21: 1.0, 22: 0.8, 23: 0.5
            },
            'commercial': {
                # Activité diurne forte
                0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.2,
                6: 0.3, 7: 0.5, 8: 0.8, 9: 1.0, 10: 1.2, 11: 1.3,
                12: 1.4, 13: 1.5, 14: 1.4, 15: 1.3, 16: 1.2, 17: 1.0,
                18: 0.8, 19: 0.6, 20: 0.4, 21: 0.3, 22: 0.2, 23: 0.1
            },
            'office': {
                # Heures de bureau classiques
                0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,
                6: 0.2, 7: 0.4, 8: 0.8, 9: 1.0, 10: 1.1, 11: 1.2,
                12: 1.0, 13: 1.2, 14: 1.3, 15: 1.2, 16: 1.1, 17: 1.0,
                18: 0.8, 19: 0.5, 20: 0.3, 21: 0.2, 22: 0.1, 23: 0.1
            },
            'industrial': {
                # Production continue avec pics diurnes
                0: 0.6, 1: 0.6, 2: 0.6, 3: 0.6, 4: 0.6, 5: 0.7,
                6: 0.8, 7: 0.9, 8: 1.0, 9: 1.1, 10: 1.2, 11: 1.2,
                12: 1.1, 13: 1.2, 14: 1.3, 15: 1.2, 16: 1.1, 17: 1.0,
                18: 0.9, 19: 0.8, 20: 0.7, 21: 0.7, 22: 0.6, 23: 0.6
            },
            'hospital': {
                # Activité continue 24h/24
                0: 0.8, 1: 0.8, 2: 0.8, 3: 0.8, 4: 0.8, 5: 0.9,
                6: 1.0, 7: 1.1, 8: 1.2, 9: 1.2, 10: 1.2, 11: 1.2,
                12: 1.1, 13: 1.2, 14: 1.2, 15: 1.1, 16: 1.1, 17: 1.0,
                18: 1.0, 19: 0.9, 20: 0.9, 21: 0.9, 22: 0.8, 23: 0.8
            },
            'school': {
                # Activité scolaire diurne
                0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,
                6: 0.2, 7: 0.5, 8: 1.0, 9: 1.2, 10: 1.3, 11: 1.4,
                12: 1.2, 13: 1.3, 14: 1.4, 15: 1.2, 16: 1.0, 17: 0.8,
                18: 0.5, 19: 0.3, 20: 0.2, 21: 0.1, 22: 0.1, 23: 0.1
            }
        }
        
        return patterns.get(building_type, patterns['residential']).get(hour, 1.0)
    
    def _get_weekend_factor(self, building_type: str) -> float:
        """
        Facteur de consommation pour les weekends
        
        Args:
            building_type: Type de bâtiment
            
        Returns:
            float: Facteur multiplicateur weekend
        """
        weekend_factors = {
            'residential': 1.2,    # Plus à la maison
            'commercial': 0.8,     # Magasins moins actifs
            'office': 0.3,         # Bureaux fermés
            'industrial': 0.7,     # Production réduite
            'hospital': 1.0,       # Activité constante
            'school': 0.2,         # Écoles fermées
            'hotel': 1.1,          # Plus d'occupants
            'warehouse': 0.5       # Activité réduite
        }
        
        return weekend_factors.get(building_type, 1.0)
    
    def _add_realistic_noise(self, consumption: float) -> float:
        """
        Ajoute du bruit réaliste à la consommation
        
        Args:
            consumption: Consommation calculée
            
        Returns:
            float: Consommation avec bruit
        """
        # Bruit gaussien proportionnel à la consommation
        noise_factor = 0.05  # 5% de variation
        noise = np.random.normal(0, consumption * noise_factor)
        
        # Événements rares (pics ou creux)
        if np.random.random() < 0.02:  # 2% de chance
            event_factor = np.random.choice([0.5, 1.5, 2.0], p=[0.4, 0.4, 0.2])
            consumption *= event_factor
        
        return max(0, consumption + noise)
    
    def generate_building_metadata(
        self, 
        buildings: List[Building]
    ) -> pd.DataFrame:
        """
        Génère le DataFrame de métadonnées des bâtiments
        
        Args:
            buildings: Liste des bâtiments
            
        Returns:
            pd.DataFrame: Métadonnées structurées
        """
        if not buildings:
            return pd.DataFrame()
        
        logger.info(f"📊 Génération métadonnées pour {len(buildings)} bâtiments")
        
        # Conversion en dictionnaires
        metadata_list = [building.to_dict() for building in buildings]
        
        # Création du DataFrame
        df = pd.DataFrame(metadata_list)
        
        # Ajout de colonnes calculées
        df['total_surface_floors'] = df['surface_area_m2'] * df['floors_count']
        df['estimated_monthly_kwh'] = df['base_consumption_kwh'] * 24 * 30
        df['building_category'] = df['building_type'].apply(self._categorize_building)
        
        logger.info(f"✅ Métadonnées générées: {len(df)} lignes, {len(df.columns)} colonnes")
        
        return df
    
    def _categorize_building(self, building_type: str) -> str:
        """
        Catégorise les types de bâtiments
        
        Args:
            building_type: Type original
            
        Returns:
            str: Catégorie simplifiée
        """
        categories = {
            'residential': 'Résidentiel',
            'house': 'Résidentiel',
            'apartment': 'Résidentiel',
            'detached': 'Résidentiel',
            'terrace': 'Résidentiel',
            
            'commercial': 'Commercial',
            'retail': 'Commercial',
            'shop': 'Commercial',
            'mall': 'Commercial',
            
            'office': 'Tertiaire',
            'hotel': 'Tertiaire',
            'hospital': 'Tertiaire',
            'school': 'Tertiaire',
            'university': 'Tertiaire',
            
            'industrial': 'Industriel',
            'warehouse': 'Industriel',
            'factory': 'Industriel',
            'manufacturing': 'Industriel'
        }
        
        return categories.get(building_type.lower(), 'Autre')
    
    def get_generation_summary(
        self, 
        buildings: List[Building], 
        timeseries_df: pd.DataFrame
    ) -> Dict:
        """
        Génère un résumé statistique de la génération
        
        Args:
            buildings: Liste des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Résumé statistique complet
        """
        summary = {
            'generation_info': {
                'total_buildings': len(buildings),
                'total_observations': len(timeseries_df),
                'generation_timestamp': datetime.now().isoformat(),
                'data_quality_score': self._calculate_quality_score(timeseries_df)
            },
            
            'building_statistics': {
                'types_distribution': {},
                'total_surface_m2': 0,
                'average_surface_m2': 0,
                'energy_efficiency_distribution': {}
            },
            
            'consumption_statistics': {
                'total_consumption_kwh': 0,
                'average_hourly_consumption': 0,
                'peak_consumption': 0,
                'min_consumption': 0,
                'consumption_by_type': {}
            },
            
            'temporal_analysis': {
                'date_range': {},
                'peak_hours': [],
                'seasonal_patterns': {}
            }
        }
        
        if buildings:
            # Statistiques des bâtiments
            types = [b.building_type for b in buildings]
            summary['building_statistics']['types_distribution'] = pd.Series(types).value_counts().to_dict()
            summary['building_statistics']['total_surface_m2'] = sum(b.surface_area_m2 for b in buildings)
            summary['building_statistics']['average_surface_m2'] = summary['building_statistics']['total_surface_m2'] / len(buildings)
            
            efficiency_ratings = [b.energy_efficiency_rating for b in buildings]
            summary['building_statistics']['energy_efficiency_distribution'] = pd.Series(efficiency_ratings).value_counts().to_dict()
        
        if not timeseries_df.empty:
            # Statistiques de consommation
            summary['consumption_statistics']['total_consumption_kwh'] = timeseries_df['consumption_kwh'].sum()
            summary['consumption_statistics']['average_hourly_consumption'] = timeseries_df['consumption_kwh'].mean()
            summary['consumption_statistics']['peak_consumption'] = timeseries_df['consumption_kwh'].max()
            summary['consumption_statistics']['min_consumption'] = timeseries_df['consumption_kwh'].min()
            
            # Consommation par type
            consumption_by_type = timeseries_df.groupby('building_type')['consumption_kwh'].agg(['sum', 'mean', 'count']).to_dict()
            summary['consumption_statistics']['consumption_by_type'] = consumption_by_type
            
            # Analyse temporelle
            if 'timestamp' in timeseries_df.columns:
                summary['temporal_analysis']['date_range'] = {
                    'start': timeseries_df['timestamp'].min().isoformat(),
                    'end': timeseries_df['timestamp'].max().isoformat()
                }
                
                # Heures de pic (top 3)
                hourly_avg = timeseries_df.set_index('timestamp').groupby(timeseries_df['timestamp'].dt.hour)['consumption_kwh'].mean()
                peak_hours = hourly_avg.nlargest(3).index.tolist()
                summary['temporal_analysis']['peak_hours'] = peak_hours
        
        return summary
    
    def _calculate_quality_score(self, timeseries_df: pd.DataFrame) -> float:
        """
        Calcule un score de qualité des données générées
        
        Args:
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            float: Score de qualité (0-100)
        """
        if timeseries_df.empty:
            return 0.0
        
        score = 100.0
        
        # Pénalités pour problèmes de qualité
        
        # Valeurs négatives
        negative_count = (timeseries_df['consumption_kwh'] < 0).sum()
        if negative_count > 0:
            score -= (negative_count / len(timeseries_df)) * 30
        
        # Valeurs nulles
        null_count = timeseries_df['consumption_kwh'].isnull().sum()
        if null_count > 0:
            score -= (null_count / len(timeseries_df)) * 40
        
        # Valeurs aberrantes (> 99.9e percentile)
        percentile_99_9 = timeseries_df['consumption_kwh'].quantile(0.999)
        mean_consumption = timeseries_df['consumption_kwh'].mean()
        
        if percentile_99_9 > mean_consumption * 10:  # Plus de 10x la moyenne
            score -= 10
        
        # Bonus pour variabilité réaliste
        cv = timeseries_df['consumption_kwh'].std() / timeseries_df['consumption_kwh'].mean()
        if 0.2 <= cv <= 0.8:  # Coefficient de variation réaliste
            score += 5
        
        return max(0.0, min(100.0, score))


# ==============================================================================
# FONCTIONS UTILITAIRES DE GÉNÉRATION
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
        start_date: Date de début
        end_date: Date de fin
        frequency: Fréquence
        num_buildings: Nombre de bâtiments
        
    Returns:
        Tuple[bool, List[str]]: Validité et liste d'erreurs
    """
    errors = []
    
    # Validation des dates
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        if start >= end:
            errors.append("Date de fin doit être après date de début")
        
        if (end - start).days > GEN_CONFIG.MAX_DAYS:
            errors.append(f"Période maximale: {GEN_CONFIG.MAX_DAYS} jours")
            
    except ValueError:
        errors.append("Format de dates invalide (utiliser YYYY-MM-DD)")
    
    # Validation fréquence
    if frequency not in GEN_CONFIG.SUPPORTED_FREQUENCIES:
        errors.append(f"Fréquence supportées: {list(GEN_CONFIG.SUPPORTED_FREQUENCIES.keys())}")
    
    # Validation nombre de bâtiments
    if not (GEN_CONFIG.MIN_BUILDINGS <= num_buildings <= GEN_CONFIG.MAX_BUILDINGS):
        errors.append(f"Nombre de bâtiments: {GEN_CONFIG.MIN_BUILDINGS}-{GEN_CONFIG.MAX_BUILDINGS}")
    
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
        Dict: Estimations de temps et ressources
    """
    try:
        # Calcul du nombre de points temporels
        date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
        total_points = len(date_range) * num_buildings
        
        # Estimation temps (approximative)
        points_per_second = 1000  # Estimation conservative
        estimated_seconds = total_points / points_per_second
        
        # Estimation taille données
        bytes_per_point = 200  # Estimation moyenne
        estimated_size_mb = (total_points * bytes_per_point) / (1024 * 1024)
        
        return {
            'total_data_points': total_points,
            'estimated_duration_seconds': estimated_seconds,
            'estimated_duration_formatted': f"{int(estimated_seconds // 60)}m {int(estimated_seconds % 60)}s",
            'estimated_size_mb': round(estimated_size_mb, 2),
            'complexity_level': 'faible' if total_points < 10000 else 'moyenne' if total_points < 100000 else 'élevée'
        }
        
    except Exception as e:
        return {
            'error': f"Erreur estimation: {str(e)}",
            'total_data_points': 0,
            'estimated_duration_seconds': 0,
            'estimated_size_mb': 0
        }


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du générateur
    from src.models.building import create_building_from_coordinates
    
    # Créer quelques bâtiments de test
    test_buildings = [
        create_building_from_coordinates(3.15, 101.7, 'residential'),
        create_building_from_coordinates(3.16, 101.71, 'commercial'),
        create_building_from_coordinates(3.17, 101.72, 'office')
    ]
    
    # Initialiser le générateur
    generator = ElectricityDataGenerator()
    
    # Générer les séries temporelles
    timeseries_df = generator.generate_timeseries_for_buildings(
        buildings=test_buildings,
        start_date='2024-01-01',
        end_date='2024-01-02',
        frequency='1H'
    )
    
    print(f"✅ Test génération: {len(timeseries_df)} observations")
    print(f"📊 Consommation moyenne: {timeseries_df['consumption_kwh'].mean():.2f} kWh")
    
    # Résumé
    summary = generator.get_generation_summary(test_buildings, timeseries_df)
    print(f"🎯 Score qualité: {summary['generation_info']['data_quality_score']:.1f}/100")