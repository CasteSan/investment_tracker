"""
Investment Tracker - Aplicación Streamlit
Sesión 7 del Investment Tracker

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
            db = Database()
            stats = db.get_database_stats()
            db.close()
            
            st.metric("Transacciones", stats['total_transactions'])
            st.metric("Dividendos", stats['total_dividends'])
            st.metric("Activos únicos", stats['unique_tickers'])
        except Exception as e:
            st.error(f"Error: {e}")
        
        st.divider()
        
        # Info
        st.caption("Investment Tracker v1.0")
        st.caption("Sesiones 1-7")
    
    # Guardar configuración en session_state
    st.session_state['fiscal_method'] = fiscal_method
    st.session_state['fiscal_year'] = fiscal_year
    
    # Contenido principal - Resumen ejecutivo
    st.markdown('<p class="section-title">📈 Resumen de Cartera</p>', unsafe_allow_html=True)
    
    try:
        # Obtener datos del portfolio
        portfolio = Portfolio()
        
        # Métricas principales en 4 columnas
        col1, col2, col3, col4 = st.columns(4)
        
        # Valor total
        positions = portfolio.get_current_positions()
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
        tax = TaxCalculator(method=fiscal_method)
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
        
        st.divider()
        
        # Segunda fila: Dividendos y navegación
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<p class="section-title">💵 Dividendos del Año</p>', unsafe_allow_html=True)
            
            dm = DividendManager()
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
