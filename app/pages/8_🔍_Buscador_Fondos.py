"""
Pagina: Catalogo Inteligente de Fondos
Importa fondos desde Morningstar y explora el catalogo
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import sys
from pathlib import Path

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Autenticacion (DEBE ser antes de cualquier otro st.*)
from app.components.auth import require_auth
if not require_auth("Catalogo de Fondos", "🔍"):
    st.stop()

from src.services.fund_service import FundService
from src.providers.morningstar import FundNotFoundError, FundDataProviderError
from src.data.models import FUND_RISK_LEVELS


# =============================================================================
# FUNCIONES CACHEADAS PARA RENDIMIENTO
# =============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_categories(db_path: str):
    """Obtiene categorias de la BD con cache de 1 minuto."""
    with FundService(db_path=db_path) as service:
        return service.get_all_categories()


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_funds(db_path: str, _cache_key: str, **filters):
    """
    Obtiene fondos con cache de 5 minutos.
    _cache_key se usa para invalidar la cache cuando hay cambios.
    """
    with FundService(db_path=db_path) as service:
        return service.search_funds(**filters)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_fund_count(db_path: str, _cache_key: str):
    """Verifica si hay fondos en el catalogo con cache."""
    with FundService(db_path=db_path) as service:
        return service.has_funds()


def invalidate_fund_cache():
    """Invalida la cache de fondos cuando hay cambios."""
    get_cached_funds.clear()
    get_cached_fund_count.clear()
    get_cached_categories.clear()

st.title("🔍 Catalogo Inteligente de Fondos")

# Obtener db_path de session_state (multi-portfolio)
db_path = st.session_state.get('db_path')

# Cache key para invalidacion
if 'fund_cache_key' not in st.session_state:
    st.session_state.fund_cache_key = "v1"

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

        # Graficos: Sectores, Paises, Holdings
        allocation = preview.get('allocation', {})

        # Fila 1: Sectores y Paises
        col_sectors, col_countries = st.columns(2)

        with col_sectors:
            sectors = allocation.get('sectors', [])
            if sectors:
                st.markdown("**Sectores**")
                df_sectors = pd.DataFrame(sectors)
                fig = px.pie(
                    df_sectors,
                    values='weight',
                    names='name',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=250,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(size=10))
                )
                fig.update_traces(textposition='inside', textinfo='percent')
                st.plotly_chart(fig, use_container_width=True)

        with col_countries:
            countries = allocation.get('countries', [])
            if countries:
                st.markdown("**Paises (Top 10)**")
                df_countries = pd.DataFrame(countries[:10])
                fig = px.bar(
                    df_countries,
                    x='weight',
                    y='name',
                    orientation='h',
                    color='weight',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=250,
                    xaxis_title="Peso %",
                    yaxis_title="",
                    showlegend=False,
                    coloraxis_showscale=False
                )
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

        # Fila 2: Asset Allocation y Holdings
        col_alloc, col_hold = st.columns(2)

        with col_alloc:
            if allocation:
                st.markdown("**Asset Allocation**")
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
                    if val > 0.1:
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
                        margin=dict(t=10, b=10, l=10, r=10),
                        height=220,
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
                    height=220
                )

        st.divider()

        # Selector de categoria personalizada (dinamica desde BD)
        st.markdown("**Asignar categoria personalizada:**")

        # Obtener categorias de la BD
        db_categories = get_cached_categories(db_path)
        category_options = ["", "➕ Crear nueva..."] + db_categories

        selected_category = st.selectbox(
            "Categoria",
            options=category_options,
            index=0,
            format_func=lambda x: "Seleccionar categoria..." if x == "" else x,
            key="import_custom_category",
            label_visibility="collapsed"
        )

        # Si selecciona "Crear nueva", mostrar input
        final_category = None
        if selected_category == "➕ Crear nueva...":
            col_new, col_add = st.columns([3, 1])
            with col_new:
                new_cat_name = st.text_input(
                    "Nombre de la nueva categoria",
                    placeholder="Ej: RV Small Caps",
                    key="new_category_name",
                    label_visibility="collapsed"
                )
            with col_add:
                if st.button("Crear", type="secondary"):
                    if new_cat_name.strip():
                        with FundService(db_path=db_path) as svc:
                            if svc.add_category(new_cat_name.strip()):
                                st.success(f"Categoria '{new_cat_name}' creada")
                                invalidate_fund_cache()
                                st.rerun()
                            else:
                                st.warning("La categoria ya existe")
            final_category = new_cat_name.strip() if new_cat_name else None
        elif selected_category:
            final_category = selected_category

        # Boton guardar
        col_save, col_cancel = st.columns([1, 3])

        with col_save:
            if st.button("💾 Guardar en Base de Datos", type="primary", use_container_width=True):
                with st.spinner("Guardando..."):
                    try:
                        with FundService(db_path=db_path) as service:
                            fund = service.fetch_and_import_fund(preview['isin'])
                            # Guardar categoria personalizada si se seleccionó
                            if final_category:
                                fund.custom_category = final_category
                                service.repository.update(fund)
                            st.success(f"Fondo guardado: {fund.name}")
                            st.session_state.fund_preview = None
                            invalidate_fund_cache()
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

            # =================================================================
            # FILTRO POR CATEGORIA PERSONALIZADA (Pills - dinamico desde BD)
            # =================================================================
            st.markdown("**Filtrar por categoria:**")
            db_categories = service.get_all_categories()
            category_options = ["Todas"] + db_categories
            selected_cat_filter = st.radio(
                "Categoria",
                options=category_options,
                horizontal=True,
                key="catalog_category_filter",
                label_visibility="collapsed"
            )

            # Filtros adicionales en linea
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
            all_funds = service.search_funds(**filters)

            # Filtrar por categoria personalizada
            if selected_cat_filter != "Todas":
                funds = [f for f in all_funds if f.custom_category == selected_cat_filter]
            else:
                funds = all_funds

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
                    'Nombre': f.name[:45] + '...' if len(f.name) > 45 else f.name,
                    'Mi Cat.': f.custom_category or '-',
                    'TER %': f.ter,
                    'Riesgo': f.risk_level,
                    'Rent 1A %': f.return_1y,
                    'Rent 3A %': f.return_3y,
                })

            df_catalog = pd.DataFrame(data_for_table)

            # =================================================================
            # PAGINACION
            # =================================================================
            ITEMS_PER_PAGE = 10
            total_items = len(df_catalog)
            total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

            # Inicializar pagina en session_state
            if 'catalog_page' not in st.session_state:
                st.session_state.catalog_page = 1

            # Asegurar que la pagina es valida
            if st.session_state.catalog_page > total_pages:
                st.session_state.catalog_page = 1

            # Controles de paginacion
            col_prev, col_info, col_next = st.columns([1, 2, 1])

            with col_prev:
                if st.button("← Anterior", disabled=st.session_state.catalog_page <= 1):
                    st.session_state.catalog_page -= 1
                    st.rerun()

            with col_info:
                st.markdown(
                    f"<div style='text-align: center; padding: 8px;'>"
                    f"Pagina <b>{st.session_state.catalog_page}</b> de <b>{total_pages}</b> "
                    f"({total_items} fondos)"
                    f"</div>",
                    unsafe_allow_html=True
                )

            with col_next:
                if st.button("Siguiente →", disabled=st.session_state.catalog_page >= total_pages):
                    st.session_state.catalog_page += 1
                    st.rerun()

            # Slice del DataFrame para la pagina actual
            start_idx = (st.session_state.catalog_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            df_page = df_catalog.iloc[start_idx:end_idx]

            # Tabla con seleccion
            st.markdown("**Selecciona un fondo para ver detalles:**")

            selection = st.dataframe(
                df_page,
                use_container_width=True,
                hide_index=True,
                height=400,
                selection_mode="single-row",
                on_select="rerun",
                column_config={
                    "Mi Cat.": st.column_config.TextColumn(width="small"),
                    "TER %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Riesgo": st.column_config.NumberColumn(format="%d/7"),
                    "Rent 1A %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Rent 3A %": st.column_config.NumberColumn(format="%+.2f%%"),
                }
            )

            # Drill-down cuando hay seleccion
            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_isin = df_page.iloc[selected_idx]['ISIN']

                # Obtener fondo completo
                fund = service.get_fund_by_isin(selected_isin)

                if fund:
                    st.divider()

                    # =================================================================
                    # DASHBOARD DEL FONDO
                    # =================================================================

                    # Titulo con nombre
                    st.markdown(f"## 📊 {fund.name}")

                    # -----------------------------------------------------------------
                    # FILA 1: KPIs
                    # -----------------------------------------------------------------
                    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

                    with kpi1:
                        st.metric("ISIN", fund.isin)
                    with kpi2:
                        st.metric("Categoria", fund.morningstar_category or fund.category or "-")
                    with kpi3:
                        ter_val = f"{fund.ter:.2f}%" if fund.ter else "-"
                        st.metric("TER", ter_val)
                    with kpi4:
                        risk_val = f"{fund.risk_level}/7" if fund.risk_level else "-"
                        st.metric("Riesgo SRRI", risk_val)
                    with kpi5:
                        ytd = fund.return_ytd
                        if ytd is not None:
                            delta_color = "normal" if ytd >= 0 else "inverse"
                            st.metric("Rent. YTD", f"{ytd:+.2f}%", delta=f"{ytd:+.2f}%", delta_color=delta_color)
                        else:
                            st.metric("Rent. YTD", "-")

                    st.divider()

                    # -----------------------------------------------------------------
                    # FILA 2: Grafico NAV + Barras Rentabilidad
                    # -----------------------------------------------------------------
                    col_nav, col_bars = st.columns(2)

                    with col_nav:
                        st.markdown("**Valor Liquidativo (NAV)**")

                        # Obtener historico NAV con fallback defensivo
                        nav_df = pd.DataFrame()
                        nav_years = 3
                        nav_loaded = False

                        # Intentar primero 3 años, luego 1 año si falla
                        for years_attempt in [3, 1]:
                            try:
                                nav_df = service.get_fund_nav_history(fund.isin, years=years_attempt)
                                if nav_df is not None and not nav_df.empty:
                                    if 'date' in nav_df.columns and 'nav' in nav_df.columns:
                                        # Limpiar NaN values
                                        nav_df = nav_df.dropna(subset=['nav'])
                                        if len(nav_df) >= 2:
                                            nav_years = years_attempt
                                            nav_loaded = True
                                            break
                            except Exception:
                                continue

                        if nav_loaded:
                            # Calcular rentabilidad del periodo (defensivo)
                            try:
                                nav_inicial = float(nav_df['nav'].iloc[0])
                                nav_final = float(nav_df['nav'].iloc[-1])
                                if nav_inicial > 0:
                                    nav_return = ((nav_final - nav_inicial) / nav_inicial) * 100
                                    nav_color = '#28a745' if nav_return >= 0 else '#dc3545'
                                    st.markdown(
                                        f"<span style='color:{nav_color}; font-size:18px; font-weight:bold;'>({nav_return:+.1f}%)</span>",
                                        unsafe_allow_html=True
                                    )
                            except Exception:
                                pass  # Si falla el cálculo, no mostramos KPI pero sí el gráfico

                            fig_nav = go.Figure()
                            fig_nav.add_trace(go.Scatter(
                                x=nav_df['date'],
                                y=nav_df['nav'],
                                mode='lines',
                                fill='tozeroy',
                                fillcolor='rgba(0, 123, 255, 0.15)',
                                line=dict(color='#007bff', width=2.5),
                                name='NAV',
                                hovertemplate='%{x|%d %b %Y}<br>NAV: %{y:.2f}<extra></extra>'
                            ))
                            fig_nav.update_layout(
                                margin=dict(t=10, b=40, l=50, r=10),
                                height=500,
                                xaxis_title="",
                                yaxis_title="NAV",
                                showlegend=False,
                                hovermode='x unified',
                                xaxis=dict(
                                    rangeslider=dict(visible=False),
                                    type='date'
                                )
                            )
                            st.plotly_chart(
                                fig_nav,
                                use_container_width=True,
                                config={'scrollZoom': True, 'displayModeBar': True}
                            )
                            st.caption(f"Ultimos {nav_years} {'ano' if nav_years == 1 else 'anos'} | Zoom: scroll o arrastra")
                        else:
                            st.warning("Grafico historico no disponible temporalmente desde la fuente.")

                    with col_bars:
                        st.markdown("**Rentabilidad por Periodo**")
                        # Preparar datos de rentabilidad usando datos guardados en BD
                        returns_data = []
                        periods = [
                            ('YTD', fund.return_ytd),
                            ('1A', fund.return_1y),
                            ('3A', fund.return_3y),
                            ('5A', fund.return_5y),
                        ]

                        for label, val in periods:
                            if val is not None:
                                returns_data.append({
                                    'Periodo': label,
                                    'Rentabilidad': val,
                                    'Color': 'green' if val >= 0 else 'red'
                                })

                        if returns_data:
                            df_returns = pd.DataFrame(returns_data)
                            colors = ['#28a745' if v >= 0 else '#dc3545' for v in df_returns['Rentabilidad']]

                            # Lógica condicional: barras pequeñas (<5%) etiqueta fuera, grandes dentro
                            text_positions = []
                            text_colors = []
                            for v in df_returns['Rentabilidad']:
                                if abs(v) < 5:
                                    text_positions.append('outside')
                                    text_colors.append('#333333')  # Negro/gris oscuro
                                else:
                                    text_positions.append('inside')
                                    text_colors.append('white')

                            fig_bars = go.Figure(data=[
                                go.Bar(
                                    x=df_returns['Periodo'],
                                    y=df_returns['Rentabilidad'],
                                    marker_color=colors,
                                    text=[f"{v:+.1f}%" for v in df_returns['Rentabilidad']],
                                    textposition=text_positions,
                                    textfont=dict(size=22, family='Arial Black'),
                                    insidetextanchor='middle',
                                    width=0.6
                                )
                            ])
                            # Aplicar colores de texto por barra
                            fig_bars.update_traces(textfont_color=text_colors)

                            fig_bars.update_layout(
                                margin=dict(t=30, b=40, l=50, r=10),
                                height=500,
                                xaxis_title="",
                                yaxis_title="Rentabilidad %",
                                showlegend=False,
                                bargap=0.25,
                                yaxis=dict(tickfont=dict(size=14)),
                                xaxis=dict(tickfont=dict(size=16))
                            )
                            fig_bars.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                            st.plotly_chart(fig_bars, use_container_width=True)
                        else:
                            st.info("Sin datos de rentabilidad")

                    st.divider()

                    # -----------------------------------------------------------------
                    # FILA 3: Treemap Holdings + Donuts Sector/Pais
                    # -----------------------------------------------------------------
                    # Obtener datos de allocation con parseo robusto
                    allocation_raw = fund.asset_allocation
                    if isinstance(allocation_raw, str) and allocation_raw:
                        try:
                            allocation = json.loads(allocation_raw)
                        except json.JSONDecodeError:
                            allocation = {}
                    elif isinstance(allocation_raw, dict):
                        allocation = allocation_raw
                    else:
                        allocation = fund.get_asset_allocation() or {}

                    # Obtener holdings con parseo robusto
                    holdings_raw = fund.top_holdings
                    if isinstance(holdings_raw, str) and holdings_raw:
                        try:
                            holdings = json.loads(holdings_raw)
                        except json.JSONDecodeError:
                            holdings = []
                    elif isinstance(holdings_raw, list):
                        holdings = holdings_raw
                    else:
                        holdings = fund.get_top_holdings() or []

                    col_tree, col_donuts = st.columns([1, 1])

                    with col_tree:
                        st.markdown("**Top Holdings por Sector**")
                        if holdings and len(holdings) > 0:
                            df_holdings = pd.DataFrame(holdings)
                            if 'name' in df_holdings.columns and 'weight' in df_holdings.columns:
                                # Asegurar que sector existe, si no poner "Otros"
                                if 'sector' not in df_holdings.columns:
                                    df_holdings['sector'] = 'Otros'
                                df_holdings['sector'] = df_holdings['sector'].fillna('Otros')
                                df_holdings['sector'] = df_holdings['sector'].replace('', 'Otros')

                                # Crear treemap agrupado por sector
                                fig_tree = px.treemap(
                                    df_holdings,
                                    path=['sector', 'name'],
                                    values='weight',
                                    color='sector',
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    hover_data={'weight': ':.2f%'}
                                )
                                fig_tree.update_layout(
                                    margin=dict(t=10, b=10, l=10, r=10),
                                    height=600,
                                    coloraxis_showscale=False
                                )
                                fig_tree.update_traces(
                                    textinfo='label+percent entry',
                                    textfont_size=18,
                                    marker=dict(cornerradius=5)
                                )
                                st.plotly_chart(fig_tree, use_container_width=True)
                                st.caption("*Limitado a Top 10 por API de Morningstar")
                            else:
                                st.info("Formato de holdings invalido")
                        else:
                            st.info("Sin datos de holdings. Pulsa 'Actualizar datos'")

                    with col_donuts:
                        # Dos donuts: Sector y Pais
                        sectors = allocation.get('sectors', []) if isinstance(allocation, dict) else []
                        countries = allocation.get('countries', []) if isinstance(allocation, dict) else []

                        # --- DONUT SECTORES ---
                        st.markdown("**Sectores**")
                        if sectors and len(sectors) > 0:
                            df_sec = pd.DataFrame(sectors[:8])
                            if 'name' in df_sec.columns and 'weight' in df_sec.columns:
                                # Crear etiquetas personalizadas: "Nombre XX.X%"
                                # Ocultar etiquetas para valores < 5%
                                labels_sec = []
                                for _, row in df_sec.iterrows():
                                    if row['weight'] >= 5:
                                        labels_sec.append(f"{row['name']} {row['weight']:.1f}%")
                                    else:
                                        labels_sec.append('')

                                fig_sec = go.Figure(data=[go.Pie(
                                    labels=df_sec['name'],
                                    values=df_sec['weight'],
                                    hole=0.35,
                                    text=labels_sec,
                                    textposition='outside',
                                    textinfo='text',
                                    textfont=dict(size=16, family='Arial'),
                                    insidetextorientation='horizontal',
                                    marker=dict(colors=px.colors.qualitative.Set2),
                                    hovertemplate='%{label}<br>%{value:.1f}%<extra></extra>'
                                )])
                                fig_sec.update_layout(
                                    margin=dict(t=40, b=40, l=60, r=60),
                                    height=300,
                                    showlegend=False,
                                    uniformtext_minsize=14,
                                    uniformtext_mode='hide'
                                )
                                st.plotly_chart(fig_sec, use_container_width=True)
                            else:
                                st.caption("Formato invalido")
                        else:
                            st.caption("Sin datos de sectores")

                        # --- DONUT PAISES ---
                        st.markdown("**Paises**")
                        if countries and len(countries) > 0:
                            df_cty = pd.DataFrame(countries[:8])
                            if 'name' in df_cty.columns and 'weight' in df_cty.columns:
                                # Crear etiquetas personalizadas: "Nombre XX.X%"
                                # Ocultar etiquetas para valores < 5%
                                labels_cty = []
                                for _, row in df_cty.iterrows():
                                    if row['weight'] >= 5:
                                        labels_cty.append(f"{row['name']} {row['weight']:.1f}%")
                                    else:
                                        labels_cty.append('')

                                fig_cty = go.Figure(data=[go.Pie(
                                    labels=df_cty['name'],
                                    values=df_cty['weight'],
                                    hole=0.35,
                                    text=labels_cty,
                                    textposition='outside',
                                    textinfo='text',
                                    textfont=dict(size=16, family='Arial'),
                                    insidetextorientation='horizontal',
                                    marker=dict(colors=px.colors.qualitative.Pastel),
                                    hovertemplate='%{label}<br>%{value:.1f}%<extra></extra>'
                                )])
                                fig_cty.update_layout(
                                    margin=dict(t=40, b=40, l=60, r=60),
                                    height=300,
                                    showlegend=False,
                                    uniformtext_minsize=14,
                                    uniformtext_mode='hide'
                                )
                                st.plotly_chart(fig_cty, use_container_width=True)
                            else:
                                st.caption("Formato invalido")
                        else:
                            st.caption("Sin datos de paises")

                        # Tabla resumen debajo de los donuts
                        st.markdown("**Desglose detallado**")
                        tab_sec, tab_cty = st.tabs(["Sectores", "Paises"])

                        with tab_sec:
                            if sectors and len(sectors) > 0:
                                df_sec_table = pd.DataFrame(sectors)
                                if 'weight' in df_sec_table.columns:
                                    df_sec_table['weight'] = df_sec_table['weight'].apply(lambda x: f"{x:.2f}%")
                                    df_sec_table.columns = ['Sector', 'Peso']
                                    st.dataframe(df_sec_table, hide_index=True, height=150)
                            else:
                                st.caption("Pulsa 'Actualizar datos' para cargar sectores")

                        with tab_cty:
                            if countries and len(countries) > 0:
                                df_cty_table = pd.DataFrame(countries[:10])
                                if 'weight' in df_cty_table.columns:
                                    df_cty_table['weight'] = df_cty_table['weight'].apply(lambda x: f"{x:.2f}%")
                                    df_cty_table.columns = ['Pais', 'Peso']
                                    st.dataframe(df_cty_table, hide_index=True, height=150)
                            else:
                                st.caption("Pulsa 'Actualizar datos' para cargar paises")

                    # -----------------------------------------------------------------
                    # INFO ADICIONAL + ACCIONES
                    # -----------------------------------------------------------------
                    st.divider()

                    col_cat, col_info, col_actions = st.columns([1, 2, 1])

                    with col_cat:
                        st.markdown("**Mi Categoria:**")
                        # Obtener categorias dinamicas de la BD
                        edit_categories = service.get_all_categories()
                        current_cat = fund.custom_category or ""
                        cat_options = ["", "➕ Nueva..."] + edit_categories
                        current_idx = cat_options.index(current_cat) if current_cat in cat_options else 0

                        new_category = st.selectbox(
                            "Cambiar categoria",
                            options=cat_options,
                            index=current_idx,
                            format_func=lambda x: "Sin categoria" if x == "" else x,
                            key=f"edit_cat_{fund.isin}",
                            label_visibility="collapsed"
                        )

                        # Si selecciona crear nueva
                        if new_category == "➕ Nueva...":
                            new_cat_input = st.text_input(
                                "Nueva categoria",
                                key=f"new_cat_{fund.isin}",
                                placeholder="Nombre...",
                                label_visibility="collapsed"
                            )
                            if st.button("Crear y asignar", key=f"create_cat_{fund.isin}"):
                                if new_cat_input.strip():
                                    service.add_category(new_cat_input.strip())
                                    fund.custom_category = new_cat_input.strip()
                                    service.repository.update(fund)
                                    invalidate_fund_cache()
                                    st.success(f"Categoria '{new_cat_input}' creada y asignada")
                                    st.rerun()
                        elif new_category != current_cat:
                            fund.custom_category = new_category if new_category else None
                            service.repository.update(fund)
                            invalidate_fund_cache()
                            st.success("Categoria actualizada")
                            st.rerun()

                    with col_info:
                        with st.expander("Ver informacion adicional"):
                            info_col1, info_col2, info_col3 = st.columns(3)
                            with info_col1:
                                st.write(f"**Gestora:** {fund.manager or '-'}")
                                st.write(f"**Domicilio:** {fund.fund_domicile or '-'}")
                                st.write(f"**Divisa:** {fund.currency or 'EUR'}")
                            with info_col2:
                                st.write(f"**Benchmark:** {fund.benchmark_name or '-'}")
                                st.write(f"**AUM:** {fund.aum:,.0f}M EUR" if fund.aum else "**AUM:** -")
                                st.write(f"**Distribucion:** {fund.distribution_policy or '-'}")
                            with info_col3:
                                st.write(f"**Vol 1A:** {fund.volatility_1y:.2f}%" if fund.volatility_1y else "**Vol 1A:** -")
                                st.write(f"**Vol 3A:** {fund.volatility_3y:.2f}%" if fund.volatility_3y else "**Vol 3A:** -")
                                st.write(f"**Sharpe 1A:** {fund.sharpe_1y:.2f}" if fund.sharpe_1y else "**Sharpe 1A:** -")

                            if fund.url:
                                st.markdown(f"[🔗 Ver ficha en Morningstar]({fund.url})")

                    with col_actions:
                        if st.button("🔄 Actualizar datos", type="primary", use_container_width=True):
                            with st.spinner("Actualizando desde Morningstar..."):
                                try:
                                    updated = service.fetch_and_import_fund(fund.isin)
                                    st.success(f"Datos actualizados")
                                    invalidate_fund_cache()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                        if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
                            service.repository.delete_by_isin(fund.isin)
                            st.success(f"Fondo {fund.isin} eliminado")
                            invalidate_fund_cache()
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
