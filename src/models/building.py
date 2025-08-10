"""
Modèle de données pour les bâtiments
===================================

Ce module définit la structure de données pour représenter un bâtiment
avec toutes ses métadonnées nécessaires à la génération électrique.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid


@dataclass
class Building:
    """
    Modèle de données pour un bâtiment avec métadonnées complètes
    
    Cette classe représente un bâtiment avec toutes les informations
    nécessaires pour générer des données de consommation électrique réalistes.
    """
    
    # Identifiants uniques
    building_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    osm_id: Optional[str] = None
    
    # Informations géographiques
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = None
    zone_name: Optional[str] = None
    state: Optional[str] = None
    
    # Caractéristiques du bâtiment
    building_type: str = 'residential'
    subtype: Optional[str] = None
    surface_area_m2: float = 100.0
    floors_count: int = 1
    construction_year: Optional[int] = None
    
    # Paramètres électriques
    base_consumption_kwh: float = 0.0
    peak_consumption_kwh: float = 0.0
    energy_efficiency_rating: str = 'C'  # A, B, C, D, E
    has_solar_panels: bool = False
    has_air_conditioning: bool = True
    
    # Occupation et usage
    occupancy_type: str = 'standard'  # standard, high, low, vacant
    operating_hours_start: int = 6    # heure de début d'activité
    operating_hours_end: int = 22     # heure de fin d'activité
    weekends_active: bool = True      # actif les weekends
    
    # Métadonnées OSM
    osm_tags: Dict[str, str] = field(default_factory=dict)
    osm_geometry: List[Tuple[float, float]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validation et calculs automatiques après création"""
        self._validate_coordinates()
        self._calculate_base_consumption()
        self._set_default_subtype()
        self._validate_energy_rating()
    
    def _validate_coordinates(self):
        """Valide que les coordonnées sont dans les limites de Malaysia"""
        if not (0.5 <= self.latitude <= 7.5):
            raise ValueError(f"Latitude {self.latitude} hors limites Malaysia")
        if not (99.0 <= self.longitude <= 120.0):
            raise ValueError(f"Longitude {self.longitude} hors limites Malaysia")
    
    def _calculate_base_consumption(self):
        """Calcule la consommation de base selon le type et la taille"""
        # Facteurs de consommation par type (kWh/m²/jour)
        consumption_factors = {
            'residential': 0.15,
            'commercial': 0.25,
            'office': 0.30,
            'industrial': 0.45,
            'hospital': 0.60,
            'school': 0.20,
            'hotel': 0.40,
            'warehouse': 0.10
        }
        
        factor = consumption_factors.get(self.building_type, 0.15)
        
        # Consommation de base par jour
        daily_base = self.surface_area_m2 * factor
        
        # Conversion en consommation horaire moyenne
        self.base_consumption_kwh = daily_base / 24
        
        # Consommation de pic (1.5x à 3x la base selon le type)
        peak_multipliers = {
            'residential': 2.0,
            'commercial': 2.5,
            'office': 2.0,
            'industrial': 1.5,
            'hospital': 1.3,  # plus constant
            'school': 3.0,    # pics très marqués
            'hotel': 1.8,
            'warehouse': 1.5
        }
        
        multiplier = peak_multipliers.get(self.building_type, 2.0)
        self.peak_consumption_kwh = self.base_consumption_kwh * multiplier
    
    def _set_default_subtype(self):
        """Définit un sous-type par défaut si non spécifié"""
        if self.subtype is None:
            default_subtypes = {
                'residential': 'house',
                'commercial': 'shop',
                'office': 'general',
                'industrial': 'manufacturing',
                'hospital': 'general',
                'school': 'primary',
                'hotel': 'business',
                'warehouse': 'storage'
            }
            self.subtype = default_subtypes.get(self.building_type, 'standard')
    
    def _validate_energy_rating(self):
        """Valide la classe énergétique"""
        valid_ratings = ['A', 'B', 'C', 'D', 'E']
        if self.energy_efficiency_rating not in valid_ratings:
            self.energy_efficiency_rating = 'C'  # défaut
    
    def get_efficiency_factor(self) -> float:
        """Retourne le facteur d'efficacité énergétique (0.7 à 1.3)"""
        efficiency_factors = {
            'A': 0.7,   # très efficace
            'B': 0.85,  # efficace
            'C': 1.0,   # standard
            'D': 1.15,  # peu efficace
            'E': 1.3    # inefficace
        }
        return efficiency_factors.get(self.energy_efficiency_rating, 1.0)
    
    def get_climate_sensitivity(self) -> float:
        """Retourne la sensibilité climatique (impact de la température)"""
        # Plus élevé = plus sensible aux variations de température
        climate_sensitivity = {
            'residential': 1.2,
            'commercial': 1.5,  # besoins de climatisation importants
            'office': 1.3,
            'industrial': 0.8,  # moins sensible
            'hospital': 1.1,    # contrôle strict de température
            'school': 1.4,
            'hotel': 1.6,       # confort client prioritaire
            'warehouse': 0.6    # peu climatisé
        }
        
        base_sensitivity = climate_sensitivity.get(self.building_type, 1.0)
        
        # Ajustement selon la climatisation
        if not self.has_air_conditioning:
            base_sensitivity *= 0.3
        
        return base_sensitivity
    
    def is_active_at_hour(self, hour: int, is_weekend: bool = False) -> bool:
        """Détermine si le bâtiment est actif à une heure donnée"""
        # Si fermé les weekends et c'est le weekend
        if is_weekend and not self.weekends_active:
            return False
        
        # Vérifier les heures d'ouverture
        if self.operating_hours_start <= self.operating_hours_end:
            # Heures normales (ex: 8h à 18h)
            return self.operating_hours_start <= hour <= self.operating_hours_end
        else:
            # Heures qui passent minuit (ex: 22h à 6h)
            return hour >= self.operating_hours_start or hour <= self.operating_hours_end
    
    def get_occupancy_factor(self) -> float:
        """Retourne le facteur d'occupation (0.5 à 1.5)"""
        occupancy_factors = {
            'vacant': 0.1,      # bâtiment vide
            'low': 0.6,         # faible occupation
            'standard': 1.0,    # occupation normale
            'high': 1.4,        # haute occupation
            'overcrowded': 1.8  # suroccupé
        }
        return occupancy_factors.get(self.occupancy_type, 1.0)
    
    def to_dict(self) -> Dict:
        """Convertit le bâtiment en dictionnaire pour export"""
        return {
            'building_id': self.building_id,
            'osm_id': self.osm_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'zone_name': self.zone_name,
            'state': self.state,
            'building_type': self.building_type,
            'subtype': self.subtype,
            'surface_area_m2': self.surface_area_m2,
            'floors_count': self.floors_count,
            'construction_year': self.construction_year,
            'base_consumption_kwh': self.base_consumption_kwh,
            'peak_consumption_kwh': self.peak_consumption_kwh,
            'energy_efficiency_rating': self.energy_efficiency_rating,
            'has_solar_panels': self.has_solar_panels,
            'has_air_conditioning': self.has_air_conditioning,
            'occupancy_type': self.occupancy_type,
            'operating_hours_start': self.operating_hours_start,
            'operating_hours_end': self.operating_hours_end,
            'weekends_active': self.weekends_active,
            'efficiency_factor': self.get_efficiency_factor(),
            'climate_sensitivity': self.get_climate_sensitivity(),
            'occupancy_factor': self.get_occupancy_factor(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_osm_data(cls, osm_element: Dict, zone_name: str = None) -> 'Building':
        """
        Crée un bâtiment à partir de données OSM
        
        Args:
            osm_element: Élément OSM avec géométrie et tags
            zone_name: Nom de la zone/ville
            
        Returns:
            Instance Building créée à partir des données OSM
        """
        # Extraction des coordonnées depuis la géométrie
        if osm_element.get('geometry'):
            # Prendre le centroïde pour la position principale
            lats = [point['lat'] for point in osm_element['geometry']]
            lons = [point['lon'] for point in osm_element['geometry']]
            latitude = sum(lats) / len(lats)
            longitude = sum(lons) / len(lons)
            geometry = [(point['lat'], point['lon']) for point in osm_element['geometry']]
        else:
            latitude = osm_element.get('lat', 3.15)  # défaut KL
            longitude = osm_element.get('lon', 101.7)
            geometry = []
        
        # Extraction des tags OSM
        tags = osm_element.get('tags', {})
        
        # Détermination du type de bâtiment
        building_type = tags.get('building', 'residential')
        if building_type == 'yes':  # tag générique
            building_type = 'residential'
        
        # Estimation de la surface (simplifiée)
        if geometry and len(geometry) > 2:
            # Calcul approximatif de l'aire du polygone (formule du lacet)
            area = 0
            for i in range(len(geometry)):
                j = (i + 1) % len(geometry)
                area += geometry[i][0] * geometry[j][1]
                area -= geometry[j][0] * geometry[i][1]
            surface_area = abs(area) / 2 * 111000 * 111000  # conversion degrés -> m²
            surface_area = max(50, min(surface_area, 10000))  # bornes réalistes
        else:
            # Surface par défaut selon le type
            default_surfaces = {
                'residential': 150,
                'commercial': 300,
                'office': 500,
                'industrial': 1000,
                'hospital': 2000,
                'school': 800
            }
            surface_area = default_surfaces.get(building_type, 150)
        
        # Création du bâtiment
        return cls(
            osm_id=str(osm_element.get('id', '')),
            latitude=latitude,
            longitude=longitude,
            zone_name=zone_name,
            building_type=building_type,
            surface_area_m2=surface_area,
            floors_count=int(tags.get('building:levels', '1')),
            osm_tags=tags,
            osm_geometry=geometry
        )
    
    def update_from_generation_params(self, **params):
        """Met à jour les paramètres du bâtiment pour la génération"""
        self.updated_at = datetime.now()
        
        # Mise à jour sélective des paramètres
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Recalcul automatique après mise à jour
        self._calculate_base_consumption()


# ==============================================================================
# FONCTIONS UTILITAIRES POUR LES BÂTIMENTS
# ==============================================================================

def create_building_from_coordinates(lat: float, lon: float, building_type: str = 'residential', **kwargs) -> Building:
    """
    Crée un bâtiment rapidement à partir de coordonnées
    
    Args:
        lat: Latitude
        lon: Longitude  
        building_type: Type de bâtiment
        **kwargs: Paramètres additionnels
        
    Returns:
        Building: Instance de bâtiment créée
    """
    return Building(
        latitude=lat,
        longitude=lon,
        building_type=building_type,
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
            
            valid_buildings.append(building)
            
        except Exception as e:
            errors.append(f"Bâtiment {i}: {str(e)}")
    
    return valid_buildings, errors
