# CLAUDE.md

Guia para Claude al trabajar con investment_tracker.

## Stack tecnologico

Python 3.10+ | SQLite + SQLAlchemy | Pandas/NumPy | Streamlit + Plotly

## Comandos esenciales

```bash
# Ejecutar app Streamlit
streamlit run app/main.py

# Ejecutar API FastAPI
uvicorn api.main:app --reload
# Documentacion: http://localhost:8000/docs

# Tests con pytest (138 tests)
python -m pytest tests/unit/ -v           # Todos los unitarios
python -m pytest tests/unit/ -q           # Modo rapido
python -m pytest tests/unit/test_fund_service.py -v  # Archivo especifico

# Migraciones
python -m src.data.migrations.001_create_funds_table  # Crear tabla funds

# Instalar dependencias
pip install -r requirements.txt
```

## Arquitectura (Completa - Sesiones 1-8)

```
┌─────────────────────────────────────────────────────────┐
│              INTERFACES (Adaptadores)                    │
├─────────────────────┬───────────────────────────────────┤
│   Streamlit (app/)  │       FastAPI (api/)              │
│   UI Web            │       REST API                    │
└─────────┬───────────┴───────────────┬───────────────────┘
          │                           │
          └─────────────┬─────────────┘
                        │
          ┌─────────────▼─────────────┐
          │  SERVICIOS (src/services/) │
          │  PortfolioService          │
          │  FundService               │
          └─────────────┬─────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
┌───▼────────┐  ┌───────▼───────┐   ┌───────▼────────┐
│ CORE       │  │ NEGOCIO       │   │ DATOS          │
│ analytics/ │  │ Portfolio,Tax │   │ Database,Models│
│ Metricas   │  │ Dividends     │   │ Repositories   │
└────────────┘  └───────────────┘   └────────────────┘
```

## Estructura de carpetas

```
src/
├── services/           # Capa de servicios (orquestadores)
│   ├── base.py         # BaseService (clase abstracta)
│   ├── portfolio_service.py  # Dashboard, metricas avanzadas
│   └── fund_service.py       # Catalogo de fondos
├── core/               # Logica pura (sin BD/UI)
│   └── analytics/      # Sharpe, Beta, VaR, Volatilidad, etc.
├── data/               # Capa de datos
│   ├── database.py     # Database, modelos base
│   ├── models.py       # Fund (catalogo fondos)
│   ├── repositories/   # Patron Repository
│   │   └── fund_repository.py
│   └── migrations/     # Scripts de migracion
├── database.py         # [SHIM] Re-exporta desde data/
├── portfolio.py        # Calculos de cartera
├── tax_calculator.py   # Calculos fiscales
├── dividends.py        # Gestion dividendos
└── exceptions.py       # Excepciones de dominio

app/                    # UI Streamlit
├── pages/              # 1_Dashboard, 3_Analisis, 8_Buscador_Fondos, etc.
└── components/         # Componentes reutilizables

tests/                  # Tests pytest (138 tests)
├── conftest.py         # Fixtures compartidas
└── unit/               # test_analytics, test_portfolio_service,
                        # test_fund_repository, test_fund_service

api/                    # FastAPI (Sesion 8)
```

## Servicios disponibles

### PortfolioService - Cartera y metricas

```python
from src.services import PortfolioService

with PortfolioService() as service:
    # Dashboard
    data = service.get_dashboard_data(fiscal_year=2024)

    # Metricas avanzadas (Sharpe, Beta, Alpha, VaR, etc.)
    metrics = service.get_portfolio_metrics(
        start_date='2024-01-01',
        benchmark_name='SP500',
        risk_free_rate=0.02
    )

    print(f"Sharpe: {metrics['performance']['sharpe_ratio']:.2f}")
    print(f"Beta: {metrics['risk']['beta']:.2f}")
```

### FundService - Catalogo de fondos

```python
from src.services import FundService

with FundService() as service:
    # Buscar fondos
    funds = service.search_funds(
        category='Renta Variable',
        max_ter=1.0,
        min_rating=4,
        order_by='return_1y',
        order_desc=True
    )

    # Helpers
    low_cost = service.find_low_cost_funds(max_ter=0.5)
    top_rated = service.find_top_rated_funds(min_rating=5)

    # Importar fondos
    service.import_funds_bulk([
        {'isin': 'IE00B3RBWM25', 'name': 'Vanguard...', 'ter': 0.22},
    ])
```

## Metricas Analytics (src/core/analytics/)

