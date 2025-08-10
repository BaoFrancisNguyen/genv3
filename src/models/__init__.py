# src/models/__init__.py
"""
Modèles de données pour le générateur électrique Malaysia
========================================================

Ce package contient les structures de données principales:
- Building: Modèle de bâtiment avec métadonnées
- TimeSeries: Modèle de série temporelle électrique
"""

from .building import Building, create_building_from_coordinates, validate_building_list
from .timeseries import TimeSeries, timeseries_to_dataframe, validate_timeseries_data

__all__ = [
    'Building',
    'create_building_from_coordinates',
    'validate_building_list',
    'TimeSeries',
    'timeseries_to_dataframe',
    'validate_timeseries_data'
]