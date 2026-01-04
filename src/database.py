"""
Módulo de gestión de base de datos
Gestiona todas las operaciones con SQLite usando SQLAlchemy
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, 
    DateTime, Text, ForeignKey, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import pandas as pd
from pathlib import Path
import sys

# Añadir directorio raíz al path para imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATABASE_URL, DATABASE_PATH

# Base para modelos SQLAlchemy
Base = declarative_base()


# ==========================================
# MODELOS (TABLAS)
# ==========================================

class Transaction(Base):
    """
    Modelo de transacciones financieras
    Registra todas las operaciones: compras, ventas, traspasos
    """
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # buy, sell, transfer
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(200))  # Nombre del activo (opcional)
    asset_type = Column(String(20))  # accion, fondo, etf, bono
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    total = Column(Float)  # Se calcula automáticamente
    notes = Column(Text)  # Notas adicionales
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Transaction({self.date}, {self.type}, {self.ticker}, {self.quantity})>"


class Dividend(Base):
    """
    Modelo de dividendos recibidos
    """
    __tablename__ = 'dividends'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    gross_amount = Column(Float, nullable=False)  # Importe bruto
    net_amount = Column(Float, nullable=False)    # Importe neto (después retención)
    withholding_tax = Column(Float)  # Retención aplicada
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Dividend({self.ticker}, {self.date}, {self.net_amount}€)>"


class BenchmarkData(Base):
    """
    Modelo de datos de benchmarks (índices de referencia)
    """
    __tablename__ = 'benchmark_data'
    
    id = Column(Integer, primary_key=True)
    benchmark_name = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    close_value = Column(Float, nullable=False)
    
    def __repr__(self):
        return f"<Benchmark({self.benchmark_name}, {self.date}, {self.close_value})>"


class PortfolioSnapshot(Base):
    """
    Modelo de snapshots de cartera (para tracking histórico)
    Se puede guardar valor total de cartera en fechas específicas
    """
    __tablename__ = 'portfolio_snapshots'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    invested_capital = Column(Float)  # Capital aportado hasta esa fecha
    realized_gains = Column(Float)    # Ganancias realizadas acumuladas
    notes = Column(Text)
    
    def __repr__(self):
        return f"<Snapshot({self.date}, {self.total_value}€)>"


# ==========================================
# CLASE DATABASE - GESTOR PRINCIPAL
# ==========================================

class Database:
    """
    Clase principal para gestionar la base de datos
    Proporciona métodos para todas las operaciones CRUD
    """
    
    def __init__(self, db_url=None):
        """
        Inicializa conexión a la base de datos
        
        Args:
            db_url: URL de conexión (usa config por defecto si no se especifica)
        """
        self.db_url = db_url or DATABASE_URL
        self.engine = create_engine(self.db_url, echo=False)
        
        # Crear todas las tablas si no existen
        Base.metadata.create_all(self.engine)
        
        # Crear sesión
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        print(f"✅ Base de datos inicializada: {DATABASE_PATH}")
    
    def close(self):
        """Cierra la sesión de la base de datos"""
        self.session.close()
    
    # ==========================================
    # MÉTODOS PARA TRANSACTIONS
    # ==========================================
    
    def add_transaction(self, transaction_data):
        """
        Añade una nueva transacción
        
        Args:
            transaction_data: Dict con datos de la transacción
                Campos requeridos: date, type, ticker, quantity, price
                Campos opcionales: name, asset_type, commission, notes
        
        Returns:
            ID de la transacción creada
        """
        # Calcular total si no viene especificado
        if 'total' not in transaction_data:
            quantity = transaction_data['quantity']
            price = transaction_data['price']
            commission = transaction_data.get('commission', 0.0)
            
            if transaction_data['type'] == 'buy':
                total = (quantity * price) + commission
            elif transaction_data['type'] == 'sell':
                total = (quantity * price) - commission
            else:
                total = quantity * price
            
            transaction_data['total'] = total
        
        # Crear objeto Transaction
        trans = Transaction(**transaction_data)
        
        # Guardar en DB
        self.session.add(trans)
        self.session.commit()
        
        print(f"✅ Transacción añadida: {trans.type.upper()} {trans.quantity} {trans.ticker}")
        return trans.id
    
    def get_transactions(self, **filters):
        """
        Obtiene transacciones con filtros opcionales
        
        Args:
            **filters: Filtros opcionales
                - type: tipo de transacción ('buy', 'sell', 'transfer')
                - ticker: ticker específico
                - asset_type: tipo de activo
                - start_date: fecha inicio
                - end_date: fecha fin
                - year: año específico
                - limit: número máximo de resultados
        
        Returns:
            Lista de objetos Transaction
        """
        query = self.session.query(Transaction)
        
        # Aplicar filtros
        if 'type' in filters:
            query = query.filter(Transaction.type == filters['type'])
        
        if 'ticker' in filters:
            query = query.filter(Transaction.ticker == filters['ticker'])
        
        if 'asset_type' in filters:
            query = query.filter(Transaction.asset_type == filters['asset_type'])
        
        if 'start_date' in filters:
            query = query.filter(Transaction.date >= filters['start_date'])
        
        if 'end_date' in filters:
            query = query.filter(Transaction.date <= filters['end_date'])
        
        if 'year' in filters:
            year = filters['year']
            query = query.filter(
                Transaction.date >= f'{year}-01-01',
                Transaction.date <= f'{year}-12-31'
            )
        
        # Ordenar por fecha descendente por defecto
        query = query.order_by(Transaction.date.desc())
        
        # Limitar resultados si se especifica
        if 'limit' in filters:
            query = query.limit(filters['limit'])
        
        return query.all()
    
    def get_transaction_by_id(self, transaction_id):
        """Obtiene una transacción específica por ID"""
        return self.session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
    
    def update_transaction(self, transaction_id, update_data):
        """
        Actualiza una transacción existente
        
        Args:
            transaction_id: ID de la transacción
            update_data: Dict con campos a actualizar
        
        Returns:
            True si se actualizó, False si no se encontró
        """
        trans = self.get_transaction_by_id(transaction_id)
        
        if not trans:
            print(f"❌ Transacción {transaction_id} no encontrada")
            return False
        
        # Actualizar campos
        for key, value in update_data.items():
            if hasattr(trans, key):
                setattr(trans, key, value)
        
        # Recalcular total si cambió cantidad, precio o comisión
        if any(k in update_data for k in ['quantity', 'price', 'commission']):
            if trans.type == 'buy':
                trans.total = (trans.quantity * trans.price) + trans.commission
            elif trans.type == 'sell':
                trans.total = (trans.quantity * trans.price) - trans.commission
        
        self.session.commit()
        print(f"✅ Transacción {transaction_id} actualizada")
        return True
    
    def delete_transaction(self, transaction_id):
        """
        Elimina una transacción
        
        Args:
            transaction_id: ID de la transacción a eliminar
        
        Returns:
            True si se eliminó, False si no se encontró
        """
        trans = self.get_transaction_by_id(transaction_id)
        
        if not trans:
            print(f"❌ Transacción {transaction_id} no encontrada")
            return False
        
        self.session.delete(trans)
        self.session.commit()
        print(f"✅ Transacción {transaction_id} eliminada")
        return True
    
    def get_all_tickers(self):
        """Obtiene lista de todos los tickers únicos"""
        tickers = self.session.query(Transaction.ticker).distinct().all()
        return [t[0] for t in tickers]
    
    # ==========================================
    # MÉTODOS PARA DIVIDENDS
    # ==========================================
    
    def add_dividend(self, dividend_data):
        """
        Añade un dividendo recibido
        
        Args:
            dividend_data: Dict con datos del dividendo
                Campos requeridos: ticker, date, gross_amount, net_amount
        
        Returns:
            ID del dividendo creado
        """
        # Calcular retención si no viene
        if 'withholding_tax' not in dividend_data:
            dividend_data['withholding_tax'] = (
                dividend_data['gross_amount'] - dividend_data['net_amount']
            )
        
        div = Dividend(**dividend_data)
        self.session.add(div)
        self.session.commit()
        
        print(f"✅ Dividendo añadido: {div.ticker} - {div.net_amount}€")
        return div.id
    
    def get_dividends(self, **filters):
        """
        Obtiene dividendos con filtros opcionales
        
        Args:
            **filters: Filtros opcionales (ticker, year, start_date, end_date)
        
        Returns:
            Lista de objetos Dividend
        """
        query = self.session.query(Dividend)
        
        if 'ticker' in filters:
            query = query.filter(Dividend.ticker == filters['ticker'])
        
        if 'year' in filters:
            year = filters['year']
            query = query.filter(
                Dividend.date >= f'{year}-01-01',
                Dividend.date <= f'{year}-12-31'
            )
        
        if 'start_date' in filters:
            query = query.filter(Dividend.date >= filters['start_date'])
        
        if 'end_date' in filters:
            query = query.filter(Dividend.date <= filters['end_date'])
        
        return query.order_by(Dividend.date.desc()).all()
    
    # ==========================================
    # MÉTODOS PARA BENCHMARKS
    # ==========================================
    
    def add_benchmark_data(self, benchmark_name, date, close_value):
        """Añade un punto de dato de benchmark"""
        bench = BenchmarkData(
            benchmark_name=benchmark_name,
            date=date,
            close_value=close_value
        )
        self.session.add(bench)
        self.session.commit()
        return bench.id
    
    def get_benchmark_data(self, benchmark_name, start_date=None, end_date=None):
        """Obtiene datos de un benchmark"""
        query = self.session.query(BenchmarkData).filter(
            BenchmarkData.benchmark_name == benchmark_name
        )
        
        if start_date:
            query = query.filter(BenchmarkData.date >= start_date)
        if end_date:
            query = query.filter(BenchmarkData.date <= end_date)
        
        return query.order_by(BenchmarkData.date).all()
    
    def get_available_benchmarks(self):
        """Lista de benchmarks disponibles en la DB"""
        benchmarks = self.session.query(BenchmarkData.benchmark_name).distinct().all()
        return [b[0] for b in benchmarks]
    
    # ==========================================
    # MÉTODOS AUXILIARES - CONVERSIÓN A PANDAS
    # ==========================================
    
    def transactions_to_dataframe(self, transactions=None):
        """
        Convierte transacciones a DataFrame de pandas
        
        Args:
            transactions: Lista de Transaction objects (usa todas si es None)
        
        Returns:
            pandas DataFrame
        """
        if transactions is None:
            transactions = self.get_transactions()
        
        if not transactions:
            return pd.DataFrame()
        
        data = []
        for t in transactions:
            data.append({
                'id': t.id,
                'date': t.date,
                'type': t.type,
                'ticker': t.ticker,
                'name': t.name,
                'asset_type': t.asset_type,
                'quantity': t.quantity,
                'price': t.price,
                'commission': t.commission,
                'total': t.total,
                'notes': t.notes
            })
        
        return pd.DataFrame(data)
    
    def dividends_to_dataframe(self, dividends=None):
        """Convierte dividendos a DataFrame de pandas"""
        if dividends is None:
            dividends = self.get_dividends()
        
        if not dividends:
            return pd.DataFrame()
        
        data = []
        for d in dividends:
            data.append({
                'id': d.id,
                'ticker': d.ticker,
                'date': d.date,
                'gross_amount': d.gross_amount,
                'net_amount': d.net_amount,
                'withholding_tax': d.withholding_tax,
                'notes': d.notes
            })
        
        return pd.DataFrame(data)
    
    # ==========================================
    # MÉTODOS DE UTILIDAD
    # ==========================================
    
    def get_database_stats(self):
        """Obtiene estadísticas de la base de datos"""
        stats = {
            'total_transactions': self.session.query(Transaction).count(),
            'total_dividends': self.session.query(Dividend).count(),
            'unique_tickers': len(self.get_all_tickers()),
            'date_range': None
        }
        
        # Rango de fechas
        first = self.session.query(Transaction).order_by(Transaction.date).first()
        last = self.session.query(Transaction).order_by(Transaction.date.desc()).first()
        
        if first and last:
            stats['date_range'] = (first.date, last.date)
        
        return stats
    
    def clear_all_data(self):
        """
        ⚠️ CUIDADO: Elimina TODOS los datos de todas las tablas
        Útil solo para testing o reset completo
        """
        confirm = input("⚠️ Esto eliminará TODOS los datos. ¿Confirmas? (escribe 'SI'): ")
        
        if confirm == 'SI':
            self.session.query(Transaction).delete()
            self.session.query(Dividend).delete()
            self.session.query(BenchmarkData).delete()
            self.session.query(PortfolioSnapshot).delete()
            self.session.commit()
            print("✅ Todos los datos eliminados")
        else:
            print("❌ Operación cancelada")


# ==========================================
# FUNCIÓN DE PRUEBA
# ==========================================

def test_database():
    """Función de prueba para validar que todo funciona"""
    print("\n" + "="*50)
    print("🧪 PROBANDO BASE DE DATOS")
    print("="*50 + "\n")
    
    # Inicializar DB
    db = Database()
    
    # 1. Añadir transacciones de prueba
    print("\n1️⃣ Añadiendo transacciones de prueba...")
    
    trans1_id = db.add_transaction({
        'date': '2024-01-15',
        'type': 'buy',
        'ticker': 'TEF',
        'name': 'Telefónica SA',
        'asset_type': 'accion',
        'quantity': 100,
        'price': 4.20,
        'commission': 10.0,
        'notes': 'Primera compra de prueba'
    })
    
    trans2_id = db.add_transaction({
        'date': '2024-03-20',
        'type': 'buy',
        'ticker': 'BBVA',
        'name': 'Banco BBVA',
        'asset_type': 'accion',
        'quantity': 50,
        'price': 9.50,
        'commission': 8.50
    })
    
    # 2. Consultar transacciones
    print("\n2️⃣ Consultando transacciones...")
    all_trans = db.get_transactions()
    print(f"   Total transacciones: {len(all_trans)}")
    
    # 3. Filtrar por ticker
    print("\n3️⃣ Filtrando por ticker TEF...")
    tef_trans = db.get_transactions(ticker='TEF')
    print(f"   Transacciones de TEF: {len(tef_trans)}")
    
    # 4. Añadir dividendo
    print("\n4️⃣ Añadiendo dividendo de prueba...")
    div_id = db.add_dividend({
        'ticker': 'TEF',
        'date': '2024-06-15',
        'gross_amount': 25.00,
        'net_amount': 20.25,
        'notes': 'Dividendo semestral'
    })
    
    # 5. Consultar dividendos
    print("\n5️⃣ Consultando dividendos...")
    divs = db.get_dividends(ticker='TEF')
    print(f"   Dividendos de TEF: {len(divs)}")
    
    # 6. Convertir a DataFrame
    print("\n6️⃣ Convirtiendo a pandas DataFrame...")
    df_trans = db.transactions_to_dataframe()
    print(f"   DataFrame shape: {df_trans.shape}")
    print("\n   Primeras filas:")
    print(df_trans.head())
    
    # 7. Estadísticas
    print("\n7️⃣ Estadísticas de la base de datos...")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 8. Obtener todos los tickers
    print("\n8️⃣ Tickers únicos en la base de datos...")
    tickers = db.get_all_tickers()
    print(f"   Tickers: {tickers}")
    
    print("\n" + "="*50)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("="*50 + "\n")
    
    db.close()


if __name__ == '__main__':
    # Si ejecutas este archivo directamente, corre las pruebas
    test_database()