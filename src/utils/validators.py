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


def validate_timeseries_data(timeseries_list: List[Dict]) -> Tuple[List[Dict], List[str], List[str]]:
    """
    Valide une liste de données de séries temporelles
    
    Args:
        timeseries_list: Liste de dictionnaires de données temporelles
        
    Returns:
        Tuple[List[Dict], List[str], List[str]]: (données_valides, erreurs, warnings)
    """
    valid_data = []
    errors = []
    warnings = []
    
    if not timeseries_list:
        errors.append("Liste de données temporelles vide")
        return valid_data, errors, warnings
    
    required_fields = ['building_id', 'timestamp', 'consumption_kwh']
    
    for i, data_point in enumerate(timeseries_list):
        try:
            # Vérification des champs requis
            missing_fields = [field for field in required_fields if field not in data_point]
            if missing_fields:
                errors.append(f"Point {i}: Champs manquants: {', '.join(missing_fields)}")
                continue
            
            # Validation du timestamp
            is_valid, error = validate_timestamp(data_point['timestamp'])
            if not is_valid:
                errors.append(f"Point {i}: {error}")
                continue
            
            # Validation de la consommation
            is_valid, error = validate_consumption(data_point['consumption_kwh'])
            if not is_valid:
                errors.append(f"Point {i}: {error}")
                continue
            
            # Validation des données optionnelles
            if 'temperature_c' in data_point:
                temp = data_point['temperature_c']
                try:
                    temp_val = float(temp)
                    if temp_val < 10 or temp_val > 50:
                        warnings.append(f"Point {i}: Température suspecte ({temp_val}°C)")
                except (ValueError, TypeError):
                    warnings.append(f"Point {i}: Température invalide")
            
            if 'humidity' in data_point:
                humidity = data_point['humidity']
                try:
                    humidity_val = float(humidity)
                    if humidity_val < 0 or humidity_val > 1:
                        warnings.append(f"Point {i}: Humidité hors plage (0-1): {humidity_val}")
                except (ValueError, TypeError):
                    warnings.append(f"Point {i}: Humidité invalide")
            
            # Point valide
            valid_data.append(data_point)
            
        except Exception as e:
            errors.append(f"Point {i}: Erreur validation ({str(e)})")
    
    return valid_data, errors, warnings


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


def validate_file_size(file_size_bytes: int, max_size_mb: int = 100) -> Tuple[bool, str]:
    """
    Valide la taille d'un fichier
    
    Args:
        file_size_bytes: Taille du fichier en bytes
        max_size_mb: Taille maximum en MB
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    try:
        size_bytes = int(file_size_bytes)
        max_bytes = max_size_mb * 1024 * 1024
        
        if size_bytes < 0:
            return False, "Taille de fichier invalide"
        
        if size_bytes > max_bytes:
            size_mb = size_bytes / (1024 * 1024)
            return False, f"Fichier trop volumineux: {size_mb:.1f} MB (maximum {max_size_mb} MB)"
        
        return True, ""
        
    except (ValueError, TypeError):
        return False, "Taille de fichier doit être un nombre"


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
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
    
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


def validate_percentage(value: Union[int, float]) -> Tuple[bool, str]:
    """
    Valide qu'une valeur est un pourcentage valide (0-100)
    
    Args:
        value: Valeur à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    return validate_numeric_range(value, 0, 100)


def validate_probability(value: Union[int, float]) -> Tuple[bool, str]:
    """
    Valide qu'une valeur est une probabilité valide (0-1)
    
    Args:
        value: Valeur à valider
        
    Returns:
        Tuple[bool, str]: (Validité, message d'erreur)
    """
    return validate_numeric_range(value, 0, 1)


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
    
    # Validation de l'efficacité énergétique
    if 'energy_efficiency_rating' in building_data:
        rating = building_data['energy_efficiency_rating']
        if rating not in ['A', 'B', 'C', 'D', 'E']:
            errors.append(f"Classe énergétique invalide: {rating}")
    
    return len(errors) == 0, errors


