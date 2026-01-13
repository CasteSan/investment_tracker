"""
Pagina: Buscador de Fondos
Explora y filtra el catalogo de fondos de inversion
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.services.fund_service import FundService
from src.data.models import FUND_CATEGORIES, FUND_REGIONS, FUND_RISK_LEVELS

st.set_page_config(
    page_title="Buscador de Fondos",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Buscador de Fondos")
st.markdown("Explora el catalogo de fondos de inversion con filtros avanzados.")

# =============================================================================
# SIDEBAR - FILTROS
# =============================================================================

with st.sidebar:
    st.header("Filtros")

    # Busqueda por texto
    search_text = st.text_input(
        "Buscar por nombre",
        placeholder="Ej: Vanguard, Bestinver...",
        help="Busca en el nombre del fondo"
    )

    search_isin = st.text_input(
        "Buscar por ISIN",
        placeholder="Ej: ES0114105036",
        help="Codigo ISIN del fondo"
    )

    st.divider()

    # Filtro por categoria
    st.subheader("Categoria")
    selected_categories = st.multiselect(
        "Tipo de activo",
        options=FUND_CATEGORIES,
        default=[],
        help="Filtra por tipo de fondo"
    )

    # Filtro por region
    selected_region = st.selectbox(
        "Region",
        options=["Todas"] + FUND_REGIONS,
        help="Region geografica del fondo"
    )

    st.divider()

    # Filtro por costes
    st.subheader("Costes")
    max_ter = st.slider(
        "TER maximo (%)",
        min_value=0.0,
        max_value=3.0,
        value=3.0,
        step=0.1,
        help="Total Expense Ratio - gastos corrientes del fondo"
    )

    st.divider()

    # Filtro por riesgo
    st.subheader("Riesgo")
    risk_range = st.slider(
        "Nivel de riesgo (1-7)",
        min_value=1,
        max_value=7,
        value=(1, 7),
        help="1=Muy bajo, 7=Muy alto (clasificacion CNMV)"
    )

    st.divider()

    # Filtro por rating
    st.subheader("Rating")
    min_rating = st.slider(
        "Rating Morningstar minimo",
        min_value=1,
        max_value=5,
        value=1,
        help="Numero de estrellas Morningstar"
    )

    st.divider()

    # Filtro por rentabilidad
    st.subheader("Rentabilidad")
    min_return = st.number_input(
        "Rentabilidad 1A minima (%)",
        min_value=-100.0,
        max_value=100.0,
        value=-100.0,
        step=1.0,
        help="Rentabilidad minima a 1 ano"
    )

    st.divider()

    # Ordenamiento
    st.subheader("Ordenar por")
    order_options = {
        "Nombre": "name",
        "TER (menor a mayor)": "ter",
        "Rating (mayor a menor)": "morningstar_rating",
        "Rentabilidad 1A": "return_1y",
        "Riesgo": "risk_level",
    }
    order_by = st.selectbox(
        "Campo",
        options=list(order_options.keys())
    )
    order_desc = st.checkbox(
        "Orden descendente",
        value=order_by in ["Rating (mayor a menor)", "Rentabilidad 1A"]
    )

# =============================================================================
# CONTENIDO PRINCIPAL
# =============================================================================

try:
    with FundService() as service:
        # Verificar si hay fondos
        if not service.has_funds():
            st.warning("El catalogo de fondos esta vacio.")
            st.info("""
            Para usar el buscador, primero debes importar fondos al catalogo.

            **Opciones:**
            1. Ejecutar la migracion: `python -m src.data.migrations.001_create_funds_table`
            2. Importar datos desde un CSV o fuente externa
            """)

            # Mostrar ejemplo de como importar
            with st.expander("Ver ejemplo de importacion"):
                st.code("""
from src.services import FundService

# Datos de ejemplo
funds_data = [
    {
        'isin': 'IE00B3RBWM25',
        'name': 'Vanguard FTSE All-World UCITS ETF',
        'category': 'Renta Variable',
        'manager': 'Vanguard',
        'ter': 0.22,
        'risk_level': 5,
        'morningstar_rating': 5,
        'return_1y': 18.2,
        'region': 'Global',
    },
    # ... mas fondos
]

