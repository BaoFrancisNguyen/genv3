"""
Modèle de données pour les séries temporelles électriques
========================================================

Ce module définit la structure de données pour les points temporels
de consommation électrique avec métadonnées climatiques et contextuelles.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import pandas as pd


@dataclass
class TimeSeries:
    """
    Modèle de données pour un point temporel de consommation électrique
    
    Représente une observation de consommation électrique à un moment donné
    avec toutes les métadonnées contextuelles nécessaires.
    """
    
    # Identifiants et timestamp
    building_id: str
    timestamp: pd.Timestamp
    
    # Données de consommation électrique
    consumption_kwh: float
    
    # Données météorologiques
    temperature_c: float
    humidity: float
    heat_index: float
    
    # Métadonnées contextuelles
    building_type: str
    zone_name: Optional[str] = None
    
    # Flags temporels (calculés automatiquement)
    hour: Optional[int] = None
    day_of_week: Optional[int] = None
    month: Optional[int] = None
    is_weekend: Optional[bool] = None
    is_business_hour: Optional[bool] = None
    
    # Métadonnées de qualité
    data_quality_score: Optional[float] = None
    anomaly_flag: Optional[bool] = None
    
    def __post_init__(self):
        """Calculs automatiques après création de l'instance"""
        self._calculate_temporal_flags()
        self._calculate_quality_score()
        self._detect_anomalies()
    
    def _calculate_temporal_flags(self):
        """Calcule les flags temporels basés sur le timestamp"""
        if isinstance(self.timestamp, pd.Timestamp):
            self.hour = self.timestamp.hour
            self.day_of_week = self.timestamp.dayofweek
            self.month = self.timestamp.month
            self.is_weekend = self.timestamp.dayofweek >= 5
            self.is_business_hour = 8 <= self.timestamp.hour <= 18
    
    def _calculate_quality_score(self):
        """Calcule un score de qualité des données (0-1)"""
        score = 1.0
        
        # Pénalités pour valeurs suspectes
        if self.consumption_kwh < 0:
            score -= 0.5  # Consommation négative très suspecte
        elif self.consumption_kwh == 0:
            score -= 0.2  # Consommation nulle suspecte
        
        # Vérification cohérence température-consommation
        if self.building_type in ['residential', 'commercial', 'office']:
            if self.temperature_c > 30 and self.consumption_kwh < 1:
                score -= 0.1  # Faible consommation par forte chaleur
        
        # Vérification humidité réaliste pour Malaysia
        if not (0.4 <= self.humidity <= 1.0):
            score -= 0.1  # Humidité irréaliste
        
        self.data_quality_score = max(0.0, score)
    
    def _detect_anomalies(self):
        """Détecte si ce point est potentiellement anormal"""
        anomaly_flags = []
        
        # Consommation extrême
        if self.consumption_kwh > 100:  # >100 kWh/période très élevé
            anomaly_flags.append('high_consumption')
        
        if self.consumption_kwh < 0:
            anomaly_flags.append('negative_consumption')
        
        # Température extrême pour Malaysia
        if self.temperature_c < 15 or self.temperature_c > 45:
            anomaly_flags.append('extreme_temperature')
        
        # Humidité extrême
        if self.humidity < 0.3 or self.humidity > 1.0:
            anomaly_flags.append('extreme_humidity')
        
        self.anomaly_flag = len(anomaly_flags) > 0
    
    def to_dict(self) -> Dict:
        """
        Convertit l'objet en dictionnaire pour export
        
        Returns:
            Dict: Représentation dictionnaire complète
        """
        return {
            'building_id': self.building_id,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, pd.Timestamp) else str(self.timestamp),
            'consumption_kwh': round(self.consumption_kwh, 4),
            'temperature_c': round(self.temperature_c, 2),
            'humidity': round(self.humidity, 3),
            'heat_index': round(self.heat_index, 2),
            'building_type': self.building_type,
            'zone_name': self.zone_name,
            'hour': self.hour,
            'day_of_week': self.day_of_week,
            'month': self.month,
            'is_weekend': self.is_weekend,
            'is_business_hour': self.is_business_hour,
            'data_quality_score': round(self.data_quality_score, 3) if self.data_quality_score else None,
            'anomaly_flag': self.anomaly_flag
        }
    
    def to_pandas_row(self) -> Dict:
        """
        Convertit en format optimisé pour pandas DataFrame
        
        Returns:
            Dict: Données optimisées pour DataFrame
        """
        return {
            'building_id': self.building_id,
            'timestamp': self.timestamp,
            'consumption_kwh': self.consumption_kwh,
            'temperature_c': self.temperature_c,
            'humidity': self.humidity,
            'heat_index': self.heat_index,
            'building_type': self.building_type,
            'zone_name': self.zone_name,
            'hour': self.hour,
            'day_of_week': self.day_of_week,
            'month': self.month,
            'is_weekend': self.is_weekend,
            'is_business_hour': self.is_business_hour,
            'data_quality_score': self.data_quality_score,
            'anomaly_flag': self.anomaly_flag
        }
    
    def get_consumption_category(self) -> str:
        """
        Catégorise le niveau de consommation
        
        Returns:
            str: Catégorie de consommation
        """
        if self.consumption_kwh < 0:
            return 'invalid'
        elif self.consumption_kwh == 0:
            return 'zero'
        elif self.consumption_kwh < 1:
            return 'very_low'
        elif self.consumption_kwh < 5:
            return 'low'
        elif self.consumption_kwh < 15:
            return 'normal'
        elif self.consumption_kwh < 30:
            return 'high'
        else:
            return 'very_high'
    
    def get_climate_stress_level(self) -> str:
        """
        Évalue le niveau de stress climatique
        
        Returns:
            str: Niveau de stress climatique
        """
        if self.heat_index < 27:
            return 'comfortable'
        elif self.heat_index < 32:
            return 'caution'
        elif self.heat_index < 40:
            return 'extreme_caution'
        elif self.heat_index < 52:
            return 'danger'
        else:
            return 'extreme_danger'
    
    def is_peak_hour(self) -> bool:
        """
        Détermine si c'est une heure de pic selon le type de bâtiment
        
        Returns:
            bool: True si heure de pic
        """
        if self.hour is None:
            return False
        
        # Heures de pic par type de bâtiment
        peak_hours = {
            'residential': [7, 8, 18, 19, 20, 21],
            'commercial': [10, 11, 12, 13, 14, 15, 16],
            'office': [9, 10, 11, 14, 15, 16],
            'industrial': [8, 9, 10, 11, 12, 13, 14, 15],
            'hospital': list(range(24)),  # Toujours actif
            'school': [8, 9, 10, 11, 12, 13, 14, 15]
        }
        
        building_peaks = peak_hours.get(self.building_type, [])
        return self.hour in building_peaks
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TimeSeries':
        """
        Crée une instance TimeSeries à partir d'un dictionnaire
        
        Args:
            data: Dictionnaire contenant les données
            
        Returns:
            TimeSeries: Instance créée
        """
        # Conversion du timestamp
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        elif not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)
        
        return cls(
            building_id=data.get('building_id', ''),
            timestamp=timestamp,
            consumption_kwh=float(data.get('consumption_kwh', 0)),
            temperature_c=float(data.get('temperature_c', 28)),
            humidity=float(data.get('humidity', 0.8)),
            heat_index=float(data.get('heat_index', 30)),
            building_type=data.get('building_type', 'residential'),
            zone_name=data.get('zone_name')
        )


