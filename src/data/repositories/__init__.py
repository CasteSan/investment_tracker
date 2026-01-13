"""
Repositories - Capa de acceso a datos

Este paquete contiene repositorios que encapsulan la logica de acceso
a la base de datos para cada entidad del dominio.

Patron Repository:
- Abstrae la capa de persistencia
- Permite cambiar BD sin afectar logica de negocio
- Facilita testing con mocks/stubs

Uso:
    from src.data.repositories import FundRepository

    repo = FundRepository(db_session)
    funds = repo.find_by_category('Renta Variable')
"""

from src.data.repositories.fund_repository import FundRepository

__all__ = ['FundRepository']
