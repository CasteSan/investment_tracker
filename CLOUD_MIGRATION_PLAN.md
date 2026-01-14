# Cloud Migration Plan: Investment Tracker Web Service

Plan de migración para transformar la aplicación local en un servicio web seguro con arquitectura híbrida.

---

## Objetivo

Crear una aplicación que funcione en **dos modos** con el mismo código:

| Aspecto | Modo Local | Modo Cloud |
|---------|------------|------------|
| Base de datos | SQLite (archivos `.db`) | PostgreSQL (Supabase) |
| Carteras | Múltiples, selector visible | Una por usuario, selector oculto |
| Autenticación | Ninguna | Email/Password via `st.secrets` |
| ProfileManager | `LocalProfileManager` | `CloudProfileManager` |

---

## Stack Tecnológico

- **Frontend/Hosting:** Streamlit Community Cloud (Free)
- **Database Cloud:** Supabase PostgreSQL (Free Tier)
- **Autenticación:** `st.secrets` (MVP simple y seguro)
- **Conexión BD:** `DATABASE_URL` directa (NO usar claves de API)

---

## Arquitectura Híbrida: "Adaptive Multi-Tenancy"

### Detección de Entorno

```python
# src/core/environment.py
import os

def is_cloud_environment() -> bool:
    """Detecta si estamos en la nube."""
    return os.getenv('DATABASE_URL') is not None

def get_environment_name() -> str:
    return 'cloud' if is_cloud_environment() else 'local'
```

### Diagrama de Flujo

```
                         App Startup
                              │
                              ▼
                  ┌───────────────────────┐
                  │  DATABASE_URL exists? │
                  └───────────┬───────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼ NO                          ▼ YES
    ┌─────────────────────┐       ┌─────────────────────┐
    │    MODO LOCAL       │       │    MODO CLOUD       │
    ├─────────────────────┤       ├─────────────────────┤
    │ - SQLite files      │       │ - PostgreSQL        │
    │ - LocalProfileMgr   │       │ - CloudProfileMgr   │
    │ - Selector visible  │       │ - Auth required     │
    │ - Multi-portfolio   │       │ - Selector oculto   │
    └─────────────────────┘       │ - Single portfolio  │
                                  └─────────────────────┘
```

### Abstracción del ProfileManager

```python
# src/core/profile_manager.py

from typing import Protocol

class ProfileManagerProtocol(Protocol):
    """Interfaz común para ambos modos."""

    def get_current_portfolio_id(self) -> int | str: ...
    def get_portfolio_name(self) -> str: ...
    def list_portfolios(self) -> list[str]: ...
    def can_switch_portfolio(self) -> bool: ...
    def switch_portfolio(self, name: str) -> None: ...


class LocalProfileManager:
    """Modo local: múltiples SQLite, selector libre."""

    def can_switch_portfolio(self) -> bool:
        return True  # Permite cambiar

    def list_portfolios(self) -> list[str]:
        # Retorna todos los .db en data/portfolios/
        ...


class CloudProfileManager:
    """Modo cloud: PostgreSQL, cartera fija por usuario."""

    def __init__(self, user_email: str, portfolio_id: int):
        self.user_email = user_email
        self.portfolio_id = portfolio_id

    def can_switch_portfolio(self) -> bool:
        return False  # NO permite cambiar

    def list_portfolios(self) -> list[str]:
        return [self.get_portfolio_name()]  # Solo una
```

### Factory Function

```python
# src/core/profile_factory.py

def get_profile_manager(session_state: dict) -> ProfileManagerProtocol:
    """Retorna el ProfileManager adecuado según el entorno."""

    if is_cloud_environment():
        user_email = session_state.get('user_email')
        portfolio_id = session_state.get('portfolio_id')
        return CloudProfileManager(user_email, portfolio_id)
    else:
        return LocalProfileManager()
```

### Uso en UI (Sidebar)

```python
# app/main.py

pm = get_profile_manager(st.session_state)

# El selector SOLO aparece si el ProfileManager lo permite
if pm.can_switch_portfolio():
    portfolios = pm.list_portfolios()
    selected = st.sidebar.selectbox("Cartera", portfolios)
    if selected != pm.get_portfolio_name():
        pm.switch_portfolio(selected)
        st.rerun()
else:
    # Modo cloud: mostrar nombre sin opción de cambiar
    st.sidebar.info(f"Cartera: {pm.get_portfolio_name()}")
```

---

## Modelo de Datos PostgreSQL

### Nuevas Tablas

```sql
-- Tabla de portfolios (reemplaza archivos .db)
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Las tablas existentes añaden portfolio_id
ALTER TABLE transactions ADD COLUMN portfolio_id INTEGER REFERENCES portfolios(id);
ALTER TABLE dividends ADD COLUMN portfolio_id INTEGER REFERENCES portfolios(id);

-- Índices para performance
CREATE INDEX idx_transactions_portfolio ON transactions(portfolio_id);
CREATE INDEX idx_dividends_portfolio ON dividends(portfolio_id);
```

