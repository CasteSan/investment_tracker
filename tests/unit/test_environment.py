"""
Tests para el módulo de detección de entorno y CloudProfileManager

Ejecutar:
    pytest tests/unit/test_environment.py -v
"""

import pytest
import os
from unittest.mock import patch

from src.core.environment import (
    is_cloud_environment,
    is_local_environment,
    get_environment,
    get_database_url,
)
from src.core.cloud_profile_manager import CloudProfileManager
from src.core.profile_manager import (
    LocalProfileManager,
    ProfileManagerProtocol,
    get_profile_manager,
)


class TestEnvironmentDetection:
    """Tests para detección de entorno."""

    def test_local_when_no_database_url(self):
        """Modo local cuando DATABASE_URL no existe."""
        with patch.dict(os.environ, {}, clear=True):
            # Asegurar que DATABASE_URL no existe
            os.environ.pop('DATABASE_URL', None)
            assert is_local_environment() is True
            assert is_cloud_environment() is False
            assert get_environment() == 'local'

    def test_cloud_when_database_url_exists(self):
        """Modo cloud cuando DATABASE_URL existe."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            assert is_cloud_environment() is True
            assert is_local_environment() is False
            assert get_environment() == 'cloud'

    def test_get_database_url_returns_value(self):
        """get_database_url retorna el valor de DATABASE_URL."""
        test_url = 'postgresql://user:pass@host:5432/db'
        with patch.dict(os.environ, {'DATABASE_URL': test_url}):
            assert get_database_url() == test_url

    def test_get_database_url_returns_none_when_missing(self):
        """get_database_url retorna None si no existe."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('DATABASE_URL', None)
            assert get_database_url() is None


class TestCloudProfileManager:
    """Tests para CloudProfileManager."""

    @pytest.fixture
    def cloud_pm(self):
        """CloudProfileManager de prueba."""
        return CloudProfileManager(
            portfolio_id=1,
            username='testuser',
            portfolio_name='Mi Cartera'
        )

    def test_init(self, cloud_pm):
        """Inicialización correcta."""
        assert cloud_pm.portfolio_id == 1
        assert cloud_pm.username == 'testuser'
        assert cloud_pm.get_portfolio_name() == 'Mi Cartera'

    def test_cannot_switch_portfolio(self, cloud_pm):
        """No permite cambiar de portfolio."""
        assert cloud_pm.can_switch_portfolio() is False

    def test_list_profiles_single(self, cloud_pm):
        """Lista solo un portfolio."""
        profiles = cloud_pm.list_profiles()
        assert len(profiles) == 1
        assert profiles[0]['name'] == 'Mi Cartera'
        assert profiles[0]['portfolio_id'] == 1
        assert profiles[0]['is_cloud'] is True

    def test_get_profile_names_single(self, cloud_pm):
        """Nombres solo incluye el portfolio asignado."""
        names = cloud_pm.get_profile_names()
        assert names == ['Mi Cartera']

    def test_profile_exists_own_portfolio(self, cloud_pm):
        """profile_exists True solo para su portfolio."""
        assert cloud_pm.profile_exists('Mi Cartera') is True
        assert cloud_pm.profile_exists('Otro') is False

    def test_get_db_path_cloud_format(self, cloud_pm):
        """get_db_path retorna formato cloud:id."""
        path = cloud_pm.get_db_path()
        assert path == 'cloud:1'

    def test_get_default_profile(self, cloud_pm):
        """Default es siempre el portfolio asignado."""
        assert cloud_pm.get_default_profile() == 'Mi Cartera'

    def test_get_portfolio_id(self, cloud_pm):
        """Obtiene el ID del portfolio."""
        assert cloud_pm.get_portfolio_id() == 1

    def test_get_username(self, cloud_pm):
        """Obtiene el username."""
        assert cloud_pm.get_username() == 'testuser'

    def test_portfolio_name_placeholder(self):
        """Usa placeholder si no se provee nombre."""
        pm = CloudProfileManager(portfolio_id=42)
        assert pm.get_portfolio_name() == 'Portfolio 42'

    # Tests de operaciones no permitidas

    def test_create_profile_raises(self, cloud_pm):
        """create_profile lanza NotImplementedError."""
        with pytest.raises(NotImplementedError, match="no está disponible"):
            cloud_pm.create_profile('Nuevo')

    def test_delete_profile_raises(self, cloud_pm):
        """delete_profile lanza NotImplementedError."""
        with pytest.raises(NotImplementedError, match="no está disponible"):
            cloud_pm.delete_profile('Mi Cartera', confirm=True)

    def test_rename_profile_raises(self, cloud_pm):
        """rename_profile lanza NotImplementedError."""
        with pytest.raises(NotImplementedError, match="no está disponible"):
            cloud_pm.rename_profile('Mi Cartera', 'Nuevo Nombre')

    def test_duplicate_profile_raises(self, cloud_pm):
        """duplicate_profile lanza NotImplementedError."""
        with pytest.raises(NotImplementedError, match="no está disponible"):
            cloud_pm.duplicate_profile('Mi Cartera', 'Copia')


class TestProfileManagerProtocol:
    """Tests para verificar que las clases implementan el protocolo."""

    def test_local_implements_protocol(self, temp_profiles_dir):
        """LocalProfileManager implementa ProfileManagerProtocol."""
        pm = LocalProfileManager(portfolios_dir=temp_profiles_dir)
        assert isinstance(pm, ProfileManagerProtocol)

    def test_cloud_implements_protocol(self):
        """CloudProfileManager implementa ProfileManagerProtocol."""
        pm = CloudProfileManager(portfolio_id=1)
        assert isinstance(pm, ProfileManagerProtocol)


class TestGetProfileManagerFactory:
    """Tests para la factory get_profile_manager."""

    def test_returns_local_when_no_database_url(self, temp_profiles_dir):
        """Retorna LocalProfileManager en modo local."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('DATABASE_URL', None)
            # Forzar reset del singleton para tests
            import src.core.profile_manager as pm_module
            pm_module._default_manager = None

            pm = get_profile_manager()
            assert isinstance(pm, LocalProfileManager)

    def test_returns_cloud_when_database_url_exists(self):
        """Retorna CloudProfileManager en modo cloud."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            session_state = {
                'portfolio_id': 1,
                'username': 'testuser'
            }
            pm = get_profile_manager(session_state)
            assert isinstance(pm, CloudProfileManager)

    def test_cloud_requires_session_state(self):
        """Modo cloud requiere session_state."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            with pytest.raises(ValueError, match="session_state es requerido"):
                get_profile_manager(None)

    def test_cloud_requires_portfolio_id(self):
        """Modo cloud requiere portfolio_id en session_state."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            session_state = {'username': 'testuser'}  # Sin portfolio_id
            with pytest.raises(ValueError, match="portfolio_id no encontrado"):
                get_profile_manager(session_state)


class TestLocalProfileManagerCanSwitch:
    """Test específico para can_switch_portfolio en Local."""

    def test_local_can_switch(self, temp_profiles_dir):
        """LocalProfileManager siempre permite cambiar."""
        pm = LocalProfileManager(portfolios_dir=temp_profiles_dir)
        assert pm.can_switch_portfolio() is True


# Fixture compartida
@pytest.fixture
def temp_profiles_dir():
    """Crea un directorio temporal para perfiles."""
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
