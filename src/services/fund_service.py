"""
FundService - Servicio para catalogo de fondos de inversion

Este servicio actua como puente entre la UI y el repositorio de fondos.
Proporciona metodos de alto nivel para buscar, filtrar y gestionar fondos.

Uso:
    from src.services.fund_service import FundService

    with FundService() as service:
        # Buscar fondos
        funds = service.search_funds(
            category='Renta Variable',
            max_ter=1.0,
            min_rating=4
        )

        # Obtener estadisticas
        stats = service.get_catalog_stats()
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

try:
    from src.services.base import BaseService
    from src.data.models import Fund, Category, FUND_CATEGORIES, FUND_REGIONS, FUND_RISK_LEVELS, DEFAULT_CUSTOM_CATEGORIES
    from src.data.repositories.fund_repository import FundRepository
    from src.providers.morningstar import (
        FundDataProvider,
        FundNotFoundError,
        FundDataProviderError
    )
    from src.logger import get_logger
except ImportError:
    from services.base import BaseService
    from data.models import Fund, Category, FUND_CATEGORIES, FUND_REGIONS, FUND_RISK_LEVELS, DEFAULT_CUSTOM_CATEGORIES
    from data.repositories.fund_repository import FundRepository
    from providers.morningstar import (
        FundDataProvider,
        FundNotFoundError,
        FundDataProviderError
    )
    from logger import get_logger

logger = get_logger(__name__)


class FundService(BaseService):
    """
    Servicio para gestion del catalogo de fondos.

    Proporciona:
    - Busqueda avanzada con filtros
    - Conversion a DataFrame para visualizacion
    - Estadisticas del catalogo
    - Importacion/exportacion de datos
    """

    def __init__(self, db_path: str = None):
        """
        Inicializa el servicio.

        Args:
            db_path: Ruta a la BD. Si es None, usa la por defecto.
        """
        super().__init__(db_path)
        self._repository = None
        self._ensure_table_exists()
        logger.info("FundService inicializado")

    def _ensure_table_exists(self):
        """Crea las tablas funds y categories si no existen."""
        try:
            Fund.__table__.create(self.db.engine, checkfirst=True)
            Category.__table__.create(self.db.engine, checkfirst=True)
            # Poblar categorias iniciales si la tabla esta vacia
            self._seed_categories()
        except Exception as e:
            logger.warning(f"No se pudo verificar tablas: {e}")

    def _seed_categories(self):
        """Inserta categorias por defecto si la tabla esta vacia."""
        try:
            count = self.db.session.query(Category).count()
            if count == 0:
                for name in DEFAULT_CUSTOM_CATEGORIES:
                    cat = Category(name=name)
                    self.db.session.add(cat)
                self.db.session.commit()
                logger.info(f"Insertadas {len(DEFAULT_CUSTOM_CATEGORIES)} categorias iniciales")
        except Exception as e:
            self.db.session.rollback()
            logger.warning(f"No se pudieron insertar categorias: {e}")

    @property
    def repository(self) -> FundRepository:
        """Acceso lazy al repositorio."""
        if self._repository is None:
            self._repository = FundRepository(self.db.session)
        return self._repository

    def close(self):
        """Cierra conexiones."""
        super().close()
        logger.debug("FundService cerrado")

    # =========================================================================
    # GESTION DE CATEGORIAS PERSONALIZADAS
    # =========================================================================

    def get_all_categories(self) -> List[str]:
        """
        Obtiene todas las categorias personalizadas de la BD.

        Returns:
            Lista de nombres de categorias ordenados alfabeticamente
        """
        try:
            categories = self.db.session.query(Category).order_by(Category.name).all()
            return [c.name for c in categories]
        except Exception as e:
            logger.warning(f"Error obteniendo categorias: {e}")
            return DEFAULT_CUSTOM_CATEGORIES

    def add_category(self, name: str) -> bool:
        """
        Añade una nueva categoria personalizada.

        Args:
            name: Nombre de la categoria (se normaliza)

        Returns:
            True si se creo, False si ya existia
        """
        name = name.strip()
        if not name:
            return False

        try:
            # Verificar si ya existe
            existing = self.db.session.query(Category).filter_by(name=name).first()
            if existing:
                return False

            cat = Category(name=name)
            self.db.session.add(cat)
            self.db.session.commit()
            logger.info(f"Categoria creada: {name}")
            return True
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error creando categoria: {e}")
            return False

    def delete_category(self, name: str) -> bool:
        """
        Elimina una categoria personalizada.

        Args:
            name: Nombre de la categoria

        Returns:
            True si se elimino, False si no existia
        """
        try:
            cat = self.db.session.query(Category).filter_by(name=name).first()
            if cat:
                self.db.session.delete(cat)
                self.db.session.commit()
                logger.info(f"Categoria eliminada: {name}")
                return True
            return False
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error eliminando categoria: {e}")
            return False

    # =========================================================================
    # BUSQUEDA Y FILTRADO
    # =========================================================================

    def search_funds(
        self,
        # Filtros de texto
        name: str = None,
        isin: str = None,
        manager: str = None,

        # Filtros de categoria
        category: str = None,
        categories: List[str] = None,
        region: str = None,

        # Filtros de costes
        max_ter: float = None,

        # Filtros de riesgo y rating
        risk_level: int = None,
        max_risk_level: int = None,
        min_rating: int = None,

        # Filtros de rendimiento
        min_return_1y: float = None,

        # Ordenamiento
        order_by: str = 'name',
        order_desc: bool = False,

        # Paginacion
        limit: int = None,
        offset: int = 0,

        # Formato de salida
        as_dataframe: bool = False,
    ) -> Any:
        """
        Busca fondos con filtros multiples.

        Args:
            name: Buscar en nombre (parcial)
            isin: Buscar por ISIN
            manager: Filtrar por gestora
            category: Categoria exacta
            categories: Lista de categorias
            region: Region geografica
            max_ter: TER maximo (%)
            risk_level: Nivel de riesgo exacto (1-7)
            max_risk_level: Riesgo maximo
            min_rating: Rating Morningstar minimo (1-5)
            min_return_1y: Rentabilidad 1 ano minima (%)
            order_by: Campo para ordenar
            order_desc: True para orden descendente
            limit: Limite de resultados
            offset: Desplazamiento
            as_dataframe: Si True, devuelve DataFrame

        Returns:
            Lista de Fund o DataFrame
        """
        funds = self.repository.search(
            name=name,
            isin=isin,
            manager=manager,
            category=category,
            categories=categories,
            region=region,
            max_ter=max_ter,
            risk_level=risk_level,
            max_risk_level=max_risk_level,
            min_rating=min_rating,
            min_return_1y=min_return_1y,
            order_by=order_by,
            order_desc=order_desc,
            limit=limit,
            offset=offset,
        )

        if as_dataframe:
            return self._funds_to_dataframe(funds)

        return funds

    def get_fund_by_isin(self, isin: str) -> Optional[Fund]:
        """Obtiene un fondo por ISIN."""
        return self.repository.get_by_isin(isin)

    def get_fund_details(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles completos de un fondo.

        Returns:
            Dict con todos los campos del fondo o None
        """
        fund = self.repository.get_by_isin(isin)
        if fund:
            return fund.to_dict()
        return None

    # =========================================================================
    # METODOS DE CONVENIENCIA
    # =========================================================================

    def find_low_cost_funds(
        self,
        max_ter: float = 0.5,
        category: str = None,
        limit: int = 20
    ) -> List[Fund]:
        """Busca fondos de bajo coste."""
        return self.search_funds(
            category=category,
            max_ter=max_ter,
            order_by='ter',
            limit=limit
        )

    def find_top_rated_funds(
        self,
        min_rating: int = 4,
        category: str = None,
        limit: int = 20
    ) -> List[Fund]:
        """Busca fondos con mejor rating."""
        return self.search_funds(
            category=category,
            min_rating=min_rating,
            order_by='morningstar_rating',
            order_desc=True,
            limit=limit
        )

    def find_best_performers(
        self,
        category: str = None,
        limit: int = 10
    ) -> List[Fund]:
        """Busca fondos con mejor rentabilidad a 1 ano."""
        return self.search_funds(
            category=category,
            order_by='return_1y',
            order_desc=True,
            limit=limit
        )

    def find_conservative_funds(
        self,
        max_risk: int = 3,
        limit: int = 20
    ) -> List[Fund]:
        """Busca fondos conservadores (bajo riesgo)."""
        return self.search_funds(
            max_risk_level=max_risk,
            order_by='risk_level',
            limit=limit
        )

    # =========================================================================
    # ESTADISTICAS Y AGREGACIONES
    # =========================================================================

    def get_catalog_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadisticas del catalogo.

        Returns:
            Dict con:
            - total_funds
            - by_category
            - by_risk_level
            - top_managers
            - avg_ter
        """
        stats = self.repository.get_stats()

        # Calcular TER promedio
        funds = self.repository.get_all()
        if funds:
            ters = [f.ter for f in funds if f.ter is not None]
            stats['avg_ter'] = sum(ters) / len(ters) if ters else 0
        else:
            stats['avg_ter'] = 0

        return stats

    def get_filter_options(self) -> Dict[str, List]:
        """
        Obtiene opciones disponibles para filtros de UI.

        Returns:
            Dict con listas de opciones para cada filtro
        """
        return {
            'categories': self.repository.get_categories() or FUND_CATEGORIES,
            'regions': self.repository.get_regions() or FUND_REGIONS,
            'managers': self.repository.get_managers(),
            'risk_levels': list(FUND_RISK_LEVELS.keys()),
            'risk_level_names': FUND_RISK_LEVELS,
        }

    def count_funds(self, **filters) -> int:
        """Cuenta fondos que cumplen los filtros."""
        funds = self.search_funds(**filters)
        return len(funds)

    # =========================================================================
    # CONVERSION A DATAFRAME
    # =========================================================================

    def _funds_to_dataframe(self, funds: List[Fund]) -> pd.DataFrame:
        """Convierte lista de fondos a DataFrame."""
        if not funds:
            return pd.DataFrame()

        data = [f.to_summary_dict() for f in funds]
        df = pd.DataFrame(data)

        # Ordenar columnas
        column_order = [
            'isin', 'name', 'category', 'manager',
            'ter', 'risk_level', 'morningstar_rating',
            'return_1y', 'return_3y'
        ]
        cols = [c for c in column_order if c in df.columns]
        df = df[cols]

        return df

    def get_funds_dataframe(self, **filters) -> pd.DataFrame:
        """
        Obtiene fondos como DataFrame listo para mostrar.

        Args:
            **filters: Filtros para search_funds()

        Returns:
            DataFrame con columnas formateadas
        """
        return self.search_funds(**filters, as_dataframe=True)

    def format_funds_for_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Formatea DataFrame para visualizacion en UI.

        Args:
            df: DataFrame de fondos

        Returns:
            DataFrame con valores formateados como strings
        """
        if df.empty:
            return df

        formatted = df.copy()

        # Renombrar columnas
        column_names = {
            'isin': 'ISIN',
            'name': 'Nombre',
            'category': 'Categoria',
            'manager': 'Gestora',
            'ter': 'TER %',
            'risk_level': 'Riesgo',
            'morningstar_rating': 'Rating',
            'return_1y': 'Rent. 1A',
            'return_3y': 'Rent. 3A',
        }
        formatted = formatted.rename(columns=column_names)

        # Formatear valores
        if 'TER %' in formatted.columns:
            formatted['TER %'] = formatted['TER %'].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
            )

        if 'Rent. 1A' in formatted.columns:
            formatted['Rent. 1A'] = formatted['Rent. 1A'].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
            )

        if 'Rent. 3A' in formatted.columns:
            formatted['Rent. 3A'] = formatted['Rent. 3A'].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
            )

        if 'Rating' in formatted.columns:
            formatted['Rating'] = formatted['Rating'].apply(
                lambda x: "★" * int(x) if pd.notna(x) else "-"
            )

        if 'Riesgo' in formatted.columns:
            formatted['Riesgo'] = formatted['Riesgo'].apply(
                lambda x: f"{int(x)}/7" if pd.notna(x) else "-"
            )

        return formatted

    # =========================================================================
    # IMPORTACION DESDE MORNINGSTAR
    # =========================================================================

    def fetch_fund_preview(self, isin: str) -> Dict[str, Any]:
        """
        Obtiene datos de un fondo desde Morningstar sin guardarlo.

        Util para mostrar una vista previa antes de guardar en BD.

        Args:
            isin: Codigo ISIN del fondo (ej: 'IE00B3RBWM25')

        Returns:
            Dict con datos del fondo desde Morningstar

        Raises:
            FundNotFoundError: Si el fondo no se encuentra
            FundDataProviderError: Si hay error en la consulta
        """
        provider = FundDataProvider()
        data = provider.get_fund_data(isin)
        logger.info(f"Obtenidos datos de Morningstar para {isin}: {data.get('name')}")
        return data

    def fetch_and_import_fund(self, isin: str) -> Fund:
        """
        Obtiene datos de Morningstar y guarda el fondo en BD.

        Orquesta el flujo completo:
        1. Consulta datos de Morningstar via FundDataProvider
        2. Mapea y guarda en BD via FundRepository

        Args:
            isin: Codigo ISIN del fondo (ej: 'IE00B3RBWM25')

        Returns:
            Fund guardado en BD

        Raises:
            FundNotFoundError: Si el fondo no se encuentra
            FundDataProviderError: Si hay error en la consulta
        """
        # Obtener datos del provider
        provider = FundDataProvider()
        data = provider.get_fund_data(isin)

        # Guardar en BD
        fund = self.repository.upsert_from_provider(data)
        logger.info(f"Fondo importado: {fund.isin} - {fund.name}")

        return fund

    def get_fund_nav_history(self, isin: str, years: int = 3) -> pd.DataFrame:
        """
        Obtiene historico de NAV desde Morningstar.

        Args:
            isin: Codigo ISIN del fondo
            years: Anos de historia (default 3)

        Returns:
            DataFrame con columnas: date, nav, totalReturn
        """
        provider = FundDataProvider()
        return provider.get_nav_history(isin, years=years)

    # =========================================================================
    # IMPORTACION DE DATOS (MANUAL)
    # =========================================================================

    def import_fund(self, fund_data: Dict[str, Any]) -> Fund:
        """
        Importa o actualiza un fondo manualmente.

        Args:
            fund_data: Dict con datos del fondo (debe incluir 'isin')

        Returns:
            Fund insertado o actualizado
        """
        return self.repository.upsert(fund_data)

    def import_funds_bulk(self, funds_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Importa multiples fondos.

        Returns:
            Dict con 'inserted' y 'updated' counts
        """
        return self.repository.bulk_upsert(funds_data)

    def import_from_dataframe(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Importa fondos desde DataFrame.

        Args:
            df: DataFrame con columnas que coinciden con campos de Fund

        Returns:
            Dict con conteos de insertados/actualizados
        """
        funds_data = df.to_dict('records')
        return self.import_funds_bulk(funds_data)

    # =========================================================================
    # EXPORTACION
    # =========================================================================

    def export_to_csv(self, filepath: str, **filters) -> int:
        """
        Exporta fondos a CSV.

        Args:
            filepath: Ruta del archivo
            **filters: Filtros para search_funds()

        Returns:
            Numero de fondos exportados
        """
        df = self.get_funds_dataframe(**filters)
        df.to_csv(filepath, index=False)
        return len(df)

    def has_funds(self) -> bool:
        """Verifica si hay fondos en el catalogo."""
        return self.repository.count() > 0
