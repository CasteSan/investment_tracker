"""
Página de Configuración del Investment Tracker.

Esta página permite:
- Configurar opciones fiscales (FIFO/LIFO, año fiscal)
- Gestionar activos (tickers, tipos, divisas)
- Ajustar preferencias de visualización
- Ver información del sistema (logs, estadísticas, versión)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
import sys

# Configurar path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Autenticacion (DEBE ser antes de cualquier otro st.*)
from app.components.auth import require_auth
if not require_auth("Configuración", "⚙️"):
    st.stop()

# Imports de los módulos del proyecto
from src.database import Database
from src.logger import get_logger

logger = get_logger(__name__)

st.title("⚙️ Configuración")
st.markdown("Personaliza tu experiencia con Investment Tracker")

# Inicializar base de datos (usando cartera seleccionada)
db_path = st.session_state.get('db_path')
db = Database(db_path=db_path)

# ============================================================================
# INICIALIZAR SESSION STATE PARA CONFIGURACIÓN
# ============================================================================
# Valores por defecto de configuración
DEFAULT_CONFIG = {
    'fiscal_method': 'FIFO',
    'fiscal_year': datetime.now().year,
    'default_currency': 'EUR',
    'default_asset_type': 'accion',
    'decimal_places': 2,
    'show_percentages': True,
    'app_version': '1.0.0'
}

# Cargar configuración en session_state si no existe
for key, default_value in DEFAULT_CONFIG.items():
    if f'config_{key}' not in st.session_state:
        st.session_state[f'config_{key}'] = default_value

# ============================================================================
# FUNCIÓN PARA GUARDAR CONFIGURACIÓN
# ============================================================================
def save_config():
    """Guarda la configuración actual (en memoria/session_state)."""
    logger.info("Configuración guardada correctamente")
    st.success("✅ Configuración guardada correctamente")

# ============================================================================
# TABS DE CONFIGURACIÓN
# ============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "💰 Configuración Fiscal",
    "📊 Gestión de Activos", 
    "🎨 Preferencias de Visualización",
    "ℹ️ Información del Sistema"
])

# ============================================================================
# TAB 1: CONFIGURACIÓN FISCAL
# ============================================================================
with tab1:
    st.header("💰 Configuración Fiscal")
    st.markdown("""
    Configura las opciones relacionadas con el cálculo de plusvalías y minusvalías
    según la normativa fiscal española.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Método de Cálculo de Plusvalías")
        
        fiscal_method = st.radio(
            "Método de asignación de lotes:",
            options=['FIFO', 'LIFO'],
            index=0 if st.session_state.config_fiscal_method == 'FIFO' else 1,
            help="""
            **FIFO (First In, First Out)**: Las primeras acciones compradas son las primeras en venderse.
            Es el método obligatorio en España para acciones.
            
            **LIFO (Last In, First Out)**: Las últimas acciones compradas son las primeras en venderse.
            Solo para fondos de inversión en ciertos casos.
            """
        )
        st.session_state.config_fiscal_method = fiscal_method
        
        # Explicación del método seleccionado
        if fiscal_method == 'FIFO':
            st.info("""
            📌 **FIFO es el método obligatorio** en España para la mayoría de activos.
            Cuando vendas, se considerará que vendes primero las acciones más antiguas.
            """)
        else:
            st.warning("""
            ⚠️ **LIFO solo aplica en casos específicos** (ciertos fondos de inversión).
            Consulta con tu asesor fiscal antes de usar este método.
            """)
    
    with col2:
        st.subheader("Año Fiscal Activo")
        
        current_year = datetime.now().year
        fiscal_year = st.selectbox(
            "Año fiscal para informes:",
            options=list(range(current_year - 5, current_year + 1)),
            index=5,  # Año actual por defecto
            help="Selecciona el año fiscal para generar informes y calcular plusvalías"
        )
        st.session_state.config_fiscal_year = fiscal_year
        
        st.info(f"""
        📅 **Año fiscal seleccionado: {fiscal_year}**
        
        Los informes fiscales y cálculos de plusvalías/minusvalías
        se generarán para este año.
        """)
    
    st.divider()
    
    # Información sobre normativa fiscal española
    with st.expander("📚 Normativa Fiscal Española (Referencia)", expanded=False):
        st.markdown("""
        ### Tramos IRPF del Ahorro 2024/2025
        
        | Base Imponible | Tipo Impositivo |
        |----------------|-----------------|
        | Hasta 6.000€ | 19% |
        | 6.000€ - 50.000€ | 21% |
        | 50.000€ - 200.000€ | 23% |
        | 200.000€ - 300.000€ | 27% |
        | Más de 300.000€ | 28% |
        
        ### Reglas Importantes
        
        1. **FIFO obligatorio**: Para acciones y ETFs, las más antiguas se venden primero.
        
        2. **Regla de los 2 meses**: Si vendes con pérdidas y recompras el mismo valor
           en los 2 meses anteriores o posteriores, la minusvalía NO es deducible.
        
        3. **Traspasos entre fondos**: Los traspasos entre fondos de inversión NO generan
           fiscalidad. El coste fiscal se transfiere al nuevo fondo.
        
        4. **Compensación de pérdidas**: Las minusvalías pueden compensarse con plusvalías
           del mismo ejercicio y de los 4 años siguientes.
        """)

