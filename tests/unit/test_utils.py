"""
Tests para src/core/utils.py
"""

import pytest
from src.core.utils import smart_truncate


class TestSmartTruncate:
    """Tests para la función smart_truncate"""

    def test_short_name_unchanged(self):
        """Nombres cortos no se modifican"""
        assert smart_truncate("Apple Inc", 15) == "Apple Inc"
        assert smart_truncate("BBVA", 15) == "BBVA"

    def test_exact_length_unchanged(self):
        """Nombres de longitud exacta no se modifican"""
        assert smart_truncate("Nombre Exacto!!", 15) == "Nombre Exacto!!"

    def test_long_name_truncated(self):
        """Nombres largos se truncan con ..."""
        result = smart_truncate("Vanguard Global Stock Index Fund", 15)
        assert len(result) <= 15
        assert result.endswith("...")

    def test_cuts_at_space_when_possible(self):
        """Corta en espacio si hay uno cerca del límite"""
        result = smart_truncate("Vanguard Global Stock", 15)
        # Debería cortar en un espacio, no en medio de palabra
        assert "..." in result
        # El resultado no debería tener una palabra cortada antes del ...
        before_ellipsis = result[:-3]
        assert not before_ellipsis.endswith(" ")  # No espacio justo antes

    def test_empty_string(self):
        """String vacío devuelve vacío"""
        assert smart_truncate("", 15) == ""

    def test_none_returns_none(self):
        """None devuelve None"""
        assert smart_truncate(None, 15) is None

    def test_custom_max_length(self):
        """Funciona con diferentes longitudes máximas"""
        name = "iShares Core MSCI World ETF"

        result_10 = smart_truncate(name, 10)
        assert len(result_10) <= 10

        result_20 = smart_truncate(name, 20)
        assert len(result_20) <= 20

        result_30 = smart_truncate(name, 30)
        assert len(result_30) <= 30

    def test_very_short_max_length(self):
        """Maneja longitudes máximas muy cortas"""
        result = smart_truncate("Test Name", 5)
        assert len(result) <= 5

    def test_single_word_truncated(self):
        """Palabras únicas largas se truncan directamente"""
        result = smart_truncate("Supercalifragilistico", 15)
        assert len(result) <= 15
        assert result.endswith("...")

    def test_preserves_short_words(self):
        """No corta si el nombre ya cabe"""
        short_names = ["AAPL", "MSFT", "GOOGL", "Meta"]
        for name in short_names:
            assert smart_truncate(name, 15) == name

    def test_realistic_fund_names(self):
        """Prueba con nombres reales de fondos"""
        test_cases = [
            ("Vanguard S&P 500 ETF", 15),
            ("iShares Core MSCI World UCITS ETF", 15),
            ("Fidelity Global Technology Fund", 20),
            ("BlackRock Global Allocation Fund", 18),
        ]

        for name, max_len in test_cases:
            result = smart_truncate(name, max_len)
            assert len(result) <= max_len, f"'{result}' excede {max_len} caracteres"
            if len(name) > max_len:
                assert result.endswith("..."), f"'{result}' debería terminar en ..."
