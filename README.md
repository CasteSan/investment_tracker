# 📊 Investment Tracker - Sistema de Registro de Cartera Personal

Sistema completo de gestión y análisis de inversiones personales desarrollado en Python.

## 🎯 Estado Actual del Proyecto

### ✅ Sesión 1 Completada: Base de Datos y Configuración

**Módulos funcionales:**
- ✅ `config.py` - Configuración global
- ✅ `src/database.py` - Gestión completa de base de datos
- ✅ Base de datos SQLite con tablas: Transactions, Dividends, BenchmarkData, PortfolioSnapshots

**Próximas sesiones:**
- 🔜 Sesión 2: Importador de datos (CSV/Excel)
- 🔜 Sesión 3: Módulo de Portfolio (cálculos de cartera)
- 🔜 Sesión 4: Interfaz Streamlit (Dashboard)
- 🔜 Sesión 5: Tax Calculator (cálculos fiscales)
- 🔜 Sesión 6: Módulo de Dividendos
- 🔜 Sesión 7: Módulo de Benchmarks
- 🔜 Sesión 8: Completar UI y pulir

---

## 🚀 Configuración Inicial (Setup)

### 1. Prerrequisitos

- **Python 3.10 o superior**
- **VSCode** (recomendado)
- **Git** (opcional, para control de versiones)

Verifica tu versión de Python:
```bash
python --version
# Debe mostrar: Python 3.10.x o superior
```

### 2. Crear Estructura de Carpetas

Abre PowerShell en la ubicación donde quieres crear el proyecto:

```powershell
# Navega a tu carpeta de documentos (o donde prefieras)
cd C:\Users\TuNombre\Documents

# Crea la estructura completa
mkdir investment_tracker
cd investment_tracker

mkdir data, data\benchmark_data, data\exports
mkdir src, app, app\pages
mkdir notebooks, tests, scripts
```

### 3. Crear los Archivos del Proyecto

Copia el contenido de los artifacts en los siguientes archivos:

```
investment_tracker/
├── config.py                    # Copiar contenido del artifact "config.py"
├── requirements.txt             # Copiar contenido del artifact "requirements.txt"
├── test_database.py            # Copiar contenido del artifact "test_database.py"
├── README.md                    # Este archivo
└── src/
    ├── __init__.py             # Copiar contenido del artifact "src/__init__.py"
    └── database.py             # Copiar contenido del artifact "src/database.py"
```

### 4. Crear Entorno Virtual

Es **altamente recomendado** usar un entorno virtual para aislar las dependencias:

```bash
# Crear entorno virtual
python -m venv venv

# Activar el entorno virtual
# En Windows PowerShell:
venv\Scripts\Activate.ps1

# En Windows CMD:
venv\Scripts\activate.bat

# Deberías ver (venv) al inicio de tu línea de comandos
```

### 5. Instalar Dependencias

Con el entorno virtual activado:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Esto instalará:
- SQLAlchemy (base de datos)
- Pandas, NumPy (análisis de datos)
- Streamlit, Plotly (visualización)
- openpyxl (Excel)
- yfinance (precios de mercado)

### 6. Verificar Instalación

```bash
pip list
# Deberías ver todas las dependencias listadas
```

---

## 🧪 Probar que Todo Funciona

### Opción 1: Script de Prueba Completo

Ejecuta el script de prueba que valida toda la funcionalidad:

```bash
python test_database.py
```

**Salida esperada:**
```
🚀 INVESTMENT TRACKER - TEST DE BASE DE DATOS
============================================================

📊 Inicializando base de datos...
✅ Base de datos inicializada: data\database.db

============================================================
TEST 1: Añadir Transacciones
============================================================

➕ Añadiendo compra de Telefónica...
✅ Transacción añadida: BUY 100 TEF
...
[más tests]
...
============================================================
🎉 TODOS LOS TESTS PASARON EXITOSAMENTE
============================================================
```

### Opción 2: Prueba Manual en Python

Abre Python interactivo:

```bash
python
```

Y ejecuta:

```python
from src.database import Database

# Inicializar BD
db = Database()

# Añadir una transacción
db.add_transaction({
    'date': '2024-01-15',
    'type': 'buy',
    'ticker': 'TEF',
    'name': 'Telefónica',
    'asset_type': 'accion',
    'quantity': 100,
    'price': 4.20,
    'commission': 10.0
})

# Ver todas las transacciones
trans = db.get_transactions()
print(f"Total transacciones: {len(trans)}")

# Convertir a DataFrame
df = db.transactions_to_dataframe()
print(df)

db.close()
```

---

## 📖 Uso del Módulo de Base de Datos

### Añadir Transacciones

```python
from src.database import Database

db = Database()

# Compra de acciones
db.add_transaction({
    'date': '2024-01-15',
    'type': 'buy',
    'ticker': 'BBVA',
    'name': 'Banco BBVA',
    'asset_type': 'accion',
    'quantity': 50,
    'price': 9.50,
    'commission': 8.50,
    'notes': 'Primera compra'
})

# Venta de acciones
db.add_transaction({
    'date': '2024-06-20',
    'type': 'sell',
    'ticker': 'BBVA',
    'quantity': 25,
    'price': 10.20,
    'commission': 8.00
})
```

### Consultar Transacciones

```python
# Todas las transacciones
all_trans = db.get_transactions()

# Solo compras
compras = db.get_transactions(type='buy')

# Transacciones de un ticker específico
bbva_trans = db.get_transactions(ticker='BBVA')

# Transacciones de 2024
trans_2024 = db.get_transactions(year=2024)

# Últimas 10 transacciones
ultimas = db.get_transactions(limit=10)
```

### Añadir Dividendos

