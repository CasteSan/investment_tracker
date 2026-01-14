"""
CloudProfileManager - Gestor de perfiles para modo CLOUD

En modo cloud (Streamlit Cloud + Supabase PostgreSQL):
- Cada usuario tiene asignado UN portfolio fijo
- No se permite cambiar de cartera (selector oculto en UI)
- Los datos se filtran por portfolio_id en las queries

Este módulo será completamente funcional en la Fase 2 cuando
se implemente el soporte PostgreSQL.

Uso:
    # Normalmente se obtiene via factory
    from src.core.profile_manager import get_profile_manager

    pm = get_profile_manager(st.session_state)
    # En cloud, retorna CloudProfileManager automáticamente
"""

from typing import List, Dict, Optional

try:
    from src.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)


class CloudProfileManager:
    """
    Gestor de perfiles para modo CLOUD.

    A diferencia de LocalProfileManager que permite múltiples carteras,
    CloudProfileManager restringe al usuario a su cartera asignada.

    El portfolio_id viene del mapeo usuario->portfolio en st.secrets
    y se establece durante el login.
    """

    def __init__(self, portfolio_id: int, username: str = None, portfolio_name: str = None):
        """
        Inicializa el gestor de perfiles cloud.

        Args:
            portfolio_id: ID del portfolio asignado al usuario
            username: Nombre del usuario (opcional, para logging)
            portfolio_name: Nombre del portfolio (opcional, se puede obtener de BD)
        """
        self.portfolio_id = portfolio_id
        self.username = username
        self._portfolio_name = portfolio_name

        logger.info(
            f"CloudProfileManager inicializado: "
            f"user={username}, portfolio_id={portfolio_id}"
        )

    def can_switch_portfolio(self) -> bool:
        """
        Indica si el usuario puede cambiar de cartera.

        En modo cloud, NUNCA se permite cambiar.
        El usuario solo ve su cartera asignada.

        Returns:
            False (siempre en modo cloud)
        """
        return False

    def list_profiles(self) -> List[Dict]:
        """
        Lista los perfiles disponibles para este usuario.

        En modo cloud, solo retorna el portfolio asignado.

        Returns:
            Lista con un solo elemento (el portfolio del usuario)
        """
        return [{
            'name': self.get_portfolio_name(),
            'portfolio_id': self.portfolio_id,
            'is_cloud': True
        }]

    def get_profile_names(self) -> List[str]:
        """
        Devuelve los nombres de perfiles disponibles.

        En modo cloud, solo hay uno.

        Returns:
            Lista con el nombre del portfolio asignado
        """
        return [self.get_portfolio_name()]

    def profile_exists(self, name: str) -> bool:
        """
        Verifica si un perfil existe.

        En modo cloud, solo el portfolio asignado "existe" para este usuario.

        Args:
            name: Nombre del perfil

        Returns:
            True solo si coincide con el portfolio asignado
        """
        return name == self.get_portfolio_name()

    def get_db_path(self, profile_name: str = None) -> str:
        """
        Obtiene el identificador de la BD.

        En modo cloud, esto retorna un identificador especial
        que indica usar PostgreSQL con el portfolio_id.

        Args:
            profile_name: Ignorado en modo cloud

        Returns:
            String especial 'cloud:portfolio_id' que Database interpreta

        Note:
            En Fase 2, Database detectará este formato y usará PostgreSQL.
        """
        # Retorna un identificador especial que Database interpretará
        # para usar PostgreSQL en lugar de SQLite
        return f"cloud:{self.portfolio_id}"

    def get_portfolio_name(self) -> str:
        """
        Obtiene el nombre del portfolio asignado.

        Returns:
            Nombre del portfolio (o placeholder si no está cargado)
        """
        if self._portfolio_name:
            return self._portfolio_name

        # Placeholder hasta que se implemente la consulta a BD
        # En Fase 2, esto consultará la tabla 'portfolios' en PostgreSQL
        return f"Portfolio {self.portfolio_id}"

    def get_portfolio_id(self) -> int:
        """
        Obtiene el ID del portfolio asignado.

        Returns:
            ID numérico del portfolio en PostgreSQL
        """
        return self.portfolio_id

    def get_default_profile(self) -> Optional[str]:
        """
        Obtiene el perfil por defecto.

        En modo cloud, siempre es el portfolio asignado.

        Returns:
            Nombre del portfolio asignado
        """
        return self.get_portfolio_name()

    def get_username(self) -> Optional[str]:
        """
        Obtiene el nombre del usuario actual.

        Returns:
            Username o None si no está disponible
        """
        return self.username

    # Métodos deshabilitados en modo cloud
    # Estos lanzan errores claros para evitar uso accidental

    def create_profile(self, name: str) -> str:
        """No permitido en modo cloud."""
        raise NotImplementedError(
            "create_profile no está disponible en modo cloud. "
            "Los portfolios se gestionan desde el panel de administración."
        )

    def delete_profile(self, name: str, confirm: bool = False) -> bool:
        """No permitido en modo cloud."""
        raise NotImplementedError(
            "delete_profile no está disponible en modo cloud. "
            "Los portfolios se gestionan desde el panel de administración."
        )

    def rename_profile(self, old_name: str, new_name: str) -> str:
        """No permitido en modo cloud."""
        raise NotImplementedError(
            "rename_profile no está disponible en modo cloud. "
            "Los portfolios se gestionan desde el panel de administración."
        )

    def duplicate_profile(self, source_name: str, new_name: str) -> str:
        """No permitido en modo cloud."""
        raise NotImplementedError(
            "duplicate_profile no está disponible en modo cloud. "
            "Los portfolios se gestionan desde el panel de administración."
        )
