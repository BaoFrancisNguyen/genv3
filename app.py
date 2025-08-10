"""
Application Flask principale - Générateur électrique Malaysia
===========================================================

Application complète avec gestion d'erreurs robuste.
"""

from flask import Flask, request, jsonify, render_template, send_file
import logging
import traceback
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

# Imports des modules
from config import APP_CONFIG, LOGGING_CONFIG, initialize_config
from src.core.osm_handler import OSMHandler
from src.core.generator import ElectricityDataGenerator
from src.core.data_exporter import DataExporter
from src.services.osm_service import OSMService
from src.services.generation_service import GenerationService
from src.services.export_service import ExportService


# ==============================================================================
# CONFIGURATION DE L'APPLICATION
# ==============================================================================

def setup_logging():
    """Configure le système de logging"""
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG.LOG_LEVEL),
        format=LOGGING_CONFIG.LOG_FORMAT,
        datefmt=LOGGING_CONFIG.DATE_FORMAT
    )

def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    app.config.from_object(APP_CONFIG)
    initialize_config()
    setup_logging()
    return app


# ==============================================================================
# INITIALISATION DE L'APPLICATION
# ==============================================================================

# Création de l'application
app = create_app()

# Initialisation des gestionnaires principaux
osm_handler = OSMHandler()
generator = ElectricityDataGenerator()
data_exporter = DataExporter()

# Initialisation des services métier
osm_service = OSMService(osm_handler)
generation_service = GenerationService(generator)
export_service = ExportService(data_exporter)

# Logger de l'application
logger = logging.getLogger('malaysia_generator')


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def validate_generation_parameters_simple(start_date: str, end_date: str, frequency: str, num_buildings: int):
    """Validation simplifiée des paramètres"""
    errors = []
    
    # Validation dates
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        if start >= end:
            errors.append("Date de fin doit être après date de début")
        if (end - start).days > 365:
            errors.append("Période maximale: 365 jours")
    except Exception as e:
        errors.append(f"Format de dates invalide: {str(e)}")
    
    # Validation fréquence
    valid_frequencies = ['15T', '30T', '1H', '3H', 'D']
    if frequency not in valid_frequencies:
        errors.append(f"Fréquence invalide. Supportées: {valid_frequencies}")
    
    # Validation nombre de bâtiments
    if not (1 <= num_buildings <= 50000):
        errors.append(f"Nombre de bâtiments doit être entre 1 et 50000")
    
    return len(errors) == 0, errors


# ==============================================================================
# ROUTES PRINCIPALES
# ==============================================================================

@app.route('/')
def index():
    """Page d'accueil"""
    try:
        available_zones = osm_service.get_available_zones()
        return render_template('index.html', zones=available_zones)
    except Exception as e:
        logger.error(f"❌ Erreur page d'accueil: {str(e)}")
        return render_template('index.html', zones=[], error="Erreur de chargement")


