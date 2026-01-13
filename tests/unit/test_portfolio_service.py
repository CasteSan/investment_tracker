"""
Tests Unitarios para PortfolioService

Estos tests verifican la logica del servicio sin depender
de la base de datos real. Usan fixtures con BD temporal.

Ejecutar:
    pytest tests/unit/test_portfolio_service.py -v

Ejecutar con output:
    pytest tests/unit/test_portfolio_service.py -v -s
"""

import pytest
import pandas as pd
from datetime import datetime


class TestPortfolioServiceInit:
    """Tests de inicializacion del servicio."""

    def test_create_service(self, portfolio_service):
        """Verifica que el servicio se crea correctamente."""
        assert portfolio_service is not None
        assert portfolio_service.portfolio is not None
        assert portfolio_service.db is not None

    def test_service_has_logger(self, portfolio_service):
        """Verifica que el servicio tiene logger configurado."""
        assert portfolio_service.logger is not None

    def test_context_manager(self, temp_db_path):
        """Verifica que funciona como context manager."""
        from src.services.portfolio_service import PortfolioService

        with PortfolioService(db_path=temp_db_path) as service:
            assert service is not None
        # No deberia dar error al cerrar


class TestFilterPositions:
    """Tests para el metodo filter_positions()."""

    def test_filter_empty_dataframe(self, portfolio_service, empty_positions_df):
        """Filtrar DataFrame vacio devuelve DataFrame vacio."""
        result = portfolio_service.filter_positions(empty_positions_df, 'Acciones')
        assert result.empty

    def test_filter_none_type(self, portfolio_service, sample_positions_df):
        """Filtrar con None devuelve todas las posiciones."""
        result = portfolio_service.filter_positions(sample_positions_df, None)
        assert len(result) == len(sample_positions_df)

    def test_filter_todos(self, portfolio_service, sample_positions_df):
        """Filtrar con 'Todos' devuelve todas las posiciones."""
        result = portfolio_service.filter_positions(sample_positions_df, 'Todos')
        assert len(result) == len(sample_positions_df)

    def test_filter_acciones(self, portfolio_service, sample_positions_df):
        """Filtrar por 'Acciones' devuelve solo acciones."""
        result = portfolio_service.filter_positions(sample_positions_df, 'Acciones')
        assert len(result) == 2
        assert all(result['asset_type'] == 'accion')

    def test_filter_fondos(self, portfolio_service, sample_positions_df):
        """Filtrar por 'Fondos' devuelve solo fondos."""
        result = portfolio_service.filter_positions(sample_positions_df, 'Fondos')
        assert len(result) == 1
        assert all(result['asset_type'] == 'fondo')

    def test_filter_internal_type(self, portfolio_service, sample_positions_df):
        """Filtrar con tipo interno (accion) funciona."""
        result = portfolio_service.filter_positions(sample_positions_df, 'accion')
        assert len(result) == 2

    def test_filter_preserves_data(self, portfolio_service, sample_positions_df):
        """Filtrar no modifica el DataFrame original."""
        original_len = len(sample_positions_df)
        _ = portfolio_service.filter_positions(sample_positions_df, 'Acciones')
        assert len(sample_positions_df) == original_len


class TestSortPositions:
    """Tests para el metodo sort_positions()."""

    def test_sort_empty_dataframe(self, portfolio_service, empty_positions_df):
        """Ordenar DataFrame vacio devuelve DataFrame vacio."""
        result = portfolio_service.sort_positions(empty_positions_df, 'Valor de mercado')
        assert result.empty

    def test_sort_by_market_value(self, portfolio_service, sample_positions_df):
        """Ordenar por valor de mercado (descendente)."""
        result = portfolio_service.sort_positions(sample_positions_df, 'Valor de mercado')
        values = result['market_value'].tolist()
        assert values == sorted(values, reverse=True)

    def test_sort_by_gain_eur(self, portfolio_service, sample_positions_df):
        """Ordenar por ganancia EUR (descendente)."""
        result = portfolio_service.sort_positions(sample_positions_df, 'Ganancia €')
        values = result['unrealized_gain'].tolist()
        assert values == sorted(values, reverse=True)

    def test_sort_by_gain_pct(self, portfolio_service, sample_positions_df):
        """Ordenar por ganancia porcentaje (descendente)."""
        result = portfolio_service.sort_positions(sample_positions_df, 'Ganancia %')
        values = result['unrealized_gain_pct'].tolist()
        assert values == sorted(values, reverse=True)

    def test_sort_by_name(self, portfolio_service, sample_positions_df):
        """Ordenar por nombre (ascendente)."""
        result = portfolio_service.sort_positions(sample_positions_df, 'Nombre')
        names = result['name'].tolist()
        assert names == sorted(names)

    def test_sort_default(self, portfolio_service, sample_positions_df):
        """Ordenamiento por defecto es valor de mercado."""
        result = portfolio_service.sort_positions(sample_positions_df, 'opcion_invalida')
        values = result['market_value'].tolist()
        assert values == sorted(values, reverse=True)