```python
db.add_dividend({
    'ticker': 'TEF',
    'date': '2024-06-15',
    'gross_amount': 25.00,
    'net_amount': 20.25,
    'notes': 'Dividendo semestral'
})
```

### Trabajar con DataFrames

```python
import pandas as pd

# Convertir transacciones a DataFrame
df = db.transactions_to_dataframe()

# Ahora puedes usar todo el poder de pandas
print(df.describe())
print(df.groupby('ticker')['quantity'].sum())
```

---

## 📁 Estructura Actual del Proyecto

```
investment_tracker/
│
├── 📄 config.py              # ✅ Configuración global
├── 📄 requirements.txt       # ✅ Dependencias
├── 📄 test_database.py      # ✅ Script de prueba
├── 📄 README.md             # ✅ Este archivo
│
├── 📁 data/                 # Se crea automáticamente
│   ├── database.db          # SQLite (se crea al ejecutar)
│   ├── benchmark_data/      # Para índices (futuro)
│   └── exports/             # Para exportaciones (futuro)
│
├── 📁 src/                  # ✅ Módulos principales
│   ├── __init__.py          # ✅ Marca como paquete
│   └── database.py          # ✅ FUNCIONAL - Gestión BD
│
├── 📁 app/                  # 🔜 Interfaz Streamlit (Sesión 4)
├── 📁 notebooks/            # 🔜 Jupyter notebooks
├── 📁 tests/                # 🔜 Tests unitarios
└── 📁 scripts/              # 🔜 Scripts auxiliares
```

---

## 🗃️ Esquema de Base de Datos

### Tabla: `transactions`

| Columna      | Tipo    | Descripción                          |
|--------------|---------|--------------------------------------|
| id           | Integer | ID único (auto-incremento)           |
| date         | Date    | Fecha de la transacción              |
| type         | String  | Tipo: buy, sell, transfer            |
| ticker       | String  | Ticker/ISIN del activo               |
| name         | String  | Nombre del activo (opcional)         |
| asset_type   | String  | Tipo: accion, fondo, etf, bono       |
| quantity     | Float   | Cantidad de unidades                 |
| price        | Float   | Precio unitario                      |
| commission   | Float   | Comisiones pagadas                   |
| total        | Float   | Total de la operación (calculado)    |
| notes        | Text    | Notas adicionales                    |
| created_at   | DateTime| Timestamp de creación                |

### Tabla: `dividends`

| Columna         | Tipo    | Descripción                        |
|-----------------|---------|-------------------------------------|
| id              | Integer | ID único (auto-incremento)          |
| ticker          | String  | Ticker del activo                   |
| date            | Date    | Fecha del dividendo                 |
| gross_amount    | Float   | Importe bruto                       |
| net_amount      | Float   | Importe neto (después retención)    |
| withholding_tax | Float   | Retención fiscal aplicada           |
| notes           | Text    | Notas adicionales                   |
| created_at      | DateTime| Timestamp de creación               |

### Tabla: `benchmark_data`

| Columna        | Tipo    | Descripción                        |
|----------------|---------|-------------------------------------|
| id             | Integer | ID único                            |
| benchmark_name | String  | Nombre del índice (IBEX35, SP500)   |
| date           | Date    | Fecha del dato                      |
| close_value    | Float   | Valor de cierre del índice          |

---

## 🛠️ Herramientas Recomendadas

### VSCode Extensions

- **Python** (Microsoft)
- **SQLite** (alexcvzz.vscode-sqlite) - Para inspeccionar la BD visualmente
- **Jupyter** - Para notebooks (sesiones futuras)

### Inspeccionar Base de Datos

Puedes ver el contenido de `database.db` con:

1. **VSCode SQLite Extension**: Click derecho en database.db → Open Database
2. **DB Browser for SQLite**: https://sqlitebrowser.org/ (software gratuito)
3. **Python**:
   ```python
   from src.database import Database
   db = Database()
   df = db.transactions_to_dataframe()
   print(df)
   ```

---

## 🐛 Troubleshooting

### Error: "No module named 'src'"

**Solución**: Asegúrate de ejecutar Python desde la raíz del proyecto:

```bash
cd investment_tracker  # Raíz del proyecto
python test_database.py
```

### Error: "No module named 'sqlalchemy'"

**Solución**: Activa el entorno virtual e instala dependencias:

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### Error: "Unable to create file database.db"

**Solución**: La carpeta `data/` no existe. Créala manualmente:

```bash
mkdir data
```

---

## 📝 Próximos Pasos

Una vez validado que todo funciona:

1. ✅ **Familiarízate con el módulo database.py**
   - Prueba añadir tus propias transacciones
   - Experimenta con los filtros de consulta
   - Convierte datos a DataFrame y explora con pandas

2. 🔜 **Sesión 2: Data Loader**
   - Importar transacciones desde CSV/Excel
   - Validación automática de datos
   - Exportación de datos

3. 🔜 **Sesión 3: Portfolio Module**
   - Cálculo de posiciones actuales
   - Rentabilidad por activo
   - Valor total de cartera

4. 🔜 **Sesión 4: Streamlit UI**
   - Dashboard visual
   - Gráficos interactivos
   - Formularios para añadir operaciones

---

## 🤝 Contacto y Soporte

Este es tu proyecto personal. Si encuentras problemas o quieres modificar algo:

1. Revisa el código de `database.py` - está bien comentado
2. Consulta la documentación de SQLAlchemy si quieres personalizar modelos
3. Experimenta con pandas para análisis custom

---

## 📜 Licencia

Proyecto personal - Úsalo como quieras 🚀

---

**¡Felicidades! Has completado la Sesión 1. Tu base de datos está lista para registrar transacciones.** 🎉