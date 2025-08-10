"""
Package utilitaires pour Malaysia Electricity Generator
======================================================

Ce package contient les fonctions utilitaires et helpers partagés
dans toute l'application refactorisée.
"""

# Version du package utils
__version__ = '1.0.0'

# Import des modules principaux
from .validators import *
from .helpers import *
from .constants import *

# Fonctions publiques du package
__all__ = [
    # Validators
    'validate_coordinates_malaysia',
    'validate_building_type',
    'validate_date_range',
    'validate_frequency',
    'sanitize_filename',
    'validate_email',
    'validate_json_structure',
    
    # Helpers
    'calculate_distance_km',
    'format_duration',
    'format_file_size',
    'calculate_bbox_area',
    'normalize_building_type',
    'generate_unique_id',
    'safe_float_parse',
    'safe_int_parse',
    'chunk_list',
    'deep_merge_dict',
    
    # Constants
    'MALAYSIA_BOUNDS',
    'BUILDING_TYPES',
    'SUPPORTED_FREQUENCIES',
    'DEFAULT_VALUES',
    'ERROR_MESSAGES',
    'SUCCESS_MESSAGES'
]
