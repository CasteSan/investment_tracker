"""
Tests Unitarios para el Modulo Analytics

Estos tests verifican los calculos matematicos de riesgo y rendimiento
usando valores conocidos y casos edge.

Ejecutar:
    pytest tests/unit/test_analytics.py -v
"""

import pytest
import numpy as np
import pandas as pd


class TestVolatility:
    """Tests para calculate_volatility()."""

    def test_volatility_constant_returns(self):
        """Retornos constantes tienen volatilidad cero."""
        from src.core.analytics import calculate_volatility

        returns = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
        vol = calculate_volatility(returns, annualize=False)
        assert vol == 0.0

    def test_volatility_known_value(self):
        """Verifica calculo con valor conocido."""
        from src.core.analytics import calculate_volatility

        # Crear retornos con std conocida
        returns = np.array([0.10, -0.05, 0.08, -0.03, 0.05])
        vol = calculate_volatility(returns, annualize=False)

        # std manual
        expected = np.std(returns, ddof=1)
        assert abs(vol - expected) < 0.0001

    def test_volatility_annualized(self):
        """Verifica anualizacion correcta."""
        from src.core.analytics import calculate_volatility

        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02] * 50)  # 250 dias
        vol_daily = calculate_volatility(returns, annualize=False)
        vol_annual = calculate_volatility(returns, annualize=True, periods_per_year=252)

        # Anualizado = diario * sqrt(252)
        assert abs(vol_annual - vol_daily * np.sqrt(252)) < 0.0001

    def test_volatility_empty(self):
        """Array vacio devuelve cero."""
        from src.core.analytics import calculate_volatility

        vol = calculate_volatility(np.array([]))
        assert vol == 0.0

    def test_volatility_single_value(self):
        """Un solo valor devuelve cero."""
        from src.core.analytics import calculate_volatility

        vol = calculate_volatility(np.array([0.05]))
        assert vol == 0.0


class TestVaR:
    """Tests para calculate_var()."""

    def test_var_95_known(self):
        """VaR 95% con valores conocidos."""
        from src.core.analytics import calculate_var

        # Crear retornos con perdidas claras en el 5% inferior
        # 100 retornos donde el peor 5% tiene perdidas de -15%
        returns = np.concatenate([
            np.array([-0.15] * 6),   # 6% peores = -15%
            np.array([0.02] * 94)    # 94% restante = ganancias
        ])

        var_95 = calculate_var(returns, confidence_level=0.95)
        # El percentil 5 debe incluir las perdidas de -15%
        # VaR devuelve valor absoluto de la perdida
        assert var_95 >= 0.10  # Esperamos al menos 10% de VaR

    def test_var_positive_returns(self):
        """Retornos todos positivos dan VaR cercano a cero."""
        from src.core.analytics import calculate_var

        returns = np.random.uniform(0.01, 0.05, 100)
        var = calculate_var(returns, confidence_level=0.95)
        # VaR deberia ser muy pequeño o cero
        assert var < 0.05

    def test_var_insufficient_data(self):
        """Pocos datos devuelve cero."""
        from src.core.analytics import calculate_var

        returns = np.array([0.01, -0.02, 0.03])
        var = calculate_var(returns)
        assert var == 0.0


class TestBeta:
    """Tests para calculate_beta()."""

    def test_beta_identical_returns(self):
        """Retornos identicos dan beta = 1."""
        from src.core.analytics import calculate_beta

        returns = np.random.randn(100) * 0.02
        beta = calculate_beta(returns, returns)
        assert abs(beta - 1.0) < 0.001

    def test_beta_double_returns(self):
        """Retornos dobles dan beta = 2."""
        from src.core.analytics import calculate_beta

        benchmark = np.random.randn(100) * 0.02
        asset = benchmark * 2  # Doble sensibilidad
        beta = calculate_beta(asset, benchmark)
        assert abs(beta - 2.0) < 0.1

    def test_beta_inverse_returns(self):
        """Retornos inversos dan beta negativo."""
        from src.core.analytics import calculate_beta

        benchmark = np.random.randn(100) * 0.02
        asset = -benchmark  # Inverso
        beta = calculate_beta(asset, benchmark)
        assert beta < 0

    def test_beta_uncorrelated(self):
        """Retornos sin correlacion dan beta cercano a 0."""
        from src.core.analytics import calculate_beta

        np.random.seed(42)
        benchmark = np.random.randn(1000) * 0.02
        asset = np.random.randn(1000) * 0.02  # Independiente
        beta = calculate_beta(asset, benchmark)
        assert abs(beta) < 0.2  # Deberia estar cerca de 0


