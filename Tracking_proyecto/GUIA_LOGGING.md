# 📋 Sistema de Logging - Guía Completa

## 1. ¿Qué es Logging y Por Qué es Importante?

### Analogía Simple

Imagina que eres un detective investigando un crimen. Los logs son como las cámaras de seguridad del edificio: grabaron todo lo que pasó, en qué orden, y te ayudan a entender qué salió mal.

**Sin logging:**
```
Usuario: "La app no funciona"
Desarrollador: "¿Qué hacías? ¿Qué pasó? ¿Qué datos tenías?"
Usuario: "No sé, simplemente dejó de funcionar"
Desarrollador: 😫 (horas de debugging manual)
```

**Con logging:**
```
Usuario: "La app no funciona"
Desarrollador: (mira los logs)
[2026-01-06 10:45:23] ERROR | portfolio | División por cero en línea 234
[2026-01-06 10:45:23] DEBUG | portfolio | ticker='AAPL', quantity=0, price=150
Desarrollador: "¡Ah! El usuario intentó calcular rentabilidad con cantidad 0"
(Fix en 5 minutos)
```

### Por Qué Es Crítico en Desarrollo Profesional

| Sin Logging | Con Logging |
|------------|-------------|
| "Algo falló" | "El error X ocurrió en el módulo Y, línea Z, con estos datos" |
| Debug con print() por todas partes | Logs estructurados y filtrables |
| Imposible debugear producción | Logs persistentes para análisis |
| Problemas intermitentes = pesadilla | Histórico completo de eventos |

---

## 2. Niveles de Logging

El logging tiene **niveles de severidad** que permiten filtrar qué mensajes ver:

```
┌─────────────────────────────────────────────────────────────┐
│  CRITICAL (50) │ 💀 Error fatal, la app va a crashear       │
├─────────────────────────────────────────────────────────────┤
│  ERROR (40)    │ ❌ Algo falló pero la app sigue corriendo  │
├─────────────────────────────────────────────────────────────┤
│  WARNING (30)  │ ⚠️  Algo inesperado pero no crítico        │
├─────────────────────────────────────────────────────────────┤
│  INFO (20)     │ ℹ️  Operación normal completada            │
├─────────────────────────────────────────────────────────────┤
│  DEBUG (10)    │ 🔍 Detalles técnicos para desarrollo       │
└─────────────────────────────────────────────────────────────┘
```

### Cuándo Usar Cada Nivel

```python
# DEBUG: Detalles técnicos (solo en desarrollo)
logger.debug(f"Procesando ticker {ticker}, cantidad={qty}, precio={price}")

# INFO: Operaciones normales completadas
logger.info(f"Transacción añadida: ID={id}, {tipo} {cantidad} {ticker}")

# WARNING: Algo inusual pero no un error
logger.warning(f"Ticker {ticker} no encontrado en Yahoo Finance, usando precio manual")

# ERROR: Algo falló pero podemos continuar
logger.error(f"Error descargando precios de {ticker}: {error}")

# CRITICAL: Error grave que puede detener la app
logger.critical(f"No se puede conectar a la base de datos: {error}")
```

### Cómo Funciona el Filtrado

Si configuras el nivel en `INFO`, solo verás mensajes de nivel `INFO` o superior:

```python
# Nivel configurado: INFO

logger.debug("Esto NO se verá")      # DEBUG < INFO ❌
logger.info("Esto SÍ se verá")       # INFO = INFO ✅
logger.warning("Esto SÍ se verá")    # WARNING > INFO ✅
logger.error("Esto SÍ se verá")      # ERROR > INFO ✅
```

---

## 3. Arquitectura del Sistema de Logging

### Estructura de Archivos

```
investment_tracker/
├── src/
│   ├── logger.py          # 🆕 Configuración centralizada
│   ├── database.py        # ➕ Usa logging
│   ├── portfolio.py       # ➕ Usa logging
│   ├── tax_calculator.py  # ➕ Usa logging
│   ├── benchmarks.py      # ➕ Usa logging
│   └── market_data.py     # ➕ Usa logging
│
└── logs/                  # 🆕 Directorio de logs
    └── investment_tracker.log
```

### Flujo de Datos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Tu Código     │────▶│     Logger      │────▶│    Handlers     │
│                 │     │   (centralizado) │     │                 │
│ logger.info()   │     │ Formatea mensaje │     │ ├─ Consola      │
│ logger.error()  │     │ Añade timestamp  │     │ └─ Archivo      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Componentes del Sistema