# ==============================================================================
# FONCTIONS UTILITAIRES POUR SÉRIES TEMPORELLES
# ==============================================================================

def create_timeseries_from_lists(
    building_ids: list,
    timestamps: list,
    consumptions: list,
    **kwargs
) -> list:
    """
    Crée une liste de TimeSeries à partir de listes de valeurs
    
    Args:
        building_ids: Liste des IDs de bâtiments
        timestamps: Liste des timestamps
        consumptions: Liste des consommations
        **kwargs: Autres paramètres (température, humidité, etc.)
        
    Returns:
        list: Liste d'objets TimeSeries
    """
    if not (len(building_ids) == len(timestamps) == len(consumptions)):
        raise ValueError("Les listes doivent avoir la même longueur")
    
    timeseries_list = []
    
    for i in range(len(building_ids)):
        # Récupération des valeurs par défaut
        temperature = kwargs.get('temperatures', [28] * len(building_ids))[i]
        humidity = kwargs.get('humidities', [0.8] * len(building_ids))[i]
        heat_index = kwargs.get('heat_indices', [30] * len(building_ids))[i]
        building_type = kwargs.get('building_types', ['residential'] * len(building_ids))[i]
        zone_name = kwargs.get('zone_names', [None] * len(building_ids))[i]
        
        ts = TimeSeries(
            building_id=building_ids[i],
            timestamp=pd.to_datetime(timestamps[i]),
            consumption_kwh=consumptions[i],
            temperature_c=temperature,
            humidity=humidity,
            heat_index=heat_index,
            building_type=building_type,
            zone_name=zone_name
        )
        
        timeseries_list.append(ts)
    
    return timeseries_list