**Nota:** La tabla `funds` es global (catálogo compartido), no necesita `portfolio_id`.

### Mapeo Usuario -> Portfolio (en secrets)

```toml
# .streamlit/secrets.toml (configurado en Streamlit Cloud, NO en git)

DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

[auth]
# Usuarios autorizados con su portfolio asignado
[auth.users.juan]
password = "hashed_password_here"
portfolio_id = 1

[auth.users.maria]
password = "hashed_password_here"
portfolio_id = 2
```

**Ventaja:** No necesitamos tabla `users` en BD. Los usuarios se gestionan en secrets (suficiente para pocos usuarios).

---

## Sistema de Autenticación MVP

### Flujo de Login

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Usuario     │────>│  Verificar en   │────>│  Cargar          │
│  Email/Pass  │     │  st.secrets     │     │  portfolio_id    │
└──────────────┘     └─────────────────┘     └──────────────────┘
                              │                       │
                              ▼                       ▼
                     ┌─────────────────┐     ┌──────────────────┐
                     │  session_state  │     │  CloudProfile    │
                     │  authenticated  │     │  Manager         │
                     │  = True         │     │  inicializado    │
                     └─────────────────┘     └──────────────────┘
```

### Implementación

```python
# src/services/auth_service.py

import hashlib
import streamlit as st

class AuthService:
    """Autenticación simple usando st.secrets."""

    @staticmethod
    def verify_credentials(username: str, password: str) -> dict | None:
        """Verifica credenciales y retorna info del usuario."""
        users = st.secrets.get('auth', {}).get('users', {})

        user_data = users.get(username)
        if not user_data:
            return None

        # Verificar password (hash SHA256)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user_data.get('password'):
            return None

        return {
            'username': username,
            'portfolio_id': user_data.get('portfolio_id')
        }

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.get('authenticated', False)

    @staticmethod
    def get_current_user() -> dict | None:
        if not AuthService.is_authenticated():
            return None
        return {
            'username': st.session_state.get('username'),
            'portfolio_id': st.session_state.get('portfolio_id')
        }
```

### Componente de Login

```python
# app/components/login.py

def render_login_form():
    """Renderiza formulario de login. Retorna True si autenticado."""

    if AuthService.is_authenticated():
        return True

    st.title("Investment Tracker")

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            user = AuthService.verify_credentials(username, password)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['username'] = user['username']
                st.session_state['portfolio_id'] = user['portfolio_id']
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

    return False
