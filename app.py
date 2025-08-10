"""
Application Flask principale refactorisée - Générateur électrique Malaysia
========================================================================

Application épurée avec architecture modulaire et code propre.
Focus sur les fonctionnalités essentielles sans fioritures.
"""

from flask import Flask, request, jsonify, render_template, send_file
import logging
from datetime import datetime
import os
import traceback
from typing import Dict, List

# Imports des modules refactorisés
from config import APP_CONFIG, LOGGING_CONFIG, initialize_config
from src.core.osm_handler import OSMHandler
from src.core.generator import ElectricityDataGenerator, validate_generation_parameters
from src.core.data_exporter import DataExporter
from src.services.osm_service import OSMService
from src.services.generation_service import GenerationService
from src.services.export_service import ExportService


# ==============================================================================
# CONFIGURATION DE L'APPLICATION
# ==============================================================================

def create_app():
    """
    Factory pour créer l'application Flask
    
    Returns:
        Flask: Instance de l'application configurée
    """
    app = Flask(__name__)
    app.config.from_object(APP_CONFIG)
    
    # Initialisation des composants
    initialize_config()
    setup_logging()
    
    return app


def setup_logging():
    """Configure le système de logging de l'application"""
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG.LOG_LEVEL),
        format=LOGGING_CONFIG.LOG_FORMAT,
        datefmt=LOGGING_CONFIG.DATE_FORMAT
    )
    
    # Logger spécifique pour l'application
    app_logger = logging.getLogger('malaysia_generator')
    app_logger.info("✅ Application initialisée")


# ==============================================================================
# INITIALISATION DES SERVICES
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
# ROUTES PRINCIPALES
# ==============================================================================

@app.route('/')
def index():
    """Page d'accueil de l'application"""
    try:
        # Récupération des zones disponibles pour le formulaire
        available_zones = osm_service.get_available_zones()
        
        return render_template('index.html', zones=available_zones)
        
    except Exception as e:
        logger.error(f"❌ Erreur page d'accueil: {str(e)}")
        return render_template('index.html', zones=[], error="Erreur de chargement")


