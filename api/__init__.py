"""
API Module - FastAPI REST API

API REST que demuestra la escalabilidad de la arquitectura.
Consume los MISMOS servicios que Streamlit (PortfolioService, FundService).

Endpoints:
    GET  /                    - Health check
    GET  /dashboard           - Datos del dashboard
    GET  /dashboard/metrics   - Metricas avanzadas (Sharpe, Beta, etc.)
    GET  /funds               - Buscar fondos
    GET  /funds/{isin}        - Detalle de fondo
    GET  /benchmarks          - Benchmarks disponibles
    GET  /funds/stats/catalog - Estadisticas del catalogo

Uso:
    uvicorn api.main:app --reload

    # Con host y puerto especificos
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Documentacion interactiva:
    http://localhost:8000/docs     (Swagger UI)
    http://localhost:8000/redoc    (ReDoc)
"""

from api.main import app

__all__ = ["app"]
