# 🚀 Investment Tracker - Prompt de Contexto para Nueva Conversación

## INSTRUCCIONES PARA CLAUDE

Este documento contiene todo el contexto necesario para continuar el desarrollo del proyecto Investment Tracker. Lee este documento completo antes de comenzar a implementar cualquier mejora.

---

## 1. RESUMEN DEL PROYECTO

**Investment Tracker** es un sistema personal de gestión de carteras de inversión desarrollado en Python con interfaz web Streamlit. Permite:

- Registrar operaciones financieras (compras, ventas, dividendos, traspasos)
- Calcular rentabilidades y plusvalías latentes/realizadas
- Generar informes fiscales según normativa española (FIFO, regla 2 meses)
- Comparar rendimiento con benchmarks (S&P 500, IBEX 35, etc.)
- Descargar precios de mercado reales desde Yahoo Finance

**Estado actual:** Funcional y operativo con sistema de logging implementado.

---

## 2. STACK TECNOLÓGICO

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| Lenguaje | Python 3.10+ | Core de la aplicación |
| Base de datos | SQLite + SQLAlchemy | Persistencia local |
| Frontend | Streamlit | Interfaz web |
| Gráficos | Plotly | Visualizaciones interactivas |
| Datos financieros | yfinance | Precios de mercado |
| Análisis | Pandas + NumPy | Cálculos financieros |

---

## 3. ARQUITECTURA DE 3 CAPAS

```
┌─────────────────────────────────────────────────────────────┐
│                 CAPA DE PRESENTACIÓN                        │
│                    (app/pages/*.py)                         │
│         Streamlit UI - Solo muestra datos y recibe input    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE NEGOCIO                           │
│                      (src/*.py)                             │
│   portfolio.py, tax_calculator.py, benchmarks.py, etc.      │
│              Toda la lógica financiera aquí                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                            │
│                  (src/database.py)                          │
│         SQLAlchemy ORM - Única puerta a la BD               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. ESTRUCTURA DE CARPETAS

```
investment_tracker/
│
├── 📁 src/                           # CAPA DE NEGOCIO + DATOS
│   ├── __init__.py
│   ├── logger.py                     # Sistema de logging centralizado
│   ├── database.py                   # Modelos SQLAlchemy + clase Database (CRUD)
│   ├── portfolio.py                  # Cálculos de cartera y rentabilidad
│   ├── tax_calculator.py             # Cálculos fiscales (FIFO/LIFO, plusvalías)
│   ├── dividends.py                  # Gestión de dividendos
│   ├── benchmarks.py                 # Comparación con índices
│   ├── market_data.py                # Descarga precios Yahoo Finance
│   ├── data_loader.py                # Importar/exportar CSV
│   └── utils.py                      # Funciones auxiliares
│
├── 📁 app/                           # CAPA DE PRESENTACIÓN
│   ├── main.py                       # Punto de entrada Streamlit
│   └── pages/                        # Páginas de la app
│       ├── 1_📊_Dashboard.py         # Vista general de cartera
│       ├── 2_➕_Añadir_Operación.py  # Formulario registro operaciones
│       ├── 3_📈_Análisis.py          # Análisis detallado
│       ├── 4_💰_Fiscal.py            # Información fiscal
│       ├── 5_💵_Dividendos.py        # Tracking de dividendos
│       └── 6_🎯_Benchmarks.py        # Comparación con índices
│
├── 📁 data/                          # ALMACENAMIENTO
│   ├── database.db                   # Base de datos SQLite
│   ├── benchmark_data/               # Datos de índices
│   └── exports/                      # Informes generados
│
├── 📁 logs/                          # Archivos de log
│   └── investment_tracker.log
│
├── 📁 docs/                          # Documentación
│   └── GUIA_LOGGING.md
│
├── config.py                         # Configuración global
├── requirements.txt                  # Dependencias
├── .gitignore                        # Archivos ignorados
└── README.md                         # Documentación principal
```

---

## 5. MODELOS DE BASE DE DATOS (SQLAlchemy)

### Transaction (transacciones)
```python
class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    type = Column(String(20))          # 'buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'
    ticker = Column(String(50))
    name = Column(String(200))         # Nombre del activo
    asset_type = Column(String(50))    # 'accion', 'fondo', 'etf'
    quantity = Column(Float)
    price = Column(Float)
    commission = Column(Float, default=0)
    total = Column(Float)
    currency = Column(String(10), default='EUR')
    market = Column(String(20))
    realized_gain_eur = Column(Float)  # B/P en ventas
    cost_basis_eur = Column(Float)     # Coste fiscal (traspasos)
    transfer_link_id = Column(Integer) # Vincular traspasos
    notes = Column(Text)
    created_at = Column(DateTime)
