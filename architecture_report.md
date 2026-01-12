📊 Informe de Arquitectura: Investment Tracker
Resumen Ejecutivo
El proyecto investment_tracker es una aplicación de gestión de carteras de inversión con arquitectura de 3 capas bien definida. Tiene buenas bases pero presenta deuda técnica significativa que limitará la escalabilidad para los objetivos futuros (APIs externas, métricas avanzadas, servidor cliente).

Aspecto	Estado	Puntuación
Separación de capas	✅ Buena	7/10
Escalabilidad actual	⚠️ Limitada	5/10
Testing	⚠️ Básico	4/10
Preparación para APIs	❌ No preparado	3/10
Documentación	✅ Aceptable	6/10
1. Estado Actual del Proyecto
1.1 Arquitectura de Capas
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTACIÓN (app/)                       │
│  main.py + 7 páginas Streamlit + 3 componentes              │
│  ~125 KB total                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      NEGOCIO (src/)                          │
│  portfolio.py (43KB) | tax_calculator.py (50KB)             │
│  dividends.py (39KB) | benchmarks.py (52KB)                 │
│  market_data.py (26KB) | data_loader.py (19KB)              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       DATOS (src/)                           │
│  database.py (33KB) - SQLite + SQLAlchemy                   │
│  4 modelos: Transaction, Dividend, BenchmarkData, AssetPrice│
└─────────────────────────────────────────────────────────────┘
1.2 Métricas de Código
Módulo	Líneas	Métodos/Funciones	Complejidad
portfolio.py
1,079	27	🔴 Alta
database.py
935	43	🔴 Alta
tax_calculator.py
~1,200	~30	🔴 Alta
benchmarks.py
~1,400	~35	🔴 Alta
market_data.py
704	19	🟡 Media
WARNING

Archivos con más de 500 líneas son difíciles de mantener. Todos los módulos core superan este límite.

2. Principales Fallos de Construcción
2.1 🔴 Módulos Monolíticos (Prioridad Alta)
Problema: Cada archivo de src/ contiene una sola clase "God Object" con demasiadas responsabilidades.

Ejemplo en 
portfolio.py
:

Gestión de posiciones
Cálculo de plusvalías latentes
Rentabilidades históricas
Flujos de capital
Lotes FIFO/LIFO
Impacto:

Difícil de testear unitariamente
Cambios pequeños pueden romper múltiples funcionalidades
No podrás añadir métricas (Sharpe, Beta) sin inflar más el archivo
2.2 🔴 Ausencia de Interfaces/Abstracciones (Prioridad Alta)
Problema: No hay interfaces (Protocol o clases abstractas) que definan contratos.

# ❌ Actual: acoplamiento directo
class MarketDataManager:
    def __init__(self):
        self.db = Database()  # Dependencia concreta
# ✅ Debería ser:
class IMarketDataProvider(Protocol):
    def get_prices(self, ticker: str, start: date, end: date) -> pd.DataFrame: ...
class YahooFinanceProvider(IMarketDataProvider):
    # Implementación específica
class MarketDataManager:
    def __init__(self, provider: IMarketDataProvider):  # Inyección
        self.provider = provider
Impacto:

Imposible cambiar de Yahoo Finance a otra API sin modificar código existente
No puedes mockear fácilmente para tests
Bloquea la integración con APIs de precios en tiempo real
2.3 🔴 Testing Deficiente (Prioridad Alta)
Problemas encontrados:

Carpeta tests/ está vacía
Tests de integración en raíz (7 archivos test_*.py)
No usa pytest correctamente (implementación manual de contadores)
No hay fixtures de base de datos
No hay tests unitarios
# ❌ Patrón actual (test_portfolio.py)
def run_tests():
    tests_passed = 0
    # ... muy procedural
# ✅ Debería usar pytest
@pytest.fixture
def portfolio(tmp_path):
    return Portfolio(db_path=tmp_path / "test.db")
def test_get_positions_empty(portfolio):
    assert portfolio.get_current_positions().empty
2.4 🟡 Configuración Hardcodeada (Prioridad Media)
Problema: 
config.py
 usa valores hardcodeados sin soporte para diferentes entornos.

# ❌ Actual
DEBUG = True  # Cambiar a False en producción (comentario inútil)
DATABASE_PATH = DATA_DIR / 'database.db'
# ✅ Debería usar variables de entorno
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / 'database.db')))
Impacto: No puedes tener BD de producción separada de desarrollo.

2.5 🟡 Imports con Try/Except (Prioridad Media)
try:
    from src.database import Database
except ImportError:
    from database import Database
Problema: Esto indica que el proyecto no tiene un sistema de empaquetado correcto. Deberías poder importar siempre con from investment_tracker.src.database.

2.6 🟡 Sin Manejo de Errores Estructurado (Prioridad Media)
No hay excepciones personalizadas. Todas las funciones pueden fallar con excepciones genéricas.

