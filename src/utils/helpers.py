"""
Fonctions utilitaires et helpers pour Malaysia Electricity Generator
===================================================================

Ce module contient des fonctions d'aide générales utilisées dans toute
l'application pour éviter la duplication de code.
"""

import math
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# ==============================================================================
# CALCULS GÉOGRAPHIQUES
# ==============================================================================

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance entre deux points géographiques en kilomètres
    
    Args:
        lat1, lon1: Coordonnées du premier point
        lat2, lon2: Coordonnées du second point
        
    Returns:
        float: Distance en kilomètres
    """
    # Rayon de la Terre en km
    R = 6371.0
    
    # Conversion en radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Différences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Formule de Haversine
    a = (math.sin(dlat / 2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_bbox_area(bbox: List[float]) -> float:
    """
    Calcule l'aire approximative d'une bounding box en km²
    
    Args:
        bbox: [west, south, east, north] en degrés
        
    Returns:
        float: Aire en km²
    """
    if len(bbox) != 4:
        return 0.0
    
    west, south, east, north = bbox
    
    # Points pour le calcul
    sw = (south, west)  # Sud-Ouest
    se = (south, east)  # Sud-Est
    nw = (north, west)  # Nord-Ouest
    
    # Largeur et hauteur
    width_km = calculate_distance_km(sw[0], sw[1], se[0], se[1])
    height_km = calculate_distance_km(sw[0], sw[1], nw[0], nw[1])
    
    return width_km * height_km


def get_centroid(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calcule le centroïde d'une liste de coordonnées
    
    Args:
        coordinates: Liste de tuples (lat, lon)
        
    Returns:
        Tuple[float, float]: (latitude, longitude) du centroïde
    """
    if not coordinates:
        return (3.1390, 101.6869)  # Kuala Lumpur par défaut
    
    total_lat = sum(coord[0] for coord in coordinates)
    total_lon = sum(coord[1] for coord in coordinates)
    count = len(coordinates)
    
    return (total_lat / count, total_lon / count)


# ==============================================================================
# FORMATAGE ET CONVERSION
# ==============================================================================

