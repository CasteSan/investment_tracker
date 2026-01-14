# Estado Actual del Proyecto - Investment Tracker

## Resumen

**Version:** 1.3.0
**Estado:** Migración Cloud en progreso (Fase 1 completada)

## Progreso Cloud Migration

| Fase | Estado | Descripción |
|------|--------|-------------|
| Fase 1: Infraestructura Base | ✅ Completada | Environment detection + ProfileManager abstraction |
| Fase 2: Modelo de Datos Unificado | ⏳ Pendiente | Portfolio model + portfolio_id |
| Fase 3: Soporte PostgreSQL | ⏳ Pendiente | DATABASE_URL en Database class |
| Fase 4: Script Migración | ⏳ Pendiente | SQLite → PostgreSQL |
| Fase 5: Autenticación | ⏳ Pendiente | AuthService + Login UI |
| Fase 6: Deployment | ⏳ Pendiente | Streamlit Cloud |

## Cambios Fase 1 (Actual)

### Archivos Nuevos
- `src/core/environment.py` - Detección de entorno (local vs cloud)
- `src/core/cloud_profile_manager.py` - ProfileManager para modo cloud
- `tests/unit/test_environment.py` - 25 tests para nuevos módulos

### Archivos Modificados
- `src/core/profile_manager.py` - Añadido ProfileManagerProtocol, refactorizado a LocalProfileManager
- `src/core/__init__.py` - Exportaciones actualizadas

### Conceptos Clave

```python
# Detección de entorno
from src.core import is_cloud_environment, get_environment

if is_cloud_environment():
    # PostgreSQL + auth requerida
    ...
else:
    # SQLite + sin auth
    ...

# ProfileManager polimórfico
from src.core import get_profile_manager

pm = get_profile_manager(session_state)
if pm.can_switch_portfolio():
    # Modo local: mostrar selector
    ...
else:
    # Modo cloud: ocultar selector
    ...
```

## Estructura Actual

```
investment_tracker/
├── api/                    # FastAPI
├── app/                    # Streamlit (8 páginas)
├── docs/                   # Documentación
├── scripts/                # Scripts utilitarios
├── src/
│   ├── core/
│   │   ├── analytics/      # Métricas (Sharpe, Beta, etc.)
│   │   ├── environment.py  # [NEW] Detección entorno
│   │   ├── cloud_profile_manager.py  # [NEW] Cloud PM
│   │   ├── profile_manager.py  # [UPDATED] Local PM + Protocol
│   │   └── utils.py
│   ├── services/           # PortfolioService, FundService
│   └── data/               # Database, Repositories
├── data/portfolios/        # SQLite files (modo local)
├── tests/unit/             # 207 tests
├── CLOUD_MIGRATION_PLAN.md # Plan detallado
├── CHANGELOG.md
└── CURRENT_SESSION.md      # Este archivo
```

## Tests

```
207 passed, 2 skipped in 32s

Nuevos tests (Fase 1):
- test_environment.py: 25 tests
  - TestEnvironmentDetection: 4 tests
  - TestCloudProfileManager: 14 tests
  - TestProfileManagerProtocol: 2 tests
  - TestGetProfileManagerFactory: 4 tests
  - TestLocalProfileManagerCanSwitch: 1 test
```

## Comandos

```bash
# App local
streamlit run app/main.py

# Tests
python -m pytest tests/unit/ -v

# Verificar imports
python -c "from src.core import is_cloud_environment; print(is_cloud_environment())"
```

## Próximo Paso

**Fase 2: Modelo de Datos Unificado**
- Crear modelo `Portfolio` en `src/data/models.py`
- Añadir `portfolio_id` a Transaction y Dividend
- Crear migración SQLite
- Actualizar repositories

## Arquitectura Híbrida

```
                    ┌─────────────────┐
                    │  get_profile_   │
                    │    manager()    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼ DATABASE_URL?               ▼ No DATABASE_URL
    ┌─────────────────────┐       ┌─────────────────────┐
    │ CloudProfileManager │       │ LocalProfileManager │
    ├─────────────────────┤       ├─────────────────────┤
    │ can_switch: False   │       │ can_switch: True    │
    │ portfolios: 1       │       │ portfolios: N       │
    │ db: PostgreSQL      │       │ db: SQLite files    │
    └─────────────────────┘       └─────────────────────┘
```
