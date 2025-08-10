"""
Constantes pour Malaysia Electricity Generator
==============================================

Ce module contient toutes les constantes utilisées dans l'application
pour assurer la cohérence et faciliter la maintenance.
"""

from typing import Dict, List, Tuple

# ==============================================================================
# CONSTANTES GÉOGRAPHIQUES MALAYSIA
# ==============================================================================

# Limites géographiques de Malaysia
MALAYSIA_BOUNDS = {
    'min_lat': 0.5,
    'max_lat': 7.5,
    'min_lon': 99.0,
    'max_lon': 120.0
}

# Zones climatiques Malaysia
MALAYSIA_CLIMATE_ZONES = {
    'tropical_rainforest': {
        'regions': ['Sabah', 'Sarawak', 'Pahang'],
        'avg_temperature': 26,
        'avg_humidity': 0.85,
        'rainfall_mm_year': 2500
    },
    'tropical_monsoon': {
        'regions': ['Penang', 'Kedah', 'Perlis'],
        'avg_temperature': 28,
        'avg_humidity': 0.80,
        'rainfall_mm_year': 2000
    },
    'tropical_savanna': {
        'regions': ['Johor', 'Selangor', 'Kuala Lumpur'],
        'avg_temperature': 27,
        'avg_humidity': 0.82,
        'rainfall_mm_year': 2200
    }
}

# Principales villes Malaysia avec métadonnées
MALAYSIA_MAJOR_CITIES = {
    'kuala_lumpur': {
        'name': 'Kuala Lumpur',
        'state': 'Federal Territory',
        'coordinates': (3.1390, 101.6869),
        'population': 1800000,
        'area_km2': 243,
        'timezone': 'Asia/Kuala_Lumpur',
        'osm_relation_id': 1124314
    },
    'george_town': {
        'name': 'George Town',
        'state': 'Penang',
        'coordinates': (5.4164, 100.3327),
        'population': 720000,
        'area_km2': 306,
        'timezone': 'Asia/Kuala_Lumpur',
        'osm_relation_id': 1116080
    },
    'johor_bahru': {
        'name': 'Johor Bahru',
        'state': 'Johor',
        'coordinates': (1.4927, 103.7414),
        'population': 500000,
        'area_km2': 220,
        'timezone': 'Asia/Kuala_Lumpur',
        'osm_relation_id': 1116268
    },
    'ipoh': {
        'name': 'Ipoh',
        'state': 'Perak',
        'coordinates': (4.5975, 101.0901),
        'population': 350000,
        'area_km2': 130,
        'timezone': 'Asia/Kuala_Lumpur',
        'osm_relation_id': 1116269
    },
    'shah_alam': {
        'name': 'Shah Alam',
        'state': 'Selangor',
        'coordinates': (3.0733, 101.5185),
        'population': 290000,
        'area_km2': 290,
        'timezone': 'Asia/Kuala_Lumpur',
        'osm_relation_id': 1116270
    }
}

# États de Malaysia
MALAYSIA_STATES = [
    'Johor', 'Kedah', 'Kelantan', 'Malacca', 'Negeri Sembilan',
    'Pahang', 'Penang', 'Perak', 'Perlis', 'Sabah', 'Sarawak',
    'Selangor', 'Terengganu', 'Federal Territory of Kuala Lumpur',
    'Federal Territory of Labuan', 'Federal Territory of Putrajaya'
]


# ==============================================================================
# TYPES DE BÂTIMENTS
# ==============================================================================

# Types de bâtiments supportés
BUILDING_TYPES = [
    'residential',
    'commercial', 
    'office',
    'industrial',
    'hospital',
    'school',
    'hotel',
    'warehouse',
    'retail',
    'mixed_use',
    'religious',
    'government',
    'sports',
    'transportation'
]