# ============================================================================
# TAB 2: GESTIÓN DE ACTIVOS
# ============================================================================
with tab2:
    st.header("📊 Gestión de Activos")
    st.markdown("Visualiza y gestiona los activos de tu cartera")
    
    # Obtener todos los tickers únicos de las transacciones
    try:
        all_transactions = db.get_transactions()
        if all_transactions:
            df_trans = db.transactions_to_dataframe(all_transactions)
            
            # Obtener tickers únicos con su información
            tickers_info = df_trans.groupby('ticker').agg({
                'name': 'first',
                'asset_type': 'first',
                'currency': 'first',
                'market': 'first',
                'date': ['min', 'max', 'count']
            }).reset_index()
            
            # Aplanar columnas multinivel
            tickers_info.columns = [
                'Ticker', 'Nombre', 'Tipo', 'Divisa', 'Mercado',
                'Primera Op.', 'Última Op.', 'Nº Operaciones'
            ]
            
            st.subheader("📋 Activos Registrados")
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_type = st.selectbox(
                    "Filtrar por tipo:",
                    options=['Todos', 'accion', 'fondo', 'etf'],
                    index=0
                )
            with col2:
                filter_currency = st.selectbox(
                    "Filtrar por divisa:",
                    options=['Todas'] + list(tickers_info['Divisa'].dropna().unique()),
                    index=0
                )
            with col3:
                search_ticker = st.text_input(
                    "Buscar ticker:",
                    placeholder="Ej: AAPL"
                )
            
            # Aplicar filtros
            df_filtered = tickers_info.copy()
            if filter_type != 'Todos':
                df_filtered = df_filtered[df_filtered['Tipo'] == filter_type]
            if filter_currency != 'Todas':
                df_filtered = df_filtered[df_filtered['Divisa'] == filter_currency]
            if search_ticker:
                df_filtered = df_filtered[
                    df_filtered['Ticker'].str.contains(search_ticker.upper(), na=False)
                ]
            
            # Mostrar tabla
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Primera Op.': st.column_config.DateColumn(format="DD/MM/YYYY"),
                    'Última Op.': st.column_config.DateColumn(format="DD/MM/YYYY"),
                }
            )
            
            st.info(f"📊 Total: **{len(df_filtered)}** activos diferentes")
            
        else:
            st.info("No hay transacciones registradas aún. Añade operaciones para ver tus activos.")
            
    except Exception as e:
        logger.error(f"Error al cargar activos: {e}")
        st.error(f"Error al cargar los activos: {e}")
    
    st.divider()
    
    # Configuración de valores por defecto para nuevas operaciones
    st.subheader("⚙️ Valores por Defecto para Nuevas Operaciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_currency = st.selectbox(
            "Divisa por defecto:",
            options=['EUR', 'USD', 'GBP'],
            index=['EUR', 'USD', 'GBP'].index(st.session_state.config_default_currency),
            help="Divisa que se preseleccionará al añadir nuevas operaciones"
        )
        st.session_state.config_default_currency = default_currency
    
    with col2:
        default_asset_type = st.selectbox(
            "Tipo de activo por defecto:",
            options=['accion', 'fondo', 'etf'],
            index=['accion', 'fondo', 'etf'].index(st.session_state.config_default_asset_type),
            help="Tipo de activo que se preseleccionará al añadir nuevas operaciones"
        )
        st.session_state.config_default_asset_type = default_asset_type

