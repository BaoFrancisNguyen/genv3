"""
Service d'Export - Couche métier pour l'export de données
========================================================

Service simplifié pour l'export des données générées.
"""

import logging
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional

# Configuration du logger
logger = logging.getLogger(__name__)


class ExportService:
    """Service métier pour l'export de données"""
    
    def __init__(self, data_exporter=None):
        """Initialise le service d'export"""
        self.data_exporter = data_exporter
        self.export_statistics = {
            'total_exports': 0,
            'successful_exports': 0,
            'total_files_created': 0,
            'service_start_time': datetime.now()
        }
        
        logger.info("✅ Service d'export initialisé")
    
    def export_complete_dataset(
        self,
        buildings_data: List[Dict],
        timeseries_data: List[Dict],
        formats: List[str] = None,
        filename_prefix: str = None
    ) -> Dict:
        """
        Exporte un dataset complet
        
        Args:
            buildings_data: Données des bâtiments
            timeseries_data: Données des séries temporelles
            formats: Formats d'export
            filename_prefix: Préfixe pour les noms de fichiers
            
        Returns:
            Dict: Résultat de l'export
        """
        try:
            self.export_statistics['total_exports'] += 1
            
            if formats is None:
                formats = ['csv']
            
            if filename_prefix is None:
                filename_prefix = f"malaysia_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Export simple en CSV
            files_created = []
            
            if buildings_data:
                buildings_df = pd.DataFrame(buildings_data)
                buildings_file = f"{filename_prefix}_buildings.csv"
                buildings_df.to_csv(buildings_file, index=False)
                files_created.append(buildings_file)
                logger.info(f"📁 Export buildings: {buildings_file}")
            
            if timeseries_data:
                timeseries_df = pd.DataFrame(timeseries_data)
                timeseries_file = f"{filename_prefix}_timeseries.csv"
                timeseries_df.to_csv(timeseries_file, index=False)
                files_created.append(timeseries_file)
                logger.info(f"📁 Export timeseries: {timeseries_file}")
            
            self.export_statistics['successful_exports'] += 1
            self.export_statistics['total_files_created'] += len(files_created)
            
            return {
                'success': True,
                'files_created': files_created,
                'total_files': len(files_created),
                'formats_used': formats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur export: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'files_created': []
            }
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques du service"""
        return self.export_statistics.copy()