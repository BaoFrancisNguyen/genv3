"""
Exportateur de données - Export des datasets générés
==================================================

Module simple pour l'export des données en différents formats.
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List
import os

# Configuration du logger
logger = logging.getLogger(__name__)


class DataExporter:
    """Exportateur simple de données"""
    
    def __init__(self):
        """Initialise l'exportateur"""
        self.export_stats = {
            'total_exports': 0,
            'files_created': 0,
            'start_time': datetime.now()
        }
        
        logger.info("✅ Exportateur de données initialisé")
    
    def export_to_csv(self, data: List[Dict], filename: str) -> str:
        """Exporte des données en CSV"""
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.export_stats['files_created'] += 1
            logger.info(f"📁 Export CSV: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Erreur export CSV: {str(e)}")
            raise
    
    def get_export_statistics(self) -> Dict:
        """Retourne les statistiques d'export"""
        return self.export_stats.copy()