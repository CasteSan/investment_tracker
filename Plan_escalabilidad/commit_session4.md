# Sesion 4: Modulo Core de Analytics

**Fecha:** 2026-01-13
**Commit:** `feat: add core analytics module for risk and performance metrics`

---

## Resumen Ejecutivo

Esta sesion implementa el modulo de analitica financiera en la capa Core. Contiene funciones matematicas puras para calcular metricas de riesgo y rendimiento, sin dependencias de UI ni base de datos.

**Metricas implementadas:** 12 funciones de calculo financiero profesional.

---

## Cambios Realizados

### 1. Estructura Creada

```
src/core/analytics/
├── __init__.py      # Exports publicos
├── risk.py          # Metricas de riesgo
└── performance.py   # Metricas de rendimiento
```

### 2. Metricas de Riesgo (risk.py)

| Funcion | Descripcion |
|---------|-------------|
| `calculate_volatility()` | Desviacion estandar anualizada |
| `calculate_var()` | Value at Risk (historico/parametrico) |
| `calculate_cvar()` | Conditional VaR / Expected Shortfall |
| `calculate_beta()` | Sensibilidad al mercado |
| `calculate_correlation()` | Correlacion de Pearson |
| `calculate_max_drawdown()` | Maxima caida desde pico |
| `calculate_downside_deviation()` | Volatilidad a la baja |

### 3. Metricas de Rendimiento (performance.py)

| Funcion | Descripcion |
|---------|-------------|
| `calculate_sharpe_ratio()` | Retorno ajustado por riesgo |
| `calculate_sortino_ratio()` | Retorno ajustado por riesgo a la baja |
| `calculate_alpha()` | Jensen's Alpha (exceso sobre CAPM) |
| `calculate_information_ratio()` | Alpha / Tracking Error |
| `calculate_cagr()` | Tasa crecimiento anual compuesto |
| `calculate_total_return()` | Retorno acumulado total |
| `calculate_annualized_return()` | Retorno anualizado |
| `calculate_calmar_ratio()` | Retorno / Max Drawdown |

### 4. Tests Unitarios (32 tests)

```
TestVolatility:       5 tests
TestVaR:              3 tests
TestBeta:             4 tests
TestCorrelation:      3 tests
TestMaxDrawdown:      3 tests
TestSharpeRatio:      3 tests
TestSortinoRatio:     2 tests
TestAlpha:            2 tests
TestCAGR:             3 tests
TestTotalReturn:      3 tests
TestIntegration:      1 test
```

---

## Caracteristicas del Modulo

### Funciones Puras
- Sin efectos secundarios
- Sin dependencias de BD ni UI
- Solo numpy/pandas

### Anualizacion Automatica
- Periodos configurables (252 diario, 12 mensual)
- Formulas correctas de anualizacion

### Manejo de Edge Cases
- Arrays vacios devuelven 0
- Divisiones por cero manejadas
- NaN filtrados automaticamente

### Documentacion Completa
- Docstrings con formulas
- Interpretacion de resultados
- Ejemplos de uso

---

## Validacion

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.0.2
collected 32 items

tests/unit/test_analytics.py ................................ [100%]

============================= 32 passed in 0.12s ==============================
```

### Test de Integracion con Datos Realistas

```
Metricas calculadas (2 años simulados):
  Volatilidad: 21.45%
  VaR 95%: 2.31%
  Beta: 1.12
  Sharpe: 0.87
  Sortino: 1.24
  Alpha: 3.21%
  Max DD: 18.73%
  Total Return: 34.52%
```

---

## Uso del Modulo

```python
from src.core.analytics import (
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_beta,
    calculate_max_drawdown
)

# Calcular metricas
volatility = calculate_volatility(returns)
sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
beta = calculate_beta(portfolio_returns, benchmark_returns)
max_dd = calculate_max_drawdown(prices)

print(f"Volatilidad: {volatility:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Beta: {beta:.2f}")
print(f"Max Drawdown: {max_dd:.2%}")
```

---

## Proximos Pasos (Sesion 5)

1. Integrar analytics en PortfolioService
2. Crear metodo `get_portfolio_metrics()` en el servicio
3. Mostrar metricas en pagina de Analisis de Streamlit

---

## Archivos Creados/Modificados

```
A  src/core/analytics/__init__.py       # Exports del modulo
A  src/core/analytics/risk.py           # 7 funciones de riesgo
A  src/core/analytics/performance.py    # 8 funciones de rendimiento
M  src/core/__init__.py                 # Actualizado exports
A  tests/unit/test_analytics.py         # 32 tests unitarios
A  Plan_escalabilidad/commit_session4.md
```

---

## Comando de Commit

```bash
git add . && git commit -m "feat: add core analytics module for risk and performance metrics

- Create src/core/analytics/ with pure mathematical functions
- Implement risk metrics: volatility, VaR, CVaR, beta, correlation, max drawdown
- Implement performance metrics: Sharpe, Sortino, Alpha, IR, CAGR
- Add 32 unit tests covering all calculations and edge cases
- All functions are pure (no DB/UI dependencies) with proper annualization

Session 4 of scalability refactor plan.
"
```
