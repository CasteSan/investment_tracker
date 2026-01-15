# Masterclass: De Scripts a Software
## Un Post-Mortem Educativo del Proyecto Investment Tracker

---

## Introduccion: La Diferencia Fundamental

Antes de entrar en materia, necesito que entiendas algo que nadie te dice en los tutoriales:

**"Hacer que funcione" y "hacer ingenieria" son dos actividades completamente diferentes.**

Un script que funciona es como una receta escrita en una servilleta: cumple su proposito, pero intenta pasarsela a otra persona, o intenta cocinar el mismo plato en una cocina diferente, o intenta hacer 100 platos a la vez. Se desmorona.

La ingenieria de software es escribir esa receta de forma que:
- Cualquier cocinero pueda entenderla
- Funcione en cualquier cocina
- Escale a un restaurante entero
- Pueda modificarse sin empezar de cero

Este proyecto, Investment Tracker, es un caso de estudio perfecto porque cometimos (deliberadamente) algunos errores del "enfoque analista" al principio, y luego los corregimos. Vamos a diseccionar todo el proceso.

---

## Parte 1: La Hoja de Ruta Ideal

Si tuviera que empezar este proyecto desde cero hoy, con todo lo que sabemos, este seria el plan:

### Fase 0: Diseno en Papel (1-2 dias)

**Antes de escribir una sola linea de codigo.**

```
+-------------------------------------------------------------+
|                    PREGUNTAS INICIALES                       |
+-------------------------------------------------------------+
| 1. Que problema resuelve?                                   |
|    -> Gestionar carteras de inversion personales             |
|                                                             |
| 2. Quien lo va a usar?                                      |
|    -> Inicialmente yo, potencialmente familia/amigos         |
|                                                             |
| 3. Donde se va a ejecutar?                                  |
|    -> Local primero, nube despues                            |
|                                                             |
| 4. Que datos maneja?                                        |
|    -> Transacciones, dividendos, precios de mercado          |
|                                                             |
| 5. Necesita tiempo real?                                    |
|    -> No, actualizaciones diarias son suficientes            |
+-------------------------------------------------------------+
```

**Entregable de esta fase:** Un documento de una pagina con:
- Problema a resolver
- Usuarios objetivo
- Funcionalidades core (MVP)
- Restricciones conocidas

### Fase 1: Modelo de Datos (2-3 dias)

**Esta es la fase mas importante y la que mas se ignora.**

```
+-------------------------------------------------------------+
|                    ENTIDADES CORE                            |
+-------------------------------------------------------------+
|                                                             |
|  Portfolio ------+                                          |
|     |            |                                          |
|     | 1:N        | 1:N                                      |
|     v            v                                          |
|  Transaction   Dividend                                     |
|     |                                                       |
|     | N:1                                                   |
|     v                                                       |
|   Asset (ticker, name, type)                                |
|                                                             |
+-------------------------------------------------------------+
```

**Preguntas clave en esta fase:**

1. **Que entidades son "de primera clase"?**
   - Transaction, Dividend, Portfolio -> Si
   - "Ganancia" -> No, es calculada

2. **Que relaciones existen?**
   - Un Portfolio tiene muchas Transactions
   - Una Transaction pertenece a un Asset

3. **Que campos son derivados vs almacenados?**
   - `total = price x quantity` -> Lo calculamos o guardamos?
   - Decision: Guardamos (viene del broker, es la fuente de verdad)

4. **Que campos necesitaremos para filtrar/ordenar?**
   - Por fecha -> Indice en `date`
   - Por ticker -> Indice en `ticker`
   - Por portfolio -> Indice en `portfolio_id`

**Entregable:** Diagrama ER y definicion de tablas.

### Fase 2: Arquitectura de Alto Nivel (1 dia)

