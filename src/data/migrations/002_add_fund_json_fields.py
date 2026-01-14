"""
Migracion 002: Anadir campos JSON y volatilidades a tabla funds

Anade los siguientes campos:
- volatility_1y, volatility_5y (Float)
- sharpe_1y, sharpe_5y (Float)
- top_holdings (Text/JSON)
- asset_allocation (Text/JSON)

Ejecutar:
    python -m src.data.migrations.002_add_fund_json_fields

O desde la raiz del proyecto:
    python src/data/migrations/002_add_fund_json_fields.py
"""

import sys
from pathlib import Path

# Agregar raiz del proyecto al path
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import inspect, text
from src.data.database import Database


# Campos a agregar (nombre, tipo SQL)
NEW_COLUMNS = [
    ('volatility_1y', 'FLOAT'),
    ('volatility_5y', 'FLOAT'),
    ('sharpe_1y', 'FLOAT'),
    ('sharpe_5y', 'FLOAT'),
    ('top_holdings', 'TEXT'),
    ('asset_allocation', 'TEXT'),
]


def get_existing_columns(engine) -> set:
    """Obtiene los nombres de columnas existentes en la tabla funds."""
    inspector = inspect(engine)
    if 'funds' not in inspector.get_table_names():
        return set()
    columns = inspector.get_columns('funds')
    return {col['name'] for col in columns}


def run_migration():
    """Ejecuta la migracion para anadir nuevos campos."""
    print("=" * 60)
    print("Migracion 002: Anadir campos JSON y volatilidades")
    print("=" * 60)

    db = Database()
    engine = db.engine

    try:
        # Verificar que la tabla existe
        existing = get_existing_columns(engine)
        if not existing:
            print("ERROR: La tabla 'funds' no existe.")
            print("Ejecuta primero: python -m src.data.migrations.001_create_funds_table")
            return False

        # Determinar que columnas faltan
        columns_to_add = [
            (name, sql_type)
            for name, sql_type in NEW_COLUMNS
            if name not in existing
        ]

        if not columns_to_add:
            print("Todos los campos ya existen. Nada que migrar.")
            return True

        print(f"\nCampos a anadir: {len(columns_to_add)}")
        for name, sql_type in columns_to_add:
            print(f"  - {name} ({sql_type})")

        # SQLite: ALTER TABLE ADD COLUMN (una a una)
        print("\nEjecutando ALTER TABLE...")
        with engine.connect() as conn:
            for name, sql_type in columns_to_add:
                sql = f"ALTER TABLE funds ADD COLUMN {name} {sql_type}"
                print(f"  {sql}")
                conn.execute(text(sql))
            conn.commit()

        # Verificar
        new_existing = get_existing_columns(engine)
        added = [name for name, _ in columns_to_add if name in new_existing]

        print(f"\nCampos anadidos exitosamente: {len(added)}")
        for name in added:
            print(f"  - {name}")

        return len(added) == len(columns_to_add)

    except Exception as e:
        print(f"ERROR durante la migracion: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def check_migration():
    """Verifica el estado de la migracion."""
    print("=" * 60)
    print("Verificando estado de migracion 002")
    print("=" * 60)

    db = Database()
    engine = db.engine

    try:
        existing = get_existing_columns(engine)

        if not existing:
            print("La tabla 'funds' no existe.")
            return

        print(f"\nColumnas existentes en 'funds': {len(existing)}")

        # Verificar campos nuevos
        print("\nEstado de campos nuevos:")
        for name, sql_type in NEW_COLUMNS:
            status = "OK" if name in existing else "FALTA"
            print(f"  [{status}] {name}")

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Migracion: anadir campos JSON a funds'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo verificar estado, no migrar'
    )
    args = parser.parse_args()

    if args.check:
        check_migration()
    else:
        success = run_migration()
        sys.exit(0 if success else 1)
