"""
Archivo de compatibilidad para database.py

Este archivo mantiene la retrocompatibilidad con los imports existentes
mientras la base de datos real se encuentra en src/data/database.py

DEPRECATION WARNING:
    Este archivo existe solo por compatibilidad. En futuras versiones,
    actualiza tus imports a:
        from src.data.database import Database, Transaction, Dividend, ...

    O usa el __init__.py de src.data:
        from src.data import Database

Cambio realizado en: Sesion 1 - Refactor Escalabilidad
"""

# Re-exportar todo desde la nueva ubicación
from src.data.database import (
    # Clase principal
    Database,

    # Modelos SQLAlchemy
    Base,
    Transaction,
    Dividend,
    BenchmarkData,
    PortfolioSnapshot,
    AssetPrice,

    # Constantes
    DEFAULT_DB_PATH,
)

# Hacer disponibles en el namespace del módulo
__all__ = [
    'Database',
    'Base',
    'Transaction',
    'Dividend',
    'BenchmarkData',
    'PortfolioSnapshot',
    'AssetPrice',
    'DEFAULT_DB_PATH',
]
