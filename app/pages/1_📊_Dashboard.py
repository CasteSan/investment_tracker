"""
Pagina: Dashboard
Vista general completa de la cartera

Refactorizado en Sesion 2 para usar PortfolioService.
La logica de negocio ahora esta centralizada en el servicio.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Autenticacion (DEBE ser antes de cualquier otro st.*)
from app.components.auth import require_auth
if not require_auth("Dashboard", "📊"):
    st.stop()

# Importar servicio (unico punto de acceso a logica de negocio)
from src.services.portfolio_service import PortfolioService

# Importar componentes UI
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.charts import (
    plot_allocation_donut,
    plot_performance_bar,
    plot_top_bottom_performers,
    plot_portfolio_treemap
)
from components.tables import create_positions_table, display_styled_dataframe
from components.cache import get_cached_dashboard_data

st.title("📊 Dashboard de Cartera")

# Obtener configuracion del session_state
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
    # ==========================================================================
    # OBTENER DATOS CON CACHE (mejora rendimiento en cloud)
    # ==========================================================================
    db_path = st.session_state.get('db_path')

    # Obtener datos cacheados (evita consultas repetidas a PostgreSQL)
    data = get_cached_dashboard_data(db_path, fiscal_year, fiscal_method)

    # Verificar si hay posiciones
    if data['positions'] is None or data['positions'].empty:
        st.warning("⚠️ No hay posiciones en la cartera. Importa tus transacciones primero.")
        st.stop()

    positions = data['positions']
    metrics = data['metrics']
    fiscal_summary = data['fiscal_summary']
    dividend_totals = data['dividend_totals']

    # Servicio para operaciones adicionales (filtros, graficos)
    service = PortfolioService(db_path=db_path)

    # Aplicar filtros de UI (operaciones en memoria)
    positions = service.filter_positions(positions, asset_type_filter)
    positions = service.sort_positions(positions, sort_by)
    positions = service.enrich_with_weights(positions)
    positions = service.enrich_with_display_names(positions)

    # ==========================================================================
    # METRICAS PRINCIPALES (solo renderizado UI)
    # ==========================================================================
    st.markdown("### 💰 Resumen de Cartera")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Valor Total", f"{metrics['total_value']:,.2f}€")

    with col2:
        st.metric("Coste Total", f"{metrics['total_cost']:,.2f}€")

    with col3:
        st.metric(
            "Ganancia Latente",
            f"{metrics['unrealized_gain']:,.2f}€",
            delta=f"{metrics['unrealized_pct']:+.2f}%"
        )

    with col4:
        realized = fiscal_summary.get('realized_gain', 0)
        st.metric(f"Realizado {fiscal_year}", f"{realized:,.2f}€")

    with col5:
        st.metric("Posiciones", metrics['num_positions'])

    st.divider()

    # ==========================================================================
    # GRAFICOS
    # ==========================================================================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥧 Distribucion de Cartera")

        # Obtener datos de asignacion
        allocation_df = service.get_allocation_data()

        if not allocation_df.empty:
            fig = plot_allocation_donut(
                allocation_df,
                labels_col='display_name',
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
            st.info("Necesitas al menos 2 posiciones para este grafico")

    st.divider()

    # ==========================================================================
    # MAPA DE CALOR (TREEMAP)
    # ==========================================================================
    st.markdown("### 🗺️ Mapa de Calor")

    # Control de filtro por categoría
    heatmap_filter_options = {
        "Todos": "all",
        "Fondos/ETF": "fondos_etf",
        "Acciones": "acciones"
    }

    # Usar radio horizontal como segmented control
    heatmap_filter_label = st.radio(
        "Filtrar por tipo",
        options=list(heatmap_filter_options.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )
    heatmap_filter = heatmap_filter_options[heatmap_filter_label]

    # Obtener datos para el heatmap
    heatmap_df = service.get_heatmap_data(category_filter=heatmap_filter)

    if not heatmap_df.empty:
        fig = plot_portfolio_treemap(
            heatmap_df,
            size_col='weight',
            color_col='daily_change_pct',
            label_col='display_name',
            hover_name_col='name',
            title=""
        )
        st.plotly_chart(fig, use_container_width=True, key="heatmap_treemap")

        # Leyenda informativa
        st.caption(
            "📊 **Tamaño:** Peso en cartera | "
            "🎨 **Color:** Variación intradía (vs cierre anterior)"
        )
    else:
        st.info(f"No hay activos de tipo '{heatmap_filter_label}' en la cartera")

    st.divider()

    # ==========================================================================
    # TABLA DE POSICIONES
    # ==========================================================================
    st.markdown("### 📋 Posiciones Actuales")

    # Formatear y mostrar (positions ya viene filtrada y ordenada)
    table_df = create_positions_table(positions)
    display_styled_dataframe(
        table_df,
        gain_columns=['Ganancia', 'Ganancia %'],
        hide_index=True
    )

    # Boton de exportar
    csv = positions.to_csv(index=False)
    st.download_button(
        label="📥 Exportar a CSV",
        data=csv,
        file_name=f"posiciones_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

    st.divider()

    # ==========================================================================
    # RESUMEN POR TIPO DE ACTIVO
    # ==========================================================================
    if 'asset_type' in data['positions'].columns:
        st.markdown("### 📊 Resumen por Tipo de Activo")

        # Obtener resumen (usando posiciones sin filtrar para ver totales)
        summary_by_type = service.get_summary_by_type(data['positions'])

        if not summary_by_type.empty:
            # Formatear para display
            formatted_summary = service.format_summary_by_type(summary_by_type)
            st.dataframe(formatted_summary, use_container_width=True, hide_index=True)

    # ==========================================================================
    # DIVIDENDOS DEL AÑO
    # ==========================================================================
    st.markdown(f"### 💵 Dividendos {fiscal_year}")

    if dividend_totals['count'] > 0:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cobros", dividend_totals['count'])
        with col2:
            st.metric("Bruto Total", f"{dividend_totals['total_gross']:,.2f}€")
        with col3:
            st.metric("Neto Total", f"{dividend_totals['total_net']:,.2f}€")
        with col4:
            st.metric("Retenciones", f"{dividend_totals['total_withholding']:,.2f}€")
    else:
        st.info(f"No hay dividendos registrados en {fiscal_year}")

    # Cerrar servicio
    service.close()

except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.exception(e)
