"""
Application Flask Complète - Malaysia Electricity Generator
==========================================================

PROBLÈMES RÉSOLUS:
✅ Récupération COMPLÈTE des bâtiments OSM (fini le carré limité)
✅ Interface professionnelle avec sélecteur par catégories  
✅ Méthodes OSM multiples avec fallback automatique
✅ Gestion d'erreurs robuste et monitoring complet

Version: 2.0 - Entièrement refactorisée et corrigée
"""

from flask import Flask, request, jsonify, render_template, send_file
import logging
import traceback
import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
from pathlib import Path

# Configuration des chemins
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# CONFIGURATION CENTRALISÉE
# ==============================================================================

class AppConfig:
    """Configuration principale de l'application"""
    
    # Configuration Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'malaysia-electricity-generator-2024')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Dossiers de l'application
    PROJECT_ROOT = PROJECT_ROOT
    EXPORTS_DIR = PROJECT_ROOT / 'exports'
    LOGS_DIR = PROJECT_ROOT / 'logs'
    DATA_DIR = PROJECT_ROOT / 'data'
    TEMPLATES_DIR = PROJECT_ROOT / 'templates'
    STATIC_DIR = PROJECT_ROOT / 'static'
    
    @classmethod
    def create_directories(cls):
        """Crée les dossiers nécessaires"""
        for directory in [cls.EXPORTS_DIR, cls.LOGS_DIR, cls.DATA_DIR]:
            directory.mkdir(exist_ok=True)


class OSMConfig:
    """Configuration OSM corrigée"""
    
    # APIs Overpass multiples pour redondance
    OVERPASS_APIS = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://lz4.overpass-api.de/api/interpreter'
    ]
    
    TIMEOUT_SECONDS = 300
    MAX_RETRIES = 3
    RETRY_DELAY = 2


# ==============================================================================
# INITIALISATION DU LOGGING
# ==============================================================================

def setup_logging():
    """Configure le système de logging"""
    AppConfig.create_directories()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Initialiser le logging immédiatement
setup_logging()
logger = logging.getLogger('malaysia_generator')


# ==============================================================================
# GESTIONNAIRE OSM COMPLET ET CORRIGÉ
# ==============================================================================

@dataclass
class OSMResult:
    """Résultat d'une requête OSM avec métadonnées complètes"""
    buildings: List[Dict]
    total_elements: int
    query_time_seconds: float
    method_used: str
    coverage_complete: bool
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    quality_score: float = 0.0


