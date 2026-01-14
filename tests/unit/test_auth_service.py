"""
Tests para AuthService

Cloud Migration - Fase 5

Ejecutar:
    pytest tests/unit/test_auth_service.py -v
"""

import pytest
import hashlib
from unittest.mock import patch, MagicMock

from src.services.auth_service import AuthService


class TestPasswordHashing:
    """Tests para el hashing de passwords."""

    def test_hash_password_returns_sha256(self):
        """El hash es SHA256 de 64 caracteres hex."""
        password = "test_password"
        hash_result = AuthService._hash_password(password)

        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)

    def test_hash_password_is_deterministic(self):
        """El mismo password siempre da el mismo hash."""
        password = "my_secret_123"
        hash1 = AuthService._hash_password(password)
        hash2 = AuthService._hash_password(password)

        assert hash1 == hash2

    def test_hash_password_different_for_different_passwords(self):
        """Passwords diferentes dan hashes diferentes."""
        hash1 = AuthService._hash_password("password1")
        hash2 = AuthService._hash_password("password2")

        assert hash1 != hash2

    def test_generate_password_hash_public_method(self):
        """generate_password_hash es un metodo publico para generar hashes."""
        password = "user_password"
        hash_result = AuthService.generate_password_hash(password)

        expected = hashlib.sha256(password.encode('utf-8')).hexdigest()
        assert hash_result == expected


class TestVerifyCredentials:
    """Tests para verificacion de credenciales."""

    @patch.object(AuthService, '_get_secrets')
    def test_valid_credentials_returns_user_info(self, mock_secrets):
        """Credenciales validas retornan info del usuario."""
        password = "correct_password"
        password_hash = AuthService._hash_password(password)

        mock_secrets.return_value = {
            'users': {
                'testuser': {
                    'password': password_hash,
                    'portfolio_id': 1,
                    'portfolio_name': 'Mi Cartera'
                }
            }
        }

        result = AuthService.verify_credentials('testuser', password)

        assert result is not None
        assert result['username'] == 'testuser'
        assert result['portfolio_id'] == 1
        assert result['portfolio_name'] == 'Mi Cartera'

    @patch.object(AuthService, '_get_secrets')
    def test_invalid_username_returns_none(self, mock_secrets):
        """Usuario inexistente retorna None."""
        mock_secrets.return_value = {
            'users': {
                'existinguser': {'password': 'hash', 'portfolio_id': 1}
            }
        }

        result = AuthService.verify_credentials('nonexistent', 'any_password')
        assert result is None

    @patch.object(AuthService, '_get_secrets')
    def test_invalid_password_returns_none(self, mock_secrets):
        """Password incorrecto retorna None."""
        correct_hash = AuthService._hash_password('correct')
        mock_secrets.return_value = {
            'users': {
                'testuser': {'password': correct_hash, 'portfolio_id': 1}
            }
        }

        result = AuthService.verify_credentials('testuser', 'wrong_password')
        assert result is None

    @patch.object(AuthService, '_get_secrets')
    def test_empty_secrets_returns_none(self, mock_secrets):
        """Sin secrets configurados retorna None."""
        mock_secrets.return_value = {}

        result = AuthService.verify_credentials('anyuser', 'anypass')
        assert result is None


class TestSessionManagement:
    """Tests para gestion de sesion."""

    def test_is_authenticated_false_by_default(self):
        """Por defecto no esta autenticado."""
        session_state = {}
        assert AuthService.is_authenticated(session_state) is False

    def test_is_authenticated_true_when_set(self):
        """Retorna True cuando authenticated=True."""
        session_state = {'authenticated': True}
        assert AuthService.is_authenticated(session_state) is True

    def test_get_current_user_returns_none_when_not_authenticated(self):
        """get_current_user retorna None si no autenticado."""
        session_state = {'authenticated': False}
        assert AuthService.get_current_user(session_state) is None

    def test_get_current_user_returns_info_when_authenticated(self):
        """get_current_user retorna info del usuario si autenticado."""
        session_state = {
            'authenticated': True,
            'username': 'testuser',
            'portfolio_id': 42,
            'portfolio_name': 'Test Portfolio'
        }

        user = AuthService.get_current_user(session_state)

        assert user is not None
        assert user['username'] == 'testuser'
        assert user['portfolio_id'] == 42
        assert user['portfolio_name'] == 'Test Portfolio'

    def test_login_sets_session_state(self):
        """login() establece las variables de sesion."""
        session_state = {}
        user_info = {
            'username': 'newuser',
            'portfolio_id': 5,
            'portfolio_name': 'New Portfolio'
        }

        AuthService.login(session_state, user_info)

        assert session_state['authenticated'] is True
        assert session_state['username'] == 'newuser'
        assert session_state['portfolio_id'] == 5
        assert session_state['portfolio_name'] == 'New Portfolio'

    def test_logout_clears_session_state(self):
        """logout() limpia las variables de sesion."""
        session_state = {
            'authenticated': True,
            'username': 'testuser',
            'portfolio_id': 1,
            'portfolio_name': 'Test'
        }

        AuthService.logout(session_state)

        assert session_state['authenticated'] is False
        assert 'username' not in session_state
        assert 'portfolio_id' not in session_state
        assert 'portfolio_name' not in session_state


class TestEnvironmentDetection:
    """Tests para deteccion de entorno."""

    @patch('src.core.environment.is_cloud_environment')
    def test_is_cloud_mode_true_when_cloud(self, mock_is_cloud):
        """is_cloud_mode retorna True en modo cloud."""
        mock_is_cloud.return_value = True
        assert AuthService.is_cloud_mode() is True

    @patch('src.core.environment.is_cloud_environment')
    def test_is_cloud_mode_false_when_local(self, mock_is_cloud):
        """is_cloud_mode retorna False en modo local."""
        mock_is_cloud.return_value = False
        assert AuthService.is_cloud_mode() is False

    @patch('src.core.environment.is_cloud_environment')
    def test_requires_auth_true_in_cloud(self, mock_is_cloud):
        """requires_auth retorna True en modo cloud."""
        mock_is_cloud.return_value = True
        assert AuthService.requires_auth() is True

    @patch('src.core.environment.is_cloud_environment')
    def test_requires_auth_false_in_local(self, mock_is_cloud):
        """requires_auth retorna False en modo local."""
        mock_is_cloud.return_value = False
        assert AuthService.requires_auth() is False


class TestImportFromServices:
    """Tests para verificar que se puede importar desde services."""

    def test_import_from_services(self):
        """AuthService se puede importar desde src.services."""
        from src.services import AuthService as ImportedAuthService
        assert ImportedAuthService is AuthService
