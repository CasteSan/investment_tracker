"""
Página de Gestión de Operaciones del Investment Tracker.

Esta página permite:
- Añadir nuevas operaciones (compra, venta, dividendo, traspaso)
- Ver listado completo de operaciones con filtros
- Editar operaciones existentes
- Eliminar operaciones con confirmación
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
import sys

# Configurar path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Autenticacion (DEBE ser antes de cualquier otro st.*)
from app.components.auth import require_auth
if not require_auth("Gestión de Operaciones", "➕"):
    st.stop()

# Imports de los módulos del proyecto
from src.database import Database
from src.logger import get_logger

logger = get_logger(__name__)

st.title("➕ Gestión de Operaciones")

# Inicializar base de datos (usando cartera seleccionada)
db_path = st.session_state.get('db_path')
db = Database(db_path=db_path)

# ============================================================================
# INICIALIZAR SESSION STATE
# ============================================================================
if 'editing_transaction_id' not in st.session_state:
    st.session_state.editing_transaction_id = None
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = None
if 'operation_success' not in st.session_state:
    st.session_state.operation_success = None
if 'operation_error' not in st.session_state:
    st.session_state.operation_error = None

# Obtener valores por defecto de configuración (si existen)
default_currency = st.session_state.get('config_default_currency', 'EUR')
default_asset_type = st.session_state.get('config_default_asset_type', 'accion')

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def clear_messages():
    """Limpia los mensajes de éxito/error."""
    st.session_state.operation_success = None
    st.session_state.operation_error = None

def show_messages():
    """Muestra mensajes de éxito/error si existen."""
    if st.session_state.operation_success:
        st.success(st.session_state.operation_success)
        st.session_state.operation_success = None
    if st.session_state.operation_error:
        st.error(st.session_state.operation_error)
        st.session_state.operation_error = None

def validate_transaction_data(data: dict) -> tuple[bool, str]:
    """
    Valida los datos de una transacción antes de guardar.
    
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    # Validar campos obligatorios
    if not data.get('ticker'):
        return False, "El ticker es obligatorio"
    
    if not data.get('date'):
        return False, "La fecha es obligatoria"
    
    # Validar según tipo de operación
    op_type = data.get('type')
    
    if op_type in ['buy', 'sell']:
        if not data.get('quantity') or data['quantity'] <= 0:
            return False, "La cantidad debe ser mayor que 0"
        if not data.get('price') or data['price'] <= 0:
            return False, "El precio debe ser mayor que 0"
    
    if op_type == 'dividend':
        if not data.get('gross_amount') or data['gross_amount'] <= 0:
            return False, "El importe bruto debe ser mayor que 0"
    
    # Validar fecha no futura
    if data.get('date') and data['date'] > date.today():
        return False, "La fecha no puede ser futura"
    
    return True, ""

def get_tickers_list() -> list:
    """Obtiene lista de tickers únicos de las transacciones existentes."""
    try:
        transactions = db.get_transactions()
        if transactions:
            df = db.transactions_to_dataframe(transactions)
            return sorted(df['ticker'].dropna().unique().tolist())
    except Exception as e:
        logger.error(f"Error obteniendo tickers: {e}")
    return []

# ============================================================================
# MOSTRAR MENSAJES DE FEEDBACK
# ============================================================================
show_messages()

# ============================================================================
# SECCIÓN 1: AÑADIR NUEVA OPERACIÓN
# ============================================================================
st.header("📝 Añadir Nueva Operación")

# Tabs para diferentes tipos de operaciones
tab_buy, tab_sell, tab_dividend, tab_transfer = st.tabs([
    "🛒 Compra", 
    "💰 Venta", 
    "💵 Dividendo", 
    "🔄 Traspaso"
])

