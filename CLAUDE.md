# CLAUDE.md

Guia para Claude al trabajar con investment_tracker.

## Stack tecnologico

Python 3.10+ | SQLite + SQLAlchemy | Pandas/NumPy | Streamlit + Plotly

## Comandos esenciales

```bash
# Ejecutar app
streamlit run app/main.py

# Tests con pytest (RECOMENDADO)
pytest                                    # Todos los tests
pytest tests/unit/ -v                     # Solo unitarios
pytest tests/unit/test_portfolio_service.py -v  # Archivo especifico

# Tests legacy (raiz)
python test_portfolio.py

# Instalar dependencias
pip install -r requirements.txt
```

## Arquitectura (Refactorizada)

```
                    ┌─────────────────────────────┐
                    │      PRESENTACION (app/)     │
                    │   Streamlit - Solo UI        │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    SERVICIOS (src/services/) │
                    │  PortfolioService (puente)   │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼───────┐    ┌─────────────▼─────────────┐   ┌────────▼────────┐
│ CORE (analytics)│    │   NEGOCIO (src/*.py)      │   │  DATOS (src/data)│
│ Metricas puras  │    │ Portfolio, Tax, Dividends │   │    Database      │
└─────────────────┘    └───────────────────────────┘   └──────────────────┘
```

## Estructura de carpetas

```
src/
├── services/           # [NUEVO] Capa de servicios
│   ├── base.py         # BaseService (clase abstracta)
│   └── portfolio_service.py  # Orquestador para Dashboard
├── core/               # [NUEVO] Logica pura
│   └── analytics/      # Metricas: Sharpe, Beta, VaR, etc.
├── data/               # [NUEVO] Capa de datos
│   └── database.py     # Database, modelos SQLAlchemy
├── database.py         # [COMPATIBILIDAD] Re-exporta desde data/
├── portfolio.py        # Calculos de cartera
├── tax_calculator.py   # Calculos fiscales
├── dividends.py        # Gestion dividendos
└── exceptions.py       # [NUEVO] Excepciones de dominio

app/                    # UI Streamlit
├── pages/              # Paginas (1_Dashboard.py, etc.)
└── components/         # Componentes reutilizables

tests/                  # [NUEVO] Tests pytest
├── conftest.py         # Fixtures compartidas
├── unit/               # Tests unitarios
└── integration/        # Tests de integracion

api/                    # [NUEVO] FastAPI (futuro)
```

## Patron de uso: PortfolioService

```python
# ANTES (acoplado)
from src.portfolio import Portfolio
from src.database import Database
from src.tax_calculator import TaxCalculator

portfolio = Portfolio()
db = Database()
tax = TaxCalculator()
# ... logica dispersa en UI ...

# AHORA (desacoplado)
from src.services.portfolio_service import PortfolioService

service = PortfolioService()
data = service.get_dashboard_data(fiscal_year=2024)

# UI solo renderiza
st.metric("Valor Total", f"{data['metrics']['total_value']:,.2f}EUR")
service.close()
```

## Metricas Analytics (src/core/analytics/)

```python
from src.core.analytics import (
    calculate_volatility,    # Riesgo
    calculate_sharpe_ratio,  # Rendimiento ajustado
    calculate_beta,          # Sensibilidad mercado
    calculate_max_drawdown   # Maxima caida
)

# Uso: esperan Series de RETORNOS (no precios)
returns = prices.pct_change().dropna()
sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
```

## Metricas Avanzadas via Servicio

```python
from src.services import PortfolioService

with PortfolioService() as service:
    metrics = service.get_portfolio_metrics(
        start_date='2024-01-01',
        benchmark_name='SP500',
        risk_free_rate=0.02
    )

    # Riesgo
    print(f"Volatilidad: {metrics['risk']['volatility']:.2%}")
    print(f"Beta: {metrics['risk']['beta']:.2f}")
    print(f"Max Drawdown: {metrics['risk']['max_drawdown']:.2%}")

    # Rendimiento
    print(f"Sharpe: {metrics['performance']['sharpe_ratio']:.2f}")
    print(f"Alpha: {metrics['performance']['alpha']:.2%}")
```

## Convenciones

### Imports
```python
# Preferir imports desde servicios
from src.services import PortfolioService

# Base de datos (compatibilidad mantenida)
from src.database import Database  # Funciona igual que antes
from src.data import Database      # Nueva ubicacion
```

### Servicios
- Heredan de `BaseService`
- Soportan context manager: `with PortfolioService() as s:`
- Siempre cerrar con `.close()`

### Tests
- Usar pytest, no tests manuales
- Fixtures en `tests/conftest.py`
- BD temporal automatica con `temp_db_path` fixture

## Reglas fiscales (España)

- Metodo: **FIFO** (First In First Out)
- Retencion dividendos: 19%
- Divisas: EUR, USD, GBX, CAD
- Campo `realized_gain_eur` para B/P en EUR

## Errores a evitar

1. **Logica en UI** → Usar PortfolioService
2. **No cerrar conexiones** → Usar context managers
3. **Tests manuales** → Usar pytest
4. **Imports rotos** → src/database.py es shim de compatibilidad

## Archivos ignorados

- `data/database.db`, `data/*.db`
- `data/exports/`, `data/benchmark_data/`
- `venv/`, `__pycache__/`, `*.log`
