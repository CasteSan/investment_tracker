"""
Excepciones personalizadas del dominio

Este módulo define excepciones específicas del negocio que permiten
un manejo de errores más granular y mensajes más claros para el usuario.

Jerarquía:
    InvestmentTrackerError (base)
    ├── DatabaseError
    │   ├── ConnectionError
    │   └── IntegrityError
    ├── ValidationError
    │   ├── InvalidTickerError
    │   ├── InvalidDateError
    │   └── InvalidAmountError
    ├── BusinessLogicError
    │   ├── InsufficientSharesError
    │   ├── DuplicateTransactionError
    │   └── InvalidOperationError
    └── ExternalServiceError
        ├── MarketDataError
        └── APIRateLimitError

Uso:
    from src.exceptions import InsufficientSharesError

    if shares_to_sell > available_shares:
        raise InsufficientSharesError(
            ticker="AAPL",
            requested=shares_to_sell,
            available=available_shares
        )
"""


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class InvestmentTrackerError(Exception):
    """
    Excepción base para todas las excepciones del proyecto.

    Todas las excepciones personalizadas heredan de esta clase.
    """

    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Serializa la excepción para respuestas API"""
        return {
            'error': True,
            'code': self.code,
            'message': self.message
        }


# =============================================================================
# DATABASE ERRORS
# =============================================================================

class DatabaseError(InvestmentTrackerError):
    """Error relacionado con la base de datos"""
    pass


class DatabaseConnectionError(DatabaseError):
    """No se pudo conectar a la base de datos"""

    def __init__(self, db_path: str = None):
        message = f"No se pudo conectar a la base de datos"
        if db_path:
            message += f": {db_path}"
        super().__init__(message, code="DB_CONNECTION_ERROR")


class DatabaseIntegrityError(DatabaseError):
    """Error de integridad en la base de datos"""

    def __init__(self, detail: str = None):
        message = "Error de integridad en la base de datos"
        if detail:
            message += f": {detail}"
        super().__init__(message, code="DB_INTEGRITY_ERROR")


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(InvestmentTrackerError):
    """Error de validación de datos"""
    pass


class InvalidTickerError(ValidationError):
    """Ticker no válido o no encontrado"""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(
            f"Ticker no válido o no encontrado: {ticker}",
            code="INVALID_TICKER"
        )


class InvalidDateError(ValidationError):
    """Fecha no válida"""

    def __init__(self, date_value: str, reason: str = None):
        self.date_value = date_value
        message = f"Fecha no válida: {date_value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, code="INVALID_DATE")


class InvalidAmountError(ValidationError):
    """Cantidad o importe no válido"""

    def __init__(self, field: str, value, reason: str = None):
        self.field = field
        self.value = value
        message = f"Valor no válido para {field}: {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, code="INVALID_AMOUNT")


# =============================================================================
# BUSINESS LOGIC ERRORS
# =============================================================================

class BusinessLogicError(InvestmentTrackerError):
    """Error en la lógica de negocio"""
    pass


class InsufficientSharesError(BusinessLogicError):
    """
    Intento de vender más acciones de las disponibles.

    Este error se produce al intentar realizar una venta
    cuando no hay suficientes acciones en cartera.
    """

    def __init__(self, ticker: str, requested: float, available: float):
        self.ticker = ticker
        self.requested = requested
        self.available = available
        super().__init__(
            f"No hay suficientes acciones de {ticker}. "
            f"Solicitadas: {requested}, Disponibles: {available}",
            code="INSUFFICIENT_SHARES"
        )


class DuplicateTransactionError(BusinessLogicError):
    """Transacción duplicada detectada"""

    def __init__(self, ticker: str, date: str, transaction_type: str):
        self.ticker = ticker
        self.date = date
        self.transaction_type = transaction_type
        super().__init__(
            f"Posible transacción duplicada: {transaction_type} de {ticker} en {date}",
            code="DUPLICATE_TRANSACTION"
        )


class InvalidOperationError(BusinessLogicError):
    """Operación no permitida en el estado actual"""

    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Operación no permitida ({operation}): {reason}",
            code="INVALID_OPERATION"
        )


# =============================================================================
# EXTERNAL SERVICE ERRORS
# =============================================================================

class ExternalServiceError(InvestmentTrackerError):
    """Error en servicio externo"""
    pass


class MarketDataError(ExternalServiceError):
    """Error al obtener datos de mercado"""

    def __init__(self, ticker: str = None, provider: str = None, detail: str = None):
        self.ticker = ticker
        self.provider = provider
        message = "Error al obtener datos de mercado"
        if ticker:
            message += f" para {ticker}"
        if provider:
            message += f" desde {provider}"
        if detail:
            message += f": {detail}"
        super().__init__(message, code="MARKET_DATA_ERROR")


class APIRateLimitError(ExternalServiceError):
    """Límite de llamadas API excedido"""

    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"Límite de llamadas excedido para {provider}"
        if retry_after:
            message += f". Reintentar en {retry_after} segundos"
        super().__init__(message, code="API_RATE_LIMIT")


class TickerNotFoundError(ExternalServiceError):
    """Ticker no encontrado en el proveedor de datos"""

    def __init__(self, ticker: str, provider: str = None):
        self.ticker = ticker
        self.provider = provider
        message = f"Ticker '{ticker}' no encontrado"
        if provider:
            message += f" en {provider}"
        super().__init__(message, code="TICKER_NOT_FOUND")


# =============================================================================
# EXPORT ALL
# =============================================================================

__all__ = [
    # Base
    'InvestmentTrackerError',

    # Database
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseIntegrityError',

    # Validation
    'ValidationError',
    'InvalidTickerError',
    'InvalidDateError',
    'InvalidAmountError',

    # Business Logic
    'BusinessLogicError',
    'InsufficientSharesError',
    'DuplicateTransactionError',
    'InvalidOperationError',

    # External Services
    'ExternalServiceError',
    'MarketDataError',
    'APIRateLimitError',
    'TickerNotFoundError',
]
