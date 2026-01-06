"""
Logger Module - Sistema de Logging Centralizado
Investment Tracker

Este módulo configura el sistema de logging para toda la aplicación.
Proporciona:
- Logging a consola (con colores)
- Logging a archivo (rotativo)
- Niveles configurables
- Formato consistente

USO BÁSICO:
    from src.logger import get_logger
    
    logger = get_logger(__name__)
    
    logger.debug("Mensaje de debug - para desarrollo")
    logger.info("Mensaje informativo - operación normal")
    logger.warning("Advertencia - algo inesperado pero no crítico")
    logger.error("Error - algo falló")
    logger.critical("Crítico - error grave")

NIVELES DE LOGGING (de menor a mayor severidad):
    DEBUG    = 10  → Información detallada para debugging
    INFO     = 20  → Confirmación de que las cosas funcionan
    WARNING  = 30  → Algo inesperado o problema potencial
    ERROR    = 40  → Error que impide una funcionalidad
    CRITICAL = 50  → Error grave que puede detener la app
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Nivel de logging por defecto (puede cambiarse en config.py)
DEFAULT_LOG_LEVEL = logging.INFO

# Directorio de logs
LOG_DIR = Path(__file__).parent.parent / "logs"

# Formato de los mensajes
LOG_FORMAT_CONSOLE = "%(asctime)s │ %(levelname)-8s │ %(name)-25s │ %(message)s"
LOG_FORMAT_FILE = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%H:%M:%S"
DATE_FORMAT_FILE = "%Y-%m-%d %H:%M:%S"

# Tamaño máximo de archivo de log (5 MB)
MAX_LOG_SIZE = 5 * 1024 * 1024

# Número de archivos de backup
BACKUP_COUNT = 3


# =============================================================================
# COLORES PARA CONSOLA (opcional, mejora legibilidad)
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Formatter que añade colores a los mensajes de consola.
    Solo funciona en terminales que soporten ANSI colors.
    """
    
    # Códigos ANSI de colores
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Verde
        'WARNING': '\033[33m',   # Amarillo
        'ERROR': '\033[31m',     # Rojo
        'CRITICAL': '\033[41m',  # Fondo rojo
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Colorear el nivel
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(record)


# =============================================================================
# CONFIGURACIÓN DEL LOGGER
# =============================================================================

def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_file: str = None
) -> None:
    """
    Configura el sistema de logging para toda la aplicación.
    
    Args:
        level: Nivel mínimo de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Si guardar logs en archivo
        log_to_console: Si mostrar logs en consola
        log_file: Nombre del archivo de log (si None, usa investment_tracker.log)
    
    Ejemplo:
        # Al inicio de la aplicación
        from src.logger import setup_logging
        import logging
        
        setup_logging(level=logging.DEBUG)  # Modo desarrollo
        setup_logging(level=logging.INFO)   # Modo producción
    """
    # Crear directorio de logs si no existe
    if log_to_file:
        LOG_DIR.mkdir(exist_ok=True)
    
    # Obtener el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Limpiar handlers existentes
    root_logger.handlers = []
    
    # Handler de consola
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Usar formatter con colores si la terminal lo soporta
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            console_formatter = ColoredFormatter(LOG_FORMAT_CONSOLE, datefmt=DATE_FORMAT)
        else:
            console_formatter = logging.Formatter(LOG_FORMAT_CONSOLE, datefmt=DATE_FORMAT)
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Handler de archivo (rotativo)
    if log_to_file:
        if log_file is None:
            log_file = LOG_DIR / "investment_tracker.log"
        else:
            log_file = LOG_DIR / log_file
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        file_formatter = logging.Formatter(LOG_FORMAT_FILE, datefmt=DATE_FORMAT_FILE)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Log inicial
    logging.info(f"Sistema de logging inicializado - Nivel: {logging.getLevelName(level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para un módulo.
    
    Args:
        name: Nombre del módulo (usar __name__)
    
    Returns:
        Logger configurado
    
    Ejemplo:
        from src.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Módulo inicializado")
    """
    # Simplificar el nombre para que sea más legible
    # "src.portfolio" → "portfolio"
    if name.startswith("src."):
        name = name[4:]
    
    return logging.getLogger(name)


# =============================================================================
# DECORADORES ÚTILES
# =============================================================================

def log_function_call(logger: logging.Logger):
    """
    Decorador que loguea la entrada y salida de una función.
    
    Uso:
        @log_function_call(logger)
        def mi_funcion(arg1, arg2):
            return resultado
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"→ Entrando en {func_name}()")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"← Saliendo de {func_name}() - OK")
                return result
            except Exception as e:
                logger.error(f"✗ Error en {func_name}(): {e}")
                raise
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger):
    """
    Decorador que mide y loguea el tiempo de ejecución de una función.
    
    Uso:
        @log_execution_time(logger)
        def funcion_lenta():
            # código que puede tardar
            pass
    """
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.debug(f"⏱ {func.__name__}() ejecutado en {elapsed:.3f}s")
            return result
        return wrapper
    return decorator


# =============================================================================
# CONTEXTO DE LOGGING
# =============================================================================

class LogContext:
    """
    Context manager para añadir contexto a los logs.
    
    Uso:
        with LogContext(logger, "Procesando cartera"):
            # código...
            # Los logs dentro mostrarán el contexto
    """
    
    def __init__(self, logger: logging.Logger, context: str):
        self.logger = logger
        self.context = context
    
    def __enter__(self):
        self.logger.info(f"▶ Inicio: {self.context}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"◀ Fin: {self.context} - OK")
        else:
            self.logger.error(f"◀ Fin: {self.context} - ERROR: {exc_val}")
        return False  # No suprimir excepciones


# =============================================================================
# INICIALIZACIÓN POR DEFECTO
# =============================================================================

# Configurar logging básico al importar el módulo
# (puede reconfigurarse después con setup_logging())
if not logging.getLogger().handlers:
    setup_logging(level=DEFAULT_LOG_LEVEL, log_to_file=True, log_to_console=True)