```

---

## Fases de Implementación

### Fase 1: Infraestructura Base
**Objetivo:** Crear la capa de abstracción sin romper funcionalidad local.

| # | Tarea | Archivos |
|---|-------|----------|
| 1.1 | Crear módulo de detección de entorno | `src/core/environment.py` |
| 1.2 | Definir `ProfileManagerProtocol` | `src/core/profile_manager.py` |
| 1.3 | Refactorizar `LocalProfileManager` para implementar protocolo | `src/core/profile_manager.py` |
| 1.4 | Crear `CloudProfileManager` (stub) | `src/core/cloud_profile_manager.py` |
| 1.5 | Crear factory `get_profile_manager()` | `src/core/profile_factory.py` |
| 1.6 | Tests unitarios | `tests/unit/test_environment.py` |

**Validación:** App local funciona exactamente igual.

**Commit:** `feat(cloud): add environment detection and ProfileManager abstraction`

---

### Fase 2: Modelo de Datos Unificado
**Objetivo:** Adaptar modelos para soportar `portfolio_id`.

| # | Tarea | Archivos |
|---|-------|----------|
| 2.1 | Crear modelo `Portfolio` | `src/data/models.py` |
| 2.2 | Añadir `portfolio_id` a `Transaction` | `src/data/models.py` |
| 2.3 | Añadir `portfolio_id` a `Dividend` | `src/data/models.py` |
| 2.4 | Crear migración para SQLite local | `src/data/migrations/` |
| 2.5 | Actualizar repositories con filtro `portfolio_id` | `src/data/repositories/*.py` |
| 2.6 | Tests unitarios | `tests/unit/test_models.py` |

**Validación:** App local funciona con nuevos campos (nullable para compatibilidad).

**Commit:** `feat(cloud): add Portfolio model and portfolio_id to transactions`

---

### Fase 3: Soporte PostgreSQL
**Objetivo:** Database.py capaz de conectar a Postgres.

| # | Tarea | Archivos |
|---|-------|----------|
| 3.1 | Añadir `psycopg2-binary` a requirements | `requirements.txt` |
| 3.2 | Modificar `Database` para detectar `DATABASE_URL` | `src/data/database.py` |
| 3.3 | Ajustar tipos de datos para compatibilidad SQLite/Postgres | `src/data/models.py` |
| 3.4 | Tests con ambos backends | `tests/unit/test_database.py` |

**Validación:** Tests pasan con SQLite y PostgreSQL.

**Commit:** `feat(cloud): add PostgreSQL support in Database class`

---

### Fase 4: Script de Migración
**Objetivo:** Migrar datos locales a Supabase.

| # | Tarea | Archivos |
|---|-------|----------|
| 4.1 | Crear script de migración | `scripts/migrate_to_cloud.py` |
| 4.2 | Leer todos los SQLite en `data/portfolios/` | - |
| 4.3 | Crear portfolios en Postgres | - |
| 4.4 | Migrar transacciones/dividendos con `portfolio_id` | - |
| 4.5 | Verificar integridad de datos | - |
| 4.6 | Generar reporte de migración | - |

**Uso:**
```bash
# Requiere DATABASE_URL en entorno
python scripts/migrate_to_cloud.py --source data/portfolios/ --dry-run
python scripts/migrate_to_cloud.py --source data/portfolios/ --execute
```

**Commit:** `feat(cloud): add migration script for SQLite to PostgreSQL`

---

### Fase 5: Autenticación
**Objetivo:** Proteger acceso en modo cloud.

| # | Tarea | Archivos |
|---|-------|----------|
| 5.1 | Crear `AuthService` | `src/services/auth_service.py` |
| 5.2 | Crear componente de login | `app/components/login.py` |
| 5.3 | Integrar auth en `app/main.py` | `app/main.py` |
| 5.4 | Condicionar sidebar según `can_switch_portfolio()` | `app/main.py` |
| 5.5 | Tests de AuthService | `tests/unit/test_auth_service.py` |

**Validación:**
- Local: App inicia sin login, selector visible
- Cloud: Login requerido, selector oculto

**Commit:** `feat(cloud): add authentication layer with portfolio restriction`

---

### Fase 6: Deployment
**Objetivo:** Desplegar en Streamlit Cloud.

| # | Tarea | Archivos |
|---|-------|----------|
| 6.1 | Limpiar `requirements.txt` | `requirements.txt` |
| 6.2 | Crear template de secrets | `.streamlit/secrets.toml.example` |
| 6.3 | Crear guía de deployment | `docs/DEPLOYMENT_GUIDE.md` |
| 6.4 | Configurar secrets en Streamlit Cloud Dashboard | - |
| 6.5 | Deploy y verificación | - |

**Commit:** `docs(cloud): add deployment guide and secrets template`

---

## Configuración de Secrets

### Template: `.streamlit/secrets.toml.example`

```toml
# INSTRUCCIONES:
# 1. NO commitear este archivo con valores reales
# 2. Copiar estos valores al Dashboard de Streamlit Cloud
# 3. Settings > Secrets > Paste content

# Conexión directa a PostgreSQL (Supabase)
# Obtener de: Supabase Dashboard > Settings > Database > Connection String
DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"

# Usuarios autorizados
# Password: SHA256 hash (python: hashlib.sha256(b"password").hexdigest())
[auth.users]

[auth.users.juan]
password = "5e884898da28047d9..."
portfolio_id = 1

[auth.users.maria]
password = "ef92b778bafe771e..."
portfolio_id = 2
```

---

## Checklist Pre-Implementación

- [ ] Usuario tiene cuenta en Streamlit Cloud
- [ ] Usuario tiene proyecto en Supabase
- [ ] Usuario tiene `DATABASE_URL` de Supabase
- [ ] Repositorio en GitHub actualizado
- [ ] Backup de datos locales realizado

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Pérdida de datos en migración | Media | Dry-run + backup previo |
| Incompatibilidad SQLAlchemy/Postgres | Baja | Tests con ambos backends |
| Secrets expuestos | Baja | Nunca commitear `.toml` real |
| Rate limiting Supabase | Baja | Free tier suficiente para uso personal |

---

## Notas de Seguridad

1. **DATABASE_URL**: Contiene credenciales. NUNCA commitear.
2. **Passwords en secrets**: Usar SHA256 hash, no plaintext.
3. **service_role key de Supabase**: NO usar. Acceso directo via `DATABASE_URL`.
4. **Archivos `.db` locales**: Añadir a `.gitignore` (ya está).

---

## Resultado Final Esperado

```
MODO LOCAL (desarrollo):
┌─────────────────────────────────┐
│  Investment Tracker             │
├─────────────────────────────────┤
│  Sidebar:                       │
│  ┌─────────────────────────┐   │
│  │ Cartera: [Principal  v] │   │  <- Selector VISIBLE
│  │    - Principal          │   │
│  │    - Jubilación         │   │
│  │    - Trading            │   │
│  └─────────────────────────┘   │
│  [+ Nueva cartera]              │
└─────────────────────────────────┘

MODO CLOUD (producción):
┌─────────────────────────────────┐
│  Login                          │
│  Usuario: [__________]          │
│  Pass:    [__________]          │
│  [Entrar]                       │
└─────────────────────────────────┘
           │
           v (después de login)
┌─────────────────────────────────┐
│  Investment Tracker             │
├─────────────────────────────────┤
│  Sidebar:                       │
│  ┌─────────────────────────┐   │
│  │ Usuario: juan           │   │
│  │ Cartera: Mi Cartera     │   │  <- Solo INFO, sin selector
│  └─────────────────────────┘   │
│  [Cerrar sesión]                │
└─────────────────────────────────┘
```
