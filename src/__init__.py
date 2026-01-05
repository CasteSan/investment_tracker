"""
Investment Tracker - Módulos Core
=================================

Módulos disponibles:
- database: Gestión de base de datos SQLite
- portfolio: Análisis de cartera y rentabilidades
- data_loader: Importación/exportación de datos
- transactions: Lógica de transacciones
- tax_calculator: Cálculos fiscales
- dividends: Gestión de dividendos
- benchmarks: Comparación con índices
"""

from pathlib import Path

# Versión del proyecto
__version__ = '0.3.0'

# Ruta base del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
