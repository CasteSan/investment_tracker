# Contributing to Investment Tracker

## Normas de Desarrollo

### 1. Arquitectura

**Usar siempre la capa de servicios:**

```python
# CORRECTO - Usar servicios
from src.services import PortfolioService

with PortfolioService() as service:
    data = service.get_dashboard_data()

# INCORRECTO - Acceder directamente a datos desde UI
from src.data import Database
db = Database()
transactions = db.get_transactions()  # NO en codigo de UI
```

### 2. Testing

**Pytest es obligatorio para todo codigo nuevo:**

```bash
# Ejecutar antes de cada commit
python -m pytest tests/unit/ -v
```

**Estructura de tests:**
- Tests unitarios en `tests/unit/`
- Fixtures compartidas en `tests/conftest.py`
- Usar BD temporal: `temp_db_path` fixture

```python
# Ejemplo de test
def test_mi_funcionalidad(portfolio_service):
    result = portfolio_service.mi_metodo()
    assert result is not None
```

### 3. Convenciones de Codigo

**Imports:**
```python
# Orden recomendado
from src.services import PortfolioService, FundService
from src.core.analytics import calculate_sharpe_ratio
from src.data import Database, Fund
```

**Servicios:**
- Heredar de `BaseService`
- Implementar context manager (`with` statement)
- Documentar metodos publicos

**Core (analytics):**
- Funciones puras sin efectos secundarios
- No importar nada de `app/` ni `api/`
- Esperar Series de retornos (no precios)

### 4. Commits

**Formato:**
```
tipo: descripcion breve

Descripcion detallada si es necesario.

Co-Authored-By: Tu Nombre <email>
```

**Tipos:**
- `feat:` - Nueva funcionalidad
- `fix:` - Correccion de bug
- `refactor:` - Refactorizacion sin cambio funcional
- `test:` - Anadir o modificar tests
- `docs:` - Solo documentacion

### 5. Pull Requests

1. Crear rama desde `main`
2. Asegurar que `pytest` pasa
3. Actualizar documentacion si aplica
4. Descripcion clara del cambio

### 6. Estructura de Archivos

```
src/
├── services/      # Capa de servicios (punto de entrada)
├── core/          # Logica pura (sin dependencias)
├── data/          # Acceso a datos (repositories)
└── *.py           # Modulos de negocio

app/               # UI Streamlit (solo presentacion)
api/               # API FastAPI (solo presentacion)
tests/             # Tests pytest
docs/              # Documentacion
```

### 7. Errores Comunes a Evitar

1. **Logica en UI** - Mover a servicios
2. **No cerrar conexiones** - Usar context managers
3. **calculate_cagr()** - Usar `calculate_cagr_from_prices()` para series
4. **SQL disperso** - Usar repositorios
5. **Tests sin fixtures** - Usar `temp_db_path`

## Preguntas

Revisar `CLAUDE.md` para guia detallada de desarrollo.
