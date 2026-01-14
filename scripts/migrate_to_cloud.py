#!/usr/bin/env python3
"""
Script de Migración: SQLite Local → PostgreSQL Cloud

Cloud Migration - Fase 4

Este script migra todos los datos de las bases de datos SQLite locales
(en data/portfolios/) a una base de datos PostgreSQL en la nube (Supabase).

Funcionalidades:
- Lee todos los archivos .db en data/portfolios/
- Crea un registro en 'portfolios' por cada archivo
- Migra transacciones y dividendos asignando portfolio_id
- Verifica integridad de datos
- Soporta modo dry-run para pruebas

Uso:
    # Ver ayuda
    python scripts/migrate_to_cloud.py --help

    # Modo dry-run (solo muestra qué haría)
    python scripts/migrate_to_cloud.py --dry-run

    # Ejecutar migración real
    python scripts/migrate_to_cloud.py --execute

    # Especificar DATABASE_URL
    python scripts/migrate_to_cloud.py --execute --database-url "postgresql://..."

Requisitos:
    - DATABASE_URL configurada (entorno o parámetro)
    - Archivos .db en data/portfolios/
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Agregar raíz del proyecto al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.data.database import (
    Base,
    Transaction,
    Dividend,
    BenchmarkData,
    PortfolioSnapshot,
    AssetPrice,
)
from src.data.models import Portfolio


class MigrationReport:
    """Reporte de migración."""

    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.portfolios_created = 0
        self.transactions_migrated = 0
        self.dividends_migrated = 0
        self.errors = []
        self.warnings = []
        self.details = []

    def add_error(self, message: str):
        self.errors.append(message)
        print(f"  ERROR: {message}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"  WARNING: {message}")

    def add_detail(self, message: str):
        self.details.append(message)
        print(f"  {message}")

    def finish(self):
        self.end_time = datetime.now()

    def print_summary(self):
        duration = (self.end_time - self.start_time).total_seconds()
        print("\n" + "=" * 60)
        print("RESUMEN DE MIGRACION")
        print("=" * 60)
        print(f"Duracion: {duration:.2f} segundos")
        print(f"Portfolios creados: {self.portfolios_created}")
        print(f"Transacciones migradas: {self.transactions_migrated}")
        print(f"Dividendos migrados: {self.dividends_migrated}")
        print(f"Errores: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print("\nErrores:")
            for err in self.errors:
                print(f"  - {err}")

        if self.warnings:
            print("\nWarnings:")
            for warn in self.warnings:
                print(f"  - {warn}")

        print("=" * 60)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


def get_sqlite_databases(portfolios_dir: Path) -> List[Path]:
    """Obtiene lista de archivos SQLite en el directorio de portfolios."""
    if not portfolios_dir.exists():
        return []
    return sorted(portfolios_dir.glob("*.db"))


def read_sqlite_data(db_path: Path) -> Dict:
    """
    Lee todos los datos de un archivo SQLite.

    Usa SQL raw para ser compatible con BDs antiguas que no tienen
    el campo portfolio_id.

    Returns:
        Dict con 'transactions', 'dividends', etc.
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    data = {
        'transactions': [],
        'dividends': [],
        'benchmarks': [],
        'snapshots': [],
        'asset_prices': [],
    }

    with engine.connect() as conn:
        # Leer transacciones (sin portfolio_id)
        try:
            result = conn.execute(text("""
                SELECT date, type, ticker, name, asset_type, quantity, price,
                       commission, total, currency, market, realized_gain_eur,
                       unrealized_gain_eur, cost_basis_eur, transfer_link_id, notes
                FROM transactions
            """))
            for row in result:
                data['transactions'].append({
                    'date': row[0],
                    'type': row[1],
                    'ticker': row[2],
                    'name': row[3],
                    'asset_type': row[4],
                    'quantity': row[5],
                    'price': row[6],
                    'commission': row[7],
                    'total': row[8],
                    'currency': row[9],
                    'market': row[10],
                    'realized_gain_eur': row[11],
                    'unrealized_gain_eur': row[12],
                    'cost_basis_eur': row[13],
                    'transfer_link_id': row[14],
                    'notes': row[15],
                })
        except Exception as e:
            # Tabla puede no existir o tener estructura diferente
            pass

        # Leer dividendos (sin portfolio_id)
        try:
            result = conn.execute(text("""
                SELECT ticker, name, date, gross_amount, net_amount,
                       withholding_tax, currency, notes
                FROM dividends
            """))
            for row in result:
                data['dividends'].append({
                    'ticker': row[0],
                    'name': row[1],
                    'date': row[2],
                    'gross_amount': row[3],
                    'net_amount': row[4],
                    'withholding_tax': row[5],
                    'currency': row[6],
                    'notes': row[7],
                })
        except Exception:
            pass

        # Leer benchmarks (opcional)
        try:
            result = conn.execute(text("""
                SELECT benchmark_name, date, value FROM benchmark_data
            """))
            for row in result:
                data['benchmarks'].append({
                    'benchmark_name': row[0],
                    'date': row[1],
                    'value': row[2],
                })
        except Exception:
            pass

        # Leer snapshots (opcional)
        try:
            result = conn.execute(text("""
                SELECT date, total_value, total_cost, unrealized_gain, notes
                FROM portfolio_snapshots
            """))
            for row in result:
                data['snapshots'].append({
                    'date': row[0],
                    'total_value': row[1],
                    'total_cost': row[2],
                    'unrealized_gain': row[3],
                    'notes': row[4],
                })
        except Exception:
            pass

        # Leer precios de activos (opcional)
        try:
            result = conn.execute(text("""
                SELECT ticker, date, close_price, adj_close_price
                FROM asset_prices
            """))
            for row in result:
                data['asset_prices'].append({
                    'ticker': row[0],
                    'date': row[1],
                    'close_price': row[2],
                    'adj_close_price': row[3],
                })
        except Exception:
            pass

    return data


