"""
Modulo de Datos (Data Layer)

Este modulo contiene todo lo relacionado con la persistencia de datos:
- Modelos SQLAlchemy (Transaction, Dividend, Fund, Portfolio, etc.)
- Clase Database para acceso a datos
- Repositorios (FundRepository, etc.)
- Migraciones

Cloud Migration - Fase 2:
- Añadido modelo Portfolio para multi-tenant
- Transaction y Dividend ahora tienen portfolio_id

Uso:
    from src.data import Database, Transaction, Dividend, Fund, Portfolio
    from src.data.repositories import FundRepository

    db = Database()
    transactions = db.get_transactions()

    # Usar repositorio de fondos
    repo = FundRepository(db.session)
    funds = repo.find_by_category('Renta Variable')

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

from src.data.models import (
    Portfolio,
    Fund,
    FUND_CATEGORIES,
    FUND_REGIONS,
    FUND_RISK_LEVELS,
    DISTRIBUTION_POLICIES,
)

__all__ = [
    # Database
    'Database',
    'Base',
    'DEFAULT_DB_PATH',
    # Modelos existentes
    'Transaction',
    'Dividend',
    'BenchmarkData',
    'PortfolioSnapshot',
    'AssetPrice',
    # Portfolio (Cloud multi-tenant)
    'Portfolio',
    # Modelo de fondos
    'Fund',
    'FUND_CATEGORIES',
    'FUND_REGIONS',
    'FUND_RISK_LEVELS',
    'DISTRIBUTION_POLICIES',
]
