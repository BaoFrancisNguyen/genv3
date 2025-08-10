"""
Configuration centralisée pour le générateur de données électriques Malaysia
===========================================================================

Ce fichier contient toutes les constantes et paramètres de configuration
pour assurer une maintenance facile et éviter la duplication.
"""

import os
from datetime import datetime

# ==============================================================================
# CONFIGURATION GÉNÉRALE DE L'APPLICATION
# ==============================================================================

class AppConfig:
    """Configuration principale de l'application Flask"""
    
    # Configuration Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Dossiers de l'application
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    EXPORTS_DIR = os.path.join(PROJECT_ROOT, 'exports')
    LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    
    # Création automatique des dossiers
    @classmethod
    def create_directories(cls):
        """Crée les dossiers nécessaires s'ils n'existent pas"""
        for directory in [cls.EXPORTS_DIR, cls.LOGS_DIR, cls.DATA_DIR]:
            os.makedirs(directory, exist_ok=True)


# ==============================================================================
# CONFIGURATION OPENSTREETMAP (OSM)
# ==============================================================================

class OSMConfig:
    """Configuration pour les requêtes OpenStreetMap"""
    
    # API Overpass pour les requêtes OSM
    OVERPASS_API_URL = 'https://overpass-api.de/api/interpreter'
    OVERPASS_BACKUP_URL = 'https://overpass.kumi.systems/api/interpreter'
    
    # Paramètres de requête
    TIMEOUT_SECONDS = 300  # 5 minutes timeout
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # secondes entre les tentatives
    
    # Limites de sécurité
    MAX_BUILDINGS_PER_QUERY = 100000
    MAX_AREA_SIZE_KM2 = 500  # taille maximale de zone en km²
    
    # Types de bâtiments OSM à inclure
    BUILDING_TYPES = [
        'residential', 'commercial', 'office', 'retail', 'industrial',
        'hospital', 'school', 'university', 'hotel', 'apartment',
        'house', 'detached', 'terrace', 'warehouse', 'factory'
    ]


# ==============================================================================
# CONFIGURATION GÉNÉRATION DE DONNÉES ÉLECTRIQUES
# ==============================================================================

class GenerationConfig:
    """Configuration pour la génération des données électriques"""
    
    # Paramètres par défaut
    DEFAULT_START_DATE = '2024-01-01'
    DEFAULT_END_DATE = '2024-01-31'
    DEFAULT_FREQUENCY = '30T'  # 30 minutes
    DEFAULT_NUM_BUILDINGS = 50
    
    # Fréquences supportées
    SUPPORTED_FREQUENCIES = {
        '15T': '15 minutes',
        '30T': '30 minutes', 
        '1H': '1 heure',
        '3H': '3 heures',
        'D': 'Quotidien'
    }
    
    # Limites de génération
    MAX_BUILDINGS = 10000
    MAX_DAYS = 365
    MIN_BUILDINGS = 1
    MIN_DAYS = 1
    
    # Facteurs climatiques Malaysia
    MALAYSIA_CLIMATE = {
        'base_temperature': 28,  # °C température moyenne
        'humidity': 0.8,  # humidité relative
        'monsoon_months': [11, 12, 1, 2],  # mois de mousson
        'dry_months': [6, 7, 8],  # mois secs
        'peak_cooling_hours': [12, 13, 14, 15, 16]  # heures de pic climatisation
    }


# ==============================================================================
# CONFIGURATION DES ZONES MALAYSIA
# ==============================================================================

