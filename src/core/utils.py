"""
Utilidades del Core - Funciones auxiliares puras

Funciones de uso general que no dependen de BD ni UI.
"""


def smart_truncate(name: str, max_length: int = 15) -> str:
    """
    Trunca un nombre inteligentemente para mostrar en gráficos.

    Si el nombre es más largo que max_length, lo corta en el último
    espacio antes del límite y añade "...".

    Args:
        name: Nombre completo del activo
        max_length: Longitud máxima permitida (default 15)

    Returns:
        Nombre truncado o original si es suficientemente corto

    Examples:
        >>> smart_truncate("Vanguard Global Stock", 15)
        'Vanguard Glo...'
        >>> smart_truncate("Apple Inc", 15)
        'Apple Inc'
        >>> smart_truncate("iShares Core MSCI World", 20)
        'iShares Core MSC...'
    """
    if not name or len(name) <= max_length:
        return name

    # Reservar espacio para "..."
    truncate_at = max_length - 3

    if truncate_at <= 0:
        return name[:max_length]

    # Buscar último espacio antes del límite para corte limpio
    truncated = name[:truncate_at]
    last_space = truncated.rfind(' ')

    # Si hay espacio y no está muy al principio, cortar ahí
    if last_space > truncate_at // 2:
        return truncated[:last_space] + '...'

    # Si no hay buen punto de corte, truncar directamente
    return truncated + '...'
