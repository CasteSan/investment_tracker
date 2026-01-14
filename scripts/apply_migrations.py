#!/usr/bin/env python
"""
Apply Migrations - Aplica migraciones pendientes a todas las bases de datos

Este script recorre todos los archivos .db en data/portfolios/ y aplica
las migraciones de esquema necesarias.

Uso:
    python scripts/apply_migrations.py           # Aplica a todas las BDs
    python scripts/apply_migrations.py --check   # Solo verifica estado
    python scripts/apply_migrations.py --db Principal.db  # BD especifica
"""

import sys
import sqlite3
from pathlib import Path

# Configurar path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Directorio de portfolios
PORTFOLIOS_DIR = ROOT_DIR / "data" / "portfolios"


# =============================================================================
# DEFINICION DE MIGRACIONES
# =============================================================================

# Columnas a verificar/añadir en la tabla funds
FUND_COLUMNS = [
    # Migración 002: campos de volatilidad y JSON
    ('volatility_1y', 'FLOAT'),
    ('volatility_3y', 'FLOAT'),
    ('volatility_5y', 'FLOAT'),
    ('sharpe_1y', 'FLOAT'),
    ('sharpe_3y', 'FLOAT'),
    ('sharpe_5y', 'FLOAT'),
    ('max_drawdown_3y', 'FLOAT'),
    ('top_holdings', 'TEXT'),
    ('asset_allocation', 'TEXT'),
    # Campos que podrían faltar en BDs antiguas
    ('benchmark_name', 'VARCHAR(200)'),
    ('benchmark_ticker', 'VARCHAR(50)'),
    # Migración 003: categoria personalizada
    ('custom_category', 'VARCHAR(50)'),
]


def get_existing_columns(conn: sqlite3.Connection, table: str) -> set:
    """Obtiene las columnas existentes de una tabla."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Verifica si una tabla existe."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def apply_fund_migrations(db_path: Path, dry_run: bool = False) -> dict:
    """
    Aplica migraciones a la tabla funds de una base de datos.

    Args:
        db_path: Ruta al archivo .db
        dry_run: Si True, solo reporta sin aplicar cambios

    Returns:
        dict con estadísticas de la migración
    """
    result = {
        'db': db_path.name,
        'table_exists': False,
        'columns_added': [],
        'columns_existing': [],
        'errors': []
    }

    try:
        conn = sqlite3.connect(str(db_path))

        # Verificar si la tabla funds existe
        if not table_exists(conn, 'funds'):
            result['table_exists'] = False
            conn.close()
            return result

        result['table_exists'] = True

        # Obtener columnas existentes
        existing = get_existing_columns(conn, 'funds')

        # Determinar columnas faltantes
        for col_name, col_type in FUND_COLUMNS:
            if col_name in existing:
                result['columns_existing'].append(col_name)
            else:
                if not dry_run:
                    try:
                        sql = f"ALTER TABLE funds ADD COLUMN {col_name} {col_type}"
                        conn.execute(sql)
                        conn.commit()
                        result['columns_added'].append(col_name)
                    except Exception as e:
                        result['errors'].append(f"{col_name}: {e}")
                else:
                    result['columns_added'].append(col_name)

        conn.close()

    except Exception as e:
        result['errors'].append(str(e))

    return result


def find_all_databases() -> list:
    """Encuentra todas las bases de datos de portfolios."""
    dbs = []

    # Buscar en data/portfolios/
    if PORTFOLIOS_DIR.exists():
        dbs.extend(PORTFOLIOS_DIR.glob("*.db"))

    # También incluir database.db en data/ si existe
    default_db = ROOT_DIR / "data" / "database.db"
    if default_db.exists():
        dbs.append(default_db)

    return sorted(dbs)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Aplica migraciones de esquema a bases de datos'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo verificar estado, no aplicar cambios'
    )
    parser.add_argument(
        '--db',
        type=str,
        help='Aplicar solo a una BD específica (nombre del archivo)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Apply Migrations - Fund Catalog Schema")
    print("=" * 60)
    print()

    # Encontrar bases de datos
    databases = find_all_databases()

    if not databases:
        print("No se encontraron bases de datos en:")
        print(f"  - {PORTFOLIOS_DIR}")
        print(f"  - {ROOT_DIR / 'data' / 'database.db'}")
        return 1

    # Filtrar por nombre si se especificó
    if args.db:
        databases = [db for db in databases if db.name == args.db]
        if not databases:
            print(f"No se encontró la base de datos: {args.db}")
            return 1

    print(f"Bases de datos encontradas: {len(databases)}")
    for db in databases:
        print(f"  - {db}")
    print()

    # Aplicar migraciones
    total_added = 0
    total_errors = 0

    for db_path in databases:
        print(f"Procesando: {db_path.name}")
        print("-" * 40)

        result = apply_fund_migrations(db_path, dry_run=args.check)

        if not result['table_exists']:
            print("  Tabla 'funds' no existe (saltando)")
            print()
            continue

        if result['columns_added']:
            action = "Por añadir" if args.check else "Añadidas"
            print(f"  {action}: {len(result['columns_added'])}")
            for col in result['columns_added']:
                print(f"    + {col}")
            total_added += len(result['columns_added'])

        if result['columns_existing']:
            print(f"  Ya existen: {len(result['columns_existing'])}")

        if result['errors']:
            print(f"  Errores: {len(result['errors'])}")
            for err in result['errors']:
                print(f"    ! {err}")
            total_errors += len(result['errors'])

        print()

    # Resumen
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Bases de datos procesadas: {len(databases)}")
    if args.check:
        print(f"Columnas pendientes: {total_added}")
    else:
        print(f"Columnas añadidas: {total_added}")
    print(f"Errores: {total_errors}")

    if args.check and total_added > 0:
        print()
        print("Ejecuta sin --check para aplicar los cambios.")

    return 0 if total_errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
