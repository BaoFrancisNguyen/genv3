"""
Modèle Building - Représentation des bâtiments Malaysia
======================================================

Ce module définit la structure de données pour les bâtiments
avec leurs propriétés énergétiques et métadonnées.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class Building:
    """
    Modèle de données pour un bâtiment avec propriétés énergétiques
    
    Représente un bâtiment avec toutes ses caractéristiques
    nécessaires pour la génération de données électriques.
    """
    
    # Identifiants
    osm_id: str
    latitude: float
    longitude: float
    zone_name: str
    
    # Propriétés physiques
    building_type: str = 'residential'
    surface_area_m2: float = 100.0
    
    # Propriétés énergétiques
    base_consumption_kwh: float = 15.0
    
    # Métadonnées OSM
    osm_tags: Dict = field(default_factory=dict)
    
    # Identifiant unique généré
    building_id: str = field(default_factory=lambda: f"MY_{uuid.uuid4().hex[:8].upper()}")
    
    # Horodatage
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validation et calculs post-initialisation"""
        # Validation des coordonnées Malaysia
        if not (0.5 <= self.latitude <= 7.5):
            raise ValueError(f"Latitude invalide pour Malaysia: {self.latitude}")
        
        if not (99.0 <= self.longitude <= 120.0):
            raise ValueError(f"Longitude invalide pour Malaysia: {self.longitude}")
        
        # Validation de la surface
        if self.surface_area_m2 <= 0:
            raise ValueError(f"Surface invalide: {self.surface_area_m2}")
        
        # Validation de la consommation
        if self.base_consumption_kwh < 0:
            raise ValueError(f"Consommation négative: {self.base_consumption_kwh}")
        
        # Normalisation du type de bâtiment
        self.building_type = self._normalize_building_type(self.building_type)
        
        # Recalcul de la consommation de base si nécessaire
        if self.base_consumption_kwh == 15.0:  # Valeur par défaut
            self.base_consumption_kwh = self._calculate_base_consumption()
    
    def _normalize_building_type(self, building_type: str) -> str:
        """Normalise le type de bâtiment vers les catégories supportées"""
        type_mapping = {
            'residential': 'residential',
            'house': 'residential',
            'apartment': 'residential',
            'apartments': 'residential',
            'detached': 'residential',
            'terrace': 'residential',
            'commercial': 'commercial',
            'retail': 'commercial',
            'shop': 'commercial',
            'office': 'office',
            'industrial': 'industrial',
            'factory': 'industrial',
            'warehouse': 'industrial',
            'hospital': 'hospital',
            'school': 'school',
            'university': 'school',
            'hotel': 'hotel',
            'yes': 'residential',
            'true': 'residential'
        }
        
        normalized = type_mapping.get(building_type.lower(), 'residential')
        
        # Affinage avec les tags OSM si disponibles
        if self.osm_tags:
            if self.osm_tags.get('amenity') == 'hospital':
                return 'hospital'
            elif self.osm_tags.get('amenity') in ['school', 'university']:
                return 'school'
            elif self.osm_tags.get('tourism') == 'hotel':
                return 'hotel'
            elif self.osm_tags.get('shop'):
                return 'commercial'
            elif self.osm_tags.get('office'):
                return 'office'
            elif self.osm_tags.get('landuse') == 'industrial':
                return 'industrial'
        
        return normalized
    
    def _calculate_base_consumption(self) -> float:
        """Calcule la consommation de base selon le type et la surface"""
        # Coefficients de consommation par type (kWh/m²/jour) pour Malaysia
        consumption_coefficients = {
            'residential': 0.15,
            'commercial': 0.25,
            'office': 0.30,
            'industrial': 0.45,
            'hospital': 0.40,
            'school': 0.20,
            'hotel': 0.35
        }
        
        coefficient = consumption_coefficients.get(self.building_type, 0.15)
        base_consumption = self.surface_area_m2 * coefficient
        
        # Limites de validation
        min_consumption = 5.0   # 5 kWh/jour minimum
        max_consumption = 10000.0  # 10 MWh/jour maximum
        
        return max(min_consumption, min(base_consumption, max_consumption))
    
    @classmethod
    def from_osm_data(cls, osm_element: Dict, zone_name: str) -> 'Building':
        """
        Crée un Building à partir de données OSM
        
        Args:
            osm_element: Élément OSM avec geometry et tags
            zone_name: Nom de la zone
            
        Returns:
            Building: Instance créée
        """
        # Extraction des coordonnées
        geometry = osm_element.get('geometry', [])
        if not geometry:
            raise ValueError("Géométrie manquante dans l'élément OSM")
        
        # Calcul du centre géométrique
        lats = [coord['lat'] for coord in geometry if 'lat' in coord]
        lons = [coord['lon'] for coord in geometry if 'lon' in coord]
        
        if not lats or not lons:
            raise ValueError("Coordonnées invalides dans la géométrie")
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Extraction des tags
        tags = osm_element.get('tags', {})
        building_tag = tags.get('building', 'residential')
        
        # Calcul de la surface
        surface_area = cls._calculate_polygon_area_static(geometry)
        
        return cls(
            osm_id=str(osm_element.get('id', '')),
            latitude=center_lat,
            longitude=center_lon,
            building_type=building_tag,
            surface_area_m2=surface_area,
            zone_name=zone_name,
            osm_tags=tags
        )
    
    @staticmethod
    def _calculate_polygon_area_static(geometry: List[Dict]) -> float:
        """Calcule l'aire d'un polygone à partir de coordonnées géographiques"""
        if len(geometry) < 3:
            return 50.0  # Surface par défaut
        
        try:
            # Conversion en coordonnées métriques approximatives
            coords_m = []
            for coord in geometry:
                lat = coord.get('lat', 0)
                lon = coord.get('lon', 0)
                
                # Conversion approximative à la latitude de Malaysia
                x = lon * 111320 * math.cos(math.radians(lat))
                y = lat * 110540
                coords_m.append((x, y))
            
            # Formule de Shoelace
            n = len(coords_m)
            area = 0.0
            
            for i in range(n):
                j = (i + 1) % n
                area += coords_m[i][0] * coords_m[j][1]
                area -= coords_m[j][0] * coords_m[i][1]
            
            area = abs(area) / 2.0
            
            # Validation de l'aire
            if area < 10:
                return 50.0
            elif area > 100000:
                return 1000.0
            
            return area
            
        except Exception:
            return 75.0
    
    def to_dict(self) -> Dict:
        """Convertit le bâtiment en dictionnaire"""
        return {
            'building_id': self.building_id,
            'osm_id': self.osm_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'building_type': self.building_type,
            'surface_area_m2': self.surface_area_m2,
            'base_consumption_kwh': self.base_consumption_kwh,
            'zone_name': self.zone_name,
            'osm_tags': self.osm_tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Building':
        """Crée un Building à partir d'un dictionnaire"""
        building = cls(
            osm_id=data['osm_id'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            building_type=data.get('building_type', 'residential'),
            surface_area_m2=data.get('surface_area_m2', 100.0),
            base_consumption_kwh=data.get('base_consumption_kwh', 15.0),
            zone_name=data['zone_name'],
            osm_tags=data.get('osm_tags', {}),
            building_id=data.get('building_id', f"MY_{uuid.uuid4().hex[:8].upper()}")
        )
        
        # Restaurer les timestamps si présents
        if 'created_at' in data:
            building.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            building.updated_at = datetime.fromisoformat(data['updated_at'])
        
        return building
    
    def get_energy_profile(self) -> Dict:
        """Retourne le profil énergétique du bâtiment"""
        return {
            'building_id': self.building_id,
            'building_type': self.building_type,
            'base_consumption_kwh_per_day': self.base_consumption_kwh,
            'consumption_per_m2': round(self.base_consumption_kwh / self.surface_area_m2, 3),
            'estimated_annual_kwh': round(self.base_consumption_kwh * 365, 1),
            'energy_intensity': self._get_energy_intensity_category(),
            'climate_dependency': self._get_climate_dependency()
        }
    
    def _get_energy_intensity_category(self) -> str:
        """Catégorise l'intensité énergétique"""
        intensity = self.base_consumption_kwh / self.surface_area_m2
        
        if intensity < 0.1:
            return 'très_faible'
        elif intensity < 0.2:
            return 'faible'
        elif intensity < 0.3:
            return 'moyenne'
        elif intensity < 0.5:
            return 'élevée'
        else:
            return 'très_élevée'
    
    def _get_climate_dependency(self) -> str:
        """Évalue la dépendance climatique"""
        climate_dependency = {
            'residential': 'élevée',
            'commercial': 'très_élevée',
            'office': 'très_élevée',
            'industrial': 'moyenne',
            'hospital': 'critique',
            'school': 'élevée',
            'hotel': 'très_élevée'
        }
        
        return climate_dependency.get(self.building_type, 'moyenne')
    
    def distance_to(self, other: 'Building') -> float:
        """Calcule la distance vers un autre bâtiment en km"""
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Rayon de la Terre en km
    
    def is_similar_to(self, other: 'Building', tolerance_m: float = 10.0) -> bool:
        """Vérifie si deux bâtiments sont similaires (possibles doublons)"""
        distance_m = self.distance_to(other) * 1000
        return (distance_m < tolerance_m and 
                self.building_type == other.building_type and
                abs(self.surface_area_m2 - other.surface_area_m2) < 50)
    
    def update_from_generation_params(self, **params):
        """Met à jour les paramètres du bâtiment pour la génération"""
        self.updated_at = datetime.now()
        
        # Mise à jour sélective des paramètres
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Recalcul automatique après mise à jour
        if any(key in params for key in ['building_type', 'surface_area_m2']):
            self.base_consumption_kwh = self._calculate_base_consumption()
    
    def __str__(self) -> str:
        """Représentation textuelle du bâtiment"""
        return (f"Building({self.building_id}, {self.building_type}, "
                f"{self.surface_area_m2}m², {self.base_consumption_kwh}kWh/day)")
    
    def __repr__(self) -> str:
        """Représentation pour debugging"""
        return (f"Building(osm_id='{self.osm_id}', "
                f"lat={self.latitude}, lon={self.longitude}, "
                f"type='{self.building_type}', "
                f"area={self.surface_area_m2})")


# ==============================================================================
# FONCTIONS UTILITAIRES POUR LES BÂTIMENTS
# ==============================================================================

def create_building_from_coordinates(
    lat: float, 
    lon: float, 
    building_type: str = 'residential', 
    zone_name: str = 'unknown',
    **kwargs
) -> Building:
    """
    Crée un bâtiment rapidement à partir de coordonnées
    
    Args:
        lat: Latitude
        lon: Longitude  
        building_type: Type de bâtiment
        zone_name: Nom de la zone
        **kwargs: Paramètres additionnels
        
    Returns:
        Building: Instance de bâtiment créée
    """
    return Building(
        osm_id=f"manual_{uuid.uuid4().hex[:8]}",
        latitude=lat,
        longitude=lon,
        building_type=building_type,
        zone_name=zone_name,
        **kwargs
    )


def validate_building_list(buildings: List[Building]) -> Tuple[List[Building], List[str]]:
    """
    Valide une liste de bâtiments et retourne les erreurs
    
    Args:
        buildings: Liste de bâtiments à valider
        
    Returns:
        Tuple[List[Building], List[str]]: Bâtiments valides et erreurs
    """
    valid_buildings = []
    errors = []
    
    for i, building in enumerate(buildings):
        try:
            # Validation basique
            if not building.building_id:
                raise ValueError("ID bâtiment manquant")
            
            if building.surface_area_m2 <= 0:
                raise ValueError("Surface invalide")
            
            if building.base_consumption_kwh < 0:
                raise ValueError("Consommation négative")
            
            # Validation des coordonnées Malaysia
            if not (0.5 <= building.latitude <= 7.5):
                raise ValueError("Latitude hors Malaysia")
            
            if not (99.0 <= building.longitude <= 120.0):
                raise ValueError("Longitude hors Malaysia")
            
            valid_buildings.append(building)
            
        except Exception as e:
            errors.append(f"Bâtiment {i}: {str(e)}")
    
    return valid_buildings, errors


def remove_duplicate_buildings(buildings: List[Building], tolerance_m: float = 50.0) -> List[Building]:
    """
    Supprime les bâtiments doublons basés sur la proximité géographique
    
    Args:
        buildings: Liste des bâtiments
        tolerance_m: Tolérance en mètres pour considérer deux bâtiments comme doublons
        
    Returns:
        List[Building]: Liste sans doublons
    """
    if not buildings:
        return []
    
    unique_buildings = []
    
    for building in buildings:
        is_duplicate = False
        
        for existing in unique_buildings:
            if building.is_similar_to(existing, tolerance_m):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_buildings.append(building)
    
    return unique_buildings


def group_buildings_by_type(buildings: List[Building]) -> Dict[str, List[Building]]:
    """
    Groupe les bâtiments par type
    
    Args:
        buildings: Liste des bâtiments
        
    Returns:
        Dict[str, List[Building]]: Bâtiments groupés par type
    """
    groups = {}
    
    for building in buildings:
        building_type = building.building_type
        if building_type not in groups:
            groups[building_type] = []
        groups[building_type].append(building)
    
    return groups


def calculate_buildings_statistics(buildings: List[Building]) -> Dict:
    """
    Calcule des statistiques sur une liste de bâtiments
    
    Args:
        buildings: Liste des bâtiments
        
    Returns:
        Dict: Statistiques détaillées
    """
    if not buildings:
        return {'error': 'Aucun bâtiment fourni'}
    
    # Groupement par type
    type_groups = group_buildings_by_type(buildings)
    
    # Calculs statistiques
    surfaces = [b.surface_area_m2 for b in buildings]
    consumptions = [b.base_consumption_kwh for b in buildings]
    
    # Coordonnées pour bounding box
    lats = [b.latitude for b in buildings]
    lons = [b.longitude for b in buildings]
    
    statistics = {
        'total_buildings': len(buildings),
        'building_types': {
            'distribution': {t: len(bldgs) for t, bldgs in type_groups.items()},
            'percentages': {
                t: round(len(bldgs) / len(buildings) * 100, 1) 
                for t, bldgs in type_groups.items()
            }
        },
        'surface_statistics': {
            'total_m2': round(sum(surfaces), 1),
            'mean_m2': round(sum(surfaces) / len(surfaces), 1),
            'median_m2': round(sorted(surfaces)[len(surfaces)//2], 1),
            'min_m2': min(surfaces),
            'max_m2': max(surfaces)
        },
        'consumption_statistics': {
            'total_kwh_per_day': round(sum(consumptions), 1),
            'mean_kwh_per_day': round(sum(consumptions) / len(consumptions), 1),
            'median_kwh_per_day': round(sorted(consumptions)[len(consumptions)//2], 1),
            'min_kwh_per_day': min(consumptions),
            'max_kwh_per_day': max(consumptions),
            'estimated_annual_mwh': round(sum(consumptions) * 365 / 1000, 1)
        },
        'geographic_extent': {
            'bounding_box': {
                'north': max(lats),
                'south': min(lats),
                'east': max(lons),
                'west': min(lons)
            },
            'center': {
                'latitude': round(sum(lats) / len(lats), 6),
                'longitude': round(sum(lons) / len(lons), 6)
            }
        },
        'quality_metrics': {
            'unique_ids': len(set(b.building_id for b in buildings)),
            'unique_osm_ids': len(set(b.osm_id for b in buildings if b.osm_id)),
            'has_osm_tags': len([b for b in buildings if b.osm_tags]),
            'completeness_score': round(
                (len([b for b in buildings if b.osm_tags]) / len(buildings)) * 100, 1
            )
        }
    }
    
    return statistics


def filter_buildings_by_area(
    buildings: List[Building], 
    min_area: float = 0, 
    max_area: float = float('inf')
) -> List[Building]:
    """
    Filtre les bâtiments par surface
    
    Args:
        buildings: Liste des bâtiments
        min_area: Surface minimum en m²
        max_area: Surface maximum en m²
        
    Returns:
        List[Building]: Bâtiments filtrés
    """
    return [b for b in buildings if min_area <= b.surface_area_m2 <= max_area]


def filter_buildings_by_type(buildings: List[Building], building_types: List[str]) -> List[Building]:
    """
    Filtre les bâtiments par type
    
    Args:
        buildings: Liste des bâtiments
        building_types: Types de bâtiments à conserver
        
    Returns:
        List[Building]: Bâtiments filtrés
    """
    return [b for b in buildings if b.building_type in building_types]


def filter_buildings_by_consumption(
    buildings: List[Building], 
    min_consumption: float = 0, 
    max_consumption: float = float('inf')
) -> List[Building]:
    """
    Filtre les bâtiments par consommation
    
    Args:
        buildings: Liste des bâtiments
        min_consumption: Consommation minimum en kWh/jour
        max_consumption: Consommation maximum en kWh/jour
        
    Returns:
        List[Building]: Bâtiments filtrés
    """
    return [b for b in buildings if min_consumption <= b.base_consumption_kwh <= max_consumption]


def export_buildings_to_dict_list(buildings: List[Building]) -> List[Dict]:
    """
    Exporte une liste de bâtiments vers une liste de dictionnaires
    
    Args:
        buildings: Liste des bâtiments
        
    Returns:
        List[Dict]: Liste de dictionnaires
    """
    return [building.to_dict() for building in buildings]


def import_buildings_from_dict_list(data: List[Dict]) -> List[Building]:
    """
    Importe une liste de bâtiments depuis une liste de dictionnaires
    
    Args:
        data: Liste de dictionnaires
        
    Returns:
        List[Building]: Liste des bâtiments créés
    """
    buildings = []
    
    for item in data:
        try:
            building = Building.from_dict(item)
            buildings.append(building)
        except Exception as e:
            # Log l'erreur mais continue le traitement
            print(f"Erreur import bâtiment: {str(e)}")
    
    return buildings


# ==============================================================================
# VALIDATEURS SPÉCIALISÉS
# ==============================================================================

def validate_building_coordinates_malaysia(building: Building) -> Tuple[bool, str]:
    """
    Valide spécifiquement les coordonnées pour Malaysia
    
    Args:
        building: Bâtiment à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    # Limites précises de Malaysia
    malaysia_bounds = {
        'north': 7.363417,
        'south': 0.855222,
        'east': 119.267502,
        'west': 99.643478
    }
    
    if not (malaysia_bounds['south'] <= building.latitude <= malaysia_bounds['north']):
        return False, f"Latitude {building.latitude} hors des limites de Malaysia"
    
    if not (malaysia_bounds['west'] <= building.longitude <= malaysia_bounds['east']):
        return False, f"Longitude {building.longitude} hors des limites de Malaysia"
    
    return True, ""


def validate_building_energy_coherence(building: Building) -> Tuple[bool, List[str]]:
    """
    Valide la cohérence énergétique d'un bâtiment
    
    Args:
        building: Bâtiment à valider
        
    Returns:
        Tuple[bool, List[str]]: (Validité, liste des problèmes)
    """
    issues = []
    
    # Vérification intensité énergétique
    intensity = building.base_consumption_kwh / building.surface_area_m2
    
    expected_ranges = {
        'residential': (0.05, 0.25),
        'commercial': (0.15, 0.40),
        'office': (0.20, 0.50),
        'industrial': (0.30, 0.80),
        'hospital': (0.25, 0.60),
        'school': (0.10, 0.30),
        'hotel': (0.20, 0.50)
    }
    
    expected_range = expected_ranges.get(building.building_type, (0.05, 0.50))
    
    if not (expected_range[0] <= intensity <= expected_range[1]):
        issues.append(
            f"Intensité énergétique anormale: {intensity:.3f} kWh/m²/jour "
            f"(attendu: {expected_range[0]}-{expected_range[1]})"
        )
    
    # Vérification taille vs type
    type_size_ranges = {
        'residential': (30, 1000),
        'commercial': (50, 10000),
        'office': (100, 5000),
        'industrial': (200, 50000),
        'hospital': (500, 20000),
        'school': (300, 10000),
        'hotel': (200, 5000)
    }
    
    size_range = type_size_ranges.get(building.building_type, (10, 100000))
    
    if not (size_range[0] <= building.surface_area_m2 <= size_range[1]):
        issues.append(
            f"Surface anormale pour type {building.building_type}: "
            f"{building.surface_area_m2}m² (attendu: {size_range[0]}-{size_range[1]})"
        )
    
    return len(issues) == 0, issues


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test de création de bâtiment
    building = Building(
        osm_id='test_123',
        latitude=3.1390,
        longitude=101.6869,
        building_type='residential',
        surface_area_m2=150,
        zone_name='kuala_lumpur'
    )
    
    print(f"Bâtiment créé: {building}")
    print(f"Consommation calculée: {building.base_consumption_kwh} kWh/jour")
    print(f"Profil énergétique: {building.get_energy_profile()}")
    
    # Test de validation
    is_valid_coords, error = validate_building_coordinates_malaysia(building)
    print(f"Coordonnées valides: {'✅' if is_valid_coords else '❌'} {error}")
    
    is_coherent, issues = validate_building_energy_coherence(building)
    print(f"Cohérence énergétique: {'✅' if is_coherent else '❌'} {issues}")
    
    # Test de création depuis coordonnées
    building2 = create_building_from_coordinates(
        lat=3.16, lon=101.71, building_type='commercial', zone_name='kuala_lumpur'
    )
    print(f"Bâtiment 2: {building2}")
    
    # Test de distance
    distance = building.distance_to(building2)
    print(f"Distance entre bâtiments: {distance:.2f} km")
    
    # Test de statistiques
    buildings_list = [building, building2]
    stats = calculate_buildings_statistics(buildings_list)
    print(f"Statistiques: {stats['total_buildings']} bâtiments, {stats['surface_statistics']['total_m2']} m² total")
    
    print("✅ Tests du modèle Building terminés")