def create_postgres_portfolio(session, name: str, description: str = None) -> int:
    """
    Crea un portfolio en PostgreSQL y retorna su ID.
    """
    portfolio = Portfolio(name=name, description=description)
    session.add(portfolio)
    session.flush()  # Para obtener el ID
    return portfolio.id


def migrate_transactions(session, transactions: List[Dict], portfolio_id: int) -> int:
    """Migra transacciones a PostgreSQL."""
    count = 0
    for t_data in transactions:
        t_data['portfolio_id'] = portfolio_id
        transaction = Transaction(**t_data)
        session.add(transaction)
        count += 1
    return count


def migrate_dividends(session, dividends: List[Dict], portfolio_id: int) -> int:
    """Migra dividendos a PostgreSQL."""
    count = 0
    for d_data in dividends:
        d_data['portfolio_id'] = portfolio_id
        dividend = Dividend(**d_data)
        session.add(dividend)
        count += 1
    return count


def verify_migration(
    pg_session,
    portfolio_id: int,
    expected_transactions: int,
    expected_dividends: int
) -> Tuple[bool, str]:
    """
    Verifica que la migración fue correcta.

    Returns:
        Tuple (success, message)
    """
    actual_trans = pg_session.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id
    ).count()

    actual_divs = pg_session.query(Dividend).filter(
        Dividend.portfolio_id == portfolio_id
    ).count()

    if actual_trans != expected_transactions:
        return False, f"Transacciones: esperadas {expected_transactions}, encontradas {actual_trans}"

    if actual_divs != expected_dividends:
        return False, f"Dividendos: esperados {expected_dividends}, encontrados {actual_divs}"

    return True, "OK"


