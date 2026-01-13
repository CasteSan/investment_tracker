"""
Tests para Fund model y FundRepository

Sesion 6 del plan de escalabilidad.
"""

import pytest
from datetime import date

from src.data.models import (
    Fund,
    FUND_CATEGORIES,
    FUND_REGIONS,
    FUND_RISK_LEVELS,
)
from src.data.repositories.fund_repository import FundRepository


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_fund_data():
    """Datos de ejemplo para crear un fondo."""
    return {
        'isin': 'ES0114105036',
        'ticker': 'BINTLF',
        'name': 'Bestinver Internacional FI',
        'short_name': 'Bestinver Internacional',
        'category': 'Renta Variable',
        'subcategory': 'RV Global',
        'asset_class': 'Equity',
        'region': 'Global',
        'manager': 'Bestinver Gestion',
        'manager_country': 'ES',
        'currency': 'EUR',
        'ter': 1.78,
        'risk_level': 5,
        'morningstar_rating': 4,
        'return_1y': 12.5,
        'return_3y': 8.2,
        'aum': 1500.0,
        'min_investment': 100.0,
        'distribution_policy': 'accumulation',
    }


@pytest.fixture
def sample_funds_list():
    """Lista de fondos de ejemplo para tests de busqueda."""
    return [
        {
            'isin': 'ES0114105036',
            'name': 'Bestinver Internacional FI',
            'category': 'Renta Variable',
            'manager': 'Bestinver Gestion',
            'ter': 1.78,
            'risk_level': 5,
            'morningstar_rating': 4,
            'return_1y': 12.5,
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
            'region': 'Global',
        },
        {
            'isin': 'IE00B3RBWM25',
            'name': 'Vanguard FTSE All-World',
            'category': 'Renta Variable',
            'manager': 'Vanguard',
            'ter': 0.22,
            'risk_level': 5,
            'morningstar_rating': 5,
            'return_1y': 18.2,
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
            'region': 'Europa',
        },
        {
            'isin': 'LU0106234643',
            'name': 'MFS Prudent Wealth',
            'category': 'Mixto',
            'manager': 'MFS',
            'ter': 1.45,
            'risk_level': 4,
            'morningstar_rating': 4,
            'return_1y': 8.5,
            'region': 'Global',
        },
    ]


@pytest.fixture
def fund_repository(temp_db_path):
    """Repositorio con BD temporal."""
    from src.data.database import Database
    from src.data.models import Fund

    db = Database(temp_db_path)

    # Crear tabla funds si no existe
    Fund.__table__.create(db.engine, checkfirst=True)

    repo = FundRepository(db.session)
    yield repo
    db.close()


@pytest.fixture
def fund_repository_with_data(fund_repository, sample_funds_list):
    """Repositorio con datos de prueba."""
    for fund_data in sample_funds_list:
        fund = Fund(**fund_data)
        fund_repository.session.add(fund)
    fund_repository.session.commit()
    return fund_repository


# =============================================================================
# TESTS DEL MODELO FUND
# =============================================================================

class TestFundModel:
    """Tests para el modelo Fund."""

    def test_create_fund(self, sample_fund_data):
        """Puede crear un fondo con datos validos."""
        fund = Fund(**sample_fund_data)

        assert fund.isin == 'ES0114105036'
        assert fund.name == 'Bestinver Internacional FI'
        assert fund.category == 'Renta Variable'
        assert fund.ter == 1.78
        assert fund.risk_level == 5

    def test_fund_to_dict(self, sample_fund_data):
        """to_dict devuelve diccionario con todos los campos."""
        fund = Fund(**sample_fund_data)
        fund_dict = fund.to_dict()

        assert fund_dict['isin'] == 'ES0114105036'
        assert fund_dict['name'] == 'Bestinver Internacional FI'
        assert fund_dict['ter'] == 1.78
        assert 'morningstar_rating' in fund_dict

    def test_fund_to_summary_dict(self, sample_fund_data):
        """to_summary_dict devuelve version resumida."""
        fund = Fund(**sample_fund_data)
        summary = fund.to_summary_dict()

        assert 'isin' in summary
        assert 'name' in summary
        assert 'ter' in summary
        assert 'return_1y' in summary
        # No debe incluir todos los campos
        assert 'url' not in summary
        assert 'notes' not in summary

    def test_fund_repr(self, sample_fund_data):
        """__repr__ devuelve string legible."""
        fund = Fund(**sample_fund_data)
        repr_str = repr(fund)

        assert 'ES0114105036' in repr_str
        assert 'Fund' in repr_str