# Catégories de bâtiments
BUILDING_CATEGORIES = {
    'residential': {
        'types': ['residential', 'house', 'apartment', 'detached', 'terrace'],
        'base_consumption_kwh_m2_day': 0.15,
        'peak_multiplier': 2.0,
        'operating_hours': (0, 24),
        'weekend_factor': 1.2
    },
    'commercial': {
        'types': ['commercial', 'retail', 'shop', 'mall'],
        'base_consumption_kwh_m2_day': 0.25,
        'peak_multiplier': 2.5,
        'operating_hours': (8, 22),
        'weekend_factor': 0.8
    },
    'office': {
        'types': ['office'],
        'base_consumption_kwh_m2_day': 0.30,
        'peak_multiplier': 2.0,
        'operating_hours': (8, 18),
        'weekend_factor': 0.3
    },
    'industrial': {
        'types': ['industrial', 'factory', 'warehouse', 'manufacturing'],
        'base_consumption_kwh_m2_day': 0.45,
        'peak_multiplier': 1.5,
        'operating_hours': (6, 22),
        'weekend_factor': 0.7
    },
    'institutional': {
        'types': ['hospital', 'school', 'university', 'government'],
        'base_consumption_kwh_m2_day': 0.35,
        'peak_multiplier': 1.8,
        'operating_hours': (6, 22),
        'weekend_factor': 0.6
    }
}

# Distributions par zone urbaine/rurale
URBAN_BUILDING_DISTRIBUTION = {
    'residential': 0.65,
    'commercial': 0.15,
    'office': 0.08,
    'industrial': 0.05,
    'institutional': 0.04,
    'mixed_use': 0.03
}

RURAL_BUILDING_DISTRIBUTION = {
    'residential': 0.80,
    'agricultural': 0.10,
    'commercial': 0.05,
    'industrial': 0.03,
    'institutional': 0.02
}


# ==============================================================================
# PARAMÈTRES DE GÉNÉRATION
# ==============================================================================

# Fréquences d'échantillonnage supportées
SUPPORTED_FREQUENCIES = {
    '15T': '15 minutes',
    '30T': '30 minutes',
    '1H': '1 heure',
    '3H': '3 heures',
    'D': 'Quotidien'
}

# Valeurs par défaut
DEFAULT_VALUES = {
    'start_date': '2024-01-01',
    'end_date': '2024-01-31',
    'frequency': '30T',
    'num_buildings': 50,
    'surface_area_m2': 150,
    'energy_efficiency_rating': 'C',
    'base_temperature': 28,
    'humidity': 0.8,
    'timezone': 'Asia/Kuala_Lumpur'
}

# Limites de génération
GENERATION_LIMITS = {
    'min_buildings': 1,
    'max_buildings': 10000,
    'min_days': 1,
    'max_days': 365,
    'min_surface_m2': 10,
    'max_surface_m2': 100000,
    'min_consumption_kwh': 0.001,
    'max_consumption_kwh': 1000
}

# Facteurs climatiques Malaysia
MALAYSIA_CLIMATE_FACTORS = {
    'base_temperature': 28,
    'humidity_range': (0.7, 0.9),
    'monsoon_months': [11, 12, 1, 2],
    'dry_months': [6, 7, 8],
    'peak_cooling_hours': [12, 13, 14, 15, 16],
    'temperature_variation': {
        'daily': 8,  # Variation quotidienne en °C
        'seasonal': 3,  # Variation saisonnière en °C
        'hourly_pattern': {
            0: -3, 1: -3, 2: -3, 3: -3, 4: -2, 5: -2,
            6: -1, 7: 0, 8: 1, 9: 2, 10: 3, 11: 4,
            12: 5, 13: 5, 14: 5, 15: 4, 16: 3, 17: 2,
            18: 1, 19: 0, 20: -1, 21: -1, 22: -2, 23: -2
        }
    }
}


# ==============================================================================
# QUALITÉ ET VALIDATION
# ==============================================================================

# Seuils de qualité des données
QUALITY_THRESHOLDS = {
    'excellent': 90,
    'good': 75,
    'acceptable': 60,
    'poor': 40,
    'critical': 20
}

# Seuils d'anomalies
ANOMALY_THRESHOLDS = {
    'consumption_negative': True,  # Consommation négative = anomalie
    'consumption_zero_consecutive': 10,  # Plus de 10h consécutives à 0
    'consumption_extreme_multiplier': 10,  # Plus de 10x la moyenne
    'temperature_range': (10, 50),  # Température hors 10-50°C
    'humidity_range': (0.2, 1.0),  # Humidité hors 20-100%
    'coordinate_precision': 6  # Précision coordonnées en décimales
}

