"""
Models - Modelos de datos para Investment Tracker

Este modulo contiene modelos SQLAlchemy para:
- Portfolio: Carteras de inversión (cloud multi-tenant)
- Fund: Catálogo de fondos de inversión
- Category: Categorías personalizadas

Los modelos base (Transaction, Dividend, etc.) permanecen en database.py
por compatibilidad con código existente.

Cloud Migration - Fase 2: Modelo de datos unificado
"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Usar la misma Base que database.py para que compartan metadata
try:
    from src.data.database import Base
except ImportError:
    from database import Base


# =============================================================================
# MODELO PORTFOLIO - Multi-tenant para Cloud
# =============================================================================

class Portfolio(Base):
    """
    Modelo para carteras de inversión.

    En modo LOCAL: No se usa (cada archivo .db es una cartera)
    En modo CLOUD: Una fila por cartera, relacionada con transacciones/dividendos

    Uso:
        from src.data.models import Portfolio

        portfolio = Portfolio(
            name='Mi Cartera Personal',
            description='Inversiones a largo plazo'
        )
    """
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name})>"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Fund(Base):
    """
    Modelo para catalogo de fondos de inversion.

    Almacena informacion estatica de fondos para busqueda y comparacion.
    Los campos siguen la estructura de datos de CNMV/Morningstar.

    Campos principales:
    - Identificacion: isin, ticker, name
    - Clasificacion: category, subcategory, asset_class
    - Costes: ter, entry_fee, exit_fee
    - Riesgo: risk_level (1-7 CNMV), volatility
    - Rating: morningstar_rating (1-5 estrellas)
    - Gestora: manager, manager_country

    Uso:
        from src.data.models import Fund

        fund = Fund(
            isin='ES0114105036',
            name='Bestinver Internacional FI',
            category='Renta Variable',
            subcategory='RV Global',
            ter=1.78,
            risk_level=5
        )
    """
    __tablename__ = 'funds'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificacion
    isin = Column(String(12), unique=True, nullable=False, index=True)
    ticker = Column(String(50), index=True)  # Simbolo Yahoo Finance si existe
    name = Column(String(300), nullable=False)
    short_name = Column(String(100))  # Nombre corto para display

    # Clasificacion
    category = Column(String(100), index=True)  # RV, RF, Mixto, Alternativo
    subcategory = Column(String(100))  # RV Global, RF Corporativa, etc.
    asset_class = Column(String(50))  # Equity, Fixed Income, Mixed, Alternative
    region = Column(String(100))  # Global, Europa, USA, Emergentes, etc.
    sector = Column(String(100))  # Tecnologia, Salud, Financiero, etc.

    # Gestora
    manager = Column(String(200), index=True)  # Nombre gestora
    manager_country = Column(String(50))  # Pais de la gestora
    fund_domicile = Column(String(50))  # Domicilio del fondo (Luxemburgo, Irlanda, etc.)

    # Divisa
    currency = Column(String(10), default='EUR')
    hedged = Column(Boolean, default=False)  # Si tiene cobertura de divisa

    # Costes (en porcentaje)
    ter = Column(Float)  # Total Expense Ratio (gastos corrientes)
    ongoing_charges = Column(Float)  # Gastos corrientes (similar a TER)
    entry_fee = Column(Float, default=0.0)  # Comision de suscripcion
    exit_fee = Column(Float, default=0.0)  # Comision de reembolso
    performance_fee = Column(Float)  # Comision de exito
    management_fee = Column(Float)  # Comision de gestion

    # Riesgo y Rating
    risk_level = Column(Integer)  # 1-7 segun clasificacion CNMV/KIID
    morningstar_rating = Column(Integer)  # 1-5 estrellas
    morningstar_category = Column(String(100))  # Categoria Morningstar

    # Rendimiento historico (en porcentaje)
    return_ytd = Column(Float)  # Year to Date
    return_1y = Column(Float)  # 1 ano
    return_3y = Column(Float)  # 3 anos (anualizado)
    return_5y = Column(Float)  # 5 anos (anualizado)
    return_10y = Column(Float)  # 10 anos (anualizado)

    # Volatilidad y metricas de riesgo
    volatility_1y = Column(Float)  # Volatilidad 1 ano anualizada
    volatility_3y = Column(Float)  # Volatilidad 3 anos anualizada
    volatility_5y = Column(Float)  # Volatilidad 5 anos anualizada
    sharpe_1y = Column(Float)  # Ratio Sharpe 1 ano
    sharpe_3y = Column(Float)  # Ratio Sharpe 3 anos
    sharpe_5y = Column(Float)  # Ratio Sharpe 5 anos
    max_drawdown_3y = Column(Float)  # Max drawdown 3 anos

    # Datos estructurados (JSON serializado)
    top_holdings = Column(Text)  # JSON: [{name, weight, sector}, ...]
    asset_allocation = Column(Text)  # JSON: {cash, equity, bond, ...}

    # Tamano y liquidez
    aum = Column(Float)  # Assets Under Management (en millones EUR)
    min_investment = Column(Float)  # Inversion minima
    min_additional = Column(Float)  # Aportacion minima adicional

    # Politica de distribucion
    distribution_policy = Column(String(20))  # accumulation, distribution
    dividend_frequency = Column(String(20))  # annual, quarterly, monthly

    # Benchmark
    benchmark_name = Column(String(200))
    benchmark_ticker = Column(String(50))

    # Fechas
    inception_date = Column(Date)  # Fecha de lanzamiento
    data_date = Column(Date)  # Fecha de los datos

    # Metadatos
    source = Column(String(50))  # morningstar, cnmv, manual
    external_id = Column(String(100))  # ID en fuente externa
    url = Column(String(500))  # URL ficha del fondo
    notes = Column(Text)

    # Categoria personalizada del usuario
    custom_category = Column(String(50))  # RV Global, RF Corto Plazo, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Indices para busquedas frecuentes
    __table_args__ = (
        Index('ix_funds_category_risk', 'category', 'risk_level'),
        Index('ix_funds_manager_category', 'manager', 'category'),
    )

    def __repr__(self):
        return f"<Fund(isin={self.isin}, name={self.short_name or self.name[:30]})>"

    # Helpers para campos JSON
    def get_top_holdings(self) -> list:
        """Deserializa top_holdings de JSON."""
        if self.top_holdings:
            try:
                return json.loads(self.top_holdings)
            except json.JSONDecodeError:
                return []
        return []

    def set_top_holdings(self, holdings: list) -> None:
        """Serializa top_holdings a JSON."""
        self.top_holdings = json.dumps(holdings) if holdings else None

    def get_asset_allocation(self) -> dict:
        """Deserializa asset_allocation de JSON."""
        if self.asset_allocation:
            try:
                return json.loads(self.asset_allocation)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_asset_allocation(self, allocation: dict) -> None:
        """Serializa asset_allocation a JSON."""
        self.asset_allocation = json.dumps(allocation) if allocation else None

    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario."""
        return {
            'id': self.id,
            'isin': self.isin,
            'ticker': self.ticker,
            'name': self.name,
            'short_name': self.short_name,
            'category': self.category,
            'subcategory': self.subcategory,
            'asset_class': self.asset_class,
            'region': self.region,
            'sector': self.sector,
            'manager': self.manager,
            'manager_country': self.manager_country,
            'fund_domicile': self.fund_domicile,
            'currency': self.currency,
            'hedged': self.hedged,
            'ter': self.ter,
            'ongoing_charges': self.ongoing_charges,
            'entry_fee': self.entry_fee,
            'exit_fee': self.exit_fee,
            'performance_fee': self.performance_fee,
            'management_fee': self.management_fee,
            'risk_level': self.risk_level,
            'morningstar_rating': self.morningstar_rating,
            'morningstar_category': self.morningstar_category,
            'return_ytd': self.return_ytd,
            'return_1y': self.return_1y,
            'return_3y': self.return_3y,
            'return_5y': self.return_5y,
            'return_10y': self.return_10y,
            'volatility_1y': self.volatility_1y,
            'volatility_3y': self.volatility_3y,
            'volatility_5y': self.volatility_5y,
            'sharpe_1y': self.sharpe_1y,
            'sharpe_3y': self.sharpe_3y,
            'sharpe_5y': self.sharpe_5y,
            'max_drawdown_3y': self.max_drawdown_3y,
            'top_holdings': self.get_top_holdings(),
            'asset_allocation': self.get_asset_allocation(),
            'aum': self.aum,
            'min_investment': self.min_investment,
            'min_additional': self.min_additional,
            'distribution_policy': self.distribution_policy,
            'dividend_frequency': self.dividend_frequency,
            'benchmark_name': self.benchmark_name,
            'benchmark_ticker': self.benchmark_ticker,
            'inception_date': self.inception_date.isoformat() if self.inception_date else None,
            'data_date': self.data_date.isoformat() if self.data_date else None,
            'source': self.source,
            'url': self.url,
        }

    def to_summary_dict(self) -> dict:
        """Convierte a diccionario resumido para listados."""
        return {
            'id': self.id,
            'isin': self.isin,
            'name': self.short_name or self.name,
            'category': self.morningstar_category or self.category,
            'manager': self.manager,
            'ter': self.ter,
            'risk_level': self.risk_level,
            'morningstar_rating': self.morningstar_rating,
            'return_1y': self.return_1y,
            'return_3y': self.return_3y,
            'volatility_1y': self.volatility_1y,
        }


