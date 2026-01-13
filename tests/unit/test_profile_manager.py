"""
Tests para ProfileManager

Ejecutar:
    pytest tests/unit/test_profile_manager.py -v
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path

from src.core.profile_manager import ProfileManager

# Windows tiene problemas con archivos SQLite bloqueados
IS_WINDOWS = sys.platform == 'win32'


@pytest.fixture
def temp_profiles_dir():
    """Crea un directorio temporal para perfiles."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def profile_manager(temp_profiles_dir):
    """ProfileManager con directorio temporal."""
    return ProfileManager(portfolios_dir=temp_profiles_dir)


class TestProfileManagerInit:
    """Tests de inicialización."""

    def test_creates_directory(self, temp_profiles_dir):
        """Crea el directorio de portfolios si no existe."""
        subdir = Path(temp_profiles_dir) / 'subdir'
        pm = ProfileManager(portfolios_dir=str(subdir))
        assert subdir.exists()

    def test_list_empty_profiles(self, profile_manager):
        """Lista vacía cuando no hay perfiles."""
        profiles = profile_manager.list_profiles()
        assert profiles == []


class TestCreateProfile:
    """Tests para crear perfiles."""

    def test_create_profile(self, profile_manager):
        """Crea un perfil correctamente."""
        path = profile_manager.create_profile('Test')
        assert Path(path).exists()
        assert 'Test.db' in path

    def test_create_profile_appears_in_list(self, profile_manager):
        """El perfil creado aparece en la lista."""
        profile_manager.create_profile('MiCartera')
        names = profile_manager.get_profile_names()
        assert 'MiCartera' in names

    def test_create_duplicate_raises(self, profile_manager):
        """No permite crear perfiles duplicados."""
        profile_manager.create_profile('Duplicado')
        with pytest.raises(ValueError, match="ya existe"):
            profile_manager.create_profile('Duplicado')

    def test_create_empty_name_raises(self, profile_manager):
        """No permite nombres vacíos."""
        with pytest.raises(ValueError, match="vacío"):
            profile_manager.create_profile('')

    def test_sanitize_name(self, profile_manager):
        """Limpia caracteres especiales del nombre."""
        path = profile_manager.create_profile('Mi Cartera 2024')
        assert Path(path).exists()


class TestGetDbPath:
    """Tests para obtener rutas de BD."""

    def test_get_db_path(self, profile_manager):
        """Devuelve ruta correcta."""
        profile_manager.create_profile('Personal')
        path = profile_manager.get_db_path('Personal')
        assert 'Personal.db' in path
        assert Path(path).exists()

    def test_get_db_path_nonexistent_raises(self, profile_manager):
        """Error si el perfil no existe."""
        with pytest.raises(ValueError, match="no existe"):
            profile_manager.get_db_path('NoExiste')


class TestProfileExists:
    """Tests para verificar existencia."""

    def test_profile_exists_true(self, profile_manager):
        """Devuelve True si existe."""
        profile_manager.create_profile('Existe')
        assert profile_manager.profile_exists('Existe') is True

    def test_profile_exists_false(self, profile_manager):
        """Devuelve False si no existe."""
        assert profile_manager.profile_exists('NoExiste') is False


class TestDeleteProfile:
    """Tests para eliminar perfiles."""

    def test_delete_requires_confirm(self, profile_manager):
        """Requiere confirmación."""
        profile_manager.create_profile('ABorrar')
        with pytest.raises(ValueError, match="confirmar"):
            profile_manager.delete_profile('ABorrar')

    @pytest.mark.skipif(IS_WINDOWS, reason="Windows mantiene archivos SQLite bloqueados")
    def test_delete_with_confirm(self, profile_manager):
        """Elimina con confirmación."""
        profile_manager.create_profile('Uno')
        profile_manager.create_profile('Dos')
        result = profile_manager.delete_profile('Uno', confirm=True)
        assert result is True
        assert not profile_manager.profile_exists('Uno')

    def test_cannot_delete_last_profile(self, profile_manager):
        """No permite eliminar el último perfil."""
        profile_manager.create_profile('Unico')
        with pytest.raises(ValueError, match="último"):
            profile_manager.delete_profile('Unico', confirm=True)


class TestRenameProfile:
    """Tests para renombrar perfiles."""

    @pytest.mark.skipif(IS_WINDOWS, reason="Windows mantiene archivos SQLite bloqueados")
    def test_rename_profile(self, profile_manager):
        """Renombra correctamente."""
        profile_manager.create_profile('Antiguo')
        profile_manager.rename_profile('Antiguo', 'Nuevo')
        assert profile_manager.profile_exists('Nuevo')
        assert not profile_manager.profile_exists('Antiguo')

    def test_rename_to_existing_raises(self, profile_manager):
        """No permite renombrar a nombre existente."""
        profile_manager.create_profile('A')
        profile_manager.create_profile('B')
        with pytest.raises(ValueError, match="Ya existe"):
            profile_manager.rename_profile('A', 'B')


class TestDuplicateProfile:
    """Tests para duplicar perfiles."""

    def test_duplicate_profile(self, profile_manager):
        """Duplica correctamente."""
        profile_manager.create_profile('Original')
        profile_manager.duplicate_profile('Original', 'Copia')
        assert profile_manager.profile_exists('Original')
        assert profile_manager.profile_exists('Copia')


class TestGetDefaultProfile:
    """Tests para perfil por defecto."""

    def test_default_none_when_empty(self, profile_manager):
        """Devuelve None si no hay perfiles."""
        assert profile_manager.get_default_profile() is None

    def test_default_returns_first(self, profile_manager):
        """Devuelve el primero si no hay 'Principal'."""
        profile_manager.create_profile('Alfa')
        profile_manager.create_profile('Beta')
        default = profile_manager.get_default_profile()
        assert default == 'Alfa'

    def test_default_prefers_principal(self, profile_manager):
        """Prefiere 'Principal' si existe."""
        profile_manager.create_profile('Otro')
        profile_manager.create_profile('Principal')
        default = profile_manager.get_default_profile()
        assert default == 'Principal'


class TestListProfiles:
    """Tests para listar perfiles."""

    def test_list_returns_metadata(self, profile_manager):
        """Lista incluye metadatos."""
        profile_manager.create_profile('ConDatos')
        profiles = profile_manager.list_profiles()

        assert len(profiles) == 1
        p = profiles[0]
        assert p['name'] == 'ConDatos'
        assert 'path' in p
        assert 'size_mb' in p
        assert 'modified' in p