```python
# logger.py - Configuración centralizada

# 1. FORMATO DE MENSAJES
LOG_FORMAT_CONSOLE = "%(asctime)s │ %(levelname)-8s │ %(name)-25s │ %(message)s"
# Resultado: "10:45:23 │ INFO     │ portfolio                 │ Cartera calculada"

LOG_FORMAT_FILE = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
# Resultado: "2026-01-06 10:45:23 | INFO     | portfolio | get_positions:156 | Cartera calculada"

# 2. HANDLERS (destinos de los logs)
# - ConsoleHandler: Muestra en terminal (con colores)
# - RotatingFileHandler: Guarda en archivo (rotativo, máx 5MB)

# 3. NIVELES CONFIGURABLES
DEFAULT_LOG_LEVEL = logging.INFO  # Cambiar para desarrollo/producción
```

---

## 4. Cómo Usar el Sistema de Logging

### Uso Básico en Cualquier Módulo

```python
# Al inicio del archivo
from src.logger import get_logger

logger = get_logger(__name__)

# En cualquier parte del código
def mi_funcion():
    logger.info("Función iniciada")
    
    try:
        # hacer algo
        resultado = calcular()
        logger.debug(f"Resultado: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"Error en cálculo: {e}")
        raise
```

### Cambiar Nivel de Logging

```python
# Para debugging (ver todos los mensajes)
from src.logger import setup_logging
import logging

setup_logging(level=logging.DEBUG)  # Ver TODO

# Para producción (solo mensajes importantes)
setup_logging(level=logging.WARNING)  # Solo warnings y errores
```

### Logs en Consola vs Archivo

**Consola:** Mensajes en tiempo real mientras desarrollas
```
10:45:23 │ INFO     │ portfolio                 │ Calculando posiciones
10:45:24 │ DEBUG    │ portfolio                 │ Procesando 150 transacciones
10:45:25 │ INFO     │ portfolio                 │ 12 posiciones calculadas
```

**Archivo (`logs/investment_tracker.log`):** Histórico persistente
```
2026-01-06 10:45:23 | INFO     | portfolio | get_current_positions:122 | Calculando posiciones
2026-01-06 10:45:24 | DEBUG    | portfolio | get_current_positions:135 | Procesando 150 transacciones
2026-01-06 10:45:25 | INFO     | portfolio | get_current_positions:245 | 12 posiciones calculadas
```

---

## 5. Patrones y Buenas Prácticas

### ✅ Buenas Prácticas

```python
# 1. Usar el nombre del módulo
logger = get_logger(__name__)  # ✅ Automáticamente "portfolio", "database", etc.
logger = get_logger("mi_app")  # ❌ Nombre genérico, difícil de filtrar

# 2. Loguear datos relevantes
logger.info(f"Transacción añadida: ID={id}, {tipo} {qty} {ticker} @ {price}")  # ✅
logger.info("Transacción añadida")  # ❌ Sin contexto, inútil para debugging

# 3. Usar el nivel correcto
logger.debug(f"Variable x = {x}")  # ✅ DEBUG para detalles técnicos
logger.info(f"Variable x = {x}")   # ❌ INFO para detalles técnicos (spam)

# 4. Loguear errores con contexto
try:
    resultado = procesar(datos)
except Exception as e:
    logger.error(f"Error procesando {datos}: {e}")  # ✅ Contexto + error
    logger.error(f"Error: {e}")  # ❌ Sin contexto
```

### ❌ Anti-patrones

```python
# 1. NO usar print() para debugging
print(f"DEBUG: {variable}")  # ❌ Se mezcla con output normal
logger.debug(f"{variable}")  # ✅ Controlable y filtrable

# 2. NO loguear información sensible
logger.info(f"Usuario {email} con contraseña {password}")  # ❌ NUNCA
logger.info(f"Usuario {email} autenticado")  # ✅

# 3. NO loguear en bucles internos (performance)
for i in range(1000000):
    logger.debug(f"Iteración {i}")  # ❌ Millones de logs = lento
    
# ✅ Mejor: loguear resúmenes
logger.info(f"Procesadas {len(items)} iteraciones")

# 4. NO ignorar excepciones silenciosamente
try:
    algo()
except:
    pass  # ❌ Error silencioso, imposible de debugear
    
# ✅ Mejor: loguear el error
try:
    algo()
except Exception as e:
    logger.warning(f"Error ignorado: {e}")
```

---

## 6. Ejemplos Reales en el Proyecto

### database.py - Capa de Datos

```python
def add_transaction(self, transaction_data: Dict) -> int:
    logger.debug(f"Añadiendo transacción: {transaction_data.get('type')} {transaction_data.get('ticker')}")
    
    # ... procesamiento ...
    
    transaction = Transaction(**transaction_data)
    self.session.add(transaction)
    self.session.commit()
    
    logger.info(f"Transacción añadida: ID={transaction.id}, {transaction.type} {transaction.quantity} {transaction.ticker}")
    return transaction.id
```

