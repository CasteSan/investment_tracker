# =============================================================================
# PROMPT PARA CONTINUAR EL PROYECTO EN NUEVA CONVERSACIÓN
# =============================================================================
# Copia y pega esto al inicio de una nueva conversación con Claude.
# Adjunta también: commits de sesiones anteriores, archivos actuales si es necesario.
# =============================================================================

## 🎯 PROYECTO: Investment Tracker - Sistema de Gestión de Cartera Personal

Estoy desarrollando un sistema completo de gestión y análisis de inversiones personales en Python. El proyecto está en desarrollo activo y necesito tu ayuda para continuar implementando módulos.

### 📋 OBJETIVO
Sistema local (Windows + VSCode) para:
- Registrar operaciones financieras (compras, ventas, traspasos, dividendos)
- Calcular rentabilidades (total, por activo, histórica)
- Generar informes fiscales (plusvalías FIFO/LIFO para declaración de renta)
- Comparar rendimiento con benchmarks (IBEX, S&P 500, etc.)

### 🛠️ STACK TECNOLÓGICO
- **Python 3.10+** con entorno virtual
- **SQLite** + **SQLAlchemy** para base de datos
- **Pandas** para análisis de datos
- **Streamlit** (futuro) para interfaz web
- **Plotly** (futuro) para gráficos

### 📁 ESTRUCTURA ACTUAL DEL PROYECTO

```
investment_tracker/
├── data/
│   ├── database.db                 # Base de datos SQLite
│   └── mi_portfolio_investing.csv  # CSV exportado de Investing.com
├── src/
│   ├── __init__.py
│   ├── database.py                 # ✅ Modelos SQLAlchemy + CRUD
│   ├── data_loader.py              # ✅ Importador CSV/Excel
│   └── portfolio.py                # ✅ Análisis de cartera
├── scripts/
│   └── convert_investing_csv.py    # ✅ Conversor de Investing.com
├── test_portfolio.py               # ✅ Tests del módulo portfolio
├── config.py                       # Configuración global
└── requirements.txt
```

### ✅ MÓDULOS COMPLETADOS

#### Sesión 1: Database Module (`src/database.py`)
- Modelos SQLAlchemy: Transaction, Dividend, BenchmarkData, PortfolioSnapshot
- Campos especiales: `currency`, `market`, `realized_gain_eur`, `unrealized_gain_eur`
- CRUD completo + filtros + estadísticas

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
- Rentabilidad total y por activo
- Distribución de cartera
- Estadísticas avanzadas
- Usa `realized_gain_eur` para B/P correcta en cualquier divisa
- Muestra nombres de activos (`display_name`) en lugar de tickers

### 🔄 FLUJO DE TRABAJO ACTUAL

```bash
# 1. Exportar CSV de Investing.com (Portfolio → Exportar)

# 2. Convertir a formato interno
python scripts/convert_investing_csv.py data/mi_portfolio_investing.csv

# 3. Importar a base de datos
python -c "from src.data_loader import DataLoader; dl = DataLoader(); print(dl.import_from_csv('data/investing_converted_XXX.csv')); dl.close()"

# 4. Analizar cartera
python test_portfolio.py
```

### 🐛 BUGS YA CORREGIDOS
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

### 📋 PRÓXIMOS PASOS (por orden de prioridad)

#### Sesión 4: Tax Calculator (`src/tax_calculator.py`)
- Cálculo FIFO/LIFO configurable
- Asignación de lotes a ventas
- Informe fiscal anual (para declaración de renta)
- Simulación de impacto fiscal antes de vender
- Exportación a Excel para asesor fiscal

#### Sesión 5: Dividends Module (`src/dividends.py`)
- Registro de dividendos con retenciones
- Tracking anual
- Yield sobre precio de compra
- Inclusión en rentabilidad total

#### Sesión 6: Benchmarks (`src/benchmarks.py`)
- Comparación con índices (IBEX, S&P 500, etc.)
- Normalización base 100
- Cálculo de outperformance

#### Sesión 7+: Streamlit UI (`app/`)
- Dashboard interactivo
- Formularios para registrar operaciones
- Gráficos con Plotly

### 📎 DOCUMENTACIÓN ADICIONAL
Tengo un documento de Notion con la especificación completa del proyecto que puedo compartirte. También puedo compartir los commits de sesiones anteriores para más contexto.

### 🎯 ¿QUÉ NECESITO AHORA?
[Especifica aquí qué quieres hacer en esta sesión, por ejemplo:]
- Implementar el módulo Tax Calculator (Sesión 4)
- Corregir algún bug específico
- Añadir una funcionalidad nueva
- Revisar/refactorizar código existente

---

**Nota**: Si necesitas ver el código actual de algún módulo, pídemelo y te lo comparto. Los archivos principales son `database.py`, `data_loader.py`, `portfolio.py` y `convert_investing_csv.py`.