class TestFundConstants:
    """Tests para constantes del modulo."""

    def test_fund_categories_not_empty(self):
        """FUND_CATEGORIES tiene valores."""
        assert len(FUND_CATEGORIES) > 0
        assert 'Renta Variable' in FUND_CATEGORIES
        assert 'Renta Fija' in FUND_CATEGORIES

    def test_fund_regions_not_empty(self):
        """FUND_REGIONS tiene valores."""
        assert len(FUND_REGIONS) > 0
        assert 'Global' in FUND_REGIONS
        assert 'Europa' in FUND_REGIONS

    def test_risk_levels_complete(self):
        """FUND_RISK_LEVELS tiene niveles 1-7."""
        assert len(FUND_RISK_LEVELS) == 7
        for i in range(1, 8):
            assert i in FUND_RISK_LEVELS


# =============================================================================
# TESTS DEL REPOSITORIO
# =============================================================================

class TestFundRepositoryCRUD:
    """Tests para operaciones CRUD basicas."""

    def test_add_fund(self, fund_repository, sample_fund_data):
        """Puede anadir un fondo."""
        fund = Fund(**sample_fund_data)
        saved = fund_repository.add(fund)

        assert saved.id is not None
        assert saved.isin == 'ES0114105036'

    def test_get_by_id(self, fund_repository, sample_fund_data):
        """Puede obtener fondo por ID."""
        fund = Fund(**sample_fund_data)
        saved = fund_repository.add(fund)

        retrieved = fund_repository.get_by_id(saved.id)
        assert retrieved is not None
        assert retrieved.isin == 'ES0114105036'

    def test_get_by_isin(self, fund_repository, sample_fund_data):
        """Puede obtener fondo por ISIN."""
        fund = Fund(**sample_fund_data)
        fund_repository.add(fund)

        retrieved = fund_repository.get_by_isin('ES0114105036')
        assert retrieved is not None
        assert retrieved.name == 'Bestinver Internacional FI'

    def test_get_by_isin_case_insensitive(self, fund_repository, sample_fund_data):
        """Busqueda por ISIN es case-insensitive."""
        fund = Fund(**sample_fund_data)
        fund_repository.add(fund)

        retrieved = fund_repository.get_by_isin('es0114105036')
        assert retrieved is not None

    def test_count(self, fund_repository_with_data):
        """count() devuelve numero correcto."""
        count = fund_repository_with_data.count()
        assert count == 5

    def test_get_all(self, fund_repository_with_data):
        """get_all() devuelve todos los fondos."""
        funds = fund_repository_with_data.get_all()
        assert len(funds) == 5

    def test_get_all_with_limit(self, fund_repository_with_data):
        """get_all() respeta limite."""
        funds = fund_repository_with_data.get_all(limit=2)
        assert len(funds) == 2

    def test_delete(self, fund_repository, sample_fund_data):
        """Puede eliminar un fondo."""
        fund = Fund(**sample_fund_data)
        saved = fund_repository.add(fund)
        fund_id = saved.id

        result = fund_repository.delete(fund_id)
        assert result is True

        retrieved = fund_repository.get_by_id(fund_id)
        assert retrieved is None

    def test_delete_nonexistent(self, fund_repository):
        """delete() con ID inexistente devuelve False."""
        result = fund_repository.delete(9999)
        assert result is False


