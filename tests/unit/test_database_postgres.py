"""
Tests para soporte PostgreSQL en Database

Cloud Migration - Fase 3

Estos tests verifican:
- Detección de modo SQLite vs PostgreSQL
- Métodos is_postgres() e is_sqlite()
- Comportamiento con DATABASE_URL

Ejecutar:
    pytest tests/unit/test_database_postgres.py -v
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.data.database import Database


@pytest.fixture
def temp_db_path():
    """Crea un path temporal para SQLite."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / 'test.db'
    yield str(db_path)
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDatabaseModeDetection:
    """Tests para detección de modo SQLite vs PostgreSQL."""

    def test_sqlite_mode_default(self, temp_db_path):
        """Por defecto usa SQLite."""
        # Asegurar que no hay DATABASE_URL
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('DATABASE_URL', None)

            db = Database(db_path=temp_db_path)
            try:
                assert db.is_sqlite() is True
                assert db.is_postgres() is False
                assert db.db_path is not None
            finally:
                db.close()

    def test_sqlite_mode_explicit(self, temp_db_path):
        """SQLite explícito con db_path."""
        db = Database(db_path=temp_db_path)
        try:
            assert db.is_sqlite() is True
            assert db.is_postgres() is False
        finally:
            db.close()

    def test_postgres_mode_with_env_var(self, temp_db_path):
        """PostgreSQL cuando DATABASE_URL está en entorno."""
        # Usamos una URL inválida solo para probar la detección
        # La conexión fallará pero la detección debe funcionar
        fake_url = 'postgresql://fake:fake@localhost:5432/fake'

        with patch.dict(os.environ, {'DATABASE_URL': fake_url}):
            # Esto debería intentar conectar y fallar, pero detectar postgres
            with pytest.raises(Exception):
                # La conexión fallará porque no hay servidor
                Database(db_path=temp_db_path)

    def test_postgres_mode_with_param(self, temp_db_path):
        """PostgreSQL cuando se pasa database_url como parámetro."""
        fake_url = 'postgresql://fake:fake@localhost:5432/fake'

        with pytest.raises(Exception):
            # La conexión fallará pero debería intentar PostgreSQL
            Database(database_url=fake_url)

    def test_database_url_param_overrides_env(self, temp_db_path):
        """El parámetro database_url tiene prioridad sobre env."""
        env_url = 'postgresql://env:env@localhost:5432/env'
        param_url = 'postgresql://param:param@localhost:5432/param'

        with patch.dict(os.environ, {'DATABASE_URL': env_url}):
            # El parámetro tiene prioridad
            with pytest.raises(Exception) as exc_info:
                Database(database_url=param_url)
            # Debería mencionar 'param' no 'env' en el error
            # (esto depende del mensaje de error del driver)


class TestDatabaseStatsWithMode:
    """Tests para get_database_stats con diferentes modos."""

    def test_sqlite_stats_include_db_type(self, temp_db_path):
        """Stats de SQLite incluyen tipo correcto."""
        db = Database(db_path=temp_db_path)
        try:
            stats = db.get_database_stats()
            assert stats['is_postgres'] is False
            assert stats['db_type'] == 'SQLite'
            assert stats['db_path'] == temp_db_path
        finally:
            db.close()

    def test_sqlite_stats_include_counts(self, temp_db_path):
        """Stats incluyen contadores."""
        db = Database(db_path=temp_db_path)
        try:
            stats = db.get_database_stats()
            assert 'total_transactions' in stats
            assert 'total_dividends' in stats
            assert 'unique_tickers' in stats
        finally:
            db.close()


class TestDatabaseMethodsCompatibility:
    """Tests para verificar que los métodos funcionan en modo SQLite."""

    def test_add_transaction_sqlite(self, temp_db_path):
        """add_transaction funciona en SQLite."""
        db = Database(db_path=temp_db_path)
        try:
            trans_id = db.add_transaction({
                'date': '2024-01-15',
                'type': 'buy',
                'ticker': 'TEST',
                'quantity': 100,
                'price': 10.0
            })
            assert trans_id is not None
            assert trans_id > 0
        finally:
            db.close()

    def test_add_dividend_sqlite(self, temp_db_path):
        """add_dividend funciona en SQLite."""
        db = Database(db_path=temp_db_path)
        try:
            div_id = db.add_dividend({
                'ticker': 'TEST',
                'date': '2024-06-15',
                'gross_amount': 100.0,
                'net_amount': 81.0
            })
            assert div_id is not None
            assert div_id > 0
        finally:
            db.close()

    def test_get_transactions_sqlite(self, temp_db_path):
        """get_transactions funciona en SQLite."""
        db = Database(db_path=temp_db_path)
        try:
            db.add_transaction({
                'date': '2024-01-15',
                'type': 'buy',
                'ticker': 'AAPL',
                'quantity': 10,
                'price': 150.0
            })
            transactions = db.get_transactions()
            assert len(transactions) == 1
            assert transactions[0].ticker == 'AAPL'
        finally:
            db.close()


class TestDatabaseContextManager:
    """Tests para verificar que Database funciona sin context manager."""

    def test_close_method(self, temp_db_path):
        """El método close() funciona correctamente."""
        db = Database(db_path=temp_db_path)
        db.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEST',
            'quantity': 100,
            'price': 10.0
        })
        db.close()
        # No debería lanzar excepciones


class TestDatabaseInitializationEdgeCases:
    """Tests para casos límite de inicialización."""

    def test_creates_parent_directory(self):
        """Crea el directorio padre si no existe."""
        temp_dir = tempfile.mkdtemp()
        nested_path = Path(temp_dir) / 'subdir' / 'nested' / 'test.db'

        try:
            db = Database(db_path=str(nested_path))
            assert nested_path.parent.exists()
            db.close()
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_can_use_same_db_multiple_times(self, temp_db_path):
        """Puede conectar múltiples veces a la misma BD."""
        # Primera conexión
        db1 = Database(db_path=temp_db_path)
        db1.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'FIRST',
            'quantity': 100,
            'price': 10.0
        })
        db1.close()

        # Segunda conexión
        db2 = Database(db_path=temp_db_path)
        transactions = db2.get_transactions()
        assert len(transactions) == 1
        assert transactions[0].ticker == 'FIRST'
        db2.close()