```

### Dividend (dividendos)
```python
class Dividend(Base):
    __tablename__ = 'dividends'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(50))
    date = Column(Date)
    gross_amount = Column(Float)       # Bruto
    net_amount = Column(Float)         # Neto (después de retención)
    withholding_tax = Column(Float)    # Retención
    currency = Column(String(10))
    notes = Column(Text)
```

### BenchmarkData (datos de índices)
```python
class BenchmarkData(Base):
    __tablename__ = 'benchmark_data'
    id = Column(Integer, primary_key=True)
    benchmark_name = Column(String(50))
    date = Column(Date)
    value = Column(Float)
```

### AssetPrice (precios de activos)
```python
class AssetPrice(Base):
    __tablename__ = 'asset_prices'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(50))
    date = Column(Date)
    close_price = Column(Float)
    adj_close_price = Column(Float)
```

---

## 6. MÉTODOS PRINCIPALES DE CADA MÓDULO

### database.py - Database
```python
# Transacciones
add_transaction(data: Dict) -> int
get_transactions(ticker, type, year, ...) -> List[Transaction]
get_transaction_by_id(id) -> Transaction
update_transaction(id, data) -> bool
delete_transaction(id) -> bool
transactions_to_dataframe(trans) -> DataFrame

# Dividendos
add_dividend(data) -> int
get_dividends(ticker, year) -> List[Dividend]
update_dividend(id, data) -> bool
delete_dividend(id) -> bool

# Precios
add_asset_price(ticker, date, close, adj_close)
get_asset_prices(ticker, start, end) -> List[AssetPrice]
get_all_latest_prices() -> Dict[str, float]

# Benchmarks
add_benchmark_data(name, date, value)
get_benchmark_data(name, start, end) -> List[BenchmarkData]
get_available_benchmarks() -> List[str]
```

### portfolio.py - Portfolio
```python
get_current_positions(asset_type, include_zero, current_prices) -> DataFrame
get_total_value() -> float
get_total_cost() -> float
get_unrealized_gains() -> float
get_performance_by_asset() -> DataFrame
get_allocation() -> DataFrame
```

### tax_calculator.py - TaxCalculator
```python
__init__(method='FIFO')  # o 'LIFO'

