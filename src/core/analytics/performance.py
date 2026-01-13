"""
Performance Metrics - Metricas de Rendimiento

Funciones puras para calcular metricas de rendimiento ajustado al riesgo.
No tienen dependencias externas excepto numpy/pandas.

Metricas implementadas:
- Sharpe Ratio (rendimiento ajustado por volatilidad)
- Sortino Ratio (rendimiento ajustado por riesgo a la baja)
- Alpha (exceso de retorno sobre el benchmark)
- Information Ratio (alpha ajustado por tracking error)
- CAGR (tasa de crecimiento anual compuesto)
- Total Return (retorno total del periodo)

Todas las funciones esperan Series de RETORNOS (no precios), excepto CAGR.
"""

import numpy as np
import pandas as pd
from typing import Union, Optional

from src.core.analytics.risk import (
    calculate_volatility,
    calculate_beta,
    calculate_downside_deviation,
    TRADING_DAYS_PER_YEAR,
)


def calculate_sharpe_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el Sharpe Ratio.

    Sharpe Ratio mide el exceso de retorno por unidad de riesgo.
    Es la metrica mas usada para comparar inversiones.

    Formula: (R_p - R_f) / σ_p

    Interpretacion:
    - > 1.0: Bueno
    - > 2.0: Muy bueno
    - > 3.0: Excelente
    - < 0: El activo rinde menos que la tasa libre de riesgo

    Args:
        returns: Serie de retornos del periodo
        risk_free_rate: Tasa libre de riesgo ANUALIZADA (ej: 0.02 = 2%)
        periods_per_year: Periodos por año (252 diario, 12 mensual)

    Returns:
        Sharpe Ratio anualizado

    Example:
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
    """
    if len(returns) < 10:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return 0.0

    # Retorno medio anualizado
    mean_return = np.mean(returns) * periods_per_year

    # Volatilidad anualizada
    volatility = calculate_volatility(returns, annualize=True, periods_per_year=periods_per_year)

    if volatility == 0:
        return 0.0

    # Sharpe = (Retorno - Tasa libre) / Volatilidad
    sharpe = (mean_return - risk_free_rate) / volatility

    return float(sharpe)


def calculate_sortino_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    target_return: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el Sortino Ratio.

    Similar al Sharpe pero solo penaliza la volatilidad negativa.
    Mejor para inversores que no les importa la volatilidad al alza.

    Formula: (R_p - R_f) / σ_downside

    Args:
        returns: Serie de retornos
        risk_free_rate: Tasa libre de riesgo ANUALIZADA
        target_return: Retorno objetivo para calcular downside
        periods_per_year: Periodos por año

    Returns:
        Sortino Ratio anualizado

    Example:
        >>> sortino = calculate_sortino_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sortino Ratio: {sortino:.2f}")
    """
    if len(returns) < 10:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return 0.0

    # Retorno medio anualizado
    mean_return = np.mean(returns) * periods_per_year

    # Downside deviation anualizada
    downside_dev = calculate_downside_deviation(
        returns,
        target_return=target_return / periods_per_year,  # Convertir a periodo
        annualize=True,
        periods_per_year=periods_per_year
    )

    if downside_dev == 0:
        return 0.0 if mean_return <= risk_free_rate else float('inf')

    # Sortino = (Retorno - Tasa libre) / Downside Deviation
    sortino = (mean_return - risk_free_rate) / downside_dev

    return float(sortino)


