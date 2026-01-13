"""
Pytest Configuration and Fixtures

Este archivo contiene fixtures compartidas para todos los tests.
Pytest lo detecta automaticamente y las fixtures estan disponibles
en cualquier test sin necesidad de importarlas.

Fixtures principales:
- temp_db_path: Ruta a BD temporal que se limpia despues del test
- test_database: Instancia de Database con BD en memoria
- sample_transactions: Datos de prueba para transacciones
- portfolio_service: PortfolioService con BD temporal
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List
import pandas as pd

# Configurar path para imports
import sys
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# =============================================================================
# FIXTURES DE BASE DE DATOS
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """
    Proporciona una ruta temporal para base de datos.

    La BD se crea en un directorio temporal y se elimina
    automaticamente al finalizar el test.

    Uso:
        def test_something(temp_db_path):
            db = Database(temp_db_path)
            # ... test ...
            db.close()
    """
    db_path = tmp_path / "test_database.db"
    yield str(db_path)
    # Cleanup automatico por tmp_path


@pytest.fixture
def test_database(temp_db_path):
    """
    Proporciona una instancia de Database con BD temporal.

    La conexion se cierra automaticamente al finalizar el test.

    Uso:
        def test_database_ops(test_database):
            test_database.add_transaction({...})
            transactions = test_database.get_transactions()
    """
    from src.data.database import Database

    db = Database(temp_db_path)
    yield db
    db.close()


@pytest.fixture
def test_database_with_data(test_database, sample_transactions, sample_dividends):
    """
    Database con datos de prueba precargados.

    Incluye transacciones y dividendos de ejemplo.
    """
    # Insertar transacciones
    for trans in sample_transactions:
        test_database.add_transaction(trans)

    # Insertar dividendos
    for div in sample_dividends:
        test_database.add_dividend(div)

    yield test_database


# =============================================================================
# FIXTURES DE DATOS DE PRUEBA
# =============================================================================

@pytest.fixture
def sample_transactions() -> List[Dict]:
    """
    Conjunto de transacciones de prueba.

    Incluye:
    - 2 compras de acciones (TEF, SAN)
    - 1 compra de fondo
    - 1 venta parcial
    """
    return [
        {
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEF',
            'name': 'Telefonica',
            'asset_type': 'accion',
            'quantity': 100,
            'price': 4.00,
            'commission': 5.0,
            'currency': 'EUR',
            'market': 'BME'
        },
        {
            'date': '2024-02-01',
            'type': 'buy',
            'ticker': 'SAN',
            'name': 'Banco Santander',
            'asset_type': 'accion',
            'quantity': 50,
            'price': 3.50,
            'commission': 5.0,
            'currency': 'EUR',
            'market': 'BME'
        },
        {
            'date': '2024-03-01',
            'type': 'buy',
            'ticker': 'ES0152743003',
            'name': 'Indexa RV Mixta',
            'asset_type': 'fondo',
            'quantity': 10,
            'price': 120.0,
            'commission': 0.0,
            'currency': 'EUR',
            'market': 'BME'
        },
        {
            'date': '2024-06-15',
            'type': 'sell',
            'ticker': 'TEF',
            'name': 'Telefonica',
            'asset_type': 'accion',
            'quantity': 50,
            'price': 4.50,
            'commission': 5.0,
            'currency': 'EUR',
            'market': 'BME',
            'realized_gain_eur': 20.0
        }
    ]


@pytest.fixture
def sample_dividends() -> List[Dict]:
    """
    Conjunto de dividendos de prueba.
    """
    return [
        {
            'ticker': 'TEF',
            'name': 'Telefonica',
            'date': '2024-06-01',
            'gross_amount': 15.0,
            'net_amount': 12.15,
            'currency': 'EUR'
        },
        {
            'ticker': 'SAN',
            'name': 'Banco Santander',
            'date': '2024-07-15',
            'gross_amount': 8.75,
            'net_amount': 7.09,
            'currency': 'EUR'
        }
    ]


@pytest.fixture
def sample_positions_df() -> pd.DataFrame:
    """
    DataFrame de posiciones de prueba (sin BD).

    Util para testear metodos que procesan DataFrames
    sin necesidad de conexion a BD.
    """
    return pd.DataFrame({
        'ticker': ['TEF', 'SAN', 'FUND1'],
        'name': ['Telefonica', 'Santander', 'Fondo Test'],
        'asset_type': ['accion', 'accion', 'fondo'],
        'quantity': [100.0, 50.0, 10.0],
        'avg_price': [4.0, 3.5, 120.0],
        'cost_basis': [400.0, 175.0, 1200.0],
        'market_value': [450.0, 200.0, 1250.0],
        'unrealized_gain': [50.0, 25.0, 50.0],
        'unrealized_gain_pct': [12.5, 14.3, 4.2]
    })


@pytest.fixture
def empty_positions_df() -> pd.DataFrame:
    """DataFrame vacio con estructura correcta de posiciones."""
    return pd.DataFrame(columns=[
        'ticker', 'name', 'asset_type', 'quantity', 'avg_price',
        'cost_basis', 'market_value', 'unrealized_gain', 'unrealized_gain_pct'
    ])


# =============================================================================
# FIXTURES DE SERVICIOS
# =============================================================================

@pytest.fixture
def portfolio_service(temp_db_path):
    """
    PortfolioService con BD temporal.

    Uso:
        def test_service(portfolio_service):
            data = portfolio_service.get_dashboard_data()
            portfolio_service.close()
    """
    from src.services.portfolio_service import PortfolioService

    service = PortfolioService(db_path=temp_db_path)
    yield service
    service.close()


@pytest.fixture
def portfolio_service_with_data(temp_db_path, sample_transactions):
    """
    PortfolioService con datos de prueba precargados.
    """
    from src.services.portfolio_service import PortfolioService
    from src.data.database import Database

    # Insertar datos primero
    db = Database(temp_db_path)
    for trans in sample_transactions:
        db.add_transaction(trans)
    db.close()

    # Crear servicio
    service = PortfolioService(db_path=temp_db_path)
    yield service
    service.close()


# =============================================================================
# FIXTURES DE CONFIGURACION
# =============================================================================

@pytest.fixture
def fiscal_year():
    """Año fiscal para tests."""
    return 2024


@pytest.fixture
def fiscal_method():
    """Metodo fiscal por defecto."""
    return 'FIFO'


# =============================================================================
# HELPERS
# =============================================================================

def assert_dataframe_equal(df1: pd.DataFrame, df2: pd.DataFrame, check_order: bool = False):
    """
    Helper para comparar DataFrames en tests.

    Args:
        df1: Primer DataFrame
        df2: Segundo DataFrame
        check_order: Si verificar el orden de filas
    """
    if not check_order:
        df1 = df1.sort_values(by=df1.columns.tolist()).reset_index(drop=True)
        df2 = df2.sort_values(by=df2.columns.tolist()).reset_index(drop=True)

    pd.testing.assert_frame_equal(df1, df2)
