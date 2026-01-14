"""
Providers Module - Proveedores de Datos Externos

Este módulo contiene las abstracciones e implementaciones para
obtener datos de fuentes externas.

Estructura:
- morningstar.py: FundDataProvider (datos de fondos via mstarpy)
- base.py: Interfaz IMarketDataProvider (Protocol) - futuro
- yahoo.py: YahooFinanceProvider (actual market_data.py) - futuro

Patrón: Strategy + Adapter

Uso:
    from src.providers import FundDataProvider

    provider = FundDataProvider()
    data = provider.get_fund_data('IE00B3RBWM25')
"""

from src.providers.morningstar import (
    FundDataProvider,
    FundDataProviderError,
    FundNotFoundError,
    get_fund_provider,
)

__all__ = [
    'FundDataProvider',
    'FundDataProviderError',
    'FundNotFoundError',
    'get_fund_provider',
]
