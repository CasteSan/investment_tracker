# CLAUDE.md

Este documento guía a Claude al trabajar con investment_tracker.

## Stack tecnológico

Python 3.10+ | SQLite + SQLAlchemy | Pandas/NumPy | Streamlit + Plotly

## Comandos esenciales

```bash
# Ejecutar app
streamlit run app/main.py

# Tests individuales
python test_portfolio.py
python test_database.py
python test_tax_calculator.py
python test_dividends.py
python test_benchmarks.py

# Instalar dependencias
pip install -r requirements.txt
```

## Arquitectura de 3 capas

1. **Presentación** (`app/`) → Streamlit, no lógica de negocio
2. **Negocio** (`src/`) → Portfolio, TaxCalculator, DividendManager, BenchmarkComparator
3. **Datos** (`src/database.py`) → Único punto de acceso a SQLite

## Estructura de carpetas

```
src/           # Módulos core (database.py, portfolio.py, tax_calculator.py, etc.)
app/           # UI Streamlit (main.py, pages/, components/)
data/          # database.db, exports/, benchmark_data/
tests/         # Tests unitarios
test_*.py      # Tests de integración (raíz)
config.py      # Constantes globales (rutas, TAX_METHOD, BENCHMARKS, etc.)
```

## Convenciones del proyecto

### Imports
```python
# Siempre usar try/except para compatibilidad
try:
    from src.database import Database
    from src.logger import get_logger
except ImportError:
    from database import Database
    from logger import get_logger
```

### Base de datos
- Usar `Database()` como único punto de acceso
- Siempre cerrar conexión con `db.close()`
- Modelos en `database.py`: `Transaction`, `Dividend`, `BenchmarkData`, `AssetPrice`

### Módulos de negocio
- Cada módulo tiene un `close()` que llama a `self.db.close()`
- Soportan inyección de `db_path` para testing
- Retornan DataFrames o diccionarios estructurados

### UI Streamlit
- Emojis en nombres de archivo: `1_📊_Dashboard.py`
- Componentes reutilizables en `app/components/`
- Configuración de página siempre al inicio

## Reglas fiscales (España)

- Método por defecto: **FIFO** (First In First Out)
- Retención dividendos: 19% (`config.DEFAULT_WITHHOLDING_TAX`)
- Divisas soportadas: EUR, USD, GBX, CAD
- Campo `realized_gain_eur` almacena B/P en EUR ya convertido

## Patrones de código

### Crear tests
```python
def run_tests():
    """Ejecuta todos los tests"""
    tests_passed = 0
    tests_failed = 0
    # ... test blocks con try/except
    print(f"✅ Tests pasados: {tests_passed}")
```

### Documentación de funciones
```python
def get_current_positions(self, asset_type: str = None) -> pd.DataFrame:
    """
    Calcula las posiciones actuales de la cartera.
    
    Args:
        asset_type: Filtrar por tipo ('accion', 'fondo', 'etf')
    
    Returns:
        DataFrame con ticker, quantity, avg_price, market_value...
    """
```

## Errores comunes a evitar

1. **No cerrar conexiones DB** → Memory leaks, DB locked
2. **Lógica de negocio en UI** → Todo cálculo en `src/`
3. **Ignorar divisas** → Usar `realized_gain_eur` para B/P reales
4. **SQL directo** → Siempre usar clase `Database`

## Archivos ignorados (no versionar)

- `data/database.db`, `data/*.db`
- `data/exports/`, `data/benchmark_data/`
- `venv/`, `__pycache__/`, `*.log`