def calculate_alpha(
    returns: Union[pd.Series, np.ndarray],
    benchmark_returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el Alpha (Jensen's Alpha).

    Alpha mide el exceso de retorno sobre lo esperado dado el riesgo (beta).
    - Alpha > 0: La cartera supera al benchmark ajustado por riesgo
    - Alpha < 0: La cartera no compensa el riesgo asumido

    Formula: α = R_p - [R_f + β × (R_m - R_f)]

    Args:
        returns: Serie de retornos de la cartera
        benchmark_returns: Serie de retornos del benchmark
        risk_free_rate: Tasa libre de riesgo ANUALIZADA
        periods_per_year: Periodos por año

    Returns:
        Alpha anualizado como decimal (ej: 0.05 = 5% alpha)

    Example:
        >>> alpha = calculate_alpha(portfolio_returns, sp500_returns)
        >>> print(f"Alpha: {alpha:.2%}")
    """
    if len(returns) < 10 or len(benchmark_returns) < 10:
        return 0.0

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
        return 0.0

    # Calcular beta
    beta = calculate_beta(returns, benchmark_returns)

    # Retornos medios anualizados
    portfolio_return = np.mean(returns) * periods_per_year
    benchmark_return = np.mean(benchmark_returns) * periods_per_year

    # Alpha = Retorno cartera - Retorno esperado segun CAPM
    expected_return = risk_free_rate + beta * (benchmark_return - risk_free_rate)
    alpha = portfolio_return - expected_return

    return float(alpha)


def calculate_information_ratio(
    returns: Union[pd.Series, np.ndarray],
    benchmark_returns: Union[pd.Series, np.ndarray],
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el Information Ratio.

    Mide el alpha por unidad de tracking error.
    Util para evaluar gestores activos vs su benchmark.

    Formula: IR = (R_p - R_b) / σ(R_p - R_b)

    Interpretacion:
    - > 0.5: Bueno
    - > 1.0: Muy bueno

    Args:
        returns: Serie de retornos de la cartera
        benchmark_returns: Serie de retornos del benchmark
        periods_per_year: Periodos por año

    Returns:
        Information Ratio anualizado

    Example:
        >>> ir = calculate_information_ratio(portfolio_returns, benchmark_returns)
        >>> print(f"Information Ratio: {ir:.2f}")
    """
    if len(returns) < 10 or len(benchmark_returns) < 10:
        return 0.0

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
        return 0.0

    # Exceso de retorno (active return)
    active_return = returns - benchmark_returns

    # Tracking error (volatilidad del exceso de retorno)
    tracking_error = np.std(active_return, ddof=1) * np.sqrt(periods_per_year)

    if tracking_error == 0:
        return 0.0

    # Exceso de retorno medio anualizado
    mean_active_return = np.mean(active_return) * periods_per_year

    return float(mean_active_return / tracking_error)


def calculate_cagr(
    start_value: float,
    end_value: float,
    years: float
) -> float:
    """
    Calcula el CAGR (Compound Annual Growth Rate).

    CAGR es la tasa de crecimiento anual constante que habria
    producido el mismo resultado final.

    Formula: CAGR = (V_final / V_inicial)^(1/n) - 1

    Args:
        start_value: Valor inicial
        end_value: Valor final
        years: Numero de años (puede ser decimal)

    Returns:
        CAGR como decimal (ej: 0.10 = 10% anual)

    Example:
        >>> cagr = calculate_cagr(10000, 15000, 3)
        >>> print(f"CAGR: {cagr:.2%}")  # ~14.5%
    """
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return 0.0

    return float((end_value / start_value) ** (1 / years) - 1)


def calculate_cagr_from_prices(
    prices: Union[pd.Series, np.ndarray],
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el CAGR desde una serie de precios.

    Args:
        prices: Serie de precios o valores de cartera
        periods_per_year: Periodos por año

    Returns:
        CAGR como decimal
    """
    if len(prices) < 2:
        return 0.0

    prices = np.asarray(prices)
    prices = prices[~np.isnan(prices)]

    if len(prices) < 2:
        return 0.0

    start_value = prices[0]
    end_value = prices[-1]
    years = len(prices) / periods_per_year

    return calculate_cagr(start_value, end_value, years)


def calculate_total_return(
    returns: Union[pd.Series, np.ndarray]
) -> float:
    """
    Calcula el retorno total acumulado.

    Formula: (1 + r1) × (1 + r2) × ... × (1 + rn) - 1

    Args:
        returns: Serie de retornos

    Returns:
        Retorno total como decimal (ej: 0.50 = 50%)

    Example:
        >>> total = calculate_total_return(returns)
        >>> print(f"Retorno total: {total:.2%}")
    """
    if len(returns) < 1:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 1:
        return 0.0

    # Retorno acumulado
    cumulative = np.prod(1 + returns) - 1

    return float(cumulative)


def calculate_annualized_return(
    returns: Union[pd.Series, np.ndarray],
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el retorno anualizado.

    Args:
        returns: Serie de retornos
        periods_per_year: Periodos por año

    Returns:
        Retorno anualizado como decimal
    """
    if len(returns) < 1:
        return 0.0

    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    total_return = calculate_total_return(returns)
    years = len(returns) / periods_per_year

    if years <= 0:
        return 0.0

    # Anualizar
    annualized = (1 + total_return) ** (1 / years) - 1

    return float(annualized)


def calculate_calmar_ratio(
    returns: Union[pd.Series, np.ndarray],
    prices: Union[pd.Series, np.ndarray],
    periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calcula el Calmar Ratio.

    Mide el retorno anualizado dividido por el max drawdown.
    Util para estrategias de trading.

    Formula: Calmar = CAGR / Max Drawdown

    Args:
        returns: Serie de retornos (para calcular CAGR)
        prices: Serie de precios (para calcular Max DD)
        periods_per_year: Periodos por año

    Returns:
        Calmar Ratio
    """
    from src.core.analytics.risk import calculate_max_drawdown

    annualized_return = calculate_annualized_return(returns, periods_per_year)
    max_dd = calculate_max_drawdown(prices)

    if max_dd == 0:
        return 0.0

    return float(annualized_return / max_dd)
