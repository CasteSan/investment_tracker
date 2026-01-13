"""
Core Module - Logica de Negocio Pura

Este modulo contiene la logica de negocio sin dependencias de UI.
Aqui residen los calculos matematicos y algoritmos puros.

Submodulos:
- analytics/: Metricas de riesgo y rendimiento (Sharpe, Beta, etc.)
- portfolio/: Logica de gestion de cartera (futuro refactor)
- tax/: Calculos fiscales (futuro refactor)

Principio: El codigo en core/ NO debe importar nada de app/ ni api/

Uso:
    from src.core.analytics import calculate_sharpe_ratio, calculate_beta
"""

from src.core.analytics import (
    # Risk metrics
    calculate_volatility,
    calculate_var,
    calculate_cvar,
    calculate_beta,
    calculate_correlation,
    calculate_max_drawdown,
    # Performance metrics
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_alpha,
    calculate_information_ratio,
    calculate_cagr,
    calculate_cagr_from_prices,
    calculate_total_return,
)

from src.core.utils import smart_truncate
from src.core.profile_manager import ProfileManager, get_profile_manager

__all__ = [
    # Utils
    'smart_truncate',
    # Profile management
    'ProfileManager',
    'get_profile_manager',
    'calculate_volatility',
    'calculate_var',
    'calculate_cvar',
    'calculate_beta',
    'calculate_correlation',
    'calculate_max_drawdown',
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_alpha',
    'calculate_information_ratio',
    'calculate_cagr',
    'calculate_cagr_from_prices',
    'calculate_total_return',
]
