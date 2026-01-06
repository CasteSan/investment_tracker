"""
Componentes de Tablas - Formateo y estilizado
Funciones reutilizables para mostrar tablas en Streamlit
"""

import pandas as pd
import streamlit as st
from typing import List, Dict, Optional


def format_currency(value: float, symbol: str = "€") -> str:
    """Formatea un valor como moneda"""
    if pd.isna(value):
        return "-"
    return f"{value:,.2f}{symbol}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Formatea un valor como porcentaje con signo"""
    if pd.isna(value):
        return "-"
    return f"{value:+.{decimals}f}%"


def format_number(value: float, decimals: int = 0) -> str:
    """Formatea un número con separadores de miles"""
    if pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}"


def highlight_gains_losses(val):
    """Función de estilo para colorear según ganancia/pérdida"""
    try:
        num = float(str(val).replace('%', '').replace('€', '').replace(',', '').replace('+', ''))
        if num > 0:
            return 'color: #2ca02c'  # Verde
        elif num < 0:
            return 'color: #d62728'  # Rojo
        else:
            return ''
    except:
        return ''


def create_positions_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea tabla de posiciones formateada.
    
    Args:
        df: DataFrame de posiciones del portfolio
    
    Returns:
        DataFrame formateado para mostrar
    """
    if df.empty:
        return df
    
    # Seleccionar y renombrar columnas
    columns_map = {
        'ticker': 'Ticker',
        'name': 'Nombre',
        'quantity': 'Cantidad',
        'avg_price': 'Precio Medio',
        'current_price': 'Precio Actual',
        'cost_basis': 'Coste',
        'market_value': 'Valor Mercado',
        'unrealized_gain': 'Ganancia',
        'unrealized_gain_pct': 'Ganancia %',
        'weight': 'Peso %'
    }
    
    # Filtrar columnas disponibles
    available_cols = [c for c in columns_map.keys() if c in df.columns]
    result = df[available_cols].copy()
    result.columns = [columns_map[c] for c in available_cols]
    
    # Formatear valores
    if 'Cantidad' in result.columns:
        result['Cantidad'] = result['Cantidad'].apply(lambda x: format_number(x, 2))
    
    if 'Precio Medio' in result.columns:
        result['Precio Medio'] = result['Precio Medio'].apply(format_currency)
    
    if 'Precio Actual' in result.columns:
        result['Precio Actual'] = result['Precio Actual'].apply(format_currency)
    
    if 'Coste' in result.columns:
        result['Coste'] = result['Coste'].apply(format_currency)
    
    if 'Valor Mercado' in result.columns:
        result['Valor Mercado'] = result['Valor Mercado'].apply(format_currency)
    
    if 'Ganancia' in result.columns:
        result['Ganancia'] = result['Ganancia'].apply(lambda x: f"{x:+,.2f}€")
    
    if 'Ganancia %' in result.columns:
        result['Ganancia %'] = result['Ganancia %'].apply(format_percentage)
    
    if 'Peso %' in result.columns:
        result['Peso %'] = result['Peso %'].apply(lambda x: f"{x:.1f}%")
    
    return result


def create_transactions_table(df: pd.DataFrame, limit: int = None) -> pd.DataFrame:
    """
    Crea tabla de transacciones formateada.
    
    Args:
        df: DataFrame de transacciones
        limit: Número máximo de filas
    
    Returns:
        DataFrame formateado
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    # Limitar filas si se especifica
    if limit:
        result = result.head(limit)
    
    # Mapeo de tipos
    type_map = {
        'buy': '🟢 Compra',
        'sell': '🔴 Venta',
        'dividend': '💰 Dividendo',
        'transfer_in': '➡️ Traspaso entrada',
        'transfer_out': '⬅️ Traspaso salida'
    }
    
    if 'type' in result.columns:
        result['type'] = result['type'].map(lambda x: type_map.get(x, x))
    
    # Formatear columnas
    columns_map = {
        'date': 'Fecha',
        'type': 'Tipo',
        'ticker': 'Ticker',
        'name': 'Nombre',
        'quantity': 'Cantidad',
        'price': 'Precio',
        'total': 'Total',
        'commission': 'Comisión'
    }
    
    available_cols = [c for c in columns_map.keys() if c in result.columns]
    result = result[available_cols]
    result.columns = [columns_map[c] for c in available_cols]
    
    return result


def create_fiscal_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea tabla fiscal de ventas formateada.
    
    Args:
        df: DataFrame de detalle fiscal
    
    Returns:
        DataFrame formateado
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    columns_map = {
        'ticker': 'Ticker',
        'name': 'Nombre',
        'sale_date': 'Fecha Venta',
        'quantity': 'Cantidad',
        'sale_price': 'Precio Venta',
        'cost_basis': 'Coste',
        'sale_proceeds': 'Ingresos',
        'gain': 'Ganancia',
        'gain_pct': 'Ganancia %',
        'holding_days': 'Días'
    }
    
    available_cols = [c for c in columns_map.keys() if c in result.columns]
    result = result[available_cols]
    result.columns = [columns_map[c] for c in available_cols]
    
    # Formatear valores
    if 'Cantidad' in result.columns:
        result['Cantidad'] = result['Cantidad'].apply(lambda x: format_number(x, 2))
    
    if 'Precio Venta' in result.columns:
        result['Precio Venta'] = result['Precio Venta'].apply(format_currency)
    
    if 'Coste' in result.columns:
        result['Coste'] = result['Coste'].apply(format_currency)
    
    if 'Ingresos' in result.columns:
        result['Ingresos'] = result['Ingresos'].apply(format_currency)
    
    if 'Ganancia' in result.columns:
        result['Ganancia'] = result['Ganancia'].apply(lambda x: f"{x:+,.2f}€")
    
    if 'Ganancia %' in result.columns:
        result['Ganancia %'] = result['Ganancia %'].apply(format_percentage)
    
    return result