# ============================================================================
# TAB 3: PREFERENCIAS DE VISUALIZACIÓN
# ============================================================================
with tab3:
    st.header("🎨 Preferencias de Visualización")
    st.markdown("Personaliza cómo se muestran los datos en la aplicación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Formato de Números")
        
        decimal_places = st.slider(
            "Número de decimales:",
            min_value=0,
            max_value=4,
            value=st.session_state.config_decimal_places,
            help="Cantidad de decimales a mostrar en valores monetarios"
        )
        st.session_state.config_decimal_places = decimal_places
        
        # Preview del formato
        example_value = 1234.5678
        st.markdown(f"""
        **Vista previa:**
        - Valor original: `1234.5678`
        - Con {decimal_places} decimales: `{example_value:.{decimal_places}f}€`
        """)
    
    with col2:
        st.subheader("Opciones de Visualización")
        
        show_percentages = st.checkbox(
            "Mostrar porcentajes de ganancia/pérdida",
            value=st.session_state.config_show_percentages,
            help="Muestra el porcentaje además del valor absoluto en ganancias/pérdidas"
        )
        st.session_state.config_show_percentages = show_percentages
        
        st.markdown("---")
        
        st.markdown("""
        **Próximamente:**
        - 🌙 Modo oscuro/claro
        - 📊 Tipos de gráficos preferidos
        - 🔔 Configuración de alertas
        """)
    
    st.divider()
    
    # Botón para restablecer valores por defecto
    if st.button("🔄 Restablecer valores por defecto", type="secondary"):
        for key, value in DEFAULT_CONFIG.items():
            st.session_state[f'config_{key}'] = value
        st.success("✅ Valores restablecidos a los valores por defecto")
        st.rerun()