```python
from src.core.analytics import (
    calculate_volatility,       # Riesgo anualizado
    calculate_sharpe_ratio,     # Rendimiento ajustado
    calculate_sortino_ratio,    # Solo volatilidad negativa
    calculate_beta,             # Sensibilidad mercado
    calculate_alpha,            # Exceso sobre CAPM
    calculate_var,              # Value at Risk
    calculate_max_drawdown,     # Maxima caida
    calculate_cagr_from_prices, # CAGR desde serie de precios
    calculate_total_return,     # Retorno total
)

# Uso: esperan Series de RETORNOS (no precios)
returns = prices.pct_change().dropna()
sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)

# CAGR desde serie de precios (no retornos)
cagr = calculate_cagr_from_prices(prices_series)
```

**IMPORTANTE:** Usar `calculate_cagr_from_prices(series)` para series de precios.
NO usar `calculate_cagr()` directamente - requiere (start_value, end_value, years).

## Patron Repository (src/data/repositories/)

```python
from src.data import Database
from src.data.repositories import FundRepository

db = Database()
repo = FundRepository(db.session)

# Busqueda avanzada con 20+ filtros
funds = repo.search(
    category='Renta Variable',
    max_ter=1.0,
    min_rating=4,
    order_by='return_1y'
)

# CRUD
fund = repo.get_by_isin('IE00B3RBWM25')
repo.upsert({'isin': '...', 'name': '...', 'ter': 0.5})

db.close()
```

## Convenciones

### Imports
```python
# Servicios (preferido)
from src.services import PortfolioService, FundService

# Modelos
from src.data import Database, Fund
from src.data.repositories import FundRepository

# Analytics
from src.core.analytics import calculate_sharpe_ratio
```

### Servicios
- Heredan de `BaseService`
- Soportan context manager: `with Service() as s:`
- Siempre cerrar con `.close()` si no usas context manager

### Tests
- Usar pytest (138 tests actuales)
- Fixtures en `tests/conftest.py`
- BD temporal con fixture `temp_db_path`

## Reglas fiscales (Espana)

- Metodo: **FIFO** (First In First Out)
- Retencion dividendos: 19%
- Divisas: EUR, USD, GBX, CAD
- Campo `realized_gain_eur` para B/P en EUR

## Database - Metodos de transacciones

```python
from src.data import Database

db = Database()

# Obtener transaccion por ID (para editar/borrar)
trans = db.get_transaction_by_id(123)

# Actualizar transaccion
db.update_transaction(123, {'price': 10.50, 'quantity': 100})

# Eliminar transaccion
db.delete_transaction(123)

db.close()
```

## Limitaciones conocidas

### yfinance y fondos europeos (ISINs)

**Problema:** yfinance NO tiene datos de la mayoria de fondos mutuos europeos.
ISINs como `IE00BLP5S460`, `LU0996182563` no se encuentran.

**Comportamiento actual:**
- El sistema detecta si es ISIN (formato: 2 letras + 10 alfanumericos)
- Intenta buscar el ticker correspondiente
- Si falla, cachea el ISIN para no reintentar
- Log: "ISIN X: sin datos en yfinance (fondo no disponible)"

**Solucion futura:** Integrar API alternativa (Morningstar, Investing.com)

## Errores a evitar

1. **Logica en UI** → Usar servicios (PortfolioService, FundService)
2. **No cerrar conexiones** → Usar context managers
3. **Tests manuales** → Usar pytest
4. **Imports rotos** → src/database.py es shim de compatibilidad
5. **calculate_cagr()** → Usar `calculate_cagr_from_prices()` para series

## Estado del proyecto

Plan de escalabilidad: **8/8 sesiones completadas** ✅

| Sesion | Descripcion |
|--------|-------------|
| 1-4 | Estructura, servicios, pytest, analytics |
| 5 | Integracion metricas en UI |
| 6 | Modelo Fund y FundRepository |
| 7 | FundService y UI Buscador |
| 8 | FastAPI Demo ✅ |

## API FastAPI (api/)

```python
# Endpoints disponibles
GET  /                    # Health check
GET  /dashboard           # Datos del dashboard
GET  /dashboard/metrics   # Metricas avanzadas (Sharpe, Beta, VaR)
GET  /funds               # Buscar fondos con filtros
GET  /funds/{isin}        # Detalle de fondo
GET  /benchmarks          # Benchmarks disponibles

# Ejemplo de uso
import requests
r = requests.get("http://localhost:8000/dashboard")
data = r.json()
print(f"Valor cartera: {data['metrics']['total_value']}")
```

## Archivos ignorados

- `data/database.db`, `data/*.db`
- `data/exports/`, `data/benchmark_data/`
- `venv/`, `__pycache__/`, `*.log`
