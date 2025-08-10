"""
Service d'Export - Couche métier pour l'export de données
========================================================

Ce service gère l'export des données générées vers différents formats
avec validation, optimisation et gestion des erreurs de haut niveau.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import os

from src.core.data_exporter import DataExporter
from config import EXPORT_CONFIG, APP_CONFIG


# Configuration du logger
logger = logging.getLogger(__name__)


class ExportService:
    """
    Service métier pour l'export de données
    
    Orchestre l'export des données en gérant la validation,
    la conversion et l'optimisation selon les besoins métier.
    """
    
    def __init__(self, data_exporter: DataExporter):
        """
        Initialise le service d'export
        
        Args:
            data_exporter: Instance de l'exporteur de données
        """
        self.data_exporter = data_exporter
        self.service_statistics = {
            'total_exports': 0,
            'successful_exports': 0,
            'total_files_created': 0,
            'total_size_exported_mb': 0.0,
            'service_start_time': datetime.now()
        }
        
        logger.info("✅ Service d'export initialisé")
    
    def export_complete_dataset(
        self,
        buildings_data: List[Dict],
        timeseries_data: List[Dict],
        formats: List[str] = None,
        filename_prefix: str = None,
        export_options: Dict = None
    ) -> Dict:
        """
        Exporte un dataset complet avec optimisations métier
        
        Args:
            buildings_data: Données des bâtiments
            timeseries_data: Données des séries temporelles
            formats: Liste des formats à exporter
            filename_prefix: Préfixe des fichiers
            export_options: Options d'export personnalisées
            
        Returns:
            Dict: Résultats d'export avec métadonnées
        """
        try:
            logger.info(f"🔄 Export dataset complet - {len(buildings_data)} bâtiments, {len(timeseries_data)} observations")
            
            # Mise à jour des statistiques
            self.service_statistics['total_exports'] += 1
            
            # Phase 1: Validation et préparation des données
            preparation_result = self._prepare_data_for_export(
                buildings_data, timeseries_data, export_options
            )
            
            if not preparation_result['success']:
                return preparation_result
            
            buildings_df = preparation_result['buildings_df']
            timeseries_df = preparation_result['timeseries_df']
            
            # Phase 2: Optimisation selon les formats demandés
            if formats is None:
                formats = ['csv', 'parquet']  # Formats par défaut
            
            optimized_formats = self._optimize_export_formats(formats, len(timeseries_data))
            
            # Phase 3: Génération du préfixe de fichier intelligent
            if filename_prefix is None:
                filename_prefix = self._generate_intelligent_filename(
                    buildings_data, timeseries_data
                )
            
            # Phase 4: Export via l'exporteur de base
            export_result = self.data_exporter.export_complete_dataset(
                buildings_df=buildings_df,
                timeseries_df=timeseries_df,
                formats=optimized_formats,
                filename_prefix=filename_prefix
            )
            
            # Phase 5: Post-traitement et enrichissement
            if export_result['success']:
                self.service_statistics['successful_exports'] += 1
                self.service_statistics['total_size_exported_mb'] += export_result['total_size_mb']
                
                # Création du manifest enrichi
                manifest_path = self.data_exporter.create_export_manifest(export_result)
                
                # Enrichissement avec métadonnées métier
                enriched_result = self._enrich_export_result(
                    export_result, preparation_result, manifest_path
                )
                
                logger.info(f"✅ Export réussi: {export_result['total_size_mb']:.2f} MB")
                return enriched_result
            else:
                return export_result
                
        except Exception as e:
            logger.error(f"❌ Erreur service export: {str(e)}")
            return {
                'success': False,
                'error': f"Erreur service d'export: {str(e)}"
            }
    
    def _prepare_data_for_export(
        self,
        buildings_data: List[Dict],
        timeseries_data: List[Dict],
        export_options: Dict = None
    ) -> Dict:
        """
        Prépare et valide les données pour l'export
        
        Args:
            buildings_data: Données des bâtiments
            timeseries_data: Données des séries temporelles
            export_options: Options d'export
            
        Returns:
            Dict: Données préparées et validées
        """
        try:
            if export_options is None:
                export_options = {}
            
            # Validation de base
            if not buildings_data:
                return {
                    'success': False,
                    'error': 'Aucune donnée de bâtiments à exporter'
                }
            
            if not timeseries_data:
                return {
                    'success': False,
                    'error': 'Aucune donnée de séries temporelles à exporter'
                }
            
            # Conversion en DataFrames avec optimisations
            buildings_df = self._convert_buildings_to_dataframe(buildings_data, export_options)
            timeseries_df = self._convert_timeseries_to_dataframe(timeseries_data, export_options)
            
            # Validation de cohérence
            coherence_check = self._check_data_coherence(buildings_df, timeseries_df)
            
            if not coherence_check['coherent']:
                logger.warning(f"⚠️ Problèmes de cohérence détectés: {coherence_check['issues']}")
            
            # Application des filtres et optimisations
            if export_options.get('apply_filters', True):
                buildings_df = self._apply_data_filters(buildings_df, 'buildings')
                timeseries_df = self._apply_data_filters(timeseries_df, 'timeseries')
            
            return {
                'success': True,
                'buildings_df': buildings_df,
                'timeseries_df': timeseries_df,
                'preparation_info': {
                    'original_buildings_count': len(buildings_data),
                    'original_timeseries_count': len(timeseries_data),
                    'final_buildings_count': len(buildings_df),
                    'final_timeseries_count': len(timeseries_df),
                    'coherence_check': coherence_check
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur préparation données: {str(e)}")
            return {
                'success': False,
                'error': f"Erreur préparation: {str(e)}"
            }
    
    def _convert_buildings_to_dataframe(self, buildings_data: List[Dict], options: Dict) -> pd.DataFrame:
        """
        Convertit les données de bâtiments en DataFrame optimisé
        
        Args:
            buildings_data: Données des bâtiments
            options: Options de conversion
            
        Returns:
            pd.DataFrame: DataFrame optimisé
        """
        df = pd.DataFrame(buildings_data)
        
        # Optimisations des types de données
        if 'building_type' in df.columns:
            df['building_type'] = df['building_type'].astype('category')
        
        if 'zone_name' in df.columns:
            df['zone_name'] = df['zone_name'].astype('category')
        
        # Arrondissement des coordonnées
        if 'latitude' in df.columns:
            df['latitude'] = df['latitude'].round(6)
        if 'longitude' in df.columns:
            df['longitude'] = df['longitude'].round(6)
        
        # Arrondissement des valeurs numériques
        numeric_cols = df.select_dtypes(include=['float64', 'float32']).columns
        for col in numeric_cols:
            if 'consumption' in col.lower():
                df[col] = df[col].round(4)
            elif col in ['surface_area_m2']:
                df[col] = df[col].round(1)
        
        # Tri pour optimiser la compression
        if 'zone_name' in df.columns and 'building_type' in df.columns:
            df = df.sort_values(['zone_name', 'building_type', 'building_id'])
        
        return df
    
    def _convert_timeseries_to_dataframe(self, timeseries_data: List[Dict], options: Dict) -> pd.DataFrame:
        """
        Convertit les données de séries temporelles en DataFrame optimisé
        
        Args:
            timeseries_data: Données des séries temporelles
            options: Options de conversion
            
        Returns:
            pd.DataFrame: DataFrame optimisé
        """
        df = pd.DataFrame(timeseries_data)
        
        # Conversion et tri par timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(['building_id', 'timestamp'])
        
        # Optimisations des types
        if 'building_id' in df.columns:
            df['building_id'] = df['building_id'].astype('category')
        
        if 'building_type' in df.columns:
            df['building_type'] = df['building_type'].astype('category')
        
        # Optimisation des valeurs numériques
        if 'consumption_kwh' in df.columns:
            df['consumption_kwh'] = df['consumption_kwh'].round(4)
        
        if 'temperature_c' in df.columns:
            df['temperature_c'] = df['temperature_c'].round(2)
        
        if 'humidity' in df.columns:
            df['humidity'] = df['humidity'].round(3)
        
        # Optimisation des booléens
        bool_cols = ['is_weekend', 'is_business_hour', 'anomaly_flag']
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype('bool')
        
        # Optimisation des entiers
        int_cols = ['hour', 'day_of_week', 'month']
        for col in int_cols:
            if col in df.columns:
                df[col] = df[col].astype('int8')
        
        return df
    
    def _check_data_coherence(self, buildings_df: pd.DataFrame, timeseries_df: pd.DataFrame) -> Dict:
        """
        Vérifie la cohérence entre les DataFrames
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Résultats de vérification
        """
        issues = []
        warnings = []
        
        if buildings_df.empty or timeseries_df.empty:
            return {
                'coherent': False,
                'issues': ['DataFrames vides'],
                'warnings': []
            }
        
        # Vérification des IDs de bâtiments
        building_ids_meta = set(buildings_df['building_id'].unique())
        building_ids_ts = set(timeseries_df['building_id'].unique())
        
        missing_in_timeseries = building_ids_meta - building_ids_ts
        orphan_timeseries = building_ids_ts - building_ids_meta
        
        if missing_in_timeseries:
            warnings.append(f"{len(missing_in_timeseries)} bâtiments sans données temporelles")
        
        if orphan_timeseries:
            warnings.append(f"{len(orphan_timeseries)} séries temporelles sans bâtiment")
        
        # Vérification de la cohérence des types
        if 'building_type' in buildings_df.columns and 'building_type' in timeseries_df.columns:
            # Merger pour vérifier la cohérence
            merged = timeseries_df.merge(
                buildings_df[['building_id', 'building_type']], 
                on='building_id', 
                suffixes=('_ts', '_building')
            )
            
            type_mismatches = (merged['building_type_ts'] != merged['building_type_building']).sum()
            if type_mismatches > 0:
                issues.append(f"{type_mismatches} incohérences de types de bâtiments")
        
        # Vérification des données manquantes critiques
        critical_nulls_buildings = buildings_df[['building_id', 'latitude', 'longitude']].isnull().any(axis=1).sum()
        critical_nulls_timeseries = timeseries_df[['building_id', 'timestamp', 'consumption_kwh']].isnull().any(axis=1).sum()
        
        if critical_nulls_buildings > 0:
            issues.append(f"{critical_nulls_buildings} bâtiments avec données critiques manquantes")
        
        if critical_nulls_timeseries > 0:
            issues.append(f"{critical_nulls_timeseries} observations avec données critiques manquantes")
        
        return {
            'coherent': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'statistics': {
                'buildings_count': len(buildings_df),
                'timeseries_count': len(timeseries_df),
                'unique_buildings_in_timeseries': len(building_ids_ts),
                'coverage_percentage': (len(building_ids_ts & building_ids_meta) / len(building_ids_meta)) * 100 if building_ids_meta else 0
            }
        }
    
    def _apply_data_filters(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        Applique des filtres de nettoyage aux données
        
        Args:
            df: DataFrame à filtrer
            data_type: Type de données ('buildings' ou 'timeseries')
            
        Returns:
            pd.DataFrame: DataFrame filtré
        """
        original_count = len(df)
        
        if data_type == 'buildings':
            # Filtres pour les bâtiments
            if 'latitude' in df.columns and 'longitude' in df.columns:
                # Filtrer les coordonnées Malaysia valides
                df = df[
                    (df['latitude'] >= 0.5) & (df['latitude'] <= 7.5) &
                    (df['longitude'] >= 99.0) & (df['longitude'] <= 120.0)
                ]
            
            # Filtrer les consommations négatives
            if 'base_consumption_kwh' in df.columns:
                df = df[df['base_consumption_kwh'] >= 0]
        
        elif data_type == 'timeseries':
            # Filtres pour les séries temporelles
            if 'consumption_kwh' in df.columns:
                # Supprimer les consommations négatives ou extrêmes
                df = df[
                    (df['consumption_kwh'] >= 0) & 
                    (df['consumption_kwh'] <= 1000)  # Max 1000 kWh par période
                ]
            
            # Filtrer les températures irréalistes pour Malaysia
            if 'temperature_c' in df.columns:
                df = df[
                    (df['temperature_c'] >= 15) & 
                    (df['temperature_c'] <= 50)
                ]
            
            # Filtrer l'humidité irréaliste
            if 'humidity' in df.columns:
                df = df[
                    (df['humidity'] >= 0.2) & 
                    (df['humidity'] <= 1.0)
                ]
        
        filtered_count = len(df)
        if filtered_count < original_count:
            logger.info(f"🧹 Filtrage {data_type}: {original_count} → {filtered_count} ({original_count - filtered_count} supprimés)")
        
        return df
    
    def _optimize_export_formats(self, requested_formats: List[str], data_size: int) -> List[str]:
        """
        Optimise les formats d'export selon la taille des données
        
        Args:
            requested_formats: Formats demandés
            data_size: Taille des données
            
        Returns:
            List[str]: Formats optimisés
        """
        optimized_formats = []
        
        for format_type in requested_formats:
            if format_type not in EXPORT_CONFIG.SUPPORTED_FORMATS:
                logger.warning(f"⚠️ Format {format_type} non supporté, ignoré")
                continue
            
            # Optimisations selon la taille
            if format_type == 'xlsx' and data_size > 100000:
                logger.warning("⚠️ Excel non recommandé pour >100k observations, ajout de CSV")
                optimized_formats.extend(['csv', 'parquet'])
                continue
            
            if format_type == 'json' and data_size > 50000:
                logger.warning("⚠️ JSON non recommandé pour >50k observations")
                optimized_formats.append('parquet')
                continue
            
            optimized_formats.append(format_type)
        
        # Assurer au moins un format efficace
        if not optimized_formats:
            optimized_formats = ['csv', 'parquet']
        
        return list(set(optimized_formats))  # Supprimer les doublons
    
    def _generate_intelligent_filename(
        self, 
        buildings_data: List[Dict], 
        timeseries_data: List[Dict]
    ) -> str:
        """
        Génère un nom de fichier intelligent basé sur les données
        
        Args:
            buildings_data: Données des bâtiments
            timeseries_data: Données des séries temporelles
            
        Returns:
            str: Préfixe de fichier intelligent
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extraction des métadonnées
        zones = set()
        building_types = set()
        
        for building in buildings_data:
            if building.get('zone_name'):
                zones.add(building['zone_name'])
            if building.get('building_type'):
                building_types.add(building['building_type'])
        
        # Construction du nom
        name_parts = ['malaysia_electricity']
        
        # Ajouter la zone si unique
        if len(zones) == 1:
            zone_name = list(zones)[0].replace(' ', '_').lower()
            name_parts.append(zone_name)
        elif len(zones) <= 3:
            zone_names = '_'.join([z.replace(' ', '_').lower() for z in sorted(zones)])
            name_parts.append(zone_names)
        else:
            name_parts.append('multi_zones')
        
        # Ajouter le nombre de bâtiments
        name_parts.append(f"{len(buildings_data)}buildings")
        
        # Ajouter le timestamp
        name_parts.append(timestamp)
        
        return '_'.join(name_parts)
    
    def _enrich_export_result(
        self, 
        export_result: Dict, 
        preparation_result: Dict, 
        manifest_path: str
    ) -> Dict:
        """
        Enrichit le résultat d'export avec des métadonnées métier
        
        Args:
            export_result: Résultat d'export de base
            preparation_result: Résultat de préparation
            manifest_path: Chemin du manifest
            
        Returns:
            Dict: Résultat enrichi
        """
        enriched = export_result.copy()
        
        # Ajout d'informations de service
        enriched['service_metadata'] = {
            'export_service_version': '1.0.0',
            'preparation_info': preparation_result.get('preparation_info', {}),
            'manifest_path': manifest_path,
            'usage_recommendations': self._generate_usage_recommendations(export_result),
            'data_quality_assessment': self._assess_export_quality(export_result)
        }
        
        # Ajout de liens de téléchargement
        enriched['download_links'] = self._generate_download_links(export_result)
        
        # Mise à jour des statistiques de service
        self.service_statistics['total_files_created'] += len(export_result.get('files_created', {}))
        
        return enriched
    
    def _generate_usage_recommendations(self, export_result: Dict) -> List[str]:
        """
        Génère des recommandations d'usage pour les fichiers exportés
        
        Args:
            export_result: Résultat d'export
            
        Returns:
            List[str]: Recommandations d'usage
        """
        recommendations = []
        
        files_created = export_result.get('files_created', {})
        total_size_mb = export_result.get('total_size_mb', 0)
        
        # Recommandations par format
        if 'csv' in files_created:
            recommendations.append("Fichiers CSV: Utilisez Excel ou pandas (Python) pour l'analyse")
        
        if 'parquet' in files_created:
            recommendations.append("Fichiers Parquet: Format optimisé pour Python pandas, Apache Spark")
        
        if 'xlsx' in files_created:
            recommendations.append("Fichier Excel: Ouvrir avec Microsoft Excel, contient onglets multiples")
        
        if 'json' in files_created:
            recommendations.append("Fichiers JSON: Format pour APIs web et applications JavaScript")
        
        # Recommandations par taille
        if total_size_mb > 100:
            recommendations.append("Gros dataset: Utilisez Python pandas ou R pour l'analyse")
        elif total_size_mb < 1:
            recommendations.append("Petit dataset: Compatible avec tous les outils d'analyse")
        
        return recommendations
    
    def _assess_export_quality(self, export_result: Dict) -> Dict:
        """
        Évalue la qualité de l'export réalisé
        
        Args:
            export_result: Résultat d'export
            
        Returns:
            Dict: Évaluation de qualité
        """
        quality_score = 100.0
        issues = []
        
        # Vérification des fichiers créés
        files_created = export_result.get('files_created', {})
        
        if not files_created:
            quality_score = 0
            issues.append("Aucun fichier créé")
        else:
            # Vérification par format
            for format_type, format_info in files_created.items():
                if not format_info.get('success', True):
                    quality_score -= 20
                    issues.append(f"Échec export {format_type}")
        
        # Vérification de la validation des données
        validation_results = export_result.get('validation_results', {})
        if not validation_results.get('valid', True):
            quality_score -= 30
            issues.extend(validation_results.get('errors', []))
        
        # Bonus pour formats multiples
        if len(files_created) > 1:
            quality_score += 5
        
        return {
            'quality_score': max(0, quality_score),
            'issues': issues,
            'recommendations': [
                "Vérifiez l'intégrité des fichiers avant utilisation",
                "Consultez le manifest pour les détails techniques"
            ]
        }
    
    def _generate_download_links(self, export_result: Dict) -> Dict:
        """
        Génère les liens de téléchargement pour les fichiers
        
        Args:
            export_result: Résultat d'export
            
        Returns:
            Dict: Liens de téléchargement
        """
        download_links = {}
        
        files_created = export_result.get('files_created', {})
        
        for format_type, format_info in files_created.items():
            if format_info.get('success', True):
                format_files = format_info.get('files', {})
                
                download_links[format_type] = {}
                
                for file_type, file_info in format_files.items():
                    if 'path' in file_info:
                        filename = os.path.basename(file_info['path'])
                        download_links[format_type][file_type] = {
                            'filename': filename,
                            'size_mb': file_info.get('size_mb', 0),
                            'download_url': f"/api/download/{filename}"
                        }
        
        return download_links
    
    def get_service_status(self) -> Dict:
        """
        Retourne l'état du service d'export
        
        Returns:
            Dict: État détaillé du service
        """
        uptime = datetime.now() - self.service_statistics['service_start_time']
        
        success_rate = 0
        if self.service_statistics['total_exports'] > 0:
            success_rate = (
                self.service_statistics['successful_exports'] / 
                self.service_statistics['total_exports']
            ) * 100
        
        # Vérification de l'espace disque
        disk_space_ok = True
        try:
            import shutil
            total, used, free = shutil.disk_usage(APP_CONFIG.EXPORTS_DIR)
            free_gb = free / (1024**3)
            disk_space_ok = free_gb > 1.0  # Au moins 1GB libre
        except:
            free_gb = 0
        
        return {
            'service_name': 'Export Service',
            'status': 'active' if disk_space_ok else 'degraded',
            'uptime_seconds': int(uptime.total_seconds()),
            'disk_space_gb': round(free_gb, 1),
            'statistics': {
                'total_exports': self.service_statistics['total_exports'],
                'successful_exports': self.service_statistics['successful_exports'],
                'success_rate_percent': round(success_rate, 1),
                'total_files_created': self.service_statistics['total_files_created'],
                'total_size_exported_mb': round(self.service_statistics['total_size_exported_mb'], 2)
            }
        }
    
    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques détaillées du service
        
        Returns:
            Dict: Statistiques complètes
        """
        return self.service_statistics.copy()


