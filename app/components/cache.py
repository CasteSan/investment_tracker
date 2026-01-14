"""
Funciones cacheadas para mejorar rendimiento en Streamlit Cloud.

Este modulo centraliza las funciones con @st.cache_data para evitar
consultas repetidas a la base de datos PostgreSQL remota.

TTL (Time To Live) recomendados:
- Datos que cambian poco (posiciones, metricas): 60-120 segundos
- Datos estaticos (categorias, tickers): 300 segundos
- Datos volatiles (precios): 30-60 segundos

Uso:
    from app.components.cache import get_cached_dashboard_data

    data = get_cached_dashboard_data(db_path, fiscal_year, fiscal_method)
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime


# =============================================================================
# CACHE PARA DASHBOARD Y METRICAS
# =============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_dashboard_data(
    db_path: str,
    fiscal_year: int,
    fiscal_method: str = 'FIFO'
) -> Dict[str, Any]:
    """
    Obtiene datos del dashboard con cache de 60 segundos.
    """
    from src.services.portfolio_service import PortfolioService

    with PortfolioService(db_path=db_path) as service:
        return service.get_dashboard_data(
            fiscal_year=fiscal_year,
            fiscal_method=fiscal_method
        )


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_positions(db_path: str) -> Dict[str, Any]:
    """
    Obtiene posiciones actuales con cache.
    """
    from src.services.portfolio_service import PortfolioService

    with PortfolioService(db_path=db_path) as service:
        if not service.has_positions():
            return {'positions': None, 'has_positions': False}

        data = service.get_dashboard_data(
            fiscal_year=datetime.now().year,
            fiscal_method='FIFO'
        )
        return {
            'positions': data['positions'],
            'metrics': data['metrics'],
            'has_positions': True
        }


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_portfolio_metrics(
    db_path: str,
    start_date: Optional[str] = None,
    benchmark_name: str = 'SP500',
    risk_free_rate: float = 0.02
) -> Dict[str, Any]:
    """
    Obtiene metricas avanzadas (Sharpe, Beta, etc.) con cache de 2 minutos.
    """
    from src.services.portfolio_service import PortfolioService

    with PortfolioService(db_path=db_path) as service:
        return service.get_portfolio_metrics(
            start_date=start_date,
            benchmark_name=benchmark_name,
            risk_free_rate=risk_free_rate
        )


# =============================================================================
# CACHE PARA DATOS ESTATICOS
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_tickers(db_path: str) -> List[str]:
    """
    Obtiene lista de tickers con cache de 5 minutos.
    """
    from src.data import Database

    db = Database(db_path=db_path)
    tickers = db.get_all_tickers()
    db.close()
    return tickers


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_currencies(db_path: str) -> List[str]:
    """
    Obtiene lista de divisas usadas con cache de 5 minutos.
    """
    from src.data import Database

    db = Database(db_path=db_path)
    currencies = db.get_currencies_used()
    db.close()
    return currencies


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_database_stats(db_path: str) -> Dict[str, Any]:
    """
    Obtiene estadisticas de la BD con cache de 5 minutos.
    """
    from src.data import Database

    db = Database(db_path=db_path)
    stats = db.get_database_stats()
    db.close()
    return stats


# =============================================================================
# CACHE PARA FISCAL Y DIVIDENDOS
# =============================================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_cached_fiscal_summary(
    db_path: str,
    fiscal_year: int,
    fiscal_method: str = 'FIFO'
) -> Dict[str, Any]:
    """
    Obtiene resumen fiscal con cache de 2 minutos.
    """
    from src.tax_calculator import TaxCalculator

    tax = TaxCalculator(method=fiscal_method, db_path=db_path)
    summary = tax.get_fiscal_year_summary(fiscal_year)
    tax.close()
    return summary


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_dividend_totals(
    db_path: str,
    year: int
) -> Dict[str, Any]:
    """
    Obtiene totales de dividendos con cache de 2 minutos.
    """
    from src.dividends import DividendManager

    dm = DividendManager(db_path=db_path)
    totals = dm.get_total_dividends(year=year)
    dm.close()
    return totals


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_dividends_by_ticker(
    db_path: str,
    year: int,
    ticker: Optional[str] = None
) -> List[Dict]:
    """
    Obtiene dividendos filtrados con cache.
    """
    from src.dividends import DividendManager

    dm = DividendManager(db_path=db_path)
    dividends = dm.get_dividends(year=year, ticker=ticker if ticker != "Todos" else None)
    dm.close()
    return dividends


# =============================================================================
# CACHE PARA TRANSACCIONES (solo lectura)
# =============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_transactions(
    db_path: str,
    ticker: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Obtiene transacciones con cache de 1 minuto.
    """
    from src.data import Database

    db = Database(db_path=db_path)
    transactions = db.get_all_transactions()
    db.close()

    # Filtrar si es necesario
    if ticker:
        transactions = [t for t in transactions if t.get('ticker') == ticker]
    if transaction_type:
        transactions = [t for t in transactions if t.get('type') == transaction_type]

    return transactions[:limit]


# =============================================================================
# FUNCIONES PARA INVALIDAR CACHE
# =============================================================================

def invalidate_dashboard_cache():
    """Invalida cache del dashboard cuando hay cambios."""
    get_cached_dashboard_data.clear()
    get_cached_positions.clear()
    get_cached_portfolio_metrics.clear()


def invalidate_transaction_cache():
    """Invalida cache de transacciones cuando hay cambios."""
    get_cached_transactions.clear()
    get_cached_tickers.clear()
    invalidate_dashboard_cache()


def invalidate_dividend_cache():
    """Invalida cache de dividendos cuando hay cambios."""
    get_cached_dividend_totals.clear()
    get_cached_dividends_by_ticker.clear()


def invalidate_all_cache():
    """Invalida toda la cache (usar con cuidado)."""
    invalidate_dashboard_cache()
    invalidate_transaction_cache()
    invalidate_dividend_cache()
    get_cached_currencies.clear()
    get_cached_database_stats.clear()