# Classes d'efficacité énergétique
ENERGY_EFFICIENCY_CLASSES = {
    'A': {'factor': 0.7, 'description': 'Très efficace'},
    'B': {'factor': 0.85, 'description': 'Efficace'},
    'C': {'factor': 1.0, 'description': 'Standard'},
    'D': {'factor': 1.15, 'description': 'Peu efficace'},
    'E': {'factor': 1.3, 'description': 'Inefficace'}
}


# ==============================================================================
# FORMATS ET EXPORT
# ==============================================================================

# Formats de fichiers supportés
SUPPORTED_EXPORT_FORMATS = {
    'csv': {
        'extension': '.csv',
        'mime_type': 'text/csv',
        'description': 'Comma Separated Values',
        'compression': False,
        'max_size_mb': 500
    },
    'parquet': {
        'extension': '.parquet',
        'mime_type': 'application/octet-stream',
        'description': 'Apache Parquet',
        'compression': True,
        'max_size_mb': 2000
    },
    'xlsx': {
        'extension': '.xlsx',
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'description': 'Microsoft Excel',
        'compression': True,
        'max_size_mb': 100
    },
    'json': {
        'extension': '.json',
        'mime_type': 'application/json',
        'description': 'JavaScript Object Notation',
        'compression': False,
        'max_size_mb': 200
    }
}

# Configuration CSV
CSV_CONFIG = {
    'separator': ',',
    'encoding': 'utf-8',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'float_format': '%.4f',
    'decimal': '.',
    'thousands': None
}

# Configuration Parquet
PARQUET_CONFIG = {
    'engine': 'pyarrow',
    'compression': 'snappy',
    'row_group_size': 50000,
    'use_dictionary': True
}


# ==============================================================================
# MESSAGES ET TEXTES
# ==============================================================================

# Messages d'erreur standardisés
ERROR_MESSAGES = {
    'invalid_coordinates': "Coordonnées invalides pour Malaysia",
    'invalid_building_type': "Type de bâtiment non reconnu",
    'invalid_date_range': "Plage de dates invalide",
    'invalid_frequency': "Fréquence non supportée",
    'file_too_large': "Fichier trop volumineux",
    'missing_required_field': "Champ requis manquant",
    'data_inconsistent': "Données incohérentes détectées",
    'generation_failed': "Échec de la génération",
    'export_failed': "Échec de l'export",
    'osm_connection_failed': "Connexion OSM échouée",
    'validation_failed': "Validation des données échouée"
}

# Messages de succès
SUCCESS_MESSAGES = {
    'data_generated': "Données générées avec succès",
    'data_exported': "Données exportées avec succès",
    'buildings_loaded': "Bâtiments chargés avec succès",
    'validation_passed': "Validation réussie",
    'configuration_saved': "Configuration sauvegardée",
    'cache_cleared': "Cache vidé avec succès"
}

# Messages d'information
INFO_MESSAGES = {
    'processing': "Traitement en cours...",
    'loading_osm': "Chargement des données OSM...",
    'generating_data': "Génération des données électriques...",
    'exporting_data': "Export des données...",
    'validating_data': "Validation des données...",
    'optimizing_performance': "Optimisation des performances..."
}


# ==============================================================================
# CONFIGURATION API ET SERVICES
# ==============================================================================

# URLs et endpoints
API_ENDPOINTS = {
    'overpass_primary': 'https://overpass-api.de/api/interpreter',
    'overpass_backup': 'https://overpass.kumi.systems/api/interpreter',
    'nominatim': 'https://nominatim.openstreetmap.org/search',
    'weather_api': 'https://api.openweathermap.org/data/2.5'
}

# Timeouts et retry
REQUEST_CONFIG = {
    'timeout_seconds': 300,
    'max_retries': 3,
    'retry_delay': 2,
    'backoff_factor': 2,
    'connection_timeout': 30,
    'read_timeout': 300
}

# Headers HTTP standard
HTTP_HEADERS = {
    'User-Agent': 'Malaysia-Electricity-Generator/2.0 (OpenStreetMap Data Analysis)',
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-cache'
}


# ==============================================================================
# PATTERNS ET EXPRESSIONS RÉGULIÈRES
# ==============================================================================

# Patterns de validation
VALIDATION_PATTERNS = {
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,},
    'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12},
    'date_iso': r'^\d{4}-\d{2}-\d{2},
    'datetime_iso': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
    'filename_safe': r'^[a-zA-Z0-9._-]+,
    'building_id': r'^[A-Z][A-Z0-9]{2}[A-Z0-9]{6},
    'zone_name': r'^[a-z][a-z0-9_]{1,50}
}

