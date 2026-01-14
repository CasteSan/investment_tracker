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

# Tests con pytest
python -m pytest tests/unit/ -v           # Todos los unitarios
python -m pytest tests/unit/ -q           # Modo rapido

# Migraciones (multi-portfolio)
python scripts/apply_migrations.py        # Aplica a todas las BDs
python scripts/apply_migrations.py --check  # Solo verificar

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
investment_tracker/
├── api/                    # FastAPI REST API
│   └── main.py             # Endpoints
├── app/                    # UI Streamlit
│   ├── pages/              # 8 paginas
│   └── components/         # Componentes reutilizables
├── data/
│   └── portfolios/         # BDs por cartera (multi-portfolio)
├── docs/                   # Documentacion
│   └── architecture/       # Plan de escalabilidad consolidado
├── scripts/
│   └── apply_migrations.py # Migraciones multi-BD
├── src/                    # Codigo fuente
│   ├── services/           # Capa de servicios
│   │   ├── base.py         # BaseService
│   │   ├── portfolio_service.py
│   │   └── fund_service.py # + gestion de categorias
│   ├── providers/          # APIs externas
│   │   └── morningstar.py  # FundDataProvider (mstarpy)
│   ├── core/               # Logica pura
│   │   └── analytics/      # Metricas (Sharpe, Beta, VaR)
│   ├── data/               # Capa de datos
│   │   ├── database.py
│   │   ├── models.py       # Fund, Category
│   │   ├── repositories/
│   │   └── migrations/
│   ├── portfolio.py        # Calculos de cartera
│   ├── tax_calculator.py   # Calculos fiscales
│   ├── dividends.py        # Gestion dividendos
│   └── database.py         # [SHIM] Compatibilidad
├── tests/                  # Tests pytest
│   ├── conftest.py
│   ├── unit/               # Tests unitarios
│   └── scripts/            # Tests de scripts
├── CHANGELOG.md            # Historial de versiones
├── CONTRIBUTING.md         # Guia de contribucion
├── LICENSE                 # MIT
└── README.md               # Documentacion principal
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

    # Importar desde Morningstar (v1.3.0)
    preview = service.fetch_fund_preview('IE00B3RBWM25')  # Solo preview
    fund = service.fetch_and_import_fund('IE00B3RBWM25')  # Guarda en BD

    # Categorias dinamicas (v1.3.0)
    categories = service.get_all_categories()  # Lista desde BD
    service.add_category('RV Small Caps')      # Crear nueva

    # Helpers
    low_cost = service.find_low_cost_funds(max_ter=0.5)
    top_rated = service.find_top_rated_funds(min_rating=5)
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

**Solucion (v1.3.0):** Usar el Catalogo de Fondos con Morningstar:
- `FundService.fetch_and_import_fund(isin)` obtiene datos de Morningstar
- Incluye: rentabilidades, volatilidad, holdings, sectores, paises
- Los fondos importados se guardan en la BD local

### Morningstar API (mstarpy)

**Limitaciones:**
- API de timeSeries puede dar error 401 (rate limiting)
- El grafico NAV tiene fallback defensivo
- Algunos fondos no tienen todos los campos

## Errores a evitar

1. **Logica en UI** → Usar servicios (PortfolioService, FundService)
2. **No cerrar conexiones** → Usar context managers
3. **Tests manuales** → Usar pytest
4. **Imports rotos** → src/database.py es shim de compatibilidad
5. **calculate_cagr()** → Usar `calculate_cagr_from_prices()` para series

## Estado del proyecto

**Version:** 1.3.0 (ver CHANGELOG.md)
**Features principales:**
- Multi-portfolio (v1.2.0)
- Catalogo Inteligente de Fondos con Morningstar (v1.3.0)
- Categorias personalizadas dinamicas (v1.3.0)
- Dashboard profesional por fondo (v1.3.0)

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

## Archivos ignorados (.gitignore)

- `data/*.db`, `data/*.csv` (excepto ejemplo_transacciones.csv)
- `data/exports/`, `data/benchmark_data/`
- `venv/`, `__pycache__/`, `*.log`, `.pytest_cache/`
- `.claude/`, `.vscode/`, `.idea/`

## Documentacion adicional

- `CHANGELOG.md` - Historial de versiones
- `CONTRIBUTING.md` - Normas de desarrollo
- `docs/architecture/` - Plan de escalabilidad consolidado
