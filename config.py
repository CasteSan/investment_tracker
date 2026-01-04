"""
Configuración global del proyecto Investment Tracker
"""
import os
from pathlib import Path

# ==========================================
# RUTAS DEL PROYECTO
# ==========================================

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Directorio de datos
DATA_DIR = BASE_DIR / 'data'
EXPORTS_DIR = DATA_DIR / 'exports'
BENCHMARK_DIR = DATA_DIR / 'benchmark_data'

# Base de datos
DATABASE_PATH = DATA_DIR / 'database.db'

# Crear directorios si no existen
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)
BENCHMARK_DIR.mkdir(exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==========================================

# String de conexión SQLite
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# ==========================================
# CONFIGURACIÓN FISCAL
# ==========================================

# Método de asignación de lotes para cálculo de plusvalías
# Opciones: 'FIFO' (First In First Out) o 'LIFO' (Last In First Out)
TAX_METHOD = 'FIFO'

# Porcentaje de retención por defecto para dividendos (España: 19%)
DEFAULT_WITHHOLDING_TAX = 19.0

# ==========================================
# CONFIGURACIÓN DE VISUALIZACIÓN
# ==========================================

# Formato de fechas para mostrar
DATE_FORMAT = '%d/%m/%Y'

# Formato numérico para moneda
CURRENCY_FORMAT = '€{:,.2f}'

# Colores para gráficos
COLOR_POSITIVE = '#10b981'  # Verde
COLOR_NEGATIVE = '#ef4444'  # Rojo
COLOR_NEUTRAL = '#6b7280'   # Gris

# ==========================================
# TIPOS DE ACTIVOS
# ==========================================

ASSET_TYPES = {
    'accion': 'Acción',
    'fondo': 'Fondo de Inversión',
    'etf': 'ETF',
    'bono': 'Bono'
}

# ==========================================
# TIPOS DE TRANSACCIONES
# ==========================================

TRANSACTION_TYPES = {
    'buy': 'Compra',
    'sell': 'Venta',
    'transfer': 'Traspaso',
    'dividend': 'Dividendo'
}

# ==========================================
# CONFIGURACIÓN DE BENCHMARKS
# ==========================================

# Benchmarks disponibles (símbolo Yahoo Finance)
BENCHMARKS = {
    'IBEX35': '^IBEX',
    'SP500': '^GSPC',
    'EUROSTOXX50': '^STOXX50E',
    'NASDAQ': '^IXIC',
    'MSCI_WORLD': 'URTH'
}

# ==========================================
# CONFIGURACIÓN DE VALIDACIONES
# ==========================================

# Máximo porcentaje de comisión considerado "normal" (alerta si supera)
MAX_COMMISSION_PCT = 5.0

# ==========================================
# MODO DEBUG
# ==========================================

DEBUG = True  # Cambiar a False en producción