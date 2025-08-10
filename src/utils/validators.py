"""
Fonctions de validation pour Malaysia Electricity Generator
==========================================================

Ce module contient toutes les fonctions de validation utilisées
dans l'application pour assurer la qualité des données.
"""

import re
import json
from datetime import datetime, date
from typing import Union, List, Dict, Tuple, Any
import logging

from .constants import MALAYSIA_BOUNDS, BUILDING_TYPES, SUPPORTED_FREQUENCIES


logger = logging.getLogger(__name__)


# ==============================================================================
# VALIDATION GÉOGRAPHIQUE
# ==============================================================================

def validate_coordinates_malaysia(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Valide que les coordonnées sont dans les limites de Malaysia
    
    Args:
        latitude: Latitude à valider
        longitude: Longitude à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur si invalide)
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        # Vérification des limites Malaysia
        if not (MALAYSIA_BOUNDS['min_lat'] <= lat <= MALAYSIA_BOUNDS['max_lat']):
            return False, f"Latitude {lat} hors limites Malaysia ({MALAYSIA_BOUNDS['min_lat']} - {MALAYSIA_BOUNDS['max_lat']})"
        
        if not (MALAYSIA_BOUNDS['min_lon'] <= lon <= MALAYSIA_BOUNDS['max_lon']):
            return False, f"Longitude {lon} hors limites Malaysia ({MALAYSIA_BOUNDS['min_lon']} - {MALAYSIA_BOUNDS['max_lon']})"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Coordonnées doivent être des nombres valides"


def validate_bbox(bbox: List[float]) -> Tuple[bool, str]:
    """
    Valide une bounding box [west, south, east, north]
    
    Args:
        bbox: Liste de 4 coordonnées
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False, "Bounding box doit contenir 4 coordonnées [west, south, east, north]"
    
    try:
        west, south, east, north = [float(x) for x in bbox]
        
        # Vérification logique
        if west >= east:
            return False, "West doit être inférieur à East"
        
        if south >= north:
            return False, "South doit être inférieur à North"
        
        # Vérification que la bbox touche Malaysia
        if (east < MALAYSIA_BOUNDS['min_lon'] or west > MALAYSIA_BOUNDS['max_lon'] or
            north < MALAYSIA_BOUNDS['min_lat'] or south > MALAYSIA_BOUNDS['max_lat']):
            return False, "Bounding box ne touche pas Malaysia"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Coordonnées de bounding box doivent être des nombres"


# ==============================================================================
# VALIDATION DES BÂTIMENTS
# ==============================================================================

def validate_building_type(building_type: str) -> Tuple[bool, str]:
    """
    Valide un type de bâtiment
    
    Args:
        building_type: Type de bâtiment à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not building_type or not isinstance(building_type, str):
        return False, "Type de bâtiment requis"
    
    normalized_type = building_type.lower().strip()
    
    if normalized_type in BUILDING_TYPES:
        return True, ""
    
    # Types alternatifs acceptés
    alternative_types = {
        'house': 'residential',
        'apartment': 'residential',
        'flat': 'residential',
        'shop': 'commercial',
        'store': 'commercial',
        'mall': 'commercial',
        'factory': 'industrial',
        'plant': 'industrial',
        'clinic': 'hospital',
        'university': 'school',
        'college': 'school'
    }
    
    if normalized_type in alternative_types:
        return True, f"Type '{building_type}' converti en '{alternative_types[normalized_type]}'"
    
    return False, f"Type de bâtiment '{building_type}' non reconnu. Types supportés: {', '.join(BUILDING_TYPES)}"


def validate_building_surface(surface_m2: float) -> Tuple[bool, str]:
    """
    Valide la surface d'un bâtiment
    
    Args:
        surface_m2: Surface en mètres carrés
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        surface = float(surface_m2)
        
        if surface <= 0:
            return False, "Surface doit être positive"
        
        if surface < 10:
            return False, "Surface trop petite (minimum 10 m²)"
        
        if surface > 1000000:  # 1 km²
            return False, "Surface trop grande (maximum 1,000,000 m²)"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Surface doit être un nombre valide"


def validate_consumption(consumption_kwh: float) -> Tuple[bool, str]:
    """
    Valide une valeur de consommation électrique
    
    Args:
        consumption_kwh: Consommation en kWh
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        consumption = float(consumption_kwh)
        
        if consumption < 0:
            return False, "Consommation ne peut pas être négative"
        
        if consumption > 10000:  # 10 MW
            return False, "Consommation trop élevée (maximum 10,000 kWh)"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Consommation doit être un nombre valide"


# ==============================================================================
# VALIDATION TEMPORELLE
# ==============================================================================

def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, str]:
    """
    Valide une plage de dates
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start >= end:
            return False, "Date de fin doit être après date de début"
        
        # Vérification durée maximum (2 ans)
        duration_days = (end - start).days
        if duration_days > 730:
            return False, f"Période trop longue: {duration_days} jours (maximum 730 jours)"
        
        # Vérification que les dates ne sont pas trop dans le futur
        today = date.today()
        if start > today:
            return False, "Date de début ne peut pas être dans le futur"
        
        return True, ""
        
    except ValueError:
        return False, "Format de date invalide (utiliser YYYY-MM-DD)"


def validate_frequency(frequency: str) -> Tuple[bool, str]:
    """
    Valide une fréquence d'échantillonnage
    
    Args:
        frequency: Fréquence pandas (ex: '30T', '1H')
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not frequency or not isinstance(frequency, str):
        return False, "Fréquence requise"
    
    freq = frequency.strip().upper()
    
    if freq in SUPPORTED_FREQUENCIES:
        return True, ""
    
    return False, f"Fréquence '{frequency}' non supportée. Fréquences disponibles: {', '.join(SUPPORTED_FREQUENCIES.keys())}"