**Output:**
```
10:45:23 │ DEBUG    │ database                  │ Añadiendo transacción: buy AAPL
10:45:24 │ INFO     │ database                  │ Transacción añadida: ID=42, buy 100 AAPL @ 150
```

### portfolio.py - Capa de Negocio

```python
def get_current_positions(self, ...):
    logger.debug(f"Calculando posiciones actuales")
    
    transactions = self.db.get_transactions()
    
    if not transactions:
        logger.warning("No hay transacciones en la base de datos")
        return pd.DataFrame()
    
    logger.debug(f"Procesando {len(transactions)} transacciones")
    
    # ... cálculos ...
    
    logger.info(f"Calculadas {len(positions)} posiciones")
    return positions
```

---

## 7. Debugging con Logs

### Escenario: "La ganancia no cuadra"

```
# 1. Activar modo DEBUG
from src.logger import setup_logging
import logging
setup_logging(level=logging.DEBUG)

# 2. Ejecutar la operación
portfolio = Portfolio()
positions = portfolio.get_current_positions()

# 3. Revisar los logs
```

**Output típico:**
```
10:45:23 │ DEBUG    │ database                  │ Conectando a: database.db
10:45:23 │ INFO     │ database                  │ Base de datos inicializada
10:45:24 │ DEBUG    │ portfolio                 │ Calculando posiciones
10:45:24 │ DEBUG    │ portfolio                 │ Procesando 150 transacciones
10:45:24 │ DEBUG    │ portfolio                 │ Ticker AAPL: qty=100, cost=15000, price=175
10:45:24 │ DEBUG    │ portfolio                 │ Ticker AAPL: market_value=17500, gain=2500
...
```

### Buscar en el Archivo de Log

```bash
# Buscar errores
grep "ERROR" logs/investment_tracker.log

# Buscar por ticker
grep "AAPL" logs/investment_tracker.log

# Buscar por fecha
grep "2026-01-06 10:45" logs/investment_tracker.log

# Ver últimas 50 líneas
tail -50 logs/investment_tracker.log

# Ver en tiempo real (útil mientras desarrollas)
tail -f logs/investment_tracker.log
```

---

## 8. Configuración Avanzada

### Cambiar Nivel por Módulo

```python
import logging

# Silenciar un módulo específico
logging.getLogger("yfinance").setLevel(logging.WARNING)

# Más detalle en un módulo específico
logging.getLogger("portfolio").setLevel(logging.DEBUG)
```

### Rotar Logs Automáticamente

El sistema ya está configurado para:
- Máximo 5 MB por archivo
- Mantener 3 archivos de backup
- Rotación automática

```
logs/
├── investment_tracker.log        # Actual
├── investment_tracker.log.1      # Backup 1
├── investment_tracker.log.2      # Backup 2
└── investment_tracker.log.3      # Backup 3 (se elimina cuando llega el 4)
```

---

## 9. Integración con Streamlit

En Streamlit, los logs aparecen en la **terminal** donde ejecutas `streamlit run`:

```bash
# Terminal
$ streamlit run app/main.py

# Output de Streamlit
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501

# Tus logs aparecen aquí:
10:45:23 │ INFO     │ database                  │ Base de datos inicializada
10:45:24 │ INFO     │ portfolio                 │ Calculadas 12 posiciones
10:45:25 │ INFO     │ benchmarks                │ SP500 descargado: 365 registros
```

---

## 10. Resumen: Cheat Sheet de Logging

```python
# ============================================
# SETUP (al inicio de cada módulo)
# ============================================
from src.logger import get_logger
logger = get_logger(__name__)

# ============================================
# NIVELES (cuándo usar cada uno)
# ============================================
logger.debug("Detalles técnicos")      # Solo en desarrollo
logger.info("Operación completada")     # Operaciones normales
logger.warning("Algo inusual")          # Potenciales problemas
logger.error("Algo falló")              # Errores manejables
logger.critical("Error fatal")          # La app va a crashear

# ============================================
# CONFIGURACIÓN (opcional)
# ============================================
from src.logger import setup_logging
import logging

setup_logging(level=logging.DEBUG)      # Desarrollo (ver todo)
setup_logging(level=logging.INFO)       # Normal
setup_logging(level=logging.WARNING)    # Producción (solo problemas)

# ============================================
# DONDE VER LOS LOGS
# ============================================
# Consola: En tiempo real mientras ejecutas
# Archivo: logs/investment_tracker.log
```

---

## Conclusión

El logging es como tener un co-piloto que toma notas de todo lo que pasa en tu aplicación. Cuando algo sale mal (y siempre pasa), esas notas te salvan horas de debugging.

**Regla de oro:** Si algo puede fallar, loguéalo. Si algo es importante, loguéalo. Si no sabes si loguearlo, probablemente deberías.
