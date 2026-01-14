"""
ProfileManager - Gestor de perfiles/carteras múltiples

Arquitectura Híbrida:
- LocalProfileManager: Múltiples archivos SQLite, selector libre
- CloudProfileManager: PostgreSQL, cartera fija por usuario

El ProfileManagerProtocol define la interfaz común que ambos implementan.

Uso Local:
    from src.core.profile_manager import get_profile_manager

    pm = get_profile_manager()
    profiles = pm.list_profiles()
    db_path = pm.get_db_path('Personal')

Uso Cloud:
    # El factory detecta automáticamente el entorno
    pm = get_profile_manager(session_state)
    if pm.can_switch_portfolio():
        # Mostrar selector
        ...
"""

from pathlib import Path
from typing import List, Dict, Optional, Protocol, runtime_checkable
from datetime import datetime
import shutil

try:
    from src.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)

# Directorio por defecto para carteras
DEFAULT_PORTFOLIOS_DIR = Path(__file__).parent.parent.parent / 'data' / 'portfolios'

# Nombre del perfil por defecto (migración desde database.db existente)
DEFAULT_PROFILE_NAME = 'Principal'


@runtime_checkable
class ProfileManagerProtocol(Protocol):
    """
    Protocolo que define la interfaz común para gestores de perfiles.

    Tanto LocalProfileManager como CloudProfileManager implementan
    esta interfaz, permitiendo código polimórfico en la UI.
    """

    def list_profiles(self) -> List[Dict]:
        """Lista todos los perfiles disponibles."""
        ...

    def get_profile_names(self) -> List[str]:
        """Devuelve solo los nombres de los perfiles."""
        ...

    def profile_exists(self, name: str) -> bool:
        """Verifica si un perfil existe."""
        ...

    def get_db_path(self, profile_name: str) -> str:
        """Obtiene la ruta/identificador de la BD de un perfil."""
        ...

    def get_default_profile(self) -> Optional[str]:
        """Obtiene el nombre del perfil por defecto."""
        ...

    def can_switch_portfolio(self) -> bool:
        """Indica si el usuario puede cambiar de cartera."""
        ...