def validate_timestamp(timestamp: Union[str, datetime]) -> Tuple[bool, str]:
    """
    Valide un timestamp
    
    Args:
        timestamp: Timestamp à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        if isinstance(timestamp, str):
            # Tentative de parsing de différents formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d'
            ]
            
            parsed = None
            for fmt in formats:
                try:
                    parsed = datetime.strptime(timestamp, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed is None:
                return False, "Format de timestamp non reconnu"
            
        elif isinstance(timestamp, datetime):
            parsed = timestamp
        else:
            return False, "Timestamp doit être une chaîne ou datetime"
        
        # Vérification de plausibilité
        min_date = datetime(2000, 1, 1)
        max_date = datetime(2030, 12, 31)
        
        if parsed < min_date or parsed > max_date:
            return False, f"Timestamp hors plage valide ({min_date.year}-{max_date.year})"
        
        return True, ""
        
    except Exception as e:
        return False, f"Erreur validation timestamp: {str(e)}"


# ==============================================================================
# VALIDATION DES FICHIERS
# ==============================================================================

def sanitize_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour le rendre sûr
    
    Args:
        filename: Nom de fichier à nettoyer
        
    Returns:
        str: Nom de fichier nettoyé
    """
    if not filename:
        return "unnamed_file"
    
    # Supprimer les caractères dangereux
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Supprimer les points de début/fin
    safe_filename = safe_filename.strip('. ')
    
    # Limiter la longueur
    if len(safe_filename) > 200:
        name, ext = safe_filename.rsplit('.', 1) if '.' in safe_filename else (safe_filename, '')
        safe_filename = name[:190] + ('.' + ext if ext else '')
    
    return safe_filename or "unnamed_file"


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> Tuple[bool, str]:
    """
    Valide l'extension d'un fichier
    
    Args:
        filename: Nom du fichier
        allowed_extensions: Extensions autorisées (ex: ['.csv', '.json'])
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not filename:
        return False, "Nom de fichier requis"
    
    if '.' not in filename:
        return False, "Fichier sans extension"
    
    extension = '.' + filename.split('.')[-1].lower()
    
    if extension in [ext.lower() for ext in allowed_extensions]:
        return True, ""
    
    return False, f"Extension '{extension}' non autorisée. Extensions supportées: {', '.join(allowed_extensions)}"


# ==============================================================================
# VALIDATION DES DONNÉES
# ==============================================================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Valide une adresse email
    
    Args:
        email: Adresse email à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not email:
        return False, "Email requis"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return True, ""
    
    return False, "Format d'email invalide"


def validate_json_structure(data: Any, required_fields: List[str]) -> Tuple[bool, str]:
    """
    Valide la structure d'un objet JSON
    
    Args:
        data: Données à valider
        required_fields: Champs requis
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    if not isinstance(data, dict):
        return False, "Données doivent être un objet JSON"
    
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Champs manquants: {', '.join(missing_fields)}"
    
    return True, ""


def validate_numeric_range(value: Union[int, float], min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
    """
    Valide qu'une valeur numérique est dans une plage
    
    Args:
        value: Valeur à valider
        min_val: Valeur minimum (optionnel)
        max_val: Valeur maximum (optionnel)
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        num_value = float(value)
        
        if min_val is not None and num_value < min_val:
            return False, f"Valeur {num_value} inférieure au minimum {min_val}"
        
        if max_val is not None and num_value > max_val:
            return False, f"Valeur {num_value} supérieure au maximum {max_val}"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Valeur doit être numérique"


# ==============================================================================
# VALIDATION COMPOSITE
# ==============================================================================

def validate_building_data(building_data: Dict) -> Tuple[bool, List[str]]:
    """
    Valide complètement les données d'un bâtiment
    
    Args:
        building_data: Dictionnaire contenant les données du bâtiment
        
    Returns:
        Tuple[bool, List[str]]: (Validité, liste des erreurs)
    """
    errors = []
    
    # Champs requis
    required_fields = ['building_id', 'latitude', 'longitude', 'building_type']
    is_valid, error = validate_json_structure(building_data, required_fields)
    if not is_valid:
        errors.append(error)
        return False, errors
    
    # Validation des coordonnées
    is_valid, error = validate_coordinates_malaysia(
        building_data['latitude'], 
        building_data['longitude']
    )
    if not is_valid:
        errors.append(error)
    
    # Validation du type
    is_valid, error = validate_building_type(building_data['building_type'])
    if not is_valid:
        errors.append(error)
    
    # Validation de la surface si présente
    if 'surface_area_m2' in building_data:
        is_valid, error = validate_building_surface(building_data['surface_area_m2'])
        if not is_valid:
            errors.append(error)
    
    # Validation de la consommation si présente
    if 'base_consumption_kwh' in building_data:
        is_valid, error = validate_consumption(building_data['base_consumption_kwh'])
        if not is_valid:
            errors.append(error)
    
    return len(errors) == 0, errors


def validate_times