get_available_lots(ticker) -> List[Dict]
get_all_available_lots() -> DataFrame
calculate_sale_gain(ticker, qty, price) -> Dict
get_fiscal_year_summary(year) -> Dict
get_fiscal_year_detail(year) -> DataFrame
calculate_tax(taxable_base) -> Dict
simulate_sale(ticker, qty, price) -> Dict
get_wash_sales_in_year(year) -> DataFrame
export_fiscal_report(year, filepath)
```

### market_data.py - MarketDataManager
```python
get_portfolio_tickers() -> List[Dict]
download_ticker_prices(ticker, start, end) -> DataFrame
download_portfolio_prices(start, end) -> Dict
get_ticker_prices(ticker, start, end) -> DataFrame
get_portfolio_market_value_series(start, end) -> DataFrame
clear_price_cache()
```

### benchmarks.py - BenchmarkComparator
```python
download_benchmark(name, start, end) -> int
get_available_benchmarks() -> List[Dict]
compare_to_benchmark(name, start, end) -> DataFrame
calculate_relative_performance(name, start, end) -> Dict
calculate_risk_metrics(name, start, end, risk_free_rate) -> Dict
```

---

## 7. SISTEMA DE LOGGING

El proyecto tiene un sistema de logging centralizado en `src/logger.py`:

```python
from src.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detalles técnicos")
logger.info("Operación completada")
logger.warning("Algo inusual")
logger.error("Error manejable")
logger.critical("Error fatal")
```

Los logs se guardan en:
- Consola (con colores)
- Archivo `logs/investment_tracker.log` (rotativo, máx 5MB)

---

## 8. CARACTERÍSTICAS FISCALES ESPAÑOLAS

El sistema implementa la normativa fiscal española:

1. **FIFO obligatorio**: Las acciones más antiguas se venden primero
2. **Regla de los 2 meses**: Minusvalías no deducibles si recompras en 2 meses
3. **Traspasos entre fondos**: No generan fiscalidad, el coste fiscal se transfiere
4. **Tramos IRPF del ahorro 2024/2025**:
   - Hasta 6.000€: 19%
   - 6.000€ - 50.000€: 21%
   - 50.000€ - 200.000€: 23%
   - 200.000€ - 300.000€: 27%
   - Más de 300.000€: 28%

---

## 9. PRÓXIMAS MEJORAS A IMPLEMENTAR

### 9.1 Página de Configuración/Settings (NUEVA)

Crear una nueva página `7_⚙️_Configuración.py` que permita:

1. **Configuración fiscal:**
   - Seleccionar método por defecto (FIFO vs LIFO)
   - Configurar año fiscal activo

2. **Gestión de activos:**
   - Ver/editar lista de tickers y sus nombres
   - Configurar tipo de activo (acción, fondo, ETF)
   - Configurar divisa y mercado por defecto

3. **Preferencias de visualización:**
   - Divisa principal para mostrar totales
   - Número de decimales
   - Tema (si Streamlit lo permite)

4. **Información del sistema:**
   - Ver últimas entradas del log
   - Estadísticas de la base de datos
   - Versión de la aplicación

### 9.2 Mejoras en "Añadir Operación" (EXISTENTE)

Mejorar la página `2_➕_Añadir_Operación.py` para incluir:

1. **Listado de operaciones:**
   - Tabla con TODAS las operaciones (paginada si hay muchas)
   - Filtros por tipo (compra/venta/dividendo/traspaso)
   - Filtros por ticker y fecha
   - Ordenación por columnas

2. **Edición de operaciones:**
   - Botón "Editar" en cada fila
   - Modal/formulario para modificar:
     - Fecha
     - Cantidad
     - Precio
     - Comisión
     - Notas
   - Validación antes de guardar

3. **Eliminación de operaciones:**
   - Botón "Eliminar" en cada fila
   - Confirmación antes de eliminar
   - Mensaje de éxito/error

4. **UX mejorada:**
   - Feedback visual al añadir/editar/eliminar
   - Actualización automática de la tabla
   - Indicador de operaciones recientes

---

## 10. NOTAS TÉCNICAS IMPORTANTES

### Imports en los módulos src/
```python
# Patrón para que funcione tanto desde src/ como desde app/
try:
    from src.database import Database
    from src.logger import get_logger
except ImportError:
    from database import Database
    from logger import get_logger
```

### Uso de precios de mercado
```python
# Para obtener ganancias latentes reales:
db = Database()
current_prices = db.get_all_latest_prices()
positions = portfolio.get_current_positions(current_prices=current_prices)
```

### Session state en Streamlit
```python
# Para mantener estado entre recargas:
if 'variable' not in st.session_state:
    st.session_state.variable = valor_inicial

# Para forzar recarga:
st.rerun()
```

---

## 11. DEPENDENCIAS (requirements.txt)

```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
sqlalchemy>=2.0.0
plotly>=5.15.0
yfinance>=0.2.28
openpyxl>=3.1.0
```

---

## 12. CÓMO EJECUTAR

```bash
# Desde la carpeta investment_tracker/
streamlit run app/main.py

# La app se abre en http://localhost:8501
```

---

## 13. CONTEXTO DEL USUARIO

El usuario es un PhD en Astrofísica con experiencia programando en Python pero sin experiencia en desarrollo de proyectos de software. Está aprendiendo a pensar como un senior developer a través de este proyecto. Prefiere explicaciones detalladas del "por qué" de las decisiones técnicas.

---

## 14. ESTILO DE CÓDIGO

- Docstrings en español
- Type hints donde sea posible
- Logging en operaciones importantes
- Comentarios explicativos para lógica compleja
- Separación clara entre capas

---

## FIN DEL CONTEXTO

Con este documento tienes todo lo necesario para continuar el desarrollo. Las próximas tareas son:

1. **Crear página de Configuración** (`7_⚙️_Configuración.py`)
2. **Mejorar "Añadir Operación"** con listado, edición y eliminación de operaciones
