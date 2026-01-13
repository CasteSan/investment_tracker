"""
Risk Metrics - Metricas de Riesgo

Funciones puras para calcular metricas de riesgo de carteras.
No tienen dependencias externas excepto numpy/pandas.

Metricas implementadas:
- Volatilidad (desviacion estandar anualizada)
- VaR (Value at Risk)
- CVaR / Expected Shortfall
- Beta (sensibilidad al mercado)
- Correlacion
- Max Drawdown

Todas las funciones esperan Series de RETORNOS (no precios).
"""

import numpy as np
import pandas as pd
from typing import Union, Optional

# Constantes
TRADING_DAYS_PER_YEAR = 252
MONTHS_PER_YEAR = 12


def calculate_volatility(
    returns: Union[pd.Series, np.ndarray],
    annualize: bool = True,
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula la volatilidad (desviacion estandar) de los retornos.

    La volatilidad mide la dispersion de los retornos respecto a su media.
    Una volatilidad alta indica mayor riesgo/incertidumbre.

    Args:
        returns: Serie de retornos (decimales, ej: 0.05 = 5%)
        annualize: Si anualizar el resultado (default True)
        periods_per_year: Periodos por año (252 para diario, 12 para mensual)

    Returns:
        Volatilidad como decimal (ej: 0.20 = 20% anual)

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
        >>> vol = calculate_volatility(returns)
        >>> print(f"Volatilidad anual: {vol:.2%}")
    """
    if len(returns) < 2:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return 0.0

    std = np.std(returns, ddof=1)  # ddof=1 para muestra

    if annualize:
        return float(std * np.sqrt(periods_per_year))
    return float(std)


def calculate_var(
    returns: Union[pd.Series, np.ndarray],
    confidence_level: float = 0.95,
    method: str = 'historical'
) -> float:
    """
    Calcula el Value at Risk (VaR).

    VaR responde: "Con X% de confianza, la perdida maxima esperada
    en un periodo es Y%".

    Args:
        returns: Serie de retornos
        confidence_level: Nivel de confianza (0.95 = 95%)
        method: Metodo de calculo:
                - 'historical': Percentil historico (no asume distribucion)
                - 'parametric': Asume distribucion normal

    Returns:
        VaR como decimal positivo (perdida maxima esperada)
        Ej: 0.05 significa "perdida maxima esperada del 5%"

    Example:
        >>> var_95 = calculate_var(returns, confidence_level=0.95)
        >>> print(f"VaR 95%: {var_95:.2%}")  # Perdida maxima con 95% confianza
    """
    if len(returns) < 10:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if method == 'historical':
        # Percentil historico
        var = np.percentile(returns, (1 - confidence_level) * 100)
    elif method == 'parametric':
        # Asume distribucion normal
        from scipy import stats
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        var = stats.norm.ppf(1 - confidence_level, mu, sigma)
    else:
        raise ValueError(f"Metodo no soportado: {method}")

    # Retornamos valor absoluto (VaR es una perdida)
    return float(abs(min(var, 0)))


def calculate_cvar(
    returns: Union[pd.Series, np.ndarray],
    confidence_level: float = 0.95
) -> float:
    """
    Calcula el Conditional VaR (CVaR) o Expected Shortfall.

    CVaR es la perdida esperada cuando se supera el VaR.
    Es mas conservador que VaR porque considera la cola de la distribucion.

    Args:
        returns: Serie de retornos
        confidence_level: Nivel de confianza (0.95 = 95%)

    Returns:
        CVaR como decimal positivo

    Example:
        >>> cvar = calculate_cvar(returns, confidence_level=0.95)
        >>> print(f"CVaR 95%: {cvar:.2%}")
    """
    if len(returns) < 10:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    var_threshold = np.percentile(returns, (1 - confidence_level) * 100)
    tail_losses = returns[returns <= var_threshold]

    if len(tail_losses) == 0:
        return 0.0

    return float(abs(np.mean(tail_losses)))


def calculate_beta(
    returns: Union[pd.Series, np.ndarray],
    benchmark_returns: Union[pd.Series, np.ndarray]
) -> float:
    """
    Calcula el Beta respecto a un benchmark.

    Beta mide la sensibilidad de los retornos respecto al mercado:
    - Beta = 1: Se mueve igual que el mercado
    - Beta > 1: Mas volatil que el mercado (amplifica movimientos)
    - Beta < 1: Menos volatil que el mercado (amortigua movimientos)
    - Beta < 0: Se mueve en direccion opuesta (raro)

    Formula: Beta = Cov(R_asset, R_benchmark) / Var(R_benchmark)

    Args:
        returns: Serie de retornos del activo/cartera
        benchmark_returns: Serie de retornos del benchmark (ej: S&P500)

    Returns:
        Beta como float

    Example:
        >>> beta = calculate_beta(portfolio_returns, sp500_returns)
        >>> print(f"Beta: {beta:.2f}")
    """
    if len(returns) < 10 or len(benchmark_returns) < 10:
        return 1.0  # Default neutral

    returns = np.asarray(returns)
    benchmark_returns = np.asarray(benchmark_returns)

    # Alinear longitudes
    min_len = min(len(returns), len(benchmark_returns))
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]

    # Eliminar NaN
    mask = ~(np.isnan(returns) | np.isnan(benchmark_returns))
    returns = returns[mask]
    benchmark_returns = benchmark_returns[mask]

    if len(returns) < 10:
        return 1.0

    covariance = np.cov(returns, benchmark_returns)[0, 1]
    benchmark_variance = np.var(benchmark_returns, ddof=1)

    if benchmark_variance == 0:
        return 1.0

    return float(covariance / benchmark_variance)


def calculate_correlation(
    returns1: Union[pd.Series, np.ndarray],
    returns2: Union[pd.Series, np.ndarray]
) -> float:
    """
    Calcula la correlacion de Pearson entre dos series de retornos.

    Correlacion mide la relacion lineal entre dos activos:
    - +1: Perfectamente correlacionados (se mueven juntos)
    - 0: Sin correlacion
    - -1: Perfectamente anticorrelacionados (se mueven opuestos)

    Args:
        returns1: Primera serie de retornos
        returns2: Segunda serie de retornos

    Returns:
        Correlacion entre -1 y 1

    Example:
        >>> corr = calculate_correlation(stock_a_returns, stock_b_returns)
        >>> print(f"Correlacion: {corr:.2f}")
    """
    if len(returns1) < 3 or len(returns2) < 3:
        return 0.0

    returns1 = np.asarray(returns1)
    returns2 = np.asarray(returns2)

    # Alinear longitudes
    min_len = min(len(returns1), len(returns2))
    returns1 = returns1[-min_len:]
    returns2 = returns2[-min_len:]

    # Eliminar NaN
    mask = ~(np.isnan(returns1) | np.isnan(returns2))
    returns1 = returns1[mask]
    returns2 = returns2[mask]

    if len(returns1) < 3:
        return 0.0

    correlation_matrix = np.corrcoef(returns1, returns2)
    return float(correlation_matrix[0, 1])


def calculate_max_drawdown(
    prices: Union[pd.Series, np.ndarray]
) -> float:
    """
    Calcula el Maximum Drawdown (MDD).

    MDD es la maxima caida desde un pico hasta un valle.
    Mide el peor escenario historico que habria sufrido un inversor.

    NOTA: Esta funcion espera PRECIOS, no retornos.

    Args:
        prices: Serie de precios (o valores de cartera)

    Returns:
        Max Drawdown como decimal positivo (ej: 0.25 = -25%)

    Example:
        >>> mdd = calculate_max_drawdown(portfolio_values)
        >>> print(f"Max Drawdown: {mdd:.2%}")
    """
    if len(prices) < 2:
        return 0.0

    prices = np.asarray(prices)
    prices = prices[~np.isnan(prices)]

    if len(prices) < 2:
        return 0.0

    # Calcular picos acumulados
    peak = np.maximum.accumulate(prices)

    # Calcular drawdown en cada punto
    drawdown = (prices - peak) / peak

    # Maximo drawdown (valor mas negativo)
    max_dd = np.min(drawdown)

    return float(abs(max_dd))


def calculate_downside_deviation(
    returns: Union[pd.Series, np.ndarray],
    target_return: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula la desviacion a la baja (Downside Deviation).

    Solo considera retornos por debajo del objetivo.
    Es la base para calcular el Sortino Ratio.

    Args:
        returns: Serie de retornos
        target_return: Retorno objetivo (default 0)
        annualize: Si anualizar el resultado
        periods_per_year: Periodos por año

    Returns:
        Downside deviation como decimal
    """
    if len(returns) < 2:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    # Solo retornos por debajo del objetivo
    downside_returns = returns[returns < target_return]

    if len(downside_returns) < 2:
        return 0.0

    # Desviacion de los retornos negativos respecto al objetivo
    downside_diff = downside_returns - target_return
    downside_std = np.sqrt(np.mean(downside_diff ** 2))

    if annualize:
        return float(downside_std * np.sqrt(periods_per_year))
    return float(downside_std)
