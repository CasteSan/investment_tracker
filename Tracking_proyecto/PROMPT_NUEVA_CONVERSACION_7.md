# =============================================================================
# PROMPT PARA CONTINUAR EL PROYECTO EN NUEVA CONVERSACIÓN
# Actualizado después de Sesión 7 (Streamlit UI) - PROYECTO COMPLETADO
# =============================================================================
# Copia y pega esto al inicio de una nueva conversación con Claude.
# Adjunta también: commits anteriores, el documento de Notion si lo tienes.
# =============================================================================

## 🎯 PROYECTO: Investment Tracker - Sistema de Gestión de Cartera Personal

Estoy desarrollando un sistema completo de gestión y análisis de inversiones personales en Python. El proyecto está en desarrollo activo y necesito tu ayuda para continuar implementando módulos.

### 📋 OBJETIVO
Sistema local (Windows + VSCode) para:
- Registrar operaciones financieras (compras, ventas, traspasos, dividendos)
- Calcular rentabilidades (total, por activo, histórica)
- Generar informes fiscales (plusvalías FIFO para declaración de renta española)
- Comparar rendimiento con benchmarks (IBEX, S&P 500, etc.)

### 🛠️ STACK TECNOLÓGICO
- **Python 3.10+** con entorno virtual
- **SQLite** + **SQLAlchemy** para base de datos
- **Pandas** para análisis de datos
- **openpyxl** para exportación Excel
- **Streamlit** (futuro) para interfaz web
- **Plotly** (futuro) para gráficos

### 📁 ESTRUCTURA ACTUAL DEL PROYECTO

```
investment_tracker/
├── data/
│   ├── database.db                 # Base de datos SQLite
│   ├── mi_portfolio_investing.csv  # CSV exportado de Investing.com
│   └── exports/                    # Informes generados
│       ├── informe_fiscal_2025.xlsx
│       ├── dividends_2025.xlsx
│       └── benchmark_analysis.xlsx
├── src/
│   ├── __init__.py
│   ├── database.py                 # ✅ v3 - Modelos + CRUD completo
│   ├── data_loader.py              # ✅ Importador CSV/Excel
│   ├── portfolio.py                # ✅ Análisis de cartera (~700 líneas)
│   ├── tax_calculator.py           # ✅ Cálculos fiscales (~750 líneas)
│   ├── dividends.py                # ✅ Gestión dividendos (~700 líneas)
│   └── benchmarks.py               # ✅ Comparación con índices (~850 líneas)
├── app/                            # ✅ Interfaz Streamlit
│   ├── main.py                     # Página principal
│   ├── pages/
│   │   ├── 1_📊_Dashboard.py       # Vista general cartera
│   │   ├── 2_➕_Añadir_Operación.py # Formularios
│   │   ├── 3_📈_Análisis.py        # Análisis detallado
│   │   ├── 4_💰_Fiscal.py          # Información fiscal
│   │   ├── 5_💵_Dividendos.py      # Tracking dividendos
│   │   └── 6_🎯_Benchmarks.py      # Comparación índices
│   └── components/
│       ├── charts.py               # Gráficos Plotly
│       ├── tables.py               # Tablas formateadas
│       └── metrics.py              # Tarjetas de KPIs
├── scripts/
│   └── convert_investing_csv.py    # ✅ Conversor de Investing.com
├── test_portfolio.py               # ✅ Tests del módulo portfolio
├── test_tax_calculator.py          # ✅ Tests del módulo fiscal
├── test_dividends.py               # ✅ Tests del módulo dividendos
├── test_benchmarks.py              # ✅ Tests del módulo benchmarks
├── config.py                       # Configuración global
└── requirements.txt
```

### ✅ MÓDULOS COMPLETADOS

#### Sesión 1: Database Module (`src/database.py` - v3)
- Modelos SQLAlchemy: Transaction, Dividend, BenchmarkData, PortfolioSnapshot
- Campos especiales: `currency`, `market`, `realized_gain_eur`, `unrealized_gain_eur`
- CRUD completo para transacciones y dividendos
- Métodos: `get_dividend_by_id()`, `update_dividend()` (añadidos en v3)