class TestEnrichWithWeights:
    """Tests para el metodo enrich_with_weights()."""

    def test_enrich_empty_dataframe(self, portfolio_service, empty_positions_df):
        """Enriquecer DataFrame vacio devuelve DataFrame vacio."""
        result = portfolio_service.enrich_with_weights(empty_positions_df)
        assert result.empty

    def test_adds_weight_column(self, portfolio_service, sample_positions_df):
        """Verifica que se añade columna 'weight'."""
        result = portfolio_service.enrich_with_weights(sample_positions_df)
        assert 'weight' in result.columns

    def test_weights_sum_to_100(self, portfolio_service, sample_positions_df):
        """Los pesos suman 100%."""
        result = portfolio_service.enrich_with_weights(sample_positions_df)
        assert abs(result['weight'].sum() - 100.0) < 0.01

    def test_weights_are_positive(self, portfolio_service, sample_positions_df):
        """Todos los pesos son positivos."""
        result = portfolio_service.enrich_with_weights(sample_positions_df)
        assert all(result['weight'] >= 0)


class TestGetSummaryByType:
    """Tests para el metodo get_summary_by_type()."""

    def test_summary_empty_dataframe(self, portfolio_service, empty_positions_df):
        """Resumen de DataFrame vacio devuelve DataFrame vacio."""
        result = portfolio_service.get_summary_by_type(empty_positions_df)
        assert result.empty

    def test_summary_has_expected_columns(self, portfolio_service, sample_positions_df):
        """Verifica que el resumen tiene las columnas esperadas."""
        result = portfolio_service.get_summary_by_type(sample_positions_df)
        expected_cols = ['Tipo', 'Valor', 'Coste', 'Ganancia', 'Posiciones', 'Ganancia %', 'Peso %']
        assert all(col in result.columns for col in expected_cols)

    def test_summary_groups_correctly(self, portfolio_service, sample_positions_df):
        """Verifica agrupacion correcta por tipo."""
        result = portfolio_service.get_summary_by_type(sample_positions_df)
        # sample_positions_df tiene 2 acciones y 1 fondo
        assert len(result) == 2

    def test_summary_type_names_mapped(self, portfolio_service, sample_positions_df):
        """Verifica que los tipos internos se mapean a nombres display."""
        result = portfolio_service.get_summary_by_type(sample_positions_df)
        types = result['Tipo'].tolist()
        assert 'Acciones' in types
        assert 'Fondos' in types
        assert 'accion' not in types


class TestCalculateMetrics:
    """Tests para el metodo _calculate_metrics()."""

    def test_metrics_empty_dataframe(self, portfolio_service, empty_positions_df):
        """Metricas de DataFrame vacio devuelve zeros."""
        result = portfolio_service._calculate_metrics(empty_positions_df)
        assert result['total_value'] == 0.0
        assert result['total_cost'] == 0.0
        assert result['unrealized_gain'] == 0.0
        assert result['num_positions'] == 0

    def test_metrics_correct_values(self, portfolio_service, sample_positions_df):
        """Verifica calculo correcto de metricas."""
        result = portfolio_service._calculate_metrics(sample_positions_df)

        expected_value = sample_positions_df['market_value'].sum()
        expected_cost = sample_positions_df['cost_basis'].sum()
        expected_gain = sample_positions_df['unrealized_gain'].sum()

        assert result['total_value'] == expected_value
        assert result['total_cost'] == expected_cost
        assert result['unrealized_gain'] == expected_gain
        assert result['num_positions'] == len(sample_positions_df)

    def test_metrics_pct_calculation(self, portfolio_service, sample_positions_df):
        """Verifica calculo correcto del porcentaje."""
        result = portfolio_service._calculate_metrics(sample_positions_df)

        expected_cost = sample_positions_df['cost_basis'].sum()
        expected_gain = sample_positions_df['unrealized_gain'].sum()
        expected_pct = (expected_gain / expected_cost * 100)

        assert abs(result['unrealized_pct'] - expected_pct) < 0.01


