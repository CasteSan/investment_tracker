"""
Tests para FundService

Sesion 7 del plan de escalabilidad.
"""

import pytest
import pandas as pd

from src.services.fund_service import FundService
from src.data.models import Fund


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_funds_data():
    """Datos de fondos para tests."""
    return [
        {
            'isin': 'IE00B3RBWM25',
            'name': 'Vanguard FTSE All-World',
            'category': 'Renta Variable',
            'manager': 'Vanguard',
            'ter': 0.22,
            'risk_level': 5,
            'morningstar_rating': 5,
            'return_1y': 18.2,
            'return_3y': 12.5,
            'region': 'Global',
        },
        {
            'isin': 'LU0048578792',
            'name': 'Fidelity Global Technology',
            'category': 'Renta Variable',
            'manager': 'Fidelity',
            'ter': 1.89,
            'risk_level': 6,
            'morningstar_rating': 5,
            'return_1y': 25.3,
            'return_3y': 18.7,
            'region': 'Global',
        },
        {
            'isin': 'ES0113307001',
            'name': 'Carmignac Securite',
            'category': 'Renta Fija',
            'manager': 'Carmignac',
            'ter': 0.85,
            'risk_level': 2,
            'morningstar_rating': 3,
            'return_1y': 2.1,
            'return_3y': 1.5,
            'region': 'Europa',
        },
    ]


@pytest.fixture
def fund_service(temp_db_path):
    """FundService con BD temporal."""
    service = FundService(temp_db_path)
    yield service
    service.close()


@pytest.fixture
def fund_service_with_data(fund_service, sample_funds_data):
    """FundService con datos de prueba."""
    fund_service.import_funds_bulk(sample_funds_data)
    return fund_service


# =============================================================================
# TESTS DE INICIALIZACION
# =============================================================================

class TestFundServiceInit:
    """Tests para inicializacion del servicio."""

    def test_create_service(self, fund_service):
        """Puede crear el servicio."""
        assert fund_service is not None
        assert fund_service.repository is not None

    def test_context_manager(self, temp_db_path):
        """Soporta context manager."""
        with FundService(temp_db_path) as service:
            assert service is not None

    def test_has_funds_empty(self, fund_service):
        """has_funds devuelve False si no hay fondos."""
        assert fund_service.has_funds() is False

    def test_has_funds_with_data(self, fund_service_with_data):
        """has_funds devuelve True si hay fondos."""
        assert fund_service_with_data.has_funds() is True


# =============================================================================
# TESTS DE BUSQUEDA
# =============================================================================

class TestFundServiceSearch:
    """Tests para busqueda de fondos."""

    def test_search_all(self, fund_service_with_data):
        """search_funds sin filtros devuelve todos."""
        funds = fund_service_with_data.search_funds()
        assert len(funds) == 3

    def test_search_by_name(self, fund_service_with_data):
        """Busca por nombre parcial."""
        funds = fund_service_with_data.search_funds(name='Vanguard')
        assert len(funds) == 1
        assert 'Vanguard' in funds[0].name

    def test_search_by_category(self, fund_service_with_data):
        """Filtra por categoria."""
        funds = fund_service_with_data.search_funds(category='Renta Variable')
        assert len(funds) == 2

    def test_search_by_categories(self, fund_service_with_data):
        """Filtra por multiples categorias."""
        funds = fund_service_with_data.search_funds(
            categories=['Renta Variable', 'Renta Fija']
        )
        assert len(funds) == 3

    def test_search_max_ter(self, fund_service_with_data):
        """Filtra por TER maximo."""
        funds = fund_service_with_data.search_funds(max_ter=1.0)
        assert len(funds) == 2  # Vanguard y Carmignac

    def test_search_min_rating(self, fund_service_with_data):
        """Filtra por rating minimo."""
        funds = fund_service_with_data.search_funds(min_rating=5)
        assert len(funds) == 2  # Vanguard y Fidelity

    def test_search_risk_level(self, fund_service_with_data):
        """Filtra por nivel de riesgo."""
        funds = fund_service_with_data.search_funds(max_risk_level=3)
        assert len(funds) == 1  # Solo Carmignac

    def test_search_as_dataframe(self, fund_service_with_data):
        """Devuelve DataFrame si se solicita."""
        df = fund_service_with_data.search_funds(as_dataframe=True)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_search_with_order(self, fund_service_with_data):
        """Ordena resultados."""
        funds = fund_service_with_data.search_funds(
            order_by='ter',
            order_desc=False
        )
        assert funds[0].ter <= funds[-1].ter


# =============================================================================
# TESTS DE METODOS DE CONVENIENCIA
# =============================================================================

