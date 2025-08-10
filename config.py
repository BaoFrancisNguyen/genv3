"""
Configuration centralisée pour le générateur de données électriques Malaysia
===========================================================================

Ce fichier contient toutes les constantes et paramètres de configuration
pour assurer une maintenance facile et éviter la duplication.
"""

import os
from datetime import datetime
from typing import Dict, List


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
    MAX_BUILDINGS = 10000000
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

# Configuration complète des zones Malaysia
# À ajouter dans config.py

class MalaysiaZones:
    """Configuration complète des zones et divisions administratives de Malaysia"""
    
    # MALAYSIA ENTIÈRE
    COUNTRY = {
        'malaysia': {
            'name': 'Malaysia (Pays entier)',
            'type': 'country',
            'population': 32700000,
            'area_km2': 330803,
            'estimated_buildings': 4500000,
            'bbox': [99.0, 0.8, 119.3, 7.4],
            'osm_relation_id': 2108121,
            'complexity': 'très_élevée',
            'warning': 'Génération très longue - plusieurs heures'
        }
    }
    
    # ÉTATS (STATES)
    STATES = {
        'johor': {
            'name': 'Johor',
            'type': 'state',
            'population': 3800000,
            'area_km2': 19984,
            'estimated_buildings': 520000,
            'bbox': [102.5, 1.2, 104.4, 2.8],
            'osm_relation_id': 2108291,
            'capital': 'Johor Bahru'
        },
        'kedah': {
            'name': 'Kedah',
            'type': 'state',
            'population': 2200000,
            'area_km2': 9500,
            'estimated_buildings': 300000,
            'bbox': [99.6, 5.5, 101.2, 6.7],
            'osm_relation_id': 2108292,
            'capital': 'Alor Setar'
        },
        'kelantan': {
            'name': 'Kelantan',
            'type': 'state',
            'population': 1900000,
            'area_km2': 15099,
            'estimated_buildings': 260000,
            'bbox': [101.2, 4.5, 102.4, 6.2],
            'osm_relation_id': 2108293,
            'capital': 'Kota Bharu'
        },
        'melaka': {
            'name': 'Melaka',
            'type': 'state',
            'population': 950000,
            'area_km2': 1664,
            'estimated_buildings': 130000,
            'bbox': [102.0, 2.0, 102.6, 2.5],
            'osm_relation_id': 2108294,
            'capital': 'Melaka City'
        },
        'negeri_sembilan': {
            'name': 'Negeri Sembilan',
            'type': 'state',
            'population': 1200000,
            'area_km2': 6686,
            'estimated_buildings': 165000,
            'bbox': [101.8, 2.3, 102.8, 3.2],
            'osm_relation_id': 2108295,
            'capital': 'Seremban'
        },
        'pahang': {
            'name': 'Pahang',
            'type': 'state',
            'population': 1700000,
            'area_km2': 35965,
            'estimated_buildings': 235000,
            'bbox': [101.4, 2.8, 104.0, 4.8],
            'osm_relation_id': 2108296,
            'capital': 'Kuantan'
        },
        'penang': {
            'name': 'Penang',
            'type': 'state',
            'population': 1780000,
            'area_km2': 1048,
            'estimated_buildings': 245000,
            'bbox': [100.1, 5.1, 100.6, 5.7],
            'osm_relation_id': 2108297,
            'capital': 'George Town'
        },
        'perak': {
            'name': 'Perak',
            'type': 'state',
            'population': 2500000,
            'area_km2': 21035,
            'estimated_buildings': 345000,
            'bbox': [100.0, 3.6, 101.9, 5.8],
            'osm_relation_id': 2108298,
            'capital': 'Ipoh'
        },
        'perlis': {
            'name': 'Perlis',
            'type': 'state',
            'population': 260000,
            'area_km2': 821,
            'estimated_buildings': 36000,
            'bbox': [100.1, 6.3, 100.6, 6.7],
            'osm_relation_id': 2108299,
            'capital': 'Kangar'
        },
        'sabah': {
            'name': 'Sabah',
            'type': 'state',
            'population': 3400000,
            'area_km2': 73711,
            'estimated_buildings': 470000,
            'bbox': [115.2, 4.0, 119.3, 7.4],
            'osm_relation_id': 2108300,
            'capital': 'Kota Kinabalu'
        },
        'sarawak': {
            'name': 'Sarawak',
            'type': 'state',
            'population': 2800000,
            'area_km2': 124450,
            'estimated_buildings': 385000,
            'bbox': [109.6, 0.8, 115.6, 5.1],
            'osm_relation_id': 2108301,
            'capital': 'Kuching'
        },
        'selangor': {
            'name': 'Selangor',
            'type': 'state',
            'population': 6800000,
            'area_km2': 8104,
            'estimated_buildings': 935000,
            'bbox': [101.0, 2.6, 101.9, 3.8],
            'osm_relation_id': 2108302,
            'capital': 'Shah Alam'
        },
        'terengganu': {
            'name': 'Terengganu',
            'type': 'state',
            'population': 1250000,
            'area_km2': 13035,
            'estimated_buildings': 172000,
            'bbox': [102.5, 4.0, 103.9, 5.8],
            'osm_relation_id': 2108303,
            'capital': 'Kuala Terengganu'
        }
    }
    
    # TERRITOIRES FÉDÉRAUX
    FEDERAL_TERRITORIES = {
        'kuala_lumpur': {
            'name': 'Kuala Lumpur',
            'type': 'federal_territory',
            'population': 1800000,
            'area_km2': 243,
            'estimated_buildings': 285000,
            'bbox': [101.6, 3.05, 101.75, 3.25],
            'osm_relation_id': 1124314
        },
        'putrajaya': {
            'name': 'Putrajaya',
            'type': 'federal_territory',
            'population': 120000,
            'area_km2': 49,
            'estimated_buildings': 15000,
            'bbox': [101.65, 2.9, 101.75, 3.0],
            'osm_relation_id': 1116271
        },
        'labuan': {
            'name': 'Labuan',
            'type': 'federal_territory',
            'population': 100000,
            'area_km2': 91,
            'estimated_buildings': 14000,
            'bbox': [115.2, 5.25, 115.35, 5.35],
            'osm_relation_id': 1116272
        }
    }
    
    # PRINCIPALES VILLES
    MAJOR_CITIES = {
        'kuala_lumpur': {
            'name': 'Kuala Lumpur',
            'state': 'Federal Territory',
            'population': 1800000,
            'area_km2': 243,
            'estimated_buildings': 285000,
            'bbox': [101.6, 3.05, 101.75, 3.25],
            'osm_relation_id': 1124314,
            'importance': 'capitale'
        },
        'george_town': {
            'name': 'George Town',
            'state': 'Penang',
            'population': 720000,
            'area_km2': 306,
            'estimated_buildings': 95000,
            'bbox': [100.25, 5.35, 100.45, 5.55],
            'osm_relation_id': 1116080,
            'importance': 'patrimoine_unesco'
        },
        'johor_bahru': {
            'name': 'Johor Bahru',
            'state': 'Johor',
            'population': 500000,
            'area_km2': 220,
            'estimated_buildings': 85000,
            'bbox': [103.7, 1.45, 103.85, 1.55],
            'osm_relation_id': 1116268,
            'importance': 'frontière_singapour'
        },
        'ipoh': {
            'name': 'Ipoh',
            'state': 'Perak',
            'population': 350000,
            'area_km2': 130,
            'estimated_buildings': 58000,
            'bbox': [101.05, 4.55, 101.15, 4.65],
            'osm_relation_id': 1116269,
            'importance': 'centre_régional'
        },
        'shah_alam': {
            'name': 'Shah Alam',
            'state': 'Selangor',
            'population': 290000,
            'area_km2': 290,
            'estimated_buildings': 75000,
            'bbox': [101.45, 3.05, 101.6, 3.15],
            'osm_relation_id': 1116270,
            'importance': 'capitale_état'
        },
        'kota_kinabalu': {
            'name': 'Kota Kinabalu',
            'state': 'Sabah',
            'population': 650000,
            'area_km2': 351,
            'estimated_buildings': 89000,
            'bbox': [115.9, 5.9, 116.1, 6.1],
            'osm_relation_id': 1116273,
            'importance': 'capitale_sabah'
        },
        'kuching': {
            'name': 'Kuching',
            'state': 'Sarawak',
            'population': 680000,
            'area_km2': 431,
            'estimated_buildings': 94000,
            'bbox': [110.25, 1.5, 110.45, 1.6],
            'osm_relation_id': 1116274,
            'importance': 'capitale_sarawak'
        },
        'petaling_jaya': {
            'name': 'Petaling Jaya',
            'state': 'Selangor',
            'population': 620000,
            'area_km2': 97,
            'estimated_buildings': 125000,
            'bbox': [101.6, 3.1, 101.65, 3.15],
            'osm_relation_id': 1116275,
            'importance': 'banlieue_kl'
        },
        'klang': {
            'name': 'Klang',
            'state': 'Selangor',
            'population': 450000,
            'area_km2': 573,
            'estimated_buildings': 78000,
            'bbox': [101.4, 3.0, 101.5, 3.1],
            'osm_relation_id': 1116276,
            'importance': 'port_principal'
        },
        'kuantan': {
            'name': 'Kuantan',
            'state': 'Pahang',
            'population': 340000,
            'area_km2': 324,
            'estimated_buildings': 55000,
            'bbox': [103.3, 3.8, 103.4, 3.9],
            'osm_relation_id': 1116277,
            'importance': 'côte_est'
        }
    }
    
    # RÉGIONS SPÉCIALES
    SPECIAL_REGIONS = {
        'klang_valley': {
            'name': 'Vallée de Klang',
            'type': 'metropolitan_area',
            'description': 'Zone métropolitaine KL',
            'population': 8000000,
            'area_km2': 2793,
            'estimated_buildings': 1200000,
            'bbox': [101.3, 2.8, 101.8, 3.4],
            'cities': ['kuala_lumpur', 'petaling_jaya', 'shah_alam', 'klang', 'putrajaya']
        },
        'penang_metropolitan': {
            'name': 'Métropole de Penang',
            'type': 'metropolitan_area',
            'description': 'Zone métropolitaine Penang',
            'population': 2500000,
            'area_km2': 1048,
            'estimated_buildings': 350000,
            'bbox': [100.1, 5.1, 100.6, 5.7],
            'cities': ['george_town', 'butterworth', 'seberang_perai']
        },
        'iskandar_malaysia': {
            'name': 'Iskandar Malaysia',
            'type': 'economic_region',
            'description': 'Zone économique spéciale',
            'population': 2200000,
            'area_km2': 2217,
            'estimated_buildings': 310000,
            'bbox': [103.4, 1.2, 103.9, 1.7],
            'cities': ['johor_bahru', 'nusajaya', 'gelang_patah']
        }
    }
    
    # ZONES DE DÉVELOPPEMENT
    DEVELOPMENT_CORRIDORS = {
        'northern_corridor': {
            'name': 'Corridor Nord (NCER)',
            'states': ['perlis', 'kedah', 'penang', 'perak'],
            'population': 6500000,
            'estimated_buildings': 900000,
            'focus': 'agriculture_tourism_manufacturing'
        },
        'east_coast_corridor': {
            'name': 'Corridor Côte Est (ECER)',
            'states': ['kelantan', 'terengganu', 'pahang', 'mersing_johor'],
            'population': 4200000,
            'estimated_buildings': 580000,
            'focus': 'petrochemicals_tourism_agriculture'
        },
        'sabah_development': {
            'name': 'Corridor de Développement Sabah (SDC)',
            'states': ['sabah'],
            'population': 3400000,
            'estimated_buildings': 470000,
            'focus': 'agriculture_tourism_manufacturing'
        },
        'sarawak_corridor': {
            'name': 'Corridor de Développement Sarawak (SCORE)',
            'states': ['sarawak'],
            'population': 2800000,
            'estimated_buildings': 385000,
            'focus': 'energy_heavy_industry'
        }
    }
    
    @classmethod
    def get_all_zones(cls) -> Dict:
        """Retourne toutes les zones disponibles"""
        all_zones = {}
        
        # Pays entier
        all_zones.update(cls.COUNTRY)
        
        # États
        all_zones.update(cls.STATES)
        
        # Territoires fédéraux
        all_zones.update(cls.FEDERAL_TERRITORIES)
        
        # Villes principales
        all_zones.update(cls.MAJOR_CITIES)
        
        # Régions spéciales
        all_zones.update(cls.SPECIAL_REGIONS)
        
        return all_zones
    
    @classmethod
    def get_zones_by_type(cls, zone_type: str) -> Dict:
        """Retourne les zones d'un type spécifique"""
        type_mapping = {
            'country': cls.COUNTRY,
            'state': cls.STATES,
            'federal_territory': cls.FEDERAL_TERRITORIES,
            'city': cls.MAJOR_CITIES,
            'special': cls.SPECIAL_REGIONS
        }
        
        return type_mapping.get(zone_type, {})
    
    @classmethod
    def get_zone_hierarchy(cls) -> Dict:
        """Retourne la hiérarchie administrative"""
        return {
            'country': {
                'malaysia': {
                    'states': list(cls.STATES.keys()),
                    'federal_territories': list(cls.FEDERAL_TERRITORIES.keys()),
                    'major_cities': list(cls.MAJOR_CITIES.keys())
                }
            }
        }

# Mise à jour pour la compatibilité
MALAYSIA_ZONES = MalaysiaZones()


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