def validate_generation_parameters(
    start_date: str, 
    end_date: str, 
    frequency: str, 
    num_buildings: int
) -> Tuple[bool, List[str]]:
    """
    Valide les paramètres complets de génération
    
    Args:
        start_date: Date de début
        end_date: Date de fin
        frequency: Fréquence d'échantillonnage
        num_buildings: Nombre de bâtiments
        
    Returns:
        Tuple[bool, List[str]]: (Validité, liste des erreurs)
    """
    errors = []
    
    # Validation de la plage de dates
    is_valid, error = validate_date_range(start_date, end_date)
    if not is_valid:
        errors.append(error)
    
    # Validation de la fréquence
    is_valid, error = validate_frequency(frequency)
    if not is_valid:
        errors.append(error)
    
    # Validation du nombre de bâtiments
    is_valid, error = validate_numeric_range(num_buildings, 1, 10000)
    if not is_valid:
        errors.append(f"Nombre de bâtiments: {error}")
    
    return len(errors) == 0, errors


def validate_export_request(
    data: Dict, 
    formats: List[str]
) -> Tuple[bool, List[str], List[str]]:
    """
    Valide une requête d'export complète
    
    Args:
        data: Données à exporter
        formats: Formats demandés
        
    Returns:
        Tuple[bool, List[str], List[str]]: (Validité, erreurs, warnings)
    """
    errors = []
    warnings = []
    
    # Validation de la présence de données
    if not data:
        errors.append("Aucune donnée à exporter")
        return False, errors, warnings
    
    # Validation des formats
    allowed_formats = ['csv', 'parquet', 'xlsx', 'json']
    invalid_formats = [f for f in formats if f not in allowed_formats]
    if invalid_formats:
        errors.append(f"Formats non supportés: {', '.join(invalid_formats)}")
    
    # Validation de la structure des données
    if 'buildings' not in data and 'timeseries' not in data:
        errors.append("Données doivent contenir 'buildings' ou 'timeseries'")
    
    # Warnings pour optimisation
    if 'timeseries' in data:
        ts_count = len(data['timeseries'])
        if ts_count > 100000 and 'xlsx' in formats:
            warnings.append("Excel non recommandé pour >100k observations")
        if ts_count > 500000:
            warnings.append("Dataset très volumineux - export long")
    
    return len(errors) == 0, errors, warnings


# ==============================================================================
# VALIDATION AVANCÉE
# ==============================================================================

