"""
Portfolio Module - Análisis de Cartera y Rentabilidades
Sesión 3 del Investment Tracker (Actualizado v2)

CAMBIOS v2:
- Muestra 'name' (nombre del activo) en outputs además de ticker
- Usa 'realized_gain_eur' del CSV cuando está disponible (evita errores de divisa)
- Soporta transacciones multi-divisa (EUR, USD, GBX, CAD)
- Mejoras en formato de salida para legibilidad

Este módulo es el "cerebro financiero" del sistema:
- Calcula posiciones actuales
- Calcula valor total de cartera
- Calcula plusvalías latentes y realizadas
- Analiza rentabilidad por activo y global
- Genera datos para visualizaciones
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Union
from pathlib import Path

# Importar módulo de base de datos
try:
    from src.database import Database
except ImportError:
    from database import Database


class Portfolio:
    """
    Clase principal para análisis de cartera.
    
    Uso básico:
        portfolio = Portfolio()
        
        # Ver posiciones actuales
        positions = portfolio.get_current_positions()
        
        # Valor total de la cartera
        total = portfolio.get_total_value()
        
        # Plusvalías latentes
        gains = portfolio.get_unrealized_gains()
        
        # Rentabilidad por activo
        perf = portfolio.get_performance_by_asset()
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el Portfolio.
        
        Args:
            db_path: Ruta a la base de datos. Si es None, usa la ruta por defecto.
        """
        self.db = Database(db_path) if db_path else Database()
        self._positions_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # Cache válido por 60 segundos
    
    def _invalidate_cache(self):
        """Invalida el cache de posiciones"""
        self._positions_cache = None
        self._cache_timestamp = None
    
    def _is_cache_valid(self) -> bool:
        """Verifica si el cache es válido"""
        if self._positions_cache is None or self._cache_timestamp is None:
            return False
        return (datetime.now() - self._cache_timestamp).seconds < self._cache_ttl
    
    def _get_display_name(self, ticker: str, name: str) -> str:
        """Genera nombre para mostrar: prioriza name, fallback a ticker"""
        if name and name.strip() and name != ticker:
            # Truncar nombres muy largos
            if len(name) > 40:
                return name[:37] + "..."
            return name
        return ticker
    
    # =========================================================================
    # POSICIONES ACTUALES
    # =========================================================================
    
    def get_current_positions(self, 
                              asset_type: str = None,
                              include_zero: bool = False,
                              current_prices: Dict[str, float] = None) -> pd.DataFrame:
        """
        Calcula las posiciones actuales de la cartera.
        
        Args:
            asset_type: Filtrar por tipo ('accion', 'fondo', 'etf'). None = todos
            include_zero: Si True, incluye posiciones con cantidad 0
            current_prices: Dict con precios actuales {ticker: price}. 
                           Si None, usa el último precio de compra como aproximación.
        
        Returns:
            DataFrame con columnas:
            - ticker: Símbolo del activo
            - name: Nombre del activo
            - display_name: Nombre para mostrar (name o ticker)
            - asset_type: Tipo de activo
            - quantity: Cantidad actual
            - avg_price: Precio medio de compra
            - cost_basis: Coste total de adquisición
            - current_price: Precio actual (si se proporciona)
            - market_value: Valor de mercado actual
            - unrealized_gain: Plusvalía/minusvalía latente (€)
            - unrealized_gain_pct: Plusvalía/minusvalía latente (%)
            - currency: Divisa original de las transacciones
        """
        # Obtener todas las transacciones
        transactions = self.db.get_transactions()
        
        if not transactions:
            return pd.DataFrame(columns=[
                'ticker', 'name', 'display_name', 'asset_type', 'quantity', 'avg_price',
                'cost_basis', 'current_price', 'market_value', 
                'unrealized_gain', 'unrealized_gain_pct', 'currency'
            ])
        
        # Convertir a DataFrame
        df = self.db.transactions_to_dataframe(transactions)
        
        # Calcular posiciones por ticker usando FIFO implícito
        positions = []
        
        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker].sort_values('date')
            
            # Calcular cantidad y coste acumulado
            total_quantity = 0.0
            total_cost = 0.0
            name = ticker_df['name'].iloc[0] if 'name' in ticker_df.columns else ticker
            asset_type_val = ticker_df['asset_type'].iloc[0] if 'asset_type' in ticker_df.columns else 'unknown'
            currency = ticker_df['currency'].iloc[0] if 'currency' in ticker_df.columns else 'EUR'
            
            # Lista de lotes para FIFO
            lots = []  # [(quantity, price, date), ...]
            
            for _, row in ticker_df.iterrows():
                if row['type'] == 'buy':
                    lots.append({
                        'quantity': row['quantity'],
                        'price': row['price'],
                        'date': row['date'],
                        'commission': row.get('commission', 0)
                    })
                    total_quantity += row['quantity']
                    total_cost += (row['quantity'] * row['price']) + row.get('commission', 0)
                    
                elif row['type'] == 'sell':
                    qty_to_sell = row['quantity']
                    
                    # Aplicar FIFO: vender de los lotes más antiguos primero
                    while qty_to_sell > 0 and lots:
                        lot = lots[0]
                        if lot['quantity'] <= qty_to_sell:
                            # Vender lote completo
                            qty_to_sell -= lot['quantity']
                            total_quantity -= lot['quantity']
                            total_cost -= (lot['quantity'] * lot['price'])
                            lots.pop(0)
                        else:
                            # Vender parte del lote
                            lot['quantity'] -= qty_to_sell
                            total_quantity -= qty_to_sell
                            total_cost -= (qty_to_sell * lot['price'])
                            qty_to_sell = 0
                
                elif row['type'] == 'transfer_out':
                    # Traspaso saliente: reduce cantidad pero mantiene base de coste proporcional
                    if total_quantity > 0:
                        proportion = row['quantity'] / total_quantity
                        total_quantity -= row['quantity']
                        total_cost -= total_cost * proportion
                
                elif row['type'] == 'transfer_in':
                    # Traspaso entrante: aumenta cantidad con su base de coste
                    total_quantity += row['quantity']
                    total_cost += row['quantity'] * row['price']
            
            # Solo incluir si tiene cantidad > 0 (o si include_zero=True)
            if total_quantity > 0 or include_zero:
                avg_price = total_cost / total_quantity if total_quantity > 0 else 0
                
                # Precio actual: del dict proporcionado o usar avg_price como aproximación
                if current_prices and ticker in current_prices:
                    current_price = current_prices[ticker]
                else:
                    # Usar el último precio de transacción como aproximación
                    last_buy = ticker_df[ticker_df['type'] == 'buy']
                    current_price = last_buy['price'].iloc[-1] if len(last_buy) > 0 else avg_price
                
                market_value = total_quantity * current_price
                unrealized_gain = market_value - total_cost
                unrealized_gain_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0
                
                positions.append({
                    'ticker': ticker,
                    'name': name if name else ticker,
                    'display_name': self._get_display_name(ticker, name),
                    'asset_type': asset_type_val,
                    'quantity': round(total_quantity, 8),
                    'avg_price': round(avg_price, 4),
                    'cost_basis': round(total_cost, 2),
                    'current_price': round(current_price, 4),
                    'market_value': round(market_value, 2),
                    'unrealized_gain': round(unrealized_gain, 2),
                    'unrealized_gain_pct': round(unrealized_gain_pct, 2),
                    'currency': currency
                })
        
        result_df = pd.DataFrame(positions)
        
        # Filtrar por tipo de activo si se especifica
        if asset_type and not result_df.empty:
            result_df = result_df[result_df['asset_type'] == asset_type]
        
        # Ordenar por valor de mercado descendente
        if not result_df.empty:
            result_df = result_df.sort_values('market_value', ascending=False)
        
        return result_df.reset_index(drop=True)
    
    def get_position(self, ticker: str, current_price: float = None) -> Dict:
        """
        Obtiene detalle de una posición específica.
        
        Args:
            ticker: Símbolo del activo
            current_price: Precio actual (opcional)
        
        Returns:
            Dict con información de la posición o None si no existe
        """
        prices = {ticker: current_price} if current_price else None
        positions = self.get_current_positions(current_prices=prices)
        
        if positions.empty:
            return None
        
        position = positions[positions['ticker'] == ticker]
        
        if position.empty:
            return None
        
        return position.iloc[0].to_dict()
    
    def get_available_lots(self, ticker: str) -> List[Dict]:
        """
        Obtiene los lotes de compra disponibles (no vendidos) de un ticker.
        Útil para planificar ventas y calcular impacto fiscal.
        
        Args:
            ticker: Símbolo del activo
        
        Returns:
            Lista de lotes disponibles, cada uno con:
            - quantity: Cantidad disponible
            - price: Precio de compra
            - date: Fecha de compra
            - cost: Coste total del lote
        """
        transactions = self.db.get_transactions(ticker=ticker)
        
        if not transactions:
            return []
        
        df = self.db.transactions_to_dataframe(transactions)
        df = df.sort_values('date')
        
        lots = []
        
        for _, row in df.iterrows():
            if row['type'] == 'buy':
                lots.append({
                    'quantity': row['quantity'],
                    'price': row['price'],
                    'date': row['date'],
                    'cost': row['quantity'] * row['price']
                })
            
            elif row['type'] == 'sell':
                qty_to_sell = row['quantity']
                
                # FIFO: vender de los lotes más antiguos
                while qty_to_sell > 0 and lots:
                    if lots[0]['quantity'] <= qty_to_sell:
                        qty_to_sell -= lots[0]['quantity']
                        lots.pop(0)
                    else:
                        lots[0]['quantity'] -= qty_to_sell
                        lots[0]['cost'] = lots[0]['quantity'] * lots[0]['price']
                        qty_to_sell = 0
        
        return lots
    
    # =========================================================================
    # VALOR DE CARTERA
    # =========================================================================
    
    def get_total_value(self, current_prices: Dict[str, float] = None) -> float:
        """
        Calcula el valor total de la cartera.
        
        Args:
            current_prices: Dict con precios actuales {ticker: price}
        
        Returns:
            Valor total de la cartera en €
        """
        positions = self.get_current_positions(current_prices=current_prices)
        
        if positions.empty:
            return 0.0
        
        return round(positions['market_value'].sum(), 2)
    
    def get_total_cost_basis(self) -> float:
        """
        Calcula el coste total de adquisición de la cartera actual.
        
        Returns:
            Coste total invertido en posiciones actuales (€)
        """
        positions = self.get_current_positions()
        
        if positions.empty:
            return 0.0
        
        return round(positions['cost_basis'].sum(), 2)
    
    def get_historical_value(self, 
                            start_date: Union[str, datetime] = None,
                            end_date: Union[str, datetime] = None,
                            frequency: str = 'daily') -> pd.DataFrame:
        """
        Calcula la evolución histórica del valor de la cartera.
        
        NOTA: Sin precios de mercado históricos, esto calcula el valor
        basado en el coste de adquisición. Para valores de mercado reales,
        necesitarías integrar con una API de precios (yfinance).
        
        Args:
            start_date: Fecha inicio (YYYY-MM-DD o datetime)
            end_date: Fecha fin (YYYY-MM-DD o datetime)
            frequency: 'daily', 'weekly', 'monthly'
        
        Returns:
            DataFrame con columnas:
            - date: Fecha
            - invested_capital: Capital invertido acumulado
            - num_positions: Número de posiciones
        """
        transactions = self.db.get_transactions()
        
        if not transactions:
            return pd.DataFrame(columns=['date', 'invested_capital', 'num_positions'])
        
        df = self.db.transactions_to_dataframe(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Determinar rango de fechas
        if start_date is None:
            start_date = df['date'].min()
        else:
            start_date = pd.to_datetime(start_date)
        
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = pd.to_datetime(end_date)
        
        # Crear rango de fechas
        if frequency == 'daily':
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        elif frequency == 'weekly':
            date_range = pd.date_range(start=start_date, end=end_date, freq='W')
        elif frequency == 'monthly':
            date_range = pd.date_range(start=start_date, end=end_date, freq='ME')
        else:
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        history = []
        
        for date in date_range:
            # Filtrar transacciones hasta esta fecha
            df_until_date = df[df['date'] <= date]
            
            # Calcular capital invertido y posiciones
            invested = 0.0
            positions_count = {}
            
            for _, row in df_until_date.iterrows():
                ticker = row['ticker']
                
                if ticker not in positions_count:
                    positions_count[ticker] = 0
                
                if row['type'] == 'buy':
                    invested += row['quantity'] * row['price'] + row.get('commission', 0)
                    positions_count[ticker] += row['quantity']
                elif row['type'] == 'sell':
                    # Reducir capital invertido proporcionalmente
                    if positions_count[ticker] > 0:
                        sold_pct = row['quantity'] / positions_count[ticker]
                        # Simplificación: restamos el valor de venta
                        invested -= row['quantity'] * row['price'] - row.get('commission', 0)
                    positions_count[ticker] -= row['quantity']
            
            # Contar posiciones con cantidad > 0
            active_positions = sum(1 for qty in positions_count.values() if qty > 0)
            
            history.append({
                'date': date,
                'invested_capital': round(invested, 2),
                'num_positions': active_positions
            })
        
        return pd.DataFrame(history)
    
    def get_invested_capital_timeline(self,
                                      start_date: str = None,
                                      end_date: str = None) -> pd.DataFrame:
        """
        Genera timeline de aportaciones/retiradas de capital.
        
        Returns:
            DataFrame con:
            - date: Fecha
            - flow: Flujo de capital (positivo = aportación, negativo = retirada)
            - cumulative: Acumulado
            - type: 'buy', 'sell', etc.
        """
        transactions = self.db.get_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        if not transactions:
            return pd.DataFrame(columns=['date', 'flow', 'cumulative', 'type'])
        
        df = self.db.transactions_to_dataframe(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        flows = []
        cumulative = 0.0
        
        for _, row in df.iterrows():
            if row['type'] == 'buy':
                flow = row['quantity'] * row['price'] + row.get('commission', 0)
                cumulative += flow
            elif row['type'] == 'sell':
                flow = -(row['quantity'] * row['price'] - row.get('commission', 0))
                cumulative += flow
            else:
                continue
            
            flows.append({
                'date': row['date'],
                'flow': round(flow, 2),
                'cumulative': round(cumulative, 2),
                'type': row['type'],
                'ticker': row['ticker'],
                'name': row.get('name', row['ticker'])
            })
        
        return pd.DataFrame(flows)
    
    # =========================================================================
    # RENTABILIDAD
    # =========================================================================
    
    def get_unrealized_gains(self, 
                            current_prices: Dict[str, float] = None) -> Dict:
        """
        Calcula plusvalías/minusvalías latentes (no realizadas).
        
        Args:
            current_prices: Dict con precios actuales {ticker: price}
        
        Returns:
            Dict con:
            - total_gain: Plusvalía total (€)
            - total_gain_pct: Plusvalía total (%)
            - cost_basis: Coste total de adquisición
            - market_value: Valor de mercado actual
            - by_asset: DataFrame con desglose por activo
        """
        positions = self.get_current_positions(current_prices=current_prices)
        
        if positions.empty:
            return {
                'total_gain': 0.0,
                'total_gain_pct': 0.0,
                'cost_basis': 0.0,
                'market_value': 0.0,
                'by_asset': pd.DataFrame()
            }
        
        total_cost = positions['cost_basis'].sum()
        total_market = positions['market_value'].sum()
        total_gain = total_market - total_cost
        total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'total_gain': round(total_gain, 2),
            'total_gain_pct': round(total_gain_pct, 2),
            'cost_basis': round(total_cost, 2),
            'market_value': round(total_market, 2),
            'by_asset': positions[['ticker', 'name', 'display_name', 'unrealized_gain', 'unrealized_gain_pct']]
        }
    
    def get_realized_gains(self, year: int = None) -> Dict:
        """
        Calcula plusvalías/minusvalías realizadas (ventas completadas).
        
        IMPORTANTE: Usa el campo 'realized_gain_eur' cuando está disponible
        (ya incluye conversión de divisa correcta). Solo recalcula si no existe.
        
        Args:
            year: Año fiscal. Si es None, calcula para todos los años.
        
        Returns:
            Dict con:
            - total_gains: Total plusvalías (€)
            - total_losses: Total minusvalías (€)
            - net_gain: Balance neto
            - num_sales: Número de ventas
            - sales_detail: DataFrame con detalle de cada venta
        """
        transactions = self.db.get_transactions(type='sell')
        
        if not transactions:
            return {
                'total_gains': 0.0,
                'total_losses': 0.0,
                'net_gain': 0.0,
                'num_sales': 0,
                'sales_detail': pd.DataFrame()
            }
        
        df = self.db.transactions_to_dataframe(transactions)
        df['date'] = pd.to_datetime(df['date'])
        
        # Filtrar por año si se especifica
        if year:
            df = df[df['date'].dt.year == year]
        
        if df.empty:
            return {
                'total_gains': 0.0,
                'total_losses': 0.0,
                'net_gain': 0.0,
                'num_sales': 0,
                'sales_detail': pd.DataFrame()
            }
        
        # Calcular ganancia/pérdida por cada venta
        sales_details = []
        
        for _, sale in df.iterrows():
            ticker = sale['ticker']
            name = sale.get('name', ticker)
            sale_date = sale['date']
            sale_qty = sale['quantity']
            sale_price = sale['price']
            currency = sale.get('currency', 'EUR')
            
            # ¡IMPORTANTE! Usar realized_gain_eur si está disponible
            # Esto evita errores de conversión de divisa (ej: peniques a euros)
            if pd.notna(sale.get('realized_gain_eur')) and sale.get('realized_gain_eur') != 0:
                # Usar el B/P ya convertido a EUR del CSV
                gain = sale['realized_gain_eur']
                # Estimar proceeds y cost_basis para el reporte
                sale_proceeds = sale_qty * sale_price  # En divisa original
                cost_basis = sale_proceeds - gain  # Aproximación
            else:
                # Calcular manualmente (solo para transacciones sin realized_gain_eur)
                sale_proceeds = sale_qty * sale_price
                
                # Obtener compras anteriores a la venta para este ticker
                buys = self.db.get_transactions(
                    ticker=ticker,
                    type='buy',
                    end_date=sale_date.strftime('%Y-%m-%d')
                )
                
                if not buys:
                    cost_basis = 0
                else:
                    buys_df = self.db.transactions_to_dataframe(buys)
                    buys_df = buys_df.sort_values('date')
                    
                    # Calcular coste medio de compra (simplificado)
                    total_bought = buys_df['quantity'].sum()
                    total_cost = (buys_df['quantity'] * buys_df['price']).sum()
                    avg_cost = total_cost / total_bought if total_bought > 0 else 0
                    cost_basis = sale_qty * avg_cost
                
                gain = sale_proceeds - cost_basis
            
            sales_details.append({
                'date': sale_date,
                'ticker': ticker,
                'name': name,
                'display_name': self._get_display_name(ticker, name),
                'quantity': sale_qty,
                'sale_price': sale_price,
                'currency': currency,
                'gain_eur': round(gain, 2),  # Siempre en EUR
                'gain_pct': round((gain / cost_basis * 100) if cost_basis > 0 else 0, 2)
            })
        
        sales_df = pd.DataFrame(sales_details)
        
        # Ordenar por fecha descendente
        sales_df = sales_df.sort_values('date', ascending=False)
        
        total_gains = sales_df[sales_df['gain_eur'] > 0]['gain_eur'].sum()
        total_losses = abs(sales_df[sales_df['gain_eur'] < 0]['gain_eur'].sum())
        
        return {
            'total_gains': round(total_gains, 2),
            'total_losses': round(total_losses, 2),
            'net_gain': round(total_gains - total_losses, 2),
            'num_sales': len(sales_df),
            'sales_detail': sales_df
        }
    
    def get_total_return(self, 
                        current_prices: Dict[str, float] = None,
                        include_dividends: bool = True) -> Dict:
        """
        Calcula rentabilidad total de la cartera.
        
        IMPORTANTE: 'total_invested' es el coste de adquisición de las posiciones
        ACTUALES, no la suma de todas las compras históricas. Esto evita contar
        doble el dinero que se ha reinvertido de ventas anteriores.
        
        Args:
            current_prices: Dict con precios actuales
            include_dividends: Si True, incluye dividendos en el cálculo
        
        Returns:
            Dict con métricas de rentabilidad:
            - total_invested: Coste de adquisición de posiciones actuales
            - current_value: Valor de mercado actual
            - unrealized_gain: Plusvalías latentes (no vendidas)
            - realized_gain: Plusvalías realizadas (ventas)
            - dividends: Total dividendos cobrados
            - total_gain: Ganancia total (latente + realizada + dividendos)
            - total_return_pct: Rentabilidad % sobre lo invertido actualmente
        """
        # Plusvalías latentes
        unrealized = self.get_unrealized_gains(current_prices)
        
        # Plusvalías realizadas
        realized = self.get_realized_gains()
        
        # Dividendos (si se incluyen)
        dividends_total = 0.0
        if include_dividends:
            dividends = self.db.get_dividends()
            if dividends:
                for d in dividends:
                    dividends_total += d.net_amount
        
        # Coste de adquisición de POSICIONES ACTUALES (no todas las compras históricas)
        # Esto representa cuánto pagué por lo que tengo ahora
        total_invested = self.get_total_cost_basis()
        
        # Ganancia total = latentes + realizadas + dividendos
        total_gain = unrealized['total_gain'] + realized['net_gain'] + dividends_total
        
        # Rentabilidad sobre el capital actualmente invertido
        total_return_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'total_invested': round(total_invested, 2),
            'current_value': round(unrealized['market_value'], 2),
            'unrealized_gain': round(unrealized['total_gain'], 2),
            'realized_gain': round(realized['net_gain'], 2),
            'dividends': round(dividends_total, 2),
            'total_gain': round(total_gain, 2),
            'total_return_pct': round(total_return_pct, 2)
        }
    
    def get_performance_by_asset(self,
                                 current_prices: Dict[str, float] = None,
                                 sort_by: str = 'unrealized_gain_pct') -> pd.DataFrame:
        """
        Obtiene rentabilidad individual de cada activo.
        
        Args:
            current_prices: Dict con precios actuales
            sort_by: Columna para ordenar ('unrealized_gain_pct', 'unrealized_gain', 'market_value')
        
        Returns:
            DataFrame ordenado por rendimiento
        """
        positions = self.get_current_positions(current_prices=current_prices)
        
        if positions.empty:
            return positions
        
        # Ordenar
        ascending = sort_by in ['unrealized_gain', 'unrealized_gain_pct']  # Mejores primero
        positions = positions.sort_values(sort_by, ascending=False)
        
        return positions.reset_index(drop=True)
    
    # =========================================================================
    # COMPOSICIÓN Y DISTRIBUCIÓN
    # =========================================================================
    
    def get_allocation(self, 
                      by: str = 'asset',
                      current_prices: Dict[str, float] = None) -> pd.DataFrame:
        """
        Calcula la distribución porcentual de la cartera.
        
        Args:
            by: 'asset' (por ticker), 'type' (por tipo de activo)
            current_prices: Dict con precios actuales
        
        Returns:
            DataFrame con:
            - category: Ticker/nombre o tipo de activo
            - market_value: Valor de mercado
            - percentage: Porcentaje de la cartera
        """
        positions = self.get_current_positions(current_prices=current_prices)
        
        if positions.empty:
            return pd.DataFrame(columns=['category', 'market_value', 'percentage'])
        
        total_value = positions['market_value'].sum()
        
        if by == 'asset':
            allocation = positions.groupby('ticker').agg({
                'market_value': 'sum',
                'name': 'first',
                'display_name': 'first'
            }).reset_index()
            allocation['category'] = allocation['display_name']
        elif by == 'type':
            allocation = positions.groupby('asset_type').agg({
                'market_value': 'sum'
            }).reset_index()
            allocation['category'] = allocation['asset_type']
        else:
            allocation = positions.groupby('ticker').agg({
                'market_value': 'sum',
                'display_name': 'first'
            }).reset_index()
            allocation['category'] = allocation['display_name']
        
        allocation['percentage'] = round(allocation['market_value'] / total_value * 100, 2)
        allocation = allocation.sort_values('percentage', ascending=False)
        
        return allocation[['category', 'market_value', 'percentage']].reset_index(drop=True)
    
    # =========================================================================
    # ESTADÍSTICAS Y MÉTRICAS
    # =========================================================================
    
    def get_portfolio_summary(self, current_prices: Dict[str, float] = None) -> Dict:
        """
        Genera resumen completo de la cartera.
        
        Returns:
            Dict con todas las métricas clave
        """
        positions = self.get_current_positions(current_prices=current_prices)
        returns = self.get_total_return(current_prices)
        allocation_by_type = self.get_allocation(by='type', current_prices=current_prices)
        
        # Contar posiciones por tipo
        type_counts = {}
        if not positions.empty:
            type_counts = positions.groupby('asset_type').size().to_dict()
        
        # Top y bottom performers
        top_performer = None
        bottom_performer = None
        if not positions.empty:
            sorted_pos = positions.sort_values('unrealized_gain_pct', ascending=False)
            top_performer = {
                'ticker': sorted_pos.iloc[0]['ticker'],
                'name': sorted_pos.iloc[0]['display_name'],
                'gain_pct': sorted_pos.iloc[0]['unrealized_gain_pct']
            }
            bottom_performer = {
                'ticker': sorted_pos.iloc[-1]['ticker'],
                'name': sorted_pos.iloc[-1]['display_name'],
                'gain_pct': sorted_pos.iloc[-1]['unrealized_gain_pct']
            }
        
        return {
            'total_value': returns['current_value'],
            'total_invested': returns['total_invested'],
            'total_gain': returns['total_gain'],
            'total_return_pct': returns['total_return_pct'],
            'unrealized_gain': returns['unrealized_gain'],
            'realized_gain': returns['realized_gain'],
            'dividends': returns['dividends'],
            'num_positions': len(positions),
            'positions_by_type': type_counts,
            'allocation_by_type': allocation_by_type.to_dict('records'),
            'top_performer': top_performer,
            'bottom_performer': bottom_performer
        }
    
    def get_statistics(self, current_prices: Dict[str, float] = None) -> Dict:
        """
        Calcula estadísticas avanzadas de la cartera.
        
        Returns:
            Dict con estadísticas
        """
        positions = self.get_current_positions(current_prices=current_prices)
        
        if positions.empty:
            return {}
        
        gains = positions['unrealized_gain_pct']
        
        return {
            'mean_return': round(gains.mean(), 2),
            'median_return': round(gains.median(), 2),
            'std_return': round(gains.std(), 2),
            'min_return': round(gains.min(), 2),
            'max_return': round(gains.max(), 2),
            'positive_positions': len(positions[positions['unrealized_gain'] > 0]),
            'negative_positions': len(positions[positions['unrealized_gain'] < 0]),
            'largest_position': positions.iloc[0]['display_name'] if not positions.empty else None,
            'largest_position_pct': round(
                positions.iloc[0]['market_value'] / positions['market_value'].sum() * 100, 2
            ) if not positions.empty else 0
        }
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def get_all_tickers(self) -> List[str]:
        """Retorna lista de todos los tickers con posiciones actuales"""
        positions = self.get_current_positions()
        return positions['ticker'].tolist() if not positions.empty else []
    
    def get_transaction_history(self, 
                               ticker: str = None,
                               limit: int = None) -> pd.DataFrame:
        """
        Obtiene historial de transacciones.
        
        Args:
            ticker: Filtrar por ticker específico
            limit: Número máximo de transacciones
        
        Returns:
            DataFrame con historial
        """
        transactions = self.db.get_transactions(ticker=ticker, limit=limit)
        
        if not transactions:
            return pd.DataFrame()
        
        return self.db.transactions_to_dataframe(transactions)
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def quick_summary(db_path: str = None) -> Dict:
    """
    Función rápida para obtener resumen de cartera.
    
    Uso:
        from src.portfolio import quick_summary
        summary = quick_summary()
        print(f"Valor total: {summary['total_value']}€")
    """
    portfolio = Portfolio(db_path)
    summary = portfolio.get_portfolio_summary()
    portfolio.close()
    return summary


def print_positions(db_path: str = None):
    """
    Imprime posiciones actuales de forma formateada.
    Muestra el NOMBRE del activo (no solo el ticker).
    
    Uso:
        from src.portfolio import print_positions
        print_positions()
    """
    portfolio = Portfolio(db_path)
    positions = portfolio.get_current_positions()
    portfolio.close()
    
    if positions.empty:
        print("No hay posiciones en la cartera.")
        return
    
    print("\n" + "="*80)
    print("📊 POSICIONES ACTUALES")
    print("="*80)
    
    for _, row in positions.iterrows():
        emoji = "📈" if row['unrealized_gain'] >= 0 else "📉"
        # Mostrar nombre (display_name) en lugar de solo ticker
        print(f"\n{emoji} {row['display_name']}")
        print(f"   Ticker: {row['ticker']} | Tipo: {row['asset_type']}")
        print(f"   Cantidad: {row['quantity']:,.4f} | Precio medio: {row['avg_price']:.4f}€")
        print(f"   Valor: {row['market_value']:,.2f}€ | Coste: {row['cost_basis']:,.2f}€")
        print(f"   Ganancia: {row['unrealized_gain']:+,.2f}€ ({row['unrealized_gain_pct']:+.2f}%)")
    
    print("\n" + "="*80)
    print(f"💰 TOTAL: {positions['market_value'].sum():,.2f}€")
    print(f"📈 Ganancia Total: {positions['unrealized_gain'].sum():+,.2f}€")
    print("="*80 + "\n")


def print_realized_gains(year: int = None, db_path: str = None):
    """
    Imprime plusvalías realizadas de forma formateada.
    Muestra el NOMBRE del activo y usa realized_gain_eur correcto.
    
    Uso:
        from src.portfolio import print_realized_gains
        print_realized_gains(2025)
    """
    portfolio = Portfolio(db_path)
    realized = portfolio.get_realized_gains(year=year)
    portfolio.close()
    
    if realized['num_sales'] == 0:
        print("No hay ventas registradas.")
        return
    
    year_str = f" ({year})" if year else ""
    
    print("\n" + "="*80)
    print(f"💵 PLUSVALÍAS REALIZADAS{year_str}")
    print("="*80)
    
    print(f"\n📊 Resumen:")
    print(f"   Ventas: {realized['num_sales']}")
    print(f"   Ganancias: +{realized['total_gains']:,.2f}€")
    print(f"   Pérdidas: -{realized['total_losses']:,.2f}€")
    print(f"   Balance: {realized['net_gain']:+,.2f}€")
    
    print(f"\n📋 Detalle de ventas:")
    print("-" * 80)
    
    for _, row in realized['sales_detail'].iterrows():
        emoji = "✅" if row['gain_eur'] >= 0 else "❌"
        date_str = row['date'].strftime('%Y-%m-%d')
        print(f"{emoji} {date_str} | {row['display_name'][:35]:<35} | {row['gain_eur']:>+10.2f}€")
    
    print("="*80 + "\n")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 TEST DEL MÓDULO PORTFOLIO v2")
    print("="*70)
    
    # Crear instancia
    portfolio = Portfolio()
    
    # Test 1: Posiciones actuales
    print("\n📊 Test 1: Posiciones Actuales")
    positions = portfolio.get_current_positions()
    if positions.empty:
        print("   ⚠️  No hay transacciones en la base de datos")
        print("   💡 Importa transacciones primero con data_loader")
    else:
        print(f"   ✅ {len(positions)} posiciones encontradas")
        # Mostrar con display_name
        print(positions[['display_name', 'quantity', 'avg_price', 'unrealized_gain_pct']].head())
    
    # Test 2: Valor total
    print("\n💰 Test 2: Valor Total")
    total = portfolio.get_total_value()
    print(f"   Valor de cartera: {total:,.2f}€")
    
    # Test 3: Plusvalías realizadas (con realized_gain_eur)
    print("\n💵 Test 3: Plusvalías Realizadas")
    realized = portfolio.get_realized_gains()
    print(f"   Ventas: {realized['num_sales']}")
    print(f"   Ganancias: +{realized['total_gains']:,.2f}€")
    print(f"   Pérdidas: -{realized['total_losses']:,.2f}€")
    print(f"   Neto: {realized['net_gain']:+,.2f}€")
    
    # Test 4: Rentabilidad
    print("\n📈 Test 4: Rentabilidad Total")
    returns = portfolio.get_total_return()
    print(f"   Invertido: {returns['total_invested']:,.2f}€")
    print(f"   Valor actual: {returns['current_value']:,.2f}€")
    print(f"   Ganancia: {returns['total_gain']:+,.2f}€ ({returns['total_return_pct']:+.2f}%)")
    
    # Test 5: Distribución
    print("\n🥧 Test 5: Distribución por Tipo")
    allocation = portfolio.get_allocation(by='type')
    if not allocation.empty:
        for _, row in allocation.iterrows():
            print(f"   {row['category']}: {row['percentage']:.1f}%")
    
    # Test 6: Top/Bottom performers
    print("\n🏆 Test 6: Mejores y Peores")
    perf = portfolio.get_performance_by_asset()
    if not perf.empty:
        print(f"   🥇 Mejor: {perf.iloc[0]['display_name']} ({perf.iloc[0]['unrealized_gain_pct']:+.2f}%)")
        print(f"   🥉 Peor: {perf.iloc[-1]['display_name']} ({perf.iloc[-1]['unrealized_gain_pct']:+.2f}%)")
    
    portfolio.close()
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETADOS")
    print("="*70 + "\n")