def timeseries_to_dataframe(timeseries_list: list) -> pd.DataFrame:
    """
    Convertit une liste de TimeSeries en DataFrame pandas optimisé
    
    Args:
        timeseries_list: Liste d'objets TimeSeries
        
    Returns:
        pd.DataFrame: DataFrame optimisé
    """
    if not timeseries_list:
        return pd.DataFrame()
    
    # Conversion en dictionnaires
    data_rows = [ts.to_pandas_row() for ts in timeseries_list]
    
    # Création du DataFrame
    df = pd.DataFrame(data_rows)
    
    # Optimisation des types de données
    df['building_id'] = df['building_id'].astype('category')
    df['building_type'] = df['building_type'].astype('category')
    
    if 'zone_name' in df.columns:
        df['zone_name'] = df['zone_name'].astype('category')
    
    # Optimisation des booléens
    bool_cols = ['is_weekend', 'is_business_hour', 'anomaly_flag']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype('bool')
    
    # Optimisation des entiers
    int_cols = ['hour', 'day_of_week', 'month']
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].astype('int8')
    
    # Index sur timestamp pour optimiser les requêtes temporelles
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
    
    return df


def validate_timeseries_data(timeseries_list: list) -> tuple:
    """
    Valide une liste de données TimeSeries
    
    Args:
        timeseries_list: Liste d'objets TimeSeries
        
    Returns:
        tuple: (données_valides, erreurs, warnings)
    """
    valid_data = []
    errors = []
    warnings = []
    
    for i, ts in enumerate(timeseries_list):
        try:
            # Validations critiques
            if not ts.building_id:
                errors.append(f"Ligne {i}: ID bâtiment manquant")
                continue
            
            if ts.consumption_kwh < 0:
                errors.append(f"Ligne {i}: Consommation négative ({ts.consumption_kwh})")
                continue
            
            if not isinstance(ts.timestamp, pd.Timestamp):
                errors.append(f"Ligne {i}: Timestamp invalide")
                continue
            
            # Validations avec warnings
            if ts.consumption_kwh > 100:
                warnings.append(f"Ligne {i}: Consommation très élevée ({ts.consumption_kwh} kWh)")
            
            if ts.temperature_c < 15 or ts.temperature_c > 45:
                warnings.append(f"Ligne {i}: Température extrême ({ts.temperature_c}°C)")
            
            if ts.humidity < 0.3 or ts.humidity > 1.0:
                warnings.append(f"Ligne {i}: Humidité suspecte ({ts.humidity})")
            
            # Score de qualité faible
            if ts.data_quality_score and ts.data_quality_score < 0.7:
                warnings.append(f"Ligne {i}: Score qualité faible ({ts.data_quality_score:.2f})")
            
            valid_data.append(ts)
            
        except Exception as e:
            errors.append(f"Ligne {i}: Erreur validation ({str(e)})")
    
    return valid_data, errors, warnings