@app.route('/api/zones', methods=['GET'])
def api_get_zones():
    """API pour récupérer les zones disponibles"""
    try:
        zones = osm_service.get_available_zones()
        return jsonify({
            'success': True,
            'zones': zones,
            'total_count': len(zones)
        })
    except Exception as e:
        logger.error(f"❌ Erreur API zones: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/zone-estimation/<zone_name>', methods=['GET'])
def api_zone_estimation(zone_name: str):
    """API pour obtenir l'estimation d'une zone"""
    try:
        estimation = osm_service.get_zone_estimation(zone_name)
        return jsonify({
            'success': True,
            'estimation': estimation
        })
    except Exception as e:
        logger.error(f"❌ Erreur estimation zone {zone_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/osm-buildings/<zone_name>', methods=['POST'])
def api_load_osm_buildings(zone_name: str):
    """API pour charger les bâtiments OSM d'une zone"""
    try:
        logger.info(f"🔄 Chargement OSM pour zone: {zone_name}")
        
        osm_result = osm_service.load_complete_zone_buildings(zone_name)
        
        if not osm_result['success']:
            return jsonify(osm_result), 400
        
        logger.info(f"✅ {len(osm_result['buildings'])} bâtiments OSM chargés")
        return jsonify(osm_result)
        
    except Exception as e:
        logger.error(f"❌ Erreur chargement OSM {zone_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'buildings': []
        }), 500


@app.route('/api/estimate-generation', methods=['POST'])
def api_estimate_generation():
    """API pour estimer les ressources de génération"""
    try:
        data = request.get_json()
        logger.info(f"📊 Demande d'estimation: {data}")
        
        # Extraction des paramètres
        num_buildings = data.get('num_buildings', 0)
        start_date = data.get('start_date', '2024-01-01')
        end_date = data.get('end_date', '2024-01-31')
        frequency = data.get('frequency', '30T')
        
        logger.info(f"📊 Paramètres estimation: {num_buildings} bâtiments, {start_date} → {end_date}, {frequency}")
        
        # Validation des paramètres
        if not isinstance(num_buildings, int) or num_buildings <= 0:
            return jsonify({
                'success': False,
                'error': 'Nombre de bâtiments invalide'
            }), 400
        
        # Calcul des estimations
        try:
            # Calcul du nombre d'observations
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            days = (end - start).days + 1  # Inclure le dernier jour
            
            # Points de données par jour selon la fréquence
            freq_points_per_day = {
                'D': 1,      # Quotidien
                '3H': 8,     # Toutes les 3 heures
                '1H': 24,    # Toutes les heures
                '30T': 48,   # Toutes les 30 minutes
                '15T': 96    # Toutes les 15 minutes
            }
            
            points_per_day = freq_points_per_day.get(frequency, 48)
            total_observations = num_buildings * days * points_per_day
            
            # Estimation du temps de génération
            # Base: ~50,000 observations par seconde
            observations_per_second = 50000
            estimated_time_seconds = max(1, total_observations / observations_per_second)
            estimated_time_minutes = estimated_time_seconds / 60
            
            # Estimation de la taille des données
            # Base: ~200 bytes par observation (avec métadonnées)
            bytes_per_observation = 200
            estimated_size_bytes = total_observations * bytes_per_observation
            estimated_size_mb = estimated_size_bytes / (1024 * 1024)
            estimated_size_gb = estimated_size_mb / 1024
            
            # Estimation de l'utilisation mémoire
            # Factor 3x pour le traitement en mémoire
            memory_usage_mb = estimated_size_mb * 3
            
            # Détermination du niveau de complexité
            if total_observations < 100000:
                complexity = 'simple'
                recommendation = 'Génération rapide (< 30 secondes)'
                warning = None
            elif total_observations < 1000000:
                complexity = 'modéré'
                recommendation = 'Génération standard (1-5 minutes)'
                warning = None
            elif total_observations < 10000000:
                complexity = 'complexe'
                recommendation = 'Génération longue (5-30 minutes)'
                warning = 'Assurez-vous d\'avoir suffisamment de mémoire RAM'
            elif total_observations < 50000000:
                complexity = 'très_complexe'
                recommendation = 'Génération très longue (30 minutes - 2 heures)'
                warning = 'Génération très longue - considérez réduire la période ou la fréquence'
            else:
                complexity = 'extrême'
                recommendation = 'Génération extrêmement longue (> 2 heures)'
                warning = 'ATTENTION: Génération très longue - fortement recommandé de réduire les paramètres'
            
            # Construction de la réponse
            estimation = {
                'input_parameters': {
                    'num_buildings': num_buildings,
                    'start_date': start_date,
                    'end_date': end_date,
                    'frequency': frequency,
                    'period_days': days
                },
                'calculations': {
                    'points_per_building_per_day': points_per_day,
                    'total_observations': total_observations,
                    'observations_formatted': f"{total_observations:,}"
                },
                'time_estimation': {
                    'estimated_seconds': round(estimated_time_seconds, 1),
                    'estimated_minutes': round(estimated_time_minutes, 1),
                    'estimated_hours': round(estimated_time_minutes / 60, 1) if estimated_time_minutes > 60 else 0,
                    'human_readable': _format_duration(estimated_time_seconds)
                },
                'size_estimation': {
                    'estimated_bytes': estimated_size_bytes,
                    'estimated_mb': round(estimated_size_mb, 1),
                    'estimated_gb': round(estimated_size_gb, 2) if estimated_size_gb > 0.1 else 0,
                    'memory_usage_mb': round(memory_usage_mb, 1),
                    'human_readable': _format_size(estimated_size_bytes)
                },
                'complexity': {
                    'level': complexity,
                    'recommendation': recommendation,
                    'warning': warning
                },
                'feasibility': {
                    'is_feasible': total_observations <= 50000000,
                    'risk_level': _assess_risk_level(total_observations, memory_usage_mb),
                    'suggestions': _get_optimization_suggestions(num_buildings, days, frequency, total_observations)
                }
            }
            
            logger.info(f"✅ Estimation calculée: {total_observations:,} observations, {estimated_time_minutes:.1f} min")
            
            return jsonify({
                'success': True,
                'estimation': estimation
            })
            
        except Exception as calc_error:
            logger.error(f"❌ Erreur calcul estimation: {str(calc_error)}")
            return jsonify({
                'success': False,
                'error': f'Erreur de calcul: {str(calc_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Erreur estimation génération: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


def _format_duration(seconds: float) -> str:
    """Formate une durée en secondes en texte lisible"""
    if seconds < 60:
        return f"{int(seconds)} secondes"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        if minutes > 0:
            return f"{hours}h{minutes:02d}min"
        else:
            return f"{hours} heure{'s' if hours > 1 else ''}"


def _format_size(bytes_size: int) -> str:
    """Formate une taille en bytes en texte lisible"""
    if bytes_size < 1024:
        return f"{bytes_size} bytes"
    elif bytes_size < 1024 * 1024:
        kb = bytes_size / 1024
        return f"{kb:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        mb = bytes_size / (1024 * 1024)
        return f"{mb:.1f} MB"
    else:
        gb = bytes_size / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"


def _assess_risk_level(total_observations: int, memory_mb: float) -> str:
    """Évalue le niveau de risque de la génération"""
    if total_observations > 30000000 or memory_mb > 4000:
        return 'élevé'
    elif total_observations > 10000000 or memory_mb > 2000:
        return 'moyen'
    elif total_observations > 1000000 or memory_mb > 500:
        return 'faible'
    else:
        return 'très_faible'


def _get_optimization_suggestions(num_buildings: int, days: int, frequency: str, total_obs: int) -> List[str]:
    """Génère des suggestions d'optimisation"""
    suggestions = []
    
    if total_obs > 20000000:
        if frequency in ['15T', '30T']:
            suggestions.append("Utilisez une fréquence plus faible (1H ou D) pour réduire le volume")
        
        if days > 31:
            suggestions.append("Réduisez la période à 1 mois maximum")
        
        if num_buildings > 100000:
            suggestions.append("Divisez la génération par zones plus petites")
    
    elif total_obs > 5000000:
        if frequency == '15T':
            suggestions.append("Considérez utiliser 30T ou 1H pour de meilleures performances")
        
        if days > 90:
            suggestions.append("Période longue détectée - considérez diviser en plusieurs générations")
    
    if not suggestions:
        suggestions.append("Paramètres optimaux pour la génération")
    
    return suggestions

def convert_numpy_types(obj):
    """Convertit les types numpy/pandas en types Python natifs pour JSON"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


@app.route('/api/generate', methods=['POST'])
def api_generate_data():
    """
    API principale pour générer les données électriques
    
    Returns:
        JSON: Données générées et statistiques
    """
    try:
        logger.info("🚀 Début API generate")
        
        # Récupération des paramètres
        data = request.get_json()
        if not data:
            logger.error("❌ Aucune donnée JSON reçue")
            return jsonify({
                'success': False,
                'error': 'Données JSON requises'
            }), 400
        
        # Extraction des paramètres
        zone_name = data.get('zone_name')
        buildings_osm = data.get('buildings_osm', [])
        start_date = data.get('start_date', '2024-01-01')
        end_date = data.get('end_date', '2024-01-31')
        frequency = data.get('frequency', data.get('freq', '30T'))
        
        logger.info(f"🔄 Génération demandée - Zone: {zone_name}, Bâtiments: {len(buildings_osm)}")
        logger.info(f"📅 Paramètres: {start_date} → {end_date}, fréquence: {frequency}")
        
        # Validation des paramètres de base
        if not zone_name:
            logger.error("❌ Nom de zone manquant")
            return jsonify({
                'success': False,
                'error': 'Nom de zone requis'
            }), 400
        
        if not buildings_osm or not isinstance(buildings_osm, list):
            logger.error("❌ Bâtiments OSM invalides")
            return jsonify({
                'success': False,
                'error': 'Liste de bâtiments OSM requise'
            }), 400
        
        # Validation des paramètres de génération
        params_valid, param_errors = validate_generation_parameters_simple(
            start_date, end_date, frequency, len(buildings_osm)
        )
        
        if not params_valid:
            logger.warning(f"⚠️ Paramètres invalides: {param_errors}")
            return jsonify({
                'success': False,
                'error': 'Paramètres invalides',
                'details': param_errors
            }), 400
        
        logger.info("✅ Validation des paramètres réussie")
        
        # Génération via le service
        logger.info("🚀 Début de la génération...")
        generation_result = generation_service.generate_complete_dataset(
            zone_name=zone_name,
            buildings_osm=buildings_osm,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency
        )
        
        if generation_result.get('success'):
            total_obs = generation_result.get('statistics', {}).get('total_observations', 0)
            logger.info(f"✅ Génération terminée: {total_obs} observations")
            
            # CORRECTION: Convertir les types numpy/pandas avant la sérialisation JSON
            cleaned_result = convert_numpy_types(generation_result)
            
            return jsonify(cleaned_result)
        else:
            error_msg = generation_result.get('error', 'Erreur inconnue')
            logger.error(f"❌ Échec génération: {error_msg}")
            
            # Nettoyer aussi les erreurs
            cleaned_result = convert_numpy_types(generation_result)
            return jsonify(cleaned_result), 500
        
    except Exception as e:
        logger.error(f"❌ Erreur génération: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f"Erreur serveur: {str(e)}"
        }), 500


@app.route('/api/export', methods=['POST'])
def api_export_data():
    """API pour exporter les données générées"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données à exporter requises'
            }), 400
        
        buildings_data = data.get('buildings', [])
        timeseries_data = data.get('timeseries', [])
        export_formats = data.get('formats', ['csv', 'parquet'])
        filename_prefix = data.get('filename_prefix')
        
        logger.info(f"🔄 Export demandé - Formats: {export_formats}")
        
        # Export via le service
        export_result = export_service.export_complete_dataset(
            buildings_data=buildings_data,
            timeseries_data=timeseries_data,
            formats=export_formats,
            filename_prefix=filename_prefix
        )
        
        logger.info(f"✅ Export terminé: {export_result.get('total_size_mb', 0):.2f} MB")
        return jsonify(export_result)
        
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
        
        file_path = os.path.join(APP_CONFIG.EXPORTS_DIR, filename)
        
        if not os.path.exists(file_path):
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
# ROUTES DE STATUS ET MONITORING
# ==============================================================================

@app.route('/api/status')
def api_status():
    """API pour le statut de l'application"""
    try:
        status = {
            'healthy': True,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'osm': osm_service.test_connection(),
                'generation': True,
                'export': True
            }
        }
        
        return jsonify(status), 200 if status['healthy'] else 503
        
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
            'osm_statistics': osm_handler.get_statistics(),
            'generation_statistics': generation_service.get_statistics(),
            'application_statistics': {
                'total_api_calls': getattr(app, '_api_calls_count', 0),
                'available_zones': len(osm_service.get_available_zones())
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
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
    if APP_CONFIG.DEBUG:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == '__main__':
    logger.info("🚀 L'application est prête !")
    logger.info(f"   Ouvrez votre navigateur sur: http://127.0.0.1:{APP_CONFIG.PORT}")
    logger.info("============================================================")
    
    app.run(
        host=APP_CONFIG.HOST,
        port=APP_CONFIG.PORT,
        debug=APP_CONFIG.DEBUG
    )