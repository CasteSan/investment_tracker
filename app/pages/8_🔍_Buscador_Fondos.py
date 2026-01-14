"""
Pagina: Catalogo Inteligente de Fondos
Importa fondos desde Morningstar y explora el catalogo
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.services.fund_service import FundService
from src.providers.morningstar import FundNotFoundError, FundDataProviderError
from src.data.models import FUND_RISK_LEVELS

st.set_page_config(
    page_title="Catalogo de Fondos",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Catalogo Inteligente de Fondos")

# Obtener db_path de session_state (multi-portfolio)
db_path = st.session_state.get('db_path')

# =============================================================================
# TABS PRINCIPALES
# =============================================================================

tab_import, tab_catalog = st.tabs(["📥 Importar Fondo", "📊 Mi Catalogo"])

# =============================================================================
# TAB 1: IMPORTAR FONDO
# =============================================================================

with tab_import:
    st.markdown("### Importar fondo desde Morningstar")
    st.markdown("Introduce el ISIN de un fondo o ETF para obtener sus datos automaticamente.")

    col_input, col_btn = st.columns([3, 1])

    with col_input:
        isin_input = st.text_input(
            "Codigo ISIN",
            placeholder="Ej: IE00B3RBWM25",
            help="Codigo ISIN de 12 caracteres del fondo",
            label_visibility="collapsed"
        )

    with col_btn:
        search_btn = st.button("🔍 Buscar", type="primary", use_container_width=True)

    # Estado para preview
    if 'fund_preview' not in st.session_state:
        st.session_state.fund_preview = None

    # Buscar fondo
    if search_btn and isin_input:
        isin_clean = isin_input.strip().upper()

        if len(isin_clean) != 12:
            st.error("El ISIN debe tener 12 caracteres")
        else:
            with st.spinner(f"Buscando {isin_clean} en Morningstar..."):
                try:
                    with FundService(db_path=db_path) as service:
                        preview = service.fetch_fund_preview(isin_clean)
                        st.session_state.fund_preview = preview
                        st.success(f"Fondo encontrado: {preview['name']}")
                except FundNotFoundError:
                    st.error(f"No se encontro el fondo con ISIN: {isin_clean}")
                    st.session_state.fund_preview = None
                except FundDataProviderError as e:
                    st.error(f"Error consultando Morningstar: {e}")
                    st.session_state.fund_preview = None
                except Exception as e:
                    st.error(f"Error inesperado: {e}")
                    st.session_state.fund_preview = None

    # Mostrar preview si existe
    if st.session_state.fund_preview:
        preview = st.session_state.fund_preview

        st.divider()
        st.markdown("### Ficha del Fondo")

        # Info basica
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Informacion General**")
            st.write(f"**Nombre:** {preview.get('name', '-')}")
            st.write(f"**ISIN:** {preview.get('isin', '-')}")
            st.write(f"**Tipo:** {preview.get('asset_type', '-').upper()}")
            st.write(f"**Gestora:** {preview.get('manager', '-')}")
            st.write(f"**Categoria:** {preview.get('morningstar_category') or preview.get('category_name', '-')}")

        with col2:
            st.markdown("**Costes y Riesgo**")
            ter = preview.get('ter')
            st.write(f"**TER:** {ter:.2f}%" if ter else "**TER:** -")

            risk = preview.get('risk_level')
            if risk:
                risk_name = FUND_RISK_LEVELS.get(risk, '')
                st.write(f"**Riesgo SRRI:** {risk}/7 ({risk_name})")
            else:
                st.write("**Riesgo SRRI:** -")

            aum = preview.get('aum')
            st.write(f"**Patrimonio:** {aum:,.0f}M EUR" if aum else "**Patrimonio:** -")

            dist = preview.get('distribution_policy', '-')
            st.write(f"**Distribucion:** {dist.capitalize()}")

        with col3:
            st.markdown("**Rentabilidad**")
            ret_1y = preview.get('return_1y')
            ret_3y = preview.get('return_3y')
            ret_5y = preview.get('return_5y')

            # Colorear rentabilidades
            def format_return(val, label):
                if val is None:
                    return f"**{label}:** -"
                color = "green" if val >= 0 else "red"
                return f"**{label}:** :{color}[{val:+.2f}%]"

            st.markdown(format_return(ret_1y, "1 Ano"))
            st.markdown(format_return(ret_3y, "3 Anos"))
            st.markdown(format_return(ret_5y, "5 Anos"))

            st.markdown("**Volatilidad**")
            vol_1y = preview.get('volatility_1y')
            sharpe_1y = preview.get('sharpe_1y')
            st.write(f"**Vol 1A:** {vol_1y:.2f}%" if vol_1y else "**Vol 1A:** -")
            st.write(f"**Sharpe 1A:** {sharpe_1y:.2f}" if sharpe_1y else "**Sharpe 1A:** -")

        # Asset Allocation y Holdings
        col_alloc, col_hold = st.columns(2)

        with col_alloc:
            allocation = preview.get('allocation', {})
            if allocation:
                st.markdown("**Asset Allocation**")

                # Preparar datos para grafico
                alloc_data = []
                labels_map = {
                    'us_equity': 'RV USA',
                    'non_us_equity': 'RV Internacional',
                    'bond': 'Renta Fija',
                    'cash': 'Efectivo',
                    'other': 'Otros'
                }
                for key, label in labels_map.items():
                    val = allocation.get(key, 0)
                    if val > 0.1:  # Solo mostrar si > 0.1%
                        alloc_data.append({'Tipo': label, 'Peso': val})

                if alloc_data:
                    df_alloc = pd.DataFrame(alloc_data)
                    fig = px.pie(
                        df_alloc,
                        values='Peso',
                        names='Tipo',
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig.update_layout(
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=250,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)

        with col_hold:
            holdings = preview.get('holdings', [])
            if holdings:
                st.markdown("**Top 10 Holdings**")

                df_hold = pd.DataFrame(holdings)
                df_hold = df_hold.rename(columns={
                    'name': 'Nombre',
                    'weight': 'Peso %',
                    'sector': 'Sector'
                })
                df_hold['Peso %'] = df_hold['Peso %'].apply(lambda x: f"{x:.2f}%")

                st.dataframe(
                    df_hold,
                    use_container_width=True,
                    hide_index=True,
                    height=250
                )

        st.divider()

        # Boton guardar
        col_save, col_cancel = st.columns([1, 3])

        with col_save:
            if st.button("💾 Guardar en Base de Datos", type="primary", use_container_width=True):
                with st.spinner("Guardando..."):
                    try:
                        with FundService(db_path=db_path) as service:
                            fund = service.fetch_and_import_fund(preview['isin'])
                            st.success(f"Fondo guardado: {fund.name}")
                            st.session_state.fund_preview = None
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error guardando: {e}")

        with col_cancel:
            if st.button("Cancelar"):
                st.session_state.fund_preview = None
                st.rerun()


# =============================================================================
# TAB 2: MI CATALOGO
# =============================================================================

with tab_catalog:
    st.markdown("### Mi Catalogo de Fondos")

    try:
        with FundService(db_path=db_path) as service:
            # Verificar si hay fondos
            if not service.has_funds():
                st.info("El catalogo esta vacio. Usa la pestana 'Importar Fondo' para anadir fondos.")
                st.stop()

            # Filtros en linea
            col_filter1, col_filter2, col_filter3 = st.columns(3)

            with col_filter1:
                search_name = st.text_input(
                    "Buscar por nombre",
                    placeholder="Filtrar...",
                    key="catalog_search"
                )

            with col_filter2:
                max_ter_filter = st.slider(
                    "TER maximo %",
                    0.0, 3.0, 3.0,
                    step=0.1,
                    key="catalog_ter"
                )

            with col_filter3:
                order_options = {
                    "Nombre": ("name", False),
                    "Rentabilidad 1A": ("return_1y", True),
                    "TER": ("ter", False),
                    "Riesgo": ("risk_level", False),
                }
                order_choice = st.selectbox(
                    "Ordenar por",
                    options=list(order_options.keys()),
                    key="catalog_order"
                )

            # Construir filtros
            filters = {}
            if search_name:
                filters['name'] = search_name
            if max_ter_filter < 3.0:
                filters['max_ter'] = max_ter_filter

            order_field, order_desc = order_options[order_choice]
            filters['order_by'] = order_field
            filters['order_desc'] = order_desc

            # Obtener fondos
            funds = service.search_funds(**filters)

            if not funds:
                st.warning("No se encontraron fondos con esos filtros.")
                st.stop()

            # Metricas resumen
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Fondos", len(funds))
            with col_m2:
                avg_ter = sum(f.ter for f in funds if f.ter) / max(len([f for f in funds if f.ter]), 1)
                st.metric("TER Promedio", f"{avg_ter:.2f}%")
            with col_m3:
                avg_ret = sum(f.return_1y for f in funds if f.return_1y) / max(len([f for f in funds if f.return_1y]), 1)
                st.metric("Rent. 1A Promedio", f"{avg_ret:+.1f}%")
            with col_m4:
                total_aum = sum(f.aum for f in funds if f.aum)
                st.metric("AUM Total", f"{total_aum:,.0f}M")

            st.divider()

            # Preparar DataFrame para tabla
            data_for_table = []
            for f in funds:
                data_for_table.append({
                    'ISIN': f.isin,
                    'Nombre': f.name[:50] + '...' if len(f.name) > 50 else f.name,
                    'Categoria': f.morningstar_category or f.category or '-',
                    'TER %': f.ter,
                    'Riesgo': f.risk_level,
                    'Rent 1A %': f.return_1y,
                    'Rent 3A %': f.return_3y,
                    'Vol 1A %': f.volatility_1y,
                })

            df_catalog = pd.DataFrame(data_for_table)

            # Tabla con seleccion
            st.markdown("**Selecciona un fondo para ver detalles:**")

            selection = st.dataframe(
                df_catalog,
                use_container_width=True,
                hide_index=True,
                height=350,
                selection_mode="single-row",
                on_select="rerun",
                column_config={
                    "TER %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Riesgo": st.column_config.NumberColumn(format="%d/7"),
                    "Rent 1A %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Rent 3A %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Vol 1A %": st.column_config.NumberColumn(format="%.2f%%"),
                }
            )

            # Drill-down cuando hay seleccion
            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_isin = df_catalog.iloc[selected_idx]['ISIN']

                # Obtener fondo completo
                fund = service.get_fund_by_isin(selected_isin)

                if fund:
                    st.divider()
                    st.markdown(f"### {fund.name}")

                    # Info y metricas
                    col_info, col_metrics = st.columns(2)

                    with col_info:
                        st.markdown("**Informacion**")
                        st.write(f"**ISIN:** {fund.isin}")
                        st.write(f"**Gestora:** {fund.manager or '-'}")
                        st.write(f"**Domicilio:** {fund.fund_domicile or '-'}")
                        st.write(f"**Divisa:** {fund.currency or 'EUR'}")
                        st.write(f"**Benchmark:** {fund.benchmark_name or '-'}")

                        if fund.url:
                            st.markdown(f"[Ver en Morningstar]({fund.url})")

                    with col_metrics:
                        st.markdown("**Metricas de Riesgo**")

                        metrics_data = {
                            'Periodo': ['1 Ano', '3 Anos', '5 Anos'],
                            'Rentabilidad': [
                                f"{fund.return_1y:+.2f}%" if fund.return_1y else '-',
                                f"{fund.return_3y:+.2f}%" if fund.return_3y else '-',
                                f"{fund.return_5y:+.2f}%" if fund.return_5y else '-',
                            ],
                            'Volatilidad': [
                                f"{fund.volatility_1y:.2f}%" if fund.volatility_1y else '-',
                                f"{fund.volatility_3y:.2f}%" if fund.volatility_3y else '-',
                                f"{fund.volatility_5y:.2f}%" if fund.volatility_5y else '-',
                            ],
                            'Sharpe': [
                                f"{fund.sharpe_1y:.2f}" if fund.sharpe_1y else '-',
                                f"{fund.sharpe_3y:.2f}" if fund.sharpe_3y else '-',
                                f"{fund.sharpe_5y:.2f}" if fund.sharpe_5y else '-',
                            ],
                        }
                        st.dataframe(
                            pd.DataFrame(metrics_data),
                            hide_index=True,
                            use_container_width=True
                        )

                    # Graficos
                    col_chart1, col_chart2 = st.columns(2)

                    with col_chart1:
                        # Asset Allocation
                        allocation = fund.get_asset_allocation()
                        if allocation:
                            st.markdown("**Asset Allocation**")

                            alloc_data = []
                            labels = {
                                'us_equity': 'RV USA',
                                'non_us_equity': 'RV Internacional',
                                'bond': 'Renta Fija',
                                'cash': 'Efectivo',
                                'other': 'Otros'
                            }
                            for key, label in labels.items():
                                val = allocation.get(key, 0)
                                if val > 0.1:
                                    alloc_data.append({'Tipo': label, 'Peso': val})

                            if alloc_data:
                                fig = px.pie(
                                    pd.DataFrame(alloc_data),
                                    values='Peso',
                                    names='Tipo',
                                    hole=0.4,
                                    color_discrete_sequence=px.colors.qualitative.Set2
                                )
                                fig.update_layout(
                                    margin=dict(t=10, b=10, l=10, r=10),
                                    height=300,
                                    legend=dict(orientation="h", yanchor="bottom", y=-0.15)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Sin datos de allocation")

                    with col_chart2:
                        # Top Holdings
                        holdings = fund.get_top_holdings()
                        if holdings:
                            st.markdown("**Top 10 Holdings**")

                            df_holdings = pd.DataFrame(holdings)

                            # Grafico de barras horizontal
                            fig = px.bar(
                                df_holdings.head(10),
                                x='weight',
                                y='name',
                                orientation='h',
                                color='weight',
                                color_continuous_scale='Blues'
                            )
                            fig.update_layout(
                                margin=dict(t=10, b=10, l=10, r=10),
                                height=300,
                                xaxis_title="Peso %",
                                yaxis_title="",
                                showlegend=False,
                                coloraxis_showscale=False
                            )
                            fig.update_yaxes(autorange="reversed")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Sin datos de holdings")

                    # Boton eliminar
                    st.divider()
                    col_del, col_space = st.columns([1, 4])
                    with col_del:
                        if st.button("🗑️ Eliminar del catalogo", type="secondary"):
                            service.repository.delete_by_isin(fund.isin)
                            st.success(f"Fondo {fund.isin} eliminado")
                            st.rerun()

            # Exportar
            st.divider()
            csv = df_catalog.to_csv(index=False)
            st.download_button(
                "📥 Exportar catalogo a CSV",
                data=csv,
                file_name="mi_catalogo_fondos.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)
