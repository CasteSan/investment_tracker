"""
Market Data Module - Gestión de Precios de Mercado
Investment Tracker

Este módulo gestiona:
- Descarga de precios históricos de los activos de la cartera
- Cache de precios en base de datos
- Cálculo del valor de mercado real de la cartera
- Series temporales para gráficos tipo Investing.com

Autor: Investment Tracker Project
Fecha: Enero 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from src.database import Database
    from src.logger import get_logger
except ImportError:
    from database import Database
    from logger import get_logger

logger = get_logger(__name__)


class MarketDataManager:
    """
    Gestor de datos de mercado para la cartera.

    Permite descargar precios históricos de los activos y calcular
    el valor real de mercado de la cartera en cualquier fecha.

    Uso:
        mdm = MarketDataManager()

        # Descargar precios de todos los activos de la cartera
        mdm.download_portfolio_prices('2024-01-01', '2026-01-06')

        # Obtener valor de mercado de la cartera
        series = mdm.get_portfolio_market_value_series('2024-01-01')

        # Obtener datos estilo Investing.com
        data = mdm.get_investing_style_data('2024-01-01')

        mdm.close()
    """

    # Sufijos de mercados europeos para probar
    EUROPEAN_SUFFIXES = ['.MC', '.PA', '.DE', '.L', '.AS', '.MI', '.SW', '.BR', '.VI']

    def __init__(self, db_path: str = None):
        """
        Inicializa el gestor de datos de mercado.

        Args:
            db_path: Ruta a la base de datos (opcional)
        """
        logger.debug("Inicializando MarketDataManager")
        self.db = Database(db_path) if db_path else Database()
        self._price_cache = {}  # Cache en memoria: {ticker: DataFrame}
        self._failed_tickers = set()  # Cache de tickers sin datos (evita reintentos)
        self._isin_to_ticker = {}  # Cache de ISIN -> ticker encontrado
        logger.info("MarketDataManager inicializado")

    @staticmethod
    def _is_isin(identifier: str) -> bool:
        """
        Detecta si un identificador es un ISIN.

        ISIN format: 2 letras pais + 9 caracteres alfanumericos + 1 digito control
        Ejemplos: IE00BLP5S460, US0378331005, LU0996182563
        """
        if not identifier or len(identifier) != 12:
            return False
        # Primeros 2 caracteres deben ser letras (codigo pais)
        if not identifier[:2].isalpha():
            return False
        # El resto puede ser alfanumerico
        return identifier[2:].isalnum()
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()
        logger.debug("MarketDataManager cerrado")
    
    def clear_price_cache(self, include_failed: bool = False):
        """
        Limpia el cache de precios en memoria.

        Args:
            include_failed: Si True, tambien limpia la lista de tickers fallidos
                           permitiendo reintentar la descarga
        """
        self._price_cache = {}
        self._isin_to_ticker = {}
        if include_failed:
            self._failed_tickers = set()
        logger.debug(f"Cache de precios limpiado (include_failed={include_failed})")
    
    # =========================================================================
    # DESCARGA DE PRECIOS
    # =========================================================================
    
    def get_portfolio_tickers(self) -> List[Dict]:
        """
        Obtiene la lista de tickers únicos de la cartera con sus metadatos.
        
        Returns:
            Lista de dicts con ticker, name, asset_type, currency
        """
        transactions = self.db.get_transactions()
        
        if not transactions:
            return []
        
        tickers = {}
        for t in transactions:
            if t.ticker not in tickers:
                tickers[t.ticker] = {
                    'ticker': t.ticker,
                    'name': t.name or t.ticker,
                    'asset_type': t.asset_type or 'unknown',
                    'currency': t.currency or 'EUR'
                }
        
        return list(tickers.values())
    
    def _search_ticker_for_isin(self, isin: str) -> Optional[str]:
        """
        Intenta encontrar el ticker de Yahoo Finance para un ISIN.

        Args:
            isin: Codigo ISIN del activo

        Returns:
            Ticker encontrado o None
        """
        # Revisar cache primero
        if isin in self._isin_to_ticker:
            return self._isin_to_ticker[isin]

        try:
            # Usar la funcion de busqueda de yfinance
            ticker_obj = yf.Ticker(isin)
            search_result = ticker_obj.info

            if search_result and 'symbol' in search_result:
                found_ticker = search_result['symbol']
                self._isin_to_ticker[isin] = found_ticker
                logger.info(f"ISIN {isin} -> ticker {found_ticker}")
                return found_ticker
        except Exception as e:
            logger.debug(f"Busqueda de ISIN {isin} fallo: {e}")

        return None

    def download_ticker_prices(self,
                               ticker: str,
                               start_date: str,
                               end_date: str = None,
                               save_to_db: bool = True) -> pd.DataFrame:
        """
        Descarga precios históricos de un ticker desde Yahoo Finance.

        Args:
            ticker: Símbolo del activo o ISIN
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (si None, usa hoy)
            save_to_db: Si guardar en base de datos

        Returns:
            DataFrame con columnas: date, close, adj_close

        Nota:
            Para fondos europeos identificados por ISIN, yfinance puede no tener datos.
            El sistema intentara buscar el ticker correspondiente, pero muchos fondos
            mutuos no estan disponibles en Yahoo Finance.
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance no está instalado. Ejecuta: pip install yfinance")

        # Verificar si este ticker ya fallo anteriormente
        if ticker in self._failed_tickers:
            logger.debug(f"Ticker {ticker} en lista de fallidos, saltando")
            return pd.DataFrame()

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            search_ticker = ticker
            data = pd.DataFrame()

            # Si es un ISIN, intentar encontrar el ticker primero
            if self._is_isin(ticker):
                found_ticker = self._search_ticker_for_isin(ticker)
                if found_ticker:
                    search_ticker = found_ticker
                    logger.info(f"Usando ticker {found_ticker} para ISIN {ticker}")

            # Intentar descargar con el ticker (o ticker encontrado)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = yf.download(search_ticker, start=start_date, end=end_date, progress=False)

            # Si no hay datos, intentar con sufijos europeos
            if data.empty and not self._is_isin(ticker):
                for suffix in self.EUROPEAN_SUFFIXES:
                    alt_ticker = ticker + suffix
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        data = yf.download(alt_ticker, start=start_date, end=end_date, progress=False)
                    if not data.empty:
                        logger.info(f"Ticker {ticker} encontrado como {alt_ticker}")
                        break

            if data.empty:
                # Marcar como fallido para no reintentar
                self._failed_tickers.add(ticker)
                if self._is_isin(ticker):
                    logger.warning(f"ISIN {ticker}: sin datos en yfinance (fondo no disponible)")
                else:
                    logger.warning(f"Ticker {ticker}: sin datos en yfinance")
                return pd.DataFrame()
            
            # Procesar datos
            result = pd.DataFrame({
                'date': data.index,
                'close': data['Close'].values.flatten() if len(data['Close'].shape) > 1 else data['Close'].values,
                'adj_close': data['Adj Close'].values.flatten() if 'Adj Close' in data.columns else data['Close'].values.flatten() if len(data['Close'].shape) > 1 else data['Close'].values
            })
            
            result['date'] = pd.to_datetime(result['date'])
            result = result.dropna()
            
            # Guardar en cache
            self._price_cache[ticker] = result.copy()
            
            # Guardar en base de datos si se solicita
            if save_to_db and not result.empty:
                self._save_prices_to_db(ticker, result)
            
            return result
            
        except Exception as e:
            print(f"   ⚠️ Error descargando {ticker}: {e}")
            return pd.DataFrame()
    
    def _save_prices_to_db(self, ticker: str, prices_df: pd.DataFrame):
        """Guarda precios en la tabla asset_prices de la base de datos"""
        for _, row in prices_df.iterrows():
            try:
                self.db.add_asset_price(
                    ticker=ticker,
                    date=row['date'].strftime('%Y-%m-%d'),
                    close_price=float(row['close']),
                    adj_close_price=float(row['adj_close'])
                )
            except:
                pass  # Ignorar duplicados
    
    def download_portfolio_prices(self,
                                  start_date: str,
                                  end_date: str = None,
                                  tickers: List[str] = None) -> Dict[str, int]:
        """
        Descarga precios históricos de todos los activos de la cartera.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            tickers: Lista específica de tickers (si None, usa todos de la cartera)
        
        Returns:
            Dict con {ticker: num_registros_descargados}
        """
        if tickers is None:
            portfolio_tickers = self.get_portfolio_tickers()
            tickers = [t['ticker'] for t in portfolio_tickers]
        
        results = {}
        
        for ticker in tickers:
            print(f"📥 Descargando {ticker}...")
            df = self.download_ticker_prices(ticker, start_date, end_date)
            results[ticker] = len(df)
            
            if len(df) > 0:
                print(f"   ✅ {len(df)} registros")
            else:
                print(f"   ⚠️ Sin datos")
        
        return results
    
    def get_ticker_prices(self,
                         ticker: str,
                         start_date: str = None,
                         end_date: str = None) -> pd.DataFrame:
        """
        Obtiene precios de un ticker (de cache, DB, o descarga).
        
        Args:
            ticker: Símbolo del activo
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)
        
        Returns:
            DataFrame con precios
        """
        # 1. Intentar cache en memoria
        if ticker in self._price_cache:
            df = self._price_cache[ticker].copy()
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]
            if not df.empty:
                return df
        
        # 2. Intentar base de datos
        db_prices = self.db.get_asset_prices(ticker, start_date, end_date)
        if db_prices:
            df = pd.DataFrame([{
                'date': pd.to_datetime(p.date),
                'close': p.close_price,
                'adj_close': p.adj_close_price or p.close_price
            } for p in db_prices])
            
            self._price_cache[ticker] = df.copy()
            return df
        
        # 3. Descargar si no hay datos
        if start_date:
            return self.download_ticker_prices(ticker, start_date, end_date)
        
        return pd.DataFrame()
    
    # =========================================================================
    # CÁLCULO DE VALOR DE MERCADO
    # =========================================================================
    
    def get_portfolio_market_value_series(self,
                                          start_date: str,
                                          end_date: str = None,
                                          include_closed: bool = True) -> pd.DataFrame:
        """
        Calcula el valor de mercado REAL de la cartera en cada fecha.
        
        Usa los precios reales descargados de Yahoo Finance, no solo el coste.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin (si None, usa hoy)
            include_closed: Si incluir ganancias/pérdidas de posiciones cerradas
        
        Returns:
            DataFrame con columnas:
            - date
            - market_value: Valor de mercado de posiciones abiertas
            - cost_basis: Coste de adquisición
            - unrealized_pnl: Ganancia/pérdida latente
            - realized_pnl: Ganancia/pérdida realizada (si include_closed)
            - total_value: market_value + realized_pnl (si include_closed)
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Obtener todas las transacciones
        transactions = self.db.get_transactions(order='ASC')
        
        if not transactions:
            return pd.DataFrame()
        
        # Construir DataFrame de transacciones
        trans_df = pd.DataFrame([{
            'date': pd.to_datetime(t.date),
            'type': t.type,
            'ticker': t.ticker,
            'quantity': float(t.quantity),
            'price': float(t.price),
            'total': float(t.total) if t.total else float(t.quantity * t.price),
            'cost_basis_eur': float(t.cost_basis_eur) if t.cost_basis_eur else None,
            'realized_gain': float(t.realized_gain_eur) if t.realized_gain_eur else 0
        } for t in transactions])
        
        trans_df = trans_df.sort_values('date')
        
        # Obtener tickers únicos
        tickers = trans_df['ticker'].unique().tolist()
        
        # Descargar/obtener precios de todos los tickers
        price_data = {}
        for ticker in tickers:
            prices = self.get_ticker_prices(ticker, start_date, end_date)
            if not prices.empty:
                prices = prices.set_index('date')['adj_close']
                price_data[ticker] = prices
        
        # Crear rango de fechas
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        # Calcular valor de la cartera para cada día
        results = []
        
        for current_date in date_range:
            # Transacciones hasta esta fecha
            day_trans = trans_df[trans_df['date'] <= current_date]
            
            if day_trans.empty:
                continue
            
            # Calcular posiciones abiertas
            positions = {}  # ticker -> {'quantity': x, 'cost': y}
            realized_pnl = 0.0
            
            for _, t in day_trans.iterrows():
                ticker = t['ticker']
                
                if ticker not in positions:
                    positions[ticker] = {'quantity': 0.0, 'cost': 0.0}
                
                if t['type'] == 'buy':
                    positions[ticker]['quantity'] += t['quantity']
                    positions[ticker]['cost'] += t['total']
                
                elif t['type'] == 'sell':
                    if positions[ticker]['quantity'] > 0:
                        sell_ratio = min(t['quantity'] / positions[ticker]['quantity'], 1.0)
                        cost_sold = positions[ticker]['cost'] * sell_ratio
                        positions[ticker]['cost'] -= cost_sold
                        positions[ticker]['quantity'] -= t['quantity']
                        positions[ticker]['quantity'] = max(0, positions[ticker]['quantity'])
                        
                        # Calcular ganancia realizada
                        if t['realized_gain']:
                            realized_pnl += t['realized_gain']
                        else:
                            realized_pnl += (t['total'] - cost_sold)
                
                elif t['type'] == 'transfer_out':
                    if positions[ticker]['quantity'] > 0:
                        transfer_ratio = min(t['quantity'] / positions[ticker]['quantity'], 1.0)
                        positions[ticker]['cost'] -= positions[ticker]['cost'] * transfer_ratio
                        positions[ticker]['quantity'] -= t['quantity']
                        positions[ticker]['quantity'] = max(0, positions[ticker]['quantity'])
                
                elif t['type'] == 'transfer_in':
                    positions[ticker]['quantity'] += t['quantity']
                    cost = t['cost_basis_eur'] if t['cost_basis_eur'] else t['total']
                    positions[ticker]['cost'] += cost
            
            # Calcular valor de mercado de posiciones abiertas
            market_value = 0.0
            cost_basis = 0.0
            has_real_prices = False  # Indica si hay al menos un precio real de mercado

            for ticker, pos in positions.items():
                if pos['quantity'] > 0:
                    cost_basis += pos['cost']

                    # Obtener precio de mercado
                    if ticker in price_data:
                        # Buscar precio más cercano (hacia atrás)
                        price_series = price_data[ticker]
                        valid_prices = price_series[price_series.index <= current_date]

                        if not valid_prices.empty:
                            current_price = valid_prices.iloc[-1]
                            market_value += pos['quantity'] * current_price
                            has_real_prices = True  # Tenemos al menos un precio real
                        else:
                            # Usar coste como fallback
                            market_value += pos['cost']
                    else:
                        # Sin datos de precio, usar coste
                        market_value += pos['cost']
            
            # Solo incluir si hay posiciones
            if cost_basis > 0 or (include_closed and realized_pnl != 0):
                unrealized_pnl = market_value - cost_basis

                result_row = {
                    'date': current_date,
                    'market_value': round(market_value, 2),
                    'cost_basis': round(cost_basis, 2),
                    'unrealized_pnl': round(unrealized_pnl, 2),
                    'has_market_prices': has_real_prices  # True si hay precios reales de mercado
                }

                if include_closed:
                    result_row['realized_pnl'] = round(realized_pnl, 2)
                    result_row['total_value'] = round(market_value + realized_pnl, 2)

                results.append(result_row)
        
        if not results:
            return pd.DataFrame()
        
        return pd.DataFrame(results)
    
    def get_investing_style_data(self,
                                 start_date: str,
                                 end_date: str = None) -> pd.DataFrame:
        """
        Genera datos para gráfico estilo Investing.com.
        
        Muestra tres líneas:
        1. Valor total de la cartera (posiciones abiertas + P&L cerradas)
        2. Valor de posiciones abiertas (valor de mercado)
        3. P&L de posiciones cerradas (ganancias/pérdidas realizadas)
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
        
        Returns:
            DataFrame con columnas:
            - date
            - open_positions_value: Valor de mercado de posiciones abiertas
            - closed_positions_pnl: P&L acumulado de posiciones cerradas
            - total_portfolio_value: Suma de ambos
            - invested_capital: Capital invertido (coste)
        """
        df = self.get_portfolio_market_value_series(start_date, end_date, include_closed=True)
        
        if df.empty:
            return pd.DataFrame()
        
        result = pd.DataFrame({
            'date': df['date'],
            'open_positions_value': df['market_value'],
            'closed_positions_pnl': df['realized_pnl'],
            'total_portfolio_value': df['total_value'],
            'invested_capital': df['cost_basis'],
            'unrealized_pnl': df['unrealized_pnl']
        })
        
        return result
    
    def get_open_positions_only_series(self,
                                       start_date: str,
                                       end_date: str = None) -> pd.DataFrame:
        """
        Calcula SOLO el valor de las posiciones actualmente abiertas.
        
        Útil para comparar el rendimiento de lo que tienes HOY
        sin incluir el ruido de posiciones ya vendidas.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
        
        Returns:
            DataFrame con valor de mercado de posiciones actuales
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Primero, identificar qué posiciones están abiertas HOY
        transactions = self.db.get_transactions(order='ASC')
        
        if not transactions:
            return pd.DataFrame()
        
        # Calcular posiciones actuales
        positions = {}
        for t in transactions:
            ticker = t.ticker
            if ticker not in positions:
                positions[ticker] = 0.0
            
            if t.type == 'buy':
                positions[ticker] += t.quantity
            elif t.type == 'sell':
                positions[ticker] -= t.quantity
            elif t.type == 'transfer_out':
                positions[ticker] -= t.quantity
            elif t.type == 'transfer_in':
                positions[ticker] += t.quantity
        
        # Filtrar solo tickers con posición > 0
        open_tickers = [t for t, qty in positions.items() if qty > 0.0001]
        
        if not open_tickers:
            return pd.DataFrame()
        
        # Obtener transacciones solo de tickers abiertos
        trans_df = pd.DataFrame([{
            'date': pd.to_datetime(t.date),
            'type': t.type,
            'ticker': t.ticker,
            'quantity': float(t.quantity),
            'price': float(t.price),
            'total': float(t.total) if t.total else float(t.quantity * t.price),
            'cost_basis_eur': float(t.cost_basis_eur) if t.cost_basis_eur else None
        } for t in transactions if t.ticker in open_tickers])
        
        if trans_df.empty:
            return pd.DataFrame()
        
        trans_df = trans_df.sort_values('date')
        
        # Obtener precios
        price_data = {}
        for ticker in open_tickers:
            prices = self.get_ticker_prices(ticker, start_date, end_date)
            if not prices.empty:
                prices = prices.set_index('date')['adj_close']
                price_data[ticker] = prices
        
        # Crear rango de fechas
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        results = []
        
        for current_date in date_range:
            day_trans = trans_df[trans_df['date'] <= current_date]
            
            if day_trans.empty:
                continue
            
            # Calcular posiciones
            pos = {}
            for _, t in day_trans.iterrows():
                ticker = t['ticker']
                if ticker not in pos:
                    pos[ticker] = {'quantity': 0.0, 'cost': 0.0}
                
                if t['type'] == 'buy':
                    pos[ticker]['quantity'] += t['quantity']
                    pos[ticker]['cost'] += t['total']
                elif t['type'] == 'sell':
                    if pos[ticker]['quantity'] > 0:
                        ratio = min(t['quantity'] / pos[ticker]['quantity'], 1.0)
                        pos[ticker]['cost'] *= (1 - ratio)
                        pos[ticker]['quantity'] -= t['quantity']
                elif t['type'] == 'transfer_out':
                    if pos[ticker]['quantity'] > 0:
                        ratio = min(t['quantity'] / pos[ticker]['quantity'], 1.0)
                        pos[ticker]['cost'] *= (1 - ratio)
                        pos[ticker]['quantity'] -= t['quantity']
                elif t['type'] == 'transfer_in':
                    pos[ticker]['quantity'] += t['quantity']
                    cost = t['cost_basis_eur'] if t['cost_basis_eur'] else t['total']
                    pos[ticker]['cost'] += cost
            
            # Calcular valor de mercado
            market_value = 0.0
            cost_basis = 0.0
            has_real_prices = False

            for ticker, p in pos.items():
                if p['quantity'] > 0:
                    cost_basis += p['cost']

                    if ticker in price_data:
                        valid_prices = price_data[ticker][price_data[ticker].index <= current_date]
                        if not valid_prices.empty:
                            market_value += p['quantity'] * valid_prices.iloc[-1]
                            has_real_prices = True
                        else:
                            market_value += p['cost']
                    else:
                        market_value += p['cost']

            if cost_basis > 0:
                results.append({
                    'date': current_date,
                    'market_value': round(market_value, 2),
                    'cost_basis': round(cost_basis, 2),
                    'unrealized_pnl': round(market_value - cost_basis, 2),
                    'return_pct': round((market_value / cost_basis - 1) * 100, 2) if cost_basis > 0 else 0,
                    'has_market_prices': has_real_prices
                })
        
        return pd.DataFrame(results)
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def get_download_status(self) -> pd.DataFrame:
        """
        Muestra el estado de descarga de precios para cada ticker.
        
        Returns:
            DataFrame con ticker, tiene_precios, registros, fecha_inicio, fecha_fin
        """
        portfolio_tickers = self.get_portfolio_tickers()
        
        status = []
        for t in portfolio_tickers:
            ticker = t['ticker']
            prices = self.db.get_asset_prices(ticker)
            
            if prices:
                dates = [p.date for p in prices]
                status.append({
                    'ticker': ticker,
                    'name': t['name'],
                    'has_prices': True,
                    'records': len(prices),
                    'start_date': min(dates).strftime('%Y-%m-%d'),
                    'end_date': max(dates).strftime('%Y-%m-%d')
                })
            else:
                status.append({
                    'ticker': ticker,
                    'name': t['name'],
                    'has_prices': False,
                    'records': 0,
                    'start_date': None,
                    'end_date': None
                })
        
        return pd.DataFrame(status)
    
    def clear_price_cache(self, ticker: str = None):
        """
        Limpia la caché de precios.

        Args:
            ticker: Si se especifica, solo limpia ese ticker
        """
        if ticker:
            self._price_cache.pop(ticker, None)
        else:
            self._price_cache.clear()

    def get_latest_price_and_change(self, ticker: str, lookback_days: int = 14) -> Dict:
        """
        Obtiene el precio más reciente y la variación respecto al cierre anterior.

        Lógica robusta para calcular la variación del último día de mercado:
        1. Obtiene el historial de precios (últimos N días)
        2. Si hay al menos 2 días de datos, calcula la variación entre
           el último cierre disponible y el penúltimo cierre

        Esta función siempre devuelve la variación del último día de mercado
        disponible, independientemente de si el mercado está abierto hoy o no.

        Args:
            ticker: Símbolo del activo
            lookback_days: Días hacia atrás para buscar datos (default 14)

        Returns:
            Dict con:
                - current_price: Precio más reciente
                - previous_close: Cierre del día anterior
                - daily_change_pct: Variación porcentual (None si no hay datos)
                - last_date: Fecha del precio más reciente
                - has_data: True si se pudo calcular la variación
        """
        from datetime import timedelta

        result = {
            'current_price': None,
            'previous_close': None,
            'daily_change_pct': None,
            'last_date': None,
            'has_data': False
        }

        try:
            # Calcular rango de fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)

            # Obtener precios del periodo
            prices = self.get_ticker_prices(
                ticker,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )

            if prices.empty or len(prices) < 2:
                logger.debug(f"Ticker {ticker}: datos insuficientes ({len(prices)} registros)")
                return result

            # Ordenar por fecha y obtener los dos últimos días
            prices = prices.sort_values('date', ascending=True)

            # Último día disponible (precio más reciente)
            last_row = prices.iloc[-1]
            current_price = float(last_row['adj_close'])
            last_date = last_row['date']

            # Penúltimo día (cierre anterior)
            prev_row = prices.iloc[-2]
            previous_close = float(prev_row['adj_close'])

            # Calcular variación porcentual
            if previous_close > 0:
                daily_change_pct = ((current_price - previous_close) / previous_close) * 100
            else:
                daily_change_pct = 0.0

            result.update({
                'current_price': current_price,
                'previous_close': previous_close,
                'daily_change_pct': round(daily_change_pct, 4),
                'last_date': last_date,
                'has_data': True
            })

            logger.debug(
                f"Ticker {ticker}: {previous_close:.2f} -> {current_price:.2f} "
                f"({daily_change_pct:+.2f}%)"
            )

        except Exception as e:
            logger.debug(f"Error obteniendo variación para {ticker}: {e}")

        return result


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def download_all_portfolio_prices(start_date: str, end_date: str = None) -> Dict[str, int]:
    """Descarga precios de todos los activos de la cartera"""
    mdm = MarketDataManager()
    result = mdm.download_portfolio_prices(start_date, end_date)
    mdm.close()
    return result


def get_portfolio_value_history(start_date: str, end_date: str = None) -> pd.DataFrame:
    """Obtiene el historial de valor de la cartera"""
    mdm = MarketDataManager()
    result = mdm.get_portfolio_market_value_series(start_date, end_date)
    mdm.close()
    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 TEST DEL MÓDULO MARKET DATA")
    print("="*70)
    
    if not YFINANCE_AVAILABLE:
        print("❌ yfinance no está instalado")
    else:
        mdm = MarketDataManager()
        
        # Test 1: Listar tickers
        print("\n📊 Tickers de la cartera:")
        tickers = mdm.get_portfolio_tickers()
        for t in tickers:
            print(f"   - {t['ticker']}: {t['name']}")
        
        # Test 2: Estado de descargas
        print("\n📥 Estado de precios descargados:")
        status = mdm.get_download_status()
        print(status.to_string() if not status.empty else "   Sin datos")
        
        mdm.close()
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETADO")
    print("="*70 + "\n")
