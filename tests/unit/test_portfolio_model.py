"""
Tests para el modelo Portfolio y los campos portfolio_id

Cloud Migration - Fase 2

Ejecutar:
    pytest tests/unit/test_portfolio_model.py -v
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.data.database import Database, Transaction, Dividend
from src.data.models import Portfolio


@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para tests."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / 'test.db'
    db = Database(db_path=str(db_path))
    yield db
    db.close()
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestPortfolioModel:
    """Tests para el modelo Portfolio."""

    def test_create_portfolio(self, temp_db):
        """Puede crear un portfolio."""
        portfolio = Portfolio(
            name='Mi Cartera',
            description='Cartera de prueba'
        )
        temp_db.session.add(portfolio)
        temp_db.session.commit()

        assert portfolio.id is not None
        assert portfolio.name == 'Mi Cartera'
        assert portfolio.description == 'Cartera de prueba'
        assert portfolio.created_at is not None

    def test_portfolio_to_dict(self, temp_db):
        """to_dict() retorna diccionario correcto."""
        portfolio = Portfolio(name='Test Portfolio')
        temp_db.session.add(portfolio)
        temp_db.session.commit()

        d = portfolio.to_dict()
        assert d['id'] == portfolio.id
        assert d['name'] == 'Test Portfolio'
        assert 'created_at' in d

    def test_portfolio_unique_name(self, temp_db):
        """No permite nombres duplicados."""
        p1 = Portfolio(name='Único')
        temp_db.session.add(p1)
        temp_db.session.commit()

        p2 = Portfolio(name='Único')
        temp_db.session.add(p2)

        with pytest.raises(Exception):  # IntegrityError
            temp_db.session.commit()

    def test_portfolio_repr(self, temp_db):
        """__repr__ muestra información útil."""
        portfolio = Portfolio(name='Repr Test')
        temp_db.session.add(portfolio)
        temp_db.session.commit()

        repr_str = repr(portfolio)
        assert 'Portfolio' in repr_str
        assert 'Repr Test' in repr_str


class TestTransactionPortfolioId:
    """Tests para portfolio_id en Transaction."""

    def test_transaction_has_portfolio_id_field(self, temp_db):
        """Transaction tiene campo portfolio_id."""
        trans = Transaction(
            date=datetime.now().date(),
            type='buy',
            ticker='TEST',
            quantity=100,
            price=10.0
        )
        assert hasattr(trans, 'portfolio_id')

    def test_transaction_portfolio_id_nullable(self, temp_db):
        """portfolio_id es nullable (compatibilidad local)."""
        trans_id = temp_db.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEST',
            'quantity': 100,
            'price': 10.0
            # Sin portfolio_id
        })

        trans = temp_db.get_transaction_by_id(trans_id)
        assert trans is not None
        assert trans.portfolio_id is None

    def test_transaction_with_portfolio_id(self, temp_db):
        """Puede crear transacción con portfolio_id."""
        # Crear portfolio primero
        portfolio = Portfolio(name='Test Portfolio')
        temp_db.session.add(portfolio)
        temp_db.session.commit()

        trans_id = temp_db.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEST',
            'quantity': 100,
            'price': 10.0,
            'portfolio_id': portfolio.id
        })

        trans = temp_db.get_transaction_by_id(trans_id)
        assert trans.portfolio_id == portfolio.id

    def test_transaction_to_dict_includes_portfolio_id(self, temp_db):
        """to_dict() incluye portfolio_id."""
        trans_id = temp_db.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEST',
            'quantity': 100,
            'price': 10.0,
            'portfolio_id': 123
        })

        trans = temp_db.get_transaction_by_id(trans_id)
        d = trans.to_dict()
        assert 'portfolio_id' in d
        assert d['portfolio_id'] == 123


class TestDividendPortfolioId:
    """Tests para portfolio_id en Dividend."""

    def test_dividend_has_portfolio_id_field(self, temp_db):
        """Dividend tiene campo portfolio_id."""
        div = Dividend(
            ticker='TEST',
            date=datetime.now().date(),
            gross_amount=100.0,
            net_amount=81.0
        )
        assert hasattr(div, 'portfolio_id')

    def test_dividend_portfolio_id_nullable(self, temp_db):
        """portfolio_id es nullable (compatibilidad local)."""
        div_id = temp_db.add_dividend({
            'ticker': 'TEST',
            'date': '2024-06-15',
            'gross_amount': 100.0,
            'net_amount': 81.0
            # Sin portfolio_id
        })

        div = temp_db.get_dividend_by_id(div_id)
        assert div is not None
        assert div.portfolio_id is None

    def test_dividend_with_portfolio_id(self, temp_db):
        """Puede crear dividendo con portfolio_id."""
        # Crear portfolio primero
        portfolio = Portfolio(name='Dividend Portfolio')
        temp_db.session.add(portfolio)
        temp_db.session.commit()

        div_id = temp_db.add_dividend({
            'ticker': 'TEST',
            'date': '2024-06-15',
            'gross_amount': 100.0,
            'net_amount': 81.0,
            'portfolio_id': portfolio.id
        })

        div = temp_db.get_dividend_by_id(div_id)
        assert div.portfolio_id == portfolio.id

    def test_dividend_to_dict_includes_portfolio_id(self, temp_db):
        """to_dict() incluye portfolio_id."""
        div_id = temp_db.add_dividend({
            'ticker': 'TEST',
            'date': '2024-06-15',
            'gross_amount': 100.0,
            'net_amount': 81.0,
            'portfolio_id': 456
        })

        div = temp_db.get_dividend_by_id(div_id)
        d = div.to_dict()
        assert 'portfolio_id' in d
        assert d['portfolio_id'] == 456


class TestMigrationScript:
    """Tests para verificar que la migración funciona."""

    def test_migration_check_runs(self, temp_db):
        """El script de verificación de migración funciona."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_003",
            "src/data/migrations/003_add_portfolio_support.py"
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        # No debería lanzar excepciones
        migration.check_migration(str(temp_db.db_path))

    def test_migration_is_idempotent(self, temp_db):
        """La migración es idempotente (se puede ejecutar múltiples veces)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_003",
            "src/data/migrations/003_add_portfolio_support.py"
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        # Primera ejecución
        result1 = migration.run_migration(str(temp_db.db_path))
        assert result1 is True

        # Segunda ejecución (debería ser no-op)
        result2 = migration.run_migration(str(temp_db.db_path))
        assert result2 is True
