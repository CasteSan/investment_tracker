"""
Página: Análisis
Análisis detallado de rentabilidad y composición de la cartera
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

# Importar componentes
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.charts import (
    plot_performance_bar,
    plot_allocation_donut
)
from components.tables import create_positions_table

st.set_page_config(page_title="Análisis", page_icon="📈", layout="wide")

st.title("📈 Análisis de Cartera")

# Sidebar - Filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Tipo de activo
    asset_filter = st.multiselect(
        "Tipo de activo",
        ["accion", "fondo", "etf"],
        default=["accion", "fondo", "etf"]
    )
    
    # Divisa
    db = Database()
    currencies = db.get_currencies_used()
    db.close()
    
    currency_filter = st.multiselect(
        "Divisa",
        currencies,
        default=currencies
    )
    
    # Solo posiciones con ganancia/pérdida
    gain_loss_filter = st.radio(
        "Mostrar",
        ["Todas", "Solo ganancias", "Solo pérdidas"]
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
        st.warning("⚠️ No hay posiciones en la cartera")
        st.stop()
    
    # Aplicar filtros
    if asset_filter and 'asset_type' in positions.columns:
        positions = positions[positions['asset_type'].isin(asset_filter)]
    
    if currency_filter and 'currency' in positions.columns:
        positions = positions[positions['currency'].isin(currency_filter)]
    
    if gain_loss_filter == "Solo ganancias":
        positions = positions[positions['unrealized_gain'] > 0]
    elif gain_loss_filter == "Solo pérdidas":
        positions = positions[positions['unrealized_gain'] < 0]
    
    if positions.empty:
        st.warning("No hay posiciones que coincidan con los filtros")
        st.stop()
    
    # =========================================================================
    # MÉTRICAS DE RENDIMIENTO
    # =========================================================================
    st.markdown("### 📊 Métricas de Rendimiento")
    
    total_value = positions['market_value'].sum()
    total_cost = positions['cost_basis'].sum()
    total_gain = positions['unrealized_gain'].sum()
    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
    
    # Posiciones ganadoras vs perdedoras
    winners = positions[positions['unrealized_gain'] > 0]
    losers = positions[positions['unrealized_gain'] < 0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Rentabilidad Total",
            f"{total_gain_pct:+.2f}%",
            delta=f"{total_gain:+,.2f}€"
        )
    
    with col2:
        win_rate = (len(winners) / len(positions) * 100) if len(positions) > 0 else 0
        st.metric(
            "Tasa de Acierto",
            f"{win_rate:.1f}%",
            delta=f"{len(winners)} de {len(positions)} posiciones"
        )
    
    with col3:
        winners_gain = winners['unrealized_gain'].sum() if not winners.empty else 0
        st.metric("Total Ganancias", f"{winners_gain:+,.2f}€")
    
    with col4:
        losers_loss = losers['unrealized_gain'].sum() if not losers.empty else 0
        st.metric("Total Pérdidas", f"{losers_loss:,.2f}€")
    
    st.divider()
    
    # =========================================================================
    # GRÁFICO DE RENTABILIDAD POR ACTIVO
    # =========================================================================
    st.markdown("### 📊 Rentabilidad por Activo")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Selector de ordenación
        sort_option = st.selectbox(
            "Ordenar por",
            ["Rentabilidad % (mayor a menor)", "Rentabilidad % (menor a mayor)", 
             "Ganancia € (mayor a menor)", "Valor de mercado"]
        )
        
        if sort_option == "Rentabilidad % (mayor a menor)":
            positions_sorted = positions.sort_values('unrealized_gain_pct', ascending=False)
        elif sort_option == "Rentabilidad % (menor a mayor)":
            positions_sorted = positions.sort_values('unrealized_gain_pct', ascending=True)
        elif sort_option == "Ganancia € (mayor a menor)":
            positions_sorted = positions.sort_values('unrealized_gain', ascending=False)
        else:
            positions_sorted = positions.sort_values('market_value', ascending=False)
    
    with col2:
        # Ajustar slider para funcionar con cualquier número de posiciones
        num_positions = len(positions)
        if num_positions > 1:
            slider_min = 1
            slider_max = min(30, num_positions)
            slider_default = min(15, num_positions)
            show_top = st.slider("Mostrar top", slider_min, slider_max, slider_default)
        else:
            show_top = num_positions  # Si solo hay 1 posición, mostrar esa
    
    # Gráfico de barras
    fig = plot_performance_bar(
        positions_sorted.head(show_top),
        ticker_col='ticker',
        performance_col='unrealized_gain_pct',
        name_col='name',
        title=f"Top {show_top} por Rentabilidad",
        top_n=show_top
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # =========================================================================
    # TABLA DETALLADA
    # =========================================================================
    st.markdown("### 📋 Detalle de Posiciones")
    
    # Preparar tabla con más columnas
    detail_df = positions_sorted.copy()
    
    # Añadir peso en cartera
    detail_df['weight'] = (detail_df['market_value'] / total_value * 100)
    
    # Seleccionar columnas para mostrar
    display_cols = ['ticker', 'name', 'quantity', 'avg_price', 'cost_basis', 
                   'market_value', 'unrealized_gain', 'unrealized_gain_pct', 'weight']
    
    available_cols = [c for c in display_cols if c in detail_df.columns]
    detail_df = detail_df[available_cols]
    
    # Renombrar
    col_names = {
        'ticker': 'Ticker',
        'name': 'Nombre',
        'quantity': 'Cantidad',
        'avg_price': 'Precio Medio',
        'cost_basis': 'Coste',
        'market_value': 'Valor',
        'unrealized_gain': 'Ganancia €',
        'unrealized_gain_pct': 'Ganancia %',
        'weight': 'Peso %'
    }
    detail_df.columns = [col_names.get(c, c) for c in detail_df.columns]
    
    # Formatear valores
    if 'Cantidad' in detail_df.columns:
        detail_df['Cantidad'] = detail_df['Cantidad'].apply(lambda x: f"{x:,.2f}")
    if 'Precio Medio' in detail_df.columns:
        detail_df['Precio Medio'] = detail_df['Precio Medio'].apply(lambda x: f"{x:,.4f}€")
    if 'Coste' in detail_df.columns:
        detail_df['Coste'] = detail_df['Coste'].apply(lambda x: f"{x:,.2f}€")
    if 'Valor' in detail_df.columns:
        detail_df['Valor'] = detail_df['Valor'].apply(lambda x: f"{x:,.2f}€")
    if 'Ganancia €' in detail_df.columns:
        detail_df['Ganancia €'] = detail_df['Ganancia €'].apply(lambda x: f"{x:+,.2f}€")
    if 'Ganancia %' in detail_df.columns:
        detail_df['Ganancia %'] = detail_df['Ganancia %'].apply(lambda x: f"{x:+.2f}%")
    if 'Peso %' in detail_df.columns:
        detail_df['Peso %'] = detail_df['Peso %'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(detail_df, use_container_width=True, hide_index=True)
    
    # Botón de exportar
    csv = positions_sorted.to_csv(index=False)
    st.download_button(
        label="📥 Exportar análisis a CSV",
        data=csv,
        file_name=f"analisis_cartera_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    st.divider()
    
    # =========================================================================
    # DISTRIBUCIÓN POR CATEGORÍAS
    # =========================================================================
    st.markdown("### 🥧 Distribución de la Cartera")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Por Activo")
        fig = plot_allocation_donut(
            positions,
            labels_col='ticker',
            values_col='market_value',
            names_col='name',
            title=""
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Por tipo de activo
        if 'asset_type' in positions.columns:
            st.markdown("#### Por Tipo de Activo")
            
            by_type = positions.groupby('asset_type').agg({
                'market_value': 'sum'
            }).reset_index()
            
            type_names = {'accion': 'Acciones', 'fondo': 'Fondos', 'etf': 'ETFs'}
            by_type['asset_type'] = by_type['asset_type'].map(lambda x: type_names.get(x, x))
            
            fig2 = plot_allocation_donut(
                by_type,
                labels_col='asset_type',
                values_col='market_value',
                title=""
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    st.divider()
    
    # =========================================================================
    # ESTADÍSTICAS ADICIONALES
    # =========================================================================
    st.markdown("### 📊 Estadísticas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Mejor posición**")
        if not positions.empty:
            best = positions.loc[positions['unrealized_gain_pct'].idxmax()]
            st.success(f"🏆 {best['name']}: {best['unrealized_gain_pct']:+.2f}%")
    
    with col2:
        st.markdown("**Peor posición**")
        if not positions.empty:
            worst = positions.loc[positions['unrealized_gain_pct'].idxmin()]
            st.error(f"📉 {worst['name']}: {worst['unrealized_gain_pct']:+.2f}%")
    
    with col3:
        st.markdown("**Mayor posición**")
        if not positions.empty:
            largest = positions.loc[positions['market_value'].idxmax()]
            weight = (largest['market_value'] / total_value * 100)
            st.info(f"💰 {largest['name']}: {weight:.1f}% de la cartera")
    
    # Tabla de estadísticas
    stats_data = {
        'Métrica': [
            'Número de posiciones',
            'Posiciones ganadoras',
            'Posiciones perdedoras',
            'Posición media',
            'Mayor ganancia',
            'Mayor pérdida',
            'Rentabilidad media',
            'Concentración (top 5)'
        ],
        'Valor': [
            len(positions),
            len(winners),
            len(losers),
            f"{total_value / len(positions):,.2f}€",
            f"{positions['unrealized_gain'].max():+,.2f}€",
            f"{positions['unrealized_gain'].min():+,.2f}€",
            f"{positions['unrealized_gain_pct'].mean():+.2f}%",
            f"{positions.nlargest(5, 'market_value')['market_value'].sum() / total_value * 100:.1f}%"
        ]
    }
    
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
    
    portfolio.close()

except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.exception(e)