@app.route('/api/zones', methods=['GET'])
def api_get_zones():
    """
    API pour récupérer la liste des zones disponibles
    
    Returns:
        JSON: Liste des zones avec métadonnées
    """
    try:
        zones = osm_service.get_available_zones()
        
        return jsonify({
            'success': True,
            'zones': zones,
            'total_count': len(zones)
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur API zones: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/zone-estimation/<zone_name>', methods=['GET'])
def api_zone_estimation(zone_name: str):
    """
    API pour obtenir l'estimation de complexité d'une zone
    
    Args:
        zone_name: Nom de la zone à estimer
        
    Returns:
        JSON: Estimation de temps, taille et complexité
    """
    try:
        estimation = osm_service.get_zone_estimation(zone_name)
        
        return jsonify({
            'success': True,
            'estimation': estimation
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur estimation zone {zone_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/osm-buildings/<zone_name>', methods=['POST'])
def api_load_osm_buildings(zone_name: str):
    """
    API pour charger les bâtiments OSM d'une zone complète
    
    Args:
        zone_name: Nom de la zone
        
    Returns:
        JSON: Bâtiments OSM chargés avec métadonnées
    """
    try:
        logger.info(f"🔄 Chargement OSM pour zone: {zone_name}")
        
        # Chargement des bâtiments OSM
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


@app.route('/api/generate', methods=['POST'])
def api_generate_data():
    """
    API principale pour générer les données électriques
    
    Returns:
        JSON: Données générées et statistiques
    """
    try:
        # Récupération des paramètres de la requête
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données JSON requises'
            }), 400
        
        # Extraction des paramètres
        zone_name = data.get('zone_name')
        buildings_osm = data.get('buildings_osm', [])
        start_date = data.get('start_date', '2024-01-01')
        end_date = data.get('end_date', '2024-01-31')
        frequency = data.get('freq', '30T')
        
        logger.info(f"🔄 Génération demandée - Zone: {zone_name}, Bâtiments: {len(buildings_osm)}")
        
        # Validation des paramètres
        if not zone_name:
            return jsonify({
                'success': False,
                'error': 'Nom de zone requis'
            }), 400
        
        if not buildings_osm:
            return jsonify({
                'success': False,
                'error': 'Aucun bâtiment OSM fourni'
            }), 400
        
        # Validation des paramètres de génération
        params_valid, param_errors = validate_generation_parameters(
            start_date, end_date, frequency, len(buildings_osm)
        )
        
        if not params_valid:
            return jsonify({
                'success': False,
                'error': 'Paramètres invalides',
                'details': param_errors
            }), 400
        
        # Génération via le service
        generation_result = generation_service.generate_complete_dataset(
            zone_name=zone_name,
            buildings_osm=buildings_osm,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency
        )
        
        logger.info(f"✅ Génération terminée: {generation_result['statistics']['total_observations']} observations")
        
        return jsonify(generation_result)
        
    except Exception as e:
        logger.error(f"❌ Erreur génération: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/export', methods=['POST'])
def api_export_data():
    """
    API pour exporter les données générées
    
    Returns:
        JSON: Résultats d'export avec chemins des fichiers
    """
    try:
        # Récupération des données à exporter
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
        
        logger.info(f"✅ Export terminé: {export_result['total_size_mb']:.2f} MB")
        
        return jsonify(export_result)
        
    except Exception as e:
        logger.error(f"❌ Erreur export: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/<filename>')
def api_download_file(filename: str):
    """
    API pour télécharger un fichier exporté
    
    Args:
        filename: Nom du fichier à télécharger
        
    Returns:
        File: Fichier à télécharger
    """
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
        logger.error(f"❌ Erreur téléchargement {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==============================================================================
# ROUTES D'ÉTAT ET DIAGNOSTICS
# ==============================================================================

@app.route('/api/status')
def api_status():
    """
    API pour vérifier l'état de l'application
    
    Returns:
        JSON: État des services et statistiques
    """
    try:
        # Vérification des services
        osm_status = osm_service.get_service_status()
        generation_status = generation_service.get_service_status()
        export_status = export_service.get_service_status()
        
        return jsonify({
            'success': True,
            'application': {
                'name': 'Malaysia Electricity Data Generator',
                'version': '2.0.0',
                'status': 'active',
                'uptime_info': datetime.now().isoformat()
            },
            'services': {
                'osm_service': osm_status,
                'generation_service': generation_status,
                'export_service': export_status
            },
            'configuration': {
                'exports_directory': APP_CONFIG.EXPORTS_DIR,
                'supported_formats': ['csv', 'parquet', 'xlsx', 'json'],
                'max_buildings': 10000,
                'supported_frequencies': ['15T', '30T', '1H', '3H', 'D']
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur statut: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health')
def api_health():
    """
    API de health check pour monitoring
    
    Returns:
        JSON: État de santé minimal
    """
    try:
        # Tests de base
        osm_healthy = osm_service.test_connection()
        exports_writable = os.access(APP_CONFIG.EXPORTS_DIR, os.W_OK)
        
        healthy = osm_healthy and exports_writable
        
        return jsonify({
            'healthy': healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'osm_connection': osm_healthy,
                'exports_writable': exports_writable
            }
        }), 200 if healthy else 503
        
    except Exception as e:
        logger.error(f"❌ Erreur health check: {str(e)}")
        return jsonify({
            'healthy': False,
            'error': str(e)
        }), 503


@app.route('/api/statistics')
def api_statistics():
    """
    API pour les statistiques globales de l'application
    
    Returns:
        JSON: Statistiques d'usage et performance
    """
    try:
        stats = {
            'osm_statistics': osm_handler.get_statistics(),
            'generation_statistics': generation_service.get_statistics(),
            'export_statistics': data_exporter.get_export_statistics(),
            'application_statistics': {
                'total_api_calls': getattr(app, '_api_calls_count', 0),
                'available_zones': len(osm_service.get_available_zones()),
                'exports_directory_size_mb': _get_directory_size_mb(APP_CONFIG.EXPORTS_DIR)
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur statistiques: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==============================================================================
# ROUTES UTILITAIRES
# ==============================================================================

@app.route('/api/validate-parameters', methods=['POST'])
def api_validate_parameters():
    """
    API pour valider les paramètres de génération
    
    Returns:
        JSON: Résultats de validation
    """
    try:
        data = request.get_json()
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        frequency = data.get('frequency')
        num_buildings = data.get('num_buildings', 0)
        
        is_valid, errors = validate_generation_parameters(
            start_date, end_date, frequency, num_buildings
        )
        
        return jsonify({
            'valid': is_valid,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur validation paramètres: {str(e)}")
        return jsonify({
            'valid': False,
            'errors': [str(e)]
        }), 500


@app.route('/api/estimate-generation', methods=['POST'])
def api_estimate_generation():
    """
    API pour estimer le temps et les ressources de génération
    
    Returns:
        JSON: Estimations de temps et taille
    """
    try:
        data = request.get_json()
        
        num_buildings = data.get('num_buildings', 0)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        frequency = data.get('frequency', '30T')
        
        estimation = generation_service.estimate_generation_resources(
            num_buildings, start_date, end_date, frequency
        )
        
        return jsonify({
            'success': True,
            'estimation': estimation
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur estimation génération: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
    """Middleware exécuté avant chaque requête"""
    # Compteur d'appels API (simple)
    if not hasattr(app, '_api_calls_count'):
        app._api_calls_count = 0
    
    if request.path.startswith('/api/'):
        app._api_calls_count += 1


@app.after_request
def after_request(response):
    """Middleware exécuté après chaque requête"""
    # Headers de sécurité basiques
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    
    # CORS pour développement local (à retirer en production)
    if APP_CONFIG.DEBUG:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def _get_directory_size_mb(directory_path: str) -> float:
    """
    Calcule la taille d'un dossier en MB
    
    Args:
        directory_path: Chemin du dossier
        
    Returns:
        float: Taille en MB
    """
    try:
        if not os.path.exists(directory_path):
            return 0.0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        
        return total_size / (1024 * 1024)
        
    except Exception:
        return 0.0


def cleanup_old_exports(max_age_days: int = 7):
    """
    Nettoie les anciens fichiers d'export
    
    Args:
        max_age_days: Age maximum en jours
    """
    try:
        import time
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
        
        exports_dir = APP_CONFIG.EXPORTS_DIR
        if not os.path.exists(exports_dir):
            return
        
        removed_count = 0
        for filename in os.listdir(exports_dir):
            filepath = os.path.join(exports_dir, filename)
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                if file_time < cutoff_time:
                    os.remove(filepath)
                    removed_count += 1
        
        if removed_count > 0:
            logger.info(f"🧹 {removed_count} anciens fichiers supprimés")
            
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage: {str(e)}")


# ==============================================================================
# POINT D'ENTRÉE DE L'APPLICATION
# ==============================================================================

if __name__ == '__main__':
    logger.info("🚀 Démarrage application Malaysia Electricity Generator")
    logger.info(f"📁 Dossier exports: {APP_CONFIG.EXPORTS_DIR}")
    logger.info(f"🔧 Mode debug: {APP_CONFIG.DEBUG}")
    
    # Nettoyage initial des anciens exports
    cleanup_old_exports()
    
    # Démarrage du serveur Flask
    app.run(
        host=APP_CONFIG.HOST,
        port=APP_CONFIG.PORT,
        debug=APP_CONFIG.DEBUG,
        threaded=True
    )
