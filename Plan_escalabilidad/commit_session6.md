# Sesion 6: Modelo de Datos y Repositorio de Fondos

**Fecha:** 2026-01-13
**Commit:** `feat: add fund data model and repository`

---

## Resumen Ejecutivo

Esta sesion crea la infraestructura para el catalogo de fondos de inversion:
- Modelo `Fund` con 40+ campos para datos de fondos
- `FundRepository` con metodos de filtrado avanzado
- Script de migracion para crear la tabla
- 37 tests unitarios

---

## Cambios Realizados

### 1. Modelo Fund (src/data/models.py)

Nuevo archivo con el modelo SQLAlchemy para fondos de inversion.

**Campos principales (40+):**

| Categoria | Campos |
|-----------|--------|
| Identificacion | isin, ticker, name, short_name |
| Clasificacion | category, subcategory, asset_class, region, sector |
| Gestora | manager, manager_country, fund_domicile |
| Costes | ter, ongoing_charges, entry_fee, exit_fee, management_fee |
| Riesgo | risk_level (1-7), morningstar_rating (1-5) |
| Rendimiento | return_ytd, return_1y, return_3y, return_5y, return_10y |
| Volatilidad | volatility_3y, sharpe_3y, max_drawdown_3y |
| Tamano | aum, min_investment, min_additional |
| Politica | distribution_policy, dividend_frequency |
| Benchmark | benchmark_name, benchmark_ticker |
| Metadatos | inception_date, data_date, source, url |

**Constantes para UI:**
```python
FUND_CATEGORIES = ['Renta Variable', 'Renta Fija', 'Mixto', ...]
FUND_REGIONS = ['Global', 'Europa', 'USA', ...]
FUND_RISK_LEVELS = {1: 'Muy bajo', 2: 'Bajo', ..., 7: 'Muy alto'}
```

### 2. FundRepository (src/data/repositories/fund_repository.py)

Repositorio con patron Repository para acceso a datos de fondos.

**Metodos CRUD:**
- `get_by_id()`, `get_by_isin()`, `get_by_ticker()`
- `get_all()`, `count()`
- `add()`, `add_many()`, `update()`, `delete()`

**Metodo search() - Busqueda avanzada:**
```python
funds = repo.search(
    category='Renta Variable',
    max_ter=1.0,
    min_rating=4,
    region='Global',
    order_by='return_1y',
    order_desc=True,
    limit=10
)
```

**Filtros soportados:**
- Texto: name, isin, manager (busqueda parcial)
- Categoria: category, subcategory, asset_class, region, sector
- Costes: max_ter, min_ter
- Riesgo: risk_level, max_risk_level, min_risk_level
- Rating: min_rating, max_rating
- Rendimiento: min_return_1y, min_return_3y
- Tamano: min_aum, max_min_investment
- Otros: currency, distribution_policy, hedged

**Metodos helper:**
- `find_by_category()`, `find_by_manager()`
- `find_low_cost()`, `find_top_rated()`, `find_low_risk()`
- `find_best_performers()`

**Metodos de agregacion:**
- `get_categories()`, `get_managers()`, `get_regions()`
- `get_stats()` - estadisticas del catalogo

**Metodos de importacion:**
- `upsert()` - insertar o actualizar por ISIN
- `bulk_upsert()` - importacion masiva

### 3. Script de Migracion (src/data/migrations/001_create_funds_table.py)

Script ejecutable para crear la tabla funds en la BD existente.

```bash
# Crear tabla
python -m src.data.migrations.001_create_funds_table

# Rollback (eliminar tabla)
python -m src.data.migrations.001_create_funds_table --rollback
```

### 4. Tests Unitarios (tests/unit/test_fund_repository.py)

37 tests cubriendo:

```
TestFundModel:           4 tests - Modelo basico
TestFundConstants:       3 tests - Constantes
TestFundRepositoryCRUD: 10 tests - Operaciones CRUD
TestFundRepositorySearch: 11 tests - Busqueda y filtrado
TestFundRepositoryHelpers: 7 tests - Metodos helper
TestFundRepositoryUpsert: 3 tests - Importacion
```

---

## Estructura Creada

```
src/data/
├── models.py                    # [NUEVO] Modelo Fund
├── repositories/
│   ├── __init__.py              # [NUEVO] Exports
│   └── fund_repository.py       # [NUEVO] Repositorio
├── migrations/
│   ├── __init__.py              # [NUEVO]
│   └── 001_create_funds_table.py # [NUEVO] Migracion
└── __init__.py                  # [ACTUALIZADO] Exports
```

---

## Uso del Repositorio

```python
from src.data import Database, Fund
from src.data.repositories import FundRepository

# Crear repositorio
db = Database()
repo = FundRepository(db.session)

# Buscar fondos baratos de renta variable con buen rating
funds = repo.search(
    category='Renta Variable',
    max_ter=0.5,
    min_rating=4,
    order_by='return_3y',
    order_desc=True
)

for fund in funds:
    print(f"{fund.name}: TER={fund.ter}%, Rating={fund.morningstar_rating}")

# Estadisticas del catalogo
stats = repo.get_stats()
print(f"Total fondos: {stats['total_funds']}")
print(f"Por categoria: {stats['by_category']}")

# Importar/actualizar fondos
repo.bulk_upsert([
    {'isin': 'ES0114105036', 'name': 'Bestinver...', 'ter': 1.78},
    {'isin': 'IE00B3RBWM25', 'name': 'Vanguard...', 'ter': 0.22},
])

db.close()
```

---

## Validacion

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.0.2
collected 110 items

tests/unit/test_analytics.py ............................ [29%]
tests/unit/test_fund_repository.py ..................... [63%]
tests/unit/test_portfolio_service.py ................... [100%]

============================= 110 passed in 6.60s =============================
```

---

## Proximos Pasos (Sesion 7)

1. Crear `FundService` en `src/services/`
2. Crear pagina `app/pages/8_🔍_Buscador_Fondos.py`
3. Implementar filtros visuales en Streamlit

---

## Archivos Creados/Modificados

```
A  src/data/models.py                           # Modelo Fund (200+ lineas)
A  src/data/repositories/__init__.py            # Package init
A  src/data/repositories/fund_repository.py     # Repositorio (400+ lineas)
A  src/data/migrations/__init__.py              # Package init
A  src/data/migrations/001_create_funds_table.py # Script migracion
M  src/data/__init__.py                         # Actualizado exports
A  tests/unit/test_fund_repository.py           # 37 tests
A  Plan_escalabilidad/commit_session6.md        # Esta documentacion
```

---

## Comando de Commit

```bash
git add . && git commit -m "feat: add fund data model and repository

Create infrastructure for fund catalog functionality:

- src/data/models.py:
  * New Fund model with 40+ fields (ISIN, TER, risk, returns, etc.)
  * Constants: FUND_CATEGORIES, FUND_REGIONS, FUND_RISK_LEVELS
  * Indexes for common queries (category+risk, manager+category)

- src/data/repositories/fund_repository.py:
  * Full CRUD operations (get_by_id, get_by_isin, add, delete)
  * Advanced search() with 20+ filter parameters
  * Helper methods: find_low_cost, find_top_rated, find_best_performers
  * Aggregation: get_categories, get_managers, get_stats
  * Import support: upsert, bulk_upsert

- src/data/migrations/001_create_funds_table.py:
  * Executable script to create/drop funds table
  * Supports --rollback flag

- tests/unit/test_fund_repository.py:
  * 37 unit tests covering model, CRUD, search, helpers, upsert

Test results: 110 passed (32 analytics + 41 portfolio + 37 fund)

Session 6 of scalability refactor plan.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