# =============================================================================
# MODELO CATEGORY - Categorias personalizadas dinamicas
# =============================================================================

class Category(Base):
    """
    Modelo para categorias personalizadas de fondos.

    Permite al usuario crear sus propias categorias para organizar fondos.
    Las categorias se persisten en la base de datos.

    Uso:
        from src.data.models import Category

        cat = Category(name='RV Tecnologia')
        session.add(cat)
        session.commit()
    """
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Category(name={self.name})>"


# Constantes para filtros de UI
FUND_CATEGORIES = [
    'Renta Variable',
    'Renta Fija',
    'Mixto',
    'Monetario',
    'Alternativo',
    'Garantizado',
    'Retorno Absoluto',
]

FUND_REGIONS = [
    'Global',
    'Europa',
    'USA',
    'Espana',
    'Emergentes',
    'Asia',
    'Japon',
    'Latam',
]

FUND_RISK_LEVELS = {
    1: 'Muy bajo',
    2: 'Bajo',
    3: 'Medio-bajo',
    4: 'Medio',
    5: 'Medio-alto',
    6: 'Alto',
    7: 'Muy alto',
}

DISTRIBUTION_POLICIES = {
    'accumulation': 'Acumulacion',
    'distribution': 'Distribucion',
}

# Categorias personalizadas iniciales (seed data para tabla categories)
# Estas se insertan en la BD al migrar, luego se leen dinamicamente
DEFAULT_CUSTOM_CATEGORIES = [
    "RV Global",
    "RV USA",
    "RV Europa",
    "RV Emergente",
    "RV Sectorial",
    "RF Corto Plazo",
    "RF Largo Plazo",
    "Retorno Absoluto",
    "Monetario",
    "Otros",
]

# Alias para compatibilidad (deprecated, usar get_all_categories() del servicio)
CUSTOM_CATEGORIES = DEFAULT_CUSTOM_CATEGORIES