class LocalProfileManager:
    """
    Gestor de perfiles para modo LOCAL.

    Cada perfil es un archivo SQLite independiente en data/portfolios/.
    Permite gestionar múltiples carteras (personal, familia, clientes)
    con libertad total para cambiar entre ellas.
    """

    def __init__(self, portfolios_dir: str = None):
        """
        Inicializa el gestor de perfiles local.

        Args:
            portfolios_dir: Directorio donde se almacenan las carteras.
                           Si es None, usa data/portfolios/
        """
        if portfolios_dir is None:
            self.portfolios_dir = DEFAULT_PORTFOLIOS_DIR
        else:
            self.portfolios_dir = Path(portfolios_dir)

        # Crear directorio si no existe
        self.portfolios_dir.mkdir(parents=True, exist_ok=True)

        # Verificar si hay que migrar la BD principal existente
        self._check_migration()

        logger.info(f"LocalProfileManager inicializado: {self.portfolios_dir}")

    def _check_migration(self):
        """
        Verifica si existe database.db en data/ y lo migra a portfolios/.

        Esto permite una transición suave desde el sistema de BD única
        al sistema multi-cartera.
        """
        old_db_path = self.portfolios_dir.parent / 'database.db'
        new_db_path = self.portfolios_dir / f'{DEFAULT_PROFILE_NAME}.db'

        if old_db_path.exists() and not new_db_path.exists():
            logger.info(f"Migrando {old_db_path} -> {new_db_path}")
            shutil.copy2(old_db_path, new_db_path)
            logger.info(f"Migración completada: {DEFAULT_PROFILE_NAME}")

    def can_switch_portfolio(self) -> bool:
        """
        Indica si el usuario puede cambiar de cartera.

        En modo local, siempre se permite cambiar.

        Returns:
            True (siempre en modo local)
        """
        return True

    def list_profiles(self) -> List[Dict]:
        """
        Lista todos los perfiles/carteras disponibles.

        Returns:
            Lista de dicts con información de cada perfil:
            [
                {
                    'name': 'Personal',
                    'path': '/path/to/Personal.db',
                    'size_mb': 0.5,
                    'modified': datetime
                },
                ...
            ]
        """
        profiles = []

        for db_file in sorted(self.portfolios_dir.glob('*.db')):
            stat = db_file.stat()
            profiles.append({
                'name': db_file.stem,
                'path': str(db_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime)
            })

        return profiles

    def get_profile_names(self) -> List[str]:
        """
        Devuelve solo los nombres de los perfiles disponibles.

        Returns:
            Lista de nombres de perfiles
        """
        return [p['name'] for p in self.list_profiles()]

    def profile_exists(self, name: str) -> bool:
        """
        Verifica si un perfil existe.

        Args:
            name: Nombre del perfil

        Returns:
            True si existe, False si no
        """
        db_path = self.portfolios_dir / f'{name}.db'
        return db_path.exists()

    def get_db_path(self, profile_name: str) -> str:
        """
        Obtiene la ruta absoluta al archivo de BD de un perfil.

        Args:
            profile_name: Nombre del perfil

        Returns:
            Ruta absoluta como string

        Raises:
            ValueError: Si el perfil no existe
        """
        db_path = self.portfolios_dir / f'{profile_name}.db'

        if not db_path.exists():
            raise ValueError(f"Perfil '{profile_name}' no existe")

        return str(db_path)

    def create_profile(self, name: str) -> str:
        """
        Crea un nuevo perfil/cartera.

        Inicializa un archivo SQLite vacío con todas las tablas necesarias.

        Args:
            name: Nombre del perfil (sin extensión)

        Returns:
            Ruta al archivo creado

        Raises:
            ValueError: Si el perfil ya existe o el nombre es inválido
        """
        # Validar nombre
        if not name or not name.strip():
            raise ValueError("El nombre del perfil no puede estar vacío")

        # Limpiar nombre (quitar caracteres no válidos para nombres de archivo)
        clean_name = self._sanitize_name(name)

        if not clean_name:
            raise ValueError("El nombre del perfil contiene caracteres inválidos")

        db_path = self.portfolios_dir / f'{clean_name}.db'

        if db_path.exists():
            raise ValueError(f"El perfil '{clean_name}' ya existe")

        # Crear BD inicializando las tablas
        try:
            from src.data.database import Database
        except ImportError:
            from data.database import Database

        logger.info(f"Creando perfil: {clean_name}")
        db = Database(db_path=str(db_path))
        db.close()

        logger.info(f"Perfil creado: {db_path}")
        return str(db_path)

    def delete_profile(self, name: str, confirm: bool = False) -> bool:
        """
        Elimina un perfil/cartera.

        Args:
            name: Nombre del perfil
            confirm: Debe ser True para confirmar la eliminación

        Returns:
            True si se eliminó, False si no

        Raises:
            ValueError: Si confirm no es True o el perfil no existe
        """
        if not confirm:
            raise ValueError("Debe confirmar la eliminación con confirm=True")

        db_path = self.portfolios_dir / f'{name}.db'

        if not db_path.exists():
            raise ValueError(f"Perfil '{name}' no existe")

        # No permitir eliminar el último perfil
        if len(self.list_profiles()) <= 1:
            raise ValueError("No se puede eliminar el último perfil")

        logger.warning(f"Eliminando perfil: {name}")
        db_path.unlink()
        logger.info(f"Perfil eliminado: {name}")

        return True

    def rename_profile(self, old_name: str, new_name: str) -> str:
        """
        Renombra un perfil.

        Args:
            old_name: Nombre actual
            new_name: Nuevo nombre

        Returns:
            Nombre sanitizado del perfil (útil si el nombre fue limpiado)

        Raises:
            ValueError: Si el perfil no existe o el nuevo nombre es inválido
        """
        old_path = self.portfolios_dir / f'{old_name}.db'
        clean_new_name = self._sanitize_name(new_name)

        if not clean_new_name:
            raise ValueError("El nuevo nombre contiene solo caracteres inválidos")

        new_path = self.portfolios_dir / f'{clean_new_name}.db'

        if not old_path.exists():
            raise ValueError(f"Perfil '{old_name}' no existe")

        if new_path.exists():
            raise ValueError(f"Ya existe un perfil llamado '{clean_new_name}'")

        logger.info(f"Renombrando perfil: {old_name} -> {clean_new_name}")
        old_path.rename(new_path)

        return clean_new_name

    def duplicate_profile(self, source_name: str, new_name: str) -> str:
        """
        Duplica un perfil existente.

        Args:
            source_name: Nombre del perfil a duplicar
            new_name: Nombre del nuevo perfil

        Returns:
            Ruta al nuevo archivo

        Raises:
            ValueError: Si el origen no existe o el destino ya existe
        """
        source_path = self.portfolios_dir / f'{source_name}.db'
        clean_new_name = self._sanitize_name(new_name)
        new_path = self.portfolios_dir / f'{clean_new_name}.db'

        if not source_path.exists():
            raise ValueError(f"Perfil '{source_name}' no existe")

        if new_path.exists():
            raise ValueError(f"Ya existe un perfil llamado '{clean_new_name}'")

        logger.info(f"Duplicando perfil: {source_name} -> {clean_new_name}")
        shutil.copy2(source_path, new_path)

        return str(new_path)

    def get_default_profile(self) -> Optional[str]:
        """
        Obtiene el nombre del perfil por defecto.

        Prioridad:
        1. Si existe 'Principal', usarlo
        2. Si no, usar el primero disponible
        3. Si no hay ninguno, devolver None

        Returns:
            Nombre del perfil por defecto o None
        """
        profiles = self.get_profile_names()

        if not profiles:
            return None

        if DEFAULT_PROFILE_NAME in profiles:
            return DEFAULT_PROFILE_NAME

        return profiles[0]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Limpia un nombre para usarlo como nombre de archivo.

        Args:
            name: Nombre original

        Returns:
            Nombre limpio (sin caracteres especiales)
        """
        # Caracteres permitidos: letras, números, espacios, guiones, guiones bajos
        allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_áéíóúÁÉÍÓÚñÑ')
        cleaned = ''.join(c for c in name if c in allowed)
        return cleaned.strip()


# Alias para compatibilidad con código existente
ProfileManager = LocalProfileManager


# Instancia global para uso rápido (solo modo local)
_default_manager: Optional[LocalProfileManager] = None


def get_profile_manager(session_state: dict = None) -> ProfileManagerProtocol:
    """
    Obtiene el ProfileManager adecuado según el entorno.

    En modo local, retorna LocalProfileManager (singleton).
    En modo cloud, retorna CloudProfileManager con el portfolio del usuario.

    Args:
        session_state: Estado de sesión de Streamlit (requerido en cloud)

    Returns:
        Instancia de ProfileManager según el entorno
    """
    from src.core.environment import is_cloud_environment

    if is_cloud_environment():
        # Modo cloud: usar CloudProfileManager
        from src.core.cloud_profile_manager import CloudProfileManager

        if session_state is None:
            raise ValueError("session_state es requerido en modo cloud")

        portfolio_id = session_state.get('portfolio_id')
        username = session_state.get('username')

        if portfolio_id is None:
            raise ValueError("portfolio_id no encontrado en session_state")

        return CloudProfileManager(
            portfolio_id=portfolio_id,
            username=username
        )
    else:
        # Modo local: usar singleton de LocalProfileManager
        global _default_manager
        if _default_manager is None:
            _default_manager = LocalProfileManager()
        return _default_manager
