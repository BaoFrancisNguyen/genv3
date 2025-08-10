"""
STRUCTURE DU PROJET REFACTORISÉ - GÉNÉRATEUR ÉLECTRIQUE MALAISIE
===============================================================

Nouvelle organisation avec séparation des responsabilités et code propre.

projet_refactorise/
├── app.py                          # Application Flask principale (simplifié)
├── run.py                          # Point d'entrée
├── config.py                       # Configuration centralisée
├── requirements.txt                # Dépendances
│
├── src/                            # Code source principal
│   ├── __init__.py
│   ├── core/                       # Fonctionnalités principales
│   │   ├── __init__.py
│   │   ├── generator.py           # Génération des données électriques
│   │   ├── osm_handler.py         # Gestion OpenStreetMap
│   │   └── data_exporter.py       # Export CSV/Parquet
│   │
│   ├── models/                     # Structures de données
│   │   ├── __init__.py
│   │   ├── building.py            # Modèle Building
│   │   ├── location.py            # Modèle Location
│   │   └── timeseries.py          # Modèle TimeSeries
│   │
│   ├── services/                   # Services métier
│   │   ├── __init__.py
│   │   ├── osm_service.py         # Service OSM
│   │   ├── generation_service.py  # Service de génération
│   │   └── export_service.py      # Service d'export
│   │
│   └── utils/                      # Utilitaires
│       ├── __init__.py
│       ├── validators.py          # Validation des données
│       ├── helpers.py             # Fonctions d'aide
│       └── constants.py           # Constantes du projet
│
├── static/                         # Assets frontend (simplifié)
│   ├── css/
│   │   └── main.css               # Styles essentiels
│   └── js/
│       ├── main.js                # JavaScript principal
│       └── osm_map.js             # Carte OSM
│
├── templates/                      # Templates HTML
│   ├── base.html                  # Template de base
│   └── index.html                 # Page principale
│
├── data/                          # Données de référence
│   ├── malaysia_zones.json       # Zones de Malaisie
│   └── building_types.json       # Types de bâtiments
│
├── exports/                       # Dossier d'export (généré automatiquement)
│
├── logs/                          # Logs de l'application
│
└── tests/                         # Tests unitaires
    ├── __init__.py
    ├── test_generator.py
    ├── test_osm_handler.py
    └── test_services.py

PRINCIPES DE LA REFACTORISATION:
================================

1. SÉPARATION DES RESPONSABILITÉS
   - Core: Logic métier principale
   - Models: Structures de données
   - Services: Couche service
   - Utils: Utilitaires partagés

2. CODE PROPRE
   - Commentaires explicites en français
   - Docstrings pour toutes les fonctions
   - Nommage explicite des variables
   - Pas de code dupliqué

3. ARCHITECTURE MODULAIRE
   - Chaque module a une responsabilité unique
   - Imports clairement définis
   - Configuration centralisée

4. SIMPLICITÉ
   - Suppression des icônes et animations
   - Interface utilisateur épurée
   - Focus sur les fonctionnalités essentielles
"""