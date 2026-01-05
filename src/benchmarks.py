"""
Benchmarks Module - Comparación con Índices de Referencia
Sesión 6 del Investment Tracker

Este módulo gestiona:
- Descarga de datos de benchmarks (yfinance)
- Comparación cartera vs índices
- Normalización base 100
- Métricas profesionales de riesgo y rendimiento:
  - Volatilidad, Beta, Alpha
  - Sharpe Ratio, Sortino Ratio
  - Max Drawdown, Calmar Ratio
  - Tracking Error, Information Ratio
  - Value at Risk (VaR)

Autor: Investment Tracker Project
Fecha: Enero 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
import warnings

# Silenciar warnings de yfinance
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️  yfinance no instalado. Ejecuta: pip install yfinance")

try:
    from src.database import Database
    from src.portfolio import Portfolio
except ImportError:
    from database import Database
    from portfolio import Portfolio


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Benchmarks predefinidos
BENCHMARK_SYMBOLS = {
    'SP500': '^GSPC',           # S&P 500
    'IBEX35': '^IBEX',          # IBEX 35
    'EUROSTOXX50': '^STOXX50E', # Euro Stoxx 50
    'MSCI_WORLD': 'URTH',       # iShares MSCI World ETF (proxy)
    'NASDAQ100': '^NDX',        # NASDAQ 100
    'DAX': '^GDAXI',            # DAX alemán
    'FTSE100': '^FTSE',         # FTSE 100
    'NIKKEI225': '^N225',       # Nikkei 225
    'MSCI_EM': 'EEM',           # iShares MSCI Emerging Markets ETF
}

# Tasa libre de riesgo por defecto (para Sharpe Ratio)
DEFAULT_RISK_FREE_RATE = 0.03  # 3% anual

# Días de trading por año (para anualizar métricas)
TRADING_DAYS_PER_YEAR = 252


class BenchmarkComparator:
    """
    Comparador de cartera contra benchmarks de mercado.
    
    Proporciona análisis profesional comparable al de gestores de carteras:
    - Rendimientos relativos (outperformance/underperformance)
    - Métricas de riesgo (volatilidad, beta, VaR)
    - Ratios de rendimiento ajustado (Sharpe, Sortino, Calmar)
    
    Uso básico:
        bc = BenchmarkComparator()
        
        # Descargar datos del S&P 500
        bc.download_benchmark('SP500', '2024-01-01', '2026-01-05')
        
        # Comparar cartera
        bc.print_comparison_summary('SP500')
        
        # Métricas de riesgo
        bc.print_risk_metrics('SP500')
        
        bc.close()
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el comparador de benchmarks.
        
        Args:
            db_path: Ruta a la base de datos (opcional)
        """
        self.db = Database(db_path) if db_path else Database()
        self.portfolio = Portfolio(db_path) if db_path else Portfolio()
        self._portfolio_cache = {}
    
    def close(self):
        """Cierra las conexiones"""
        self.db.close()
        self.portfolio.close()
    
    # =========================================================================
    # GESTIÓN DE DATOS DE BENCHMARKS
    # =========================================================================
    
    def download_benchmark(self,
                          benchmark_name: str,
                          start_date: str,
                          end_date: str = None) -> int:
        """
        Descarga datos de un benchmark desde Yahoo Finance.
        
        Args:
            benchmark_name: Nombre del benchmark ('SP500', 'IBEX35', etc.)
                           o símbolo directo ('^GSPC', '^IBEX')
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (si None, usa hoy)
        
        Returns:
            Número de registros descargados
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance no está instalado. Ejecuta: pip install yfinance")
        
        # Resolver símbolo
        symbol = BENCHMARK_SYMBOLS.get(benchmark_name.upper(), benchmark_name)
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"📥 Descargando {benchmark_name} ({symbol})...")
        
        try:
            # Descargar datos
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                print(f"   ⚠️  No se encontraron datos para {symbol}")
                return 0
            
            # Guardar en base de datos
            count = 0
            for date, row in data.iterrows():
                try:
                    # Usar 'Close' o 'Adj Close'
                    close_price = row['Adj Close'] if 'Adj Close' in row else row['Close']
                    
                    # Manejar el caso de que close_price sea una Serie
                    if hasattr(close_price, 'iloc'):
                        close_price = float(close_price.iloc[0])
                    else:
                        close_price = float(close_price)
                    
                    self.db.add_benchmark_data(
                        benchmark_name=benchmark_name.upper(),
                        date=date.strftime('%Y-%m-%d'),
                        value=close_price
                    )
                    count += 1
                except Exception as e:
                    # Puede fallar si ya existe el registro
                    pass
            
            print(f"   ✅ Descargados {count} registros de {benchmark_name}")
            return count
            
        except Exception as e:
            print(f"   ❌ Error descargando {benchmark_name}: {e}")
            return 0
    
    def load_benchmark_from_csv(self,
                                benchmark_name: str,
                                csv_file: str,
                                date_column: str = 'Date',
                                value_column: str = 'Close') -> int:
        """
        Carga datos de benchmark desde un archivo CSV.
        
        Args:
            benchmark_name: Nombre para identificar el benchmark
            csv_file: Ruta al archivo CSV
            date_column: Nombre de la columna de fecha
            value_column: Nombre de la columna de valor
        
        Returns:
            Número de registros importados
        """
        df = pd.read_csv(csv_file)
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip()
        
        if date_column not in df.columns:
            # Intentar encontrar columna de fecha
            date_cols = [c for c in df.columns if 'date' in c.lower() or 'fecha' in c.lower()]
            if date_cols:
                date_column = date_cols[0]
            else:
                raise ValueError(f"No se encontró columna de fecha. Columnas: {list(df.columns)}")
        
        if value_column not in df.columns:
            # Intentar encontrar columna de valor
            value_cols = [c for c in df.columns if 'close' in c.lower() or 'precio' in c.lower()]
            if value_cols:
                value_column = value_cols[0]
            else:
                raise ValueError(f"No se encontró columna de valor. Columnas: {list(df.columns)}")
        
        count = 0
        for _, row in df.iterrows():
            try:
                date = pd.to_datetime(row[date_column]).strftime('%Y-%m-%d')
                value = float(str(row[value_column]).replace(',', '.').replace(' ', ''))
                
                self.db.add_benchmark_data(
                    benchmark_name=benchmark_name.upper(),
                    date=date,
                    value=value
                )
                count += 1
            except Exception:
                pass
        
        print(f"✅ Importados {count} registros de {benchmark_name}")
        return count
    
    def get_available_benchmarks(self) -> List[Dict]:
        """
        Lista los benchmarks disponibles en la base de datos.
        
        Returns:
            Lista de dicts con nombre, fecha_inicio, fecha_fin, registros
        """
        benchmarks = self.db.get_available_benchmarks()
        
        result = []
        for name in benchmarks:
            data = self.db.get_benchmark_data(name)
            if data:
                dates = [d.date for d in data]
                result.append({
                    'name': name,
                    'start_date': min(dates).strftime('%Y-%m-%d'),
                    'end_date': max(dates).strftime('%Y-%m-%d'),
                    'records': len(data)
                })
        
        return result
    
    def get_benchmark_series(self,
                            benchmark_name: str,
                            start_date: str = None,
                            end_date: str = None) -> pd.Series:
        """
        Obtiene serie temporal de un benchmark.
        
        Returns:
            Series con índice de fechas y valores del benchmark
        """
        data = self.db.get_benchmark_data(
            benchmark_name.upper(),
            start_date=start_date,
            end_date=end_date
        )
        
        if not data:
            return pd.Series(dtype=float)
        
        dates = [d.date for d in data]
        values = [d.value for d in data]
        
        series = pd.Series(values, index=pd.DatetimeIndex(dates), name=benchmark_name)
        return series.sort_index()
    
    # =========================================================================
    # DATOS DE CARTERA
    # =========================================================================
    
    def get_portfolio_series(self,
                            start_date: str = None,
                            end_date: str = None) -> pd.Series:
        """
        Obtiene serie temporal del valor de la cartera.
        
        Para esto necesitamos calcular el valor de la cartera en cada fecha.
        Usamos una aproximación basada en las transacciones.
        
        Returns:
            Series con índice de fechas y valor de la cartera
        """
        # Obtener todas las transacciones ordenadas por fecha
        transactions = self.db.get_transactions(order='ASC')
        
        if not transactions:
            return pd.Series(dtype=float)
        
        # Construir serie de valor de cartera
        # Simplificación: usamos el valor acumulado de compras - ventas + ganancias
        
        df = pd.DataFrame([{
            'date': t.date,
            'type': t.type,
            'total': t.total or (t.quantity * t.price),
            'realized_gain': t.realized_gain_eur or 0
        } for t in transactions])
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calcular valor acumulado
        portfolio_values = []
        cumulative_invested = 0
        cumulative_gains = 0
        
        for date in df['date'].unique():
            day_trans = df[df['date'] == date]
            
            for _, t in day_trans.iterrows():
                if t['type'] == 'buy':
                    cumulative_invested += t['total']
                elif t['type'] == 'sell':
                    cumulative_invested -= t['total']
                    cumulative_gains += t['realized_gain']
            
            # Valor aproximado = invertido + ganancias realizadas
            portfolio_values.append({
                'date': date,
                'value': cumulative_invested + cumulative_gains
            })
        
        result_df = pd.DataFrame(portfolio_values)
        
        if result_df.empty:
            return pd.Series(dtype=float)
        
        series = pd.Series(
            result_df['value'].values,
            index=pd.DatetimeIndex(result_df['date']),
            name='Portfolio'
        )
        
        # Filtrar por fechas si se especifican
        if start_date:
            series = series[series.index >= pd.to_datetime(start_date)]
        if end_date:
            series = series[series.index <= pd.to_datetime(end_date)]
        
        return series
    
    # =========================================================================
    # NORMALIZACIÓN BASE 100
    # =========================================================================
    
    def normalize_to_base_100(self,
                              series: pd.Series,
                              base_date: str = None) -> pd.Series:
        """
        Normaliza una serie temporal a base 100.
        
        Args:
            series: Serie temporal de valores
            base_date: Fecha base (si None, usa primera fecha)
        
        Returns:
            Serie normalizada donde base_date = 100
        """
        if series.empty:
            return series
        
        if base_date:
            base_date = pd.to_datetime(base_date)
            # Encontrar fecha más cercana
            idx = series.index.get_indexer([base_date], method='nearest')[0]
            base_value = series.iloc[idx]
        else:
            base_value = series.iloc[0]
        
        if base_value == 0:
            return series
        
        normalized = (series / base_value) * 100
        normalized.name = f"{series.name}_normalized"
        
        return normalized
    
    # =========================================================================
    # COMPARACIÓN CARTERA VS BENCHMARK
    # =========================================================================
    
    def compare_to_benchmark(self,
                            benchmark_name: str,
                            start_date: str = None,
                            end_date: str = None) -> pd.DataFrame:
        """
        Compara la cartera contra un benchmark.
        
        Args:
            benchmark_name: Nombre del benchmark
            start_date: Fecha inicio
            end_date: Fecha fin
        
        Returns:
            DataFrame con:
            - date
            - portfolio_value, portfolio_normalized
            - benchmark_value, benchmark_normalized
            - outperformance
        """
        # Obtener series
        portfolio = self.get_portfolio_series(start_date, end_date)
        benchmark = self.get_benchmark_series(benchmark_name, start_date, end_date)
        
        if portfolio.empty or benchmark.empty:
            return pd.DataFrame()
        
        # Alinear fechas (usar solo fechas comunes)
        common_dates = portfolio.index.intersection(benchmark.index)
        
        if len(common_dates) == 0:
            # Si no hay fechas comunes, resamplear a frecuencia diaria
            all_dates = portfolio.index.union(benchmark.index)
            portfolio = portfolio.reindex(all_dates, method='ffill')
            benchmark = benchmark.reindex(all_dates, method='ffill')
            common_dates = portfolio.index.intersection(benchmark.index)
        
        portfolio = portfolio.loc[common_dates]
        benchmark = benchmark.loc[common_dates]
        
        # Normalizar a base 100
        portfolio_norm = self.normalize_to_base_100(portfolio)
        benchmark_norm = self.normalize_to_base_100(benchmark)
        
        # Calcular outperformance
        outperformance = portfolio_norm - benchmark_norm
        
        # Crear DataFrame resultado
        result = pd.DataFrame({
            'date': common_dates,
            'portfolio_value': portfolio.values,
            'portfolio_normalized': portfolio_norm.values,
            'benchmark_value': benchmark.values,
            'benchmark_normalized': benchmark_norm.values,
            'outperformance': outperformance.values
        })
        
        result['date'] = pd.to_datetime(result['date'])
        result = result.sort_values('date').reset_index(drop=True)
        
        return result
    
    # =========================================================================
    # CÁLCULO DE RENDIMIENTOS
    # =========================================================================
    
    def calculate_returns(self,
                         benchmark_name: str,
                         start_date: str = None,
                         end_date: str = None) -> Dict:
        """
        Calcula rendimientos de cartera vs benchmark.
        
        Returns:
            Dict con rendimientos y outperformance
        """
        comparison = self.compare_to_benchmark(benchmark_name, start_date, end_date)
        
        if comparison.empty:
            return {'error': 'No hay datos para comparar'}
        
        # Rendimientos totales
        portfolio_start = comparison['portfolio_normalized'].iloc[0]
        portfolio_end = comparison['portfolio_normalized'].iloc[-1]
        portfolio_return = (portfolio_end - portfolio_start) / portfolio_start * 100
        
        benchmark_start = comparison['benchmark_normalized'].iloc[0]
        benchmark_end = comparison['benchmark_normalized'].iloc[-1]
        benchmark_return = (benchmark_end - benchmark_start) / benchmark_start * 100
        
        outperformance = portfolio_return - benchmark_return
        
        # Período
        days = (comparison['date'].iloc[-1] - comparison['date'].iloc[0]).days
        years = days / 365.25
        
        # Rendimientos anualizados (si > 1 año)
        if years >= 1:
            portfolio_annual = ((1 + portfolio_return/100) ** (1/years) - 1) * 100
            benchmark_annual = ((1 + benchmark_return/100) ** (1/years) - 1) * 100
        else:
            portfolio_annual = portfolio_return
            benchmark_annual = benchmark_return
        
        return {
            'period_days': days,
            'period_years': round(years, 2),
            'portfolio_return': round(portfolio_return, 2),
            'benchmark_return': round(benchmark_return, 2),
            'outperformance': round(outperformance, 2),
            'portfolio_annual': round(portfolio_annual, 2),
            'benchmark_annual': round(benchmark_annual, 2),
            'outperformance_annual': round(portfolio_annual - benchmark_annual, 2)
        }
    
    def calculate_daily_returns(self, series: pd.Series) -> pd.Series:
        """Calcula retornos diarios porcentuales"""
        return series.pct_change().dropna() * 100
    
    # =========================================================================
    # MÉTRICAS DE RIESGO
    # =========================================================================
    
    def calculate_volatility(self,
                            series: pd.Series,
                            annualize: bool = True) -> float:
        """
        Calcula la volatilidad (desviación estándar de retornos).
        
        Args:
            series: Serie de precios
            annualize: Si True, anualiza multiplicando por sqrt(252)
        
        Returns:
            Volatilidad (en %)
        """
        returns = self.calculate_daily_returns(series)
        
        if returns.empty:
            return 0.0
        
        vol = returns.std()
        
        if annualize:
            vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        return round(vol, 2)
    
    def calculate_beta(self,
                      benchmark_name: str,
                      start_date: str = None,
                      end_date: str = None) -> float:
        """
        Calcula el Beta de la cartera respecto al benchmark.
        
        Beta = Cov(portfolio, benchmark) / Var(benchmark)
        
        Beta > 1: más volátil que el mercado
        Beta < 1: menos volátil que el mercado
        Beta = 1: igual volatilidad que el mercado
        
        Returns:
            Beta de la cartera
        """
        portfolio = self.get_portfolio_series(start_date, end_date)
        benchmark = self.get_benchmark_series(benchmark_name, start_date, end_date)
        
        if portfolio.empty or benchmark.empty:
            return 0.0
        
        # Alinear y calcular retornos
        common_dates = portfolio.index.intersection(benchmark.index)
        if len(common_dates) < 30:  # Mínimo 30 observaciones
            return 0.0
        
        port_returns = self.calculate_daily_returns(portfolio.loc[common_dates])
        bench_returns = self.calculate_daily_returns(benchmark.loc[common_dates])
        
        # Alinear retornos
        aligned = pd.DataFrame({
            'portfolio': port_returns,
            'benchmark': bench_returns
        }).dropna()
        
        if len(aligned) < 30:
            return 0.0
        
        # Calcular beta
        covariance = aligned['portfolio'].cov(aligned['benchmark'])
        variance = aligned['benchmark'].var()
        
        if variance == 0:
            return 0.0
        
        beta = covariance / variance
        
        return round(beta, 2)
    
    def calculate_alpha(self,
                       benchmark_name: str,
                       risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
                       start_date: str = None,
                       end_date: str = None) -> float:
        """
        Calcula el Alpha de Jensen.
        
        Alpha = Portfolio Return - [Risk Free + Beta * (Benchmark Return - Risk Free)]
        
        Alpha > 0: la cartera genera valor añadido
        Alpha < 0: la cartera destruye valor
        
        Returns:
            Alpha anualizado (en %)
        """
        returns = self.calculate_returns(benchmark_name, start_date, end_date)
        beta = self.calculate_beta(benchmark_name, start_date, end_date)
        
        if 'error' in returns:
            return 0.0
        
        portfolio_return = returns['portfolio_annual'] / 100
        benchmark_return = returns['benchmark_annual'] / 100
        
        expected_return = risk_free_rate + beta * (benchmark_return - risk_free_rate)
        alpha = (portfolio_return - expected_return) * 100
        
        return round(alpha, 2)
    
    def calculate_sharpe_ratio(self,
                              series: pd.Series,
                              risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> float:
        """
        Calcula el Sharpe Ratio.
        
        Sharpe = (Return - Risk Free) / Volatility
        
        Mide el retorno por unidad de riesgo total.
        Sharpe > 1: bueno
        Sharpe > 2: muy bueno
        Sharpe > 3: excelente
        
        Returns:
            Sharpe Ratio anualizado
        """
        returns = self.calculate_daily_returns(series)
        
        if returns.empty or len(returns) < 30:
            return 0.0
        
        # Retorno anualizado
        mean_daily = returns.mean() / 100
        annual_return = (1 + mean_daily) ** TRADING_DAYS_PER_YEAR - 1
        
        # Volatilidad anualizada
        vol = (returns.std() / 100) * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        if vol == 0:
            return 0.0
        
        sharpe = (annual_return - risk_free_rate) / vol
        
        return round(sharpe, 2)
    
    def calculate_sortino_ratio(self,
                               series: pd.Series,
                               risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> float:
        """
        Calcula el Sortino Ratio.
        
        Similar al Sharpe pero solo penaliza la volatilidad negativa (downside).
        
        Sortino = (Return - Risk Free) / Downside Volatility
        
        Returns:
            Sortino Ratio anualizado
        """
        returns = self.calculate_daily_returns(series)
        
        if returns.empty or len(returns) < 30:
            return 0.0
        
        # Retorno anualizado
        mean_daily = returns.mean() / 100
        annual_return = (1 + mean_daily) ** TRADING_DAYS_PER_YEAR - 1
        
        # Downside volatility (solo retornos negativos)
        negative_returns = returns[returns < 0] / 100
        
        if len(negative_returns) == 0:
            return float('inf')  # No hay retornos negativos
        
        downside_vol = negative_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        if downside_vol == 0:
            return 0.0
        
        sortino = (annual_return - risk_free_rate) / downside_vol
        
        return round(sortino, 2)
    
    def calculate_max_drawdown(self, series: pd.Series) -> Dict:
        """
        Calcula el Maximum Drawdown (máxima caída desde pico).
        
        Returns:
            Dict con:
            - max_drawdown: Porcentaje de caída máxima
            - peak_date: Fecha del pico
            - trough_date: Fecha del valle
            - recovery_date: Fecha de recuperación (si aplica)
        """
        if series.empty:
            return {'max_drawdown': 0, 'peak_date': None, 'trough_date': None}
        
        # Calcular pico acumulado
        rolling_max = series.expanding().max()
        
        # Drawdown en cada punto
        drawdown = (series - rolling_max) / rolling_max * 100
        
        # Máximo drawdown
        max_dd = drawdown.min()
        
        # Encontrar fechas
        trough_idx = drawdown.idxmin()
        peak_idx = series[:trough_idx].idxmax()
        
        # Buscar recuperación
        recovery_idx = None
        if trough_idx < series.index[-1]:
            post_trough = series[trough_idx:]
            recovered = post_trough[post_trough >= series[peak_idx]]
            if not recovered.empty:
                recovery_idx = recovered.index[0]
        
        return {
            'max_drawdown': round(max_dd, 2),
            'peak_date': peak_idx.strftime('%Y-%m-%d') if peak_idx else None,
            'trough_date': trough_idx.strftime('%Y-%m-%d') if trough_idx else None,
            'recovery_date': recovery_idx.strftime('%Y-%m-%d') if recovery_idx else None,
            'days_to_trough': (trough_idx - peak_idx).days if peak_idx and trough_idx else None
        }
    
    def calculate_calmar_ratio(self,
                              series: pd.Series,
                              years: float = None) -> float:
        """
        Calcula el Calmar Ratio.
        
        Calmar = Annual Return / |Max Drawdown|
        
        Mide el retorno por unidad de riesgo extremo.
        
        Returns:
            Calmar Ratio
        """
        if series.empty:
            return 0.0
        
        # Retorno anualizado
        returns = self.calculate_daily_returns(series)
        if returns.empty:
            return 0.0
        
        mean_daily = returns.mean() / 100
        annual_return = ((1 + mean_daily) ** TRADING_DAYS_PER_YEAR - 1) * 100
        
        # Max drawdown
        dd = self.calculate_max_drawdown(series)
        max_dd = abs(dd['max_drawdown'])
        
        if max_dd == 0:
            return float('inf')
        
        calmar = annual_return / max_dd
        
        return round(calmar, 2)
    
    def calculate_tracking_error(self,
                                benchmark_name: str,
                                start_date: str = None,
                                end_date: str = None) -> float:
        """
        Calcula el Tracking Error.
        
        Tracking Error = Std(Portfolio Returns - Benchmark Returns)
        
        Mide cuánto se desvía la cartera del benchmark.
        
        Returns:
            Tracking Error anualizado (en %)
        """
        portfolio = self.get_portfolio_series(start_date, end_date)
        benchmark = self.get_benchmark_series(benchmark_name, start_date, end_date)
        
        if portfolio.empty or benchmark.empty:
            return 0.0
        
        # Alinear
        common_dates = portfolio.index.intersection(benchmark.index)
        if len(common_dates) < 30:
            return 0.0
        
        port_returns = self.calculate_daily_returns(portfolio.loc[common_dates])
        bench_returns = self.calculate_daily_returns(benchmark.loc[common_dates])
        
        # Diferencia de retornos
        aligned = pd.DataFrame({
            'portfolio': port_returns,
            'benchmark': bench_returns
        }).dropna()
        
        diff = aligned['portfolio'] - aligned['benchmark']
        
        # Tracking error anualizado
        te = diff.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        return round(te, 2)
    
    def calculate_information_ratio(self,
                                   benchmark_name: str,
                                   start_date: str = None,
                                   end_date: str = None) -> float:
        """
        Calcula el Information Ratio.
        
        IR = Outperformance / Tracking Error
        
        Mide la consistencia del outperformance.
        IR > 0.5: bueno
        IR > 1.0: excelente
        
        Returns:
            Information Ratio
        """
        returns = self.calculate_returns(benchmark_name, start_date, end_date)
        te = self.calculate_tracking_error(benchmark_name, start_date, end_date)
        
        if 'error' in returns or te == 0:
            return 0.0
        
        outperformance = returns['outperformance_annual']
        ir = outperformance / te
        
        return round(ir, 2)
    
    def calculate_var(self,
                     series: pd.Series,
                     confidence: float = 0.95,
                     horizon_days: int = 1) -> Dict:
        """
        Calcula el Value at Risk (VaR).
        
        VaR responde: "Con X% de confianza, no perderemos más de Y€ en Z días"
        
        Args:
            series: Serie de valores de cartera
            confidence: Nivel de confianza (0.95 = 95%)
            horizon_days: Horizonte temporal en días
        
        Returns:
            Dict con VaR en % y en valor absoluto
        """
        returns = self.calculate_daily_returns(series)
        
        if returns.empty:
            return {'var_pct': 0, 'var_value': 0}
        
        # VaR paramétrico (asumiendo normalidad)
        mean = returns.mean()
        std = returns.std()
        
        # Percentil correspondiente al nivel de confianza
        from scipy import stats
        z_score = stats.norm.ppf(1 - confidence)
        
        # VaR para el horizonte especificado
        var_pct = -(mean + z_score * std * np.sqrt(horizon_days))
        
        # Valor actual de la cartera
        current_value = series.iloc[-1]
        var_value = current_value * (var_pct / 100)
        
        return {
            'confidence': confidence * 100,
            'horizon_days': horizon_days,
            'var_pct': round(var_pct, 2),
            'var_value': round(var_value, 2),
            'interpretation': f"Con {confidence*100:.0f}% de confianza, no perderás más de {var_pct:.2f}% ({var_value:.2f}€) en {horizon_days} día(s)"
        }
    
    # =========================================================================
    # RESUMEN COMPLETO DE MÉTRICAS
    # =========================================================================
    
    def get_full_risk_metrics(self,
                             benchmark_name: str,
                             start_date: str = None,
                             end_date: str = None,
                             risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> Dict:
        """
        Calcula todas las métricas de riesgo y rendimiento.
        
        Returns:
            Dict completo con todas las métricas profesionales
        """
        portfolio = self.get_portfolio_series(start_date, end_date)
        benchmark = self.get_benchmark_series(benchmark_name, start_date, end_date)
        
        if portfolio.empty:
            return {'error': 'No hay datos de cartera'}
        
        if benchmark.empty:
            return {'error': f'No hay datos del benchmark {benchmark_name}'}
        
        # Rendimientos
        returns = self.calculate_returns(benchmark_name, start_date, end_date)
        
        # Métricas de cartera
        portfolio_vol = self.calculate_volatility(portfolio)
        portfolio_sharpe = self.calculate_sharpe_ratio(portfolio, risk_free_rate)
        portfolio_sortino = self.calculate_sortino_ratio(portfolio, risk_free_rate)
        portfolio_dd = self.calculate_max_drawdown(portfolio)
        portfolio_calmar = self.calculate_calmar_ratio(portfolio)
        portfolio_var = self.calculate_var(portfolio)
        
        # Métricas de benchmark
        benchmark_vol = self.calculate_volatility(benchmark)
        benchmark_sharpe = self.calculate_sharpe_ratio(benchmark, risk_free_rate)
        benchmark_sortino = self.calculate_sortino_ratio(benchmark, risk_free_rate)
        benchmark_dd = self.calculate_max_drawdown(benchmark)
        
        # Métricas relativas
        beta = self.calculate_beta(benchmark_name, start_date, end_date)
        alpha = self.calculate_alpha(benchmark_name, risk_free_rate, start_date, end_date)
        tracking_error = self.calculate_tracking_error(benchmark_name, start_date, end_date)
        info_ratio = self.calculate_information_ratio(benchmark_name, start_date, end_date)
        
        return {
            'benchmark': benchmark_name,
            'period': {
                'start': start_date or portfolio.index[0].strftime('%Y-%m-%d'),
                'end': end_date or portfolio.index[-1].strftime('%Y-%m-%d'),
                'days': returns.get('period_days', 0),
                'years': returns.get('period_years', 0)
            },
            'returns': {
                'portfolio_total': returns.get('portfolio_return', 0),
                'benchmark_total': returns.get('benchmark_return', 0),
                'outperformance': returns.get('outperformance', 0),
                'portfolio_annual': returns.get('portfolio_annual', 0),
                'benchmark_annual': returns.get('benchmark_annual', 0),
                'outperformance_annual': returns.get('outperformance_annual', 0)
            },
            'risk': {
                'portfolio_volatility': portfolio_vol,
                'benchmark_volatility': benchmark_vol,
                'beta': beta,
                'tracking_error': tracking_error
            },
            'risk_adjusted': {
                'alpha': alpha,
                'portfolio_sharpe': portfolio_sharpe,
                'benchmark_sharpe': benchmark_sharpe,
                'portfolio_sortino': portfolio_sortino,
                'benchmark_sortino': benchmark_sortino,
                'information_ratio': info_ratio,
                'portfolio_calmar': portfolio_calmar
            },
            'drawdown': {
                'portfolio_max_dd': portfolio_dd['max_drawdown'],
                'portfolio_peak': portfolio_dd['peak_date'],
                'portfolio_trough': portfolio_dd['trough_date'],
                'benchmark_max_dd': benchmark_dd['max_drawdown']
            },
            'var': portfolio_var
        }
    
    # =========================================================================
    # EXPORTACIÓN
    # =========================================================================
    
    def export_comparison(self,
                         benchmark_name: str,
                         filepath: str = None,
                         start_date: str = None,
                         end_date: str = None) -> str:
        """
        Exporta la comparación completa a Excel.
        
        Args:
            benchmark_name: Nombre del benchmark
            filepath: Ruta del archivo
            start_date, end_date: Período
        
        Returns:
            Ruta del archivo generado
        """
        if filepath is None:
            filepath = f'data/exports/benchmark_comparison_{benchmark_name}.xlsx'
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Obtener datos
        comparison = self.compare_to_benchmark(benchmark_name, start_date, end_date)
        metrics = self.get_full_risk_metrics(benchmark_name, start_date, end_date)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            
            # Hoja 1: Datos de comparación
            if not comparison.empty:
                comparison.to_excel(writer, sheet_name='Datos', index=False)
            
            # Hoja 2: Métricas de rendimiento
            returns_data = {
                'Métrica': [
                    'Período (días)',
                    'Período (años)',
                    '',
                    'Rentabilidad Cartera',
                    'Rentabilidad Benchmark',
                    'Outperformance',
                    '',
                    'Rentabilidad Anual Cartera',
                    'Rentabilidad Anual Benchmark',
                    'Outperformance Anual'
                ],
                'Valor': [
                    metrics['period']['days'],
                    metrics['period']['years'],
                    '',
                    f"{metrics['returns']['portfolio_total']}%",
                    f"{metrics['returns']['benchmark_total']}%",
                    f"{metrics['returns']['outperformance']}%",
                    '',
                    f"{metrics['returns']['portfolio_annual']}%",
                    f"{metrics['returns']['benchmark_annual']}%",
                    f"{metrics['returns']['outperformance_annual']}%"
                ]
            }
            pd.DataFrame(returns_data).to_excel(writer, sheet_name='Rendimientos', index=False)
            
            # Hoja 3: Métricas de riesgo
            risk_data = {
                'Métrica': [
                    'VOLATILIDAD',
                    'Cartera',
                    'Benchmark',
                    '',
                    'MÉTRICAS RELATIVAS',
                    'Beta',
                    'Alpha',
                    'Tracking Error',
                    'Information Ratio',
                    '',
                    'RATIOS AJUSTADOS',
                    'Sharpe Ratio Cartera',
                    'Sharpe Ratio Benchmark',
                    'Sortino Ratio Cartera',
                    'Calmar Ratio Cartera',
                    '',
                    'DRAWDOWN',
                    'Max Drawdown Cartera',
                    'Max Drawdown Benchmark',
                    '',
                    'VALUE AT RISK (95%, 1 día)',
                    'VaR %',
                    'VaR €'
                ],
                'Valor': [
                    '',
                    f"{metrics['risk']['portfolio_volatility']}%",
                    f"{metrics['risk']['benchmark_volatility']}%",
                    '',
                    '',
                    metrics['risk']['beta'],
                    f"{metrics['risk_adjusted']['alpha']}%",
                    f"{metrics['risk']['tracking_error']}%",
                    metrics['risk_adjusted']['information_ratio'],
                    '',
                    '',
                    metrics['risk_adjusted']['portfolio_sharpe'],
                    metrics['risk_adjusted']['benchmark_sharpe'],
                    metrics['risk_adjusted']['portfolio_sortino'],
                    metrics['risk_adjusted']['portfolio_calmar'],
                    '',
                    '',
                    f"{metrics['drawdown']['portfolio_max_dd']}%",
                    f"{metrics['drawdown']['benchmark_max_dd']}%",
                    '',
                    '',
                    f"{metrics['var']['var_pct']}%",
                    f"{metrics['var']['var_value']}€"
                ]
            }
            pd.DataFrame(risk_data).to_excel(writer, sheet_name='Riesgo', index=False)
        
        print(f"✅ Comparación exportada a: {filepath}")
        return str(filepath)
    
    # =========================================================================
    # FUNCIONES DE IMPRESIÓN
    # =========================================================================
    
    def print_available_benchmarks(self):
        """Imprime los benchmarks disponibles"""
        benchmarks = self.get_available_benchmarks()
        
        print("\n" + "="*70)
        print("📊 BENCHMARKS DISPONIBLES")
        print("="*70)
        
        if not benchmarks:
            print("\n   No hay benchmarks cargados.")
            print("\n   Benchmarks predefinidos para descargar:")
            for name, symbol in BENCHMARK_SYMBOLS.items():
                print(f"      {name}: {symbol}")
            print("\n   Usa: bc.download_benchmark('SP500', '2024-01-01')")
        else:
            print(f"\n   {'Nombre':<15} {'Desde':<12} {'Hasta':<12} {'Registros':>10}")
            print(f"   {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
            for b in benchmarks:
                print(f"   {b['name']:<15} {b['start_date']:<12} {b['end_date']:<12} {b['records']:>10}")
        
        print("\n" + "="*70)
    
    def print_comparison_summary(self,
                                benchmark_name: str,
                                start_date: str = None,
                                end_date: str = None):
        """Imprime resumen de comparación cartera vs benchmark"""
        metrics = self.get_full_risk_metrics(benchmark_name, start_date, end_date)
        
        if 'error' in metrics:
            print(f"\n❌ {metrics['error']}")
            return
        
        ret = metrics['returns']
        risk = metrics['risk']
        
        print("\n" + "="*70)
        print(f"📊 COMPARACIÓN: Mi Cartera vs {benchmark_name}")
        print("="*70)
        print(f"   Período: {metrics['period']['start']} → {metrics['period']['end']}")
        print(f"            ({metrics['period']['days']} días / {metrics['period']['years']} años)")
        
        print(f"\n📈 RENDIMIENTOS")
        print("-"*50)
        print(f"   {'Mi Cartera:':<25} {ret['portfolio_total']:>+8.2f}%")
        print(f"   {benchmark_name + ':':<25} {ret['benchmark_total']:>+8.2f}%")
        
        emoji = "✅" if ret['outperformance'] > 0 else "❌"
        print(f"   {'Outperformance:':<25} {ret['outperformance']:>+8.2f}% {emoji}")
        
        if metrics['period']['years'] >= 1:
            print(f"\n   Anualizados:")
            print(f"   {'Mi Cartera:':<25} {ret['portfolio_annual']:>+8.2f}%")
            print(f"   {benchmark_name + ':':<25} {ret['benchmark_annual']:>+8.2f}%")
        
        print(f"\n📉 RIESGO")
        print("-"*50)
        print(f"   {'Volatilidad Cartera:':<25} {risk['portfolio_volatility']:>8.2f}% anual")
        print(f"   {'Volatilidad ' + benchmark_name + ':':<25} {risk['benchmark_volatility']:>8.2f}% anual")
        print(f"   {'Beta:':<25} {risk['beta']:>8.2f}")
        print(f"   {'Tracking Error:':<25} {risk['tracking_error']:>8.2f}%")
        
        print("\n" + "="*70)
    
    def print_risk_metrics(self,
                          benchmark_name: str,
                          start_date: str = None,
                          end_date: str = None):
        """Imprime métricas completas de riesgo"""
        metrics = self.get_full_risk_metrics(benchmark_name, start_date, end_date)
        
        if 'error' in metrics:
            print(f"\n❌ {metrics['error']}")
            return
        
        ra = metrics['risk_adjusted']
        dd = metrics['drawdown']
        var = metrics['var']
        
        print("\n" + "="*70)
        print(f"📊 MÉTRICAS DE RIESGO PROFESIONALES")
        print(f"   Benchmark: {benchmark_name}")
        print("="*70)
        
        print(f"\n📈 RATIOS DE RENDIMIENTO AJUSTADO")
        print("-"*50)
        print(f"   {'Alpha (Jensen):':<30} {ra['alpha']:>+8.2f}%")
        
        # Sharpe con interpretación
        sharpe = ra['portfolio_sharpe']
        if sharpe >= 2:
            sharpe_eval = "Excelente 🌟"
        elif sharpe >= 1:
            sharpe_eval = "Bueno ✅"
        elif sharpe >= 0:
            sharpe_eval = "Aceptable 🆗"
        else:
            sharpe_eval = "Malo ❌"
        print(f"   {'Sharpe Ratio Cartera:':<30} {sharpe:>8.2f} ({sharpe_eval})")
        print(f"   {'Sharpe Ratio ' + benchmark_name + ':':<30} {ra['benchmark_sharpe']:>8.2f}")
        
        print(f"\n   {'Sortino Ratio Cartera:':<30} {ra['portfolio_sortino']:>8.2f}")
        print(f"   {'Calmar Ratio Cartera:':<30} {ra['portfolio_calmar']:>8.2f}")
        
        # Information Ratio
        ir = ra['information_ratio']
        if ir > 1:
            ir_eval = "Excelente 🌟"
        elif ir > 0.5:
            ir_eval = "Bueno ✅"
        elif ir > 0:
            ir_eval = "Aceptable 🆗"
        else:
            ir_eval = "Negativo ❌"
        print(f"   {'Information Ratio:':<30} {ir:>8.2f} ({ir_eval})")
        
        print(f"\n⬇️  DRAWDOWN MÁXIMO")
        print("-"*50)
        print(f"   {'Cartera:':<30} {dd['portfolio_max_dd']:>8.2f}%")
        if dd['portfolio_peak']:
            print(f"      Pico: {dd['portfolio_peak']} → Valle: {dd['portfolio_trough']}")
        print(f"   {benchmark_name + ':':<30} {dd['benchmark_max_dd']:>8.2f}%")
        
        print(f"\n⚠️  VALUE AT RISK (VaR)")
        print("-"*50)
        print(f"   Nivel de confianza: {var['confidence']:.0f}%")
        print(f"   Horizonte: {var['horizon_days']} día(s)")
        print(f"   VaR: {var['var_pct']:.2f}% ({var['var_value']:.2f}€)")
        print(f"\n   📋 {var['interpretation']}")
        
        # Beta con interpretación
        beta = metrics['risk']['beta']
        print(f"\n📊 INTERPRETACIÓN DEL BETA ({beta:.2f})")
        print("-"*50)
        if beta > 1.2:
            print("   Tu cartera es MÁS VOLÁTIL que el mercado.")
            print("   Sube más cuando el mercado sube, pero cae más cuando cae.")
        elif beta < 0.8:
            print("   Tu cartera es MENOS VOLÁTIL que el mercado.")
            print("   Más defensiva, protege en caídas pero gana menos en subidas.")
        else:
            print("   Tu cartera tiene VOLATILIDAD SIMILAR al mercado.")
            print("   Se mueve aproximadamente igual que el benchmark.")
        
        print("\n" + "="*70)


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def quick_comparison(benchmark: str = 'SP500', period_years: int = 1):
    """Comparación rápida con un benchmark"""
    bc = BenchmarkComparator()
    
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=period_years*365)).strftime('%Y-%m-%d')
    
    # Verificar si hay datos del benchmark
    available = bc.get_available_benchmarks()
    if benchmark.upper() not in [b['name'] for b in available]:
        print(f"📥 Descargando datos de {benchmark}...")
        bc.download_benchmark(benchmark, start, end)
    
    bc.print_comparison_summary(benchmark, start, end)
    bc.print_risk_metrics(benchmark, start, end)
    
    bc.close()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 TEST DEL MÓDULO BENCHMARKS")
    print("="*70)
    
    bc = BenchmarkComparator()
    
    # Test 1: Listar benchmarks disponibles
    print("\n📊 Test 1: Benchmarks disponibles")
    bc.print_available_benchmarks()
    
    # Test 2: Descargar benchmark si hay internet
    if YFINANCE_AVAILABLE:
        print("\n📥 Test 2: Descargando S&P 500 (último año)...")
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        count = bc.download_benchmark('SP500', start, end)
        
        if count > 0:
            # Test 3: Comparación
            print("\n📊 Test 3: Comparación con S&P 500")
            bc.print_comparison_summary('SP500', start, end)
            
            # Test 4: Métricas de riesgo
            print("\n📈 Test 4: Métricas de riesgo")
            bc.print_risk_metrics('SP500', start, end)
    
    bc.close()
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETADOS")
    print("="*70 + "\n")
