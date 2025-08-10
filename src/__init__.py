# src/__init__.py
"""
Package principal du générateur de données électriques Malaysia
==============================================================

Ce package contient tous les modules nécessaires pour générer
des données électriques réalistes pour les bâtiments de Malaysia.
"""

__version__ = '2.0.0'
__author__ = 'Malaysia Energy Research Team'

# Imports principaux pour faciliter l'accès
from .core.generator import ElectricityDataGenerator
from .core.osm_handler import OSMHandler
from .core.data_exporter import DataExporter
from .models.building import Building
from .models.timeseries import TimeSeries

__all__ = [
    'ElectricityDataGenerator',
    'OSMHandler', 
    'DataExporter',
    'Building',
    'TimeSeries'
]