class TestWithData:
    """Tests que requieren datos en la BD."""

    def test_has_positions_empty(self, portfolio_service):
        """BD vacia devuelve False para has_positions()."""
        assert portfolio_service.has_positions() is False

    def test_has_positions_with_data(self, portfolio_service_with_data):
        """BD con datos devuelve True para has_positions()."""
        assert portfolio_service_with_data.has_positions() is True

    def test_get_dashboard_data_empty(self, portfolio_service):
        """get_dashboard_data con BD vacia devuelve estructura correcta."""
        data = portfolio_service.get_dashboard_data()

        assert 'positions' in data
        assert 'metrics' in data
        assert 'fiscal_summary' in data
        assert 'dividend_totals' in data

    def test_get_dashboard_data_with_data(self, portfolio_service_with_data, fiscal_year):
        """get_dashboard_data devuelve datos correctos."""
        data = portfolio_service_with_data.get_dashboard_data(fiscal_year=fiscal_year)

        assert not data['positions'].empty
        assert data['metrics']['num_positions'] > 0
        assert data['metrics']['total_value'] > 0

    def test_get_allocation_data(self, portfolio_service_with_data):
        """get_allocation_data devuelve datos para donut."""
        allocation = portfolio_service_with_data.get_allocation_data()

        assert 'ticker' in allocation.columns
        assert 'name' in allocation.columns
        assert 'market_value' in allocation.columns
        assert all(allocation['market_value'] > 0)


class TestAssetTypeMap:
    """Tests para constantes de mapeo."""

    def test_asset_type_map_completeness(self, portfolio_service):
        """Verifica que el mapa de tipos tiene todas las opciones."""
        map_keys = portfolio_service.ASSET_TYPE_MAP.keys()
        assert 'Todos' in map_keys
        assert 'Acciones' in map_keys
        assert 'Fondos' in map_keys
        assert 'ETFs' in map_keys

    def test_sort_options_completeness(self, portfolio_service):
        """Verifica que las opciones de ordenamiento estan completas."""
        sort_keys = portfolio_service.SORT_OPTIONS.keys()
        assert 'Valor de mercado' in sort_keys
        assert 'Ganancia €' in sort_keys
        assert 'Ganancia %' in sort_keys
        assert 'Nombre' in sort_keys


