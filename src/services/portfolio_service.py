"""
PortfolioService - Servicio de orquestación para datos de cartera

Este servicio actúa como puente entre la UI (Streamlit/FastAPI) y los
módulos de negocio (Portfolio, TaxCalculator, DividendManager).

Responsabilidades:
- Centralizar la obtención de datos de cartera
- Orquestar llamadas a múltiples módulos
- Transformar datos para la presentación (sin conocer la UI)
- Gestionar conexiones a BD de forma eficiente

Uso:
    from src.services.portfolio_service import PortfolioService

    service = PortfolioService()
    data = service.get_dashboard_data(fiscal_year=2024)

    # Datos listos para renderizar
    print(f"Valor total: {data['metrics']['total_value']:,.2f}")

    service.close()
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

try:
    from src.services.base import BaseService, ServiceResult
    from src.portfolio import Portfolio
    from src.tax_calculator import TaxCalculator
    from src.dividends import DividendManager
    from src.market_data import MarketDataManager
    from src.logger import get_logger
except ImportError:
    from services.base import BaseService, ServiceResult
    from portfolio import Portfolio
    from tax_calculator import TaxCalculator
    from dividends import DividendManager
    from market_data import MarketDataManager
    from logger import get_logger

logger = get_logger(__name__)


class PortfolioService(BaseService):
    """
    Servicio de orquestación para datos de cartera.

    Centraliza la lógica de negocio que antes estaba dispersa en las
    páginas de Streamlit. Permite:
    - Una única fuente de verdad para datos de cartera
    - Testing sin dependencias de UI
    - Reutilización en múltiples interfaces (Streamlit, FastAPI, CLI)

    Ejemplo:
        with PortfolioService() as service:
            data = service.get_dashboard_data(fiscal_year=2024)
            positions = service.filter_positions(
                data['positions'],
                asset_type='accion'
            )
    """

    # Mapeo de nombres UI a valores internos
    ASSET_TYPE_MAP = {
        "Todos": None,
        "Acciones": "accion",
        "Fondos": "fondo",
        "ETFs": "etf"
    }

    SORT_OPTIONS = {
        "Valor de mercado": ('market_value', False),
        "Ganancia €": ('unrealized_gain', False),
        "Ganancia %": ('unrealized_gain_pct', False),
        "Nombre": ('name', True)
    }

    def __init__(self, db_path: str = None):
        """
        Inicializa el servicio con todos los módulos necesarios.

        Args:
            db_path: Ruta opcional a la BD. Si es None, usa la por defecto.
        """
        super().__init__(db_path)
        self.portfolio = Portfolio(db_path)
        self.market_data = MarketDataManager(db_path)
        self._tax_calculator = None  # Lazy loading
        self._dividend_manager = None  # Lazy loading
        logger.info("PortfolioService inicializado")

    def close(self):
        """Cierra todas las conexiones de los módulos."""
        if self.portfolio:
            self.portfolio.close()
        if self.market_data:
            self.market_data.close()
        if self._tax_calculator:
            self._tax_calculator.close()
        if self._dividend_manager:
            self._dividend_manager.close()
        super().close()
        logger.debug("PortfolioService cerrado")

    # =========================================================================
    # MÉTODO PRINCIPAL PARA DASHBOARD
    # =========================================================================

    def get_dashboard_data(
        self,
        fiscal_year: int = None,
        fiscal_method: str = 'FIFO'
    ) -> Dict[str, Any]:
        """
        Obtiene todos los datos necesarios para el Dashboard en una sola llamada.

        Este método reemplaza ~75 líneas de lógica que estaban en el Dashboard.
        Centraliza la obtención de:
        - Posiciones actuales con precios de mercado
        - Métricas agregadas (valor total, ganancias, etc.)
        - Resumen fiscal del año
        - Totales de dividendos

        Args:
            fiscal_year: Año fiscal para filtrar datos. Default: año actual.
            fiscal_method: Método fiscal ('FIFO' o 'LIFO').

        Returns:
            Dict con estructura:
            {
                'positions': DataFrame,      # Posiciones con market_value
                'metrics': {
                    'total_value': float,
                    'total_cost': float,
                    'unrealized_gain': float,
                    'unrealized_pct': float,
                    'num_positions': int
                },
                'fiscal_summary': {
                    'realized_gain': float,
                    'year': int
                },
                'dividend_totals': {
                    'count': int,
                    'total_gross': float,
                    'total_net': float,
                    'total_withholding': float
                }
            }
        """
        if fiscal_year is None:
            fiscal_year = datetime.now().year

        logger.debug(f"Obteniendo datos de dashboard para año {fiscal_year}")

        # Obtener precios actuales de mercado
        current_prices = self.db.get_all_latest_prices()

        # Obtener posiciones con precios actuales
        positions = self.portfolio.get_current_positions(current_prices=current_prices)

        # Calcular métricas
        metrics = self._calculate_metrics(positions)

        # Obtener resumen fiscal
        fiscal_summary = self.get_fiscal_summary(fiscal_year, fiscal_method)

        # Obtener totales de dividendos
        dividend_totals = self.get_dividend_summary(fiscal_year)

        return {
            'positions': positions,
            'metrics': metrics,
            'fiscal_summary': fiscal_summary,
            'dividend_totals': dividend_totals
        }

    def _calculate_metrics(self, positions: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas agregadas de las posiciones.

        Args:
            positions: DataFrame con posiciones

        Returns:
            Dict con métricas calculadas
        """
        if positions.empty:
            return {
                'total_value': 0.0,
                'total_cost': 0.0,
                'unrealized_gain': 0.0,
                'unrealized_pct': 0.0,
                'num_positions': 0
            }

        total_value = positions['market_value'].sum()
        total_cost = positions['cost_basis'].sum()
        unrealized_gain = positions['unrealized_gain'].sum()
        unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0

        return {
            'total_value': float(total_value),
            'total_cost': float(total_cost),
            'unrealized_gain': float(unrealized_gain),
            'unrealized_pct': float(unrealized_pct),
            'num_positions': len(positions)
        }

    # =========================================================================
    # FILTRADO Y ORDENAMIENTO
    # =========================================================================

    def filter_positions(
        self,
        positions: pd.DataFrame,
        asset_type: str = None
    ) -> pd.DataFrame:
        """
        Filtra posiciones por tipo de activo.

        Args:
            positions: DataFrame de posiciones
            asset_type: Tipo de activo ("Acciones", "Fondos", "ETFs", "Todos")
                       También acepta valores internos ("accion", "fondo", "etf")

        Returns:
            DataFrame filtrado
        """
        if positions.empty or asset_type is None or asset_type == "Todos":
            return positions

        # Mapear nombre UI a valor interno si es necesario
        internal_type = self.ASSET_TYPE_MAP.get(asset_type, asset_type)

        if internal_type is None:
            return positions

        if 'asset_type' not in positions.columns:
            logger.warning("Columna 'asset_type' no encontrada en posiciones")
            return positions

        return positions[positions['asset_type'] == internal_type].copy()

    def sort_positions(
        self,
        positions: pd.DataFrame,
        sort_by: str = "Valor de mercado"
    ) -> pd.DataFrame:
        """
        Ordena posiciones según criterio especificado.

        Args:
            positions: DataFrame de posiciones
            sort_by: Criterio de ordenamiento:
                    - "Valor de mercado" (default, descendente)
                    - "Ganancia €" (descendente)
                    - "Ganancia %" (descendente)
                    - "Nombre" (ascendente)

        Returns:
            DataFrame ordenado
        """
        if positions.empty:
            return positions

        sort_col, ascending = self.SORT_OPTIONS.get(sort_by, ('market_value', False))

        if sort_col not in positions.columns:
            logger.warning(f"Columna '{sort_col}' no encontrada, usando 'market_value'")
            sort_col = 'market_value'
            ascending = False

        return positions.sort_values(sort_col, ascending=ascending).copy()

    def enrich_with_weights(self, positions: pd.DataFrame) -> pd.DataFrame:
        """
        Añade columna 'weight' con el peso de cada posición en la cartera.

        Args:
            positions: DataFrame de posiciones

        Returns:
            DataFrame con columna 'weight' añadida (en porcentaje)
        """
        if positions.empty:
            return positions

        df = positions.copy()
        total_value = df['market_value'].sum()

        if total_value > 0:
            df['weight'] = (df['market_value'] / total_value * 100)
        else:
            df['weight'] = 0.0

        return df

    # =========================================================================
    # RESÚMENES Y AGREGACIONES
    # =========================================================================

    def get_summary_by_type(self, positions: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula resumen agrupado por tipo de activo.

        Args:
            positions: DataFrame de posiciones

        Returns:
            DataFrame con columnas: Tipo, Valor, Coste, Ganancia, Posiciones,
                                   Ganancia %, Peso %
        """
        if positions.empty or 'asset_type' not in positions.columns:
            return pd.DataFrame()

        total_value = positions['market_value'].sum()

        summary = positions.groupby('asset_type').agg({
            'market_value': 'sum',
            'cost_basis': 'sum',
            'unrealized_gain': 'sum',
            'ticker': 'count'
        }).reset_index()

        summary.columns = ['Tipo', 'Valor', 'Coste', 'Ganancia', 'Posiciones']

        # Calcular porcentajes
        summary['Ganancia %'] = summary.apply(
            lambda row: (row['Ganancia'] / row['Coste'] * 100) if row['Coste'] > 0 else 0,
            axis=1
        )
        summary['Peso %'] = summary.apply(
            lambda row: (row['Valor'] / total_value * 100) if total_value > 0 else 0,
            axis=1
        )

        # Mapear nombres internos a display
        type_names = {'accion': 'Acciones', 'fondo': 'Fondos', 'etf': 'ETFs'}
        summary['Tipo'] = summary['Tipo'].map(lambda x: type_names.get(x, x))

        return summary

    def format_summary_by_type(self, summary: pd.DataFrame) -> pd.DataFrame:
        """
        Formatea el resumen por tipo para visualización.

        Args:
            summary: DataFrame del método get_summary_by_type()

        Returns:
            DataFrame con valores formateados como strings
        """
        if summary.empty:
            return summary

        formatted = summary.copy()

        for col in ['Valor', 'Coste', 'Ganancia']:
            if col in formatted.columns:
                formatted[col] = formatted[col].apply(lambda x: f"{x:,.2f}EUR")

        if 'Ganancia %' in formatted.columns:
            formatted['Ganancia %'] = formatted['Ganancia %'].apply(lambda x: f"{x:+.2f}%")

        if 'Peso %' in formatted.columns:
            formatted['Peso %'] = formatted['Peso %'].apply(lambda x: f"{x:.1f}%")

        return formatted

    # =========================================================================
    # INTEGRACIÓN CON OTROS MÓDULOS
    # =========================================================================

    def get_fiscal_summary(self, fiscal_year: int, method: str = 'FIFO') -> Dict[str, Any]:
        """
        Obtiene resumen fiscal del año especificado.

        Args:
            fiscal_year: Año fiscal
            method: Método de cálculo ('FIFO' o 'LIFO')

        Returns:
            Dict con información fiscal
        """
        try:
            # Lazy loading del TaxCalculator
            if self._tax_calculator is None:
                self._tax_calculator = TaxCalculator(method=method)

            summary = self._tax_calculator.get_fiscal_year_summary(fiscal_year)

            return {
                'realized_gain': summary.get('net_gain', 0.0),
                'year': fiscal_year,
                'method': method,
                'details': summary
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen fiscal: {e}")
            return {
                'realized_gain': 0.0,
                'year': fiscal_year,
                'method': method,
                'details': {}
            }

    def get_dividend_summary(self, year: int = None) -> Dict[str, Any]:
        """
        Obtiene totales de dividendos para el año especificado.

        Args:
            year: Año a consultar. Default: año actual.

        Returns:
            Dict con totales de dividendos
        """
        if year is None:
            year = datetime.now().year

        try:
            # Lazy loading del DividendManager
            if self._dividend_manager is None:
                self._dividend_manager = DividendManager()

            totals = self._dividend_manager.get_total_dividends(year=year)

            return {
                'count': totals.get('count', 0),
                'total_gross': totals.get('total_gross', 0.0),
                'total_net': totals.get('total_net', 0.0),
                'total_withholding': totals.get('total_withholding', 0.0),
                'year': year
            }
        except Exception as e:
            logger.error(f"Error obteniendo dividendos: {e}")
            return {
                'count': 0,
                'total_gross': 0.0,
                'total_net': 0.0,
                'total_withholding': 0.0,
                'year': year
            }

    # =========================================================================
    # MÉTODOS DE CONVENIENCIA
    # =========================================================================

    def get_positions_for_display(
        self,
        asset_type: str = None,
        sort_by: str = "Valor de mercado",
        include_weights: bool = True
    ) -> pd.DataFrame:
        """
        Obtiene posiciones listas para mostrar en UI.

        Combina: obtención de posiciones + filtrado + ordenamiento + pesos.

        Args:
            asset_type: Filtro por tipo de activo
            sort_by: Criterio de ordenamiento
            include_weights: Si añadir columna de peso

        Returns:
            DataFrame procesado listo para visualización
        """
        current_prices = self.db.get_all_latest_prices()
        positions = self.portfolio.get_current_positions(current_prices=current_prices)

        # Aplicar filtrado
        positions = self.filter_positions(positions, asset_type)

        # Aplicar ordenamiento
        positions = self.sort_positions(positions, sort_by)

        # Añadir pesos si se solicita
        if include_weights:
            positions = self.enrich_with_weights(positions)

        return positions

    def get_allocation_data(self) -> pd.DataFrame:
        """
        Obtiene datos de asignación para gráfico de donut.

        Returns:
            DataFrame con columnas: ticker, name, market_value
            Solo incluye posiciones con valor > 0
        """
        current_prices = self.db.get_all_latest_prices()
        positions = self.portfolio.get_current_positions(current_prices=current_prices)

        if positions.empty:
            return pd.DataFrame()

        allocation = positions[['ticker', 'name', 'market_value']].copy()
        allocation = allocation[allocation['market_value'] > 0]

        return allocation

    def has_positions(self) -> bool:
        """Verifica si hay posiciones en la cartera."""
        positions = self.portfolio.get_current_positions()
        return not positions.empty