# Caractères interdits dans les noms de fichiers
FORBIDDEN_FILENAME_CHARS = '<>:"/\\|?*'

# Extensions de fichiers autorisées
ALLOWED_FILE_EXTENSIONS = ['.csv', '.parquet', '.xlsx', '.json', '.txt']


# ==============================================================================
# CONSTANTES MATHEMATIQUES ET SCIENTIFIQUES
# ==============================================================================

# Constantes physiques
PHYSICAL_CONSTANTS = {
    'earth_radius_km': 6371.0,
    'degrees_to_radians': 0.017453292519943295,
    'radians_to_degrees': 57.29577951308232,
    'meters_per_degree_lat': 111000,
    'seconds_per_day': 86400,
    'minutes_per_hour': 60,
    'hours_per_day': 24
}

# Facteurs de conversion
CONVERSION_FACTORS = {
    'kwh_to_wh': 1000,
    'wh_to_kwh': 0.001,
    'celsius_to_kelvin': 273.15,
    'kelvin_to_celsius': -273.15,
    'bytes_to_kb': 1024,
    'kb_to_mb': 1024,
    'mb_to_gb': 1024
}

# Préfixes de taille
SIZE_PREFIXES = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


# ==============================================================================
# CONFIGURATION PERFORMANCE
# ==============================================================================

# Limites de performance
PERFORMANCE_LIMITS = {
    'max_memory_mb': 2048,
    'max_processing_time_minutes': 30,
    'batch_size_buildings': 1000,
    'batch_size_timeseries': 10000,
    'chunk_size_export': 50000,
    'cache_size_items': 1000,
    'cache_ttl_seconds': 3600
}

# Seuils d'alerte performance
PERFORMANCE_ALERTS = {
    'slow_query_seconds': 10,
    'large_dataset_mb': 100,
    'high_memory_usage_percent': 80,
    'many_buildings_count': 5000,
    'long_timeseries_days': 90
}


# ==============================================================================
# MÉTADONNÉES APPLICATION
# ==============================================================================

# Informations sur l'application
APPLICATION_INFO = {
    'name': 'Malaysia Electricity Data Generator',
    'version': '2.0.0',
    'description': 'Générateur de données électriques réalistes pour Malaysia',
    'author': 'Malaysia Energy Research Team',
    'license': 'MIT',
    'repository': 'https://github.com/malaysia-energy/electricity-generator',
    'documentation': 'https://docs.malaysia-energy.org/generator',
    'support_email': 'support@malaysia-energy.org'
}

# Compatibilité
COMPATIBILITY = {
    'python_min_version': '3.8',
    'python_max_version': '3.12',
    'pandas_min_version': '1.5.0',
    'numpy_min_version': '1.20.0',
    'supported_os': ['Windows', 'Linux', 'macOS'],
    'required_ram_mb': 1024,
    'recommended_ram_mb': 4096
}


# ==============================================================================
# CONFIGURATION LOGGING
# ==============================================================================

# Niveaux de log
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Formats de log
LOG_FORMATS = {
    'simple': '%(levelname)s - %(message)s',
    'standard': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'detailed': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    'json': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
}

# Configuration rotation des logs
LOG_ROTATION = {
    'max_size_mb': 10,
    'backup_count': 5,
    'rotation_interval': 'midnight',
    'compression': True
}


# ==============================================================================
# TEMPLATES ET EXEMPLES
# ==============================================================================

# Template de bâtiment par défaut
DEFAULT_BUILDING_TEMPLATE = {
    'building_id': 'GENERATED_ID',
    'building_type': 'residential',
    'latitude': 3.1390,
    'longitude': 101.6869,
    'surface_area_m2': 150.0,
    'floors_count': 1,
    'energy_efficiency_rating': 'C',
    'has_air_conditioning': True,
    'has_solar_panels': False,
    'occupancy_type': 'standard',
    'operating_hours_start': 6,
    'operating_hours_end': 22,
    'weekends_active': True
}