class TestFundRepositorySearch:
    """Tests para metodos de busqueda."""

    def test_search_by_name(self, fund_repository_with_data):
        """Busca fondos por nombre."""
        funds = fund_repository_with_data.search(name='Vanguard')
        assert len(funds) == 1
        assert 'Vanguard' in funds[0].name

    def test_search_by_category(self, fund_repository_with_data):
        """Busca fondos por categoria."""
        funds = fund_repository_with_data.search(category='Renta Variable')
        assert len(funds) == 3

    def test_search_by_manager(self, fund_repository_with_data):
        """Busca fondos por gestora."""
        funds = fund_repository_with_data.search(manager='Bestinver')
        assert len(funds) == 1

    def test_search_max_ter(self, fund_repository_with_data):
        """Busca fondos con TER maximo."""
        funds = fund_repository_with_data.search(max_ter=1.0)
        assert len(funds) == 2  # Vanguard (0.22) y Carmignac (0.85)

    def test_search_min_rating(self, fund_repository_with_data):
        """Busca fondos con rating minimo."""
        funds = fund_repository_with_data.search(min_rating=5)
        assert len(funds) == 2  # Fidelity y Vanguard

    def test_search_risk_level(self, fund_repository_with_data):
        """Busca fondos por nivel de riesgo exacto."""
        funds = fund_repository_with_data.search(risk_level=5)
        assert len(funds) == 2  # Bestinver y Vanguard

    def test_search_max_risk_level(self, fund_repository_with_data):
        """Busca fondos con riesgo maximo."""
        funds = fund_repository_with_data.search(max_risk_level=3)
        assert len(funds) == 1  # Carmignac

    def test_search_multiple_filters(self, fund_repository_with_data):
        """Combina multiples filtros."""
        funds = fund_repository_with_data.search(
            category='Renta Variable',
            min_rating=5,
            max_ter=1.0
        )
        assert len(funds) == 1  # Solo Vanguard

    def test_search_order_by(self, fund_repository_with_data):
        """Ordena resultados."""
        funds = fund_repository_with_data.search(order_by='ter')
        assert funds[0].ter <= funds[-1].ter  # Ascendente

    def test_search_order_desc(self, fund_repository_with_data):
        """Ordena descendente."""
        funds = fund_repository_with_data.search(
            order_by='return_1y',
            order_desc=True
        )
        assert funds[0].return_1y >= funds[-1].return_1y

    def test_search_with_limit(self, fund_repository_with_data):
        """Limita resultados."""
        funds = fund_repository_with_data.search(limit=2)
        assert len(funds) == 2


class TestFundRepositoryHelpers:
    """Tests para metodos helper."""

    def test_find_by_category(self, fund_repository_with_data):
        """find_by_category es shortcut para search."""
        funds = fund_repository_with_data.find_by_category('Renta Fija')
        assert len(funds) == 1
        assert funds[0].category == 'Renta Fija'

    def test_find_low_cost(self, fund_repository_with_data):
        """find_low_cost busca fondos baratos."""
        funds = fund_repository_with_data.find_low_cost(max_ter=0.5)
        assert len(funds) == 1  # Solo Vanguard
        assert funds[0].ter <= 0.5

    def test_find_top_rated(self, fund_repository_with_data):
        """find_top_rated busca fondos con mejor rating."""
        funds = fund_repository_with_data.find_top_rated(min_rating=4)
        assert len(funds) >= 3
        for fund in funds:
            assert fund.morningstar_rating >= 4

    def test_find_low_risk(self, fund_repository_with_data):
        """find_low_risk busca fondos conservadores."""
        funds = fund_repository_with_data.find_low_risk(max_risk=3)
        for fund in funds:
            assert fund.risk_level <= 3

    def test_get_categories(self, fund_repository_with_data):
        """get_categories devuelve categorias unicas."""
        categories = fund_repository_with_data.get_categories()
        assert 'Renta Variable' in categories
        assert 'Renta Fija' in categories
        assert 'Mixto' in categories
        assert len(categories) == 3

    def test_get_managers(self, fund_repository_with_data):
        """get_managers devuelve gestoras unicas."""
        managers = fund_repository_with_data.get_managers()
        assert 'Vanguard' in managers
        assert 'Fidelity' in managers
        assert len(managers) == 5

    def test_get_stats(self, fund_repository_with_data):
        """get_stats devuelve estadisticas."""
        stats = fund_repository_with_data.get_stats()

        assert stats['total_funds'] == 5
        assert 'by_category' in stats
        assert 'by_risk_level' in stats
        assert stats['by_category']['Renta Variable'] == 3


class TestFundRepositoryUpsert:
    """Tests para operaciones upsert."""

    def test_upsert_insert(self, fund_repository, sample_fund_data):
        """upsert inserta si no existe."""
        result = fund_repository.upsert(sample_fund_data)

        assert result.id is not None
        assert result.isin == 'ES0114105036'

    def test_upsert_update(self, fund_repository, sample_fund_data):
        """upsert actualiza si existe."""
        # Insertar primero
        fund_repository.upsert(sample_fund_data)

        # Actualizar
        updated_data = sample_fund_data.copy()
        updated_data['ter'] = 1.50
        updated_data['return_1y'] = 15.0

        result = fund_repository.upsert(updated_data)

        assert result.ter == 1.50
        assert result.return_1y == 15.0
        assert fund_repository.count() == 1  # No duplicado

    def test_bulk_upsert(self, fund_repository, sample_funds_list):
        """bulk_upsert procesa multiples fondos."""
        result = fund_repository.bulk_upsert(sample_funds_list)

        assert result['inserted'] == 5
        assert result['updated'] == 0
        assert fund_repository.count() == 5