```
+-------------------------------------------------------------+
|                                                             |
|                    ARQUITECTURA ELEGIDA                      |
|                                                             |
|  +------------------------------------------------------+   |
|  |                    INTERFACES                         |   |
|  |         (Streamlit UI / FastAPI REST)                |   |
|  +---------------------------+--------------------------+   |
|                              |                              |
|                              v                              |
|  +------------------------------------------------------+   |
|  |                    SERVICIOS                          |   |
|  |    (PortfolioService, FundService, AuthService)      |   |
|  +---------------------------+--------------------------+   |
|                              |                              |
|              +---------------+---------------+              |
|              v                               v              |
|  +---------------------+    +---------------------+         |
|  |        CORE         |    |        DATA         |         |
|  |  (Analytics, Tax)   |    |  (Database, Repos)  |         |
|  +---------------------+    +---------------------+         |
|                                                             |
+-------------------------------------------------------------+
```

**Por que esta arquitectura y no otra?**

| Alternativa | Pros | Contras | Veredicto |
|-------------|------|---------|-----------|
| Todo en un archivo | Rapido de empezar | Imposible de mantener | NO |
| MVC clasico | Familiar | Mezcla logica con presentacion | NO |
| Microservicios | Muy escalable | Overkill para este tamano | NO |
| **Hexagonal/Capas** | **Balance perfecto** | **Requiere disciplina** | **SI** |

### Fase 3: Infraestructura Base (3-4 dias)

```
# Estructura de carpetas desde el dia 1
investment_tracker/
├── src/
│   ├── core/           # Logica pura (sin I/O)
│   │   ├── analytics/  # Calculos matematicos
│   │   └── utils.py    # Helpers genericos
│   ├── services/       # Orquestacion
│   ├── data/           # Persistencia
│   │   ├── models.py
│   │   ├── database.py
│   │   └── repositories/
│   └── providers/      # APIs externas
├── app/                # UI Streamlit
├── api/                # REST API
├── tests/
│   ├── unit/
│   └── integration/
└── scripts/            # Utilidades CLI
```

**Decisiones tomadas aqui:**

1. **SQLAlchemy como ORM** (no SQL crudo)
   - Abstrae diferencias entre SQLite y PostgreSQL
   - Migraciones mas faciles
   - Menos errores de SQL injection

2. **Pytest desde el principio**
   - Fixtures reutilizables
   - Tests parametrizados
   - Mejor que unittest

3. **Logging estructurado**
   - No `print()` statements
   - Niveles (DEBUG, INFO, ERROR)
   - Configurable por entorno

### Fase 4: MVP Funcional (1-2 semanas)

Implementar el flujo completo mas simple posible:

```
CSV -> Importar -> Ver Dashboard -> Calcular Fiscalidad
```

**Regla de oro:** Cada feature debe funcionar end-to-end antes de pasar a la siguiente.

### Fase 5: Testing y Refactoring (Continuo)

```
+-------------------------------------------------------------+
|                   PIRAMIDE DE TESTS                          |
+-------------------------------------------------------------+
|                                                             |
|                        /\                                   |
|                       /  \     E2E (pocos)                  |
|                      /    \    - Flujos completos           |
|                     /------\                                |
|                    /        \  Integracion (algunos)        |
|                   /          \ - Servicios + BD             |
|                  /------------\                             |
|                 /              \ Unitarios (muchos)         |
|                /                \ - Funciones puras         |
|               /------------------\                          |
|                                                             |
+-------------------------------------------------------------+
```

### Fase 6: Cloud Migration (1 semana)

1. Detectar entorno (local vs cloud)
2. Anadir soporte PostgreSQL
3. Implementar autenticacion
4. Migrar datos
5. Deploy

---

## Parte 2: Las Preguntas Clave por Etapa

### Etapa: Diseno Inicial

