#!/usr/bin/env python3
"""
Point d'entrée principal pour l'application Malaysia Electricity Generator
=========================================================================

Script de démarrage simple et propre pour lancer l'application refactorisée.
"""

import os
import sys
import logging
from pathlib import Path

# Ajout du répertoire racine au path Python
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import de l'application
from app import app
from config import APP_CONFIG, initialize_config


def setup_environment():
    """
    Configure l'environnement d'exécution
    """
    # Initialisation de la configuration
    initialize_config()
    
    # Configuration du logging pour le démarrage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Démarrage Malaysia Electricity Generator")
    logger.info(f"📁 Répertoire projet: {PROJECT_ROOT}")
    
    return logger


def check_dependencies():
    """
    Vérifie que les dépendances requises sont installées
    
    Returns:
        bool: True si toutes les dépendances sont présentes
    """
    required_packages = [
        'flask',
        'pandas',
        'numpy',
        'requests',
        'pyarrow'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Dépendances manquantes:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Installez avec: pip install -r requirements.txt")
        return False
    
    return True


def check_project_structure():
    """
    Vérifie que la structure de projet est cohérente
    
    Returns:
        bool: True si la structure est correcte
    """
    required_dirs = [
        'src',
        'src/core',
        'src/models',
        'src/services',
        'templates',
        'static'
    ]
    
    required_files = [
        'config.py',
        'app.py',
        'src/models/building.py',
        'src/models/timeseries.py',
        'src/core/osm_handler.py',
        'src/core/generator.py',
        'src/core/data_exporter.py'
    ]
    
    missing_items = []
    
    # Vérification des dossiers
    for directory in required_dirs:
        dir_path = PROJECT_ROOT / directory
        if not dir_path.exists():
            missing_items.append(f"Dossier: {directory}")
    
    # Vérification des fichiers
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            missing_items.append(f"Fichier: {file_path}")
    
    if missing_items:
        print("❌ Structure de projet incomplète:")
        for item in missing_items:
            print(f"   - {item}")
        return False
    
    return True


def print_startup_info():
    """
    Affiche les informations de démarrage
    """
    print("\n" + "="*60)
    print("🇲🇾  MALAYSIA ELECTRICITY DATA GENERATOR")
    print("="*60)
    print(f"🌐 URL: http://{APP_CONFIG.HOST}:{APP_CONFIG.PORT}")
    print(f"📁 Exports: {APP_CONFIG.EXPORTS_DIR}")
    print(f"🔧 Mode: {'DEBUG' if APP_CONFIG.DEBUG else 'PRODUCTION'}")
    print("="*60)
    print("\n📋 FONCTIONNALITÉS DISPONIBLES:")
    print("   ✅ Requêtes OSM pour localités entières Malaysia")
    print("   ✅ Génération données électriques réalistes")
    print("   ✅ Export multi-format (CSV, Parquet, Excel, JSON)")
    print("   ✅ Validation automatique et contrôle qualité")
    print("   ✅ Interface web épurée et fonctionnelle")
    print("\n🚀 L'application est prête !")
    print(f"   Ouvrez votre navigateur sur: http://{APP_CONFIG.HOST}:{APP_CONFIG.PORT}")
    print("="*60)


def create_init_files():
    """
    Crée les fichiers __init__.py manquants
    """
    init_dirs = [
        'src',
        'src/core',
        'src/models',
        'src/services',
        'src/utils'
    ]
    
    for directory in init_dirs:
        dir_path = PROJECT_ROOT / directory
        init_file = dir_path / '__init__.py'
        
        if dir_path.exists() and not init_file.exists():
            try:
                init_file.touch()
                print(f"✅ Créé: {init_file}")
            except Exception as e:
                print(f"⚠️ Impossible de créer {init_file}: {e}")


def run_development_server():
    """
    Lance le serveur de développement Flask
    """
    try:
        app.run(
            host=APP_CONFIG.HOST,
            port=APP_CONFIG.PORT,
            debug=APP_CONFIG.DEBUG,
            threaded=True,
            use_reloader=False  # Éviter les doubles démarrages
        )
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt de l'application")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur démarrage serveur: {e}")
        sys.exit(1)


def main():
    """
    Fonction principale de démarrage
    """
    logger = setup_environment()
    
    # Vérifications préalables
    print("🔍 Vérification de l'environnement...")
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_project_structure():
        print("\n💡 Certains fichiers peuvent être manquants.")
        print("   Référez-vous au guide de migration pour créer les fichiers requis.")
        response = input("\n❓ Continuer quand même ? (o/N): ")
        if response.lower() not in ['o', 'oui', 'y', 'yes']:
            sys.exit(1)
    
    # Création des fichiers __init__.py si nécessaire
    create_init_files()
    
    # Test d'import de l'application
    try:
        # Test des imports critiques
        from src.core.osm_handler import OSMHandler
        from src.core.generator import ElectricityDataGenerator
        from src.core.data_exporter import DataExporter
        print("✅ Modules principaux importés avec succès")
        
    except ImportError as e:
        print(f"❌ Erreur import modules: {e}")
        print("\n💡 Vérifiez que tous les fichiers sont créés correctement.")
        sys.exit(1)
    
    # Affichage des informations de démarrage
    print_startup_info()
    
    # Test de connectivité OSM optionnel
    print("\n🔗 Test de connectivité OSM...")
    try:
        from src.core.osm_handler import test_osm_connection
        if test_osm_connection():
            print("✅ Connexion OSM opérationnelle")
        else:
            print("⚠️ Connexion OSM échouée - fonctionnement dégradé possible")
    except Exception as e:
        print(f"⚠️ Impossible de tester OSM: {e}")
    
    # Démarrage du serveur
    logger.info("🎯 Lancement du serveur Flask...")
    run_development_server()


if __name__ == '__main__':
    main()
