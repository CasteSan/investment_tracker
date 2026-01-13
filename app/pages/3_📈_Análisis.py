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
from src.services.portfolio_service import PortfolioService
from src.core.utils import smart_truncate

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
    db_path = st.session_state.get('db_path')
    db = Database(db_path=db_path)
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
    portfolio = Portfolio(db_path=db_path)
    db = Database(db_path=db_path)
    
    # Obtener precios de mercado descargados
    current_prices = db.get_all_latest_prices()
    
    # Obtener posiciones con precios actuales
    positions = portfolio.get_current_positions(current_prices=current_prices)
    
    if positions.empty:
        st.warning("⚠️ No hay posiciones en la cartera")
        st.stop()

    # Añadir nombres truncados para gráficos
    if 'name' in positions.columns:
        positions['display_name'] = positions['name'].apply(
            lambda x: smart_truncate(x, 15) if x else ''
        )

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
    # MÉTRICAS AVANZADAS DE RIESGO Y RENDIMIENTO
    # =========================================================================
    st.markdown("### 📈 Métricas Avanzadas de Riesgo y Rendimiento")

    # Selector de período y benchmark en el sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("Métricas Avanzadas")

        # Período de análisis
        periodo_opciones = {
            "1 mes": 30,
            "3 meses": 90,
            "6 meses": 180,
            "1 año": 365,
            "2 años": 730,
            "Todo": None
        }
        periodo_seleccionado = st.selectbox(
            "Período de análisis",
            list(periodo_opciones.keys()),
            index=3  # Default: 1 año
        )

        # Benchmark
        benchmark_opciones = ["SP500", "IBEX35", "MSCIWORLD", "EUROSTOXX50"]
        benchmark_seleccionado = st.selectbox(
            "Benchmark",
            benchmark_opciones,
            index=0
        )

        # Tasa libre de riesgo
        risk_free = st.slider(
            "Tasa libre de riesgo (%)",
            min_value=0.0,
            max_value=5.0,
            value=2.0,
            step=0.25
        ) / 100

    # Calcular fechas
    end_date = datetime.now().strftime('%Y-%m-%d')
    dias = periodo_opciones[periodo_seleccionado]
    if dias:
        start_date = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
    else:
        start_date = None  # Todo el histórico

    # Obtener métricas usando el servicio
    db_path = st.session_state.get('db_path')
    with PortfolioService(db_path=db_path) as service:
        metrics = service.get_portfolio_metrics(
            start_date=start_date,
            end_date=end_date,
            benchmark_name=benchmark_seleccionado,
            risk_free_rate=risk_free
        )

    # Mostrar métricas en dos filas
    # Fila 1: Métricas de Rendimiento
    st.markdown("#### Rendimiento")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_ret = metrics['performance']['total_return']
        st.metric(
            "Retorno Total",
            f"{total_ret:+.2%}",
            help="Rentabilidad acumulada en el período"
        )

    with col2:
        cagr = metrics['performance']['cagr']
        st.metric(
            "CAGR",
            f"{cagr:+.2%}",
            help="Tasa de crecimiento anual compuesto"
        )

    with col3:
        sharpe = metrics['performance']['sharpe_ratio']
        sharpe_color = "normal" if sharpe > 0 else "inverse"
        st.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            help="Retorno ajustado por riesgo. >1 es bueno, >2 es excelente"
        )

    with col4:
        sortino = metrics['performance']['sortino_ratio']
        st.metric(
            "Sortino Ratio",
            f"{sortino:.2f}",
            help="Similar a Sharpe pero solo considera volatilidad negativa"
        )

    with col5:
        alpha = metrics['performance']['alpha']
        alpha_delta = f"vs {benchmark_seleccionado}"
        st.metric(
            "Alpha",
            f"{alpha:+.2%}",
            delta=alpha_delta if metrics['meta']['has_benchmark_data'] else "Sin benchmark",
            help="Exceso de retorno sobre el benchmark ajustado por riesgo"
        )

    # Fila 2: Métricas de Riesgo
    st.markdown("#### Riesgo")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        vol = metrics['risk']['volatility']
        st.metric(
            "Volatilidad",
            f"{vol:.2%}",
            help="Desviación estándar anualizada de los retornos"
        )

    with col2:
        var = metrics['risk']['var_95']
        st.metric(
            "VaR 95%",
            f"{var:.2%}",
            help="Pérdida máxima esperada en un día con 95% de confianza"
        )

    with col3:
        max_dd = metrics['risk']['max_drawdown']
        st.metric(
            "Max Drawdown",
            f"{max_dd:.2%}",
            help="Máxima caída desde un pico anterior"
        )

    with col4:
        beta = metrics['risk']['beta']
        beta_interpretation = "Más volátil que mercado" if beta > 1 else "Menos volátil que mercado" if beta < 1 else "Igual que mercado"
        st.metric(
            "Beta",
            f"{beta:.2f}",
            delta=beta_interpretation if metrics['meta']['has_benchmark_data'] else "Sin benchmark",
            help="Sensibilidad al mercado. Beta=1 significa igual volatilidad que el benchmark"
        )

    # Info sobre el período analizado
    trading_days = metrics['meta']['trading_days']
    has_benchmark = metrics['meta']['has_benchmark_data']

    if trading_days > 0:
        info_text = f"Análisis basado en {trading_days} días de trading"
        if has_benchmark:
            info_text += f" | Benchmark: {benchmark_seleccionado}"
        else:
            info_text += f" | Sin datos de {benchmark_seleccionado} (Beta=1.0, Alpha=0.0)"
        st.caption(info_text)
    else:
        st.warning("No hay suficientes datos históricos para calcular métricas avanzadas. Descarga precios en Configuración.")

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
    
    # Gráfico de barras (usa display_name para labels, name para tooltip)
    fig = plot_performance_bar(
        positions_sorted.head(show_top),
        ticker_col='ticker',
        performance_col='unrealized_gain_pct',
        name_col='name',
        display_name_col='display_name',
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
            labels_col='display_name',
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