| Pregunta | Por que importa | Nuestra respuesta |
|----------|-----------------|-------------------|
| Necesitamos estado entre sesiones? | Determina si necesitas BD | Si -> SQLite/PostgreSQL |
| Cuantos usuarios concurrentes? | Afecta arquitectura | Pocos -> Monolito suficiente |
| Los datos son sensibles? | Seguridad requerida | Si -> Auth + HTTPS |
| Necesitamos tiempo real? | WebSockets vs polling | No -> Polling/cache OK |
| Multi-tenant o single-tenant? | Modelo de datos | Multi -> portfolio_id |

### Etapa: Modelo de Datos

| Pregunta | Por que importa | Nuestra respuesta |
|----------|-----------------|-------------------|
| SQL o NoSQL? | Estructura de datos | SQL (datos relacionales) |
| Normalizado o denormalizado? | Performance vs consistencia | Normalizado (consistencia) |
| Soft delete o hard delete? | Auditoria/recuperacion | Hard delete (simplicidad) |
| Timestamps automaticos? | Debugging/auditoria | Si (created_at, updated_at) |
| Indices necesarios? | Performance de queries | portfolio_id, ticker, date |

### Etapa: Arquitectura

| Pregunta | Por que importa | Nuestra respuesta |
|----------|-----------------|-------------------|
| Monolito o microservicios? | Complejidad operacional | Monolito modular |
| Donde vive la logica de negocio? | Mantenibilidad | Capa de Servicios |
| Como manejamos errores? | UX y debugging | Excepciones + logging |
| Como compartimos codigo? | DRY principle | Modulo core/ |
| Sync o async? | Performance | Sync (suficiente) |

### Etapa: Cloud

| Pregunta | Por que importa | Nuestra respuesta |
|----------|-----------------|-------------------|
| Vendor lock-in aceptable? | Flexibilidad futura | Minimo (SQLAlchemy abstrae) |
| Como manejamos secretos? | Seguridad | st.secrets + env vars |
| Connection pooling? | Performance BD | Si (pool_pre_ping) |
| Caching necesario? | Latencia | Si (@st.cache_data) |
| CDN para assets? | Performance frontend | No (Streamlit lo maneja) |

---

## Parte 3: Analisis de Decisiones Tecnicas

### Decision 1: SQLAlchemy como ORM

**El problema que resuelve:**

```python
# Sin ORM (SQL crudo)
cursor.execute("""
    SELECT t.*,
           (SELECT SUM(quantity) FROM transactions
            WHERE ticker = t.ticker AND date <= t.date) as cumulative
    FROM transactions t
    WHERE portfolio_id = ?
""", (portfolio_id,))

# Vulnerable a:
# - SQL injection si no escapas bien
# - Errores de sintaxis dificiles de debuggear
# - Codigo diferente para SQLite vs PostgreSQL
```

```python
# Con SQLAlchemy
transactions = session.query(Transaction)\
    .filter(Transaction.portfolio_id == portfolio_id)\
    .all()

# Beneficios:
# - Type hints y autocompletado
# - Mismo codigo para cualquier BD
# - Validacion automatica
# - Migraciones gestionadas
```

**Trade-off aceptado:** Curva de aprendizaje inicial a cambio de mantenibilidad a largo plazo.

### Decision 2: Arquitectura Hexagonal (Capas)

**Que hubiera pasado con "todo en un script"?**

```python
# El enfoque tipico del analista
# archivo: mi_cartera.py (3000 lineas)

import pandas as pd
import streamlit as st
import sqlite3

# Linea 1-500: Funciones de BD mezcladas con logica
def get_data_and_calculate_and_show():
    conn = sqlite3.connect('data.db')
    df = pd.read_sql("SELECT * FROM transactions", conn)

    # Calculos fiscales mezclados con queries
    df['gain'] = df['sell_price'] - df['buy_price']

    # UI mezclada con logica
    st.metric("Ganancia", df['gain'].sum())

    # Mas queries dentro de la misma funcion
    dividends = pd.read_sql("SELECT * FROM dividends", conn)

    # ... 2500 lineas mas asi

# PROBLEMAS:
# 1. Imposible testear (como testeas st.metric?)
# 2. Imposible reusar (la logica esta atada a Streamlit)
# 3. Imposible escalar (todo depende de todo)
# 4. Imposible debuggear (donde esta el bug en 3000 lineas?)
# 5. Imposible colaborar (merge conflicts constantes)
```

