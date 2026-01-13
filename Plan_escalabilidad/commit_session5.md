# Sesion 5: Integracion Analytics en Servicio y UI

**Fecha:** 2026-01-13
**Commit:** `feat: integrate advanced metrics into analysis page`

---

## Resumen Ejecutivo

Esta sesion conecta las metricas matematicas de `src/core/analytics/` (creadas en Sesion 4) con los datos reales del portfolio y las muestra en la pagina de Analisis de Streamlit.

**Resultado:** Nueva seccion de metricas avanzadas en la UI con 9 KPIs profesionales.

---

## Cambios Realizados

### 1. PortfolioService - Nuevo metodo get_portfolio_metrics()

Ubicacion: `src/services/portfolio_service.py:479-661`

```python
def get_portfolio_metrics(
    self,
    start_date: str = None,
    end_date: str = None,
    benchmark_name: str = 'SP500',
    risk_free_rate: float = 0.02
) -> Dict[str, Any]:
```

**Funcionalidad:**
- Obtiene serie historica de valores del portfolio
- Calcula retornos diarios
- Aplica funciones de `src/core/analytics/`
- Compara contra benchmark para Beta y Alpha
- Devuelve estructura organizada de metricas

**Estructura de retorno:**
```python
{
    'risk': {
        'volatility': float,      # Volatilidad anualizada
        'var_95': float,          # VaR al 95%
        'max_drawdown': float,    # Maxima caida
        'beta': float,            # Beta vs benchmark
    },
    'performance': {
        'total_return': float,    # Retorno total acumulado
        'cagr': float,            # Tasa crecimiento anual compuesto
        'sharpe_ratio': float,    # Ratio de Sharpe
        'sortino_ratio': float,   # Ratio de Sortino
        'alpha': float,           # Alpha de Jensen
    },
    'meta': {
        'start_date': str,
        'end_date': str,
        'benchmark': str,
        'trading_days': int,
        'has_benchmark_data': bool,
    }
}
```

### 2. Nuevo metodo get_available_benchmarks()

Lista los benchmarks disponibles en la base de datos para el selector de UI.

### 3. Pagina de Analisis - Nueva seccion de metricas

Ubicacion: `app/pages/3_📈_Analisis.py:132-291`

**Nuevos controles en sidebar:**
- Selector de periodo (1 mes a Todo)
- Selector de benchmark (SP500, IBEX35, MSCIWORLD, EUROSTOXX50)
- Slider de tasa libre de riesgo (0-5%)

**Nuevas metricas mostradas:**

| Categoria | Metrica | Descripcion |
|-----------|---------|-------------|
| Rendimiento | Retorno Total | Rentabilidad acumulada |
| Rendimiento | CAGR | Tasa crecimiento anual compuesto |
| Rendimiento | Sharpe Ratio | Retorno ajustado por riesgo |
| Rendimiento | Sortino Ratio | Solo considera volatilidad negativa |
| Rendimiento | Alpha | Exceso sobre benchmark |
| Riesgo | Volatilidad | Desviacion estandar anualizada |
| Riesgo | VaR 95% | Perdida maxima esperada |
| Riesgo | Max Drawdown | Maxima caida desde pico |
| Riesgo | Beta | Sensibilidad al mercado |

### 4. Tests nuevos (7 tests)

Ubicacion: `tests/unit/test_portfolio_service.py`

```
TestGetPortfolioMetrics:
  - test_returns_correct_structure
  - test_returns_floats
  - test_accepts_custom_parameters
  - test_default_benchmark_is_sp500
  - test_empty_portfolio_returns_defaults

TestGetAvailableBenchmarks:
  - test_returns_list
  - test_each_benchmark_has_required_fields
```

---

## Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAGINA ANALISIS (UI)                         │
│                                                                 │
│  Controles: periodo, benchmark, tasa libre riesgo               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PortfolioService.get_portfolio_metrics()           │
│                                                                 │
│  1. Obtiene valores historicos del portfolio                    │
│  2. Calcula retornos diarios                                    │
│  3. Obtiene datos de benchmark                                  │
│  4. Llama a funciones de analytics                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐
│ MarketData  │    │ BenchmarkComp.  │    │ Analytics    │
│ Manager     │    │ get_benchmark_  │    │ calculate_*  │
│             │    │ series()        │    │              │
└─────────────┘    └─────────────────┘    └──────────────┘
```

---

## Validacion

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.0.2
collected 73 items

tests/unit/test_analytics.py ................................ [43%]
tests/unit/test_portfolio_service.py ......................................... [100%]

============================= 73 passed in 2.76s ==============================
```

---

## Uso en UI

La nueva seccion aparece automaticamente en la pagina de Analisis:

1. Navegar a "📈 Analisis" en la app
2. En el sidebar, seleccionar:
   - Periodo de analisis
   - Benchmark de comparacion
   - Tasa libre de riesgo
3. Las metricas se calculan y muestran en tiempo real

**Nota:** Si no hay datos historicos de precios, se muestra un mensaje indicando que se deben descargar en Configuracion.

---

## Proximos Pasos (Sesion 6)

1. Crear modelo de datos para Fondos (`src/data/models.py`)
2. Crear repositorio de fondos (`src/data/repositories/fund_repository.py`)
3. Crear migracion para tabla de fondos

---

## Archivos Creados/Modificados

```
M  src/services/portfolio_service.py   # +190 lineas (get_portfolio_metrics, imports)
M  app/pages/3_📈_Analisis.py          # +160 lineas (seccion metricas avanzadas)
M  tests/unit/test_portfolio_service.py # +84 lineas (7 tests nuevos)
A  Plan_escalabilidad/commit_session5.md
```

---

## Comando de Commit

```bash
git add . && git commit -m "feat: integrate advanced metrics into analysis page

- Add get_portfolio_metrics() method to PortfolioService
- Integrate src/core/analytics functions with real portfolio data
- Create new advanced metrics section in Analysis page UI
- Add sidebar controls for period, benchmark, and risk-free rate
- Display 9 KPIs: Sharpe, Sortino, Alpha, Beta, VaR, Volatility, etc.
- Add 7 unit tests for new functionality
- Total tests: 73 passed

Session 5 of scalability refactor plan.
"
```