def aggregate_timeseries_by_building(
    timeseries_list: list,
    aggregation: str = 'sum'
) -> dict:
    """
    Agrège les séries temporelles par bâtiment
    
    Args:
        timeseries_list: Liste d'objets TimeSeries
        aggregation: Type d'agrégation ('sum', 'mean', 'max', 'min')
        
    Returns:
        dict: Données agrégées par building_id
    """
    if not timeseries_list:
        return {}
    
    # Conversion en DataFrame pour faciliter l'agrégation
    df = timeseries_to_dataframe(timeseries_list)
    
    # Agrégation selon le type demandé
    agg_functions = {
        'sum': df.groupby('building_id')['consumption_kwh'].sum(),
        'mean': df.groupby('building_id')['consumption_kwh'].mean(),
        'max': df.groupby('building_id')['consumption_kwh'].max(),
        'min': df.groupby('building_id')['consumption_kwh'].min()
    }
    
    if aggregation not in agg_functions:
        raise ValueError(f"Agrégation '{aggregation}' non supportée")
    
    result = agg_functions[aggregation].to_dict()
    
    return result


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du modèle TimeSeries
    import pandas as pd
    
    # Création d'un point temporel de test
    test_ts = TimeSeries(
        building_id='B001',
        timestamp=pd.Timestamp('2024-01-15 14:30:00'),
        consumption_kwh=5.2,
        temperature_c=32.5,
        humidity=0.85,
        heat_index=38.2,
        building_type='residential',
        zone_name='kuala_lumpur'
    )
    
    print("✅ Test TimeSeries créé:")
    print(f"📊 Consommation: {test_ts.consumption_kwh} kWh")
    print(f"🌡️ Température: {test_ts.temperature_c}°C")
    print(f"💧 Humidité: {test_ts.humidity:.1%}")
    print(f"🔥 Index chaleur: {test_ts.heat_index}°C")
    print(f"⏰ Heure de pic: {test_ts.is_peak_hour()}")
    print(f"🎯 Score qualité: {test_ts.data_quality_score:.2f}")
    print(f"⚠️ Anomalie: {test_ts.anomaly_flag}")
    print(f"📈 Catégorie: {test_ts.get_consumption_category()}")
    print(f"🌡️ Stress climatique: {test_ts.get_climate_stress_level()}")
    
    # Test conversion en dictionnaire
    ts_dict = test_ts.to_dict()
    print(f"\n📝 Export dict: {len(ts_dict)} champs")
    
    # Test création à partir de dictionnaire
    test_ts_2 = TimeSeries.from_dict(ts_dict)
    print(f"🔄 Reconstruction: {test_ts_2.consumption_kwh} kWh")
    
    # Test avec liste de TimeSeries
    timestamps = pd.date_range('2024-01-01', periods=24, freq='1H')
    building_ids = ['B001'] * 24
    consumptions = [2.0 + i * 0.5 for i in range(24)]
    
    ts_list = create_timeseries_from_lists(
        building_ids=building_ids,
        timestamps=timestamps,
        consumptions=consumptions,
        temperatures=[28 + i for i in range(24)],
        building_types=['residential'] * 24
    )
    
    print(f"\n📊 Liste créée: {len(ts_list)} points temporels")
    
    # Conversion en DataFrame
    df = timeseries_to_dataframe(ts_list)
    print(f"📋 DataFrame: {len(df)} lignes, {len(df.columns)} colonnes")
    print(f"📈 Consommation moyenne: {df['consumption_kwh'].mean():.2f} kWh")
    
    # Validation
    valid_data, errors, warnings = validate_timeseries_data(ts_list)
    print(f"\n✅ Validation: {len(valid_data)} valides, {len(errors)} erreurs, {len(warnings)} warnings")
    
    # Agrégation
    agg_sum = aggregate_timeseries_by_building(ts_list, 'sum')
    print(f"📊 Agrégation: {agg_sum}")