**Nuestra solucion con capas:**

```python
# src/core/analytics/performance.py
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    """
    Funcion PURA: entrada -> salida
    - No accede a BD
    - No muestra UI
    - Facil de testear
    """
    excess_returns = returns - risk_free_rate / 252
    return excess_returns.mean() / excess_returns.std() * np.sqrt(252)

# src/services/portfolio_service.py
class PortfolioService:
    """
    ORQUESTADOR: conecta datos con logica
    - Obtiene datos de repositorios
    - Llama a funciones core
    - Devuelve resultados estructurados
    """
    def get_portfolio_metrics(self):
        positions = self.portfolio.get_current_positions()
        returns = self._calculate_returns(positions)
        return {
            'sharpe': calculate_sharpe_ratio(returns, self.risk_free_rate)
        }

# app/pages/1_Dashboard.py
# UI: solo presentacion
data = service.get_dashboard_data()
st.metric("Sharpe Ratio", f"{data['sharpe']:.2f}")
```

**Resultado:**
- Cada pieza es testeable independientemente
- Puedo cambiar de Streamlit a Flask sin tocar la logica
- Puedo anadir una API REST reutilizando los servicios

### Decision 3: Migraciones de Base de Datos

**El problema:**

```python
# Dia 1: Tu modelo
class Transaction:
    id = Column(Integer)
    ticker = Column(String)
    amount = Column(Float)

# Dia 30: "Necesito anadir divisa"
class Transaction:
    id = Column(Integer)
    ticker = Column(String)
    amount = Column(Float)
    currency = Column(String)  # NUEVO

# Que pasa con los datos existentes?
# Sin migraciones: Error o perdida de datos
# Con migraciones: ALTER TABLE + valor por defecto
```

**Nuestra implementacion:**

```python
# scripts/migrations/003_add_portfolio_support.py
def upgrade(engine):
    """Anade portfolio_id a transactions y dividends"""
    with engine.connect() as conn:
        # Verificar si columna existe
        if not column_exists(conn, 'transactions', 'portfolio_id'):
            conn.execute(text(
                "ALTER TABLE transactions ADD COLUMN portfolio_id INTEGER"
            ))
            conn.execute(text(
                "CREATE INDEX idx_trans_portfolio ON transactions(portfolio_id)"
            ))
        conn.commit()
```

**Beneficio:** Podemos evolucionar el modelo sin perder datos ni romper produccion.

### Decision 4: Multi-tenant desde el diseno

**El error comun:**

```python
# "Solo lo voy a usar yo"
# 6 meses despues: "Mi hermano tambien quiere usarlo"

# Sin multi-tenant: Tienes que crear una instancia separada
# Con multi-tenant: Solo creas un nuevo usuario con su portfolio_id
```

**Nuestra implementacion:**

```python
class Transaction(Base):
    # ... otros campos ...
    portfolio_id = Column(Integer, nullable=True, index=True)

# nullable=True para compatibilidad con datos existentes
# index=True porque filtraremos por este campo constantemente
```

**Costo:** Un campo extra en cada query.
**Beneficio:** Escalar a multiples usuarios sin redisenar.

### Decision 5: Deteccion automatica de entorno

**El problema:**

```python
# Codigo que solo funciona en un entorno
db = Database('data/local.db')  # Falla en cloud

# Codigo con flags manuales
if os.getenv('IS_CLOUD') == 'true':  # Propenso a errores
    db = Database(os.getenv('DATABASE_URL'))
```

**Nuestra solucion:**