# ---------------------- TAB COMPRA ----------------------
with tab_buy:
    st.subheader("Registrar Compra")
    
    with st.form("form_compra", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buy_date = st.date_input(
                "📅 Fecha *",
                value=date.today(),
                max_value=date.today(),
                key="buy_date"
            )
            buy_ticker = st.text_input(
                "🏷️ Ticker *",
                placeholder="Ej: AAPL, TEF.MC",
                key="buy_ticker",
                help="Símbolo del activo (ej: AAPL para Apple, TEF.MC para Telefónica)"
            ).upper()
            buy_name = st.text_input(
                "📛 Nombre",
                placeholder="Ej: Apple Inc.",
                key="buy_name",
                help="Nombre descriptivo del activo (opcional)"
            )
        
        with col2:
            buy_quantity = st.number_input(
                "🔢 Cantidad *",
                min_value=0.0001,
                step=1.0,
                format="%.4f",
                key="buy_quantity",
                help="Número de acciones/participaciones"
            )
            buy_price = st.number_input(
                "💶 Precio unitario *",
                min_value=0.0001,
                step=0.01,
                format="%.4f",
                key="buy_price",
                help="Precio por acción/participación"
            )
            buy_commission = st.number_input(
                "🏦 Comisión",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=0.0,
                key="buy_commission",
                help="Comisiones del broker"
            )
        
        with col3:
            buy_currency = st.selectbox(
                "💱 Divisa",
                options=['EUR', 'USD', 'GBP'],
                index=['EUR', 'USD', 'GBP'].index(default_currency),
                key="buy_currency"
            )
            buy_asset_type = st.selectbox(
                "📊 Tipo de activo",
                options=['accion', 'fondo', 'etf'],
                index=['accion', 'fondo', 'etf'].index(default_asset_type),
                key="buy_asset_type"
            )
            buy_market = st.text_input(
                "🌍 Mercado",
                placeholder="Ej: NYSE, BME",
                key="buy_market"
            )
            buy_notes = st.text_area(
                "📝 Notas",
                placeholder="Comentarios opcionales...",
                key="buy_notes",
                height=68
            )
        
        # Cálculo del total
        if buy_quantity and buy_price:
            total = (buy_quantity * buy_price) + buy_commission
            st.metric("💰 Total a pagar", f"{total:,.2f} {buy_currency}")
        
        submitted_buy = st.form_submit_button("💾 Guardar Compra", type="primary", use_container_width=True)
        
        if submitted_buy:
            data = {
                'date': buy_date,
                'type': 'buy',
                'ticker': buy_ticker,
                'name': buy_name or None,
                'asset_type': buy_asset_type,
                'quantity': buy_quantity,
                'price': buy_price,
                'commission': buy_commission,
                'total': (buy_quantity * buy_price) + buy_commission,
                'currency': buy_currency,
                'market': buy_market or None,
                'notes': buy_notes or None
            }
            
            is_valid, error_msg = validate_transaction_data(data)
            
            if is_valid:
                try:
                    trans_id = db.add_transaction(data)
                    logger.info(f"Compra registrada: {buy_quantity} {buy_ticker} @ {buy_price} {buy_currency}")
                    st.session_state.operation_success = f"✅ Compra de {buy_quantity} {buy_ticker} registrada correctamente (ID: {trans_id})"
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error al guardar compra: {e}")
                    st.session_state.operation_error = f"❌ Error al guardar: {e}"
                    st.rerun()
            else:
                st.error(f"❌ {error_msg}")

# ---------------------- TAB VENTA ----------------------
with tab_sell:
    st.subheader("Registrar Venta")
    
    with st.form("form_venta", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            sell_date = st.date_input(
                "📅 Fecha *",
                value=date.today(),
                max_value=date.today(),
                key="sell_date"
            )
            
            # Selector de tickers existentes
            existing_tickers = get_tickers_list()
            sell_ticker_option = st.selectbox(
                "🏷️ Ticker existente",
                options=[''] + existing_tickers,
                key="sell_ticker_select",
                help="Selecciona un ticker de tu cartera"
            )
            sell_ticker_manual = st.text_input(
                "o introduce nuevo:",
                placeholder="Ticker manual",
                key="sell_ticker_manual"
            ).upper()
            sell_ticker = sell_ticker_option if sell_ticker_option else sell_ticker_manual
            
            sell_name = st.text_input(
                "📛 Nombre",
                key="sell_name"
            )
        
        with col2:
            sell_quantity = st.number_input(
                "🔢 Cantidad *",
                min_value=0.0001,
                step=1.0,
                format="%.4f",
                key="sell_quantity"
            )
            sell_price = st.number_input(
                "💶 Precio unitario *",
                min_value=0.0001,
                step=0.01,
                format="%.4f",
                key="sell_price"
            )
            sell_commission = st.number_input(
                "🏦 Comisión",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=0.0,
                key="sell_commission"
            )
        
        with col3:
            sell_currency = st.selectbox(
                "💱 Divisa",
                options=['EUR', 'USD', 'GBP'],
                index=['EUR', 'USD', 'GBP'].index(default_currency),
                key="sell_currency"
            )
            sell_asset_type = st.selectbox(
                "📊 Tipo de activo",
                options=['accion', 'fondo', 'etf'],
                key="sell_asset_type"
            )
            sell_notes = st.text_area(
                "📝 Notas",
                height=100,
                key="sell_notes"
            )
        
        # Cálculo del total
        if sell_quantity and sell_price:
            total_sell = (sell_quantity * sell_price) - sell_commission
            st.metric("💰 Total a recibir", f"{total_sell:,.2f} {sell_currency}")
        
        submitted_sell = st.form_submit_button("💾 Guardar Venta", type="primary", use_container_width=True)
        
        if submitted_sell:
            data = {
                'date': sell_date,
                'type': 'sell',
                'ticker': sell_ticker,
                'name': sell_name or None,
                'asset_type': sell_asset_type,
                'quantity': sell_quantity,
                'price': sell_price,
                'commission': sell_commission,
                'total': (sell_quantity * sell_price) - sell_commission,
                'currency': sell_currency,
                'notes': sell_notes or None
            }
            
            is_valid, error_msg = validate_transaction_data(data)
            
            if is_valid:
                try:
                    trans_id = db.add_transaction(data)
                    logger.info(f"Venta registrada: {sell_quantity} {sell_ticker} @ {sell_price} {sell_currency}")
                    st.session_state.operation_success = f"✅ Venta de {sell_quantity} {sell_ticker} registrada correctamente (ID: {trans_id})"
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error al guardar venta: {e}")
                    st.session_state.operation_error = f"❌ Error al guardar: {e}"
                    st.rerun()
            else:
                st.error(f"❌ {error_msg}")

# ---------------------- TAB DIVIDENDO ----------------------
with tab_dividend:
    st.subheader("Registrar Dividendo")
    
    with st.form("form_dividendo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            div_date = st.date_input(
                "📅 Fecha de cobro *",
                value=date.today(),
                max_value=date.today(),
                key="div_date"
            )
            
            existing_tickers = get_tickers_list()
            div_ticker_option = st.selectbox(
                "🏷️ Ticker *",
                options=[''] + existing_tickers,
                key="div_ticker_select"
            )
            div_ticker_manual = st.text_input(
                "o introduce nuevo:",
                key="div_ticker_manual"
            ).upper()
            div_ticker = div_ticker_option if div_ticker_option else div_ticker_manual
            
            div_currency = st.selectbox(
                "💱 Divisa",
                options=['EUR', 'USD', 'GBP'],
                index=['EUR', 'USD', 'GBP'].index(default_currency),
                key="div_currency"
            )
        
        with col2:
            div_gross = st.number_input(
                "💰 Importe bruto *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="div_gross",
                help="Importe antes de retenciones"
            )
            div_net = st.number_input(
                "💵 Importe neto",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key="div_net",
                help="Importe después de retenciones (si lo conoces)"
            )
            
            # Calcular retención automáticamente
            if div_gross and div_net:
                retention = div_gross - div_net
                retention_pct = (retention / div_gross) * 100 if div_gross > 0 else 0
                st.info(f"📊 Retención: {retention:.2f} {div_currency} ({retention_pct:.1f}%)")
            
            div_notes = st.text_area(
                "📝 Notas",
                placeholder="Ej: Dividendo trimestral Q3",
                key="div_notes",
                height=68
            )
        
        submitted_div = st.form_submit_button("💾 Guardar Dividendo", type="primary", use_container_width=True)
        
        if submitted_div:
            if not div_ticker:
                st.error("❌ El ticker es obligatorio")
            elif not div_gross or div_gross <= 0:
                st.error("❌ El importe bruto debe ser mayor que 0")
            else:
                data = {
                    'ticker': div_ticker,
                    'date': div_date,
                    'gross_amount': div_gross,
                    'net_amount': div_net if div_net else div_gross,
                    'withholding_tax': (div_gross - div_net) if div_net else 0,
                    'currency': div_currency,
                    'notes': div_notes or None
                }
                
                try:
                    div_id = db.add_dividend(data)
                    logger.info(f"Dividendo registrado: {div_gross} {div_currency} de {div_ticker}")
                    st.session_state.operation_success = f"✅ Dividendo de {div_gross} {div_currency} de {div_ticker} registrado (ID: {div_id})"
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error al guardar dividendo: {e}")
                    st.session_state.operation_error = f"❌ Error al guardar: {e}"
                    st.rerun()

# ---------------------- TAB TRASPASO ----------------------
with tab_transfer:
    st.subheader("Registrar Traspaso entre Fondos")
    
    st.info("""
    💡 **Nota sobre traspasos:**
    Los traspasos entre fondos de inversión en España NO generan fiscalidad.
    El coste fiscal se transfiere del fondo origen al destino.
    """)
    
    with st.form("form_traspaso", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📤 Fondo Origen**")
            trans_date = st.date_input(
                "📅 Fecha del traspaso *",
                value=date.today(),
                max_value=date.today(),
                key="trans_date"
            )
            
            existing_tickers = get_tickers_list()
            trans_from_ticker = st.selectbox(
                "🏷️ Fondo origen *",
                options=[''] + existing_tickers,
                key="trans_from_ticker"
            )
            trans_from_quantity = st.number_input(
                "🔢 Participaciones a traspasar *",
                min_value=0.0001,
                step=0.0001,
                format="%.4f",
                key="trans_from_qty"
            )
            trans_amount = st.number_input(
                "💶 Importe del traspaso *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="trans_amount",
                help="Valor de mercado en el momento del traspaso"
            )
        
        with col2:
            st.markdown("**📥 Fondo Destino**")
            trans_to_ticker = st.text_input(
                "🏷️ Ticker fondo destino *",
                placeholder="Ej: ES0000000000",
                key="trans_to_ticker"
            ).upper()
            trans_to_name = st.text_input(
                "📛 Nombre fondo destino",
                key="trans_to_name"
            )
            trans_to_quantity = st.number_input(
                "🔢 Participaciones recibidas *",
                min_value=0.0001,
                step=0.0001,
                format="%.4f",
                key="trans_to_qty"
            )
            trans_notes = st.text_area(
                "📝 Notas",
                key="trans_notes",
                height=68
            )
        
        submitted_trans = st.form_submit_button("💾 Guardar Traspaso", type="primary", use_container_width=True)
        
        if submitted_trans:
            if not trans_from_ticker or not trans_to_ticker:
                st.error("❌ Debes indicar ambos fondos (origen y destino)")
            elif not trans_from_quantity or not trans_to_quantity:
                st.error("❌ Debes indicar las participaciones de ambos fondos")
            elif not trans_amount:
                st.error("❌ Debes indicar el importe del traspaso")
            else:
                try:
                    # Registrar salida del fondo origen
                    data_out = {
                        'date': trans_date,
                        'type': 'transfer_out',
                        'ticker': trans_from_ticker,
                        'asset_type': 'fondo',
                        'quantity': trans_from_quantity,
                        'price': trans_amount / trans_from_quantity,
                        'total': trans_amount,
                        'currency': 'EUR',
                        'notes': f"Traspaso a {trans_to_ticker}. {trans_notes or ''}"
                    }
                    id_out = db.add_transaction(data_out)
                    
                    # Registrar entrada al fondo destino
                    data_in = {
                        'date': trans_date,
                        'type': 'transfer_in',
                        'ticker': trans_to_ticker,
                        'name': trans_to_name or None,
                        'asset_type': 'fondo',
                        'quantity': trans_to_quantity,
                        'price': trans_amount / trans_to_quantity,
                        'total': trans_amount,
                        'currency': 'EUR',
                        'transfer_link_id': id_out,  # Vincular con la salida
                        'notes': f"Traspaso desde {trans_from_ticker}. {trans_notes or ''}"
                    }
                    id_in = db.add_transaction(data_in)
                    
                    # Actualizar el link en la salida
                    db.update_transaction(id_out, {'transfer_link_id': id_in})
                    
                    logger.info(f"Traspaso registrado: {trans_from_ticker} -> {trans_to_ticker} ({trans_amount} EUR)")
                    st.session_state.operation_success = f"✅ Traspaso registrado: {trans_from_ticker} → {trans_to_ticker}"
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Error al guardar traspaso: {e}")
                    st.session_state.operation_error = f"❌ Error al guardar: {e}"
                    st.rerun()

# ============================================================================
# SECCIÓN 2: LISTADO DE OPERACIONES
# ============================================================================
st.divider()
st.header("📋 Listado de Operaciones")

# Filtros
with st.expander("🔍 Filtros", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_type = st.selectbox(
            "Tipo de operación:",
            options=['Todas', 'buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'],
            format_func=lambda x: {
                'Todas': '📋 Todas',
                'buy': '🛒 Compras',
                'sell': '💰 Ventas',
                'dividend': '💵 Dividendos',
                'transfer_in': '📥 Traspasos entrada',
                'transfer_out': '📤 Traspasos salida'
            }.get(x, x)
        )
    
    with col2:
        filter_ticker = st.selectbox(
            "Ticker:",
            options=['Todos'] + get_tickers_list()
        )
    
    with col3:
        filter_year = st.selectbox(
            "Año:",
            options=['Todos'] + list(range(datetime.now().year, 2019, -1))
        )
    
    with col4:
        filter_search = st.text_input(
            "Buscar:",
            placeholder="Buscar en notas..."
        )

# Obtener transacciones con filtros
try:
    # Construir filtros
    filters = {}
    if filter_type != 'Todas':
        filters['type'] = filter_type
    if filter_ticker != 'Todos':
        filters['ticker'] = filter_ticker
    if filter_year != 'Todos':
        filters['year'] = filter_year
    
    transactions = db.get_transactions(**filters)
    
    if transactions:
        df = db.transactions_to_dataframe(transactions)
        
        # Aplicar filtro de búsqueda en notas
        if filter_search:
            df = df[df['notes'].fillna('').str.contains(filter_search, case=False)]
        
        # Ordenar por fecha descendente
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        
        # Estadísticas rápidas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total operaciones", len(df))
        with col2:
            total_compras = df[df['type'] == 'buy']['total'].sum()
            st.metric("Total compras", f"{total_compras:,.2f}€")
        with col3:
            total_ventas = df[df['type'] == 'sell']['total'].sum()
            st.metric("Total ventas", f"{total_ventas:,.2f}€")
        with col4:
            n_tickers = df['ticker'].nunique()
            st.metric("Activos diferentes", n_tickers)
        
        st.markdown("---")
        
        # Paginación
        items_per_page = 15
        total_pages = (len(df) + items_per_page - 1) // items_per_page
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if total_pages > 1:
                page = st.selectbox(
                    "Página:",
                    options=range(1, total_pages + 1),
                    format_func=lambda x: f"Página {x} de {total_pages}"
                )
            else:
                page = 1
        
        # Obtener página actual
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        df_page = df.iloc[start_idx:end_idx]
        
        # Mostrar tabla con acciones
        st.markdown("### Operaciones")
        
        for idx, row in df_page.iterrows():
            original_idx = df.index[df['id'] == row['id']].tolist()[0] if 'id' in df.columns else idx
            
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 3, 2])
                
                # Icono según tipo
                type_icons = {
                    'buy': '🛒',
                    'sell': '💰',
                    'dividend': '💵',
                    'transfer_in': '📥',
                    'transfer_out': '📤'
                }
                
                with col1:
                    st.markdown(f"**{type_icons.get(row['type'], '📄')}**")
                    st.caption(row['type'])
                
                with col2:
                    st.markdown(f"**{row['ticker']}**")
                    if pd.notna(row.get('name')):
                        st.caption(row['name'][:20] + '...' if len(str(row['name'])) > 20 else row['name'])
                
                with col3:
                    st.markdown(f"📅 {row['date'].strftime('%d/%m/%Y') if hasattr(row['date'], 'strftime') else row['date']}")
                    if row['type'] in ['buy', 'sell']:
                        st.caption(f"{row['quantity']:.2f} @ {row['price']:.4f}")
                
                with col4:
                    if row['type'] in ['buy', 'sell', 'transfer_in', 'transfer_out']:
                        total_val = row.get('total', 0) or 0
                        currency = row.get('currency', 'EUR') or 'EUR'
                        color = "green" if row['type'] == 'sell' else "red" if row['type'] == 'buy' else "blue"
                        st.markdown(f"**:{color}[{total_val:,.2f} {currency}]**")
                    elif row['type'] == 'dividend':
                        st.markdown(f"**:green[+{row.get('total', 0) or 0:,.2f} €]**")
                    
                    if pd.notna(row.get('notes')) and row['notes']:
                        st.caption(f"📝 {row['notes'][:30]}...")
                
                with col5:
                    btn_col1, btn_col2 = st.columns(2)
                    
                    with btn_col1:
                        if st.button("✏️", key=f"edit_{row['id']}", help="Editar"):
                            st.session_state.editing_transaction_id = row['id']
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("🗑️", key=f"delete_{row['id']}", help="Eliminar"):
                            st.session_state.show_delete_confirm = row['id']
                            st.rerun()
                
                st.markdown("---")
        
        # Modal de confirmación de eliminación
        if st.session_state.show_delete_confirm:
            trans_id = st.session_state.show_delete_confirm
            trans_to_delete = db.get_transaction_by_id(trans_id)
            
            if trans_to_delete:
                st.warning(f"""
                ⚠️ **¿Estás seguro de que quieres eliminar esta operación?**
                
                - **ID:** {trans_id}
                - **Tipo:** {trans_to_delete.type}
                - **Ticker:** {trans_to_delete.ticker}
                - **Fecha:** {trans_to_delete.date}
                - **Total:** {trans_to_delete.total}€
                
                Esta acción no se puede deshacer.
                """)
                
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("✅ Sí, eliminar", type="primary"):
                        try:
                            db.delete_transaction(trans_id)
                            logger.info(f"Transacción eliminada: ID {trans_id}")
                            st.session_state.operation_success = f"✅ Operación {trans_id} eliminada correctamente"
                            st.session_state.show_delete_confirm = None
                            st.rerun()
                        except Exception as e:
                            logger.error(f"Error al eliminar: {e}")
                            st.session_state.operation_error = f"❌ Error al eliminar: {e}"
                            st.session_state.show_delete_confirm = None
                            st.rerun()
                
                with col2:
                    if st.button("❌ Cancelar"):
                        st.session_state.show_delete_confirm = None
                        st.rerun()
        
        # Modal de edición
        if st.session_state.editing_transaction_id:
            trans_id = st.session_state.editing_transaction_id
            trans_to_edit = db.get_transaction_by_id(trans_id)
            
            if trans_to_edit:
                st.markdown("---")
                st.subheader(f"✏️ Editando Operación #{trans_id}")
                
                with st.form(f"edit_form_{trans_id}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        edit_date = st.date_input(
                            "📅 Fecha",
                            value=trans_to_edit.date,
                            max_value=date.today()
                        )
                        edit_ticker = st.text_input(
                            "🏷️ Ticker",
                            value=trans_to_edit.ticker or ''
                        )
                        edit_name = st.text_input(
                            "📛 Nombre",
                            value=trans_to_edit.name or ''
                        )
                    
                    with col2:
                        edit_quantity = st.number_input(
                            "🔢 Cantidad",
                            value=float(trans_to_edit.quantity or 0),
                            format="%.4f"
                        )
                        edit_price = st.number_input(
                            "💶 Precio",
                            value=float(trans_to_edit.price or 0),
                            format="%.4f"
                        )
                        edit_commission = st.number_input(
                            "🏦 Comisión",
                            value=float(trans_to_edit.commission or 0),
                            format="%.2f"
                        )
                    
                    with col3:
                        edit_type = st.selectbox(
                            "📋 Tipo",
                            options=['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'],
                            index=['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'].index(trans_to_edit.type) if trans_to_edit.type in ['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'] else 0
                        )
                        edit_currency = st.selectbox(
                            "💱 Divisa",
                            options=['EUR', 'USD', 'GBP'],
                            index=['EUR', 'USD', 'GBP'].index(trans_to_edit.currency) if trans_to_edit.currency in ['EUR', 'USD', 'GBP'] else 0
                        )
                        edit_notes = st.text_area(
                            "📝 Notas",
                            value=trans_to_edit.notes or ''
                        )
                    
                    # Calcular nuevo total
                    if edit_type in ['buy', 'transfer_in']:
                        new_total = (edit_quantity * edit_price) + edit_commission
                    else:
                        new_total = (edit_quantity * edit_price) - edit_commission
                    
                    st.metric("💰 Nuevo total", f"{new_total:,.2f} {edit_currency}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.form_submit_button("💾 Guardar cambios", type="primary"):
                            update_data = {
                                'date': edit_date,
                                'type': edit_type,
                                'ticker': edit_ticker.upper(),
                                'name': edit_name or None,
                                'quantity': edit_quantity,
                                'price': edit_price,
                                'commission': edit_commission,
                                'total': new_total,
                                'currency': edit_currency,
                                'notes': edit_notes or None
                            }
                            
                            try:
                                db.update_transaction(trans_id, update_data)
                                logger.info(f"Transacción actualizada: ID {trans_id}")
                                st.session_state.operation_success = f"✅ Operación {trans_id} actualizada correctamente"
                                st.session_state.editing_transaction_id = None
                                st.rerun()
                            except Exception as e:
                                logger.error(f"Error al actualizar: {e}")
                                st.error(f"❌ Error al actualizar: {e}")
                    
                    with col2:
                        if st.form_submit_button("❌ Cancelar"):
                            st.session_state.editing_transaction_id = None
                            st.rerun()
    else:
        st.info("📭 No hay operaciones registradas con los filtros seleccionados.")
        
        st.markdown("""
        ### ¿Cómo empezar?
        
        1. **Añade tu primera compra** usando el formulario de arriba
        2. **Importa datos históricos** desde un CSV (próximamente en la sección de Configuración)
        3. **Registra dividendos** recibidos para un tracking completo
        """)

except Exception as e:
    logger.error(f"Error al cargar operaciones: {e}")
    st.error(f"Error al cargar las operaciones: {e}")

# ============================================================================
# SECCIÓN 3: ACCIONES RÁPIDAS
# ============================================================================
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📥 Importar Datos")
    st.markdown("Próximamente: Importar operaciones desde CSV/Excel")
    st.button("📁 Importar CSV", disabled=True)

with col2:
    st.markdown("### 📤 Exportar Datos")
    if st.button("📥 Exportar a CSV"):
        try:
            all_trans = db.get_transactions()
            if all_trans:
                df_export = db.transactions_to_dataframe(all_trans)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar CSV",
                    data=csv,
                    file_name=f"operaciones_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No hay operaciones para exportar")
        except Exception as e:
            st.error(f"Error al exportar: {e}")

with col3:
    st.markdown("### 🔄 Actualizar")
    if st.button("🔄 Refrescar página"):
        st.rerun()
