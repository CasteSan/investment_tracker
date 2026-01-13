# Estado Actual del Proyecto - Investment Tracker

## Resumen

**Version:** 1.2.0
**Estado:** Multi-Portfolio implementado

## Progreso

| Fase | Estado | Descripcion |
|------|--------|-------------|
| Plan escalabilidad | ✅ 8/8 | Arquitectura hexagonal implementada |
| Bug fixes | ✅ | get_transaction_by_id, calculate_cagr, yfinance |
| Limpieza | ✅ | 39 archivos obsoletos eliminados |
| Heatmap Dashboard | ✅ | Treemap interactivo con variacion diaria |
| Etiquetas graficos | ✅ | Nombres de activos con truncado inteligente |
| Multi-Portfolio | ✅ | Multiples carteras independientes |

## Ultimo Commit

```
02b4424 - docs: update changelog for v1.2.0 multi-portfolio release
a87a8f6 - feat: add multi-portfolio support and fix db_path sync issues
```

**Cambios v1.2.0:**
- Multi-Portfolio con ProfileManager (`src/core/profile_manager.py`)
- Cada cartera usa SQLite separado en `data/portfolios/`
- Selector de cartera en sidebar (crear/renombrar)
- Migracion automatica de `database.db` a `portfolios/Principal.db`
- Fix: todas las paginas usan `db_path` de session_state
- Fix: Benchmarks filtra dias sin precios reales (`has_market_prices`)
- 184 tests unitarios (+21 nuevos)

## Estructura Actual

```
investment_tracker/
├── api/                    # FastAPI
├── app/                    # Streamlit (8 paginas)
├── docs/architecture/      # Documentacion tecnica
├── scripts/                # Scripts utilitarios
├── src/                    # Codigo fuente
│   ├── services/           # PortfolioService, FundService
│   ├── core/               # ProfileManager, utils.py, analytics/
│   └── data/               # Database, Repositories
├── data/
│   └── portfolios/         # SQLite files por cartera (*.db)
├── tests/
│   ├── unit/               # 184 tests
│   └── scripts/            # Tests de scripts
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

## Archivos Clave Multi-Portfolio

```python
# ProfileManager - Gestor de carteras
from src.core.profile_manager import ProfileManager, get_profile_manager

pm = get_profile_manager()
pm.create_profile('NuevaCartera')
pm.get_db_path('NuevaCartera')  # Ruta al SQLite
pm.rename_profile('Viejo', 'Nuevo')

# En Streamlit - usar db_path de session_state
db_path = st.session_state.get('db_path')
service = PortfolioService(db_path=db_path)
```

## Comandos Principales

```bash
# App
streamlit run app/main.py
uvicorn api.main:app --reload

# Tests
python -m pytest tests/unit/ -v   # 184 tests

# Verificar
python -c "from src.core import ProfileManager; print('OK')"
```

## Tests

```
184 passed, 2 skipped in 24s

- test_analytics.py: 32 tests
- test_fund_repository.py: 37 tests
- test_fund_service.py: 28 tests
- test_portfolio_service.py: 55 tests
- test_profile_manager.py: 21 tests (nuevo)
- test_utils.py: 11 tests
```

## Limitaciones Conocidas

- **yfinance + ISINs europeos:** Fondos mutuos no disponibles
- **Precios fondos:** Solo ETFs/acciones con ticker Yahoo
- **Windows SQLite:** Tests de delete/rename skipped por file locking

## Proximos Pasos Sugeridos

1. **API de precios alternativa** - Morningstar/Investing.com
2. **Autenticacion API** - JWT tokens
3. **Tests de integracion** - TestClient FastAPI
4. **CI/CD** - GitHub Actions
5. **Docker** - Containerizacion
