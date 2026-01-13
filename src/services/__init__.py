"""
Capa de Servicios (Service Layer)

Esta capa actua como puente entre la UI (Streamlit/FastAPI) y la logica
de negocio (Core). Los servicios:

- Orquestan operaciones complejas
- NO conocen la UI (no importan Streamlit ni FastAPI)
- Devuelven datos estructurados (dicts, dataclasses)
- Manejan transacciones y errores de dominio

Servicios disponibles:
- PortfolioService: Gestion de cartera y posiciones
- FundService: Catalogo de fondos de inversion
- ReportService: Generacion de informes (futuro)

Uso:
    from src.services import PortfolioService, FundService

    with PortfolioService() as service:
        data = service.get_dashboard_data()

    with FundService() as fund_svc:
        funds = fund_svc.search_funds(category='Renta Variable')
"""

from src.services.base import BaseService, ServiceResult
from src.services.portfolio_service import PortfolioService
from src.services.fund_service import FundService

__all__ = [
    'BaseService',
    'ServiceResult',
    'PortfolioService',
    'FundService',
]
