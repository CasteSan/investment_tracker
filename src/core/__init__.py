"""
Core Module - Logica de Negocio Pura

Este modulo contiene la logica de negocio sin dependencias de UI.
Aqui residen los calculos matematicos y algoritmos puros.

Submodulos:
- analytics/: Metricas de riesgo y rendimiento (Sharpe, Beta, etc.)
- environment: Deteccion de entorno (local vs cloud)
- profile_manager: Gestion de perfiles/carteras (Local y Cloud)

Principio: El codigo en core/ NO debe importar nada de app/ ni api/

Uso:
    from src.core.analytics import calculate_sharpe_ratio, calculate_beta
    from src.core.environment import is_cloud_environment
    from src.core.profile_manager import get_profile_manager
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

# Environment detection
from src.core.environment import (
    is_cloud_environment,
    is_local_environment,
    get_environment,
    get_database_url,
)

# Profile management (Hybrid: Local + Cloud)
from src.core.profile_manager import (
    ProfileManager,
    LocalProfileManager,
    ProfileManagerProtocol,
    get_profile_manager,
)
from src.core.cloud_profile_manager import CloudProfileManager

__all__ = [
    # Utils
    'smart_truncate',
    # Environment detection
    'is_cloud_environment',
    'is_local_environment',
    'get_environment',
    'get_database_url',
    # Profile management
    'ProfileManager',
    'LocalProfileManager',
    'CloudProfileManager',
    'ProfileManagerProtocol',
    'get_profile_manager',
    # Analytics - Risk
    'calculate_volatility',
    'calculate_var',
    'calculate_cvar',
    'calculate_beta',
    'calculate_correlation',
    'calculate_max_drawdown',
    # Analytics - Performance
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_alpha',
    'calculate_information_ratio',
    'calculate_cagr',
    'calculate_cagr_from_prices',
    'calculate_total_return',
]
