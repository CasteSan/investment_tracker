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
