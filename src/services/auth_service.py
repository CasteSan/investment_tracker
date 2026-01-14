"""
AuthService - Servicio de Autenticacion para modo Cloud

Cloud Migration - Fase 5

Este servicio maneja la autenticacion de usuarios en modo cloud.
Los usuarios y sus credenciales se almacenan en st.secrets (Streamlit Cloud).

Caracteristicas:
- Verificacion de credenciales con hash SHA256
- Mapeo usuario -> portfolio_id
- Integracion con session_state de Streamlit
- Solo activo en modo cloud (con DATABASE_URL)

Uso:
    from src.services.auth_service import AuthService

    # Verificar credenciales
    user = AuthService.verify_credentials('juan', 'password123')
    if user:
        print(f"Bienvenido! Portfolio ID: {user['portfolio_id']}")

    # Comprobar si esta autenticado
    if AuthService.is_authenticated(st.session_state):
        print("Usuario autenticado")

Configuracion de secrets (.streamlit/secrets.toml):
    [auth.users.juan]
    password = "sha256_hash_aqui"
    portfolio_id = 1
"""

import hashlib
from typing import Optional, Dict, Any

try:
    from src.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """
    Servicio de autenticacion para modo cloud.

    Utiliza st.secrets para almacenar credenciales de forma segura.
    Los passwords deben estar hasheados con SHA256.
    """

    @staticmethod
    def _get_secrets() -> Dict:
        """
        Obtiene los secrets de Streamlit.

        Returns:
            Dict con la configuracion de auth, o dict vacio si no existe.
        """
        try:
            import streamlit as st
            return dict(st.secrets.get('auth', {}))
        except Exception:
            # Fuera de Streamlit o sin secrets configurados
            return {}

    @staticmethod
    def _hash_password(password: str) -> str:
        """
        Genera hash SHA256 de un password.

        Args:
            password: Password en texto plano

        Returns:
            Hash SHA256 en hexadecimal
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def verify_credentials(cls, username: str, password: str) -> Optional[Dict]:
        """
        Verifica las credenciales de un usuario.

        Args:
            username: Nombre de usuario
            password: Password en texto plano (se hashea internamente)

        Returns:
            Dict con info del usuario si credenciales validas:
                {
                    'username': 'juan',
                    'portfolio_id': 1,
                    'portfolio_name': 'Mi Cartera'  # opcional
                }
            None si credenciales invalidas
        """
        secrets = cls._get_secrets()
        users = secrets.get('users', {})

        # Buscar usuario
        user_data = users.get(username)
        if not user_data:
            logger.warning(f"Usuario no encontrado: {username}")
            return None

        # Verificar password
        password_hash = cls._hash_password(password)
        stored_hash = user_data.get('password', '')

        if password_hash != stored_hash:
            logger.warning(f"Password incorrecto para usuario: {username}")
            return None

        # Credenciales validas
        logger.info(f"Login exitoso: {username}")
        return {
            'username': username,
            'portfolio_id': user_data.get('portfolio_id'),
            'portfolio_name': user_data.get('portfolio_name'),
        }

    @staticmethod
    def is_authenticated(session_state: Dict) -> bool:
        """
        Verifica si el usuario esta autenticado.

        Args:
            session_state: st.session_state de Streamlit

        Returns:
            True si autenticado, False si no
        """
        return session_state.get('authenticated', False)

    @staticmethod
    def get_current_user(session_state: Dict) -> Optional[Dict]:
        """
        Obtiene informacion del usuario actual.

        Args:
            session_state: st.session_state de Streamlit

        Returns:
            Dict con info del usuario o None si no autenticado
        """
        if not AuthService.is_authenticated(session_state):
            return None

        return {
            'username': session_state.get('username'),
            'portfolio_id': session_state.get('portfolio_id'),
            'portfolio_name': session_state.get('portfolio_name'),
        }

    @staticmethod
    def login(session_state: Dict, user_info: Dict) -> None:
        """
        Establece la sesion de usuario.

        Args:
            session_state: st.session_state de Streamlit
            user_info: Dict retornado por verify_credentials
        """
        session_state['authenticated'] = True
        session_state['username'] = user_info.get('username')
        session_state['portfolio_id'] = user_info.get('portfolio_id')
        session_state['portfolio_name'] = user_info.get('portfolio_name')
        logger.info(f"Sesion iniciada: {user_info.get('username')}")

    @staticmethod
    def logout(session_state: Dict) -> None:
        """
        Cierra la sesion del usuario.

        Args:
            session_state: st.session_state de Streamlit
        """
        username = session_state.get('username', 'unknown')
        session_state['authenticated'] = False
        session_state.pop('username', None)
        session_state.pop('portfolio_id', None)
        session_state.pop('portfolio_name', None)
        logger.info(f"Sesion cerrada: {username}")

    @classmethod
    def is_cloud_mode(cls) -> bool:
        """
        Verifica si estamos en modo cloud.

        Returns:
            True si DATABASE_URL existe (modo cloud)
        """
        from src.core.environment import is_cloud_environment
        return is_cloud_environment()

    @classmethod
    def requires_auth(cls) -> bool:
        """
        Indica si se requiere autenticacion.

        Solo se requiere auth en modo cloud.

        Returns:
            True si se requiere auth, False si no
        """
        return cls.is_cloud_mode()

    @classmethod
    def generate_password_hash(cls, password: str) -> str:
        """
        Genera un hash SHA256 para un password.

        Util para generar hashes para configurar en secrets.toml

        Args:
            password: Password en texto plano

        Returns:
            Hash SHA256 listo para usar en secrets

        Ejemplo:
            >>> AuthService.generate_password_hash("mi_password_seguro")
            'a1b2c3d4e5f6...'  # Usar este valor en secrets.toml
        """
        return cls._hash_password(password)