```python
# src/core/environment.py
def is_cloud_environment() -> bool:
    """Detecta automaticamente basandose en DATABASE_URL"""
    if os.getenv('DATABASE_URL'):
        return True
    if _get_database_url_from_secrets():  # Streamlit secrets
        return True
    return False

# Uso transparente
db = Database()  # Funciona en ambos entornos
```

**Beneficio:** El mismo codigo funciona en local y en cloud sin modificaciones.

---

## Parte 4: Escalabilidad y Preparacion para el Futuro

### Lo que ya esta preparado

#### 1. Separacion de Interfaces

```
+-------------------------------------------------------------+
|                   MISMO BACKEND, MULTIPLES FRONTENDS         |
+-------------------------------------------------------------+
|                                                             |
|   +----------+  +----------+  +----------+  +----------+    |
|   |Streamlit |  | FastAPI  |  |  CLI     |  | Mobile?  |    |
|   |   Web    |  |   REST   |  |  Tool    |  |  App?    |    |
|   +----+-----+  +----+-----+  +----+-----+  +----+-----+    |
|        |             |             |             |          |
|        +-------------+------+------+-------------+          |
|                             |                               |
|                             v                               |
|                    +-----------------+                      |
|                    |    SERVICIOS    |                      |
|                    |  (La misma API) |                      |
|                    +-----------------+                      |
|                                                             |
+-------------------------------------------------------------+
```

**Implicacion:** Manana podrias crear una app movil consumiendo los mismos servicios.

#### 2. Base de datos agnostica

```python
# Tu codigo no sabe (ni le importa) si es SQLite o PostgreSQL
class Database:
    def __init__(self, db_path=None):
        if self._should_use_postgres():
            self.engine = create_engine(DATABASE_URL)
        else:
            self.engine = create_engine(f'sqlite:///{db_path}')
```

**Implicacion:** Podrias migrar a MySQL, Oracle, o cualquier BD SQL sin cambiar la logica de negocio.

#### 3. Caching con invalidacion

```python
@st.cache_data(ttl=60)
def get_cached_dashboard_data(db_path, fiscal_year, fiscal_method):
    # Se cachea automaticamente por 60 segundos
    ...

def invalidate_dashboard_cache():
    # Cuando hay cambios, invalidamos manualmente
    get_cached_dashboard_data.clear()
```

**Implicacion:** Puedes ajustar TTLs segun la carga sin cambiar logica.

#### 4. Autenticacion modular

```python
class AuthService:
    @staticmethod
    def verify_credentials(username, password):
        # Hoy: Verifica contra st.secrets
        # Manana: Podria verificar contra OAuth, LDAP, etc.
        ...
```

**Implicacion:** Cambiar el proveedor de autenticacion no afecta al resto del sistema.

### Lo que queda por hacer (roadmap futuro)

#### Corto plazo (mejoras inmediatas)

```
1. [ ] Anadir mas tests de integracion
2. [ ] Implementar rate limiting en API
3. [ ] Anadir metricas de observabilidad (tiempos de respuesta)
4. [ ] Optimizar queries N+1 en algunas paginas
```

#### Medio plazo (features)

```
1. [ ] Notificaciones (dividendos proximos, alertas de precio)
2. [ ] Importacion automatica desde brokers
3. [ ] Comparacion entre portfolios
4. [ ] Reportes PDF exportables
```

#### Largo plazo (escala)

```
1. [ ] Separar en microservicios si el trafico lo justifica
2. [ ] Anadir read replicas para queries pesadas
3. [ ] Implementar cola de mensajes para operaciones async
4. [ ] CDN para assets si hay muchos usuarios
```

---

## Parte 5: Lecciones Finales

### La diferencia entre Junior y Senior

