"""
Dividends Module - Gestión de Dividendos
Sesión 5 del Investment Tracker

Este módulo gestiona:
- Registro de dividendos (bruto, neto, retenciones)
- Tracking de fechas ex-dividendo
- Cálculo de Yield on Cost (YOC)
- Calendario de cobros
- Proyección de dividendos futuros
- Integración con portfolio y tax_calculator

Autor: Investment Tracker Project
Fecha: Enero 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from pathlib import Path
from collections import defaultdict
from calendar import month_abbr

try:
    from src.database import Database
except ImportError:
    from database import Database


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Retención estándar en España para dividendos
DEFAULT_WITHHOLDING_RATE = 0.19  # 19%

# Frecuencias de pago comunes
PAYMENT_FREQUENCIES = {
    'monthly': 12,
    'quarterly': 4,
    'semi-annual': 2,
    'annual': 1,
    'irregular': 0
}


class DividendManager:
    """
    Gestor de dividendos para el portfolio.
    
    Permite registrar, consultar y analizar dividendos cobrados,
    calcular yields, y proyectar ingresos futuros.
    
    Uso básico:
        dm = DividendManager()
        
        # Registrar dividendo
        dm.add_dividend('TEF', gross=0.30, net=0.243, date='2025-06-15')
        
        # Ver resumen
        dm.print_dividend_summary(2025)
        
        # Calcular yield
        yields = dm.get_dividend_yield('TEF')
        
        dm.close()
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el gestor de dividendos.
        
        Args:
            db_path: Ruta a la base de datos (opcional)
        """
        self.db = Database(db_path) if db_path else Database()
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()
    
    # =========================================================================
    # CRUD DE DIVIDENDOS
    # =========================================================================
    
    def add_dividend(self,
                    ticker: str,
                    gross_amount: float,
                    net_amount: float = None,
                    date: Union[str, datetime] = None,
                    name: str = None,
                    currency: str = 'EUR',
                    ex_date: Union[str, datetime] = None,
                    payment_type: str = 'ordinary',
                    notes: str = None) -> int:
        """
        Registra un nuevo dividendo.
        
        Args:
            ticker: Símbolo del activo
            gross_amount: Importe bruto
            net_amount: Importe neto (si None, calcula con retención 19%)
            date: Fecha de cobro (si None, usa hoy)
            name: Nombre del activo (opcional)
            currency: Divisa (EUR, USD, etc.)
            ex_date: Fecha ex-dividendo (opcional)
            payment_type: 'ordinary', 'special', 'return_of_capital'
            notes: Notas adicionales
        
        Returns:
            ID del dividendo creado
        """
        # Procesar fecha
        if date is None:
            date = datetime.now()
        elif isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        # Calcular neto si no se proporciona
        if net_amount is None:
            net_amount = gross_amount * (1 - DEFAULT_WITHHOLDING_RATE)
        
        # Calcular retención
        withholding_tax = gross_amount - net_amount
        
        # Procesar ex_date
        if ex_date and isinstance(ex_date, str):
            ex_date = datetime.strptime(ex_date, '%Y-%m-%d')
        
        # Preparar datos
        dividend_data = {
            'ticker': ticker.upper(),
            'name': name,
            'date': date.strftime('%Y-%m-%d'),
            'gross_amount': gross_amount,
            'net_amount': net_amount,
            'withholding_tax': withholding_tax,
            'currency': currency,
            'notes': notes
        }
        
        # Añadir campos opcionales si el modelo los soporta
        # (ex_date y payment_type se guardan en notes si no hay columnas)
        extra_info = []
        if ex_date:
            extra_info.append(f"Ex-date: {ex_date.strftime('%Y-%m-%d')}")
        if payment_type != 'ordinary':
            extra_info.append(f"Tipo: {payment_type}")
        
        if extra_info:
            existing_notes = notes or ''
            dividend_data['notes'] = f"{existing_notes} [{', '.join(extra_info)}]".strip()
        
        # Guardar en DB
        dividend_id = self.db.add_dividend(dividend_data)
        
        return dividend_id
    
    def update_dividend(self, dividend_id: int, **kwargs) -> bool:
        """
        Actualiza un dividendo existente.
        
        Args:
            dividend_id: ID del dividendo
            **kwargs: Campos a actualizar
        
        Returns:
            True si se actualizó correctamente
        """
        return self.db.update_dividend(dividend_id, kwargs)
    
    def delete_dividend(self, dividend_id: int) -> bool:
        """
        Elimina un dividendo.
        
        Args:
            dividend_id: ID del dividendo
        
        Returns:
            True si se eliminó correctamente
        """
        return self.db.delete_dividend(dividend_id)
    
    def get_dividend(self, dividend_id: int) -> Optional[Dict]:
        """
        Obtiene un dividendo por ID.
        
        Args:
            dividend_id: ID del dividendo
        
        Returns:
            Dict con datos del dividendo o None
        """
        dividend = self.db.get_dividend_by_id(dividend_id)
        if dividend:
            return self._dividend_to_dict(dividend)
        return None
    
    def _dividend_to_dict(self, dividend) -> Dict:
        """Convierte objeto Dividend a diccionario"""
        return {
            'id': dividend.id,
            'ticker': dividend.ticker,
            'name': dividend.name,
            'date': dividend.date.strftime('%Y-%m-%d') if dividend.date else None,
            'gross_amount': dividend.gross_amount,
            'net_amount': dividend.net_amount,
            'withholding_tax': dividend.withholding_tax,
            'currency': getattr(dividend, 'currency', 'EUR'),
            'notes': dividend.notes
        }
    
    # =========================================================================
    # CONSULTAS Y FILTROS
    # =========================================================================
    
    def get_dividends(self,
                     ticker: str = None,
                     year: int = None,
                     start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
        """
        Obtiene dividendos con filtros opcionales.
        
        Args:
            ticker: Filtrar por ticker
            year: Filtrar por año
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
        
        Returns:
            DataFrame con dividendos
        """
        dividends = self.db.get_dividends(
            ticker=ticker,
            year=year,
            start_date=start_date,
            end_date=end_date
        )
        
        if not dividends:
            return pd.DataFrame()
        
        data = [self._dividend_to_dict(d) for d in dividends]
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
        
        return df.reset_index(drop=True)
    
    def get_dividends_by_ticker(self, ticker: str) -> pd.DataFrame:
        """Obtiene todos los dividendos de un activo"""
        return self.get_dividends(ticker=ticker)
    
    def get_dividends_by_year(self, year: int) -> pd.DataFrame:
        """Obtiene todos los dividendos de un año"""
        return self.get_dividends(year=year)
    
    # =========================================================================
    # ANÁLISIS Y MÉTRICAS
    # =========================================================================
    
    def get_total_dividends(self, year: int = None) -> Dict:
        """
        Calcula totales de dividendos.
        
        Args:
            year: Año específico (None = todo el historial)
        
        Returns:
            Dict con totales
        """
        df = self.get_dividends(year=year)
        
        if df.empty:
            return {
                'year': year,
                'count': 0,
                'total_gross': 0.0,
                'total_net': 0.0,
                'total_withholding': 0.0,
                'avg_withholding_rate': 0.0
            }
        
        total_gross = df['gross_amount'].sum()
        total_net = df['net_amount'].sum()
        total_withholding = df['withholding_tax'].sum()
        
        avg_rate = (total_withholding / total_gross * 100) if total_gross > 0 else 0
        
        return {
            'year': year,
            'count': len(df),
            'total_gross': round(total_gross, 2),
            'total_net': round(total_net, 2),
            'total_withholding': round(total_withholding, 2),
            'avg_withholding_rate': round(avg_rate, 2)
        }
    
    def get_dividends_by_asset(self, year: int = None) -> pd.DataFrame:
        """
        Desglose de dividendos por activo.
        
        Args:
            year: Año específico (None = todo el historial)
        
        Returns:
            DataFrame con totales por activo
        """
        df = self.get_dividends(year=year)
        
        if df.empty:
            return pd.DataFrame()
        
        # Agrupar por ticker
        grouped = df.groupby(['ticker', 'name']).agg({
            'gross_amount': 'sum',
            'net_amount': 'sum',
            'withholding_tax': 'sum',
            'id': 'count'
        }).reset_index()
        
        grouped.columns = ['ticker', 'name', 'gross', 'net', 'withholding', 'payments']
        
        # Calcular porcentaje del total
        total_gross = grouped['gross'].sum()
        grouped['pct_of_total'] = (grouped['gross'] / total_gross * 100).round(2)
        
        # Ordenar por gross descendente
        grouped = grouped.sort_values('gross', ascending=False)
        
        return grouped.reset_index(drop=True)
    
    def get_dividend_yield(self, ticker: str) -> Dict:
        """
        Calcula el dividend yield de un activo.
        
        YOC (Yield on Cost) = Dividendos anuales / Coste de adquisición
        
        Args:
            ticker: Símbolo del activo
        
        Returns:
            Dict con métricas de yield
        """
        # Obtener dividendos del último año
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        df = self.get_dividends(ticker=ticker, start_date=one_year_ago)
        
        annual_dividends = df['gross_amount'].sum() if not df.empty else 0
        annual_dividends_net = df['net_amount'].sum() if not df.empty else 0
        
        # Obtener coste de adquisición desde portfolio
        try:
            from src.portfolio import Portfolio
        except ImportError:
            from portfolio import Portfolio
        
        portfolio = Portfolio()
        positions = portfolio.get_current_positions()
        portfolio.close()
        
        position = positions[positions['ticker'] == ticker.upper()]
        
        if position.empty:
            return {
                'ticker': ticker,
                'error': 'No hay posición de este activo',
                'annual_dividends_gross': round(annual_dividends, 2),
                'annual_dividends_net': round(annual_dividends_net, 2),
                'yoc_gross': 0,
                'yoc_net': 0
            }
        
        cost_basis = position['cost_basis'].values[0]
        quantity = position['quantity'].values[0]
        
        # Calcular yields
        yoc_gross = (annual_dividends / cost_basis * 100) if cost_basis > 0 else 0
        yoc_net = (annual_dividends_net / cost_basis * 100) if cost_basis > 0 else 0
        
        # Dividendo por acción
        dps = annual_dividends / quantity if quantity > 0 else 0
        
        return {
            'ticker': ticker,
            'name': position['name'].values[0] if 'name' in position.columns else ticker,
            'quantity': quantity,
            'cost_basis': round(cost_basis, 2),
            'annual_dividends_gross': round(annual_dividends, 2),
            'annual_dividends_net': round(annual_dividends_net, 2),
            'dividend_per_share': round(dps, 4),
            'yoc_gross': round(yoc_gross, 2),
            'yoc_net': round(yoc_net, 2),
            'payments_last_year': len(df)
        }
    
    def get_portfolio_yield(self) -> Dict:
        """
        Calcula el yield medio de toda la cartera.
        
        Returns:
            Dict con métricas de yield del portfolio
        """
        # Obtener coste total de la cartera
        try:
            from src.portfolio import Portfolio
        except ImportError:
            from portfolio import Portfolio
        
        portfolio = Portfolio()
        total_cost = portfolio.get_total_cost_basis()
        positions = portfolio.get_current_positions()
        portfolio.close()
        
        # Dividendos del último año
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        df = self.get_dividends(start_date=one_year_ago)
        
        annual_gross = df['gross_amount'].sum() if not df.empty else 0
        annual_net = df['net_amount'].sum() if not df.empty else 0
        
        # Calcular yield
        yoc_gross = (annual_gross / total_cost * 100) if total_cost > 0 else 0
        yoc_net = (annual_net / total_cost * 100) if total_cost > 0 else 0
        
        # Activos que pagan dividendos
        if not df.empty:
            dividend_payers = df['ticker'].nunique()
        else:
            dividend_payers = 0
        
        return {
            'total_cost_basis': round(total_cost, 2),
            'total_positions': len(positions),
            'dividend_payers': dividend_payers,
            'annual_dividends_gross': round(annual_gross, 2),
            'annual_dividends_net': round(annual_net, 2),
            'portfolio_yoc_gross': round(yoc_gross, 2),
            'portfolio_yoc_net': round(yoc_net, 2)
        }
    
    def get_top_dividend_payers(self, n: int = 10, year: int = None) -> pd.DataFrame:
        """
        Obtiene los activos que más dividendos generan.
        
        Args:
            n: Número de activos a mostrar
            year: Año específico
        
        Returns:
            DataFrame con top pagadores
        """
        df = self.get_dividends_by_asset(year=year)
        
        if df.empty:
            return pd.DataFrame()
        
        return df.head(n)
    
    # =========================================================================
    # CALENDARIO Y PROYECCIONES
    # =========================================================================
    
    def get_dividend_calendar(self, year: int = None) -> pd.DataFrame:
        """
        Genera calendario de dividendos por mes.
        
        Args:
            year: Año (None = año actual)
        
        Returns:
            DataFrame con dividendos por mes
        """
        if year is None:
            year = datetime.now().year
        
        df = self.get_dividends(year=year)
        
        if df.empty:
            # Retornar calendario vacío
            months = list(range(1, 13))
            return pd.DataFrame({
                'month': months,
                'month_name': [month_abbr[m] for m in months],
                'gross': [0.0] * 12,
                'net': [0.0] * 12,
                'payments': [0] * 12
            })
        
        # Agrupar por mes
        df['month'] = df['date'].dt.month
        
        monthly = df.groupby('month').agg({
            'gross_amount': 'sum',
            'net_amount': 'sum',
            'id': 'count'
        }).reset_index()
        
        monthly.columns = ['month', 'gross', 'net', 'payments']
        
        # Completar meses faltantes
        all_months = pd.DataFrame({'month': range(1, 13)})
        monthly = all_months.merge(monthly, on='month', how='left').fillna(0)
        
        monthly['month_name'] = monthly['month'].apply(lambda m: month_abbr[int(m)])
        monthly['gross'] = monthly['gross'].round(2)
        monthly['net'] = monthly['net'].round(2)
        monthly['payments'] = monthly['payments'].astype(int)
        
        return monthly
    
    def get_monthly_income(self, year: int = None) -> pd.DataFrame:
        """
        Ingresos por dividendos por mes (alias de get_dividend_calendar).
        """
        return self.get_dividend_calendar(year)
    
    def estimate_annual_dividends(self) -> Dict:
        """
        Estima dividendos anuales basado en historial.
        
        Proyecta dividendos para los próximos 12 meses basándose
        en los pagos del último año.
        
        Returns:
            Dict con estimación
        """
        # Dividendos del último año
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        df = self.get_dividends(start_date=one_year_ago)
        
        if df.empty:
            return {
                'estimated_annual_gross': 0,
                'estimated_annual_net': 0,
                'confidence': 'low',
                'basis': 'No hay historial de dividendos'
            }
        
        # Calcular totales del último año
        annual_gross = df['gross_amount'].sum()
        annual_net = df['net_amount'].sum()
        
        # Analizar frecuencia de pagos por activo
        by_ticker = df.groupby('ticker').agg({
            'gross_amount': ['sum', 'count', 'mean']
        }).reset_index()
        by_ticker.columns = ['ticker', 'total', 'payments', 'avg_payment']
        
        # Determinar confianza basada en regularidad
        if len(df) >= 4:
            confidence = 'high'
            basis = f'Basado en {len(df)} pagos del último año'
        elif len(df) >= 2:
            confidence = 'medium'
            basis = f'Basado en {len(df)} pagos del último año'
        else:
            confidence = 'low'
            basis = f'Solo {len(df)} pago(s) registrado(s)'
        
        return {
            'estimated_annual_gross': round(annual_gross, 2),
            'estimated_annual_net': round(annual_net, 2),
            'estimated_monthly_gross': round(annual_gross / 12, 2),
            'estimated_monthly_net': round(annual_net / 12, 2),
            'confidence': confidence,
            'basis': basis,
            'payers': len(by_ticker)
        }
    
    def get_dividend_frequency(self, ticker: str) -> Dict:
        """
        Detecta la frecuencia de pago de dividendos de un activo.
        
        Args:
            ticker: Símbolo del activo
        
        Returns:
            Dict con frecuencia detectada
        """
        df = self.get_dividends(ticker=ticker)
        
        if df.empty or len(df) < 2:
            return {
                'ticker': ticker,
                'frequency': 'unknown',
                'payments_per_year': 0,
                'avg_days_between': None
            }
        
        # Calcular días entre pagos
        df = df.sort_values('date')
        df['days_since_last'] = df['date'].diff().dt.days
        
        avg_days = df['days_since_last'].mean()
        
        # Determinar frecuencia
        if avg_days is None or pd.isna(avg_days):
            frequency = 'unknown'
            payments_per_year = 0
        elif avg_days <= 45:
            frequency = 'monthly'
            payments_per_year = 12
        elif avg_days <= 120:
            frequency = 'quarterly'
            payments_per_year = 4
        elif avg_days <= 200:
            frequency = 'semi-annual'
            payments_per_year = 2
        elif avg_days <= 400:
            frequency = 'annual'
            payments_per_year = 1
        else:
            frequency = 'irregular'
            payments_per_year = round(365 / avg_days, 1) if avg_days > 0 else 0
        
        return {
            'ticker': ticker,
            'frequency': frequency,
            'payments_per_year': payments_per_year,
            'avg_days_between': round(avg_days, 0) if avg_days else None,
            'total_payments': len(df)
        }
    
    # =========================================================================
    # INTEGRACIÓN CON PORTFOLIO
    # =========================================================================
    
    def get_total_return_with_dividends(self, ticker: str = None) -> Dict:
        """
        Calcula rentabilidad total incluyendo dividendos.
        
        Total Return = Plusvalía + Dividendos
        
        Args:
            ticker: Ticker específico (None = cartera completa)
        
        Returns:
            Dict con rentabilidad total
        """
        try:
            from src.portfolio import Portfolio
        except ImportError:
            from portfolio import Portfolio
        
        portfolio = Portfolio()
        
        if ticker:
            # Rentabilidad de un activo específico
            positions = portfolio.get_current_positions()
            position = positions[positions['ticker'] == ticker.upper()]
            
            if position.empty:
                portfolio.close()
                return {'error': f'No hay posición de {ticker}'}
            
            cost_basis = position['cost_basis'].values[0]
            market_value = position['market_value'].values[0]
            unrealized_gain = position['unrealized_gain'].values[0]
            
            # Dividendos de este activo
            divs = self.get_total_dividends()
            divs_ticker = self.get_dividends(ticker=ticker)
            total_dividends = divs_ticker['net_amount'].sum() if not divs_ticker.empty else 0
            
            portfolio.close()
            
            total_return = unrealized_gain + total_dividends
            total_return_pct = (total_return / cost_basis * 100) if cost_basis > 0 else 0
            
            return {
                'ticker': ticker,
                'cost_basis': round(cost_basis, 2),
                'market_value': round(market_value, 2),
                'unrealized_gain': round(unrealized_gain, 2),
                'dividends_received': round(total_dividends, 2),
                'total_return': round(total_return, 2),
                'total_return_pct': round(total_return_pct, 2),
                'capital_gain_contribution': round(unrealized_gain, 2),
                'dividend_contribution': round(total_dividends, 2)
            }
        else:
            # Rentabilidad de toda la cartera
            returns = portfolio.get_total_return(include_dividends=True)
            portfolio.close()
            
            # Añadir breakdown
            divs = self.get_total_dividends()
            
            return {
                'cost_basis': returns['total_invested'],
                'market_value': returns['current_value'],
                'unrealized_gain': returns['unrealized_gain'],
                'realized_gain': returns['realized_gain'],
                'dividends_received': divs['total_net'],
                'total_return': returns['total_gain'],
                'total_return_pct': returns['total_return_pct']
            }
    
    def get_dividend_contribution(self) -> Dict:
        """
        Calcula qué porcentaje de la rentabilidad total viene de dividendos.
        
        Returns:
            Dict con contribución de dividendos
        """
        total_return = self.get_total_return_with_dividends()
        
        if 'error' in total_return:
            return total_return
        
        total = total_return['total_return']
        dividends = total_return['dividends_received']
        
        if total == 0:
            pct = 0
        elif total > 0:
            pct = (dividends / total * 100) if dividends >= 0 else 0
        else:
            # Si hay pérdidas, los dividendos mitigan
            pct = 0  # No tiene sentido hablar de contribución
        
        return {
            'total_return': round(total, 2),
            'from_capital_gains': round(total - dividends, 2),
            'from_dividends': round(dividends, 2),
            'dividend_contribution_pct': round(pct, 2)
        }
    
    # =========================================================================
    # EXPORTACIÓN
    # =========================================================================
    
    def export_dividends(self,
                        filepath: str = None,
                        year: int = None,
                        format: str = 'excel') -> str:
        """
        Exporta dividendos a archivo.
        
        Args:
            filepath: Ruta del archivo
            year: Año específico (None = todo)
            format: 'excel' o 'csv'
        
        Returns:
            Ruta del archivo generado
        """
        if filepath is None:
            suffix = f'_{year}' if year else '_all'
            ext = '.xlsx' if format == 'excel' else '.csv'
            filepath = f'data/exports/dividends{suffix}{ext}'
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        df = self.get_dividends(year=year)
        
        if df.empty:
            print("⚠️  No hay dividendos para exportar")
            return None
        
        if format == 'excel':
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Hoja 1: Detalle
                df.to_excel(writer, sheet_name='Detalle', index=False)
                
                # Hoja 2: Por activo
                by_asset = self.get_dividends_by_asset(year=year)
                if not by_asset.empty:
                    by_asset.to_excel(writer, sheet_name='Por Activo', index=False)
                
                # Hoja 3: Calendario
                if year:
                    calendar = self.get_dividend_calendar(year)
                    calendar.to_excel(writer, sheet_name='Calendario', index=False)
                
                # Hoja 4: Resumen
                totals = self.get_total_dividends(year=year)
                summary_df = pd.DataFrame([totals])
                summary_df.to_excel(writer, sheet_name='Resumen', index=False)
        else:
            df.to_csv(filepath, index=False)
        
        print(f"✅ Dividendos exportados a: {filepath}")
        return str(filepath)
    
    # =========================================================================
    # FUNCIONES DE CONVENIENCIA (PRINT)
    # =========================================================================
    
    def print_dividend_summary(self, year: int = None):
        """Imprime resumen de dividendos"""
        totals = self.get_total_dividends(year=year)
        
        title = f"DIVIDENDOS {year}" if year else "DIVIDENDOS (TOTAL HISTÓRICO)"
        
        print("\n" + "="*70)
        print(f"💰 {title}")
        print("="*70)
        
        if totals['count'] == 0:
            print("\n   No hay dividendos registrados")
            print("="*70)
            return
        
        print(f"\n📊 TOTALES")
        print("-"*50)
        print(f"   Cobros:            {totals['count']}")
        print(f"   Total bruto:       {totals['total_gross']:,.2f}€")
        print(f"   Retenciones:       {totals['total_withholding']:,.2f}€ ({totals['avg_withholding_rate']:.1f}%)")
        print(f"   Total neto:        {totals['total_net']:,.2f}€")
        
        # Por activo
        by_asset = self.get_dividends_by_asset(year=year)
        if not by_asset.empty:
            print(f"\n📈 POR ACTIVO")
            print("-"*50)
            print(f"   {'Ticker':<10} {'Nombre':<25} {'Bruto':>10} {'Neto':>10} {'%':>6}")
            print(f"   {'-'*10} {'-'*25} {'-'*10} {'-'*10} {'-'*6}")
            
            for _, row in by_asset.iterrows():
                name = (row['name'] or row['ticker'])[:25]
                print(f"   {row['ticker']:<10} {name:<25} {row['gross']:>10.2f} {row['net']:>10.2f} {row['pct_of_total']:>5.1f}%")
        
        # Calendario (si es año específico)
        if year:
            calendar = self.get_dividend_calendar(year)
            print(f"\n📅 CALENDARIO {year}")
            print("-"*50)
            
            months_str = "   "
            values_str = "   "
            for _, row in calendar.iterrows():
                months_str += f"{row['month_name']:>6}"
                val = row['net']
                values_str += f"{val:>6.0f}" if val > 0 else f"{'--':>6}"
            
            print(months_str)
            print(values_str + "€")
        
        print("\n" + "="*70)
    
    def print_dividend_calendar(self, year: int = None):
        """Imprime calendario de dividendos"""
        if year is None:
            year = datetime.now().year
        
        calendar = self.get_dividend_calendar(year)
        
        print("\n" + "="*70)
        print(f"📅 CALENDARIO DE DIVIDENDOS {year}")
        print("="*70)
        
        total = calendar['net'].sum()
        
        if total == 0:
            print(f"\n   No hay dividendos registrados en {year}")
        else:
            print(f"\n   {'Mes':<10} {'Bruto':>10} {'Neto':>10} {'Pagos':>8}")
            print(f"   {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
            
            for _, row in calendar.iterrows():
                if row['payments'] > 0:
                    print(f"   {row['month_name']:<10} {row['gross']:>10.2f} {row['net']:>10.2f} {int(row['payments']):>8}")
                else:
                    print(f"   {row['month_name']:<10} {'--':>10} {'--':>10} {'--':>8}")
            
            print(f"   {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
            print(f"   {'TOTAL':<10} {calendar['gross'].sum():>10.2f} {calendar['net'].sum():>10.2f} {int(calendar['payments'].sum()):>8}")
        
        print("\n" + "="*70)
    
    def print_top_payers(self, n: int = 10, year: int = None):
        """Imprime top pagadores de dividendos"""
        top = self.get_top_dividend_payers(n=n, year=year)
        
        title = f"TOP {n} PAGADORES DE DIVIDENDOS"
        if year:
            title += f" ({year})"
        
        print("\n" + "="*70)
        print(f"🏆 {title}")
        print("="*70)
        
        if top.empty:
            print("\n   No hay dividendos registrados")
        else:
            print(f"\n   {'#':<3} {'Ticker':<10} {'Nombre':<25} {'Neto':>10} {'%Total':>8}")
            print(f"   {'-'*3} {'-'*10} {'-'*25} {'-'*10} {'-'*8}")
            
            for i, row in top.iterrows():
                name = (row['name'] or row['ticker'])[:25]
                print(f"   {i+1:<3} {row['ticker']:<10} {name:<25} {row['net']:>10.2f} {row['pct_of_total']:>7.1f}%")
        
        print("\n" + "="*70)
    
    def print_yield_analysis(self):
        """Imprime análisis de yield"""
        portfolio_yield = self.get_portfolio_yield()
        
        print("\n" + "="*70)
        print("📈 ANÁLISIS DE YIELD")
        print("="*70)
        
        print(f"\n📊 CARTERA TOTAL")
        print("-"*50)
        print(f"   Coste de adquisición:    {portfolio_yield['total_cost_basis']:,.2f}€")
        print(f"   Posiciones totales:      {portfolio_yield['total_positions']}")
        print(f"   Activos con dividendos:  {portfolio_yield['dividend_payers']}")
        print(f"\n   Dividendos anuales:")
        print(f"      Bruto:                {portfolio_yield['annual_dividends_gross']:,.2f}€")
        print(f"      Neto:                 {portfolio_yield['annual_dividends_net']:,.2f}€")
        print(f"\n   Yield on Cost (YOC):")
        print(f"      Bruto:                {portfolio_yield['portfolio_yoc_gross']:.2f}%")
        print(f"      Neto:                 {portfolio_yield['portfolio_yoc_net']:.2f}%")
        
        # Yield por activo (solo los que tienen dividendos)
        df = self.get_dividends()
        if not df.empty:
            tickers = df['ticker'].unique()
            
            print(f"\n📈 YIELD POR ACTIVO")
            print("-"*50)
            print(f"   {'Ticker':<10} {'Nombre':<20} {'Coste':>10} {'Divs/Año':>10} {'YOC':>8}")
            print(f"   {'-'*10} {'-'*20} {'-'*10} {'-'*10} {'-'*8}")
            
            yields = []
            for ticker in tickers:
                y = self.get_dividend_yield(ticker)
                if 'error' not in y:
                    yields.append(y)
            
            # Ordenar por YOC
            yields.sort(key=lambda x: x['yoc_net'], reverse=True)
            
            for y in yields:
                name = (y.get('name') or y['ticker'])[:20]
                print(f"   {y['ticker']:<10} {name:<20} {y['cost_basis']:>10.2f} {y['annual_dividends_net']:>10.2f} {y['yoc_net']:>7.2f}%")
        
        print("\n" + "="*70)


# =============================================================================
# DATOS DE EJEMPLO
# =============================================================================

def create_example_dividends(db_path: str = None):
    """
    Crea datos de ejemplo de dividendos para testing.
    
    Simula dividendos de activos típicos españoles y americanos
    durante 2024 y 2025.
    """
    dm = DividendManager(db_path)
    
    print("\n" + "="*70)
    print("📦 CREANDO DATOS DE EJEMPLO DE DIVIDENDOS")
    print("="*70)
    
    # Datos de ejemplo
    example_dividends = [
        # Telefónica - Semestral
        {'ticker': 'TEF', 'name': 'Telefónica', 'gross': 0.30, 'date': '2024-06-15', 'ex_date': '2024-06-10'},
        {'ticker': 'TEF', 'name': 'Telefónica', 'gross': 0.30, 'date': '2024-12-15', 'ex_date': '2024-12-10'},
        {'ticker': 'TEF', 'name': 'Telefónica', 'gross': 0.30, 'date': '2025-06-15', 'ex_date': '2025-06-10'},
        
        # BBVA - Trimestral
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.15, 'date': '2024-04-10', 'ex_date': '2024-04-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.16, 'date': '2024-07-10', 'ex_date': '2024-07-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.17, 'date': '2024-10-10', 'ex_date': '2024-10-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.18, 'date': '2025-01-10', 'ex_date': '2025-01-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.19, 'date': '2025-04-10', 'ex_date': '2025-04-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.20, 'date': '2025-07-10', 'ex_date': '2025-07-05'},
        {'ticker': 'BBVA', 'name': 'Banco BBVA', 'gross': 0.21, 'date': '2025-10-10', 'ex_date': '2025-10-05'},
        
        # Iberdrola - Semestral
        {'ticker': 'IBE', 'name': 'Iberdrola', 'gross': 0.25, 'date': '2024-07-01', 'ex_date': '2024-06-25'},
        {'ticker': 'IBE', 'name': 'Iberdrola', 'gross': 0.27, 'date': '2025-01-15', 'ex_date': '2025-01-10'},
        {'ticker': 'IBE', 'name': 'Iberdrola', 'gross': 0.26, 'date': '2025-07-01', 'ex_date': '2025-06-25'},
        
        # Santander - Trimestral
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.10, 'date': '2024-05-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.10, 'date': '2024-08-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.11, 'date': '2024-11-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.11, 'date': '2025-02-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.12, 'date': '2025-05-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.12, 'date': '2025-08-01'},
        {'ticker': 'SAN', 'name': 'Banco Santander', 'gross': 0.13, 'date': '2025-11-01'},
        
        # Inditex - Anual
        {'ticker': 'ITX', 'name': 'Inditex', 'gross': 1.25, 'date': '2024-05-15', 'ex_date': '2024-05-10'},
        {'ticker': 'ITX', 'name': 'Inditex', 'gross': 1.35, 'date': '2025-05-15', 'ex_date': '2025-05-10'},
        
        # Apple (USD) - Trimestral
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 0.96, 'date': '2024-05-16', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 0.96, 'date': '2024-08-15', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 0.98, 'date': '2024-11-14', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 0.99, 'date': '2025-02-13', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 1.00, 'date': '2025-05-15', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 1.00, 'date': '2025-08-14', 'currency': 'USD'},
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'gross': 1.02, 'date': '2025-11-13', 'currency': 'USD'},
    ]
    
    count = 0
    for div in example_dividends:
        try:
            dm.add_dividend(
                ticker=div['ticker'],
                gross_amount=div['gross'],
                date=div['date'],
                name=div.get('name'),
                currency=div.get('currency', 'EUR'),
                ex_date=div.get('ex_date')
            )
            count += 1
        except Exception as e:
            print(f"   ⚠️  Error añadiendo {div['ticker']}: {e}")
    
    print(f"\n   ✅ Creados {count} dividendos de ejemplo")
    
    # Mostrar resumen
    dm.print_dividend_summary()
    
    dm.close()
    
    return count


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 TEST DEL MÓDULO DIVIDENDS")
    print("="*70)
    
    dm = DividendManager()
    
    # Verificar si hay dividendos
    totals = dm.get_total_dividends()
    
    if totals['count'] == 0:
        print("\n⚠️  No hay dividendos registrados.")
        print("   Creando datos de ejemplo...")
        dm.close()
        create_example_dividends()
        dm = DividendManager()
    
    # Test: Resumen
    print("\n📊 Test 1: Resumen de dividendos")
    dm.print_dividend_summary(2025)
    
    # Test: Calendario
    print("\n📅 Test 2: Calendario")
    dm.print_dividend_calendar(2025)
    
    # Test: Top payers
    print("\n🏆 Test 3: Top pagadores")
    dm.print_top_payers(5, 2025)
    
    # Test: Yield
    print("\n📈 Test 4: Análisis de yield")
    dm.print_yield_analysis()
    
    # Test: Estimación
    print("\n🔮 Test 5: Estimación anual")
    est = dm.estimate_annual_dividends()
    print(f"   Dividendos estimados: {est['estimated_annual_net']:.2f}€/año")
    print(f"   Confianza: {est['confidence']}")
    
    dm.close()
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETADOS")
    print("="*70 + "\n")
