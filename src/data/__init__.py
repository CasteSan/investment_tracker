"""
Módulo de Datos (Data Layer)

Este módulo contiene todo lo relacionado con la persistencia de datos:
- Modelos SQLAlchemy
- Clase Database para acceso a datos
- Repositorios (futuro)
- Migraciones (futuro)

Uso:
    from src.data import Database, Transaction, Dividend

    db = Database()
    transactions = db.get_transactions()
    db.close()
"""

from src.data.database import (
    Database,
    Base,
    Transaction,
    Dividend,
    BenchmarkData,
    PortfolioSnapshot,
    AssetPrice,
    DEFAULT_DB_PATH,
)

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