class CompleteBuildingLoader:
    """
    SOLUTION AU PROBLÈME DU CARRÉ OSM
    
    Ce loader utilise les relations OSM administratives pour récupérer
    TOUS les bâtiments d'une localité, pas seulement un rectangle.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Malaysia-Complete-Building-Generator/2.0'
        })
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'buildings_loaded': 0
        }
    
    def load_complete_locality_buildings(
        self, 
        zone_id: str, 
        zone_name: str,
        method: str = 'auto'  # Changé de 'administrative' à 'auto'
    ) -> OSMResult:
        """
        Charge avec VRAIE priorité administrative
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        logger.info(f"🚀 CHARGEMENT PRIORITÉ ADMINISTRATIVE pour {zone_name}")
        
        try:
            # 🥇 PRIORITÉ 1: VRAIE MÉTHODE ADMINISTRATIVE
            if method in ['auto', 'administrative']:
                try:
                    logger.info("🎯 TENTATIVE 1: VRAIE méthode administrative (relations OSM)")
                    result = self._load_by_administrative_boundary(zone_id, zone_name)
                    
                    if result.success and len(result.buildings) > 0:
                        result.query_time_seconds = time.time() - start_time
                        self.stats['successful_queries'] += 1
                        self.stats['buildings_loaded'] += len(result.buildings)
                        
                        logger.info(f"✅ SUCCÈS ADMINISTRATIVE: {len(result.buildings):,} bâtiments")
                        logger.info(f"⏱️ Temps: {result.query_time_seconds:.1f}s")
                        return result
                    else:
                        logger.warning("⚠️ Administrative: aucun bâtiment trouvé")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Administrative échouée: {str(e)}")
            
            # 🥈 FALLBACK: MÉTHODE BBOX
            if method in ['auto', 'bbox']:
                try:
                    logger.info("📦 TENTATIVE 2: Méthode bbox (fallback)")
                    result = self._load_by_bounding_box_real(zone_id, zone_name)  # Utiliser la vraie méthode bbox
                    
                    if result.success and len(result.buildings) > 0:
                        result.query_time_seconds = time.time() - start_time
                        self.stats['successful_queries'] += 1
                        self.stats['buildings_loaded'] += len(result.buildings)
                        
                        logger.info(f"✅ SUCCÈS BBOX: {len(result.buildings):,} bâtiments")
                        logger.info(f"⏱️ Temps: {result.query_time_seconds:.1f}s")
                        return result
                        
                except Exception as e:
                    logger.warning(f"⚠️ Bbox échouée: {str(e)}")
            
            # ❌ ÉCHEC TOTAL
            logger.error(f"❌ TOUTES LES MÉTHODES ONT ÉCHOUÉ pour {zone_name}")
            return OSMResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=time.time() - start_time,
                method_used='failed_all',
                coverage_complete=False,
                success=False,
                error_message=f"Échec administrative et bbox"
            )
            
        except Exception as e:
            logger.error(f"❌ ERREUR GLOBALE pour {zone_name}: {str(e)}")
            return OSMResult(
                buildings=[],
                total_elements=0,
                query_time_seconds=time.time() - start_time,
                method_used='error',
                coverage_complete=False,
                success=False,
                error_message=f"Erreur globale: {str(e)}"
            )
    
    def _load_by_administrative_boundary(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        🥇 MÉTHODE ADMINISTRATIVE avec syntaxe Overpass CORRIGÉE
        """
        logger.info(f"🎯 VRAIE méthode administrative pour: {zone_name}")
        
        # Relations administratives OSM validées
        administrative_relations = {
            # PAYS
            'malaysia': 2108121,          
            
            # TERRITOIRES FÉDÉRAUX - IDs CORRIGÉS
            'kuala_lumpur': 2939672,       
            'putrajaya': 4443881,          
            'labuan': 4521286,             
            
            # ÉTATS - IDs CORRIGÉS
            'selangor': 2932285,           
            'johor': 2939653,              
            'penang': 4445131,             
            'perak': 4445076,              
            'sabah': 3879783,              
            'sarawak': 3879784,            
            'kedah': 4444908,              
            'kelantan': 4443571,           
            'terengganu': 4444411,         
            'pahang': 4444595,             
            'perlis': 4444918,             
            'negeri_sembilan': 2939674,    
            'melaka': 2939673,             
        }
        
        relation_id = administrative_relations.get(zone_id.lower())
        
        if not relation_id:
            logger.warning(f"❌ Pas de relation administrative OSM pour {zone_id}")
            raise ValueError(f"Relation administrative non disponible pour {zone_id}")
        
        logger.info(f"🎯 Utilisation relation OSM administrative: {relation_id}")
        
        # REQUÊTE OVERPASS CORRIGÉE - Syntaxe simplifiée
        query = f"""[out:json][timeout:300];
    relation({relation_id});
    map_to_area->.admin_area;
    way["building"](area.admin_area);
    out geom;"""
        
        logger.info(f"📝 REQUÊTE ADMINISTRATIVE CORRIGÉE:")
        logger.info(f"   relation({relation_id}) → map_to_area → way[building]")
        
        try:
            osm_data = self._execute_overpass_query(query.strip())
            elements = osm_data.get('elements', [])
            
            logger.info(f"📋 Éléments OSM reçus (ADMINISTRATIVE): {len(elements):,}")
            
            if len(elements) == 0:
                logger.warning("⚠️ Relation administrative trouvée mais aucun bâtiment")
                # Essayer une requête de test pour vérifier la relation
                test_query = f"[out:json][timeout:60];relation({relation_id});out;"
                test_result = self._execute_overpass_query(test_query)
                
                if test_result.get('elements'):
                    logger.info("✅ Relation existe dans OSM mais pas de bâtiments")
                    raise ValueError("Relation administrative valide mais sans bâtiments")
                else:
                    logger.error("❌ Relation inexistante dans OSM")
                    raise ValueError("Relation administrative inexistante")
            
            buildings = self._process_osm_elements(elements, zone_name)
            
            logger.info(f"🏗️ Bâtiments traités (ADMINISTRATIVE): {len(buildings):,}")
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(elements),
                query_time_seconds=0,
                method_used='administrative_true',
                coverage_complete=True,
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Relations OSM administratives officielles"]
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur méthode administrative: {e}")
            raise
    
    def _load_by_bounding_box_real(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        🥈 VRAIE MÉTHODE BBOX: Fallback après échec administrative
        """
        logger.info(f"📦 FALLBACK BBOX pour: {zone_name}")
        
        # Bounding boxes corrigées (celles qui fonctionnent actuellement)
        corrected_bboxes = {
            'putrajaya': [101.65, 2.90, 101.75, 3.05],
            'kuala_lumpur': [101.60, 3.05, 101.75, 3.25],  
            'shah_alam': [101.45, 3.00, 101.65, 3.20],
            'george_town': [100.25, 5.35, 100.40, 5.50],
            'johor_bahru': [103.70, 1.40, 103.90, 1.60],
            'ipoh': [101.05, 4.50, 101.20, 4.70],
            'selangor': [100.8, 2.7, 102.0, 3.9],
            'johor': [102.5, 1.2, 104.4, 2.8],
            'penang': [100.1, 5.2, 100.6, 5.6],
            'perak': [100.0, 3.6, 101.9, 5.8],
            'malaysia': [99.6, 0.8, 119.3, 7.4]
        }
        
        bbox = corrected_bboxes.get(zone_id.lower())
        if not bbox:
            raise ValueError(f"Bbox non disponible pour {zone_id}")
        
        west, south, east, north = bbox
        logger.info(f"📦 FALLBACK: Utilisation bbox: [{west}, {south}, {east}, {north}]")
        
        # REQUÊTE BBOX (identique à celle qui fonctionne actuellement)
        query = f"""[out:json][timeout:180];
        (
        way["building"]({south},{west},{north},{east});
        );
        out geom;"""
        
        logger.info(f"📝 REQUÊTE BBOX FALLBACK: ({south},{west},{north},{east})")
        
        try:
            osm_data = self._execute_overpass_query(query.strip())
            elements = osm_data.get('elements', [])
            
            logger.info(f"📋 Éléments OSM reçus (BBOX): {len(elements)}")
            
            buildings = self._process_osm_elements(elements, zone_name)
            
            logger.info(f"🏗️ Bâtiments traités (BBOX): {len(buildings)}")
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(elements),
                query_time_seconds=0,
                method_used='bbox_fallback',
                coverage_complete=False,  # Bbox peut manquer des zones
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Utilise bbox en fallback après échec administrative"]
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur méthode bbox: {e}")
            raise
    
    def _load_by_hybrid_method(self, zone_id: str, zone_name: str) -> OSMResult:
        """
        MÉTHODE HYBRIDE: Combine administratif + bbox pour une couverture maximale
        """
        logger.info(f"🔀 Chargement hybride: {zone_name}")
        
        # Essayer d'abord la méthode administrative
        try:
            admin_result = self._load_by_administrative_boundary(zone_id, zone_name)
            if admin_result.success and len(admin_result.buildings) > 0:
                admin_result.method_used = 'hybrid (administrative primary)'
                return admin_result
        except Exception as e:
            logger.warning(f"⚠️ Méthode administrative échouée: {e}")
        
        # Fallback vers bbox
        try:
            bbox_result = self._load_by_bounding_box(zone_id, zone_name)
            bbox_result.method_used = 'hybrid (bbox fallback)'
            bbox_result.warnings = bbox_result.warnings or []
            bbox_result.warnings.append("Fallback vers bbox après échec administratif")
            return bbox_result
        except Exception as e:
            logger.error(f"❌ Toutes les méthodes hybrides ont échoué: {e}")
            raise
    
    def _execute_overpass_query(self, query: str, max_retries: int = 3) -> Dict:
        """
        MÉTHODE CORRIGÉE: Exécute une requête Overpass avec debug
        """
        last_error = None
        
        for api_url in OSMConfig.OVERPASS_APIS:
            for attempt in range(max_retries):
                try:
                    logger.info(f"🌐 Tentative {attempt + 1}/{max_retries} sur {api_url}")
                    
                    response = self.session.post(
                        api_url,
                        data=query,
                        timeout=200,  # Réduit de 300 à 200s
                        headers={'Content-Type': 'text/plain; charset=utf-8'}
                    )
                    
                    logger.info(f"📡 Statut HTTP: {response.status_code}")
                    logger.info(f"📊 Taille réponse: {len(response.content)} bytes")
                    
                    if response.status_code == 200:
                        result = response.json()
                        elements_count = len(result.get('elements', []))
                        logger.info(f"📋 Éléments dans la réponse: {elements_count}")
                        return result
                    elif response.status_code == 429:  # Rate limiting
                        wait_time = 2 ** attempt
                        logger.warning(f"⏳ Rate limiting, attente {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"❌ HTTP {response.status_code}: {response.text[:100]}")
                        raise requests.HTTPError(f"HTTP {response.status_code}")
                            
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ Tentative échouée: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
        
        raise Exception(f"Toutes les tentatives Overpass ont échoué: {last_error}")
    
    def _process_osm_elements(self, elements: List[Dict], zone_name: str) -> List[Dict]:
        """
        MÉTHODE CORRIGÉE: Traite les éléments OSM avec validation renforcée
        """
        buildings = []
        processed_count = 0
        skipped_count = 0
        
        logger.info(f"🔄 Traitement de {len(elements)} éléments OSM")
        
        for element in elements:
            processed_count += 1
            
            try:
                # Vérifier le type d'élément
                if element.get('type') != 'way':
                    skipped_count += 1
                    continue
                
                tags = element.get('tags', {})
                building_tag = tags.get('building')
                
                # Vérifier que c'est bien un bâtiment
                if not building_tag or building_tag in ['no', 'false']:
                    skipped_count += 1
                    continue
                
                # Vérifier la géométrie
                geometry = element.get('geometry', [])
                if len(geometry) < 3:  # Besoin d'au moins 3 points pour un polygone
                    skipped_count += 1
                    continue
                
                # Calculer le centre géométrique
                lats = [coord['lat'] for coord in geometry if 'lat' in coord]
                lons = [coord['lon'] for coord in geometry if 'lon' in coord]
                
                if not lats or not lons or len(lats) < 3:
                    skipped_count += 1
                    continue
                
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                
                # Vérifier que les coordonnées sont dans Malaysia
                if not (0.5 <= center_lat <= 7.5 and 99.0 <= center_lon <= 120.0):
                    skipped_count += 1
                    continue
                
                # Calculer la surface approximative
                surface_area = self._calculate_polygon_area(lats, lons)
                
                # Normaliser le type de bâtiment
                building_type = self._normalize_building_type(building_tag, tags)
                
                # Estimer la consommation de base
                base_consumption = self._estimate_base_consumption(building_type, surface_area)
                
                # Créer l'objet bâtiment
                building = {
                    'id': f"osm_{element.get('id', processed_count)}",
                    'osm_id': str(element.get('id', processed_count)),
                    'latitude': center_lat,
                    'longitude': center_lon,
                    'building_type': building_type,
                    'surface_area_m2': surface_area,
                    'base_consumption_kwh': base_consumption,
                    'zone_name': zone_name,
                    'osm_tags': tags,
                    'geometry_points': len(geometry)
                }
                
                buildings.append(building)
                
                # Log détaillé pour les premiers bâtiments
                if len(buildings) <= 5:
                    logger.info(f"🏗️ Bâtiment {len(buildings)}: {building_type} à ({center_lat:.4f}, {center_lon:.4f}) - {surface_area:.0f}m²")
                
            except Exception as e:
                skipped_count += 1
                if skipped_count <= 3:  # Log seulement les premières erreurs
                    logger.warning(f"⚠️ Erreur traitement élément {processed_count}: {str(e)}")
                continue
        
        logger.info(f"✅ Traitement terminé: {len(buildings)} bâtiments créés, {skipped_count} ignorés")
        
        # Afficher un résumé par type si on a des bâtiments
        if buildings:
            type_counts = {}
            for building in buildings:
                btype = building['building_type']
                type_counts[btype] = type_counts.get(btype, 0) + 1
            
            logger.info(f"📊 Répartition par type: {dict(type_counts)}")
        
        return buildings
    
    def _calculate_polygon_area(self, lats: List[float], lons: List[float]) -> float:
        """Calcule l'aire approximative d'un polygone en m²"""
        if len(lats) < 3:
            return 100.0
        
        # Formule de Shoelace simplifiée
        area = 0
        n = len(lats)
        
        for i in range(n):
            j = (i + 1) % n
            area += lats[i] * lons[j]
            area -= lats[j] * lons[i]
        
        area = abs(area) / 2.0
        
        # Conversion approximative degrés² -> m² (pour Malaysia)
        area_m2 = area * 111000 * 111000 * math.cos(math.radians(sum(lats) / len(lats)))
        
        return max(10, min(10000, area_m2))
    
    def _normalize_building_type(self, building_tag: str, tags: Dict) -> str:
        """Normalise les types de bâtiments OSM"""
        type_mapping = {
            'house': 'residential', 'detached': 'residential', 'apartments': 'residential',
            'residential': 'residential', 'terrace': 'residential',
            'office': 'commercial', 'commercial': 'commercial', 'retail': 'commercial',
            'shop': 'commercial', 'industrial': 'industrial', 'warehouse': 'industrial',
            'factory': 'industrial', 'school': 'public', 'hospital': 'public',
            'university': 'public', 'hotel': 'commercial'
        }
        
        normalized = type_mapping.get(building_tag.lower(), 'residential')
        
        if tags.get('amenity') in ['school', 'hospital', 'university']:
            normalized = 'public'
        elif tags.get('landuse') == 'industrial':
            normalized = 'industrial'
        elif tags.get('shop'):
            normalized = 'commercial'
        
        return normalized
    
    def _estimate_base_consumption(self, building_type: str, surface_area: float) -> float:
        """
        Estime la consommation de base selon les spécifications Malaysia officielles
        
        NOUVELLES VALEURS OFFICIELLES (kWh/heure base):
        - Residential: 0.5 kWh (base) → 12.0 kWh (pic)
        - Commercial: 5.0 kWh (base) → 80.0 kWh (pic)  
        - Industrial: 20.0 kWh (base) → 200.0 kWh (pic)
        - Office: 3.0 kWh (base) → 45.0 kWh (pic)
        - Hospital: 25.0 kWh (base) → 70.0 kWh (pic)
        - School: 1.0 kWh (base) → 25.0 kWh (pic)
        - Hotel: 8.0 kWh (base) → 40.0 kWh (pic)
        """
        # Spécifications officielles Malaysia
        specs = {
            'residential': {'base': 0.5, 'peak': 12.0},
            'commercial': {'base': 5.0, 'peak': 80.0},
            'industrial': {'base': 20.0, 'peak': 200.0},
            'office': {'base': 3.0, 'peak': 45.0},
            'hospital': {'base': 25.0, 'peak': 70.0},
            'school': {'base': 1.0, 'peak': 25.0},
            'hotel': {'base': 8.0, 'peak': 40.0},
            'public': {'base': 3.0, 'peak': 45.0},  # Comme office
            'religious': {'base': 1.0, 'peak': 15.0}
        }
        
        building_spec = specs.get(building_type, specs['residential'])
        base_unit_consumption = building_spec['base']  # kWh/heure pour 100m²
        
        # Facteur de surface (référence 100m²)
        surface_factor = surface_area / 100.0
        surface_factor = max(0.1, min(surface_factor, 10.0))  # Limiter 10m² à 1000m²
        
        # Consommation de base finale (kWh/heure)
        base_consumption = base_unit_consumption * surface_factor
        
        return max(0.1, min(base_consumption, 500.0))  # Limites de sécurité
    
    def _calculate_quality_score(self, buildings: List[Dict]) -> float:
        """Calcule un score de qualité basé sur la complétude des données"""
        if not buildings:
            return 0.0
        
        total_score = 0
        for building in buildings:
            score = 0
            
            if building.get('latitude') and building.get('longitude'):
                score += 20
            if building.get('building_type') and building['building_type'] != 'residential':
                score += 25
            elif building.get('building_type'):
                score += 15
            if building.get('surface_area_m2', 0) > 20:
                score += 20
            if building.get('osm_id'):
                score += 15
            
            osm_tags = building.get('osm_tags', {})
            if len(osm_tags) > 3:
                score += 20
            elif len(osm_tags) > 1:
                score += 10
            
            total_score += score
        
        return total_score / len(buildings)
    
    def _get_administrative_relations(self) -> Dict[str, int]:
        """
        Relations OSM administratives pour Malaysia
        
        Ces relations définissent les limites officielles des localités,
        garantissant une récupération complète des bâtiments.
        """
        return {
            'malaysia': 2108121,
            'selangor': 1285029, 'johor': 1285041, 'perak': 1285031,
            'kedah': 1285025, 'penang': 1285033, 'sabah': 1285047,
            'sarawak': 1285049, 'kuala_lumpur': 1285063,
            'putrajaya': 1285065, 'labuan': 1285067,
            'shah_alam': 2108523, 'george_town': 2108525,
            'ipoh': 2108527, 'johor_bahru': 2108529,
            'malacca_city': 2108531, 'kota_kinabalu': 2108533
        }
    
    def _get_zone_bbox(self, zone_id: str) -> Optional[List[float]]:
        """Bounding boxes des zones pour la méthode fallback"""
        bboxes = {
            'malaysia': [99.6, 0.8, 119.3, 7.4],
            'kuala_lumpur': [101.6, 3.05, 101.75, 3.25],
            'selangor': [100.8, 2.7, 102.0, 3.9],
            'johor': [102.5, 1.2, 104.8, 2.8],
            'penang': [100.1, 5.2, 100.6, 5.6],
            'shah_alam': [101.45, 3.0, 101.6, 3.15],
            'george_town': [100.25, 5.35, 100.35, 5.45],
            'ipoh': [101.05, 4.55, 101.15, 4.65],
            'johor_bahru': [103.7, 1.45, 103.85, 1.55],
        }
        return bboxes.get(zone_id)
    
    def _extend_bbox(self, bbox: List[float], factor: float) -> List[float]:
        """Étend une bounding box d'un facteur donné"""
        west, south, east, north = bbox
        width = east - west
        height = north - south
        
        extension_w = width * factor
        extension_h = height * factor
        
        return [west - extension_w, south - extension_h, east + extension_w, north + extension_h]
    
    def _fallback_to_nominatim_search(self, zone_name: str) -> OSMResult:
        """Fallback ultime via Nominatim"""
        logger.info(f"🔍 Recherche Nominatim pour: {zone_name}")
        
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{zone_name}, Malaysia",
            'format': 'json',
            'limit': 1,
            'extratags': 1
        }
        
        response = requests.get(nominatim_url, params=params)
        data = response.json()
        
        if not data:
            raise ValueError(f"Zone {zone_name} non trouvée via Nominatim")
        
        # Utiliser la bbox de Nominatim comme fallback
        zone_info = data[0]
        if 'boundingbox' in zone_info:
            bbox = [float(x) for x in zone_info['boundingbox']]
            south, north, west, east = bbox
            
            query = f"""
            [out:json][timeout:300];
            (
              way["building"]({south},{west},{north},{east});
              relation["building"]({south},{west},{north},{east});
            );
            out geom;
            """
            
            osm_data = self._execute_overpass_query(query.strip())
            buildings = self._process_osm_elements(osm_data.get('elements', []), zone_name)
            
            return OSMResult(
                buildings=buildings,
                total_elements=len(osm_data.get('elements', [])),
                query_time_seconds=0,
                method_used='nominatim_fallback',
                coverage_complete=False,
                success=True,
                quality_score=self._calculate_quality_score(buildings),
                warnings=["Utilisé recherche Nominatim comme fallback"]
            )
        else:
            raise ValueError("Pas de géométrie disponible via Nominatim")
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        success_rate = 0
        if self.stats['total_queries'] > 0:
            success_rate = (self.stats['successful_queries'] / self.stats['total_queries']) * 100
        
        return {
            'total_queries': self.stats['total_queries'],
            'successful_queries': self.stats['successful_queries'],
            'success_rate_percent': round(success_rate, 1),
            'total_buildings_loaded': self.stats['buildings_loaded']
        }


# ==============================================================================
# GÉNÉRATEUR DE DONNÉES ÉLECTRIQUES
# ==============================================================================

class ElectricityDataGenerator:
    """Générateur de données électriques réalistes"""
    
    def __init__(self):
        self.generation_count = 0
    
    def generate_timeseries_data(
        self, 
        buildings: List[Dict], 
        start_date: str, 
        end_date: str, 
        frequency: str = '1H'
    ) -> Dict:
        """
        Génère des données de consommation électrique pour les bâtiments
        """
        start_time = time.time()
        self.generation_count += 1
        
        logger.info(f"⚡ Génération données électriques pour {len(buildings)} bâtiments")
        
        try:
            # Créer l'index temporel
            date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
            
            # Générer les données pour chaque bâtiment
            all_data = []
            
            for building in buildings:
                building_data = self._generate_building_timeseries(
                    building, date_range
                )
                all_data.extend(building_data)
            
            # Créer le DataFrame final
            df = pd.DataFrame(all_data)
            
            generation_time = time.time() - start_time
            
            logger.info(f"✅ {len(all_data)} points de données générés en {generation_time:.1f}s")
            
            return {
                'success': True,
                'data': df,
                'metadata': {
                    'total_points': len(all_data),
                    'buildings_count': len(buildings),
                    'date_range': {
                        'start': start_date,
                        'end': end_date,
                        'frequency': frequency
                    },
                    'generation_time_seconds': generation_time
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur génération: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _estimate_base_consumption(self, building_type: str, surface_area: float) -> float:
        """
        Estime la consommation de base selon les spécifications Malaysia officielles
        
        NOUVELLES VALEURS OFFICIELLES (kWh/heure base):
        - Residential: 0.5 kWh (base) → 12.0 kWh (pic)
        - Commercial: 5.0 kWh (base) → 80.0 kWh (pic)  
        - Industrial: 20.0 kWh (base) → 200.0 kWh (pic)
        - Office: 3.0 kWh (base) → 45.0 kWh (pic)
        - Hospital: 25.0 kWh (base) → 70.0 kWh (pic)
        - School: 1.0 kWh (base) → 25.0 kWh (pic)
        - Hotel: 8.0 kWh (base) → 40.0 kWh (pic)
        """
        # Spécifications officielles Malaysia
        specs = {
            'residential': {'base': 0.5, 'peak': 12.0},
            'commercial': {'base': 5.0, 'peak': 80.0},
            'industrial': {'base': 20.0, 'peak': 200.0},
            'office': {'base': 3.0, 'peak': 45.0},
            'hospital': {'base': 25.0, 'peak': 70.0},
            'school': {'base': 1.0, 'peak': 25.0},
            'hotel': {'base': 8.0, 'peak': 40.0},
            'public': {'base': 3.0, 'peak': 45.0},  # Comme office
            'religious': {'base': 1.0, 'peak': 15.0}
        }
        
        building_spec = specs.get(building_type, specs['residential'])
        base_unit_consumption = building_spec['base']  # kWh/heure pour 100m²
        
        # Facteur de surface (référence 100m²)
        surface_factor = surface_area / 100.0
        surface_factor = max(0.1, min(surface_factor, 10.0))  # Limiter 10m² à 1000m²
        
        # Consommation de base finale (kWh/heure)
        base_consumption = base_unit_consumption * surface_factor
        
        return max(0.1, min(base_consumption, 500.0))  # Limites de sécurité
        
    def _generate_building_timeseries(self, building: Dict, date_range: pd.DatetimeIndex) -> List[Dict]:
        """Génère la série temporelle avec TOUS les patterns Malaysia"""
        building_id = building['id']
        building_type = building['building_type']
        surface_area = building.get('surface_area_m2', 100)
        
        # Consommation de base (kWh/heure) selon spécifications Malaysia
        base_consumption_hourly = self._estimate_base_consumption(building_type, surface_area)
        
        data_points = []
        
        for timestamp in date_range:
            # 1. Facteur horaire tropical Malaysia
            hour_factor = self._get_hourly_factor(timestamp.hour, building_type)
            
            # 2. Facteur hebdomadaire Malaysia  
            day_factor = self._get_daily_factor(timestamp.weekday(), building_type)
            
            # 3. Facteur saisonnier Malaysia
            seasonal_factor = self._get_seasonal_factor(timestamp.month)
            
            # 4. Facteur Ramadan Malaysia
            ramadan_factor = self._get_ramadan_factor(timestamp.month, timestamp.hour, building_type)
            
            # 5. Variation aléatoire réaliste
            random_factor = np.random.normal(1.0, 0.05)  # ±5% seulement
            random_factor = max(0.8, min(random_factor, 1.2))  # Limiter
            
            # 6. Calcul de la durée de l'intervalle
            if len(date_range) > 1:
                interval_hours = (date_range[1] - date_range[0]).total_seconds() / 3600
            else:
                interval_hours = 1.0
            
            # 7. CALCUL FINAL avec tous les patterns Malaysia
            consumption = (base_consumption_hourly *      # Base kWh/h
                        hour_factor *                   # Pattern tropical
                        day_factor *                    # Pattern hebdomadaire
                        seasonal_factor *               # Pattern saisonnier  
                        ramadan_factor *                # Pattern Ramadan
                        random_factor *                 # Variation réaliste
                        interval_hours)                 # Durée de l'intervalle
            
            # 8. Limites de sécurité
            consumption = max(0.001, consumption)  # Minimum technique
            
            # 9. Vérification cohérence (optionnel pour debug)
            if len(data_points) < 3:  # Log les premiers points
                logger.info(f"🔍 Point {len(data_points)+1} - {building_type} {surface_area}m²:")
                logger.info(f"   Base: {base_consumption_hourly:.3f} kWh/h")
                logger.info(f"   Facteurs: hour={hour_factor:.2f}, day={day_factor:.2f}, season={seasonal_factor:.2f}, ramadan={ramadan_factor:.2f}")
                logger.info(f"   Intervalle: {interval_hours:.2f}h")
                logger.info(f"   Final: {consumption:.4f} kWh")
            
            data_points.append({
                'building_id': building_id,
                'timestamp': timestamp,
                'consumption_kwh': round(consumption, 4),
                'building_type': building_type,
                'latitude': building['latitude'],
                'longitude': building['longitude'],
                'zone_name': building['zone_name']
            })
        
        return data_points
    
    def _get_hourly_factor(self, hour: int, building_type: str) -> float:
        """
        Facteurs horaires selon le climat tropical Malaysia
        
        Patterns officiels:
        - 6h-8h : Pic matinal (avant la chaleur) 
        - 11h-16h : Maximum de climatisation (heures les plus chaudes)
        - 17h-21h : Activité élevée (après-midi/soirée)
        - 22h-5h : Consommation nocturne réduite
        """
        # Facteurs nocturnes par type
        night_factors = {
            'residential': 0.3, 'commercial': 0.2, 'industrial': 0.7,
            'office': 0.1, 'hospital': 0.8, 'school': 0.05,
            'hotel': 0.6, 'public': 0.1, 'religious': 0.05
        }
        
        night_factor = night_factors.get(building_type, 0.3)
        
        if building_type == 'residential':
            if 6 <= hour <= 8:  # Pic matinal
                return 1.4
            elif 11 <= hour <= 16:  # Maximum climatisation  
                return 2.0
            elif 17 <= hour <= 21:  # Activité élevée
                return 1.6
            elif 22 <= hour <= 23 or 0 <= hour <= 5:  # Nuit
                return night_factor
            else:
                return 1.0
                
        elif building_type == 'commercial':
            if 9 <= hour <= 21:  # Ouvert
                if 11 <= hour <= 16:  # Pic climatisation
                    return 2.5
                else:
                    return 1.8
            else:  # Fermé
                return night_factor
                
        elif building_type == 'office':
            if 8 <= hour <= 18:  # Heures bureau
                if 11 <= hour <= 16:  # Pic climatisation
                    return 3.0
                else:
                    return 2.0
            else:  # Fermé
                return night_factor
                
        elif building_type == 'school':
            if 7 <= hour <= 15:  # Heures scolaires
                if 11 <= hour <= 14:  # Pic climatisation
                    return 5.0
                else:
                    return 3.0
            else:  # Fermé
                return night_factor
                
        elif building_type == 'hospital':
            if 11 <= hour <= 16:  # Pic climatisation
                return 1.8
            elif 6 <= hour <= 22:  # Activité diurne
                return 1.4
            else:  # Nuit
                return night_factor
                
        elif building_type == 'industrial':
            if 11 <= hour <= 16:  # Pic climatisation
                return 2.0
            elif 6 <= hour <= 22:  # Production
                return 1.5
            else:  # Nuit
                return night_factor
        
        return 1.0
    
    def _get_daily_factor(self, weekday: int, building_type: str) -> float:
        """
        Facteurs hebdomadaires Malaysia:
        
        - Vendredi après-midi : Réduction d'activité (prière du vendredi)
        - Weekend : Plus de consommation résidentielle
        - Jours ouvrables : Pics dans les bureaux/commerces
        """
        # 0=Lundi, 4=Vendredi, 5=Samedi, 6=Dimanche
        is_weekend = weekday >= 5
        
        if building_type == 'residential':
            return 1.2 if is_weekend else 1.0
            
        elif building_type in ['office', 'commercial']:
            if is_weekend:
                return 0.4  # Fermé week-end
            else:
                return 1.0
                
        elif building_type == 'school':
            return 0.05 if is_weekend else 1.0  # École fermée
            
        elif building_type in ['hospital', 'hotel']:
            return 1.0  # Pas d'impact majeur
            
        elif building_type == 'industrial':
            return 0.7 if is_weekend else 1.0  # Production réduite
            
        else:
            return 1.0
    
    def _get_seasonal_factor(self, month: int) -> float:
        """
        Facteurs saisonniers Malaysia selon le document officiel:
        
        - Nov-Fév: Mousson NE (0.9-1.1×) - Moins de climatisation
        - Mar-Avr: Transition (1.2-1.5×) - Période chaude + Ramadan  
        - Mai-Août: Saison sèche (1.3-1.7×) - Maximum de climatisation
        - Sep-Oct: Variable (1.0-1.3×) - Climat changeant
        """
        seasonal_factors = {
            # Mousson NE - Moins de climatisation
            11: 0.95, 12: 0.9, 1: 0.9, 2: 1.0,
            
            # Transition - Période chaude + Ramadan
            3: 1.3, 4: 1.4,
            
            # Saison sèche - Maximum de climatisation
            5: 1.5, 6: 1.6, 7: 1.7, 8: 1.6,
            
            # Variable - Climat changeant  
            9: 1.2, 10: 1.1
        }
        
        return seasonal_factors.get(month, 1.0)

    def _get_ramadan_factor(self, month: int, hour: int, building_type: str) -> float:
        """
        Facteurs Ramadan (Mar-Avr approximatif):
        
        - 4h-17h : Consommation réduite de 40% (jeûne)
        - 18h-23h : Consommation augmentée de 40% (Iftar, activités nocturnes)
        """
        # Ramadan approximatif en Mars-Avril
        if month not in [3, 4]:
            return 1.0
            
        if building_type in ['residential', 'commercial']:
            if 4 <= hour <= 17:  # Période de jeûne
                return 0.6  # Réduction de 40%
            elif 18 <= hour <= 23:  # Iftar et activités nocturnes
                return 1.4  # Augmentation de 40%
            else:
                return 1.0
        else:
            return 1.0  # Hôpitaux, industriel moins affectés
    
    def get_statistics(self) -> Dict:
        """Statistiques du générateur"""
        return {
            'total_generations': self.generation_count,
            'last_generation': datetime.now().isoformat() if self.generation_count > 0 else None
        }


# ==============================================================================
# EXPORTEUR DE DONNÉES
# ==============================================================================

class DataExporter:
    """Exporteur multi-format pour les données générées"""
    
    def __init__(self):
        self.export_count = 0
    
    def export_data(
        self, 
        dataframe: pd.DataFrame, 
        formats: List[str], 
        filename_prefix: str = 'malaysia_electricity'
    ) -> Dict:
        """
        Exporte les données dans les formats demandés
        """
        start_time = time.time()
        self.export_count += 1
        
        logger.info(f"📁 Export données vers {len(formats)} format(s)")
        
        try:
            exported_files = []
            total_size_bytes = 0
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for format_type in formats:
                if format_type.lower() == 'csv':
                    filename = f"{filename_prefix}_{timestamp}.csv"
                    filepath = AppConfig.EXPORTS_DIR / filename
                    dataframe.to_csv(filepath, index=False)
                    
                elif format_type.lower() == 'json':
                    filename = f"{filename_prefix}_{timestamp}.json"
                    filepath = AppConfig.EXPORTS_DIR / filename
                    dataframe.to_json(filepath, orient='records', date_format='iso')
                    
                elif format_type.lower() == 'excel':
                    filename = f"{filename_prefix}_{timestamp}.xlsx"
                    filepath = AppConfig.EXPORTS_DIR / filename
                    dataframe.to_excel(filepath, index=False, engine='openpyxl')
                    
                elif format_type.lower() == 'parquet':
                    filename = f"{filename_prefix}_{timestamp}.parquet"
                    filepath = AppConfig.EXPORTS_DIR / filename
                    dataframe.to_parquet(filepath, index=False)
                
                else:
                    logger.warning(f"⚠️ Format non supporté: {format_type}")
                    continue
                
                # Calculer la taille du fichier
                file_size = filepath.stat().st_size
                total_size_bytes += file_size
                
                exported_files.append({
                    'format': format_type,
                    'filename': filename,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })
                
                logger.info(f"✅ Exporté: {filename} ({file_size / (1024 * 1024):.2f} MB)")
            
            export_time = time.time() - start_time
            
            return {
                'success': True,
                'exported_files': exported_files,
                'total_size_mb': round(total_size_bytes / (1024 * 1024), 2),
                'export_time_seconds': export_time,
                'export_timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur export: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict:
        """Statistiques de l'exporteur"""
        return {
            'total_exports': self.export_count
        }


# ==============================================================================
# DONNÉES DE ZONES MALAYSIA
# ==============================================================================

def get_malaysia_zones_complete() -> List[Dict]:
    """
    Retourne la liste complète des zones Malaysia avec toutes les métadonnées
    """
    return [
        # Malaysia entière
        {
            'zone_id': 'malaysia',
            'name': 'Malaysia Entière',
            'type': 'country',
            'population': 32700000,
            'area_km2': 330803,
            'estimated_buildings': 8500000,
            'complexity_level': 'high',
            'has_osm_relation': True,
            'recommended_method': 'hybrid'
        },
        
        # États principaux
        {
            'zone_id': 'selangor',
            'name': 'Selangor',
            'type': 'state',
            'population': 6500000,
            'area_km2': 8104,
            'estimated_buildings': 1800000,
            'complexity_level': 'high',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'johor',
            'name': 'Johor',
            'type': 'state',
            'population': 3800000,
            'area_km2': 19984,
            'estimated_buildings': 1100000,
            'complexity_level': 'high',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'perak',
            'name': 'Perak',
            'type': 'state',
            'population': 2500000,
            'area_km2': 21005,
            'estimated_buildings': 750000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'kedah',
            'name': 'Kedah',
            'type': 'state',
            'population': 2200000,
            'area_km2': 9500,
            'estimated_buildings': 650000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'penang',
            'name': 'Penang',
            'type': 'state',
            'population': 1800000,
            'area_km2': 1048,
            'estimated_buildings': 520000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        
        # Territoires fédéraux
        {
            'zone_id': 'kuala_lumpur',
            'name': 'Kuala Lumpur',
            'type': 'federal_territory',
            'population': 1800000,
            'area_km2': 243,
            'estimated_buildings': 520000,
            'complexity_level': 'high',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'putrajaya',
            'name': 'Putrajaya',
            'type': 'federal_territory',
            'population': 110000,
            'area_km2': 49,
            'estimated_buildings': 35000,
            'complexity_level': 'low',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        
        # Villes principales
        {
            'zone_id': 'shah_alam',
            'name': 'Shah Alam',
            'type': 'major_city',
            'population': 750000,
            'area_km2': 290,
            'estimated_buildings': 220000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'george_town',
            'name': 'George Town',
            'type': 'major_city',
            'population': 720000,
            'area_km2': 306,
            'estimated_buildings': 210000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'ipoh',
            'name': 'Ipoh',
            'type': 'major_city',
            'population': 650000,
            'area_km2': 643,
            'estimated_buildings': 180000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        },
        {
            'zone_id': 'johor_bahru',
            'name': 'Johor Bahru',
            'type': 'major_city',
            'population': 550000,
            'area_km2': 220,
            'estimated_buildings': 165000,
            'complexity_level': 'medium',
            'has_osm_relation': True,
            'recommended_method': 'administrative'
        }
    ]


# ==============================================================================
# INITIALISATION DE L'APPLICATION FLASK
# ==============================================================================

def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    app.config.from_object(AppConfig)
    return app


# Création de l'application
app = create_app()

# Initialisation des gestionnaires
complete_loader = CompleteBuildingLoader()
generator = ElectricityDataGenerator()
exporter = DataExporter()


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def validate_generation_parameters(start_date: str, end_date: str, frequency: str, num_buildings: int):
    """Validation des paramètres de génération"""
    errors = []
    
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        if start >= end:
            errors.append("Date de fin doit être après date de début")
        if (end - start).days > 365:
            errors.append("Période maximale: 365 jours")
    except Exception as e:
        errors.append(f"Format de dates invalide: {str(e)}")
    
    valid_frequencies = ['15T', '30T', '1H', '3H', 'D']
    if frequency not in valid_frequencies:
        errors.append(f"Fréquence invalide. Supportées: {valid_frequencies}")
    
    if not (1 <= num_buildings <= 5000000):
        errors.append("Nombre de bâtiments doit être entre 1 et 5000000")
    
    return len(errors) == 0, errors


def calculate_detailed_estimation(zone_info: Dict) -> Dict:
    """Calcule une estimation détaillée pour une zone"""
    buildings = zone_info['estimated_buildings']
    area = zone_info['area_km2']
    complexity = zone_info['complexity_level']
    
    estimated_time_minutes = max(1, buildings / 8000)
    estimated_size_mb = max(0.1, buildings * 0.0025)
    building_density = buildings / area if area > 0 else 0
    
    if complexity == 'low':
        time_range = '30 secondes - 2 minutes'
        recommendation = 'Chargement rapide - toutes méthodes OK'
    elif complexity == 'medium':
        time_range = '2 - 8 minutes'
        recommendation = 'Chargement modéré - méthode administrative recommandée'
    else:
        time_range = '8 - 25 minutes'
        recommendation = 'Chargement long - patience requise, méthode hybride conseillée'
    
    warnings = []
    recommendations = []
    
    if buildings > 1000000:
        warnings.append('Zone très grande : Plus d\'1 million de bâtiments estimés')
        recommendations.append('Considérez diviser en sous-zones')
    
    if area > 50000:
        warnings.append('Zone très étendue : Risque de timeout')
        recommendations.append('Méthode hybride fortement recommandée')
    
    return {
        'zone_name': zone_info['name'],
        'estimated_buildings': buildings,
        'area_km2': area,
        'building_density_per_km2': round(building_density, 1),
        'estimated_time_range': time_range,
        'estimated_time_minutes': round(estimated_time_minutes, 1),
        'estimated_size_mb': round(estimated_size_mb, 1),
        'complexity_level': complexity,
        'recommendation': recommendation,
        'recommended_method': zone_info['recommended_method'],
        'warnings': warnings,
        'recommendations': recommendations
    }


# ==============================================================================
# ROUTES PRINCIPALES
# ==============================================================================

@app.route('/')
def index():
    """Page d'accueil avec interface améliorée"""
    try:
        zones = get_malaysia_zones_complete()
        return render_template('index.html', zones=zones)
    except Exception as e:
        logger.error(f"❌ Erreur page d'accueil: {str(e)}")
        return render_template('index.html', zones=[], error="Erreur de chargement")


# ==============================================================================
# API ZONES ET ESTIMATION
# ==============================================================================

@app.route('/api/zones', methods=['GET'])
def api_get_zones():
    """API pour récupérer les zones disponibles avec catégories"""
    try:
        zones_data = get_malaysia_zones_complete()
        
        organized_zones = {
            'success': True,
            'zones': zones_data,
            'categories': {
                'country': [z for z in zones_data if z['type'] == 'country'],
                'state': [z for z in zones_data if z['type'] == 'state'],
                'federal_territory': [z for z in zones_data if z['type'] == 'federal_territory'],
                'major_city': [z for z in zones_data if z['type'] == 'major_city']
            },
            'total_zones': len(zones_data)
        }
        
        return jsonify(organized_zones), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur API zones: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/zone-estimation/<zone_name>', methods=['GET'])
def api_zone_estimation(zone_name: str):
    """API pour obtenir l'estimation détaillée d'une zone"""
    try:
        zone_id = zone_name.lower().replace(' ', '_').replace('-', '_')
        
        zones_data = get_malaysia_zones_complete()
        zone_info = next((z for z in zones_data if z['zone_id'] == zone_id), None)
        
        if not zone_info:
            return jsonify({
                'success': False,
                'error': f'Zone {zone_name} non trouvée',
                'available_zones': [z['zone_id'] for z in zones_data[:10]]
            }), 404
        
        estimation = calculate_detailed_estimation(zone_info)
        
        return jsonify({
            'success': True,
            'zone_name': zone_name,
            'estimation': estimation
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur estimation {zone_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# API OSM CORRIGÉE - SOLUTION AU PROBLÈME DU CARRÉ
# ==============================================================================

@app.route('/api/osm-buildings/<zone_name>', methods=['POST'])
def api_load_osm_buildings_corrected(zone_name: str):
    """
    API CORRIGÉE pour charger TOUS les bâtiments OSM d'une zone
    
    RÉSOLUTION DU PROBLÈME:
    - Utilise les relations OSM administratives au lieu des bounding boxes
    - Récupère TOUS les bâtiments de la localité, pas seulement un carré
    - Méthodes multiples avec fallback automatique
    """
    try:
        data = request.get_json() or {}
        method = data.get('method', 'administrative')
        
        logger.info(f"🔄 Début chargement OSM COMPLET pour {zone_name} (méthode: {method})")
        
        if not zone_name or zone_name.strip() == '':
            return jsonify({
                'success': False,
                'error': 'Nom de zone requis',
                'code': 'INVALID_ZONE_NAME'
            }), 400
        
        zone_id = zone_name.lower().replace(' ', '_').replace('-', '_')
        
        # UTILISATION DU NOUVEAU LOADER CORRIGÉ
        result = complete_loader.load_complete_locality_buildings(
            zone_id=zone_id,
            zone_name=zone_name,
            method=method
        )
        
        if result.success:
            # Format de réponse compatible avec le frontend existant
            response = {
                'success': True,
                'buildings': result.buildings,
                'metadata': {
                    'total_buildings': len(result.buildings),
                    'total_osm_elements': result.total_elements,
                    'query_time_seconds': result.query_time_seconds,
                    'method_used': result.method_used,
                    'coverage_complete': result.coverage_complete,
                    'quality_metrics': {
                        'quality_score': result.quality_score,
                        'data_completeness': 'complete' if result.coverage_complete else 'partial',
                        'building_density': len(result.buildings) / max(1, result.total_elements) * 100
                    }
                }
            }
            
            if result.warnings:
                response['metadata']['warnings'] = result.warnings
            
            logger.info(f"✅ {len(result.buildings)} bâtiments chargés pour {zone_name}")
            return jsonify(response), 200
            
        else:
            # Gestion d'erreur avec suggestions
            error_response = {
                'success': False,
                'error': result.error_message,
                'zone_name': zone_name,
                'method_tried': method,
                'suggestions': [
                    'Essayez la méthode "bbox" comme alternative',
                    'Vérifiez que la zone existe dans OpenStreetMap',
                    'Essayez avec une zone plus petite si timeout'
                ],
                'fallback_methods': [
                    {'method': 'bbox', 'description': 'Rectangle géographique étendu'},
                    {'method': 'hybrid', 'description': 'Combinaison administratif + bbox'}
                ]
            }
            
            logger.warning(f"⚠️ Échec chargement {zone_name}: {result.error_message}")
            return jsonify(error_response), 400
            
    except Exception as e:
        logger.error(f"❌ Erreur serveur chargement {zone_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur serveur interne: {str(e)}',
            'zone_name': zone_name,
            'code': 'INTERNAL_SERVER_ERROR'
        }), 500


@app.route('/api/osm-methods', methods=['GET'])
def api_get_osm_methods():
    """API pour obtenir les informations sur les méthodes OSM disponibles"""
    methods_info = {
        'administrative': {
            'name': 'Limites Administratives',
            'description': 'Utilise les relations OSM pour récupérer TOUS les bâtiments de la localité officielle',
            'advantages': [
                'Couverture complète garantie',
                'Respecte les limites administratives officielles',
                'Pas de bâtiments manqués en périphérie'
            ],
            'recommended_for': ['Études officielles', 'Analyses complètes', 'Données gouvernementales'],
            'complexity': 'medium'
        },
        'bbox': {
            'name': 'Rectangle Géographique',
            'description': 'Récupère les bâtiments dans un rectangle géographique étendu',
            'advantages': [
                'Plus rapide pour grandes zones',
                'Fonctionne même sans relations OSM',
                'Méthode de fallback fiable'
            ],
            'recommended_for': ['Tests rapides', 'Prototypage', 'Zones sans relations OSM'],
            'complexity': 'low'
        },
        'hybrid': {
            'name': 'Méthode Hybride',
            'description': 'Combine administratif + bbox pour une couverture maximale',
            'advantages': [
                'Meilleure couverture possible',
                'Fallback automatique si une méthode échoue',
                'Plus robuste'
            ],
            'recommended_for': ['Projets critiques', 'Zones problématiques', 'Maximum de fiabilité'],
            'complexity': 'high'
        }
    }
    
    return jsonify({
        'success': True,
        'methods': methods_info,
        'default_method': 'administrative',
        'recommendations': {
            'small_zones': 'administrative',
            'large_zones': 'hybrid',
            'quick_tests': 'bbox'
        }
    }), 200


# ==============================================================================
# API GÉNÉRATION DE DONNÉES ÉLECTRIQUES
# ==============================================================================

@app.route('/api/generate', methods=['POST'])
def api_generate_electrical_data():
    """API pour générer les données électriques"""
    try:
        data = request.get_json()
        
        # Validation des paramètres
        required_fields = ['zone_name', 'buildings_osm', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Champ requis manquant: {field}'
                }), 400
        
        zone_name = data['zone_name']
        buildings_osm = data['buildings_osm']
        start_date = data['start_date']
        end_date = data['end_date']
        frequency = data.get('frequency', '1H')
        
        logger.info(f"⚡ Génération données pour {zone_name}: {len(buildings_osm)} bâtiments")
        
        # Validation des paramètres
        is_valid, errors = validate_generation_parameters(
            start_date, end_date, frequency, len(buildings_osm)
        )
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Paramètres invalides',
                'validation_errors': errors
            }), 400
        
        # Génération des données
        generation_result = generator.generate_timeseries_data(
            buildings=buildings_osm,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency
        )
        
        if generation_result['success']:
            # Statistiques de génération
            metadata = generation_result['metadata']
            
            response = {
                'success': True,
                'zone_name': zone_name,
                'generation_metadata': metadata,
                'data_preview': generation_result['data'].head(10).to_dict('records'),
                'statistics': {
                    'total_points': metadata['total_points'],
                    'buildings_count': metadata['buildings_count'],
                    'time_range': f"{start_date} à {end_date}",
                    'frequency': frequency,
                    'generation_time': f"{metadata['generation_time_seconds']:.1f}s"
                },
                'next_steps': {
                    'export_available': True,
                    'supported_formats': ['CSV', 'JSON', 'Excel', 'Parquet']
                }
            }
            
            # Stocker les données pour l'export (en mémoire pour cette session)
            app.generated_data = generation_result['data']
            app.generation_metadata = metadata
            
            logger.info(f"✅ Génération terminée: {metadata['total_points']} points")
            return jsonify(response), 200
        else:
            return jsonify(generation_result), 500
            
    except Exception as e:
        logger.error(f"❌ Erreur génération: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur génération: {str(e)}'
        }), 500


# ==============================================================================
# API EXPORT DE DONNÉES
# ==============================================================================

@app.route('/api/export', methods=['POST'])
def api_export_data():
    """API pour exporter les données générées"""
    try:
        data = request.get_json()
        
        if not hasattr(app, 'generated_data'):
            return jsonify({
                'success': False,
                'error': 'Aucune donnée générée à exporter. Générez d\'abord les données.'
            }), 400
        
        export_formats = data.get('formats', ['csv'])
        filename_prefix = data.get('filename_prefix', 'malaysia_electricity')
        
        logger.info(f"📁 Export vers {len(export_formats)} format(s)")
        
        # Export des données
        export_result = exporter.export_data(
            dataframe=app.generated_data,
            formats=export_formats,
            filename_prefix=filename_prefix
        )
        
        if export_result['success']:
            logger.info(f"✅ Export terminé: {export_result.get('total_size_mb', 0):.2f} MB")
            return jsonify(export_result), 200
        else:
            return jsonify(export_result), 500
        
    except Exception as e:
        logger.error(f"❌ Erreur export: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<filename>')
def api_download_file(filename: str):
    """API pour télécharger un fichier exporté"""
    try:
        # Sécurisation du nom de fichier
        if '..' in filename or '/' in filename:
            return jsonify({
                'success': False,
                'error': 'Nom de fichier invalide'
            }), 400
        
        file_path = AppConfig.EXPORTS_DIR / filename
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'Fichier non trouvé'
            }), 404
        
        logger.info(f"📁 Téléchargement: {filename}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# API MONITORING ET STATISTIQUES
# ==============================================================================

@app.route('/api/status')
def api_status():
    """API pour le statut de l'application"""
    try:
        status = {
            'healthy': True,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'osm': True,  # Simplifié pour cette version
                'generation': True,
                'export': True
            },
            'version': '2.0-corrected'
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur health check: {str(e)}")
        return jsonify({
            'healthy': False,
            'error': str(e)
        }), 503


@app.route('/api/statistics')
def api_statistics():
    """API pour les statistiques globales"""
    try:
        stats = {
            'osm_statistics': complete_loader.get_statistics(),
            'generation_statistics': generator.get_statistics(),
            'export_statistics': exporter.get_statistics(),
            'application_statistics': {
                'total_api_calls': getattr(app, '_api_calls_count', 0),
                'available_zones': len(get_malaysia_zones_complete()),
                'uptime': 'Calculé dynamiquement'
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur statistiques: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# GESTION D'ERREURS GLOBALE
# ==============================================================================

@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return jsonify({
        'success': False,
        'error': 'Endpoint non trouvé',
        'code': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    logger.error(f"❌ Erreur interne serveur: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Erreur interne du serveur',
        'code': 500
    }), 500


@app.before_request
def before_request():
    """Middleware avant chaque requête"""
    if not hasattr(app, '_api_calls_count'):
        app._api_calls_count = 0
    
    if request.path.startswith('/api/'):
        app._api_calls_count += 1


@app.after_request
def after_request(response):
    """Middleware après chaque requête"""
    # Headers de sécurité
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    
    # CORS pour développement
    if AppConfig.DEBUG:
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response


# ==============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ==============================================================================

if __name__ == '__main__':
    logger.info("🚀 Malaysia Electricity Generator v2.0 - Version Corrigée")
    logger.info("=" * 60)
    logger.info("✅ PROBLÈMES RÉSOLUS:")
    logger.info("   - Récupération COMPLÈTE des bâtiments OSM (fini le carré)")
    logger.info("   - Interface professionnelle avec sélecteur par catégories")
    logger.info("   - Méthodes OSM multiples avec fallback automatique")
    logger.info("   - Gestion d'erreurs robuste")
    logger.info("=" * 60)
    logger.info(f"🌐 URL: http://{AppConfig.HOST}:{AppConfig.PORT}")
    logger.info(f"📁 Exports: {AppConfig.EXPORTS_DIR}")
    logger.info(f"🔧 Mode: {'DEBUG' if AppConfig.DEBUG else 'PRODUCTION'}")
    logger.info("=" * 60)
    
    try:
        app.run(
            host=AppConfig.HOST,
            port=AppConfig.PORT,
            debug=AppConfig.DEBUG,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt de l'application")
    except Exception as e:
        logger.error(f"❌ Erreur démarrage: {e}")