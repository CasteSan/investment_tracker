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
    from src.benchmarks import BenchmarkComparator
    from src.logger import get_logger
    from src.core.analytics import (
        calculate_volatility,
        calculate_var,
        calculate_beta,
        calculate_max_drawdown,
        calculate_sharpe_ratio,
        calculate_sortino_ratio,
        calculate_alpha,
        calculate_cagr_from_prices,
        calculate_total_return,
    )
    from src.core.utils import smart_truncate
except ImportError:
    from services.base import BaseService, ServiceResult
    from portfolio import Portfolio
    from tax_calculator import TaxCalculator
    from dividends import DividendManager
    from market_data import MarketDataManager
    from benchmarks import BenchmarkComparator
    from logger import get_logger
    from core.analytics import (
        calculate_volatility,
        calculate_var,
        calculate_beta,
        calculate_max_drawdown,
        calculate_sharpe_ratio,
        calculate_sortino_ratio,
        calculate_alpha,
        calculate_cagr_from_prices,
        calculate_total_return,
    )
    from core.utils import smart_truncate

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
        self._benchmark_comparator = None  # Lazy loading
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
        if self._benchmark_comparator:
            self._benchmark_comparator.close()
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

    def enrich_with_display_names(
        self,
        positions: pd.DataFrame,
        max_length: int = 15
    ) -> pd.DataFrame:
        """
        Añade columna 'display_name' con nombres truncados para gráficos.

        Args:
            positions: DataFrame de posiciones con columna 'name'
            max_length: Longitud máxima del nombre truncado

        Returns:
            DataFrame con columna 'display_name' añadida
        """
        if positions.empty or 'name' not in positions.columns:
            return positions

        df = positions.copy()
        df['display_name'] = df['name'].apply(
            lambda x: smart_truncate(x, max_length) if x else ''
        )

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
    # MÉTRICAS AVANZADAS DE ANALYTICS
    # =========================================================================

    def get_portfolio_metrics(
        self,
        start_date: str = None,
        end_date: str = None,
        benchmark_name: str = 'SP500',
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        Calcula métricas avanzadas de riesgo y rendimiento del portfolio.

        Usa los precios históricos de mercado para calcular retornos reales,
        y compara contra un benchmark para métricas como Beta y Alpha.

        Args:
            start_date: Fecha inicio (YYYY-MM-DD). Default: 1 año atrás.
            end_date: Fecha fin (YYYY-MM-DD). Default: hoy.
            benchmark_name: Nombre del benchmark ('SP500', 'IBEX35', 'MSCIWORLD').
            risk_free_rate: Tasa libre de riesgo anual (default 2%).

        Returns:
            Dict con estructura:
            {
                'risk': {
                    'volatility': float,      # Volatilidad anualizada
                    'var_95': float,          # VaR al 95%
                    'max_drawdown': float,    # Máxima caída
                    'beta': float,            # Beta vs benchmark
                },
                'performance': {
                    'total_return': float,    # Retorno total acumulado
                    'cagr': float,            # Tasa crecimiento anual compuesto
                    'sharpe_ratio': float,    # Ratio de Sharpe
                    'sortino_ratio': float,   # Ratio de Sortino
                    'alpha': float,           # Alpha de Jensen
                },
                'meta': {
                    'start_date': str,
                    'end_date': str,
                    'benchmark': str,
                    'trading_days': int,
                    'has_benchmark_data': bool,
                }
            }
        """
        from datetime import timedelta

        # Establecer fechas por defecto
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        logger.debug(f"Calculando métricas: {start_date} a {end_date}, benchmark={benchmark_name}")

        # Inicializar resultado con valores por defecto
        result = {
            'risk': {
                'volatility': 0.0,
                'var_95': 0.0,
                'max_drawdown': 0.0,
                'beta': 1.0,  # Neutral por defecto
            },
            'performance': {
                'total_return': 0.0,
                'cagr': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'alpha': 0.0,
            },
            'meta': {
                'start_date': start_date,
                'end_date': end_date,
                'benchmark': benchmark_name,
                'trading_days': 0,
                'has_benchmark_data': False,
            }
        }

        try:
            # 1. Obtener serie de valores del portfolio
            portfolio_series = self.market_data.get_portfolio_market_value_series(
                start_date, end_date
            )

            if portfolio_series.empty or 'market_value' not in portfolio_series.columns:
                logger.warning("No hay datos de valor de mercado del portfolio")
                return result

            # Convertir a Series con índice de fechas
            portfolio_values = portfolio_series.set_index('date')['market_value']
            portfolio_values = portfolio_values.dropna()

            if len(portfolio_values) < 2:
                logger.warning("Datos insuficientes para calcular retornos")
                return result

            # 2. Calcular retornos diarios del portfolio
            portfolio_returns = portfolio_values.pct_change().dropna()

            # Filtrar retornos extremos (errores de datos)
            portfolio_returns = portfolio_returns[
                (portfolio_returns > -0.5) & (portfolio_returns < 0.5)
            ]

            if len(portfolio_returns) < 10:
                logger.warning("Menos de 10 retornos válidos")
                return result

            result['meta']['trading_days'] = len(portfolio_returns)

            # 3. Calcular métricas de riesgo (no requieren benchmark)
            result['risk']['volatility'] = float(calculate_volatility(
                portfolio_returns, annualize=True, periods_per_year=252
            ))

            result['risk']['var_95'] = float(calculate_var(
                portfolio_returns, confidence_level=0.95, method='historical'
            ))

            result['risk']['max_drawdown'] = float(calculate_max_drawdown(
                portfolio_values
            ))

            # 4. Calcular métricas de rendimiento básicas
            result['performance']['total_return'] = float(calculate_total_return(
                portfolio_values
            ))

            result['performance']['cagr'] = float(calculate_cagr_from_prices(
                portfolio_values
            ))

            result['performance']['sharpe_ratio'] = float(calculate_sharpe_ratio(
                portfolio_returns, risk_free_rate=risk_free_rate
            ))

            result['performance']['sortino_ratio'] = float(calculate_sortino_ratio(
                portfolio_returns, risk_free_rate=risk_free_rate
            ))

            # 5. Obtener benchmark para Beta y Alpha
            if self._benchmark_comparator is None:
                self._benchmark_comparator = BenchmarkComparator()

            benchmark_series = self._benchmark_comparator.get_benchmark_series(
                benchmark_name, start_date, end_date
            )

            if not benchmark_series.empty and len(benchmark_series) > 10:
                result['meta']['has_benchmark_data'] = True

                # Alinear fechas entre portfolio y benchmark
                common_dates = portfolio_values.index.intersection(benchmark_series.index)

                if len(common_dates) > 10:
                    aligned_portfolio = portfolio_values.loc[common_dates]
                    aligned_benchmark = benchmark_series.loc[common_dates]

                    portfolio_ret = aligned_portfolio.pct_change().dropna()
                    benchmark_ret = aligned_benchmark.pct_change().dropna()

                    # Alinear retornos
                    common_ret_dates = portfolio_ret.index.intersection(benchmark_ret.index)
                    portfolio_ret = portfolio_ret.loc[common_ret_dates]
                    benchmark_ret = benchmark_ret.loc[common_ret_dates]

                    if len(portfolio_ret) > 10:
                        result['risk']['beta'] = float(calculate_beta(
                            portfolio_ret, benchmark_ret
                        ))

                        result['performance']['alpha'] = float(calculate_alpha(
                            portfolio_ret, benchmark_ret, risk_free_rate=risk_free_rate
                        ))
            else:
                logger.info(f"Sin datos de benchmark {benchmark_name}, usando Beta=1.0, Alpha=0.0")

        except Exception as e:
            logger.error(f"Error calculando métricas de portfolio: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        return result

    def get_available_benchmarks(self) -> List[Dict]:
        """
        Lista los benchmarks disponibles para comparación.

        Returns:
            Lista de dicts con nombre, fecha_inicio, fecha_fin, registros
        """
        if self._benchmark_comparator is None:
            self._benchmark_comparator = BenchmarkComparator()

        return self._benchmark_comparator.get_available_benchmarks()

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

    def get_allocation_data(self, name_max_length: int = 15) -> pd.DataFrame:
        """
        Obtiene datos de asignación para gráfico de donut.

        Args:
            name_max_length: Longitud máxima para display_name (default 15)

        Returns:
            DataFrame con columnas: ticker, name, display_name, market_value
            Solo incluye posiciones con valor > 0
        """
        current_prices = self.db.get_all_latest_prices()
        positions = self.portfolio.get_current_positions(current_prices=current_prices)

        if positions.empty:
            return pd.DataFrame()

        allocation = positions[['ticker', 'name', 'market_value']].copy()
        allocation = allocation[allocation['market_value'] > 0]

        # Añadir nombre truncado para labels de gráficos
        allocation['display_name'] = allocation['name'].apply(
            lambda x: smart_truncate(x, name_max_length)
        )

        return allocation

    def get_heatmap_data(
        self,
        category_filter: str = 'all',
        name_max_length: int = 15
    ) -> pd.DataFrame:
        """
        Obtiene datos para el mapa de calor (treemap) del dashboard.

        Calcula la variación intradía de cada activo para determinar el color,
        y usa el peso en cartera para el tamaño de cada celda.

        La variación intradía se calcula como:
        daily_change_pct = (current_price - previous_close) / previous_close * 100

        Args:
            category_filter: Filtro de categoría:
                - 'all': Todos los activos
                - 'fondos_etf': Solo fondos y ETFs
                - 'acciones': Solo acciones
            name_max_length: Longitud máxima para display_name

        Returns:
            DataFrame con columnas:
                - ticker, name, display_name
                - market_value, weight, current_price
                - daily_change_pct (% variación intradía)
                - total_return (% ganancia total acumulada)
                - asset_type
        """
        from datetime import timedelta

        # Obtener posiciones actuales con precios de mercado
        current_prices = self.db.get_all_latest_prices()
        positions = self.portfolio.get_current_positions(current_prices=current_prices)

        if positions.empty:
            return pd.DataFrame()

        # Filtrar posiciones con valor > 0
        positions = positions[positions['market_value'] > 0].copy()

        if positions.empty:
            return pd.DataFrame()

        # Aplicar filtro de categoría
        if category_filter == 'fondos_etf':
            positions = positions[positions['asset_type'].isin(['fondo', 'etf'])]
        elif category_filter == 'acciones':
            positions = positions[positions['asset_type'] == 'accion']

        if positions.empty:
            return pd.DataFrame()

        # Calcular peso en cartera
        total_value = positions['market_value'].sum()
        positions['weight'] = (positions['market_value'] / total_value * 100)

        # Calcular variación intradía para cada ticker
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        # Si ayer fue fin de semana, buscar el viernes
        while yesterday.weekday() >= 5:  # 5=Sábado, 6=Domingo
            yesterday -= timedelta(days=1)

        daily_changes = []
        current_prices_list = []

        for _, row in positions.iterrows():
            ticker = row['ticker']
            daily_change = None
            current_price = None

            try:
                # Obtener el precio actual de mercado
                if ticker in current_prices:
                    current_price = current_prices[ticker]
                else:
                    # Calcular desde market_value y quantity
                    if row['quantity'] > 0:
                        current_price = row['market_value'] / row['quantity']

                # Obtener el cierre del día anterior
                prices = self.market_data.get_ticker_prices(
                    ticker,
                    start_date=(yesterday - timedelta(days=7)).strftime('%Y-%m-%d'),
                    end_date=yesterday.strftime('%Y-%m-%d')
                )

                if not prices.empty and current_price is not None:
                    # Ordenar por fecha y tomar el último (cierre de ayer)
                    prices = prices.sort_values('date')
                    previous_close = prices.iloc[-1]['adj_close']

                    if previous_close > 0:
                        # Variación intradía: (precio actual - cierre ayer) / cierre ayer
                        daily_change = ((current_price - previous_close) / previous_close) * 100

            except Exception as e:
                logger.debug(f"No se pudo calcular variación intradía para {ticker}: {e}")

            daily_changes.append(daily_change)
            current_prices_list.append(current_price)

        positions['daily_change_pct'] = daily_changes
        positions['current_price'] = current_prices_list

        # Guardar rentabilidad total acumulada (para referencia)
        positions['total_return'] = positions['unrealized_gain_pct']

        # Para el color, usar ESTRICTAMENTE variación intradía
        # Si no hay datos, usar 0 (color neutro)
        positions['daily_change_pct'] = positions['daily_change_pct'].fillna(0.0)

        # Añadir display_name
        positions['display_name'] = positions['name'].apply(
            lambda x: smart_truncate(x, name_max_length) if x else ''
        )

        # Seleccionar y ordenar columnas
        result = positions[[
            'ticker', 'name', 'display_name', 'market_value', 'weight',
            'current_price', 'daily_change_pct', 'total_return', 'asset_type'
        ]].copy()

        return result.sort_values('weight', ascending=False)

    def has_positions(self) -> bool:
        """Verifica si hay posiciones en la cartera."""
        positions = self.portfolio.get_current_positions()
        return not positions.empty
