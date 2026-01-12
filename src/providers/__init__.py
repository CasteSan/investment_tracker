"""
Providers Module - Proveedores de Datos Externos

Este módulo contendrá las abstracciones e implementaciones para
obtener datos de fuentes externas.

Estructura planificada:
- base.py: Interfaz IMarketDataProvider (Protocol)
- yahoo.py: YahooFinanceProvider (actual market_data.py)
- morningstar.py: MorningstarProvider (futuro, para fondos)
- alpha_vantage.py: AlphaVantageProvider (futuro, alternativa)

Patrón: Strategy + Adapter

Uso futuro:
    from src.providers import YahooFinanceProvider

    provider = YahooFinanceProvider()
    prices = provider.get_historical_prices("AAPL", start_date, end_date)
"""

__all__ = []
