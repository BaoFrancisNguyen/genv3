# src/services/__init__.py
"""
Services métier pour le générateur électrique Malaysia
=====================================================

Ce package contient les services de haut niveau qui orchestrent
les différents composants de l'application:
- OSMService: Service OpenStreetMap
- GenerationService: Service de génération
- ExportService: Service d'export
"""

from .osm_service import OSMService
from .generation_service import GenerationService  
from .export_service import ExportService

__all__ = [
    'OSMService',
    'GenerationService',
    'ExportService'
]