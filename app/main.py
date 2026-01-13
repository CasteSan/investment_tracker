"""
Investment Tracker - Aplicación Streamlit
Sesión 7 del Investment Tracker (actualizado v1.1 - Multi-Cartera)

Ejecutar: streamlit run app/main.py
"""

import streamlit as st
import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configuración de la página (DEBE ser lo primero)
st.set_page_config(
    page_title="Mi Cartera Personal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Investment Tracker - Sistema de Gestión de Cartera Personal"
    }
)

# Importar módulos del proyecto
try:
    from src.portfolio import Portfolio
    from src.database import Database
    from src.tax_calculator import TaxCalculator
    from src.dividends import DividendManager
    from src.benchmarks import BenchmarkComparator, YFINANCE_AVAILABLE
    from src.core.profile_manager import ProfileManager, get_profile_manager
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    IMPORT_ERROR = str(e)

# CSS personalizado
st.markdown("""
<style>
    /* Métricas más grandes */
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
    }
    
    /* Colores para ganancias/pérdidas */
    .gain { color: #00c853; }
    .loss { color: #ff1744; }
    
    /* Título principal */
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    
    /* Subtítulos de sección */
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Página principal de la aplicación"""
    
    # Título principal
    st.markdown('<p class="main-title">📊 Mi Cartera Personal</p>', unsafe_allow_html=True)
    
    # Verificar que los módulos están disponibles
    if not MODULES_AVAILABLE:
        st.error(f"❌ Error importando módulos: {IMPORT_ERROR}")
        st.info("Asegúrate de que todos los módulos están en la carpeta `src/`")
        return
    
    # Sidebar - Configuración global
    with st.sidebar:
        # =================================================================
        # SELECTOR DE CARTERA (Multi-Portfolio)
        # =================================================================
        st.header("💼 Cartera")

        profile_manager = get_profile_manager()
        profiles = profile_manager.get_profile_names()

        # Si no hay perfiles, crear uno por defecto
        if not profiles:
            profile_manager.create_profile('Principal')
            profiles = profile_manager.get_profile_names()

        # Inicializar session_state si no existe
        if 'current_profile' not in st.session_state:
            st.session_state['current_profile'] = profile_manager.get_default_profile()

        # Selector de cartera
        selected_profile = st.selectbox(
            "Seleccionar cartera",
            profiles,
            index=profiles.index(st.session_state['current_profile']) if st.session_state['current_profile'] in profiles else 0,
            key="profile_selector"
        )

        # Detectar cambio de cartera
        if selected_profile != st.session_state.get('current_profile'):
            st.session_state['current_profile'] = selected_profile
            st.rerun()

        # Obtener db_path para la cartera seleccionada
        current_db_path = profile_manager.get_db_path(selected_profile)
        st.session_state['db_path'] = current_db_path

        # Botón para crear nueva cartera
        with st.expander("➕ Nueva cartera"):
            new_profile_name = st.text_input("Nombre", key="new_profile_name")
            if st.button("Crear", key="create_profile_btn"):
                if new_profile_name:
                    try:
                        profile_manager.create_profile(new_profile_name)
                        st.session_state['current_profile'] = new_profile_name
                        st.success(f"Cartera '{new_profile_name}' creada")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.warning("Introduce un nombre")

        # Configuración de la cartera actual
        with st.expander("⚙️ Configuración cartera"):
            st.caption(f"Cartera actual: **{selected_profile}**")

            # Renombrar cartera
            rename_name = st.text_input(
                "Nuevo nombre",
                key="rename_profile_name",
                placeholder=selected_profile
            )
            if st.button("Renombrar", key="rename_profile_btn"):
                if rename_name and rename_name != selected_profile:
                    try:
                        # Renombrar y obtener el nombre sanitizado
                        clean_name = profile_manager.rename_profile(selected_profile, rename_name)
                        st.session_state['current_profile'] = clean_name
                        st.success(f"Cartera renombrada a '{clean_name}'")
                        st.rerun()
                    except PermissionError:
                        st.error("No se puede renombrar: archivo en uso. Cierra otras pestañas y reintenta.")
                    except ValueError as e:
                        st.error(str(e))
                elif rename_name == selected_profile:
                    st.info("El nombre es el mismo")
                else:
                    st.warning("Introduce un nuevo nombre")

        st.divider()

        # =================================================================
        # CONFIGURACIÓN FISCAL
        # =================================================================
        st.header("⚙️ Configuración")

        # Método de cálculo fiscal
        fiscal_method = st.selectbox(
            "Método fiscal",
            ["FIFO", "LIFO"],
            help="FIFO: First In First Out (por defecto en España)\nLIFO: Last In First Out"
        )

        # Año fiscal
        from datetime import datetime
        current_year = datetime.now().year
        fiscal_year = st.selectbox(
            "Año fiscal",
            list(range(current_year, current_year - 5, -1)),
            index=0
        )

        st.divider()

        # Estado de la base de datos
        st.subheader("📁 Base de Datos")
        try:
            db = Database(db_path=current_db_path)
            stats = db.get_database_stats()
            db.close()

            st.metric("Transacciones", stats['total_transactions'])
            st.metric("Dividendos", stats['total_dividends'])
            st.metric("Activos únicos", stats['unique_tickers'])
        except Exception as e:
            st.error(f"Error: {e}")

        st.divider()

        # Info
        st.caption("Investment Tracker v1.1")
        st.caption(f"Cartera: {selected_profile}")
    
    # Guardar configuración en session_state
    st.session_state['fiscal_method'] = fiscal_method
    st.session_state['fiscal_year'] = fiscal_year
    
    # Contenido principal - Resumen ejecutivo
    st.markdown('<p class="section-title">📈 Resumen de Cartera</p>', unsafe_allow_html=True)
    
    try:
        # Obtener datos del portfolio (usando db_path de session_state)
        db_path = st.session_state.get('db_path')
        db = Database(db_path=db_path)
        portfolio = Portfolio(db_path=db_path)

        # Obtener precios de mercado actuales (igual que Dashboard)
        current_prices = db.get_all_latest_prices()

        # Métricas principales en 4 columnas
        col1, col2, col3, col4 = st.columns(4)

        # Valor total (usando precios de mercado actualizados)
        positions = portfolio.get_current_positions(current_prices=current_prices)
        total_value = positions['market_value'].sum() if not positions.empty else 0
        total_cost = positions['cost_basis'].sum() if not positions.empty else 0
        unrealized_gain = positions['unrealized_gain'].sum() if not positions.empty else 0
        unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0
        
        with col1:
            st.metric(
                "💰 Valor Total",
                f"{total_value:,.2f}€",
                help="Valor de mercado actual de todas las posiciones"
            )
        
        with col2:
            st.metric(
                "📊 Invertido",
                f"{total_cost:,.2f}€",
                help="Coste total de adquisición"
            )
        
        with col3:
            delta_color = "normal" if unrealized_gain >= 0 else "inverse"
            st.metric(
                "📈 Plusvalía Latente",
                f"{unrealized_gain:,.2f}€",
                delta=f"{unrealized_pct:+.2f}%",
                delta_color=delta_color,
                help="Ganancias no realizadas"
            )
        
        # Plusvalías realizadas del año
        tax = TaxCalculator(method=fiscal_method, db_path=db_path)
        fiscal_summary = tax.get_fiscal_year_summary(fiscal_year)
        realized_gain = fiscal_summary.get('net_gain', 0)
        tax.close()
        
        with col4:
            delta_color = "normal" if realized_gain >= 0 else "inverse"
            st.metric(
                f"💵 Realizado {fiscal_year}",
                f"{realized_gain:,.2f}€",
                delta_color=delta_color,
                help=f"Plusvalías/minusvalías realizadas en {fiscal_year}"
            )
        
        portfolio.close()
        db.close()

        st.divider()
        
        # Segunda fila: Dividendos y navegación
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<p class="section-title">💵 Dividendos del Año</p>', unsafe_allow_html=True)
            
            dm = DividendManager(db_path=db_path)
            div_totals = dm.get_total_dividends(year=fiscal_year)
            dm.close()
            
            if div_totals['count'] > 0:
                subcol1, subcol2, subcol3 = st.columns(3)
                with subcol1:
                    st.metric("Cobros", div_totals['count'])
                with subcol2:
                    st.metric("Bruto", f"{div_totals['total_gross']:,.2f}€")
                with subcol3:
                    st.metric("Neto", f"{div_totals['total_net']:,.2f}€")
            else:
                st.info("No hay dividendos registrados este año")
        
        with col2:
            st.markdown('<p class="section-title">🧭 Navegación Rápida</p>', unsafe_allow_html=True)
            
            st.markdown("""
            - 📊 **Dashboard**: Vista detallada de la cartera
            - ➕ **Añadir Operación**: Registrar compras, ventas, dividendos
            - 📈 **Análisis**: Rentabilidad por activo
            - 💰 **Fiscal**: Plusvalías e informes para la renta
            - 💵 **Dividendos**: Calendario y yields
            - 🎯 **Benchmarks**: Comparación con índices
            
            👈 Usa el menú lateral para navegar
            """)
        
        st.divider()
        
        # Top posiciones
        st.markdown('<p class="section-title">🏆 Top 5 Posiciones por Valor</p>', unsafe_allow_html=True)
        
        if not positions.empty:
            top5 = positions.nlargest(5, 'market_value')[['ticker', 'name', 'quantity', 'market_value', 'unrealized_gain', 'unrealized_gain_pct']]
            top5.columns = ['Ticker', 'Nombre', 'Cantidad', 'Valor (€)', 'Ganancia (€)', 'Ganancia (%)']
            
            # Formatear
            top5['Valor (€)'] = top5['Valor (€)'].apply(lambda x: f"{x:,.2f}")
            top5['Ganancia (€)'] = top5['Ganancia (€)'].apply(lambda x: f"{x:+,.2f}")
            top5['Ganancia (%)'] = top5['Ganancia (%)'].apply(lambda x: f"{x:+.2f}%")
            
            st.dataframe(
                top5,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay posiciones en la cartera")
        
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
