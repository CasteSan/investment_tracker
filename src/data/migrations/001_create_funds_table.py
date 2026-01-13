"""
Migracion 001: Crear tabla funds

Crea la tabla para el catalogo de fondos de inversion.

Ejecutar:
    python -m src.data.migrations.001_create_funds_table

O desde la raiz del proyecto:
    python src/data/migrations/001_create_funds_table.py
"""

import sys
from pathlib import Path

# Agregar raiz del proyecto al path
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import inspect
from src.data.database import Database, Base
from src.data.models import Fund


def check_table_exists(engine, table_name: str) -> bool:
    """Verifica si una tabla existe en la BD."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def run_migration():
    """Ejecuta la migracion para crear la tabla funds."""
    print("=" * 60)
    print("Migracion 001: Crear tabla funds")
    print("=" * 60)

    # Conectar a la BD
    db = Database()
    engine = db.engine

    try:
        # Verificar si la tabla ya existe
        if check_table_exists(engine, 'funds'):
            print("La tabla 'funds' ya existe. Saltando creacion.")
            print("Si deseas recrearla, elimina la tabla manualmente primero.")
            return False

        # Crear la tabla
        print("Creando tabla 'funds'...")
        Fund.__table__.create(engine)

        # Verificar creacion
        if check_table_exists(engine, 'funds'):
            print("Tabla 'funds' creada exitosamente!")

            # Mostrar columnas creadas
            inspector = inspect(engine)
            columns = inspector.get_columns('funds')
            print(f"\nColumnas creadas ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"  - {col['name']}: {col['type']} {nullable}")

            return True
        else:
            print("ERROR: No se pudo verificar la creacion de la tabla")
            return False

    except Exception as e:
        print(f"ERROR durante la migracion: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def rollback_migration():
    """Deshace la migracion (elimina la tabla funds)."""
    print("=" * 60)
    print("Rollback: Eliminar tabla funds")
    print("=" * 60)

    db = Database()
    engine = db.engine

    try:
        if not check_table_exists(engine, 'funds'):
            print("La tabla 'funds' no existe. Nada que eliminar.")
            return False

        print("Eliminando tabla 'funds'...")
        Fund.__table__.drop(engine)

        if not check_table_exists(engine, 'funds'):
            print("Tabla 'funds' eliminada exitosamente!")
            return True
        else:
            print("ERROR: No se pudo eliminar la tabla")
            return False

    except Exception as e:
        print(f"ERROR durante rollback: {e}")
        return False

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migracion: crear tabla funds')
    parser.add_argument('--rollback', action='store_true', help='Deshacer migracion')
    args = parser.parse_args()

    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()

    sys.exit(0 if success else 1)