def run_migration(
    database_url: str,
    portfolios_dir: Path,
    dry_run: bool = True
) -> MigrationReport:
    """
    Ejecuta la migración de SQLite a PostgreSQL.

    Args:
        database_url: URL de conexión PostgreSQL
        portfolios_dir: Directorio con archivos .db
        dry_run: Si es True, no hace cambios reales

    Returns:
        MigrationReport con resultados
    """
    report = MigrationReport()

    print("=" * 60)
    print("MIGRACION SQLite -> PostgreSQL")
    print("=" * 60)
    print(f"Modo: {'DRY-RUN (sin cambios)' if dry_run else 'EJECUCION REAL'}")
    print(f"Directorio: {portfolios_dir}")
    print()

    # Buscar archivos SQLite
    sqlite_files = get_sqlite_databases(portfolios_dir)

    if not sqlite_files:
        report.add_error(f"No se encontraron archivos .db en {portfolios_dir}")
        report.finish()
        return report

    print(f"Archivos SQLite encontrados: {len(sqlite_files)}")
    for f in sqlite_files:
        print(f"  - {f.name}")
    print()

    # Conectar a PostgreSQL
    if not dry_run:
        try:
            pg_engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True
            )
            # Crear tablas si no existen
            Base.metadata.create_all(pg_engine)
            PgSession = sessionmaker(bind=pg_engine)
            pg_session = PgSession()
            print("Conexion a PostgreSQL establecida")
        except Exception as e:
            report.add_error(f"No se pudo conectar a PostgreSQL: {e}")
            report.finish()
            return report
    else:
        pg_session = None
        print("Modo dry-run: no se conectara a PostgreSQL")

    print()

    # Procesar cada archivo SQLite
    for sqlite_path in sqlite_files:
        portfolio_name = sqlite_path.stem
        print(f"Procesando: {portfolio_name}")

        # Leer datos del SQLite
        try:
            data = read_sqlite_data(sqlite_path)
            trans_count = len(data['transactions'])
            div_count = len(data['dividends'])
            report.add_detail(f"  Transacciones: {trans_count}")
            report.add_detail(f"  Dividendos: {div_count}")
        except Exception as e:
            report.add_error(f"Error leyendo {sqlite_path}: {e}")
            continue

        if dry_run:
            report.add_detail(f"  [DRY-RUN] Se crearia portfolio '{portfolio_name}'")
            report.add_detail(f"  [DRY-RUN] Se migrarian {trans_count} transacciones")
            report.add_detail(f"  [DRY-RUN] Se migrarian {div_count} dividendos")
            report.portfolios_created += 1
            report.transactions_migrated += trans_count
            report.dividends_migrated += div_count
        else:
            try:
                # Crear portfolio
                portfolio_id = create_postgres_portfolio(
                    pg_session,
                    name=portfolio_name,
                    description=f"Migrado desde {sqlite_path.name}"
                )
                report.add_detail(f"  Portfolio creado: ID={portfolio_id}")
                report.portfolios_created += 1

                # Migrar transacciones
                migrated_trans = migrate_transactions(
                    pg_session,
                    data['transactions'],
                    portfolio_id
                )
                report.transactions_migrated += migrated_trans

                # Migrar dividendos
                migrated_divs = migrate_dividends(
                    pg_session,
                    data['dividends'],
                    portfolio_id
                )
                report.dividends_migrated += migrated_divs

                # Commit parcial
                pg_session.commit()

                # Verificar
                success, msg = verify_migration(
                    pg_session,
                    portfolio_id,
                    trans_count,
                    div_count
                )
                if success:
                    report.add_detail(f"  Verificación: {msg}")
                else:
                    report.add_warning(f"  Verificación fallida: {msg}")

            except Exception as e:
                report.add_error(f"Error migrando {portfolio_name}: {e}")
                pg_session.rollback()
                continue

        print()

    # Cerrar conexión PostgreSQL
    if pg_session:
        pg_session.close()

    report.finish()
    report.print_summary()

    return report


def main():
    parser = argparse.ArgumentParser(
        description='Migrar datos de SQLite local a PostgreSQL cloud',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ver qué se migraría (sin cambios)
  python scripts/migrate_to_cloud.py --dry-run

  # Ejecutar migración real
  python scripts/migrate_to_cloud.py --execute

  # Con DATABASE_URL explícita
  python scripts/migrate_to_cloud.py --execute --database-url "postgresql://..."
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular migración sin hacer cambios'
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Ejecutar migración real (requiere DATABASE_URL)'
    )

    parser.add_argument(
        '--database-url',
        type=str,
        help='URL de PostgreSQL (o usar env DATABASE_URL)'
    )

    parser.add_argument(
        '--source',
        type=str,
        default=str(ROOT_DIR / 'data' / 'portfolios'),
        help='Directorio con archivos SQLite (default: data/portfolios/)'
    )

    args = parser.parse_args()

    # Validar argumentos
    if not args.dry_run and not args.execute:
        print("Error: Debe especificar --dry-run o --execute")
        parser.print_help()
        sys.exit(1)

    if args.dry_run and args.execute:
        print("Error: No puede usar --dry-run y --execute juntos")
        sys.exit(1)

    # Obtener DATABASE_URL
    database_url = args.database_url or os.getenv('DATABASE_URL')

    if args.execute and not database_url:
        print("Error: Se requiere DATABASE_URL para ejecutar la migración")
        print("Use --database-url o configure la variable de entorno DATABASE_URL")
        sys.exit(1)

    # Ejecutar migración
    portfolios_dir = Path(args.source)
    report = run_migration(
        database_url=database_url or "dry-run-no-url",
        portfolios_dir=portfolios_dir,
        dry_run=args.dry_run
    )

    # Exit code
    sys.exit(0 if report.success else 1)


if __name__ == '__main__':
    main()
