# 📚 Guía Completa del Proyecto Investment Tracker

## Índice
1. [Filosofía del Proyecto](#1-filosofía-del-proyecto)
2. [Estructura de Carpetas](#2-estructura-de-carpetas)
3. [¿Qué hace cada archivo?](#3-qué-hace-cada-archivo)
4. [¿Por qué test_*.py y no src/*.py directamente?](#4-por-qué-test_py-y-no-src_py-directamente)
5. [Cómo se conectan las piezas](#5-cómo-se-conectan-las-piezas)
6. [Flujos de trabajo](#6-flujos-de-trabajo)
7. [Comandos de referencia rápida](#7-comandos-de-referencia-rápida)

---

## 1. Filosofía del Proyecto

### El proyecto tiene 3 capas:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                      │
│         (Lo que VES y con lo que INTERACTÚAS)               │
│                                                              │
│   ┌─────────────┐     ┌─────────────────────────────────┐   │
│   │ Terminal    │     │ Interfaz Web (Streamlit)        │   │
│   │ test_*.py   │     │ app/main.py + app/pages/        │   │
│   └─────────────┘     └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA DE NEGOCIO                │
│              (El CEREBRO que hace los cálculos)             │
│                                                              │
│   src/portfolio.py      → Cálculos de cartera               │
│   src/tax_calculator.py → Cálculos fiscales                 │
│   src/dividends.py      → Gestión de dividendos             │
│   src/benchmarks.py     → Comparación con índices           │
│   src/data_loader.py    → Importar/exportar datos           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                            │
│           (Donde se GUARDAN los datos)                      │
│                                                              │
│   src/database.py       → Gestión de SQLite                 │
│   data/database.db      → El archivo de base de datos       │
│   data/exports/         → Informes generados                │
└─────────────────────────────────────────────────────────────┘
```

### Principio clave: Separación de responsabilidades

- **Los módulos de `src/`** son **librerías/bibliotecas** → Contienen funciones y clases
- **Los archivos `test_*.py`** son **scripts ejecutables** → Usan las librerías para hacer cosas
- **La carpeta `app/`** es la **interfaz web** → También usa las librerías de src/

---

## 2. Estructura de Carpetas

```
investment_tracker/
│
├── 📁 src/                      # LIBRERÍAS (no se ejecutan directamente)
│   ├── database.py              # Conexión y modelos de BD
│   ├── data_loader.py           # Importar/exportar CSV
│   ├── portfolio.py             # Análisis de cartera
│   ├── tax_calculator.py        # Cálculos fiscales
│   ├── dividends.py             # Gestión de dividendos
│   └── benchmarks.py            # Comparación con índices
│
├── 📁 app/                      # INTERFAZ WEB (Streamlit)
│   ├── main.py                  # Página principal
│   ├── pages/                   # Páginas de la aplicación
│   │   ├── 1_📊_Dashboard.py
│   │   ├── 2_➕_Añadir_Operación.py
│   │   ├── 3_📈_Análisis.py
│   │   ├── 4_💰_Fiscal.py
│   │   ├── 5_💵_Dividendos.py
│   │   └── 6_🎯_Benchmarks.py
│   └── components/              # Componentes visuales
│       ├── charts.py
│       ├── tables.py
│       └── metrics.py
│
├── 📁 data/                     # DATOS
│   ├── database.db              # Base de datos SQLite
│   └── exports/                 # Informes generados
│
├── 📁 scripts/                  # SCRIPTS DE UTILIDAD
│   └── convert_investing_csv.py # Conversor de Investing.com
│
├── 📄 test_portfolio.py         # Script para probar portfolio
├── 📄 test_tax_calculator.py    # Script para probar fiscal
├── 📄 test_dividends.py         # Script para probar dividendos
├── 📄 test_benchmarks.py        # Script para probar benchmarks
│
└── 📄 config.py                 # Configuración global
```

---

## 3. ¿Qué hace cada archivo?

### 📁 Carpeta `src/` - Las librerías

Estos archivos **NO se ejecutan directamente**. Son como cajas de herramientas que otros programas usan.

| Archivo | Qué contiene | Para qué sirve |
|---------|--------------|----------------|
| `database.py` | Clase `Database`, modelos SQLAlchemy | Guardar/leer datos de la BD |
| `data_loader.py` | Clase `DataLoader` | Importar CSV, exportar a Excel |
| `portfolio.py` | Clase `Portfolio` | Calcular posiciones, rentabilidad |
| `tax_calculator.py` | Clase `TaxCalculator` | Calcular plusvalías, FIFO, informes fiscales |
| `dividends.py` | Clase `DividendManager` | Gestionar dividendos, yields |
| `benchmarks.py` | Clase `BenchmarkComparator` | Descargar índices, comparar rendimiento |

**Ejemplo de uso:**
```python
# Esto NO funciona (database.py no es ejecutable):
# python src/database.py  ❌

# Esto SÍ funciona (importar y usar la clase):
from src.database import Database
db = Database()
transactions = db.get_transactions()
db.close()
```

### 📄 Archivos `test_*.py` - Scripts ejecutables

Estos archivos **SÍ se ejecutan** desde terminal. Usan las librerías de `src/` para:
1. Probar que todo funciona
2. Mostrar demos de las funcionalidades
3. Permitir uso rápido sin abrir Streamlit

| Archivo | Qué hace |
|---------|----------|
| `test_portfolio.py` | Muestra análisis de cartera, posiciones, rentabilidad |
| `test_tax_calculator.py` | Muestra plusvalías, informe fiscal, simula ventas |
| `test_dividends.py` | Muestra dividendos, calendario, yields |
| `test_benchmarks.py` | Descarga benchmarks, compara con cartera |

**Cómo usarlos:**
```bash
python test_portfolio.py          # Tests básicos
python test_portfolio.py demo     # Demo completa
python test_dividends.py --create-examples  # Crear datos de ejemplo
```

### 📁 Carpeta `app/` - Interfaz web

La interfaz visual que agrupa todo en un dashboard bonito.

| Archivo | Qué muestra |
|---------|-------------|
| `main.py` | Página de inicio, resumen ejecutivo |
| `pages/1_📊_Dashboard.py` | Vista general: métricas, gráficos, posiciones |
| `pages/2_➕_Añadir_Operación.py` | Formularios para registrar operaciones |
| `pages/3_📈_Análisis.py` | Rentabilidad detallada por activo |
| `pages/4_💰_Fiscal.py` | Plusvalías, simulador, lotes FIFO |
| `pages/5_💵_Dividendos.py` | Calendario, yields, proyecciones |
| `pages/6_🎯_Benchmarks.py` | Comparación con S&P 500, IBEX, etc. |

**Cómo ejecutar:**
```bash
streamlit run app/main.py
# Se abre en http://localhost:8501
```

---

## 4. ¿Por qué test_*.py y no src/*.py directamente?

### Razón 1: Los módulos de src/ son LIBRERÍAS, no PROGRAMAS

```python
# src/portfolio.py contiene esto:
class Portfolio:
    def __init__(self):
        self.db = Database()
    
    def get_current_positions(self):
        # ... código ...
        return dataframe

# Si ejecutas "python src/portfolio.py" no pasa nada útil
# porque solo defines la clase, no la usas
```

### Razón 2: Los test_*.py son la "interfaz de terminal"

```python
# test_portfolio.py hace esto:
from src.portfolio import Portfolio

portfolio = Portfolio()
portfolio.print_portfolio_summary()  # ← Esto SÍ muestra algo
portfolio.print_positions_table()
portfolio.close()
```

### Razón 3: Separación = Flexibilidad

Al tener las librerías separadas de los scripts:
- Puedes usar `Portfolio` desde Streamlit
- Puedes usar `Portfolio` desde un test
- Puedes usar `Portfolio` desde un notebook de Jupyter
- Puedes usar `Portfolio` desde otro programa que crees

### Analogía: La cocina de un restaurante

```
src/portfolio.py     = Los ingredientes y recetas (no comes directamente)
test_portfolio.py    = El cocinero que prepara el plato
app/main.py          = El camarero que te lo sirve bonito

Todos usan los mismos ingredientes (src/), pero de formas diferentes.
```

---

## 5. Cómo se conectan las piezas

### Diagrama de dependencias:

```
                    ┌──────────────────┐
                    │   database.db    │
                    │   (tus datos)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   database.py    │
                    │   (lee/escribe)  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  portfolio.py │   │tax_calculator │   │  dividends.py │
│               │   │     .py       │   │               │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │  test_*.py    │               │   app/*.py    │
    │  (terminal)   │               │  (Streamlit)  │
    └───────────────┘               └───────────────┘
```

### Flujo de datos:

```
1. Tus operaciones reales (broker)
         │
         ▼
2. CSV de Investing.com
         │
         ▼
3. convert_investing_csv.py  → Convierte formato
         │
         ▼
4. data_loader.py  → Importa a la base de datos
         │
         ▼
5. database.db  ← Aquí viven tus datos
         │
         ▼
6. Los módulos (portfolio, tax, dividends, benchmarks)
   leen de la BD y hacen cálculos
         │
         ├──► test_*.py muestra resultados en terminal
         │
         └──► app/*.py muestra resultados en navegador
```

---

## 6. Flujos de trabajo

### 🔄 Flujo 1: Primera vez (configuración inicial)

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# 2. Instalar dependencias
pip install pandas sqlalchemy openpyxl yfinance streamlit plotly scipy

# 3. Exportar datos de Investing.com (desde la web)
#    Portfolio → Export → CSV

# 4. Convertir el CSV
python scripts/convert_investing_csv.py data/mi_portfolio.csv

# 5. Importar a la base de datos
python -c "
from src.data_loader import DataLoader
dl = DataLoader()
result = dl.import_from_csv('data/investing_converted_XXXXXX.csv')
print(result)
dl.close()
"

# 6. Verificar que todo funciona
python test_portfolio.py

# 7. Abrir interfaz web
streamlit run app/main.py
```

### 🔄 Flujo 2: Uso diario (registrar nueva operación)

**Opción A: Desde Streamlit (recomendado)**
```bash
streamlit run app/main.py
# → Ir a "➕ Añadir Operación"
# → Rellenar formulario
# → Guardar
```

**Opción B: Desde Python**
```python
from src.database import Database

db = Database()
db.add_transaction({
    'date': '2026-01-06',
    'type': 'buy',
    'ticker': 'AAPL',
    'name': 'Apple Inc.',
    'quantity': 10,
    'price': 185.50,
    'commission': 1.00,
    'currency': 'USD'
})
db.close()
```

### 🔄 Flujo 3: Análisis periódico (mensual/trimestral)

```bash
# Abrir Streamlit
streamlit run app/main.py

# Navegar por las páginas:
# 1. Dashboard → Ver resumen general
# 2. Análisis → Ver rentabilidad por activo
# 3. Benchmarks → Comparar con S&P 500
# 4. Dividendos → Ver cobros del período
```

**O desde terminal:**
```bash
python test_portfolio.py demo    # Análisis de cartera
python test_benchmarks.py demo   # Comparación con índices
```

### 🔄 Flujo 4: Declaración de la renta (anual)

```bash
# Abrir Streamlit
streamlit run app/main.py

# Ir a "💰 Fiscal"
# 1. Seleccionar año (ej: 2025)
# 2. Revisar plusvalías y minusvalías
# 3. Verificar alertas de wash sales
# 4. Exportar informe Excel
```

**O desde terminal:**
```bash
python test_tax_calculator.py demo
# → Se genera data/exports/informe_fiscal_2025.xlsx
```

### 🔄 Flujo 5: Actualizar datos de Investing.com

Cuando quieras sincronizar con las operaciones registradas en Investing.com:

```bash
# 1. Exportar nuevo CSV desde Investing.com

# 2. Convertir
python scripts/convert_investing_csv.py data/nuevo_export.csv

# 3. Importar (detecta duplicados automáticamente)
python -c "
from src.data_loader import DataLoader
dl = DataLoader()
result = dl.import_from_csv('data/investing_converted_XXXXXX.csv')
print(f'Importadas: {result[\"imported\"]}')
print(f'Duplicados: {result[\"duplicates\"]}')
dl.close()
"
```

---

## 7. Comandos de referencia rápida

### Ejecutar Streamlit (interfaz web)
```bash
streamlit run app/main.py
```

### Análisis rápido desde terminal
```bash
python test_portfolio.py          # Tests de portfolio
python test_portfolio.py demo     # Demo completa

python test_tax_calculator.py     # Tests fiscales
python test_tax_calculator.py demo

python test_dividends.py          # Tests dividendos
python test_dividends.py demo
python test_dividends.py --create-examples  # Crear datos ejemplo

python test_benchmarks.py         # Tests benchmarks
python test_benchmarks.py demo
```

### Importar datos
```bash
# Convertir CSV de Investing.com
python scripts/convert_investing_csv.py data/archivo.csv

# Importar a BD
python -c "from src.data_loader import DataLoader; dl = DataLoader(); print(dl.import_from_csv('archivo.csv')); dl.close()"
```

### Resetear base de datos (¡CUIDADO!)
```bash
# Windows
del data\database.db

# Linux/Mac
rm data/database.db

# La próxima vez que ejecutes cualquier módulo, se creará vacía
```

### Ver estado de la BD
```python
from src.database import Database
db = Database()
print(db.get_database_stats())
db.close()
```

---

## Resumen: ¿Qué usar cuándo?

| Quiero... | Uso... |
|-----------|--------|
| Ver mi cartera visualmente | `streamlit run app/main.py` |
| Registrar una operación | Streamlit → "➕ Añadir Operación" |
| Ver análisis rápido en terminal | `python test_portfolio.py demo` |
| Importar datos de Investing.com | `python scripts/convert_investing_csv.py` |
| Generar informe fiscal | Streamlit → "💰 Fiscal" → Exportar |
| Comparar con S&P 500 | Streamlit → "🎯 Benchmarks" |
| Crear un script personalizado | Importar clases de `src/` |

---

## Preguntas frecuentes

### ¿Puedo borrar los archivos test_*.py?
Sí, pero perderás la posibilidad de usar el sistema desde terminal. Son útiles para debugging y uso rápido.

### ¿Por qué no ejecutar directamente src/portfolio.py?
Porque es una librería, no un programa. Es como preguntar "¿por qué no puedo comer la receta?". La receta te dice cómo cocinar, pero necesitas a alguien (test_*.py o Streamlit) que la prepare.

### ¿Dónde están mis datos?
En `data/database.db`. Es un único archivo que contiene todo. Puedes copiarlo para hacer backup.

### ¿Puedo usar solo Streamlit sin los test_*.py?
Sí, perfectamente. Streamlit es la forma principal de usar el sistema. Los test_*.py son para uso avanzado/terminal.

### ¿Cómo añado un nuevo módulo?
1. Crea el archivo en `src/nuevo_modulo.py`
2. Crea `test_nuevo_modulo.py` para probarlo
3. Crea una página en `app/pages/X_nombre.py` si quieres verlo en Streamlit
