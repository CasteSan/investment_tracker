"""
Database Module - Gestión de Base de Datos SQLite
Sesión 1 del Investment Tracker (Actualizado v3 - Soporte Dividendos Completo)

CAMBIOS v2:
- Añadido campo 'currency' para divisa de la transacción
- Añadido campo 'market' para mercado de origen
- Añadido campo 'realized_gain_eur' para ventas (B/P ya en EUR)
- Añadido campo 'unrealized_gain_eur' para posiciones abiertas

CAMBIOS v3:
- Añadido método get_dividend_by_id()
- Añadido método update_dividend()
- Soporte completo para módulo dividends.py

CAMBIOS v4 (Refactor Escalabilidad):
- Movido a src/data/database.py
- Archivo de compatibilidad en src/database.py mantiene imports existentes

CAMBIOS v5 (Cloud Migration - Fase 2):
- Añadido campo portfolio_id a Transaction y Dividend
- Soporte para multi-tenant en modo cloud
- portfolio_id es nullable para compatibilidad local

Este módulo gestiona toda la interacción con la base de datos SQLite.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Importar logger
try:
    from src.logger import get_logger
except ImportError:
    try:
        from ..logger import get_logger
    except ImportError:
        from logger import get_logger

logger = get_logger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Ruta por defecto de la base de datos (ajustada para nueva ubicación)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'database.db'


# =============================================================================
# MODELOS DE DATOS
# =============================================================================

class Transaction(Base):
    """
    Modelo de transacciones financieras.

    Campos nuevos para soporte multi-divisa:
    - currency: Divisa de la transacción (EUR, USD, GBX, CAD, etc.)
    - market: Mercado de origen (BME, NYSE, LON, etc.)
    - realized_gain_eur: Para ventas, el B/P ya convertido a EUR
    - unrealized_gain_eur: Para posiciones abiertas, B/P latente en EUR

    Campo para traspasos:
    - cost_basis_eur: Para transfer_in, el coste fiscal heredado del fondo origen
    - transfer_link_id: ID de la transacción vinculada (transfer_out <-> transfer_in)

    Campo para cloud multi-tenant:
    - portfolio_id: ID del portfolio (nullable para compatibilidad local)
    """
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    type = Column(String(20), nullable=False)  # buy, sell, transfer_in, transfer_out
    ticker = Column(String(50), nullable=False)
    name = Column(String(200))
    asset_type = Column(String(20))  # accion, fondo, etf
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # Precio en divisa original
    commission = Column(Float, default=0.0)
    total = Column(Float)  # Calculado en divisa original

    # CAMPOS para multi-divisa
    currency = Column(String(10), default='EUR')  # EUR, USD, GBX, CAD, GBP
    market = Column(String(20))  # BME, NYSE, NASDAQ, LON, etc.
    realized_gain_eur = Column(Float)  # B/P de venta YA en EUR (del CSV)
    unrealized_gain_eur = Column(Float)  # B/P latente YA en EUR (del CSV)

    # CAMPOS para traspasos (fiscalidad española)
    cost_basis_eur = Column(Float)  # Coste fiscal heredado (para transfer_in)
    transfer_link_id = Column(Integer)  # ID de la transacción vinculada

    # CAMPO para cloud multi-tenant (nullable para compatibilidad local)
    portfolio_id = Column(Integer, nullable=True, index=True)

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Transaction(id={self.id}, {self.type} {self.quantity} {self.ticker} @ {self.price} {self.currency})>"

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'type': self.type,
            'ticker': self.ticker,
            'name': self.name,
            'asset_type': self.asset_type,
            'quantity': self.quantity,
            'price': self.price,
            'commission': self.commission,
            'total': self.total,
            'currency': self.currency,
            'market': self.market,
            'realized_gain_eur': self.realized_gain_eur,
            'unrealized_gain_eur': self.unrealized_gain_eur,
            'cost_basis_eur': self.cost_basis_eur,
            'transfer_link_id': self.transfer_link_id,
            'portfolio_id': self.portfolio_id,
            'notes': self.notes
        }


class Dividend(Base):
    """
    Modelo de dividendos recibidos.

    Campo para cloud multi-tenant:
    - portfolio_id: ID del portfolio (nullable para compatibilidad local)
    """
    __tablename__ = 'dividends'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(50), nullable=False)
    name = Column(String(200))  # nombre del activo
    date = Column(Date, nullable=False)
    gross_amount = Column(Float, nullable=False)
    net_amount = Column(Float, nullable=False)
    withholding_tax = Column(Float)  # Calculado: gross - net
    currency = Column(String(10), default='EUR')
    notes = Column(Text)

    # CAMPO para cloud multi-tenant (nullable para compatibilidad local)
    portfolio_id = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Dividend(id={self.id}, {self.ticker} {self.net_amount}€)>"

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'name': self.name,
            'date': self.date.isoformat() if self.date else None,
            'gross_amount': self.gross_amount,
            'net_amount': self.net_amount,
            'withholding_tax': self.withholding_tax,
            'currency': self.currency,
            'portfolio_id': self.portfolio_id,
            'notes': self.notes
        }


class BenchmarkData(Base):
    """Modelo de datos de índices de referencia"""
    __tablename__ = 'benchmark_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    benchmark_name = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)

    def __repr__(self):
        return f"<BenchmarkData({self.benchmark_name} {self.date}: {self.value})>"


class PortfolioSnapshot(Base):
    """Snapshots del valor de la cartera"""
    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    total_value = Column(Float, nullable=False)
    total_cost = Column(Float)
    unrealized_gain = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class AssetPrice(Base):
    """
    Precios históricos de activos de la cartera.

    Almacena precios descargados de Yahoo Finance para calcular
    el valor de mercado real de la cartera.
    """
    __tablename__ = 'asset_prices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    adj_close_price = Column(Float)  # Precio ajustado por dividendos/splits

    def __repr__(self):
        return f"<AssetPrice({self.ticker} {self.date}: {self.close_price})>"

    def to_dict(self):
        return {
            'ticker': self.ticker,
            'date': self.date.isoformat() if self.date else None,
            'close_price': self.close_price,
            'adj_close_price': self.adj_close_price
        }


# =============================================================================
# CLASE DATABASE
# =============================================================================

class Database:
    """
    Clase principal para gestión de la base de datos.

    Uso:
        db = Database()

        # Añadir transacción
        db.add_transaction({
            'date': '2024-01-15',
            'type': 'buy',
            'ticker': 'TEF',
            'name': 'Telefónica',
            'quantity': 100,
            'price': 4.20,
            'currency': 'EUR',
            'market': 'BME'
        })

        # Añadir venta con B/P en EUR
        db.add_transaction({
            'date': '2024-06-15',
            'type': 'sell',
            'ticker': 'TLW.L',
            'name': 'Tullow Oil',
            'quantity': 2300,
            'price': 10.10,  # En GBX (peniques)
            'currency': 'GBX',
            'market': 'LON',
            'realized_gain_eur': -143.28  # B/P REAL en EUR
        })

        db.close()
    """

    def __init__(self, db_path: str = None):
        """
        Inicializa la conexión a la base de datos.

        Args:
            db_path: Ruta al archivo de base de datos. Si es None, usa la ruta por defecto.
        """
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self.db_path = Path(db_path)

        # Crear directorio si no existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Crear engine y sesión
        logger.debug(f"Conectando a base de datos: {self.db_path}")
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        logger.info(f"Base de datos inicializada: {self.db_path.name}")

    def close(self):
        """Cierra la conexión a la base de datos"""
        self.session.close()
        logger.debug("Conexión a base de datos cerrada")

    # =========================================================================
    # TRANSACCIONES
    # =========================================================================

    def add_transaction(self, transaction_data: Dict) -> int:
        """
        Añade una nueva transacción.

        Args:
            transaction_data: Dict con los datos de la transacción.
                Campos requeridos: date, type, ticker, quantity, price
                Campos opcionales: name, asset_type, commission, currency, market,
                                   realized_gain_eur, unrealized_gain_eur, notes,
                                   cost_basis_eur (para traspasos),
                                   transfer_link_id (para vincular traspasos)

        Returns:
            ID de la transacción creada
        """
        logger.debug(f"Añadiendo transacción: {transaction_data.get('type')} {transaction_data.get('ticker')}")

        # Convertir fecha si es string
        if isinstance(transaction_data.get('date'), str):
            transaction_data['date'] = datetime.strptime(transaction_data['date'], '%Y-%m-%d').date()

        # Calcular total si no está especificado
        if 'total' not in transaction_data:
            qty = transaction_data.get('quantity', 0)
            price = transaction_data.get('price', 0)
            commission = transaction_data.get('commission', 0)

            if transaction_data.get('type') in ['buy', 'transfer_in']:
                transaction_data['total'] = qty * price + commission
            else:
                transaction_data['total'] = qty * price - commission

        # Valores por defecto
        if 'currency' not in transaction_data:
            transaction_data['currency'] = 'EUR'

        transaction = Transaction(**transaction_data)
        self.session.add(transaction)
        self.session.commit()

        logger.info(f"Transacción añadida: ID={transaction.id}, {transaction.type} {transaction.quantity} {transaction.ticker} @ {transaction.price}")
        return transaction.id

    def get_transactions(self,
                        ticker: str = None,
                        type: str = None,
                        asset_type: str = None,
                        currency: str = None,
                        market: str = None,
                        start_date: str = None,
                        end_date: str = None,
                        year: int = None,
                        limit: int = None,
                        order: str = 'ASC') -> List[Transaction]:
        """
        Obtiene transacciones con filtros opcionales.

        Args:
            ticker: Filtrar por ticker
            type: Filtrar por tipo (buy, sell, transfer_in, transfer_out)
            asset_type: Filtrar por tipo de activo
            currency: Filtrar por divisa
            market: Filtrar por mercado
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            year: Filtrar por año
            limit: Número máximo de resultados
            order: 'ASC' o 'DESC' por fecha

        Returns:
            Lista de objetos Transaction
        """
        query = self.session.query(Transaction)

        if ticker:
            query = query.filter(Transaction.ticker == ticker)

        if type:
            query = query.filter(Transaction.type == type)

        if asset_type:
            query = query.filter(Transaction.asset_type == asset_type)

        if currency:
            query = query.filter(Transaction.currency == currency)

        if market:
            query = query.filter(Transaction.market == market)

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date <= end_date)

        if year:
            from sqlalchemy import extract
            query = query.filter(extract('year', Transaction.date) == year)

        # Ordenar
        if order.upper() == 'DESC':
            query = query.order_by(Transaction.date.desc())
        else:
            query = query.order_by(Transaction.date.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Obtiene una transaccion por su ID.

        Args:
            transaction_id: ID de la transaccion

        Returns:
            Transaction o None si no existe
        """
        return self.session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

    def update_transaction(self, transaction_id: int, new_data: Dict) -> bool:
        """Actualiza una transacción existente"""
        transaction = self.session.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not transaction:
            return False

        for key, value in new_data.items():
            if hasattr(transaction, key):
                if key == 'date' and isinstance(value, str):
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                setattr(transaction, key, value)

        self.session.commit()
        return True

    def delete_transaction(self, transaction_id: int) -> bool:
        """Elimina una transacción"""
        transaction = self.session.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not transaction:
            return False

        self.session.delete(transaction)
        self.session.commit()
        return True

    def transactions_to_dataframe(self, transactions: List[Transaction] = None) -> pd.DataFrame:
        """
        Convierte lista de transacciones a DataFrame de pandas.

        Args:
            transactions: Lista de transacciones. Si es None, obtiene todas.

        Returns:
            DataFrame con las transacciones
        """
        if transactions is None:
            transactions = self.get_transactions()

        if not transactions:
            return pd.DataFrame()

        data = [t.to_dict() for t in transactions]
        df = pd.DataFrame(data)

        # Convertir fecha
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        return df

    # =========================================================================
    # DIVIDENDOS
    # =========================================================================

    def add_dividend(self, dividend_data: Dict) -> int:
        """
        Añade un nuevo dividendo.

        Args:
            dividend_data: Dict con campos del dividendo
                - ticker (requerido)
                - date (requerido)
                - gross_amount (requerido)
                - net_amount (requerido)
                - name, currency, notes (opcionales)

        Returns:
            ID del dividendo creado
        """
        if isinstance(dividend_data.get('date'), str):
            dividend_data['date'] = datetime.strptime(dividend_data['date'], '%Y-%m-%d').date()

        # Calcular retención
        if 'withholding_tax' not in dividend_data:
            dividend_data['withholding_tax'] = dividend_data.get('gross_amount', 0) - dividend_data.get('net_amount', 0)

        dividend = Dividend(**dividend_data)
        self.session.add(dividend)
        self.session.commit()

        return dividend.id

    def get_dividend_by_id(self, dividend_id: int) -> Optional[Dividend]:
        """
        Obtiene un dividendo por su ID.

        Args:
            dividend_id: ID del dividendo

        Returns:
            Objeto Dividend o None si no existe
        """
        return self.session.query(Dividend).filter(Dividend.id == dividend_id).first()

    def get_dividends(self,
                     ticker: str = None,
                     year: int = None,
                     start_date: str = None,
                     end_date: str = None) -> List[Dividend]:
        """
        Obtiene dividendos con filtros opcionales.

        Args:
            ticker: Filtrar por ticker
            year: Filtrar por año
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)

        Returns:
            Lista de objetos Dividend
        """
        query = self.session.query(Dividend)

        if ticker:
            query = query.filter(Dividend.ticker == ticker.upper())

        if year:
            from sqlalchemy import extract
            query = query.filter(extract('year', Dividend.date) == year)

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Dividend.date >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Dividend.date <= end_date)

        return query.order_by(Dividend.date.desc()).all()

    def update_dividend(self, dividend_id: int, update_data: Dict) -> bool:
        """
        Actualiza un dividendo existente.

        Args:
            dividend_id: ID del dividendo
            update_data: Dict con campos a actualizar

        Returns:
            True si se actualizó correctamente, False si no existe
        """
        dividend = self.session.query(Dividend).filter(Dividend.id == dividend_id).first()

        if not dividend:
            return False

        for key, value in update_data.items():
            if hasattr(dividend, key):
                if key == 'date' and isinstance(value, str):
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                setattr(dividend, key, value)

        # Recalcular retención si se actualizan importes
        if 'gross_amount' in update_data or 'net_amount' in update_data:
            dividend.withholding_tax = dividend.gross_amount - dividend.net_amount

        self.session.commit()
        return True

    def delete_dividend(self, dividend_id: int) -> bool:
        """
        Elimina un dividendo.

        Args:
            dividend_id: ID del dividendo

        Returns:
            True si se eliminó, False si no existía
        """
        dividend = self.session.query(Dividend).filter(Dividend.id == dividend_id).first()

        if not dividend:
            return False

        self.session.delete(dividend)
        self.session.commit()
        return True

    # =========================================================================
    # BENCHMARKS
    # =========================================================================

    def add_benchmark_data(self, benchmark_name: str, date: str, value: float) -> int:
        """Añade datos de un índice de referencia"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        benchmark = BenchmarkData(
            benchmark_name=benchmark_name,
            date=date,
            value=value
        )
        self.session.add(benchmark)
        self.session.commit()

        return benchmark.id

    def get_benchmark_data(self,
                          benchmark_name: str,
                          start_date: str = None,
                          end_date: str = None) -> List[BenchmarkData]:
        """Obtiene datos de un índice"""
        query = self.session.query(BenchmarkData).filter(
            BenchmarkData.benchmark_name == benchmark_name
        )

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(BenchmarkData.date >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(BenchmarkData.date <= end_date)

        return query.order_by(BenchmarkData.date.asc()).all()

    def get_available_benchmarks(self) -> List[str]:
        """Retorna lista de benchmarks disponibles"""
        result = self.session.query(BenchmarkData.benchmark_name).distinct().all()
        return [r[0] for r in result]

    # =========================================================================
    # PRECIOS DE ACTIVOS
    # =========================================================================

    def add_asset_price(self,
                       ticker: str,
                       date: str,
                       close_price: float,
                       adj_close_price: float = None) -> int:
        """
        Añade un precio de un activo.

        Args:
            ticker: Símbolo del activo
            date: Fecha (YYYY-MM-DD)
            close_price: Precio de cierre
            adj_close_price: Precio ajustado (opcional)

        Returns:
            ID del registro creado
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        # Verificar si ya existe
        existing = self.session.query(AssetPrice).filter(
            AssetPrice.ticker == ticker,
            AssetPrice.date == date
        ).first()

        if existing:
            # Actualizar precio existente
            existing.close_price = close_price
            existing.adj_close_price = adj_close_price or close_price
            self.session.commit()
            return existing.id

        # Crear nuevo registro
        price = AssetPrice(
            ticker=ticker,
            date=date,
            close_price=close_price,
            adj_close_price=adj_close_price or close_price
        )
        self.session.add(price)
        self.session.commit()

        return price.id

    def get_asset_prices(self,
                        ticker: str,
                        start_date: str = None,
                        end_date: str = None) -> List[AssetPrice]:
        """
        Obtiene precios históricos de un activo.

        Args:
            ticker: Símbolo del activo
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)

        Returns:
            Lista de objetos AssetPrice ordenados por fecha
        """
        query = self.session.query(AssetPrice).filter(
            AssetPrice.ticker == ticker
        )

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(AssetPrice.date >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(AssetPrice.date <= end_date)

        return query.order_by(AssetPrice.date.asc()).all()

    def get_latest_price(self, ticker: str) -> Optional[float]:
        """Obtiene el precio más reciente de un activo"""
        price = self.session.query(AssetPrice).filter(
            AssetPrice.ticker == ticker
        ).order_by(AssetPrice.date.desc()).first()

        return price.adj_close_price if price else None

    def get_tickers_with_prices(self) -> List[str]:
        """Retorna lista de tickers con precios descargados"""
        result = self.session.query(AssetPrice.ticker).distinct().all()
        return [r[0] for r in result]

    def get_all_latest_prices(self) -> Dict[str, float]:
        """
        Obtiene el último precio de todos los tickers con datos.

        Returns:
            Dict con {ticker: ultimo_precio}
        """
        from sqlalchemy import func

        # Subquery para obtener la fecha más reciente de cada ticker
        subq = self.session.query(
            AssetPrice.ticker,
            func.max(AssetPrice.date).label('max_date')
        ).group_by(AssetPrice.ticker).subquery()

        # Query para obtener el precio de cada ticker en su fecha más reciente
        results = self.session.query(AssetPrice).join(
            subq,
            (AssetPrice.ticker == subq.c.ticker) &
            (AssetPrice.date == subq.c.max_date)
        ).all()

        return {r.ticker: r.adj_close_price or r.close_price for r in results}

    def delete_asset_prices(self, ticker: str = None):
        """
        Elimina precios de activos.

        Args:
            ticker: Si se especifica, solo elimina precios de ese ticker.
                   Si es None, elimina TODOS los precios.
        """
        if ticker:
            self.session.query(AssetPrice).filter(
                AssetPrice.ticker == ticker
            ).delete()
        else:
            self.session.query(AssetPrice).delete()

        self.session.commit()

    # =========================================================================
    # SNAPSHOTS
    # =========================================================================

    def add_portfolio_snapshot(self,
                              total_value: float,
                              total_cost: float = None,
                              date: str = None,
                              notes: str = None) -> int:
        """Guarda un snapshot del valor de la cartera"""
        if date is None:
            date = datetime.now().date()
        elif isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        unrealized_gain = total_value - total_cost if total_cost else None

        snapshot = PortfolioSnapshot(
            date=date,
            total_value=total_value,
            total_cost=total_cost,
            unrealized_gain=unrealized_gain,
            notes=notes
        )
        self.session.add(snapshot)
        self.session.commit()

        return snapshot.id

    def get_portfolio_snapshots(self,
                               start_date: str = None,
                               end_date: str = None) -> List[PortfolioSnapshot]:
        """Obtiene snapshots de la cartera"""
        query = self.session.query(PortfolioSnapshot)

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(PortfolioSnapshot.date >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(PortfolioSnapshot.date <= end_date)

        return query.order_by(PortfolioSnapshot.date.asc()).all()

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def get_database_stats(self) -> Dict:
        """Retorna estadísticas de la base de datos"""
        return {
            'total_transactions': self.session.query(Transaction).count(),
            'total_dividends': self.session.query(Dividend).count(),
            'total_benchmarks': self.session.query(BenchmarkData).count(),
            'total_snapshots': self.session.query(PortfolioSnapshot).count(),
            'unique_tickers': self.session.query(Transaction.ticker).distinct().count(),
            'db_path': str(self.db_path)
        }

    def get_all_tickers(self) -> List[str]:
        """Retorna lista de todos los tickers únicos"""
        result = self.session.query(Transaction.ticker).distinct().all()
        return [r[0] for r in result]

    def get_currencies_used(self) -> List[str]:
        """Retorna lista de divisas usadas en transacciones"""
        result = self.session.query(Transaction.currency).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_markets_used(self) -> List[str]:
        """Retorna lista de mercados usados"""
        result = self.session.query(Transaction.market).distinct().all()
        return [r[0] for r in result if r[0]]

    def clear_all_data(self, confirm: bool = False):
        """
        Elimina todos los datos de la base de datos.

        Args:
            confirm: Debe ser True para confirmar la eliminación
        """
        if not confirm:
            raise ValueError("Debes pasar confirm=True para eliminar todos los datos")

        self.session.query(Transaction).delete()
        self.session.query(Dividend).delete()
        self.session.query(BenchmarkData).delete()
        self.session.query(PortfolioSnapshot).delete()
        self.session.commit()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TEST DEL MODULO DATABASE v4 (Nueva ubicacion)")
    print("="*60)

    # Crear base de datos de prueba
    db = Database()

    print(f"\nBase de datos: {db.db_path}")

    # Test: Añadir transacción con divisa
    print("\nTest: Añadir transaccion EUR")
    trans_id1 = db.add_transaction({
        'date': '2024-01-15',
        'type': 'buy',
        'ticker': 'TEF',
        'name': 'Telefonica',
        'asset_type': 'accion',
        'quantity': 100,
        'price': 4.20,
        'currency': 'EUR',
        'market': 'BME'
    })
    print(f"   Transaccion EUR creada: ID {trans_id1}")

    # Test: Añadir transacción GBX (peniques)
    print("\nTest: Añadir venta GBX con realized_gain_eur")
    trans_id2 = db.add_transaction({
        'date': '2024-08-08',
        'type': 'sell',
        'ticker': 'TLW.L',
        'name': 'Tullow Oil',
        'asset_type': 'accion',
        'quantity': 2300,
        'price': 10.10,  # En peniques
        'currency': 'GBX',
        'market': 'LON',
        'realized_gain_eur': -143.28  # B/P real en EUR
    })
    print(f"   Transaccion GBX creada: ID {trans_id2}")

    # Test: Añadir dividendo
    print("\nTest: Añadir dividendo")
    div_id = db.add_dividend({
        'ticker': 'TEF',
        'name': 'Telefonica',
        'date': '2024-06-15',
        'gross_amount': 30.00,
        'net_amount': 24.30,
        'currency': 'EUR',
        'notes': 'Dividendo semestral'
    })
    print(f"   Dividendo creado: ID {div_id}")

    # Test: Obtener dividendo por ID
    print("\nTest: Obtener dividendo por ID")
    dividend = db.get_dividend_by_id(div_id)
    if dividend:
        print(f"   Encontrado: {dividend.ticker} - {dividend.net_amount}EUR")

    # Test: Actualizar dividendo
    print("\nTest: Actualizar dividendo")
    updated = db.update_dividend(div_id, {'notes': 'Dividendo semestral 2024'})
    print(f"   Actualizado: {updated}")

    # Test: Obtener transacciones
    print("\nTest: Obtener transacciones")
    transactions = db.get_transactions()
    for t in transactions[-2:]:
        print(f"   {t.name}: {t.quantity} @ {t.price} {t.currency}")
        if t.realized_gain_eur:
            print(f"      -> B/P EUR: {t.realized_gain_eur:+.2f}EUR")

    # Test: Estadísticas
    print("\nTest: Estadisticas")
    stats = db.get_database_stats()
    print(f"   Total transacciones: {stats['total_transactions']}")
    print(f"   Total dividendos: {stats['total_dividends']}")
    print(f"   Divisas: {db.get_currencies_used()}")
    print(f"   Mercados: {db.get_markets_used()}")

    # Limpiar test
    db.delete_transaction(trans_id1)
    db.delete_transaction(trans_id2)
    db.delete_dividend(div_id)

    db.close()

    print("\n" + "="*60)
    print("TESTS COMPLETADOS")
    print("="*60 + "\n")