| Junior | Senior |
|--------|--------|
| "Funciona en mi maquina" | "Funciona en cualquier maquina" |
| Escribe codigo | Disena sistemas |
| Arregla bugs | Previene bugs |
| Copia de Stack Overflow | Entiende por que funciona |
| "Ya lo optimizamos despues" | "Cual es el trade-off?" |
| Un archivo gigante | Modulos con responsabilidades claras |

### Los 5 principios que guiaron este proyecto

1. **Separacion de responsabilidades**
   - Cada modulo hace UNA cosa bien
   - La UI no conoce la BD
   - La BD no conoce la UI

2. **Inversion de dependencias**
   - Los modulos de alto nivel no dependen de los de bajo nivel
   - Ambos dependen de abstracciones (interfaces)

3. **Configuracion sobre codigo**
   - Secretos en variables de entorno, no en codigo
   - TTLs configurables, no hardcodeados

4. **Fail fast, fail loud**
   - Errores explicitos mejor que comportamiento silencioso incorrecto
   - Logging en cada capa

5. **Disenar para el cambio**
   - Asumir que los requisitos van a cambiar
   - Hacer facil lo que probablemente cambiara

### Tu roadmap personal como Data Analyst -> Data Engineer -> Full Stack

```
Nivel 1: Data Analyst
+-- [x] Python basico
+-- [x] Pandas/NumPy
+-- [x] SQL basico
+-- [x] Visualizacion (Matplotlib, Plotly)

Nivel 2: Data Analyst Avanzado (ESTAS AQUI)
+-- [x] Git/GitHub
+-- [x] Streamlit
+-- [x] SQLAlchemy basico
+-- [ ] Testing (pytest)

Nivel 3: Data Engineer Junior
+-- [ ] Docker
+-- [ ] CI/CD (GitHub Actions)
+-- [ ] Cloud basics (AWS/GCP)
+-- [ ] Airflow/Luigi (orquestacion)

Nivel 4: Data Engineer
+-- [ ] Kafka/mensajeria
+-- [ ] Data warehousing (BigQuery, Snowflake)
+-- [ ] Infrastructure as Code (Terraform)
+-- [ ] Kubernetes

Nivel 5: Full Stack
+-- [ ] Frontend moderno (React/Vue)
+-- [ ] APIs REST y GraphQL
+-- [ ] Autenticacion avanzada (OAuth2, JWT)
+-- [ ] System design
```

### Mensaje final

Este proyecto no es perfecto. Tiene deuda tecnica. Algunas decisiones podrian haber sido diferentes. Pero eso esta bien.

La ingenieria de software no es sobre escribir codigo perfecto. Es sobre:
- Tomar decisiones informadas con la informacion disponible
- Documentar por que tomaste esas decisiones
- Construir de forma que puedas cambiar de opinion despues
- Entregar valor mientras mantienes la calidad

Has pasado de "tengo un CSV con mis inversiones" a "tengo una aplicacion en la nube con autenticacion, multiples usuarios, caching, y una arquitectura que puede crecer".

Eso no es "hacer que funcione". Eso es ingenieria.

---

*"Any fool can write code that a computer can understand. Good programmers write code that humans can understand."* - Martin Fowler

---

## Anexo: Glosario de Terminos

| Termino | Definicion |
|---------|------------|
| **ORM** | Object-Relational Mapping. Capa que traduce entre objetos Python y tablas SQL |
| **MVP** | Minimum Viable Product. La version mas simple que entrega valor |
| **TTL** | Time To Live. Tiempo que un dato permanece en cache |
| **Multi-tenant** | Arquitectura donde multiples usuarios comparten la misma instancia |
| **Monolito** | Aplicacion desplegada como una sola unidad |
| **Microservicios** | Aplicacion dividida en servicios independientes |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **Connection Pooling** | Reutilizar conexiones a BD en lugar de crear nuevas |
| **Hexagonal Architecture** | Patron que separa logica de negocio de infraestructura |
| **DRY** | Don't Repeat Yourself. Principio de no duplicar codigo |