class TestGetPortfolioMetrics:
    """Tests para get_portfolio_metrics() - métricas avanzadas."""

    def test_returns_correct_structure(self, portfolio_service):
        """Verifica que devuelve la estructura correcta."""
        metrics = portfolio_service.get_portfolio_metrics()

        # Verificar estructura principal
        assert 'risk' in metrics
        assert 'performance' in metrics
        assert 'meta' in metrics

        # Verificar claves de riesgo
        assert 'volatility' in metrics['risk']
        assert 'var_95' in metrics['risk']
        assert 'max_drawdown' in metrics['risk']
        assert 'beta' in metrics['risk']

        # Verificar claves de rendimiento
        assert 'total_return' in metrics['performance']
        assert 'cagr' in metrics['performance']
        assert 'sharpe_ratio' in metrics['performance']
        assert 'sortino_ratio' in metrics['performance']
        assert 'alpha' in metrics['performance']

        # Verificar metadatos
        assert 'start_date' in metrics['meta']
        assert 'end_date' in metrics['meta']
        assert 'benchmark' in metrics['meta']
        assert 'trading_days' in metrics['meta']
        assert 'has_benchmark_data' in metrics['meta']

    def test_returns_floats(self, portfolio_service):
        """Verifica que todas las métricas son floats."""
        metrics = portfolio_service.get_portfolio_metrics()

        for key, value in metrics['risk'].items():
            assert isinstance(value, (int, float)), f"risk.{key} no es float"

        for key, value in metrics['performance'].items():
            assert isinstance(value, (int, float)), f"performance.{key} no es float"

    def test_accepts_custom_parameters(self, portfolio_service):
        """Verifica que acepta parámetros personalizados."""
        metrics = portfolio_service.get_portfolio_metrics(
            start_date='2024-01-01',
            end_date='2024-12-31',
            benchmark_name='IBEX35',
            risk_free_rate=0.03
        )

        assert metrics['meta']['benchmark'] == 'IBEX35'

    def test_default_benchmark_is_sp500(self, portfolio_service):
        """Verifica que el benchmark por defecto es SP500."""
        metrics = portfolio_service.get_portfolio_metrics()
        assert metrics['meta']['benchmark'] == 'SP500'

    def test_empty_portfolio_returns_defaults(self, portfolio_service):
        """Sin datos, devuelve valores por defecto."""
        metrics = portfolio_service.get_portfolio_metrics()

        # Con portfolio vacío, métricas son 0 o valores por defecto
        assert metrics['risk']['beta'] == 1.0  # Default neutral
        assert metrics['meta']['trading_days'] >= 0


class TestGetAvailableBenchmarks:
    """Tests para get_available_benchmarks()."""

    def test_returns_list(self, portfolio_service):
        """Verifica que devuelve una lista."""
        benchmarks = portfolio_service.get_available_benchmarks()
        assert isinstance(benchmarks, list)

    def test_each_benchmark_has_required_fields(self, portfolio_service):
        """Cada benchmark tiene los campos esperados si hay datos."""
        benchmarks = portfolio_service.get_available_benchmarks()

        for benchmark in benchmarks:
            assert 'name' in benchmark
            assert 'records' in benchmark


class TestGetHeatmapData:
    """Tests para get_heatmap_data()."""

    def test_returns_dataframe(self, portfolio_service):
        """Verifica que devuelve un DataFrame."""
        result = portfolio_service.get_heatmap_data()
        assert isinstance(result, pd.DataFrame)

    def test_empty_portfolio_returns_empty_df(self, portfolio_service):
        """Sin posiciones, devuelve DataFrame vacío."""
        result = portfolio_service.get_heatmap_data()
        assert result.empty

    def test_has_required_columns(self, portfolio_service_with_data):
        """Verifica que tiene todas las columnas esperadas."""
        result = portfolio_service_with_data.get_heatmap_data()

        if not result.empty:
            required_cols = [
                'ticker', 'name', 'display_name', 'market_value', 'weight',
                'current_price', 'daily_change_pct', 'total_return', 'asset_type'
            ]
            for col in required_cols:
                assert col in result.columns, f"Falta columna: {col}"

    def test_filter_all_returns_all(self, portfolio_service_with_data):
        """Filtro 'all' devuelve todos los activos."""
        result_all = portfolio_service_with_data.get_heatmap_data(category_filter='all')
        # Debe incluir acciones y fondos
        if not result_all.empty:
            asset_types = result_all['asset_type'].unique()
            # sample_transactions tiene acciones y fondos
            assert len(asset_types) >= 1

    def test_filter_acciones(self, portfolio_service_with_data):
        """Filtro 'acciones' solo devuelve acciones."""
        result = portfolio_service_with_data.get_heatmap_data(category_filter='acciones')

        if not result.empty:
            assert all(result['asset_type'] == 'accion')

    def test_filter_fondos_etf(self, portfolio_service_with_data):
        """Filtro 'fondos_etf' solo devuelve fondos y ETFs."""
        result = portfolio_service_with_data.get_heatmap_data(category_filter='fondos_etf')

        if not result.empty:
            valid_types = ['fondo', 'etf']
            assert all(result['asset_type'].isin(valid_types))

    def test_weights_sum_to_100(self, portfolio_service_with_data):
        """Los pesos deben sumar 100% (dentro del filtro)."""
        result = portfolio_service_with_data.get_heatmap_data()

        if not result.empty:
            total_weight = result['weight'].sum()
            assert abs(total_weight - 100) < 0.1, f"Pesos suman {total_weight}, esperado 100"

    def test_display_name_is_truncated(self, portfolio_service_with_data):
        """display_name no debe exceder la longitud máxima."""
        result = portfolio_service_with_data.get_heatmap_data(name_max_length=15)

        if not result.empty:
            for display_name in result['display_name']:
                assert len(display_name) <= 18  # 15 + "..." = 18 max

    def test_daily_change_is_numeric(self, portfolio_service_with_data):
        """daily_change_pct debe ser numérico (no NaN)."""
        result = portfolio_service_with_data.get_heatmap_data()

        if not result.empty:
            assert result['daily_change_pct'].notna().all()
            assert result['daily_change_pct'].dtype in ['float64', 'int64', 'float32', 'int32']

    def test_sorted_by_weight_descending(self, portfolio_service_with_data):
        """Resultado debe estar ordenado por peso descendente."""
        result = portfolio_service_with_data.get_heatmap_data()

        if len(result) > 1:
            weights = result['weight'].tolist()
            assert weights == sorted(weights, reverse=True)