class TestCorrelation:
    """Tests para calculate_correlation()."""

    def test_correlation_identical(self):
        """Series identicas tienen correlacion 1."""
        from src.core.analytics import calculate_correlation

        returns = np.random.randn(100)
        corr = calculate_correlation(returns, returns)
        assert abs(corr - 1.0) < 0.001

    def test_correlation_inverse(self):
        """Series inversas tienen correlacion -1."""
        from src.core.analytics import calculate_correlation

        returns = np.random.randn(100)
        corr = calculate_correlation(returns, -returns)
        assert abs(corr - (-1.0)) < 0.001

    def test_correlation_range(self):
        """Correlacion esta entre -1 y 1."""
        from src.core.analytics import calculate_correlation

        np.random.seed(42)
        returns1 = np.random.randn(100)
        returns2 = np.random.randn(100)
        corr = calculate_correlation(returns1, returns2)
        assert -1 <= corr <= 1


class TestMaxDrawdown:
    """Tests para calculate_max_drawdown()."""

    def test_max_drawdown_known(self):
        """MDD conocido: 100 -> 50 = -50%."""
        from src.core.analytics import calculate_max_drawdown

        # Empieza en 100, baja a 50, sube a 80
        prices = np.array([100, 90, 80, 70, 60, 50, 60, 70, 80])
        mdd = calculate_max_drawdown(prices)
        assert abs(mdd - 0.50) < 0.001

    def test_max_drawdown_monotonic_up(self):
        """Precios siempre subiendo tienen MDD = 0."""
        from src.core.analytics import calculate_max_drawdown

        prices = np.array([100, 110, 120, 130, 140, 150])
        mdd = calculate_max_drawdown(prices)
        assert mdd == 0.0

    def test_max_drawdown_monotonic_down(self):
        """Precios siempre bajando tienen MDD = caida total."""
        from src.core.analytics import calculate_max_drawdown

        prices = np.array([100, 90, 80, 70, 60, 50])
        mdd = calculate_max_drawdown(prices)
        assert abs(mdd - 0.50) < 0.001  # 100 -> 50 = -50%


class TestSharpeRatio:
    """Tests para calculate_sharpe_ratio()."""

    def test_sharpe_positive(self):
        """Retornos positivos constantes dan Sharpe positivo."""
        from src.core.analytics import calculate_sharpe_ratio

        # Retornos diarios de ~10% anual
        returns = np.array([0.0004] * 252)  # ~10% anual
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert sharpe > 0

    def test_sharpe_requires_variance(self):
        """Retornos casi constantes producen Sharpe extremo o cero."""
        from src.core.analytics import calculate_sharpe_ratio

        # Con retornos casi identicos, la volatilidad es casi cero
        # Por lo que Sharpe puede ser muy alto o la funcion devuelve 0
        returns = np.array([0.001] * 100)
        sharpe = calculate_sharpe_ratio(returns)
        # Puede ser 0 (si vol=0) o muy alto (si vol muy pequeño)
        assert sharpe == 0.0 or sharpe > 100

    def test_sharpe_negative(self):
        """Retornos muy negativos dan Sharpe negativo."""
        from src.core.analytics import calculate_sharpe_ratio

        # Retornos claramente negativos: media de -5% anual
        np.random.seed(123)
        returns = np.random.normal(-0.0002, 0.01, 252)  # ~-5% anual
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert sharpe < 0


class TestSortinoRatio:
    """Tests para calculate_sortino_ratio()."""

    def test_sortino_no_downside(self):
        """Sin retornos negativos, Sortino es inf o muy alto."""
        from src.core.analytics import calculate_sortino_ratio

        returns = np.abs(np.random.randn(100)) * 0.01  # Solo positivos
        sortino = calculate_sortino_ratio(returns)
        # Con downside_dev = 0, deberia ser inf o muy alto
        assert sortino == float('inf') or sortino > 10

    def test_sortino_vs_sharpe(self):
        """Sortino >= Sharpe cuando hay mas volatilidad al alza."""
        from src.core.analytics import (
            calculate_sharpe_ratio,
            calculate_sortino_ratio
        )

        # Retornos asimetricos: mas subidas que bajadas
        np.random.seed(42)
        returns = np.concatenate([
            np.random.uniform(0.01, 0.05, 70),   # Subidas
            np.random.uniform(-0.02, 0, 30)      # Bajadas pequeñas
        ])
        np.random.shuffle(returns)

        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0)
        sortino = calculate_sortino_ratio(returns, risk_free_rate=0)

        # Sortino deberia ser mayor porque ignora volatilidad al alza
        assert sortino >= sharpe