def validate_data_consistency(buildings: List[Dict], timeseries: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Valide la cohérence entre bâtiments et séries temporelles
    
    Args:
        buildings: Liste des bâtiments
        timeseries: Liste des données temporelles
        
    Returns:
        Tuple[bool, List[str]]: (Cohérent, liste des problèmes)
    """
    issues = []
    
    if not buildings or not timeseries:
        return True, []  # Pas de validation si données manquantes
    
    # Extraction des IDs
    building_ids = {b.get('building_id') for b in buildings if b.get('building_id')}
    timeseries_ids = {ts.get('building_id') for ts in timeseries if ts.get('building_id')}
    
    # Bâtiments sans données temporelles
    missing_timeseries = building_ids - timeseries_ids
    if missing_timeseries:
        issues.append(f"{len(missing_timeseries)} bâtiments sans données temporelles")
    
    # Données temporelles orphelines
    orphan_timeseries = timeseries_ids - building_ids
    if orphan_timeseries:
        issues.append(f"{len(orphan_timeseries)} séries temporelles sans bâtiment associé")
    
    # Validation des types cohérents
    type_mismatches = 0
    for ts in timeseries:
        ts_id = ts.get('building_id')
        ts_type = ts.get('building_type')
        
        # Trouver le bâtiment correspondant
        building = next((b for b in buildings if b.get('building_id') == ts_id), None)
        if building and building.get('building_type') != ts_type:
            type_mismatches += 1
    
    if type_mismatches > 0:
        issues.append(f"{type_mismatches} incohérences de types de bâtiments")
    
    return len(issues) == 0, issues


def validate_data_quality(data: List[Dict], data_type: str) -> Dict:
    """
    Évalue la qualité globale d'un dataset
    
    Args:
        data: Données à évaluer
        data_type: Type de données ('buildings' ou 'timeseries')
        
    Returns:
        Dict: Rapport de qualité avec score et détails
    """
    if not data:
        return {
            'quality_score': 0,
            'issues': ['Dataset vide'],
            'recommendations': ['Vérifier la génération des données']
        }
    
    issues = []
    recommendations = []
    score = 100.0
    
    # Analyse selon le type
    if data_type == 'buildings':
        # Validation des bâtiments
        null_coords = sum(1 for d in data if not d.get('latitude') or not d.get('longitude'))
        if null_coords > 0:
            score -= (null_coords / len(data)) * 30
            issues.append(f"{null_coords} bâtiments sans coordonnées")
            recommendations.append("Vérifier la source des données OSM")
        
        missing_types = sum(1 for d in data if not d.get('building_type'))
        if missing_types > 0:
            score -= (missing_types / len(data)) * 20
            issues.append(f"{missing_types} bâtiments sans type")
    
    elif data_type == 'timeseries':
        # Validation des séries temporelles
        negative_consumption = sum(1 for d in data if d.get('consumption_kwh', 0) < 0)
        if negative_consumption > 0:
            score -= (negative_consumption / len(data)) * 40
            issues.append(f"{negative_consumption} valeurs de consommation négatives")
            recommendations.append("Revoir les paramètres de génération")
        
        null_consumption = sum(1 for d in data if d.get('consumption_kwh') is None)
        if null_consumption > 0:
            score -= (null_consumption / len(data)) * 30
            issues.append(f"{null_consumption} valeurs de consommation manquantes")
    
    # Score final
    final_score = max(0, score)
    
    # Niveau de qualité
    if final_score >= 90:
        quality_level = "Excellente"
    elif final_score >= 75:
        quality_level = "Bonne"
    elif final_score >= 60:
        quality_level = "Acceptable"
    else:
        quality_level = "Problématique"
    
    return {
        'quality_score': round(final_score, 1),
        'quality_level': quality_level,
        'total_records': len(data),
        'issues': issues,
        'recommendations': recommendations
    }


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def get_validation_summary(validations: List[Tuple[bool, str]]) -> Dict:
    """
    Génère un résumé de plusieurs validations
    
    Args:
        validations: Liste de tuples (validité, message)
        
    Returns:
        Dict: Résumé des validations
    """
    total = len(validations)
    passed = sum(1 for valid, _ in validations if valid)
    failed = total - passed
    
    errors = [msg for valid, msg in validations if not valid and msg]
    
    return {
        'total_validations': total,
        'passed': passed,
        'failed': failed,
        'success_rate': (passed / total * 100) if total > 0 else 0,
        'errors': errors,
        'overall_valid': failed == 0
    }


def validate_all_building_data(buildings_list: List[Dict]) -> Dict:
    """
    Valide une liste complète de bâtiments
    
    Args:
        buildings_list: Liste de dictionnaires de bâtiments
        
    Returns:
        Dict: Rapport de validation complet
    """
    valid_buildings = []
    all_errors = []
    
    for i, building in enumerate(buildings_list):
        is_valid, errors = validate_building_data(building)
        if is_valid:
            valid_buildings.append(building)
        else:
            for error in errors:
                all_errors.append(f"Bâtiment {i}: {error}")
    
    return {
        'total_buildings': len(buildings_list),
        'valid_buildings': len(valid_buildings),
        'invalid_buildings': len(buildings_list) - len(valid_buildings),
        'success_rate': (len(valid_buildings) / len(buildings_list) * 100) if buildings_list else 0,
        'errors': all_errors,
        'valid_data': valid_buildings
    }


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Tests des fonctions de validation
    print("🧪 Tests des validations:")
    
    # Test coordonnées
    valid, error = validate_coordinates_malaysia(3.15, 101.7)
    print(f"Coordonnées KL: {'✅' if valid else '❌'} {error}")
    
    # Test type de bâtiment
    valid, error = validate_building_type('residential')
    print(f"Type résidentiel: {'✅' if valid else '❌'} {error}")
    
    # Test date
    valid, error = validate_date_range('2024-01-01', '2024-01-31')
    print(f"Dates janvier: {'✅' if valid else '❌'} {error}")
    
    # Test données de bâtiment complet
    test_building = {
        'building_id': 'B001',
        'latitude': 3.15,
        'longitude': 101.7,
        'building_type': 'residential',
        'surface_area_m2': 150
    }
    
    valid, errors = validate_building_data(test_building)
    print(f"Bâtiment test: {'✅' if valid else '❌'} {errors}")
    
    print("✅ Tests de validation terminés")