#### Sesión 2: Data Loader (`src/data_loader.py`)
- Importación desde CSV/Excel
- Validación de datos
- Mapeo flexible de columnas
- Soporte para campos multi-divisa

#### Sesión 2.5: Conversor Investing.com (`scripts/convert_investing_csv.py`)
- Parsea CSV exportado de Investing.com (formato español)
- Extrae "B/P neto" ya convertido a EUR (evita errores de divisa)
- Detecta tipo de activo (accion, fondo, etf)
- Detecta divisa según mercado (LON=GBX, NYSE=USD, etc.)

#### Sesión 3: Portfolio Module (`src/portfolio.py`)
- ~700 líneas de código
- Posiciones actuales con cálculo FIFO
- Plusvalías latentes y realizadas
- Rentabilidad total y por activo (usa cost_basis de posiciones actuales, no histórico)
- Distribución de cartera
- Usa `realized_gain_eur` para B/P correcta en cualquier divisa
- Muestra nombres de activos (`display_name`) en lugar de tickers

#### Sesión 4: Tax Calculator (`src/tax_calculator.py`)
- ~750 líneas de código
- Gestión de lotes (FIFO por defecto, LIFO configurable)
- Cálculo de plusvalías por venta
- **Regla de los 2 meses** (antiaplicación): detecta pérdidas no deducibles
- **Tramos IRPF del ahorro** España (19%, 21%, 23%, 27%, 28%)
- Simulación de ventas (ver impacto fiscal antes de vender)
- Exportación a Excel con 6 hojas
- Funciones: `print_fiscal_summary()`, `print_simulation()`, `print_available_lots()`

#### Sesión 5: Dividends Module (`src/dividends.py`)
- ~700 líneas de código
- CRUD completo de dividendos con soporte para fecha ex-dividendo
- **Yield on Cost (YOC)**: Por activo y cartera completa
- **Calendario**: Dividendos por mes, proyección anual
- **Frecuencia**: Detecta si es mensual, trimestral, semestral, anual
- **Integración**: `get_total_return_with_dividends()` para rentabilidad total
- Exportación a Excel
- Funciones: `print_dividend_summary()`, `print_dividend_calendar()`, `print_yield_analysis()`
- Datos de ejemplo: `create_example_dividends()` con TEF, BBVA, IBE, SAN, ITX, AAPL

#### Sesión 6: Benchmarks Module (`src/benchmarks.py`)
- ~850 líneas de código
- **Descarga automática** de datos con yfinance (SP500, IBEX35, MSCI World, etc.)
- **Normalización base 100** para comparar visualmente
- **Rendimientos**: Total, anualizado, outperformance
- **Métricas de riesgo**: Volatilidad, Beta, Alpha, Tracking Error
- **Ratios ajustados**: Sharpe, Sortino, Calmar, Information Ratio
- **Max Drawdown**: Máxima caída con fechas de pico/valle/recuperación
- **Value at Risk (VaR)**: Pérdida máxima con 95% de confianza
- Exportación a Excel con 3 hojas
- Funciones: `print_comparison_summary()`, `print_risk_metrics()`

#### Sesión 7: Streamlit UI (`app/`)
- ~3,000 líneas de código total
- **6 páginas interactivas**:
  - 📊 Dashboard: Métricas, distribución, top performers
  - ➕ Añadir Operación: Formularios compra/venta/dividendo/traspaso
  - 📈 Análisis: Rentabilidad por activo, filtros, estadísticas
  - 💰 Fiscal: Plusvalías, simulador de venta, lotes FIFO
  - 💵 Dividendos: Calendario, YOC, proyecciones
  - 🎯 Benchmarks: Comparación con índices, métricas de riesgo
- **Componentes reutilizables**: charts.py, tables.py, metrics.py
- Gráficos interactivos con Plotly
- Exportación a CSV y Excel desde la UI

### 🔄 FLUJO DE TRABAJO ACTUAL

