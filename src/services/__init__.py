"""
Capa de Servicios (Service Layer)

Esta capa actúa como puente entre la UI (Streamlit/FastAPI) y la lógica
de negocio (Core). Los servicios:

- Orquestan operaciones complejas
- NO conocen la UI (no importan Streamlit ni FastAPI)
- Devuelven datos estructurados (dicts, dataclasses)
- Manejan transacciones y errores de dominio

Servicios disponibles:
- PortfolioService: Gestión de cartera y posiciones (futuro)
- ReportService: Generación de informes (futuro)
- FundService: Catálogo de fondos (futuro)

Uso:
    from src.services import PortfolioService

    service = PortfolioService()
    data = service.get_dashboard_data()
"""

from src.services.base import BaseService

__all__ = [
    'BaseService',
]