# ============================================================================
# TAB 4: INFORMACIÓN DEL SISTEMA
# ============================================================================
with tab4:
    st.header("ℹ️ Información del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Estadísticas de la Base de Datos")
        
        try:
            # Contar registros
            all_trans = db.get_transactions()
            all_divs = db.get_dividends()
            all_benchmarks = db.get_available_benchmarks()
            
            n_transactions = len(all_trans) if all_trans else 0
            n_dividends = len(all_divs) if all_divs else 0
            n_benchmarks = len(all_benchmarks) if all_benchmarks else 0
            
            # Calcular tipos de transacciones
            if all_trans:
                df_trans = db.transactions_to_dataframe(all_trans)
                trans_by_type = df_trans['type'].value_counts().to_dict()
            else:
                trans_by_type = {}
            
            # Mostrar estadísticas
            st.metric("Total de Transacciones", n_transactions)
            st.metric("Total de Dividendos", n_dividends)
            st.metric("Benchmarks Disponibles", n_benchmarks)
            
            if trans_by_type:
                st.markdown("**Desglose por tipo:**")
                for tipo, count in trans_by_type.items():
                    st.markdown(f"- {tipo}: {count}")
            
            # Tamaño de la base de datos (usar la cartera seleccionada)
            current_db_path = Path(db_path) if db_path else Path("data/database.db")
            if current_db_path.exists():
                db_size = current_db_path.stat().st_size / 1024  # KB
                if db_size > 1024:
                    st.metric("Tamaño de BD", f"{db_size/1024:.2f} MB")
                else:
                    st.metric("Tamaño de BD", f"{db_size:.2f} KB")
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            st.error(f"Error al obtener estadísticas: {e}")
    
    with col2:
        st.subheader("📝 Últimas Entradas del Log")
        
        # Leer las últimas líneas del archivo de log
        log_path = Path("logs/investment_tracker.log")
        
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    # Leer últimas 50 líneas
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                
                # Filtrar por nivel
                log_level = st.selectbox(
                    "Filtrar por nivel:",
                    options=['Todos', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    index=0
                )
                
                if log_level != 'Todos':
                    last_lines = [l for l in last_lines if log_level in l]
                
                # Mostrar en un área de texto
                log_content = ''.join(last_lines[-20:])  # Últimas 20 después de filtrar
                st.text_area(
                    "Log reciente:",
                    value=log_content,
                    height=300,
                    disabled=True
                )
                
                # Botón para descargar log completo
                with open(log_path, 'r', encoding='utf-8') as f:
                    full_log = f.read()
                
                st.download_button(
                    label="📥 Descargar log completo",
                    data=full_log,
                    file_name="investment_tracker.log",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Error al leer el log: {e}")
        else:
            st.info("No se ha creado aún el archivo de log.")
    
    st.divider()
    
    # Información de la aplicación
    st.subheader("🚀 Información de la Aplicación")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        **Versión:** {st.session_state.config_app_version}
        
        **Desarrollado con:**
        - Python 3.10+
        - Streamlit
        - SQLAlchemy
        - Plotly
        """)
    
    with col2:
        st.markdown("""
        **Funcionalidades:**
        - ✅ Gestión de operaciones
        - ✅ Cálculos fiscales FIFO/LIFO
        - ✅ Comparación con benchmarks
        - ✅ Gestión de dividendos
        - ✅ Informes fiscales
        """)
    
    with col3:
        st.markdown("""
        **Soporte:**
        - 📚 Documentación en `docs/`
        - 🐛 Issues en GitHub (próximamente)
        - 💬 Feedback bienvenido
        """)
    
    # Acciones de mantenimiento
    st.divider()
    st.subheader("🔧 Acciones de Mantenimiento")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Limpiar caché de precios", type="secondary"):
            try:
                from src.market_data import MarketDataManager
                mdm = MarketDataManager(db_path=db_path)
                mdm.clear_price_cache()
                mdm.close()
                st.success("✅ Caché de precios limpiada")
                logger.info("Caché de precios limpiada manualmente")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with col2:
        if st.button("📊 Recalcular posiciones", type="secondary"):
            st.info("Esta funcionalidad recalculará todas las posiciones basándose en las transacciones.")
            # TODO: Implementar recálculo de posiciones
    
    with col3:
        if st.button("💾 Exportar configuración", type="secondary"):
            # Crear dict con la configuración actual
            config_export = {
                key.replace('config_', ''): value 
                for key, value in st.session_state.items() 
                if key.startswith('config_')
            }
            
            import json
            config_json = json.dumps(config_export, indent=2, default=str)
            
            st.download_button(
                label="📥 Descargar configuración",
                data=config_json,
                file_name="investment_tracker_config.json",
                mime="application/json"
            )

# ============================================================================
# FOOTER CON BOTÓN GUARDAR
# ============================================================================
st.divider()

col1, col2, col3 = st.columns([2, 1, 2])

with col2:
    if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
        save_config()
        logger.info(f"Configuración guardada: method={st.session_state.config_fiscal_method}, "
                   f"year={st.session_state.config_fiscal_year}")