# ==============================================================================
# FONCTIONS UTILITAIRES DU SERVICE
# ==============================================================================

def estimate_export_time(data_size: int, formats: List[str]) -> Dict:
    """
    Estime le temps d'export selon la taille et les formats
    
    Args:
        data_size: Nombre d'observations
        formats: Liste des formats
        
    Returns:
        Dict: Estimations de temps
    """
    # Temps de base par format (secondes pour 1000 observations)
    format_times = {
        'csv': 0.5,
        'parquet': 0.3,
        'xlsx': 2.0,
        'json': 1.0
    }
    
    total_time = 0
    format_estimates = {}
    
    for format_type in formats:
        if format_type in format_times:
            format_time = (data_size / 1000) * format_times[format_type]
            format_estimates[format_type] = round(format_time, 1)
            total_time += format_time
    
    return {
        'total_time_seconds': round(total_time, 1),
        'format_breakdown': format_estimates,
        'complexity': 'simple' if total_time < 10 else 'moderate' if total_time < 60 else 'complex'
    }


def validate_export_request(
    buildings_count: int, 
    timeseries_count: int, 
    formats: List[str]
) -> Dict:
    """
    Valide une demande d'export
    
    Args:
        buildings_count: Nombre de bâtiments
        timeseries_count: Nombre d'observations
        formats: Formats demandés
        
    Returns:
        Dict: Résultats de validation
    """
    errors = []
    warnings = []
    
    # Validation des tailles
    if buildings_count == 0:
        errors.append("Aucun bâtiment à exporter")
    
    if timeseries_count == 0:
        errors.append("Aucune donnée temporelle à exporter")
    
    if timeseries_count > 1000000:
        warnings.append("Dataset très volumineux - export long")
    
    # Validation des formats
    if not formats:
        errors.append("Aucun format d'export spécifié")
    
    unsupported_formats = [f for f in formats if f not in EXPORT_CONFIG.SUPPORTED_FORMATS]
    if unsupported_formats:
        errors.append(f"Formats non supportés: {unsupported_formats}")
    
    # Recommandations
    if 'xlsx' in formats and timeseries_count > 100000:
        warnings.append("Excel non recommandé pour >100k observations")
    
    if 'json' in formats and timeseries_count > 50000:
        warnings.append("JSON non recommandé pour gros datasets")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test du service d'export
    from src.core.data_exporter import DataExporter
    
    # Initialisation
    data_exporter = DataExporter()
    export_service = ExportService(data_exporter)
    
    # Données de test
    test_buildings = [
        {
            'building_id': 'B001',
            'latitude': 3.15,
            'longitude': 101.7,
            'building_type': 'residential',
            'zone_name': 'kuala_lumpur'
        }
    ]
    
    test_timeseries = [
        {
            'building_id': 'B001',
            'timestamp': '2024-01-01T10:00:00',
            'consumption_kwh': 2.5,
            'temperature_c': 30.0,
            'humidity': 0.8,
            'building_type': 'residential'
        }
    ]
    
    # Test d'export
    result = export_service.export_complete_dataset(
        buildings_data=test_buildings,
        timeseries_data=test_timeseries,
        formats=['csv', 'parquet']
    )
    
    if result['success']:
        print(f"✅ Export test réussi:")
        print(f"📁 {len(result['files_created'])} formats créés")
        print(f"💾 {result['total_size_mb']:.2f} MB")
        print(f"🎯 Score qualité: {result['service_metadata']['data_quality_assessment']['quality_score']}")
    else:
        print(f"❌ Export échoué: {result['error']}")
    
    # Statut du service
    status = export_service.get_service_status()
    print(f"📊 Service: {status['status']}, {status['statistics']['success_rate_percent']}% succès")

                