# Template de série temporelle par défaut
DEFAULT_TIMESERIES_TEMPLATE = {
    'building_id': 'BUILDING_ID',
    'timestamp': '2024-01-01T00:00:00',
    'consumption_kwh': 0.0,
    'temperature_c': 28.0,
    'humidity': 0.8,
    'heat_index': 30.0,
    'building_type': 'residential',
    'zone_name': 'kuala_lumpur'
}


# ==============================================================================
# EXPORT ET ACCÈS
# ==============================================================================

# Liste des constantes exportées
__all__ = [
    # Géographie
    'MALAYSIA_BOUNDS',
    'MALAYSIA_CLIMATE_ZONES', 
    'MALAYSIA_MAJOR_CITIES',
    'MALAYSIA_STATES',
    
    # Bâtiments
    'BUILDING_TYPES',
    'BUILDING_CATEGORIES',
    'URBAN_BUILDING_DISTRIBUTION',
    'RURAL_BUILDING_DISTRIBUTION',
    
    # Génération
    'SUPPORTED_FREQUENCIES',
    'DEFAULT_VALUES',
    'GENERATION_LIMITS',
    'MALAYSIA_CLIMATE_FACTORS',
    
    # Qualité
    'QUALITY_THRESHOLDS',
    'ANOMALY_THRESHOLDS',
    'ENERGY_EFFICIENCY_CLASSES',
    
    # Export
    'SUPPORTED_EXPORT_FORMATS',
    'CSV_CONFIG',
    'PARQUET_CONFIG',
    
    # Messages
    'ERROR_MESSAGES',
    'SUCCESS_MESSAGES',
    'INFO_MESSAGES',
    
    # API
    'API_ENDPOINTS',
    'REQUEST_CONFIG',
    'HTTP_HEADERS',
    
    # Validation
    'VALIDATION_PATTERNS',
    'FORBIDDEN_FILENAME_CHARS',
    'ALLOWED_FILE_EXTENSIONS',
    
    # Performance
    'PERFORMANCE_LIMITS',
    'PERFORMANCE_ALERTS',
    
    # Application
    'APPLICATION_INFO',
    'COMPATIBILITY',
    
    # Templates
    'DEFAULT_BUILDING_TEMPLATE',
    'DEFAULT_TIMESERIES_TEMPLATE'
]


# ==============================================================================
# FONCTION D'ACCÈS RAPIDE
# ==============================================================================

def get_constant(category: str, key: str = None):
    """
    Fonction d'accès rapide aux constantes
    
    Args:
        category: Catégorie de constante
        key: Clé spécifique (optionnel)
        
    Returns:
        Constante demandée ou dictionnaire de catégorie
    """
    categories = {
        'malaysia': {
            'bounds': MALAYSIA_BOUNDS,
            'cities': MALAYSIA_MAJOR_CITIES,
            'states': MALAYSIA_STATES,
            'climate': MALAYSIA_CLIMATE_FACTORS
        },
        'buildings': {
            'types': BUILDING_TYPES,
            'categories': BUILDING_CATEGORIES,
            'urban_distribution': URBAN_BUILDING_DISTRIBUTION,
            'rural_distribution': RURAL_BUILDING_DISTRIBUTION
        },
        'generation': {
            'frequencies': SUPPORTED_FREQUENCIES,
            'defaults': DEFAULT_VALUES,
            'limits': GENERATION_LIMITS
        },
        'export': {
            'formats': SUPPORTED_EXPORT_FORMATS,
            'csv': CSV_CONFIG,
            'parquet': PARQUET_CONFIG
        },
        'messages': {
            'errors': ERROR_MESSAGES,
            'success': SUCCESS_MESSAGES,
            'info': INFO_MESSAGES
        }
    }
    
    if category not in categories:
        return None
    
    if key is None:
        return categories[category]
    
    return categories[category].get(key)


if __name__ == '__main__':
    # Test des constantes
    print("🧪 Test des constantes:")
    print(f"Types de bâtiments: {len(BUILDING_TYPES)}")
    print(f"Villes principales: {len(MALAYSIA_MAJOR_CITIES)}")
    print(f"Formats export: {len(SUPPORTED_EXPORT_FORMATS)}")
    print(f"Messages d'erreur: {len(ERROR_MESSAGES)}")
    
    # Test fonction d'accès
    bounds = get_constant('malaysia', 'bounds')
    print(f"Limites Malaysia: {bounds}")
    
    print("✅ Tests terminés")
