"""
Exporteur de données pour les formats CSV et Parquet
==================================================

Ce module gère l'export des données générées vers différents formats
avec optimisation et validation automatique.
"""

import pandas as pd
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from config import EXPORT_CONFIG, APP_CONFIG


# Configuration du logger
logger = logging.getLogger(__name__)


class DataExporter:
    """
    Gestionnaire d'export de données vers multiple formats
    
    Supporte CSV, Parquet, Excel et JSON avec optimisation
    et validation automatique des données exportées.
    """
    
    def __init__(self, export_directory: str = None):
        """
        Initialise l'exporteur de données
        
        Args:
            export_directory: Dossier d'export (optionnel)
        """
        self.export_directory = export_directory or APP_CONFIG.EXPORTS_DIR
        
        # Créer le dossier d'export s'il n'existe pas
        os.makedirs(self.export_directory, exist_ok=True)
        
        # Statistiques d'export
        self.export_count = 0
        self.total_files_created = 0
        self.total_size_mb = 0.0
        
        logger.info(f"✅ Exporteur initialisé - Dossier: {self.export_directory}")
    
    def export_complete_dataset(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame,
        formats: List[str] = ['csv', 'parquet'],
        filename_prefix: str = None
    ) -> Dict:
        """
        Exporte un dataset complet (bâtiments + séries temporelles)
        
        Args:
            buildings_df: DataFrame des métadonnées de bâtiments
            timeseries_df: DataFrame des séries temporelles
            formats: Liste des formats à exporter
            filename_prefix: Préfixe pour les noms de fichiers
            
        Returns:
            Dict: Résultats d'export avec chemins et statistiques
        """
        logger.info(f"🔄 Export dataset complet - Formats: {formats}")
        
        # Validation des DataFrames
        validation_results = self._validate_dataframes(buildings_df, timeseries_df)
        if not validation_results['valid']:
            raise ValueError(f"Données invalides: {validation_results['errors']}")
        
        # Génération des noms de fichiers
        if not filename_prefix:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_prefix = f"malaysia_electricity_{timestamp}"
        
        export_results = {
            'success': True,
            'export_timestamp': datetime.now().isoformat(),
            'files_created': {},
            'total_size_mb': 0.0,
            'validation_results': validation_results,
            'statistics': {}
        }
        
        # Export pour chaque format demandé
        for format_type in formats:
            if format_type not in EXPORT_CONFIG.SUPPORTED_FORMATS:
                logger.warning(f"⚠️ Format {format_type} non supporté, ignoré")
                continue
            
            try:
                format_results = self._export_format(
                    buildings_df, timeseries_df, format_type, filename_prefix
                )
                export_results['files_created'][format_type] = format_results
                export_results['total_size_mb'] += format_results['total_size_mb']
                
            except Exception as e:
                logger.error(f"❌ Erreur export {format_type}: {str(e)}")
                export_results['files_created'][format_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Génération des statistiques finales
        export_results['statistics'] = self._generate_export_statistics(
            buildings_df, timeseries_df
        )
        
        # Mise à jour des compteurs
        self.export_count += 1
        self.total_size_mb += export_results['total_size_mb']
        
        logger.info(f"✅ Export terminé - {export_results['total_size_mb']:.2f} MB créés")
        
        return export_results
    
    def _validate_dataframes(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame
    ) -> Dict:
        """
        Valide les DataFrames avant export
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Résultats de validation
        """
        errors = []
        warnings = []
        
        # Validation DataFrame bâtiments
        if buildings_df.empty:
            errors.append("DataFrame bâtiments vide")
        else:
            # Colonnes requises pour les bâtiments
            required_building_cols = [
                'building_id', 'latitude', 'longitude', 'building_type'
            ]
            missing_cols = [col for col in required_building_cols if col not in buildings_df.columns]
            if missing_cols:
                errors.append(f"Colonnes manquantes bâtiments: {missing_cols}")
            
            # Vérification valeurs nulles critiques
            if buildings_df['building_id'].isnull().any():
                errors.append("IDs de bâtiments manquants")
            
            # Vérification coordonnées Malaysia
            invalid_coords = (
                (buildings_df['latitude'] < 0.5) | (buildings_df['latitude'] > 7.5) |
                (buildings_df['longitude'] < 99.0) | (buildings_df['longitude'] > 120.0)
            ).sum()
            if invalid_coords > 0:
                warnings.append(f"{invalid_coords} bâtiments avec coordonnées hors Malaysia")
        
        # Validation DataFrame séries temporelles
        if timeseries_df.empty:
            errors.append("DataFrame séries temporelles vide")
        else:
            # Colonnes requises pour les séries temporelles
            required_timeseries_cols = [
                'building_id', 'timestamp', 'consumption_kwh'
            ]
            missing_cols = [col for col in required_timeseries_cols if col not in timeseries_df.columns]
            if missing_cols:
                errors.append(f"Colonnes manquantes séries temporelles: {missing_cols}")
            
            # Vérification valeurs de consommation
            negative_consumption = (timeseries_df['consumption_kwh'] < 0).sum()
            if negative_consumption > 0:
                warnings.append(f"{negative_consumption} valeurs de consommation négatives")
            
            null_consumption = timeseries_df['consumption_kwh'].isnull().sum()
            if null_consumption > 0:
                warnings.append(f"{null_consumption} valeurs de consommation manquantes")
        
        # Validation cohérence entre DataFrames
        if not buildings_df.empty and not timeseries_df.empty:
            building_ids_set = set(buildings_df['building_id'])
            timeseries_ids_set = set(timeseries_df['building_id'])
            
            # Bâtiments sans données temporelles
            missing_timeseries = building_ids_set - timeseries_ids_set
            if missing_timeseries:
                warnings.append(f"{len(missing_timeseries)} bâtiments sans données temporelles")
            
            # Données temporelles sans bâtiments
            orphan_timeseries = timeseries_ids_set - building_ids_set
            if orphan_timeseries:
                warnings.append(f"{len(orphan_timeseries)} séries temporelles sans bâtiment associé")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'buildings_count': len(buildings_df) if not buildings_df.empty else 0,
            'timeseries_count': len(timeseries_df) if not timeseries_df.empty else 0
        }
    
    def _export_format(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame, 
        format_type: str, 
        filename_prefix: str
    ) -> Dict:
        """
        Exporte vers un format spécifique
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            format_type: Type de format (csv, parquet, etc.)
            filename_prefix: Préfixe des fichiers
            
        Returns:
            Dict: Résultats d'export pour ce format
        """
        format_results = {
            'success': True,
            'format': format_type,
            'files': {},
            'total_size_mb': 0.0
        }
        
        # Noms de fichiers
        buildings_filename = f"{filename_prefix}_buildings.{format_type}"
        timeseries_filename = f"{filename_prefix}_timeseries.{format_type}"
        
        buildings_path = os.path.join(self.export_directory, buildings_filename)
        timeseries_path = os.path.join(self.export_directory, timeseries_filename)
        
        try:
            # Export selon le format
            if format_type == 'csv':
                self._export_csv(buildings_df, buildings_path, 'buildings')
                self._export_csv(timeseries_df, timeseries_path, 'timeseries')
            
            elif format_type == 'parquet':
                self._export_parquet(buildings_df, buildings_path, 'buildings')
                self._export_parquet(timeseries_df, timeseries_path, 'timeseries')
            
            elif format_type == 'xlsx':
                # Export Excel avec onglets multiples
                excel_path = os.path.join(self.export_directory, f"{filename_prefix}.xlsx")
                self._export_excel(buildings_df, timeseries_df, excel_path)
                format_results['files']['excel'] = {
                    'path': excel_path,
                    'size_mb': os.path.getsize(excel_path) / (1024 * 1024)
                }
            
            elif format_type == 'json':
                self._export_json(buildings_df, timeseries_df, filename_prefix)
            
            # Calcul des tailles de fichiers (sauf Excel déjà traité)
            if format_type != 'xlsx':
                if os.path.exists(buildings_path):
                    size_mb = os.path.getsize(buildings_path) / (1024 * 1024)
                    format_results['files']['buildings'] = {
                        'path': buildings_path,
                        'size_mb': size_mb
                    }
                    format_results['total_size_mb'] += size_mb
                
                if os.path.exists(timeseries_path):
                    size_mb = os.path.getsize(timeseries_path) / (1024 * 1024)
                    format_results['files']['timeseries'] = {
                        'path': timeseries_path,
                        'size_mb': size_mb
                    }
                    format_results['total_size_mb'] += size_mb
            
            self.total_files_created += len(format_results['files'])
            
        except Exception as e:
            format_results['success'] = False
            format_results['error'] = str(e)
            logger.error(f"❌ Erreur export {format_type}: {str(e)}")
        
        return format_results
    
    def _export_csv(self, df: pd.DataFrame, filepath: str, data_type: str):
        """
        Exporte un DataFrame vers CSV avec optimisations
        
        Args:
            df: DataFrame à exporter
            filepath: Chemin du fichier
            data_type: Type de données ('buildings' ou 'timeseries')
        """
        if df.empty:
            logger.warning(f"⚠️ DataFrame {data_type} vide, export CSV ignoré")
            return
        
        # Optimisations spécifiques selon le type
        df_optimized = df.copy()
        
        if data_type == 'timeseries':
            # Optimisation des timestamps
            if 'timestamp' in df_optimized.columns:
                df_optimized['timestamp'] = pd.to_datetime(df_optimized['timestamp'])
                df_optimized['timestamp'] = df_optimized['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Arrondir les valeurs numériques
            numeric_cols = df_optimized.select_dtypes(include=['float64', 'float32']).columns
            df_optimized[numeric_cols] = df_optimized[numeric_cols].round(4)
        
        # Export CSV avec configuration optimisée
        df_optimized.to_csv(
            filepath,
            index=False,
            encoding=EXPORT_CONFIG.CSV_ENCODING,
            sep=EXPORT_CONFIG.CSV_SEPARATOR,
            float_format='%.4f',
            date_format=EXPORT_CONFIG.CSV_DATE_FORMAT
        )
        
        logger.info(f"✅ CSV {data_type} exporté: {os.path.basename(filepath)}")
    
    def _export_parquet(self, df: pd.DataFrame, filepath: str, data_type: str):
        """
        Exporte un DataFrame vers Parquet avec compression
        
        Args:
            df: DataFrame à exporter
            filepath: Chemin du fichier
            data_type: Type de données
        """
        if df.empty:
            logger.warning(f"⚠️ DataFrame {data_type} vide, export Parquet ignoré")
            return
        
        # Optimisations spécifiques
        df_optimized = df.copy()
        
        # Optimisation des types de données
        for col in df_optimized.columns:
            if df_optimized[col].dtype == 'object':
                # Convertir les chaînes en catégories si répétitives
                if df_optimized[col].nunique() / len(df_optimized) < 0.5:
                    df_optimized[col] = df_optimized[col].astype('category')
        
        # Conversion des timestamps
        if 'timestamp' in df_optimized.columns:
            df_optimized['timestamp'] = pd.to_datetime(df_optimized['timestamp'])
        
        # Export Parquet avec compression
        df_optimized.to_parquet(
            filepath,
            engine=EXPORT_CONFIG.PARQUET_ENGINE,
            compression=EXPORT_CONFIG.PARQUET_COMPRESSION,
            index=False
        )
        
        logger.info(f"✅ Parquet {data_type} exporté: {os.path.basename(filepath)}")
    
    def _export_excel(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame, 
        filepath: str
    ):
        """
        Exporte vers Excel avec onglets multiples
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            filepath: Chemin du fichier Excel
        """
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Onglet métadonnées bâtiments
            if not buildings_df.empty:
                buildings_df.to_excel(writer, sheet_name='Buildings', index=False)
            
            # Onglet séries temporelles (limité pour éviter les gros fichiers)
            if not timeseries_df.empty:
                # Limiter à 100k lignes pour Excel
                if len(timeseries_df) > 100000:
                    sample_df = timeseries_df.sample(n=100000).sort_values('timestamp')
                    sample_df.to_excel(writer, sheet_name='Timeseries_Sample', index=False)
                    
                    # Ajouter une note d'information
                    info_df = pd.DataFrame({
                        'Info': ['Échantillon de 100k observations sur ' + str(len(timeseries_df)) + ' total'],
                        'Note': ['Utilisez CSV ou Parquet pour les données complètes']
                    })
                    info_df.to_excel(writer, sheet_name='Info', index=False)
                else:
                    timeseries_df.to_excel(writer, sheet_name='Timeseries', index=False)
            
            # Onglet statistiques
            stats_df = self._create_statistics_sheet(buildings_df, timeseries_df)
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        
        logger.info(f"✅ Excel exporté: {os.path.basename(filepath)}")
    
    def _export_json(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame, 
        filename_prefix: str
    ):
        """
        Exporte vers JSON avec structure optimisée
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            filename_prefix: Préfixe des fichiers
        """
        # Export bâtiments en JSON
        if not buildings_df.empty:
            buildings_json_path = os.path.join(
                self.export_directory, f"{filename_prefix}_buildings.json"
            )
            buildings_df.to_json(
                buildings_json_path, 
                orient='records', 
                date_format='iso', 
                indent=2
            )
        
        # Export séries temporelles en JSON (structure optimisée)
        if not timeseries_df.empty:
            timeseries_json_path = os.path.join(
                self.export_directory, f"{filename_prefix}_timeseries.json"
            )
            
            # Structure optimisée par bâtiment
            timeseries_grouped = {}
            for building_id in timeseries_df['building_id'].unique():
                building_data = timeseries_df[timeseries_df['building_id'] == building_id]
                timeseries_grouped[building_id] = building_data.to_dict('records')
            
            with open(timeseries_json_path, 'w', encoding='utf-8') as f:
                json.dump(timeseries_grouped, f, indent=2, default=str)
        
        logger.info(f"✅ JSON exporté: {filename_prefix}")
    
    def _create_statistics_sheet(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Crée une feuille de statistiques pour Excel
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            pd.DataFrame: Statistiques formatées
        """
        stats_data = []
        
        # Statistiques générales
        stats_data.append(['=== STATISTIQUES GÉNÉRALES ===', ''])
        stats_data.append(['Nombre de bâtiments', len(buildings_df) if not buildings_df.empty else 0])
        stats_data.append(['Observations temporelles', len(timeseries_df) if not timeseries_df.empty else 0])
        stats_data.append(['Date export', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        stats_data.append(['', ''])
        
        # Statistiques des bâtiments
        if not buildings_df.empty:
            stats_data.append(['=== BÂTIMENTS ===', ''])
            
            # Distribution par type
            type_counts = buildings_df['building_type'].value_counts()
            stats_data.append(['Distribution par type:', ''])
            for building_type, count in type_counts.items():
                stats_data.append([f"  {building_type}", count])
            
            # Surface moyenne
            if 'surface_area_m2' in buildings_df.columns:
                avg_surface = buildings_df['surface_area_m2'].mean()
                stats_data.append(['Surface moyenne (m²)', f"{avg_surface:.1f}"])
            
            stats_data.append(['', ''])
        
        # Statistiques de consommation
        if not timeseries_df.empty:
            stats_data.append(['=== CONSOMMATION ÉLECTRIQUE ===', ''])
            
            consumption_stats = timeseries_df['consumption_kwh'].describe()
            for stat_name, value in consumption_stats.items():
                stats_data.append([f"Consommation {stat_name}", f"{value:.4f}"])
            
            # Consommation totale
            total_consumption = timeseries_df['consumption_kwh'].sum()
            stats_data.append(['Consommation totale (kWh)', f"{total_consumption:.2f}"])
            
            # Période temporelle
            if 'timestamp' in timeseries_df.columns:
                start_date = timeseries_df['timestamp'].min()
                end_date = timeseries_df['timestamp'].max()
                stats_data.append(['Période début', str(start_date)])
                stats_data.append(['Période fin', str(end_date)])
        
        return pd.DataFrame(stats_data, columns=['Statistique', 'Valeur'])
    
    def _generate_export_statistics(
        self, 
        buildings_df: pd.DataFrame, 
        timeseries_df: pd.DataFrame
    ) -> Dict:
        """
        Génère des statistiques complètes d'export
        
        Args:
            buildings_df: DataFrame des bâtiments
            timeseries_df: DataFrame des séries temporelles
            
        Returns:
            Dict: Statistiques d'export
        """
        stats = {
            'export_summary': {
                'buildings_exported': len(buildings_df) if not buildings_df.empty else 0,
                'timeseries_observations': len(timeseries_df) if not timeseries_df.empty else 0,
                'export_session_count': self.export_count,
                'total_files_created_session': self.total_files_created
            },
            'data_quality': {
                'buildings_completeness': 0.0,
                'timeseries_completeness': 0.0,
                'data_consistency_score': 0.0
            }
        }
        
        # Analyse qualité bâtiments
        if not buildings_df.empty:
            required_cols = ['building_id', 'latitude', 'longitude', 'building_type']
            completeness_scores = []
            
            for col in required_cols:
                if col in buildings_df.columns:
                    completeness = 1 - (buildings_df[col].isnull().sum() / len(buildings_df))
                    completeness_scores.append(completeness)
            
            stats['data_quality']['buildings_completeness'] = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
        
        # Analyse qualité séries temporelles
        if not timeseries_df.empty:
            required_cols = ['building_id', 'timestamp', 'consumption_kwh']
            completeness_scores = []
            
            for col in required_cols:
                if col in timeseries_df.columns:
                    completeness = 1 - (timeseries_df[col].isnull().sum() / len(timeseries_df))
                    completeness_scores.append(completeness)
            
            stats['data_quality']['timeseries_completeness'] = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
            
            # Score de cohérence (pas de valeurs négatives)
            if 'consumption_kwh' in timeseries_df.columns:
                negative_count = (timeseries_df['consumption_kwh'] < 0).sum()
                consistency_score = 1 - (negative_count / len(timeseries_df))
                stats['data_quality']['data_consistency_score'] = consistency_score
        
        return stats
    
    def create_export_manifest(self, export_results: Dict) -> str:
        """
        Crée un fichier manifest décrivant l'export
        
        Args:
            export_results: Résultats d'export
            
        Returns:
            str: Chemin du fichier manifest
        """
        manifest_data = {
            'export_metadata': {
                'export_timestamp': export_results['export_timestamp'],
                'exporter_version': '1.0.0',
                'total_size_mb': export_results['total_size_mb']
            },
            'files_created': export_results['files_created'],
            'validation_results': export_results['validation_results'],
            'statistics': export_results['statistics'],
            'usage_instructions': {
                'csv_files': 'Lisibles avec Excel, Python pandas, R',
                'parquet_files': 'Format optimisé pour analyse big data (Python, Spark)',
                'excel_files': 'Fichier Excel avec onglets multiples',
                'json_files': 'Format structuré pour APIs et applications web'
            }
        }
        
        manifest_path = os.path.join(self.export_directory, 'export_manifest.json')
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, default=str)
        
        logger.info(f"✅ Manifest créé: {manifest_path}")
        return manifest_path
    
    def get_export_statistics(self) -> Dict:
        """
        Retourne les statistiques globales de l'exporteur
        
        Returns:
            Dict: Statistiques de session
        """
        return {
            'session_stats': {
                'total_exports': self.export_count,
                'total_files_created': self.total_files_created,
                'total_size_mb': round(self.total_size_mb, 2),
                'export_directory': self.export_directory
            },
            'supported_formats': EXPORT_CONFIG.SUPPORTED_FORMATS,
            'directory_info': {
                'exists': os.path.exists(self.export_directory),
                'writable': os.access(self.export_directory, os.W_OK),
                'files_count': len(os.listdir(self.export_directory)) if os.path.exists(self.export_directory) else 0
            }
        }


# ==============================================================================
# FONCTIONS UTILITAIRES D'EXPORT
# ==============================================================================

def quick_csv_export(
    buildings_df: pd.DataFrame, 
    timeseries_df: pd.DataFrame, 
    output_dir: str = None
) -> Tuple[str, str]:
    """
    Export CSV rapide sans validation complète
    
    Args:
        buildings_df: DataFrame des bâtiments
        timeseries_df: DataFrame des séries temporelles
        output_dir: Dossier de sortie
        
    Returns:
        Tuple[str, str]: Chemins des fichiers créés
    """
    if output_dir is None:
        output_dir = APP_CONFIG.EXPORTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    buildings_path = os.path.join(output_dir, f"buildings_{timestamp}.csv")
    timeseries_path = os.path.join(output_dir, f"timeseries_{timestamp}.csv")
    
    if not buildings_df.empty:
        buildings_df.to_csv(buildings_path, index=False)
    
    if not timeseries_df.empty:
        timeseries_df.to_csv(timeseries_path, index=False)
    
    return buildings_path, timeseries_path


def calculate_file_size_estimate(
    num_buildings: int, 
    num_timeseries_points: int
) -> Dict:
    """
    Estime la taille des fichiers d'export
    
    Args:
        num_buildings: Nombre de bâtiments
        num_timeseries_points: Nombre de points temporels
        
    Returns:
        Dict: Estimations de taille par format
    """
    # Estimations basées sur des moyennes observées
    bytes_per_building = 500     # métadonnées par bâtiment
    bytes_per_timeseries = 200   # point temporel
    
    buildings_size_bytes = num_buildings * bytes_per_building
    timeseries_size_bytes = num_timeseries_points * bytes_per_timeseries
    
    total_size_bytes = buildings_size_bytes + timeseries_size_bytes
    
    # Facteurs de compression/expansion par format
    format_factors = {
        'csv': 1.0,        # référence
        'parquet': 0.3,    # compression efficace
        'xlsx': 1.2,       # légèrement plus lourd
        'json': 1.4        # structure verbale
    }
    
    estimates = {}
    for format_name, factor in format_factors.items():
        size_mb = (total_size_bytes * factor) / (1024 * 1024)
        estimates[format_name] = {
            'size_mb': round(size_mb, 2),
            'size_formatted': f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_mb * 1024:.0f} KB"
        }
    
    return estimates


def validate_export_directory(directory_path: str) -> Dict:
    """
    Valide qu'un dossier d'export est utilisable
    
    Args:
        directory_path: Chemin du dossier
        
    Returns:
        Dict: Résultats de validation
    """
    results = {
        'valid': False,
        'exists': False,
        'writable': False,
        'space_available_mb': 0,
        'errors': []
    }
    
    try:
        # Vérification existence
        if os.path.exists(directory_path):
            results['exists'] = True
            
            # Vérification permissions d'écriture
            if os.access(directory_path, os.W_OK):
                results['writable'] = True
            else:
                results['errors'].append("Pas de permission d'écriture")
        else:
            # Tentative de création
            try:
                os.makedirs(directory_path, exist_ok=True)
                results['exists'] = True
                results['writable'] = True
            except Exception as e:
                results['errors'].append(f"Impossible de créer le dossier: {str(e)}")
        
        # Vérification espace disque (si possible)
        if results['exists']:
            try:
                import shutil
                total, used, free = shutil.disk_usage(directory_path)
                results['space_available_mb'] = free / (1024 * 1024)
            except:
                results['space_available_mb'] = 0  # Information non disponible
        
        results['valid'] = results['exists'] and results['writable']
        
    except Exception as e:
        results['errors'].append(f"Erreur validation: {str(e)}")
    
    return results


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    # Test de l'exporteur
    import pandas as pd
    
    # Création de données de test
    test_buildings = pd.DataFrame({
        'building_id': ['B001', 'B002', 'B003'],
        'latitude': [3.15, 3.16, 3.17],
        'longitude': [101.7, 101.71, 101.72],
        'building_type': ['residential', 'commercial', 'office'],
        'surface_area_m2': [150, 300, 500]
    })
    
    test_timeseries = pd.DataFrame({
        'building_id': ['B001', 'B001', 'B002', 'B002'],
        'timestamp': pd.date_range('2024-01-01', periods=4, freq='1H'),
        'consumption_kwh': [2.5, 3.0, 5.0, 4.5],
        'building_type': ['residential', 'residential', 'commercial', 'commercial']
    })
    
    # Test de l'exporteur
    exporter = DataExporter()
    
    # Export complet
    results = exporter.export_complete_dataset(
        test_buildings, 
        test_timeseries, 
        formats=['csv', 'parquet']
    )
    
    print(f"✅ Export test terminé:")
    print(f"📁 Fichiers: {len(results['files_created'])}")
    print(f"📊 Taille: {results['total_size_mb']:.2f} MB")
    
    # Création du manifest
    manifest_path = exporter.create_export_manifest(results)
    print(f"📋 Manifest: {manifest_path}")

                