```bash
# 1. Exportar CSV de Investing.com (Portfolio → Exportar)

# 2. Convertir a formato interno
python scripts/convert_investing_csv.py data/mi_portfolio_investing.csv

# 3. Importar a base de datos (si la DB es nueva)
del data\database.db  # Solo si hay cambios de esquema
python -c "from src.data_loader import DataLoader; dl = DataLoader(); print(dl.import_from_csv('data/investing_converted_XXX.csv')); dl.close()"

# 4. Ejecutar interfaz web (RECOMENDADO)
streamlit run app/main.py

# --- O usar módulos por terminal ---

# Analizar cartera
python test_portfolio.py

# Ver fiscalidad
python test_tax_calculator.py

# Ver dividendos
python test_dividends.py demo

# Comparar con benchmarks
python test_benchmarks.py demo
```

### 🐛 BUGS YA CORREGIDOS (no repetir)
1. **Tullow Oil -12,420€ → -143€**: Precios en GBX (peniques) se trataban como EUR. Solucionado usando "B/P neto" del CSV.
2. **Total invertido 95K → 33K**: Sumaba todas las compras históricas. Ahora solo suma el coste de posiciones actuales.
3. **Tickers crípticos**: Añadido `display_name` para mostrar nombres legibles.

### 📊 ESTADO ACTUAL DE MI CARTERA (para contexto)
- ~25 posiciones activas
- Divisas: EUR (mayoría), USD, GBX, CAD
- Mercados: BME, NYSE, NASDAQ, LON, BIT, ETR, EPA, LU, IR, TSXV
- Tipos: fondos (72%), acciones (25%), ETFs (3%)
- Valor actual: ~33,000€
- Plusvalías realizadas 2025: ~-1,100€ (mayoría pérdidas)

### 📋 ESTADO: PROYECTO COMPLETADO ✅

El sistema Investment Tracker está funcionalmente completo con todas las sesiones implementadas:
- ✅ Sesión 1: Database (modelos, CRUD)
- ✅ Sesión 2: Data Loader (importación CSV/Excel)
- ✅ Sesión 3: Portfolio (análisis de cartera)
- ✅ Sesión 4: Tax Calculator (fiscalidad española)
- ✅ Sesión 5: Dividends (tracking, yields)
- ✅ Sesión 6: Benchmarks (comparación con índices)
- ✅ Sesión 7: Streamlit UI (interfaz web)

**Total: ~7,500 líneas de código Python**

### 🚀 CÓMO EJECUTAR

```bash
# Activar entorno virtual
.venv\Scripts\activate  # Windows

# Ejecutar interfaz web
streamlit run app/main.py

# Se abre en http://localhost:8501
```

### 🔧 POSIBLES MEJORAS FUTURAS

1. **Market Data en tiempo real**: Precios actuales con yfinance
2. **Alertas**: Notificaciones de dividendos próximos
3. **Rebalanceo**: Sugerencias de ajuste de cartera
4. **Multi-usuario**: Soporte para varias carteras
5. **Backtesting**: Simular estrategias históricas
6. **API REST**: Exponer datos para otras aplicaciones
7. **Móvil**: App nativa con Kivy o similar

### 📎 DOCUMENTACIÓN ADICIONAL
Tengo un documento de Notion con la especificación completa del proyecto. También puedo compartir los commits de sesiones anteriores para más contexto.

### 🎯 ¿QUÉ NECESITO AHORA?
[Especifica aquí qué quieres hacer en esta sesión, por ejemplo:]
- Implementar el módulo Benchmarks (Sesión 6)
- Empezar con la interfaz Streamlit (Sesión 7)
- Corregir algún bug específico
- Añadir una funcionalidad nueva
- Revisar/refactorizar código existente

---

**Nota**: Si necesitas ver el código actual de algún módulo, pídemelo y te lo comparto. Los archivos principales son `database.py`, `data_loader.py`, `portfolio.py`, `tax_calculator.py`, `dividends.py`, `benchmarks.py` y `convert_investing_csv.py`.
