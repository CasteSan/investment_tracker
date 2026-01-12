"""
Base Service - Clase base para todos los servicios

Define la interfaz común y funcionalidad compartida entre servicios.
Todos los servicios deben heredar de BaseService.

Patrón: Template Method + Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from src.data.database import Database
    from src.logger import get_logger
except ImportError:
    from data.database import Database
    from logger import get_logger


class BaseService(ABC):
    """
    Clase base abstracta para servicios.

    Proporciona:
    - Gestión automática de conexión a base de datos
    - Logger configurado
    - Método close() para limpieza de recursos
    - Interfaz común para todos los servicios

    Uso:
        class PortfolioService(BaseService):
            def __init__(self, db_path: str = None):
                super().__init__(db_path)
                # Inicialización específica

            def get_dashboard_data(self) -> dict:
                # Implementación
                pass
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa el servicio con conexión a base de datos.

        Args:
            db_path: Ruta opcional a la base de datos.
                    Si es None, usa la ruta por defecto.
        """
        self.db = Database(db_path)
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug(f"{self.__class__.__name__} inicializado")

    def close(self):
        """
        Cierra recursos del servicio.

        Siempre llamar cuando se termine de usar el servicio
        para evitar memory leaks y conexiones abiertas.
        """
        if hasattr(self, 'db') and self.db:
            self.db.close()
            self.logger.debug(f"{self.__class__.__name__} cerrado")

    def __enter__(self):
        """Soporte para context manager (with statement)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra automáticamente al salir del context manager"""
        self.close()
        return False

    def _validate_required_fields(self, data: Dict, required: list) -> bool:
        """
        Valida que un diccionario contenga campos requeridos.

        Args:
            data: Diccionario a validar
            required: Lista de campos requeridos

        Returns:
            True si todos los campos están presentes

        Raises:
            ValueError: Si falta algún campo requerido
        """
        missing = [field for field in required if field not in data or data[field] is None]
        if missing:
            raise ValueError(f"Campos requeridos faltantes: {', '.join(missing)}")
        return True


class ServiceResult:
    """
    Clase para encapsular resultados de servicios.

    Proporciona una forma consistente de devolver resultados
    con información de éxito/error y datos.

    Uso:
        def get_portfolio(self) -> ServiceResult:
            try:
                data = self._fetch_portfolio()
                return ServiceResult.success(data)
            except Exception as e:
                return ServiceResult.error(str(e))
    """

    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def success(cls, data: Any = None) -> 'ServiceResult':
        """Crea un resultado exitoso"""
        return cls(success=True, data=data)

    @classmethod
    def error(cls, message: str) -> 'ServiceResult':
        """Crea un resultado de error"""
        return cls(success=False, error=message)

    def to_dict(self) -> Dict:
        """Convierte a diccionario para serialización"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error
        }