def create_dividends_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea tabla de dividendos formateada.
    
    Args:
        df: DataFrame de dividendos
    
    Returns:
        DataFrame formateado
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    columns_map = {
        'ticker': 'Ticker',
        'name': 'Nombre',
        'date': 'Fecha',
        'gross_amount': 'Bruto',
        'net_amount': 'Neto',
        'withholding_tax': 'Retención',
        'currency': 'Divisa'
    }
    
    available_cols = [c for c in columns_map.keys() if c in result.columns]
    result = result[available_cols]
    result.columns = [columns_map[c] for c in available_cols]
    
    # Formatear valores
    if 'Bruto' in result.columns:
        result['Bruto'] = result['Bruto'].apply(format_currency)
    
    if 'Neto' in result.columns:
        result['Neto'] = result['Neto'].apply(format_currency)
    
    if 'Retención' in result.columns:
        result['Retención'] = result['Retención'].apply(format_currency)
    
    return result


def create_benchmark_metrics_table(metrics: Dict) -> pd.DataFrame:
    """
    Crea tabla de métricas de benchmark.
    
    Args:
        metrics: Dict con métricas del benchmark
    
    Returns:
        DataFrame formateado
    """
    data = []
    
    # Rendimientos
    if 'returns' in metrics:
        ret = metrics['returns']
        data.append({'Categoría': 'RENDIMIENTOS', 'Métrica': '', 'Cartera': '', 'Benchmark': ''})
        data.append({
            'Categoría': '', 
            'Métrica': 'Rentabilidad Total',
            'Cartera': f"{ret.get('portfolio_total', 0):+.2f}%",
            'Benchmark': f"{ret.get('benchmark_total', 0):+.2f}%"
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Rentabilidad Anual',
            'Cartera': f"{ret.get('portfolio_annual', 0):+.2f}%",
            'Benchmark': f"{ret.get('benchmark_annual', 0):+.2f}%"
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Outperformance',
            'Cartera': f"{ret.get('outperformance', 0):+.2f}%",
            'Benchmark': '-'
        })
    
    # Riesgo
    if 'risk' in metrics:
        risk = metrics['risk']
        data.append({'Categoría': 'RIESGO', 'Métrica': '', 'Cartera': '', 'Benchmark': ''})
        data.append({
            'Categoría': '', 
            'Métrica': 'Volatilidad',
            'Cartera': f"{risk.get('portfolio_volatility', 0):.2f}%",
            'Benchmark': f"{risk.get('benchmark_volatility', 0):.2f}%"
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Beta',
            'Cartera': f"{risk.get('beta', 0):.2f}",
            'Benchmark': '1.00'
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Tracking Error',
            'Cartera': f"{risk.get('tracking_error', 0):.2f}%",
            'Benchmark': '-'
        })
    
    # Ratios ajustados
    if 'risk_adjusted' in metrics:
        ra = metrics['risk_adjusted']
        data.append({'Categoría': 'RATIOS', 'Métrica': '', 'Cartera': '', 'Benchmark': ''})
        data.append({
            'Categoría': '', 
            'Métrica': 'Alpha',
            'Cartera': f"{ra.get('alpha', 0):+.2f}%",
            'Benchmark': '0.00%'
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Sharpe Ratio',
            'Cartera': f"{ra.get('portfolio_sharpe', 0):.2f}",
            'Benchmark': f"{ra.get('benchmark_sharpe', 0):.2f}"
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Sortino Ratio',
            'Cartera': f"{ra.get('portfolio_sortino', 0):.2f}",
            'Benchmark': f"{ra.get('benchmark_sortino', 0):.2f}"
        })
        data.append({
            'Categoría': '', 
            'Métrica': 'Information Ratio',
            'Cartera': f"{ra.get('information_ratio', 0):.2f}",
            'Benchmark': '-'
        })
    
    # Drawdown
    if 'drawdown' in metrics:
        dd = metrics['drawdown']
        data.append({'Categoría': 'DRAWDOWN', 'Métrica': '', 'Cartera': '', 'Benchmark': ''})
        data.append({
            'Categoría': '', 
            'Métrica': 'Max Drawdown',
            'Cartera': f"{dd.get('portfolio_max_dd', 0):.2f}%",
            'Benchmark': f"{dd.get('benchmark_max_dd', 0):.2f}%"
        })
    
    return pd.DataFrame(data)


def display_styled_dataframe(df: pd.DataFrame, 
                            gain_columns: List[str] = None,
                            use_container_width: bool = True,
                            hide_index: bool = True):
    """
    Muestra un DataFrame con estilos aplicados.
    
    Args:
        df: DataFrame a mostrar
        gain_columns: Columnas a colorear según ganancia/pérdida
        use_container_width: Si usar todo el ancho
        hide_index: Si ocultar el índice
    """
    if df.empty:
        st.info("No hay datos para mostrar")
        return
    
    # Si hay columnas de ganancia, aplicar estilo
    if gain_columns:
        styled = df.style.applymap(
            highlight_gains_losses,
            subset=[c for c in gain_columns if c in df.columns]
        )
        st.dataframe(styled, use_container_width=use_container_width, hide_index=hide_index)
    else:
        st.dataframe(df, use_container_width=use_container_width, hide_index=hide_index)