class MalaysiaZones:
    """Configuration des zones et villes de Malaysia"""
    
    # Zones principales avec métadonnées
    MAJOR_ZONES = {
        'kuala_lumpur': {
            'name': 'Kuala Lumpur',
            'state': 'Federal Territory',
            'population': 1800000,
            'area_km2': 243,
            'timezone': 'Asia/Kuala_Lumpur',
            'estimated_buildings': 285000,
            'bbox': [101.6, 3.05, 101.75, 3.25],
            'osm_relation_id': 1124314
        },
        'george_town': {
            'name': 'George Town',
            'state': 'Penang',
            'population': 720000,
            'area_km2': 306,
            'timezone': 'Asia/Kuala_Lumpur',
            'estimated_buildings': 95000,
            'bbox': [100.25, 5.35, 100.45, 5.55],
            'osm_relation_id': 1116080
        },
        'johor_bahru': {
            'name': 'Johor Bahru',
            'state': 'Johor',
            'population': 500000,
            'area_km2': 220,
            'timezone': 'Asia/Kuala_Lumpur',
            'estimated_buildings': 85000,
            'bbox': [103.7, 1.45, 103.85, 1.55],
            'osm_relation_id': 1116268
        }
    }
    
    # Types de bâtiments par zone urbaine
    URBAN_BUILDING_DISTRIBUTION = {
        'residential': 0.65,
        'commercial': 0.15,
        'office': 0.08,
        'industrial': 0.05,
        'institutional': 0.04,
        'mixed_use': 0.03
    }
    
    # Types de bâtiments par zone rurale
    RURAL_BUILDING_DISTRIBUTION = {
        'residential': 0.80,
        'agricultural': 0.10,
        'commercial': 0.05,
        'industrial': 0.03,
        'institutional': 0.02
    }


# ==============================================================================
# CONFIGURATION EXPORT DES DONNÉES
# ==============================================================================

class ExportConfig:
    """Configuration pour l'export des données"""
    
    # Formats supportés
    SUPPORTED_FORMATS = ['csv', 'parquet', 'xlsx', 'json']
    
    # Configuration CSV
    CSV_SEPARATOR = ','
    CSV_ENCODING = 'utf-8'
    CSV_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Configuration Parquet
    PARQUET_COMPRESSION = 'snappy'
    PARQUET_ENGINE = 'pyarrow'
    
    # Noms de fichiers par défaut
    DEFAULT_BUILDINGS_FILENAME = 'buildings_metadata'
    DEFAULT_TIMESERIES_FILENAME = 'electricity_timeseries'
    
    # Préfixes avec timestamp
    @staticmethod
    def get_timestamped_filename(base_name: str, extension: str) -> str:
        """Génère un nom de fichier avec timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}.{extension}"


# ==============================================================================
# CONFIGURATION LOGGING
# ==============================================================================

class LoggingConfig:
    """Configuration pour les logs de l'application"""
    
    # Niveau de log par défaut
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Format des logs
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Fichiers de log
    LOG_FILE = 'generator.log'
    ERROR_LOG_FILE = 'errors.log'
    
    # Rotation des logs
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5


# ==============================================================================
# CONFIGURATION VALIDATION
# ==============================================================================

class ValidationConfig:
    """Configuration pour la validation des données"""
    
    # Seuils de validation
    MIN_CONSUMPTION_KWH = 0.1
    MAX_CONSUMPTION_KWH = 1000.0
    
    # Seuils d'alerte
    ANOMALY_THRESHOLD_STD = 3.0  # nombre d'écarts-types
    HIGH_CONSUMPTION_PERCENTILE = 95
    
    # Validation géographique
    MALAYSIA_BOUNDS = {
        'min_lat': 0.5,
        'max_lat': 7.5,
        'min_lon': 99.0,
        'max_lon': 120.0
    }


# ==============================================================================
# FONCTION D'INITIALISATION
# ==============================================================================

def initialize_config():
    """Initialise la configuration et crée les dossiers nécessaires"""
    AppConfig.create_directories()
    print("✅ Configuration initialisée et dossiers créés")


# ==============================================================================
# VARIABLES GLOBALES D'ACCÈS RAPIDE
# ==============================================================================

# Export des configurations pour accès facile
APP_CONFIG = AppConfig()
OSM_CONFIG = OSMConfig()
GEN_CONFIG = GenerationConfig()
MALAYSIA_ZONES = MalaysiaZones()
EXPORT_CONFIG = ExportConfig()
LOGGING_CONFIG = LoggingConfig()
VALIDATION_CONFIG = ValidationConfig()

# Initialisation automatique
if __name__ == '__main__':
    initialize_config()
