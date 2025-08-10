#!/usr/bin/env python3
"""
Point d'entrée principal pour Malaysia Electricity Generator v2.0
=================================================================

COMPATIBLE avec le nouveau app.py corrigé qui utilise CompleteBuildingLoader
au lieu de l'ancien OSMHandler.
"""

import os
import sys
import logging
from pathlib import Path

# Ajout du répertoire racine au path Python
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def setup_environment():
    """Configure l'environnement d'exécution"""
    # Configuration du logging pour le démarrage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Démarrage Malaysia Electricity Generator v2.0")
    logger.info(f"📁 Répertoire projet: {PROJECT_ROOT}")
    
    return logger

def check_dependencies():
    """Vérifie que les dépendances requises sont installées"""
    required_packages = [
        'flask',
        'pandas', 
        'numpy',
        'requests',
        'openpyxl',  # pour Excel
        'pyarrow'    # pour Parquet
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
        print("\n💡 Installez avec: pip install flask pandas numpy requests openpyxl pyarrow")
        return False
    
    return True

def check_project_structure():
    """Vérifie la structure de projet basique"""
    required_dirs = [
        'templates',
        'static',
        'exports',
        'logs'
    ]
    
    missing_dirs = []
    
    for directory in required_dirs:
        dir_path = PROJECT_ROOT / directory
        if not dir_path.exists():
            # Créer le dossier manquant
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"✅ Créé dossier: {directory}")
            except Exception as e:
                missing_dirs.append(directory)
                print(f"❌ Impossible de créer {directory}: {e}")
    
    if missing_dirs:
        print(f"⚠️ Dossiers manquants: {missing_dirs}")
        return False
    
    return True

def check_app_py():
    """Vérifie que app.py contient les bonnes classes"""
    app_file = PROJECT_ROOT / 'app.py'
    
    if not app_file.exists():
        print("❌ Fichier app.py manquant")
        return False
    
    try:
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier que le nouveau code est présent
        required_elements = [
            'CompleteBuildingLoader',
            'ElectricityDataGenerator', 
            'DataExporter',
            'def api_load_osm_buildings_corrected'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print("❌ app.py ne contient pas les éléments requis:")
            for element in missing_elements:
                print(f"   - {element}")
            print("\n💡 Utilisez le app.py corrigé v2.0")
            return False
        
        print("✅ app.py contient tous les éléments requis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lecture app.py: {e}")
        return False

def create_index_template():
    """Crée un template index.html basique si manquant"""
    templates_dir = PROJECT_ROOT / 'templates'
    index_file = templates_dir / 'index.html'
    
    if index_file.exists():
        return True
    
    try:
        templates_dir.mkdir(exist_ok=True)
        
        # Template HTML basique
        basic_template = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Malaysia Electricity Generator v2.0</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { background: white; border-radius: 20px; margin: 2rem auto; padding: 2rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">🇲🇾 Malaysia Electricity Generator v2.0</h1>
        <div class="alert alert-info">
            <h5>Application prête !</h5>
            <p>L'application fonctionne correctement. Pour utiliser l'interface complète, utilisez le template HTML fourni dans les artefacts.</p>
            <p><strong>API disponible :</strong></p>
            <ul>
                <li><code>GET /api/zones</code> - Liste des zones Malaysia</li>
                <li><code>POST /api/osm-buildings/&lt;zone_name&gt;</code> - Chargement OSM corrigé</li>
                <li><code>POST /api/generate</code> - Génération de données électriques</li>
                <li><code>GET /api/status</code> - Statut de l'application</li>
            </ul>
        </div>
        
        <div class="text-center">
            <button class="btn btn-primary" onclick="testAPI()">Tester l'API</button>
            <div id="result" class="mt-3"></div>
        </div>
    </div>
    
    <script>
        async function testAPI() {
            try {
                const response = await fetch('/api/zones');
                const data = await response.json();
                document.getElementById('result').innerHTML = 
                    `<div class="alert alert-success">✅ API fonctionne ! ${data.total_zones} zones disponibles</div>`;
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    `<div class="alert alert-danger">❌ Erreur API: ${error}</div>`;
            }
        }
    </script>
</body>
</html>'''
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(basic_template)
        
        print("✅ Template index.html basique créé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur création template: {e}")
        return False

def main():
    """Fonction principale de démarrage"""
    logger = setup_environment()
    
    print("🔍 Vérification de l'environnement...")
    
    # Vérification des dépendances
    if not check_dependencies():
        print("\n💡 Installez les dépendances manquantes et relancez.")
        sys.exit(1)
    
    # Vérification de la structure
    if not check_project_structure():
        print("\n⚠️ Problèmes de structure détectés mais dossiers créés.")
    
    # Vérification d'app.py
    if not check_app_py():
        print("\n💡 Remplacez app.py par la version corrigée v2.0.")
        sys.exit(1)
    
    # Création du template basique
    create_index_template()
    
    # Import et lancement de l'application
    try:
        print("\n🚀 Démarrage de l'application...")
        
        # Import de l'application corrigée
        from app import app, logger as app_logger
        
        # Vérification que les nouvelles classes sont bien présentes
        from app import complete_loader, generator, exporter
        
        print("✅ Toutes les classes sont correctement importées")
        print(f"   - CompleteBuildingLoader: {type(complete_loader).__name__}")
        print(f"   - ElectricityDataGenerator: {type(generator).__name__}")
        print(f"   - DataExporter: {type(exporter).__name__}")
        
        # Lancement du serveur
        print("\n" + "="*60)
        print("🇲🇾 MALAYSIA ELECTRICITY GENERATOR v2.0 - CORRIGÉ")
        print("="*60)
        print("✅ NOUVELLES FONCTIONNALITÉS:")
        print("   - Récupération COMPLÈTE des bâtiments OSM")
        print("   - Méthodes OSM multiples (administrative, bbox, hybrid)")
        print("   - Interface professionnelle avec sélecteur par catégories")
        print("   - Gestion d'erreurs robuste avec fallback automatique")
        print("="*60)
        print(f"🌐 URL: http://127.0.0.1:5000")
        print(f"📁 Exports: {PROJECT_ROOT}/exports")
        print("="*60)
        print("🚀 L'application est prête !")
        print("   Ctrl+C pour arrêter")
        print("="*60)
        
        # Démarrage de l'application
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            threaded=True
        )
        
    except ImportError as e:
        print(f"\n❌ Erreur import: {e}")
        print("💡 Vérifiez que app.py contient le code corrigé v2.0")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt de l'application")
        
    except Exception as e:
        print(f"\n❌ Erreur démarrage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()