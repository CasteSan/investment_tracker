"""
Migracion 003: Soporte para Cloud Multi-Tenant (Portfolios)

Cloud Migration - Fase 2

Esta migración añade:
1. Tabla 'portfolios' para gestión de carteras en cloud
2. Campo 'portfolio_id' a tabla 'transactions'
3. Campo 'portfolio_id' a tabla 'dividends'
4. Índices para optimizar queries filtradas por portfolio

Los campos son nullable para mantener compatibilidad con modo local.

Ejecutar:
    python -m src.data.migrations.003_add_portfolio_support

O con el script general:
    python scripts/apply_migrations.py
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import inspect, text
from src.data.database import Database


# Definición de la tabla portfolios
PORTFOLIOS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

# Campos a agregar a tablas existentes
NEW_COLUMNS = {
    'transactions': [
        ('portfolio_id', 'INTEGER'),
    ],
    'dividends': [
        ('portfolio_id', 'INTEGER'),
    ],
}

# Índices a crear
NEW_INDEXES = [
    ('ix_transactions_portfolio_id', 'transactions', 'portfolio_id'),
    ('ix_dividends_portfolio_id', 'dividends', 'portfolio_id'),
]


def get_existing_tables(engine) -> set:
    """Obtiene los nombres de tablas existentes."""
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def get_existing_columns(engine, table_name: str) -> set:
    """Obtiene los nombres de columnas existentes en una tabla."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}


def get_existing_indexes(engine, table_name: str) -> set:
    """Obtiene los nombres de índices existentes en una tabla."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    indexes = inspector.get_indexes(table_name)
    return {idx['name'] for idx in indexes if idx['name']}


def run_migration(db_path: str = None):
    """
    Ejecuta la migración para añadir soporte de portfolios.

    Args:
        db_path: Ruta a la base de datos. Si es None, usa la por defecto.
    """
    print("=" * 60)
    print("Migración 003: Soporte para Cloud Multi-Tenant (Portfolios)")
    print("=" * 60)

    db = Database(db_path=db_path) if db_path else Database()
    engine = db.engine

    try:
        existing_tables = get_existing_tables(engine)
        changes_made = []

        # 1. Crear tabla portfolios si no existe
        print("\n1. Verificando tabla 'portfolios'...")
        if 'portfolios' not in existing_tables:
            print("   Creando tabla 'portfolios'...")
            with engine.connect() as conn:
                conn.execute(text(PORTFOLIOS_TABLE_SQL))
                conn.commit()
            changes_made.append("Tabla 'portfolios' creada")
            print("   OK - Tabla creada")
        else:
            print("   OK - Tabla ya existe")

        # 2. Añadir columnas portfolio_id a transactions y dividends
        print("\n2. Añadiendo columnas portfolio_id...")
        for table_name, columns in NEW_COLUMNS.items():
            if table_name not in existing_tables:
                print(f"   SKIP - Tabla '{table_name}' no existe")
                continue

            existing_cols = get_existing_columns(engine, table_name)

            for col_name, col_type in columns:
                if col_name in existing_cols:
                    print(f"   OK - {table_name}.{col_name} ya existe")
                else:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    print(f"   Ejecutando: {sql}")
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    changes_made.append(f"Columna {table_name}.{col_name} añadida")

        # 3. Crear índices
        print("\n3. Creando índices...")
        for idx_name, table_name, col_name in NEW_INDEXES:
            if table_name not in existing_tables:
                print(f"   SKIP - Tabla '{table_name}' no existe")
                continue

            existing_idx = get_existing_indexes(engine, table_name)
            if idx_name in existing_idx:
                print(f"   OK - Índice {idx_name} ya existe")
            else:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({col_name})"
                print(f"   Ejecutando: {sql}")
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                changes_made.append(f"Índice {idx_name} creado")

        # Resumen
        print("\n" + "=" * 60)
        if changes_made:
            print(f"Migración completada. Cambios realizados: {len(changes_made)}")
            for change in changes_made:
                print(f"  - {change}")
        else:
            print("Migración completada. No se requirieron cambios.")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nERROR durante la migración: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def check_migration(db_path: str = None):
    """Verifica el estado de la migración."""
    print("=" * 60)
    print("Verificando estado de migración 003 (Portfolios)")
    print("=" * 60)

    db = Database(db_path=db_path) if db_path else Database()
    engine = db.engine

    try:
        existing_tables = get_existing_tables(engine)

        # Verificar tabla portfolios
        print("\n1. Tabla 'portfolios':")
        if 'portfolios' in existing_tables:
            cols = get_existing_columns(engine, 'portfolios')
            print(f"   [OK] Existe con {len(cols)} columnas")
        else:
            print("   [FALTA] Tabla no existe")

        # Verificar columnas portfolio_id
        print("\n2. Columnas portfolio_id:")
        for table_name in ['transactions', 'dividends']:
            if table_name not in existing_tables:
                print(f"   [{table_name}] Tabla no existe")
                continue

            cols = get_existing_columns(engine, table_name)
            status = "OK" if 'portfolio_id' in cols else "FALTA"
            print(f"   [{status}] {table_name}.portfolio_id")

        # Verificar índices
        print("\n3. Índices:")
        for idx_name, table_name, _ in NEW_INDEXES:
            if table_name not in existing_tables:
                continue
            existing_idx = get_existing_indexes(engine, table_name)
            status = "OK" if idx_name in existing_idx else "FALTA"
            print(f"   [{status}] {idx_name}")

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Migración: añadir soporte para portfolios (cloud multi-tenant)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo verificar estado, no migrar'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='Ruta a la base de datos (opcional)'
    )
    args = parser.parse_args()

    if args.check:
        check_migration(args.db_path)
    else:
        success = run_migration(args.db_path)
        sys.exit(0 if success else 1)