def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible
    
    Args:
        seconds: Durée en secondes
        
    Returns:
        str: Durée formatée (ex: "2h 15m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f"{hours}h {remaining_minutes}m"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    return f"{days}j {remaining_hours}h"


def format_file_size(size_bytes: int) -> str:
    """
    Formate une taille de fichier en format lisible
    
    Args:
        size_bytes: Taille en bytes
        
    Returns:
        str: Taille formatée (ex: "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def format_number_french(number: Union[int, float]) -> str:
    """
    Formate un nombre selon la locale française
    
    Args:
        number: Nombre à formater
        
    Returns:
        str: Nombre formaté
    """
    if isinstance(number, float):
        return f"{number:,.2f}".replace(',', ' ').replace('.', ',')
    else:
        return f"{number:,}".replace(',', ' ')


def safe_float_parse(value: Any, default: float = 0.0) -> float:
    """
    Parse une valeur en float de manière sécurisée
    
    Args:
        value: Valeur à parser
        default: Valeur par défaut si parsing échoue
        
    Returns:
        float: Valeur parsée ou défaut
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_parse(value: Any, default: int = 0) -> int:
    """
    Parse une valeur en int de manière sécurisée
    
    Args:
        value: Valeur à parser
        default: Valeur par défaut si parsing échoue
        
    Returns:
        int: Valeur parsée ou défaut
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ==============================================================================
# MANIPULATION DE DONNÉES
# ==============================================================================

def normalize_building_type(building_type: str) -> str:
    """
    Normalise un type de bâtiment
    
    Args:
        building_type: Type original
        
    Returns:
        str: Type normalisé
    """
    if not building_type:
        return 'residential'
    
    normalized = building_type.lower().strip()
    
    # Mapping des types alternatifs
    type_mapping = {
        'house': 'residential',
        'apartment': 'residential',
        'flat': 'residential',
        'home': 'residential',
        'shop': 'commercial',
        'store': 'commercial',
        'retail': 'commercial',
        'mall': 'commercial',
        'factory': 'industrial',
        'plant': 'industrial',
        'manufacturing': 'industrial',
        'clinic': 'hospital',
        'medical': 'hospital',
        'university': 'school',
        'college': 'school',
        'education': 'school',
        'yes': 'residential'  # Tag OSM générique
    }
    
    return type_mapping.get(normalized, normalized)


def chunk_list(data: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Divise une liste en chunks de taille donnée
    
    Args:
        data: Liste à diviser
        chunk_size: Taille des chunks
        
    Returns:
        List[List[Any]]: Liste de chunks
    """
    if chunk_size <= 0:
        return [data]
    
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def deep_merge_dict(dict1: Dict, dict2: Dict) -> Dict:
    """
    Fusionne récursivement deux dictionnaires
    
    Args:
        dict1: Premier dictionnaire
        dict2: Second dictionnaire (prioritaire)
        
    Returns:
        Dict: Dictionnaire fusionné
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def filter_dict_keys(data: Dict, allowed_keys: List[str]) -> Dict:
    """
    Filtre un dictionnaire pour ne garder que certaines clés
    
    Args:
        data: Dictionnaire source
        allowed_keys: Clés autorisées
        
    Returns:
        Dict: Dictionnaire filtré
    """
    return {key: value for key, value in data.items() if key in allowed_keys}


def flatten_dict(data: Dict, separator: str = '.') -> Dict:
    """
    Aplatit un dictionnaire imbriqué
    
    Args:
        data: Dictionnaire à aplatir
        separator: Séparateur pour les clés imbriquées
        
    Returns:
        Dict: Dictionnaire aplati
    """
    def _flatten(obj, parent_key=''):
        items = []
        for key, value in obj.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(_flatten(value, new_key).items())
            else:
                items.append((new_key, value))
        return dict(items)
    
    return _flatten(data)


# ==============================================================================
# GÉNÉRATION D'IDENTIFIANTS
# ==============================================================================

def generate_unique_id(prefix: str = '', length: int = 8) -> str:
    """
    Génère un identifiant unique
    
    Args:
        prefix: Préfixe optionnel
        length: Longueur de la partie unique
        
    Returns:
        str: Identifiant unique
    """
    unique_part = str(uuid.uuid4()).replace('-', '')[:length]
    return f"{prefix}{unique_part}" if prefix else unique_part


def generate_building_id(building_type: str, zone_name: str) -> str:
    """
    Génère un ID de bâtiment descriptif
    
    Args:
        building_type: Type de bâtiment
        zone_name: Nom de la zone
        
    Returns:
        str: ID du bâtiment
    """
    # Première lettre du type
    type_prefix = building_type[0].upper() if building_type else 'B'
    
    # Code zone (3 premières lettres)
    zone_code = zone_name.replace('_', '').upper()[:3] if zone_name else 'ZON'
    
    # Partie unique
    unique_part = generate_unique_id(length=6)
    
    return f"{type_prefix}{zone_code}{unique_part}"


def generate_session_id() -> str:
    """
    Génère un ID de session unique
    
    Returns:
        str: ID de session
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_part = generate_unique_id(length=6)
    return f"session_{timestamp}_{unique_part}"


# ==============================================================================
# MANIPULATION DE DATES
# ==============================================================================

def parse_date_flexible(date_string: str) -> Optional[datetime]:
    """
    Parse une date avec plusieurs formats possibles
    
    Args:
        date_string: Chaîne de date
        
    Returns:
        Optional[datetime]: Date parsée ou None
    """
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%d/%m/%Y',
        '%d-%m-%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None


def get_malaysia_time() -> datetime:
    """
    Retourne l'heure actuelle en timezone Malaysia
    
    Returns:
        datetime: Heure Malaysia (UTC+8)
    """
    from datetime import timezone
    malaysia_tz = timezone(timedelta(hours=8))
    return datetime.now(malaysia_tz)


def calculate_time_difference(start: datetime, end: datetime) -> Dict[str, int]:
    """
    Calcule la différence entre deux dates
    
    Args:
        start: Date de début
        end: Date de fin
        
    Returns:
        Dict[str, int]: Différence en jours, heures, minutes, secondes
    """
    diff = end - start
    
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return {
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'total_seconds': int(diff.total_seconds())
    }


# ==============================================================================
# HASH ET SÉCURITÉ
# ==============================================================================

def calculate_hash(data: Union[str, bytes]) -> str:
    """
    Calcule le hash SHA-256 de données
    
    Args:
        data: Données à hasher
        
    Returns:
        str: Hash hexadécimal
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()


def calculate_data_fingerprint(data: Dict) -> str:
    """
    Calcule une empreinte unique pour un dictionnaire de données
    
    Args:
        data: Dictionnaire de données
        
    Returns:
        str: Empreinte unique
    """
    # Sérialisation déterministe
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return calculate_hash(json_str)[:16]  # 16 premiers caractères


def obfuscate_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """
    Obfusque les données sensibles
    
    Args:
        text: Texte à obfusquer
        visible_chars: Nombre de caractères visibles au début/fin
        
    Returns:
        str: Texte obfusqué
    """
    if not text or len(text) <= visible_chars * 2:
        return '*' * len(text)
    
    start = text[:visible_chars]
    end = text[-visible_chars:]
    middle = '*' * (len(text) - visible_chars * 2)
    
    return f"{start}{middle}{end}"


# ==============================================================================
# PERFORMANCE ET CACHE
# ==============================================================================

def measure_execution_time(func):
    """
    Décorateur pour mesurer le temps d'exécution
    
    Args:
        func: Fonction à mesurer
        
    Returns:
        Function: Fonction décorée
    """
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ {func.__name__} exécuté en {format_duration(duration)}")
        
        return result
    
    return wrapper


class SimpleCache:
    """Cache simple en mémoire avec TTL"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialise le cache
        
        Args:
            default_ttl: Time-to-live par défaut en secondes
        """
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache"""
        if key not in self._cache:
            return None
        
        # Vérification TTL
        if self._is_expired(key):
            self.delete(key)
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Stocke une valeur dans le cache"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
        if ttl:
            self._timestamps[key + '_ttl'] = ttl
    
    def delete(self, key: str) -> None:
        """Supprime une valeur du cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._timestamps.pop(key + '_ttl', None)
    
    def clear(self) -> None:
        """Vide le cache"""
        self._cache.clear()
        self._timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Vérifie si une clé a expiré"""
        if key not in self._timestamps:
            return True
        
        ttl = self._timestamps.get(key + '_ttl', self.default_ttl)
        age = (datetime.now() - self._timestamps[key]).total_seconds()
        
        return age > ttl


# ==============================================================================
# HELPERS SPÉCIFIQUES MALAYSIA
# ==============================================================================

def get_malaysia_states() -> List[str]:
    """
    Retourne la liste des états de Malaysia
    
    Returns:
        List[str]: États de Malaysia
    """
    return [
        'Johor', 'Kedah', 'Kelantan', 'Malacca', 'Negeri Sembilan',
        'Pahang', 'Penang', 'Perak', 'Perlis', 'Sabah', 'Sarawak',
        'Selangor', 'Terengganu', 'Federal Territory of Kuala Lumpur',
        'Federal Territory of Labuan', 'Federal Territory of Putrajaya'
    ]


def get_malaysia_major_cities() -> Dict[str, Tuple[float, float]]:
    """
    Retourne les principales villes de Malaysia avec coordonnées
    
    Returns:
        Dict[str, Tuple[float, float]]: Villes et coordonnées
    """
    return {
        'Kuala Lumpur': (3.1390, 101.6869),
        'George Town': (5.4164, 100.3327),
        'Ipoh': (4.5975, 101.0901),
        'Shah Alam': (3.0733, 101.5185),
        'Petaling Jaya': (3.1073, 101.6067),
        'Johor Bahru': (1.4927, 103.7414),
        'Malacca City': (2.2055, 102.2501),
        'Alor Setar': (6.1184, 100.3681),
        'Kota Kinabalu': (5.9804, 116.0735),
        'Kuching': (1.5535, 110.3593)
    }


def is_malaysia_holiday(date_obj: datetime) -> bool:
    """
    Vérifie si une date est un jour férié en Malaysia (approximatif)
    
    Args:
        date_obj: Date à vérifier
        
    Returns:
        bool: True si jour férié
    """
    # Jours fériés fixes (approximatifs)
    fixed_holidays = [
        (1, 1),   # Nouvel An
        (2, 1),   # Territoire Fédéral
        (5, 1),   # Fête du Travail
        (6, 1),   # Fête de Gawai Dayak
        (8, 31),  # Fête Nationale
        (9, 16),  # Jour de Malaysia
        (12, 25), # Noël
    ]
    
    month_day = (date_obj.month, date_obj.day)
    return month_day in fixed_holidays


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Tests des fonctions helpers
    print("🧪 Tests des fonctions helpers:")
    
    # Test distance
    kl_coords = (3.1390, 101.6869)
    penang_coords = (5.4164, 100.3327)
    distance = calculate_distance_km(*kl_coords, *penang_coords)
    print(f"Distance KL-Penang: {distance:.1f} km")
    
    # Test formatage
    print(f"Durée: {format_duration(3725)}")  # 1h 2m 5s
    print(f"Taille: {format_file_size(1536000)}")  # 1.46 MB
    
    # Test ID
    building_id = generate_building_id('residential', 'kuala_lumpur')
    print(f"ID bâtiment: {building_id}")
    
    # Test cache
    cache = SimpleCache()
    cache.set('test', 'valeur', ttl=10)
    print(f"Cache test: {cache.get('test')}")
    
    print("✅ Tests terminés")