# ✅ Debería existir
class TickerNotFoundError(Exception): ...
class InsufficientSharesError(Exception): ...
class InvalidTransactionError(Exception): ...
3. Análisis de Escalabilidad para Objetivos Futuros
3.1 Métricas Avanzadas (Sharpe, Beta, Correlaciones)
Preparación	Descripción
🟡 Parcial	Ya tienes 
market_data.py
 con precios históricos
❌ Falta	No hay módulo de cálculo estadístico separado
❌ Falta	Sin matrices de correlación
Recomendación: Crear src/analytics/ con:

risk_metrics.py - Beta, volatilidad, VaR
performance_metrics.py - Sharpe, Sortino, Alpha
correlation.py - Matrices de correlación
3.2 APIs de Precios en Tiempo Real
Preparación	Descripción
❌ No preparado	
MarketDataManager
 acoplado a Yahoo Finance
❌ No preparado	Sin sistema de caché con TTL
❌ No preparado	Sin rate limiting para APIs
Arquitectura necesaria:

src/
├── providers/
│   ├── base.py          # IMarketDataProvider (interfaz)
│   ├── yahoo.py         # YahooProvider
│   ├── alpha_vantage.py # AlphaVantageProvider
│   └── morningstar.py   # MorningstarProvider
├── cache/
│   ├── memory_cache.py  # Cache en memoria con TTL
│   └── db_cache.py      # Cache persistente
3.3 Generación de Documentación Automática
Preparación	Descripción
❌ No preparado	Sin sistema de templates
❌ No preparado	Sin exportación a PDF
🟡 Parcial	Ya exportas a Excel (data/exports/)
Recomendación:

Usar jinja2 para templates HTML
weasyprint o reportlab para PDF
Crear src/reports/ con generadores
3.4 Servidor Web para Clientes
Preparación	Descripción
❌ No preparado	Streamlit no es adecuado para multi-usuario
❌ No preparado	Sin autenticación
❌ No preparado	Sin API REST
Migración necesaria:

# Streamlit → FastAPI + Frontend
src/
├── api/
│   ├── routes/
│   │   ├── portfolio.py
│   │   ├── auth.py
│   │   └── reports.py
│   ├── auth/
│   │   ├── jwt.py
│   │   └── permissions.py
│   └── main.py
CAUTION

Streamlit es excelente para prototipos pero no escalable para múltiples clientes con acceso restringido. Necesitarás migrar a FastAPI + React/Vue eventualmente.

4. Plan de Mejoras Recomendado
Fase 1: Estabilización (2-3 semanas)
Reestructurar testing

Mover tests a tests/ con estructura pytest
Añadir fixtures de BD en memoria
Cobertura mínima 60%
Configuración por entornos

.env files para dev/prod
Variables de entorno para rutas sensibles
Excepciones personalizadas

Crear src/exceptions.py
Fase 2: Refactorización (3-4 semanas)
Dividir módulos monolíticos

src/
├── portfolio/
│   ├── positions.py
│   ├── returns.py
│   ├── lots.py
│   └── service.py  # Orquestador
├── analytics/
│   ├── risk.py
│   └── performance.py
Introducir interfaces

IMarketDataProvider
IReportGenerator
IDataExporter
Sistema de plugins para proveedores de datos

Fase 3: Nuevas Funcionalidades (4-6 semanas)
Métricas avanzadas

Sharpe, Sortino, Beta, Alpha
Correlaciones entre activos
Múltiples proveedores de datos

Alpha Vantage (gratuito, 5 calls/min)
Morningstar (para fondos)
Generador de informes PDF

Fase 4: Multi-Cliente (8-12 semanas)
Migrar backend a FastAPI
Sistema de autenticación JWT
Base de datos multi-tenant (PostgreSQL)
Frontend separado (opcional: mantener Streamlit para admin)
5. Estructura de Carpetas Propuesta
investment_tracker/
├── src/
│   ├── core/                    # [NUEVO] Lógica central
│   │   ├── portfolio/
│   │   ├── tax/
│   │   └── dividends/
│   ├── analytics/               # [NUEVO] Métricas
│   │   ├── risk.py
│   │   ├── performance.py
│   │   └── correlation.py
│   ├── providers/               # [NUEVO] Proveedores externos
│   │   ├── base.py
│   │   ├── yahoo.py
│   │   └── morningstar.py
│   ├── reports/                 # [NUEVO] Generación documentos
│   │   ├── templates/
│   │   └── generators/
│   ├── data/                    # [RENOMBRAR de database.py]
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── migrations/
│   └── exceptions.py            # [NUEVO]
├── api/                         # [NUEVO] FastAPI
│   ├── routes/
│   ├── auth/
│   └── main.py
├── app/                         # Streamlit (mantener para admin)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
│   ├── settings.py
│   └── .env.example
└── docs/
    ├── api/
    └── user_guide/
