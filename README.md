# Investment Tracker

Sistema de gestion y analisis de carteras de inversion con arquitectura hexagonal.

Este proyecto es tanto una herramienta funcional como un **caso de estudio educativo** sobre arquitectura de software, patrones de diseno y buenas practicas en Python.

---

## Tabla de Contenidos

1. [Descripcion del Proyecto](#descripcion-del-proyecto)
2. [Arquitectura](#arquitectura)
3. [Estructura de Carpetas](#estructura-de-carpetas)
4. [Stack Tecnologico](#stack-tecnologico)
5. [Instalacion y Configuracion](#instalacion-y-configuracion)
6. [Uso](#uso)
7. [Testing](#testing)
8. [Patrones de Diseno](#patrones-de-diseno)
9. [Lecciones Aprendidas](#lecciones-aprendidas)

---

## Descripcion del Proyecto

Investment Tracker es un gestor de carteras personales que permite:

- Registrar transacciones de compra/venta de activos
- Calcular posiciones actuales y rentabilidad
- Analizar metricas de riesgo (Sharpe, Beta, VaR, Volatilidad)
- Gestionar dividendos y calculos fiscales (FIFO)
- Explorar un catalogo de fondos de inversion
- Exponer datos via UI web (Streamlit) y API REST (FastAPI)

### Por que este proyecto es educativo

El proyecto fue desarrollado en **8 sesiones incrementales** siguiendo un plan de escalabilidad. Cada sesion introdujo conceptos arquitectonicos especificos:

| Sesion | Concepto Introducido |
|--------|---------------------|
| 1-2 | Reestructuracion en capas, Service Layer |
| 3 | Infraestructura de testing con pytest |
| 4 | Modulo Core (logica pura sin dependencias) |
| 5 | Integracion de capas (Core -> Service -> UI) |
| 6 | Patron Repository para acceso a datos |
| 7 | UI completa consumiendo servicios |
| 8 | API REST demostrando desacoplamiento |

---

## Arquitectura

### Diagrama de Capas

```
+------------------------------------------------------------------+
|                      CAPA DE PRESENTACION                         |
|                   (Adaptadores de Entrada)                        |
+--------------------------------+---------------------------------+
|        Streamlit (app/)        |        FastAPI (api/)           |
|        UI Web Interactiva      |        API REST JSON            |
|        Puerto: 8501            |        Puerto: 8000             |
+---------------+----------------+----------------+----------------+
                |                                 |
                +----------------+----------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                      CAPA DE SERVICIOS                            |
|                  (Orquestadores de Negocio)                       |
+------------------------------------------------------------------+
|  PortfolioService              |  FundService                     |
|  - get_dashboard_data()        |  - search_funds()                |
|  - get_portfolio_metrics()     |  - get_fund_details()            |
|  - filter_positions()          |  - import_funds_bulk()           |
+---------------+----------------+----------------+-----------------+
                |                                 |
                +----------------+----------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                      CAPAS INFERIORES                             |
+------------------+------------------+----------------------------+
|   CORE           |   NEGOCIO        |   DATOS                    |
|   (analytics/)   |   (src/*.py)     |   (data/)                  |
+------------------+------------------+----------------------------+
|  Funciones puras |  Portfolio       |  Database (SQLAlchemy)     |
|  sin dependencias|  TaxCalculator   |  Models (Fund, etc.)       |
|                  |  DividendManager |  Repositories              |
|  - volatility()  |  MarketData      |  - FundRepository          |
|  - sharpe_ratio()|  Benchmarks      |                            |
|  - beta()        |                  |                            |
|  - var()         |                  |                            |
+------------------+------------------+----------------------------+
                                 |
                                 v
                        +----------------+
                        |    SQLite      |
                        |  database.db   |
                        +----------------+
```

### Explicacion de Cada Capa

#### 1. Capa de Presentacion (Adaptadores)

**Proposito:** Interactuar con el mundo exterior (usuarios, otros sistemas).

**Caracteristicas:**
- **No contiene logica de negocio** - solo presenta datos
- **Intercambiable** - puedes tener multiples interfaces
- **Depende de la capa de servicios** - nunca accede directamente a datos

```python
# app/pages/1_Dashboard.py (Streamlit)
from src.services import PortfolioService

with PortfolioService() as service:
    data = service.get_dashboard_data(fiscal_year=2024)
    st.metric("Valor Total", f"{data['metrics']['total_value']:,.2f} EUR")
```

```python
# api/main.py (FastAPI)
from src.services import PortfolioService

@app.get("/dashboard")
async def get_dashboard():
    with PortfolioService() as service:
        return service.get_dashboard_data()
```

**Por que es importante:**
- Streamlit y FastAPI usan el **mismo servicio**
- Si manana necesitas una app movil, solo creas un nuevo adaptador
- La logica de negocio no se duplica

#### 2. Capa de Servicios (Orquestadores)

**Proposito:** Coordinar operaciones de negocio y exponer una API limpia.

**Caracteristicas:**
- **Punto de entrada unico** para operaciones complejas
- **Orquesta** multiples modulos (Portfolio, Tax, Dividends)
- **Gestiona transaccionalidad** y manejo de errores
- **No conoce la UI** - devuelve datos puros (dicts, DataFrames)

```python
# src/services/portfolio_service.py
class PortfolioService(BaseService):
    def get_dashboard_data(self, fiscal_year: int = None) -> Dict[str, Any]:
        """
        Orquesta la obtencion de todos los datos del dashboard.
        Antes, esta logica estaba dispersa en 75+ lineas del Dashboard.
        """
        # Obtener datos de multiples fuentes
        current_prices = self.db.get_all_latest_prices()
        positions = self.portfolio.get_current_positions(current_prices)
        metrics = self._calculate_metrics(positions)
        fiscal_summary = self.get_fiscal_summary(fiscal_year)
        dividend_totals = self.get_dividend_summary(fiscal_year)

        # Devolver datos estructurados (no HTML, no widgets)
        return {
            'positions': positions,
            'metrics': metrics,
            'fiscal_summary': fiscal_summary,
            'dividend_totals': dividend_totals
        }
```

**Por que es importante:**
- Antes: Dashboard.py tenia 200+ lineas mezclando logica y UI
- Ahora: Dashboard.py tiene ~50 lineas de puro rendering
- **Testeable:** puedes probar `get_dashboard_data()` sin Streamlit

#### 3. Capa Core (Logica Pura)

**Proposito:** Calculos matematicos sin dependencias externas.

**Caracteristicas:**
- **Funciones puras** - mismo input = mismo output
- **Sin efectos secundarios** - no tocan BD, archivos, red
- **Sin dependencias** de UI, BD, o frameworks
- **Altamente testeable** - solo necesitas datos de entrada

```python
# src/core/analytics/risk.py
def calculate_volatility(
    returns: pd.Series,
    annualize: bool = True,
    periods_per_year: int = 252
) -> float:
    """
    Calcula volatilidad de una serie de retornos.

    Esta funcion NO sabe de donde vienen los retornos.
    Podrian ser de tu cartera, de un backtest, o de un test unitario.
    """
    if len(returns) < 2:
        return 0.0

    std = np.std(returns, ddof=1)

    if annualize:
        return float(std * np.sqrt(periods_per_year))
    return float(std)
```

**Por que es importante:**
- Puedes testear `calculate_volatility()` con datos inventados
- Si cambias de SQLite a PostgreSQL, **esta capa no cambia**
- Reutilizable en otros proyectos

#### 4. Capa de Datos (Repositories)

**Proposito:** Abstraer el acceso a la base de datos.

**Caracteristicas:**
- **Encapsula queries SQL** - el resto del codigo no ve SQL
- **Patron Repository** - una clase por entidad (FundRepository)
- **Facilita cambiar BD** - solo cambias el repositorio

```python
# src/data/repositories/fund_repository.py
class FundRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_isin(self, isin: str) -> Optional[Fund]:
        """El servicio no necesita saber que usamos SQLAlchemy."""
        return self.session.query(Fund).filter(Fund.isin == isin.upper()).first()

    def search(self, category: str = None, max_ter: float = None, ...) -> List[Fund]:
        """Query compleja encapsulada - el servicio solo pasa parametros."""
        query = self.session.query(Fund)

        if category:
            query = query.filter(Fund.category == category)
        if max_ter:
            query = query.filter(Fund.ter <= max_ter)

        return query.all()
```

**Por que es importante:**
- El servicio llama `repo.search(category="RV", max_ter=1.0)`
- No necesita saber si es SQL, MongoDB, o una API externa
- **Inyeccion de dependencias:** puedes pasar un mock en tests

---

## Estructura de Carpetas

```
investment_tracker/
|
|-- api/                          # API REST (FastAPI)
|   |-- __init__.py               # Exporta 'app'
|   |-- main.py                   # Endpoints, modelos Pydantic
|
|-- app/                          # UI Web (Streamlit)
|   |-- main.py                   # Punto de entrada
|   |-- pages/                    # Paginas de la app
|   |   |-- 1_Dashboard.py        # -> PortfolioService
|   |   |-- 3_Analisis.py         # -> PortfolioService (metricas)
|   |   |-- 8_Buscador_Fondos.py  # -> FundService
|   |-- components/               # Componentes reutilizables
|
|-- src/                          # Codigo fuente principal
|   |
|   |-- services/                 # CAPA DE SERVICIOS
|   |   |-- __init__.py           # Exporta servicios
|   |   |-- base.py               # BaseService (clase abstracta)
|   |   |-- portfolio_service.py  # Orquestador de cartera
|   |   |-- fund_service.py       # Orquestador de fondos
|   |
|   |-- core/                     # CAPA CORE (logica pura)
|   |   |-- analytics/
|   |   |   |-- __init__.py       # Exporta funciones
|   |   |   |-- risk.py           # volatility, var, beta, max_drawdown
|   |   |   |-- performance.py    # sharpe, sortino, alpha, cagr
|   |
|   |-- data/                     # CAPA DE DATOS
|   |   |-- __init__.py           # Exporta Database, Fund
|   |   |-- database.py           # Clase Database (SQLAlchemy)
|   |   |-- models.py             # Modelos ORM (Fund)
|   |   |-- repositories/
|   |   |   |-- fund_repository.py
|   |   |-- migrations/
|   |       |-- 001_create_funds_table.py
|   |
|   |-- portfolio.py              # Logica de cartera
|   |-- tax_calculator.py         # Calculos fiscales (FIFO)
|   |-- dividends.py              # Gestion de dividendos
|   |-- market_data.py            # Precios de mercado
|   |-- benchmarks.py             # Comparacion con indices
|   |-- exceptions.py             # Excepciones de dominio
|   |-- database.py               # [SHIM] Compatibilidad
|
|-- tests/                        # Tests (pytest)
|   |-- conftest.py               # Fixtures compartidas
|   |-- unit/
|       |-- test_analytics.py     # 32 tests
|       |-- test_fund_repository.py # 37 tests
|       |-- test_fund_service.py  # 28 tests
|       |-- test_portfolio_service.py # 41 tests
|
|-- data/                         # Datos (gitignored)
|   |-- database.db               # SQLite
|   |-- benchmark_data/
|   |-- exports/
|
|-- requirements.txt
|-- pytest.ini
|-- CLAUDE.md                     # Guia para el asistente
|-- CURRENT_SESSION.md            # Estado del proyecto
|-- IMPLEMENTATION_PLAN.md        # Plan de 8 sesiones
```

### Por que esta estructura

1. **Separacion clara de responsabilidades**
   - `api/` y `app/` son intercambiables
   - `src/services/` es el punto de entrada para cualquier interfaz
   - `src/core/` no importa nada del proyecto

2. **Imports predecibles**
   ```python
   # Siempre sabes donde esta cada cosa
   from src.services import PortfolioService, FundService
   from src.core.analytics import calculate_sharpe_ratio
   from src.data.repositories import FundRepository
   ```

3. **Escalable**
   - Nuevo servicio? -> `src/services/nuevo_service.py`
   - Nueva metrica? -> `src/core/analytics/nueva_metrica.py`
   - Nueva interfaz? -> `nueva_interfaz/` en la raiz

---

## Stack Tecnologico

| Categoria | Tecnologia | Por que |
|-----------|------------|---------|
| **Lenguaje** | Python 3.10+ | Ecosistema de data science |
| **Base de Datos** | SQLite + SQLAlchemy | Portable, sin servidor |
| **Analisis** | Pandas, NumPy | Estandar en data engineering |
| **UI Web** | Streamlit | Prototipos rapidos, sin JS |
| **API REST** | FastAPI | Moderna, async, tipada |
| **Graficos** | Plotly | Interactivos |
| **Testing** | pytest | Fixtures, parametrize |

---

## Instalacion y Configuracion

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd investment_tracker
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
source venv/Scripts/activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear tabla de fondos (primera vez)

```bash
python -m src.data.migrations.001_create_funds_table
```

### 5. Verificar instalacion

```bash
# Tests
python -m pytest tests/unit/ -v

# Imports
python -c "from src.services import PortfolioService, FundService; print('OK')"
```

---

## Uso

### Streamlit (UI Web)

```bash
streamlit run app/main.py
```

Abre http://localhost:8501 en tu navegador.

**Paginas disponibles:**
- Dashboard: Resumen de cartera
- Analisis: Metricas avanzadas (Sharpe, Beta, VaR)
- Buscador Fondos: Catalogo con filtros

### FastAPI (API REST)

```bash
uvicorn api.main:app --reload
```

**Documentacion interactiva:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Endpoints:**

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/dashboard` | Datos del dashboard |
| GET | `/dashboard/metrics` | Metricas avanzadas |
| GET | `/funds` | Buscar fondos |
| GET | `/funds/{isin}` | Detalle de fondo |
| GET | `/benchmarks` | Indices disponibles |

**Ejemplos:**

```bash
# Dashboard completo
curl http://localhost:8000/dashboard

# Metricas con benchmark
curl "http://localhost:8000/dashboard/metrics?benchmark=SP500"

# Buscar fondos baratos de renta variable
curl "http://localhost:8000/funds?category=Renta%20Variable&max_ter=0.5"
```

### Uso programatico (Python)

```python
from src.services import PortfolioService, FundService

# Context manager (recomendado) - cierra automaticamente
with PortfolioService() as service:
    data = service.get_dashboard_data(fiscal_year=2024)
    print(f"Valor total: {data['metrics']['total_value']:,.2f} EUR")

    metrics = service.get_portfolio_metrics(benchmark_name='SP500')
    print(f"Sharpe Ratio: {metrics['performance']['sharpe_ratio']:.2f}")

# Buscar fondos
with FundService() as service:
    funds = service.search_funds(
        category='Renta Variable',
        max_ter=0.5,
        min_rating=4,
        order_by='return_1y',
        order_desc=True
    )
    for fund in funds[:5]:
        print(f"{fund.name}: TER={fund.ter}%")
```

---

## Testing

### Ejecutar tests

```bash
# Todos los tests (138)
python -m pytest tests/unit/ -v

# Modo rapido
python -m pytest tests/unit/ -q

# Un archivo especifico
python -m pytest tests/unit/test_analytics.py -v

# Con coverage (si tienes pytest-cov)
python -m pytest tests/unit/ --cov=src --cov-report=html
```

### Estructura de tests

```
tests/unit/
|-- test_analytics.py         # 32 tests - Capa Core
|   |-- TestVolatility
|   |-- TestVaR
|   |-- TestBeta
|   |-- TestSharpeRatio
|   |-- ...
|
|-- test_fund_repository.py   # 37 tests - Capa Datos
|   |-- TestFundRepositoryCRUD
|   |-- TestFundRepositorySearch
|   |-- TestFundRepositoryHelpers
|
|-- test_fund_service.py      # 28 tests - Capa Servicios
|   |-- TestFundServiceSearch
|   |-- TestFundServiceHelpers
|   |-- TestFundServiceImport
|
|-- test_portfolio_service.py # 41 tests - Capa Servicios
    |-- TestFilterPositions
    |-- TestSortPositions
    |-- TestGetPortfolioMetrics
```

### Ejemplo de test (Capa Core)

```python
# tests/unit/test_analytics.py
import pytest
import pandas as pd
from src.core.analytics import calculate_volatility

class TestVolatility:
    def test_volatility_known_value(self):
        """Test con datos conocidos."""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01])
        vol = calculate_volatility(returns, annualize=False)
        assert 0.01 < vol < 0.02  # Volatilidad esperada ~1.5%

    def test_volatility_constant_returns(self):
        """Retornos constantes = volatilidad cero."""
        returns = pd.Series([0.01, 0.01, 0.01, 0.01])
        vol = calculate_volatility(returns)
        assert vol == 0.0

    def test_volatility_empty(self):
        """Serie vacia no rompe."""
        returns = pd.Series([])
        vol = calculate_volatility(returns)
        assert vol == 0.0
```

### Ejemplo de test (Capa Servicios con fixtures)

```python
# tests/conftest.py
import pytest
from src.data import Database

@pytest.fixture
def temp_db_path(tmp_path):
    """BD temporal para cada test."""
    return str(tmp_path / "test.db")

@pytest.fixture
def portfolio_service(temp_db_path):
    """Servicio con BD limpia."""
    from src.services import PortfolioService
    service = PortfolioService(db_path=temp_db_path)
    yield service
    service.close()
```

```python
# tests/unit/test_portfolio_service.py
class TestDashboardData:
    def test_get_dashboard_data_empty(self, portfolio_service):
        """Dashboard sin datos devuelve estructura valida."""
        data = portfolio_service.get_dashboard_data()

        assert 'metrics' in data
        assert 'positions' in data
        assert data['metrics']['total_value'] == 0.0
        assert data['metrics']['num_positions'] == 0
```

---

## Patrones de Diseno

### 1. Service Layer (Capa de Servicios)

**Problema:** Logica de negocio dispersa en la UI.
**Solucion:** Centralizar en clases de servicio.

```python
# ANTES (Dashboard.py con 200+ lineas mezcladas)
def render_dashboard():
    db = Database()
    prices = db.get_all_latest_prices()
    positions = portfolio.get_positions(prices)
    total = positions['market_value'].sum()
    # ... 50 lineas mas de calculos ...
    st.metric("Total", total)  # UI mezclada con logica

# DESPUES (Dashboard.py con 50 lineas de pura UI)
def render_dashboard():
    with PortfolioService() as service:
        data = service.get_dashboard_data()  # Una linea
    st.metric("Total", data['metrics']['total_value'])  # Solo UI
```

### 2. Repository Pattern

**Problema:** SQL disperso por todo el codigo.
**Solucion:** Encapsular acceso a datos en repositorios.

```python
# ANTES (SQL en el servicio)
def search_funds(self, category):
    return self.session.query(Fund).filter(Fund.category == category).all()

# DESPUES (Servicio usa repositorio)
class FundService(BaseService):
    def search_funds(self, category=None, max_ter=None):
        return self.repository.search(category=category, max_ter=max_ter)

class FundRepository:
    def search(self, category=None, max_ter=None):
        query = self.session.query(Fund)
        if category:
            query = query.filter(Fund.category == category)
        if max_ter:
            query = query.filter(Fund.ter <= max_ter)
        return query.all()
```

### 3. Dependency Injection

**Problema:** Clases crean sus propias dependencias (dificil de testear).
**Solucion:** Recibir dependencias por constructor.

```python
# ANTES (dependencia hardcodeada)
class PortfolioService:
    def __init__(self):
        self.db = Database()  # Siempre usa BD real

# DESPUES (dependencia inyectada)
class PortfolioService(BaseService):
    def __init__(self, db_path: str = None):
        super().__init__(db_path)  # Permite BD de test

# En tests:
service = PortfolioService(db_path="/tmp/test.db")
```

### 4. Context Manager Protocol

**Problema:** Olvidar cerrar conexiones causa memory leaks.
**Solucion:** Implementar `__enter__` y `__exit__`.

```python
class BaseService:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

# Uso seguro
with PortfolioService() as service:
    data = service.get_dashboard_data()
# Conexion cerrada automaticamente
```

### 5. Pure Functions (Capa Core)

**Problema:** Funciones con efectos secundarios son dificiles de testear.
**Solucion:** Funciones puras que solo dependen de sus inputs.

```python
# IMPURO (accede a BD)
def calculate_portfolio_volatility():
    db = Database()
    prices = db.get_prices()  # Efecto secundario
    returns = prices.pct_change()
    return np.std(returns)

# PURO (solo usa parametros)
def calculate_volatility(returns: pd.Series) -> float:
    """No sabe de donde vienen los returns."""
    return float(np.std(returns, ddof=1))

# El servicio obtiene los datos, core solo calcula
class PortfolioService:
    def get_volatility(self):
        returns = self._get_portfolio_returns()  # Servicio obtiene datos
        return calculate_volatility(returns)     # Core calcula
```

---

## Lecciones Aprendidas

### Por que esta arquitectura

1. **Testabilidad**
   - Antes: Imposible testear sin Streamlit corriendo
   - Ahora: 138 tests que corren en 9 segundos

2. **Mantenibilidad**
   - Antes: Cambiar un calculo requeria modificar 3 archivos
   - Ahora: Cambias `core/analytics/` y todo lo demas funciona

3. **Escalabilidad**
   - Antes: "Si quiero una API, tengo que reescribir todo"
   - Ahora: API creada en 1 sesion, reutilizando servicios existentes

4. **Onboarding**
   - Antes: Nuevo desarrollador perdido en 200 lineas de Dashboard.py
   - Ahora: "Mira, UI aqui, logica aqui, datos aqui"

### Errores que cometimos (y corregimos)

1. **Logica en UI**
   - Error: Calculos complejos en Dashboard.py
   - Solucion: Mover a PortfolioService

2. **SQL disperso**
   - Error: `session.query(Fund)` en multiples archivos
   - Solucion: FundRepository centraliza queries

3. **No cerrar conexiones**
   - Error: `db = Database()` sin `db.close()`
   - Solucion: Context managers obligatorios

4. **Tests tardios**
   - Error: Codigo escrito sin tests
   - Solucion: Sesion 3 dedicada a pytest infrastructure

### Cuando usar esta arquitectura

**SI usar si:**
- Proyecto con vida esperada > 6 meses
- Multiples interfaces (web, API, CLI)
- Equipo de > 1 persona
- Logica de negocio no trivial

**NO usar si:**
- Script unico de < 200 lineas
- Prototipo descartable
- Sin planes de escalar

---

## Comandos Utiles

```bash
# Desarrollo
streamlit run app/main.py              # UI
uvicorn api.main:app --reload          # API

# Tests
python -m pytest tests/unit/ -v        # Todos
python -m pytest tests/unit/ -q        # Rapido
python -m pytest -x                    # Parar en primer fallo

# Verificaciones
python -c "from src.services import PortfolioService; print('OK')"
python -c "from api.main import app; print(app.title)"

# Git
git log --oneline -10                  # Ultimos commits
git diff --stat HEAD~1                 # Cambios ultimo commit

# Base de datos
python -m src.data.migrations.001_create_funds_table
```

---

## Contribuir

1. Lee `CLAUDE.md` para convenciones
2. Crea rama desde `main`
3. Escribe tests para codigo nuevo
4. Asegurate que `pytest` pasa
5. Crea PR con descripcion clara

---

## Licencia

Proyecto personal con fines educativos.

---

**Desarrollado en 8 sesiones siguiendo principios de Clean Architecture.**