class TestFundServiceHelpers:
    """Tests para metodos helper."""

    def test_find_low_cost_funds(self, fund_service_with_data):
        """find_low_cost_funds busca fondos baratos."""
        funds = fund_service_with_data.find_low_cost_funds(max_ter=0.5)
        assert len(funds) == 1
        assert funds[0].ter <= 0.5

    def test_find_top_rated_funds(self, fund_service_with_data):
        """find_top_rated_funds busca fondos con buen rating."""
        funds = fund_service_with_data.find_top_rated_funds(min_rating=5)
        assert len(funds) == 2
        for f in funds:
            assert f.morningstar_rating >= 5

    def test_find_best_performers(self, fund_service_with_data):
        """find_best_performers ordena por rentabilidad."""
        funds = fund_service_with_data.find_best_performers(limit=2)
        assert len(funds) == 2
        assert funds[0].return_1y >= funds[1].return_1y

    def test_find_conservative_funds(self, fund_service_with_data):
        """find_conservative_funds busca fondos de bajo riesgo."""
        funds = fund_service_with_data.find_conservative_funds(max_risk=3)
        for f in funds:
            assert f.risk_level <= 3

    def test_get_fund_by_isin(self, fund_service_with_data):
        """Obtiene fondo por ISIN."""
        fund = fund_service_with_data.get_fund_by_isin('IE00B3RBWM25')
        assert fund is not None
        assert fund.name == 'Vanguard FTSE All-World'

    def test_get_fund_details(self, fund_service_with_data):
        """get_fund_details devuelve dict completo."""
        details = fund_service_with_data.get_fund_details('IE00B3RBWM25')
        assert details is not None
        assert details['isin'] == 'IE00B3RBWM25'
        assert 'ter' in details
        assert 'morningstar_rating' in details


# =============================================================================
# TESTS DE ESTADISTICAS
# =============================================================================

class TestFundServiceStats:
    """Tests para estadisticas."""

    def test_get_catalog_stats(self, fund_service_with_data):
        """get_catalog_stats devuelve estadisticas."""
        stats = fund_service_with_data.get_catalog_stats()

        assert stats['total_funds'] == 3
        assert 'by_category' in stats
        assert 'by_risk_level' in stats
        assert 'avg_ter' in stats

    def test_get_filter_options(self, fund_service_with_data):
        """get_filter_options devuelve opciones para UI."""
        options = fund_service_with_data.get_filter_options()

        assert 'categories' in options
        assert 'regions' in options
        assert 'managers' in options
        assert 'risk_levels' in options

    def test_count_funds(self, fund_service_with_data):
        """count_funds cuenta con filtros."""
        total = fund_service_with_data.count_funds()
        assert total == 3

        rv_count = fund_service_with_data.count_funds(category='Renta Variable')
        assert rv_count == 2


# =============================================================================
# TESTS DE DATAFRAME
# =============================================================================

class TestFundServiceDataFrame:
    """Tests para conversion a DataFrame."""

    def test_get_funds_dataframe(self, fund_service_with_data):
        """get_funds_dataframe devuelve DataFrame."""
        df = fund_service_with_data.get_funds_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert 'isin' in df.columns
        assert 'name' in df.columns
        assert len(df) == 3

    def test_format_funds_for_display(self, fund_service_with_data):
        """format_funds_for_display formatea valores."""
        df = fund_service_with_data.get_funds_dataframe()
        formatted = fund_service_with_data.format_funds_for_display(df)

        # Columnas renombradas
        assert 'ISIN' in formatted.columns
        assert 'Nombre' in formatted.columns

        # TER formateado
        assert '%' in str(formatted['TER %'].iloc[0])


# =============================================================================
# TESTS DE IMPORTACION
# =============================================================================

class TestFundServiceImport:
    """Tests para importacion de datos."""

    def test_import_fund(self, fund_service):
        """import_fund inserta un fondo."""
        fund_data = {
            'isin': 'TEST123456',
            'name': 'Test Fund',
            'category': 'Renta Variable',
            'ter': 1.0,
        }

        fund = fund_service.import_fund(fund_data)
        assert fund.id is not None
        assert fund.isin == 'TEST123456'

    def test_import_fund_update(self, fund_service):
        """import_fund actualiza si existe."""
        fund_data = {
            'isin': 'TEST123456',
            'name': 'Test Fund',
            'ter': 1.0,
        }
        fund_service.import_fund(fund_data)

        # Actualizar
        fund_data['ter'] = 0.5
        updated = fund_service.import_fund(fund_data)

        assert updated.ter == 0.5
        assert fund_service.repository.count() == 1

    def test_import_funds_bulk(self, fund_service, sample_funds_data):
        """import_funds_bulk importa multiples fondos."""
        result = fund_service.import_funds_bulk(sample_funds_data)

        assert result['inserted'] == 3
        assert result['updated'] == 0
        assert fund_service.has_funds()

    def test_import_from_dataframe(self, fund_service, sample_funds_data):
        """import_from_dataframe importa desde DataFrame."""
        df = pd.DataFrame(sample_funds_data)
        result = fund_service.import_from_dataframe(df)

        assert result['inserted'] == 3