6. Conclusiones
Lo que está bien ✅
Arquitectura de 3 capas correctamente separada
Uso de SQLAlchemy con modelos definidos
Sistema de logging existente
Soporte multi-divisa
Integración con Yahoo Finance funcional
Lo que necesita mejora urgente ⚠️
Testing estructurado con pytest
Romper módulos monolíticos
Interfaces para proveedores externos
Configuración por entornos
Bloqueantes para objetivos futuros 🚫
Sin abstracciones → No podrás añadir nuevas APIs fácilmente
Streamlit → No escala para clientes múltiples
Sin autenticación → No puedes exponer servicios
IMPORTANT

Recomendación principal: Antes de añadir nuevas funcionalidades (Sharpe, APIs, informes), invierte 2-3 sprints en preparar la infraestructura. La deuda técnica actual multiplicará el coste de cada nueva feature si no se aborda primero.

🎯 La Clave: Separar el "Core" de la "Interfaz"
┌─────────────────────────────────────────────────────────────────┐
│                         INTERFACES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Streamlit  │  │   FastAPI   │  │  CLI / Scripts batch   │  │
│  │   (ahora)   │  │  (futuro)   │  │      (testing)         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                             │
│         (PortfolioService, ReportService, etc.)                  │
│         Esta capa NO conoce ni Streamlit ni FastAPI              │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CORE                                     │
│    Portfolio | TaxCalculator | Analytics | Providers             │
└─────────────────────────────────────────────────────────────────┘
✅ Cómo Lograrlo con Tu Proyecto Actual
Paso 1: Crear una Capa de Servicios (la pieza que falta)
python
# src/services/portfolio_service.py
class PortfolioService:
    """
    Orquestador que NO conoce la UI.
    Streamlit y FastAPI llaman a esta clase.
    """
    def __init__(self, db_path: str = None):
        self.portfolio = Portfolio(db_path)
        self.market_data = MarketDataManager(db_path)
    
    def get_dashboard_data(self) -> dict:
        """Retorna datos estructurados, no DataFrames de Streamlit"""
        positions = self.portfolio.get_current_positions()
        return {
            "positions": positions.to_dict('records'),
            "total_value": self.portfolio.get_total_value(),
            "unrealized_gains": self.portfolio.get_unrealized_gains()
        }
    
    def get_portfolio_metrics(self) -> dict:
        """Sharpe, Beta, etc."""
        return {
            "sharpe": self.analytics.calculate_sharpe(),
            "beta": self.analytics.calculate_beta()
        }
Paso 2: Streamlit Consume el Servicio
python
# app/pages/1_Dashboard.py (AHORA)
from src.services.portfolio_service import PortfolioService
service = PortfolioService()
data = service.get_dashboard_data()
# Streamlit solo renderiza
st.metric("Valor Total", f"€{data['total_value']:,.2f}")
st.dataframe(pd.DataFrame(data['positions']))
Paso 3: FastAPI Consume EL MISMO Servicio
python
# api/routes/portfolio.py (FUTURO - sin cambiar el core)
from src.services.portfolio_service import PortfolioService
router = APIRouter()
service = PortfolioService()
@router.get("/dashboard")
def get_dashboard():
    return service.get_dashboard_data()  # ¡Mismo método!
@router.get("/metrics")
def get_metrics():
    return service.get_portfolio_metrics()
📊 Comparativa de Enfoques
Aspecto	❌ Sin capa de servicios	✅ Con capa de servicios
Migrar a FastAPI	Reescribir lógica	Solo añadir rutas
Testing	Difícil (depende de UI)	Fácil (testeas servicios)
Desarrollo	Rápido inicialmente	20% más lento al inicio
Mantenimiento	Código duplicado	Un solo lugar
🛠️ Estructura Propuesta (Compatible Streamlit → FastAPI)
investment_tracker/
├── src/
│   ├── core/                    # Lógica pura (ya existe, reorganizar)
│   │   ├── portfolio.py
│   │   ├── tax_calculator.py
│   │   └── analytics/
│   ├── providers/               # APIs externas
│   │   ├── base.py              # Interfaz
│   │   └── yahoo.py
│   ├── services/                # [NUEVO] Orquestadores
│   │   ├── portfolio_service.py
│   │   ├── report_service.py
│   │   └── auth_service.py      # Preparado para autenticación
│   └── data/
│       ├── models.py
│       └── repository.py
│
├── app/                         # Streamlit (desarrollo personal)
│   └── pages/
│
├── api/                         # [FUTURO] FastAPI
│   ├── routes/
│   ├── auth/
│   └── main.py
│
└── tests/
    ├── unit/
    └── integration/
⏱️ Esfuerzo de Migración con Esta Arquitectura
Fase	Descripción	Tiempo
Ahora	Crear services/ + refactorizar Streamlit para usarlos	2-3 semanas
Desarrollo	Nuevas features siempre en services/, UI solo renderiza	Continuo
Migración	Añadir FastAPI consumiendo services/	1-2 semanas
Producción	Autenticación + despliegue AWS/Azure	2-3 semanas