class TestAlpha:
    """Tests para calculate_alpha()."""

    def test_alpha_outperformer(self):
        """Cartera que supera al benchmark tiene alpha positivo."""
        from src.core.analytics import calculate_alpha

        np.random.seed(42)
        benchmark = np.random.normal(0.0003, 0.01, 252)  # ~7.5% anual
        portfolio = benchmark + 0.0002  # Supera en ~5% anual

        alpha = calculate_alpha(portfolio, benchmark)
        assert alpha > 0

    def test_alpha_underperformer(self):
        """Cartera que no alcanza benchmark tiene alpha negativo."""
        from src.core.analytics import calculate_alpha

        np.random.seed(42)
        benchmark = np.random.normal(0.0003, 0.01, 252)
        portfolio = benchmark - 0.0002  # Por debajo

        alpha = calculate_alpha(portfolio, benchmark)
        assert alpha < 0


class TestCAGR:
    """Tests para calculate_cagr()."""

    def test_cagr_double_in_7_years(self):
        """Doblar dinero en ~7 años = ~10% CAGR (regla del 72)."""
        from src.core.analytics import calculate_cagr

        cagr = calculate_cagr(start_value=10000, end_value=20000, years=7.2)
        assert abs(cagr - 0.10) < 0.01  # ~10%

    def test_cagr_no_change(self):
        """Mismo valor inicial y final = 0% CAGR."""
        from src.core.analytics import calculate_cagr

        cagr = calculate_cagr(start_value=10000, end_value=10000, years=5)
        assert cagr == 0.0

    def test_cagr_loss(self):
        """Perdida de valor = CAGR negativo."""
        from src.core.analytics import calculate_cagr

        cagr = calculate_cagr(start_value=10000, end_value=5000, years=2)
        assert cagr < 0


class TestTotalReturn:
    """Tests para calculate_total_return()."""

    def test_total_return_simple(self):
        """Retornos simples."""
        from src.core.analytics import calculate_total_return

        # 10% + 10% = 21% (no 20%)
        returns = np.array([0.10, 0.10])
        total = calculate_total_return(returns)
        assert abs(total - 0.21) < 0.001

    def test_total_return_loss_recovery(self):
        """Perdida y recuperacion."""
        from src.core.analytics import calculate_total_return

        # -50% + 100% = 0% (no 50%)
        returns = np.array([-0.50, 1.00])
        total = calculate_total_return(returns)
        assert abs(total - 0.0) < 0.001

    def test_total_return_empty(self):
        """Array vacio devuelve cero."""
        from src.core.analytics import calculate_total_return

        total = calculate_total_return(np.array([]))
        assert total == 0.0


class TestIntegration:
    """Tests de integracion entre metricas."""

    def test_all_metrics_with_real_like_data(self):
        """Ejecutar todas las metricas con datos realistas."""
        from src.core.analytics import (
            calculate_volatility,
            calculate_var,
            calculate_beta,
            calculate_sharpe_ratio,
            calculate_sortino_ratio,
            calculate_alpha,
            calculate_max_drawdown,
            calculate_total_return,
        )

        np.random.seed(42)

        # Simular 2 años de retornos diarios
        n_days = 504
        benchmark_returns = np.random.normal(0.0003, 0.012, n_days)  # ~7.5% anual, 19% vol
        portfolio_returns = benchmark_returns * 1.1 + np.random.normal(0.0001, 0.005, n_days)

        # Calcular precios desde retornos
        portfolio_prices = 100 * np.cumprod(1 + portfolio_returns)

        # Ejecutar todas las metricas
        vol = calculate_volatility(portfolio_returns)
        var = calculate_var(portfolio_returns)
        beta = calculate_beta(portfolio_returns, benchmark_returns)
        sharpe = calculate_sharpe_ratio(portfolio_returns, risk_free_rate=0.02)
        sortino = calculate_sortino_ratio(portfolio_returns, risk_free_rate=0.02)
        alpha = calculate_alpha(portfolio_returns, benchmark_returns, risk_free_rate=0.02)
        mdd = calculate_max_drawdown(portfolio_prices)
        total = calculate_total_return(portfolio_returns)

        # Verificar que todas devuelven valores razonables
        assert 0 < vol < 1  # Volatilidad entre 0% y 100%
        assert 0 <= var < 0.5  # VaR razonable
        assert 0.5 < beta < 2  # Beta cercano a 1
        assert -5 < sharpe < 5  # Sharpe razonable
        assert -5 < sortino < 10  # Sortino razonable
        assert -0.5 < alpha < 0.5  # Alpha pequeño
        assert 0 <= mdd < 1  # MDD entre 0% y 100%
        assert -1 < total < 2  # Retorno total razonable

        print(f"\nMetricas calculadas:")
        print(f"  Volatilidad: {vol:.2%}")
        print(f"  VaR 95%: {var:.2%}")
        print(f"  Beta: {beta:.2f}")
        print(f"  Sharpe: {sharpe:.2f}")
        print(f"  Sortino: {sortino:.2f}")
        print(f"  Alpha: {alpha:.2%}")
        print(f"  Max DD: {mdd:.2%}")
        print(f"  Total Return: {total:.2%}")
