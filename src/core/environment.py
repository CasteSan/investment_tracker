"""
Environment Detection Module

Detecta el entorno de ejecución (local vs cloud) para adaptar
el comportamiento de la aplicación.

Uso:
    from src.core.environment import is_cloud_environment, get_environment

    if is_cloud_environment():
        # Modo cloud: PostgreSQL, auth requerida
        ...
    else:
        # Modo local: SQLite, sin auth
        ...
"""

import os
from typing import Literal

EnvironmentType = Literal['local', 'cloud']


def is_cloud_environment() -> bool:
    """
    Detecta si la aplicación está ejecutándose en la nube.

    La detección se basa en la presencia de DATABASE_URL,
    que indica conexión a PostgreSQL en Supabase.

    Returns:
        True si estamos en cloud, False si local
    """
    return os.getenv('DATABASE_URL') is not None


def is_local_environment() -> bool:
    """
    Detecta si la aplicación está ejecutándose localmente.

    Returns:
        True si estamos en local, False si cloud
    """
    return not is_cloud_environment()


def get_environment() -> EnvironmentType:
    """
    Obtiene el nombre del entorno actual.

    Returns:
        'cloud' o 'local'
    """
    return 'cloud' if is_cloud_environment() else 'local'


def get_database_url() -> str | None:
    """
    Obtiene la URL de la base de datos PostgreSQL.

    Returns:
        DATABASE_URL si existe, None si no (modo local)
    """
    return os.getenv('DATABASE_URL')
