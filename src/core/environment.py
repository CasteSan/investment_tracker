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


def _get_database_url_from_secrets() -> str | None:
    """
    Intenta obtener DATABASE_URL desde st.secrets (Streamlit Cloud).

    Returns:
        DATABASE_URL si existe en secrets, None si no
    """
    try:
        import streamlit as st
        return st.secrets.get('DATABASE_URL')
    except Exception:
        return None


def is_cloud_environment() -> bool:
    """
    Detecta si la aplicación está ejecutándose en la nube.

    La detección se basa en la presencia de DATABASE_URL:
    1. Primero verifica os.environ (variable de entorno)
    2. Luego verifica st.secrets (Streamlit Cloud)

    Returns:
        True si estamos en cloud, False si local
    """
    # Verificar variable de entorno
    if os.getenv('DATABASE_URL') is not None:
        return True

    # Verificar Streamlit secrets
    if _get_database_url_from_secrets() is not None:
        return True

    return False


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

    Busca en:
    1. os.environ (variable de entorno)
    2. st.secrets (Streamlit Cloud)

    Returns:
        DATABASE_URL si existe, None si no (modo local)
    """
    # Primero verificar variable de entorno
    url = os.getenv('DATABASE_URL')
    if url:
        return url

    # Luego verificar Streamlit secrets
    return _get_database_url_from_secrets()
