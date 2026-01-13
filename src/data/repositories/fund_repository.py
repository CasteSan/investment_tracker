"""
FundRepository - Repositorio para acceso a datos de fondos

Encapsula todas las operaciones de base de datos relacionadas con
el catalogo de fondos. Soporta filtrado avanzado, paginacion y ordenamiento.

Uso:
    from src.data.repositories import FundRepository
    from src.data.database import Database

    db = Database()
    repo = FundRepository(db.session)

    # Buscar fondos de renta variable con bajo coste
    funds = repo.search(
        category='Renta Variable',
        max_ter=1.0,
        min_rating=4
    )

    # Obtener por ISIN
    fund = repo.get_by_isin('ES0114105036')

    db.close()
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

try:
    from src.data.models import Fund
    from src.logger import get_logger
except ImportError:
    from data.models import Fund
    from logger import get_logger

logger = get_logger(__name__)


class FundRepository:
    """
    Repositorio para operaciones CRUD y busqueda de fondos.

    Attributes:
        session: Sesion de SQLAlchemy activa
    """

    def __init__(self, session: Session):
        """
        Inicializa el repositorio con una sesion de BD.

        Args:
            session: Sesion de SQLAlchemy
        """
        self.session = session

    # =========================================================================
    # OPERACIONES CRUD BASICAS
    # =========================================================================

    def get_by_id(self, fund_id: int) -> Optional[Fund]:
        """Obtiene un fondo por su ID."""
        return self.session.query(Fund).filter(Fund.id == fund_id).first()

    def get_by_isin(self, isin: str) -> Optional[Fund]:
        """Obtiene un fondo por su ISIN."""
        return self.session.query(Fund).filter(Fund.isin == isin.upper()).first()

    def get_by_ticker(self, ticker: str) -> Optional[Fund]:
        """Obtiene un fondo por su ticker."""
        return self.session.query(Fund).filter(Fund.ticker == ticker.upper()).first()

    def get_all(self, limit: int = None, offset: int = 0) -> List[Fund]:
        """
        Obtiene todos los fondos con paginacion opcional.

        Args:
            limit: Numero maximo de resultados
            offset: Desplazamiento para paginacion
        """
        query = self.session.query(Fund).offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()

    def count(self) -> int:
        """Retorna el numero total de fondos en el catalogo."""
        return self.session.query(Fund).count()

    def add(self, fund: Fund) -> Fund:
        """
        Anade un nuevo fondo al catalogo.

        Args:
            fund: Instancia de Fund a guardar

        Returns:
            El fondo guardado con ID asignado
        """
        self.session.add(fund)
        self.session.commit()
        self.session.refresh(fund)
        logger.info(f"Fondo anadido: {fund.isin} - {fund.name}")
        return fund

    def add_many(self, funds: List[Fund]) -> int:
        """
        Anade multiples fondos en batch.

        Args:
            funds: Lista de fondos a guardar

        Returns:
            Numero de fondos anadidos
        """
        self.session.add_all(funds)
        self.session.commit()
        logger.info(f"Anadidos {len(funds)} fondos al catalogo")
        return len(funds)

    def update(self, fund: Fund) -> Fund:
        """Actualiza un fondo existente."""
        self.session.commit()
        self.session.refresh(fund)
        return fund

    def delete(self, fund_id: int) -> bool:
        """
        Elimina un fondo por su ID.

        Returns:
            True si se elimino, False si no existia
        """
        fund = self.get_by_id(fund_id)
        if fund:
            self.session.delete(fund)
            self.session.commit()
            logger.info(f"Fondo eliminado: {fund.isin}")
            return True
        return False

    def delete_by_isin(self, isin: str) -> bool:
        """Elimina un fondo por su ISIN."""
        fund = self.get_by_isin(isin)
        if fund:
            self.session.delete(fund)
            self.session.commit()
            return True
        return False

    # =========================================================================
    # METODOS DE BUSQUEDA Y FILTRADO
    # =========================================================================

    def search(
        self,
        # Filtros de texto
        name: str = None,
        isin: str = None,
        manager: str = None,

        # Filtros de categoria
        category: str = None,
        categories: List[str] = None,
        subcategory: str = None,
        asset_class: str = None,
        region: str = None,
        sector: str = None,

        # Filtros de costes
        max_ter: float = None,
        min_ter: float = None,

        # Filtros de riesgo
        risk_level: int = None,
        max_risk_level: int = None,
        min_risk_level: int = None,

        # Filtros de rating
        min_rating: int = None,
        max_rating: int = None,

        # Filtros de rendimiento
        min_return_1y: float = None,
        min_return_3y: float = None,

        # Filtros de tamano
        min_aum: float = None,
        max_min_investment: float = None,

        # Otros filtros
        currency: str = None,
        distribution_policy: str = None,
        hedged: bool = None,

        # Ordenamiento y paginacion
        order_by: str = 'name',
        order_desc: bool = False,
        limit: int = None,
        offset: int = 0,
    ) -> List[Fund]:
        """
        Busqueda avanzada de fondos con multiples filtros.

        Args:
            name: Busca en nombre (contiene)
            isin: Busca por ISIN exacto o parcial
            manager: Filtra por gestora (contiene)
            category: Categoria exacta
            categories: Lista de categorias (OR)
            subcategory: Subcategoria exacta
            asset_class: Clase de activo
            region: Region geografica
            sector: Sector
            max_ter: TER maximo
            min_ter: TER minimo
            risk_level: Nivel de riesgo exacto (1-7)
            max_risk_level: Riesgo maximo
            min_risk_level: Riesgo minimo
            min_rating: Rating Morningstar minimo (1-5)
            max_rating: Rating Morningstar maximo
            min_return_1y: Rentabilidad 1 ano minima (%)
            min_return_3y: Rentabilidad 3 anos minima (%)
            min_aum: Patrimonio minimo (millones)
            max_min_investment: Inversion minima maxima
            currency: Divisa
            distribution_policy: 'accumulation' o 'distribution'
            hedged: Si tiene cobertura de divisa
            order_by: Campo para ordenar (name, ter, risk_level, return_1y, etc.)
            order_desc: True para orden descendente
            limit: Limite de resultados
            offset: Desplazamiento

        Returns:
            Lista de fondos que cumplen los criterios
        """
        query = self.session.query(Fund)
        filters = []

        # Filtros de texto (busqueda parcial case-insensitive)
        if name:
            filters.append(Fund.name.ilike(f'%{name}%'))
        if isin:
            filters.append(Fund.isin.ilike(f'%{isin}%'))
        if manager:
            filters.append(Fund.manager.ilike(f'%{manager}%'))

        # Filtros de categoria
        if category:
            filters.append(Fund.category == category)
        if categories:
            filters.append(Fund.category.in_(categories))
        if subcategory:
            filters.append(Fund.subcategory == subcategory)
        if asset_class:
            filters.append(Fund.asset_class == asset_class)
        if region:
            filters.append(Fund.region == region)
        if sector:
            filters.append(Fund.sector == sector)

        # Filtros de costes
        if max_ter is not None:
            filters.append(Fund.ter <= max_ter)
        if min_ter is not None:
            filters.append(Fund.ter >= min_ter)

        # Filtros de riesgo
        if risk_level is not None:
            filters.append(Fund.risk_level == risk_level)
        if max_risk_level is not None:
            filters.append(Fund.risk_level <= max_risk_level)
        if min_risk_level is not None:
            filters.append(Fund.risk_level >= min_risk_level)

        # Filtros de rating
        if min_rating is not None:
            filters.append(Fund.morningstar_rating >= min_rating)
        if max_rating is not None:
            filters.append(Fund.morningstar_rating <= max_rating)

        # Filtros de rendimiento
        if min_return_1y is not None:
            filters.append(Fund.return_1y >= min_return_1y)
        if min_return_3y is not None:
            filters.append(Fund.return_3y >= min_return_3y)

        # Filtros de tamano
        if min_aum is not None:
            filters.append(Fund.aum >= min_aum)
        if max_min_investment is not None:
            filters.append(Fund.min_investment <= max_min_investment)

        # Otros filtros
        if currency:
            filters.append(Fund.currency == currency)
        if distribution_policy:
            filters.append(Fund.distribution_policy == distribution_policy)
        if hedged is not None:
            filters.append(Fund.hedged == hedged)

        # Aplicar filtros
        if filters:
            query = query.filter(and_(*filters))

        # Ordenamiento
        order_column = getattr(Fund, order_by, Fund.name)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        # Paginacion
        query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def find_by_category(self, category: str) -> List[Fund]:
        """Busca fondos por categoria."""
        return self.search(category=category)

    def find_by_manager(self, manager: str) -> List[Fund]:
        """Busca fondos por gestora."""
        return self.search(manager=manager)

    def find_low_cost(self, max_ter: float = 0.5) -> List[Fund]:
        """Busca fondos de bajo coste (TER <= max_ter)."""
        return self.search(max_ter=max_ter, order_by='ter')

    def find_top_rated(self, min_rating: int = 4) -> List[Fund]:
        """Busca fondos con rating alto (>= min_rating estrellas)."""
        return self.search(min_rating=min_rating, order_by='morningstar_rating', order_desc=True)

    def find_low_risk(self, max_risk: int = 3) -> List[Fund]:
        """Busca fondos de bajo riesgo (nivel <= max_risk)."""
        return self.search(max_risk_level=max_risk, order_by='risk_level')

    def find_best_performers(self, period: str = '1y', top_n: int = 10) -> List[Fund]:
        """
        Busca los fondos con mejor rendimiento.

        Args:
            period: '1y', '3y', '5y'
            top_n: Numero de resultados
        """
        order_field = f'return_{period}'
        return self.search(order_by=order_field, order_desc=True, limit=top_n)

    # =========================================================================
    # METODOS DE AGREGACION
    # =========================================================================

    def get_categories(self) -> List[str]:
        """Obtiene lista de categorias unicas."""
        result = self.session.query(Fund.category).distinct().all()
        return sorted([r[0] for r in result if r[0]])

    def get_managers(self) -> List[str]:
        """Obtiene lista de gestoras unicas."""
        result = self.session.query(Fund.manager).distinct().all()
        return sorted([r[0] for r in result if r[0]])

    def get_regions(self) -> List[str]:
        """Obtiene lista de regiones unicas."""
        result = self.session.query(Fund.region).distinct().all()
        return sorted([r[0] for r in result if r[0]])

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadisticas del catalogo.

        Returns:
            Dict con conteos por categoria, gestora, etc.
        """
        from sqlalchemy import func

        total = self.count()

        # Conteo por categoria
        by_category = dict(
            self.session.query(Fund.category, func.count(Fund.id))
            .group_by(Fund.category)
            .all()
        )

        # Conteo por riesgo
        by_risk = dict(
            self.session.query(Fund.risk_level, func.count(Fund.id))
            .group_by(Fund.risk_level)
            .all()
        )

        # Top gestoras
        top_managers = (
            self.session.query(Fund.manager, func.count(Fund.id))
            .group_by(Fund.manager)
            .order_by(desc(func.count(Fund.id)))
            .limit(10)
            .all()
        )

        return {
            'total_funds': total,
            'by_category': by_category,
            'by_risk_level': by_risk,
            'top_managers': dict(top_managers),
            'num_categories': len(by_category),
            'num_managers': len(self.get_managers()),
        }

    # =========================================================================
    # METODOS DE IMPORTACION
    # =========================================================================

    def upsert(self, fund_data: Dict[str, Any]) -> Fund:
        """
        Inserta o actualiza un fondo por ISIN.

        Args:
            fund_data: Diccionario con datos del fondo (debe incluir 'isin')

        Returns:
            El fondo insertado o actualizado
        """
        isin = fund_data.get('isin')
        if not isin:
            raise ValueError("El campo 'isin' es requerido")

        existing = self.get_by_isin(isin)

        if existing:
            # Actualizar campos
            for key, value in fund_data.items():
                if hasattr(existing, key) and key != 'id':
                    setattr(existing, key, value)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Crear nuevo
            fund = Fund(**fund_data)
            return self.add(fund)

    def bulk_upsert(self, funds_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Inserta o actualiza multiples fondos.

        Returns:
            Dict con conteo de insertados y actualizados
        """
        inserted = 0
        updated = 0

        for fund_data in funds_data:
            isin = fund_data.get('isin')
            if not isin:
                continue

            existing = self.get_by_isin(isin)
            if existing:
                for key, value in fund_data.items():
                    if hasattr(existing, key) and key != 'id':
                        setattr(existing, key, value)
                updated += 1
            else:
                fund = Fund(**fund_data)
                self.session.add(fund)
                inserted += 1

        self.session.commit()
        logger.info(f"Bulk upsert: {inserted} insertados, {updated} actualizados")

        return {'inserted': inserted, 'updated': updated}