class TestGetLatestPriceAndChange:
    """Tests para MarketDataManager.get_latest_price_and_change()."""

    def test_returns_dict_structure(self, portfolio_service):
        """Verifica que devuelve un dict con la estructura correcta."""
        from src.market_data import MarketDataManager

        mdm = MarketDataManager(portfolio_service.db.db_path)
        result = mdm.get_latest_price_and_change('AAPL')

        # Verificar estructura del resultado
        assert isinstance(result, dict)
        assert 'current_price' in result
        assert 'previous_close' in result
        assert 'daily_change_pct' in result
        assert 'last_date' in result
        assert 'has_data' in result

        mdm.close()

    def test_returns_has_data_false_for_unknown_ticker(self, portfolio_service):
        """Ticker desconocido devuelve has_data=False."""
        from src.market_data import MarketDataManager

        mdm = MarketDataManager(portfolio_service.db.db_path)
        result = mdm.get_latest_price_and_change('TICKER_QUE_NO_EXISTE_XYZ123')

        assert result['has_data'] is False
        assert result['daily_change_pct'] is None

        mdm.close()

    def test_daily_change_not_zero_with_price_history(self, temp_db_path):
        """Con historial de precios, daily_change no debe ser siempre 0."""
        from src.market_data import MarketDataManager
        from src.data import Database
        from datetime import datetime, timedelta

        db = Database(temp_db_path)

        # Insertar precios simulados para un ticker
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        # Añadir precios con variación
        db.add_asset_price('TEST_TICKER', day_before.strftime('%Y-%m-%d'), 100.0, 100.0)
        db.add_asset_price('TEST_TICKER', yesterday.strftime('%Y-%m-%d'), 105.0, 105.0)

        db.close()

        # Probar el método
        mdm = MarketDataManager(temp_db_path)
        result = mdm.get_latest_price_and_change('TEST_TICKER')

        assert result['has_data'] is True
        assert result['current_price'] == 105.0
        assert result['previous_close'] == 100.0
        # Variación esperada: (105 - 100) / 100 * 100 = 5%
        assert abs(result['daily_change_pct'] - 5.0) < 0.01

        mdm.close()

    def test_daily_change_calculation_negative(self, temp_db_path):
        """Verifica cálculo correcto para variación negativa."""
        from src.market_data import MarketDataManager
        from src.data import Database
        from datetime import datetime, timedelta

        db = Database(temp_db_path)

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        # Precio baja de 100 a 95 (-5%)
        db.add_asset_price('TEST_NEG', day_before.strftime('%Y-%m-%d'), 100.0, 100.0)
        db.add_asset_price('TEST_NEG', yesterday.strftime('%Y-%m-%d'), 95.0, 95.0)

        db.close()

        mdm = MarketDataManager(temp_db_path)
        result = mdm.get_latest_price_and_change('TEST_NEG')

        assert result['has_data'] is True
        # Variación esperada: (95 - 100) / 100 * 100 = -5%
        assert abs(result['daily_change_pct'] - (-5.0)) < 0.01

        mdm.close()
