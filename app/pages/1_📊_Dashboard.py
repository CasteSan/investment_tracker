"""
Página: Dashboard
Vista general completa de la cartera
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.portfolio import Portfolio
from src.database import Database
from src.tax_calculator import TaxCalculator
from src.dividends import DividendManager

# Importar componentes
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.charts import (
    plot_allocation_donut, 
    plot_performance_bar,
    plot_top_bottom_performers
)
from components.tables import create_positions_table, display_styled_dataframe

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Cartera")

# Obtener configuración del session_state
fiscal_method = st.session_state.get('fiscal_method', 'FIFO')
fiscal_year = st.session_state.get('fiscal_year', datetime.now().year)

# Filtros en sidebar
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Tipo de activo
    asset_type_filter = st.selectbox(
        "Tipo de activo",
        ["Todos", "Acciones", "Fondos", "ETFs"],
        index=0
    )
    
    # Ordenar por
    sort_by = st.selectbox(
        "Ordenar posiciones por",
        ["Valor de mercado", "Ganancia €", "Ganancia %", "Nombre"],
        index=0
    )

try:
    # Cargar datos
    portfolio = Portfolio()
    db = Database()
    
    # Obtener precios de mercado descargados
    current_prices = db.get_all_latest_prices()
    
    # Obtener posiciones con precios actuales
    positions = portfolio.get_current_positions(current_prices=current_prices)
    
    if positions.empty:
        st.warning("⚠️ No hay posiciones en la cartera. Importa tus transacciones primero.")
        st.stop()
    
    # Filtrar por tipo de activo si aplica
    if asset_type_filter != "Todos":
        type_map = {"Acciones": "accion", "Fondos": "fondo", "ETFs": "etf"}
        if 'asset_type' in positions.columns:
            positions = positions[positions['asset_type'] == type_map.get(asset_type_filter, '')]
    
    # =========================================================================
    # MÉTRICAS PRINCIPALES
    # =========================================================================
    st.markdown("### 💰 Resumen de Cartera")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_value = positions['market_value'].sum()
    total_cost = positions['cost_basis'].sum()
    unrealized_gain = positions['unrealized_gain'].sum()
    unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0
    num_positions = len(positions)
    
    with col1:
        st.metric("Valor Total", f"{total_value:,.2f}€")
    
    with col2:
        st.metric("Coste Total", f"{total_cost:,.2f}€")
    
    with col3:
        st.metric(
            "Ganancia Latente", 
            f"{unrealized_gain:,.2f}€",
            delta=f"{unrealized_pct:+.2f}%"
        )
    
    with col4:
        # Plusvalías realizadas del año
        tax = TaxCalculator(method=fiscal_method)
        summary = tax.get_fiscal_year_summary(fiscal_year)
        realized = summary.get('net_gain', 0)
        tax.close()
        
        st.metric(f"Realizado {fiscal_year}", f"{realized:,.2f}€")
    
    with col5:
        st.metric("Posiciones", num_positions)
    
    st.divider()
    
    # =========================================================================
    # GRÁFICOS
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🥧 Distribución de Cartera")
        
        # Preparar datos para el donut
        allocation_df = positions[['ticker', 'name', 'market_value']].copy()
        allocation_df = allocation_df[allocation_df['market_value'] > 0]
        
        if not allocation_df.empty:
            fig = plot_allocation_donut(
                allocation_df,
                labels_col='ticker',
                values_col='market_value',
                names_col='name'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar")
    
    with col2:
        st.markdown("### 📊 Mejores y Peores")
        
        if len(positions) >= 2:
            fig = plot_top_bottom_performers(
                positions,
                ticker_col='ticker',
                perf_col='unrealized_gain_pct',
                n=min(5, len(positions) // 2)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Necesitas al menos 2 posiciones para este gráfico")
    
    st.divider()
    
    # =========================================================================
    # TABLA DE POSICIONES
    # =========================================================================
    st.markdown("### 📋 Posiciones Actuales")
    
    # Ordenar según selección
    sort_map = {
        "Valor de mercado": ('market_value', False),
        "Ganancia €": ('unrealized_gain', False),
        "Ganancia %": ('unrealized_gain_pct', False),
        "Nombre": ('name', True)
    }
    sort_col, ascending = sort_map.get(sort_by, ('market_value', False))
    positions_sorted = positions.sort_values(sort_col, ascending=ascending)
    
    # Añadir peso en cartera
    positions_sorted['weight'] = (positions_sorted['market_value'] / total_value * 100)
    
    # Formatear y mostrar
    table_df = create_positions_table(positions_sorted)
    display_styled_dataframe(
        table_df, 
        gain_columns=['Ganancia', 'Ganancia %'],
        hide_index=True
    )
    
    # Botón de exportar
    csv = positions_sorted.to_csv(index=False)
    st.download_button(
        label="📥 Exportar a CSV",
        data=csv,
        file_name=f"posiciones_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    st.divider()
    
    # =========================================================================
    # RESUMEN POR TIPO DE ACTIVO
    # =========================================================================
    if 'asset_type' in positions.columns:
        st.markdown("### 📊 Resumen por Tipo de Activo")
        
        summary_by_type = positions.groupby('asset_type').agg({
            'market_value': 'sum',
            'cost_basis': 'sum',
            'unrealized_gain': 'sum',
            'ticker': 'count'
        }).reset_index()
        
        summary_by_type.columns = ['Tipo', 'Valor', 'Coste', 'Ganancia', 'Posiciones']
        summary_by_type['Ganancia %'] = (summary_by_type['Ganancia'] / summary_by_type['Coste'] * 100)
        summary_by_type['Peso %'] = (summary_by_type['Valor'] / total_value * 100)
        
        # Mapear nombres
        type_names = {'accion': 'Acciones', 'fondo': 'Fondos', 'etf': 'ETFs'}
        summary_by_type['Tipo'] = summary_by_type['Tipo'].map(lambda x: type_names.get(x, x))
        
        # Formatear
        for col in ['Valor', 'Coste', 'Ganancia']:
            summary_by_type[col] = summary_by_type[col].apply(lambda x: f"{x:,.2f}€")
        summary_by_type['Ganancia %'] = summary_by_type['Ganancia %'].apply(lambda x: f"{x:+.2f}%")
        summary_by_type['Peso %'] = summary_by_type['Peso %'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(summary_by_type, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # DIVIDENDOS DEL AÑO
    # =========================================================================
    st.markdown(f"### 💵 Dividendos {fiscal_year}")
    
    dm = DividendManager()
    div_totals = dm.get_total_dividends(year=fiscal_year)
    dm.close()
    
    if div_totals['count'] > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Cobros", div_totals['count'])
        with col2:
            st.metric("Bruto Total", f"{div_totals['total_gross']:,.2f}€")
        with col3:
            st.metric("Neto Total", f"{div_totals['total_net']:,.2f}€")
        with col4:
            st.metric("Retenciones", f"{div_totals['total_withholding']:,.2f}€")
    else:
        st.info(f"No hay dividendos registrados en {fiscal_year}")
    
    portfolio.close()

except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.exception(e)