with FundService() as svc:
    result = svc.import_funds_bulk(funds_data)
    print(f"Importados: {result['inserted']}")
                """, language="python")

            st.stop()

        # Construir filtros
        filters = {}

        if search_text:
            filters['name'] = search_text

        if search_isin:
            filters['isin'] = search_isin

        if selected_categories:
            filters['categories'] = selected_categories

        if selected_region != "Todas":
            filters['region'] = selected_region

        if max_ter < 3.0:
            filters['max_ter'] = max_ter

        if risk_range[0] > 1:
            filters['min_risk_level'] = risk_range[0]
        if risk_range[1] < 7:
            filters['max_risk_level'] = risk_range[1]

        if min_rating > 1:
            filters['min_rating'] = min_rating

        if min_return > -100.0:
            filters['min_return_1y'] = min_return

        # Ordenamiento
        filters['order_by'] = order_options[order_by]
        filters['order_desc'] = order_desc

        # Buscar fondos
        funds = service.search_funds(**filters)
        total_funds = service.repository.count()

        # Mostrar estadisticas
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Resultados", len(funds))
        with col2:
            st.metric("Total catalogo", total_funds)
        with col3:
            if funds:
                avg_ter = sum(f.ter for f in funds if f.ter) / len([f for f in funds if f.ter])
                st.metric("TER promedio", f"{avg_ter:.2f}%")
            else:
                st.metric("TER promedio", "-")
        with col4:
            if funds:
                avg_risk = sum(f.risk_level for f in funds if f.risk_level) / len([f for f in funds if f.risk_level])
                st.metric("Riesgo promedio", f"{avg_risk:.1f}/7")
            else:
                st.metric("Riesgo promedio", "-")

        st.divider()

        if not funds:
            st.info("No se encontraron fondos con los filtros seleccionados.")
            st.stop()

        # =================================================================
        # TABLA DE RESULTADOS
        # =================================================================

        st.subheader(f"Fondos encontrados ({len(funds)})")

        # Convertir a DataFrame
        df = service._funds_to_dataframe(funds)
        df_display = service.format_funds_for_display(df)

        # Mostrar tabla
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )

        # Boton de exportar
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Exportar a CSV",
            data=csv,
            file_name="fondos_filtrados.csv",
            mime="text/csv"
        )

        st.divider()

        # =================================================================
        # DETALLE DE FONDO SELECCIONADO
        # =================================================================

        st.subheader("Detalle de fondo")

        # Selector de fondo
        fund_options = {f"{f.isin} - {f.name[:50]}": f.isin for f in funds}

        if fund_options:
            selected_fund_key = st.selectbox(
                "Selecciona un fondo para ver detalles",
                options=list(fund_options.keys())
            )

            selected_isin = fund_options[selected_fund_key]
            fund_details = service.get_fund_details(selected_isin)

            if fund_details:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Informacion General**")
                    st.write(f"**ISIN:** {fund_details.get('isin', '-')}")
                    st.write(f"**Nombre:** {fund_details.get('name', '-')}")
                    st.write(f"**Gestora:** {fund_details.get('manager', '-')}")
                    st.write(f"**Categoria:** {fund_details.get('category', '-')}")
                    st.write(f"**Region:** {fund_details.get('region', '-')}")
                    st.write(f"**Divisa:** {fund_details.get('currency', '-')}")

                with col2:
                    st.markdown("**Metricas**")

                    ter = fund_details.get('ter')
                    st.write(f"**TER:** {ter:.2f}%" if ter else "**TER:** -")

                    risk = fund_details.get('risk_level')
                    risk_name = FUND_RISK_LEVELS.get(risk, '-') if risk else '-'
                    st.write(f"**Riesgo:** {risk}/7 ({risk_name})" if risk else "**Riesgo:** -")

                    rating = fund_details.get('morningstar_rating')
                    stars = "★" * rating if rating else "-"
                    st.write(f"**Rating:** {stars}")

                    ret_1y = fund_details.get('return_1y')
                    st.write(f"**Rent. 1A:** {ret_1y:+.2f}%" if ret_1y else "**Rent. 1A:** -")

                    ret_3y = fund_details.get('return_3y')
                    st.write(f"**Rent. 3A:** {ret_3y:+.2f}%" if ret_3y else "**Rent. 3A:** -")

                # URL del fondo
                url = fund_details.get('url')
                if url:
                    st.markdown(f"[Ver ficha del fondo]({url})")

        st.divider()

        # =================================================================
        # ESTADISTICAS DEL CATALOGO
        # =================================================================

        with st.expander("Ver estadisticas del catalogo"):
            stats = service.get_catalog_stats()

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Por categoria**")
                if stats.get('by_category'):
                    cat_df = pd.DataFrame(
                        list(stats['by_category'].items()),
                        columns=['Categoria', 'Fondos']
                    )
                    st.dataframe(cat_df, hide_index=True)

            with col2:
                st.markdown("**Por nivel de riesgo**")
                if stats.get('by_risk_level'):
                    risk_data = [
                        {
                            'Nivel': f"{k}/7 - {FUND_RISK_LEVELS.get(k, '')}",
                            'Fondos': v
                        }
                        for k, v in sorted(stats['by_risk_level'].items())
                        if k is not None
                    ]
                    if risk_data:
                        risk_df = pd.DataFrame(risk_data)
                        st.dataframe(risk_df, hide_index=True)

            st.markdown("**Top gestoras**")
            if stats.get('top_managers'):
                managers_df = pd.DataFrame(
                    list(stats['top_managers'].items()),
                    columns=['Gestora', 'Fondos']
                )
                st.dataframe(managers_df, hide_index=True)

except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.exception(e)
