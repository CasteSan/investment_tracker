"""
Analytics Module - Metricas de Riesgo y Rendimiento

Este modulo contiene funciones puras para calculos financieros.
NO tiene dependencias de UI ni base de datos.

Submodulos:
- risk: Volatilidad, VaR, Beta, Correlacion
- performance: Sharpe Ratio, Sortino Ratio, Alpha, CAGR

Uso:
    from src.core.analytics import (
        calculate_volatility,
        calculate_sharpe_ratio,
        calculate_beta
    )

    # Con Series de retornos
    vol = calculate_volatility(returns_series)
    sharpe = calculate_sharpe_ratio(returns_series, risk_free_rate=0.02)
    beta = calculate_beta(returns_series, benchmark_returns)

Nota: Todas las funciones esperan Series/arrays de RETORNOS (no precios).
      Usa returns = prices.pct_change().dropna() para convertir.
"""

from src.core.analytics.risk import (
    calculate_volatility,
    calculate_var,
    calculate_cvar,
    calculate_beta,
    calculate_correlation,
    calculate_max_drawdown,
)

from src.core.analytics.performance import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_alpha,
    calculate_information_ratio,
    calculate_cagr,
    calculate_total_return,
)

__all__ = [
    # Risk metrics
    'calculate_volatility',
    'calculate_var',
    'calculate_cvar',
    'calculate_beta',
    'calculate_correlation',
    'calculate_max_drawdown',
    # Performance metrics
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_alpha',
    'calculate_information_ratio',
    'calculate_cagr',
    'calculate_total_return',
]
