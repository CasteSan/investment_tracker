"""
Tests Package - Investment Tracker

Estructura:
    tests/
    ├── conftest.py          # Fixtures compartidas
    ├── unit/                # Tests unitarios (sin BD real)
    │   └── test_portfolio_service.py
    └── integration/         # Tests de integracion (con BD)
        └── test_database.py

Ejecutar todos los tests:
    pytest

Ejecutar con cobertura:
    pytest --cov=src --cov-report=html

Ejecutar solo unitarios:
    pytest tests/unit/

Ejecutar un archivo especifico:
    pytest tests/unit/test_portfolio_service.py -v
"""
