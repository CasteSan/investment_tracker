"""
Página: Añadir Operación
Formularios para registrar compras, ventas, dividendos y traspasos
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, date

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.database import Database
from src.dividends import DividendManager

st.set_page_config(page_title="Añadir Operación", page_icon="➕", layout="wide")

st.title("➕ Añadir Nueva Operación")

# Tabs para diferentes tipos de operaciones
tab1, tab2, tab3, tab4 = st.tabs(["🟢 Compra", "🔴 Venta", "💰 Dividendo", "🔄 Traspaso"])

# =============================================================================
# TAB 1: COMPRA
# =============================================================================
with tab1:
    st.markdown("### Registrar Compra")
    
    with st.form("form_compra", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            buy_date = st.date_input("Fecha", value=date.today(), key="buy_date")
            buy_ticker = st.text_input("Ticker *", placeholder="Ej: TEF, AAPL", key="buy_ticker").upper()
            buy_name = st.text_input("Nombre", placeholder="Ej: Telefónica", key="buy_name")
            buy_asset_type = st.selectbox("Tipo de activo", ["accion", "fondo", "etf"], key="buy_asset_type")
        
        with col2:
            buy_quantity = st.number_input("Cantidad *", min_value=0.0001, step=1.0, format="%.4f", key="buy_qty")
            buy_price = st.number_input("Precio unitario (€) *", min_value=0.0001, step=0.01, format="%.4f", key="buy_price")
            buy_commission = st.number_input("Comisión (€)", min_value=0.0, step=0.01, value=0.0, key="buy_comm")
            buy_currency = st.selectbox("Divisa", ["EUR", "USD", "GBP", "GBX", "CAD"], key="buy_currency")
        
        # Cálculo automático
        buy_total = (buy_quantity * buy_price) + buy_commission
        st.metric("💰 Total a pagar", f"{buy_total:,.2f} {buy_currency}")
        
        buy_notes = st.text_area("Notas (opcional)", key="buy_notes", height=68)
        
        submitted_buy = st.form_submit_button("💾 Guardar Compra", use_container_width=True)
        
        if submitted_buy:
            if not buy_ticker:
                st.error("❌ El ticker es obligatorio")
            elif buy_quantity <= 0:
                st.error("❌ La cantidad debe ser mayor que 0")
            elif buy_price <= 0:
                st.error("❌ El precio debe ser mayor que 0")
            else:
                try:
                    db = Database()
                    transaction_id = db.add_transaction({
                        'date': buy_date.strftime('%Y-%m-%d'),
                        'type': 'buy',
                        'ticker': buy_ticker,
                        'name': buy_name or buy_ticker,
                        'asset_type': buy_asset_type,
                        'quantity': buy_quantity,
                        'price': buy_price,
                        'commission': buy_commission,
                        'currency': buy_currency,
                        'notes': buy_notes
                    })
                    db.close()
                    
                    st.success(f"✅ Compra registrada correctamente (ID: {transaction_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# =============================================================================
# TAB 2: VENTA
# =============================================================================
with tab2:
    st.markdown("### Registrar Venta")
    
    # Obtener tickers disponibles
    db = Database()
    available_tickers = db.get_all_tickers()
    db.close()
    
    with st.form("form_venta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            sell_date = st.date_input("Fecha", value=date.today(), key="sell_date")
            
            if available_tickers:
                sell_ticker = st.selectbox("Ticker *", available_tickers, key="sell_ticker")
            else:
                sell_ticker = st.text_input("Ticker *", placeholder="Ej: TEF", key="sell_ticker_text").upper()
            
            sell_name = st.text_input("Nombre", placeholder="Ej: Telefónica", key="sell_name")
        
        with col2:
            sell_quantity = st.number_input("Cantidad *", min_value=0.0001, step=1.0, format="%.4f", key="sell_qty")
            sell_price = st.number_input("Precio unitario (€) *", min_value=0.0001, step=0.01, format="%.4f", key="sell_price")
            sell_commission = st.number_input("Comisión (€)", min_value=0.0, step=0.01, value=0.0, key="sell_comm")
            sell_currency = st.selectbox("Divisa", ["EUR", "USD", "GBP", "GBX", "CAD"], key="sell_currency")
        
        # Cálculo automático
        sell_total = (sell_quantity * sell_price) - sell_commission
        st.metric("💰 Total a recibir", f"{sell_total:,.2f} {sell_currency}")
        
        # Campo opcional para B/P ya calculado (para importaciones)
        sell_realized_gain = st.number_input(
            "Beneficio/Pérdida conocido en EUR (opcional)", 
            step=0.01, 
            format="%.2f",
            help="Si conoces el B/P real (ej: de un extracto), introdúcelo aquí",
            key="sell_gain"
        )
        
        sell_notes = st.text_area("Notas (opcional)", key="sell_notes", height=68)
        
        submitted_sell = st.form_submit_button("💾 Guardar Venta", use_container_width=True)
        
        if submitted_sell:
            ticker_value = sell_ticker if available_tickers else sell_ticker
            
            if not ticker_value:
                st.error("❌ El ticker es obligatorio")
            elif sell_quantity <= 0:
                st.error("❌ La cantidad debe ser mayor que 0")
            elif sell_price <= 0:
                st.error("❌ El precio debe ser mayor que 0")
            else:
                try:
                    db = Database()
                    
                    transaction_data = {
                        'date': sell_date.strftime('%Y-%m-%d'),
                        'type': 'sell',
                        'ticker': ticker_value,
                        'name': sell_name or ticker_value,
                        'quantity': sell_quantity,
                        'price': sell_price,
                        'commission': sell_commission,
                        'currency': sell_currency,
                        'notes': sell_notes
                    }
                    
                    # Añadir B/P si se especificó
                    if sell_realized_gain != 0:
                        transaction_data['realized_gain_eur'] = sell_realized_gain
                    
                    transaction_id = db.add_transaction(transaction_data)
                    db.close()
                    
                    st.success(f"✅ Venta registrada correctamente (ID: {transaction_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# =============================================================================
# TAB 3: DIVIDENDO
# =============================================================================
with tab3:
    st.markdown("### Registrar Dividendo")
    
    with st.form("form_dividendo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            div_date = st.date_input("Fecha de cobro", value=date.today(), key="div_date")
            
            db = Database()
            div_tickers = db.get_all_tickers()
            db.close()
            
            if div_tickers:
                div_ticker = st.selectbox("Ticker *", div_tickers, key="div_ticker")
            else:
                div_ticker = st.text_input("Ticker *", placeholder="Ej: TEF", key="div_ticker_text").upper()
            
            div_name = st.text_input("Nombre", placeholder="Ej: Telefónica", key="div_name")
        
        with col2:
            div_gross = st.number_input("Importe bruto (€) *", min_value=0.01, step=0.01, format="%.2f", key="div_gross")
            div_net = st.number_input("Importe neto (€) *", min_value=0.01, step=0.01, format="%.2f", key="div_net")
            div_currency = st.selectbox("Divisa", ["EUR", "USD", "GBP", "CAD"], key="div_currency")
        
        # Cálculo automático de retención
        if div_gross > 0 and div_net > 0:
            retention = div_gross - div_net
            retention_pct = (retention / div_gross * 100) if div_gross > 0 else 0
            st.info(f"📊 Retención: {retention:.2f}€ ({retention_pct:.1f}%)")
        
        div_ex_date = st.date_input("Fecha ex-dividendo (opcional)", value=None, key="div_ex_date")
        div_notes = st.text_area("Notas (opcional)", key="div_notes", height=68)
        
        submitted_div = st.form_submit_button("💾 Guardar Dividendo", use_container_width=True)
        
        if submitted_div:
            ticker_value = div_ticker if div_tickers else div_ticker
            
            if not ticker_value:
                st.error("❌ El ticker es obligatorio")
            elif div_gross <= 0:
                st.error("❌ El importe bruto debe ser mayor que 0")
            elif div_net <= 0:
                st.error("❌ El importe neto debe ser mayor que 0")
            elif div_net > div_gross:
                st.error("❌ El importe neto no puede ser mayor que el bruto")
            else:
                try:
                    dm = DividendManager()
                    
                    # Construir notas con ex-date si se proporcionó
                    notes = div_notes
                    if div_ex_date:
                        ex_date_str = div_ex_date.strftime('%Y-%m-%d')
                        notes = f"Ex-date: {ex_date_str}" + (f" | {notes}" if notes else "")
                    
                    dividend_id = dm.add_dividend(
                        ticker=ticker_value,
                        gross_amount=div_gross,
                        net_amount=div_net,
                        date=div_date.strftime('%Y-%m-%d'),
                        name=div_name or ticker_value,
                        currency=div_currency,
                        notes=notes
                    )
                    dm.close()
                    
                    st.success(f"✅ Dividendo registrado correctamente (ID: {dividend_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# =============================================================================
# TAB 4: TRASPASO
# =============================================================================
with tab4:
    st.markdown("### Registrar Traspaso entre Fondos")
    st.info("""💡 **Fiscalidad de traspasos en España:**
    - Los traspasos entre fondos NO generan plusvalía/minusvalía
    - El coste fiscal se MANTIENE del fondo origen al destino
    - Solo al vender el fondo destino se calcula la ganancia/pérdida
    """)
    
    with st.form("form_traspaso", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📤 Fondo Origen**")
            transfer_date = st.date_input("Fecha del traspaso", value=date.today(), key="transfer_date")
            transfer_from_ticker = st.text_input("Ticker origen *", placeholder="Ej: ES0000000001", key="transfer_from")
            transfer_from_name = st.text_input("Nombre origen", placeholder="Ej: Fondo Indexado A", key="transfer_from_name")
            transfer_quantity = st.number_input("Participaciones a traspasar *", min_value=0.0001, step=0.01, format="%.4f", key="transfer_qty")
            transfer_value = st.number_input("Valor de mercado del traspaso (€) *", min_value=0.01, step=0.01, format="%.2f", 
                                            help="Valor actual de las participaciones (NO es el coste fiscal)",
                                            key="transfer_value")
        
        with col2:
            st.markdown("**📥 Fondo Destino**")
            transfer_to_ticker = st.text_input("Ticker destino *", placeholder="Ej: ES0000000002", key="transfer_to")
            transfer_to_name = st.text_input("Nombre destino", placeholder="Ej: Fondo Indexado B", key="transfer_to_name")
            transfer_to_quantity = st.number_input("Participaciones recibidas *", min_value=0.0001, step=0.01, format="%.4f", key="transfer_to_qty")
            transfer_cost_basis = st.number_input(
                "Coste fiscal a traspasar (€) *", 
                min_value=0.01, 
                step=0.01, 
                format="%.2f",
                help="⚠️ IMPORTANTE: Este es el coste de ADQUISICIÓN original, NO el valor actual. Lo encuentras en tu informe fiscal o extracto del broker.",
                key="transfer_cost"
            )
        
        # Mostrar cálculo de plusvalía latente
        if transfer_value > 0 and transfer_cost_basis > 0:
            latent_gain = transfer_value - transfer_cost_basis
            latent_pct = (latent_gain / transfer_cost_basis * 100)
            if latent_gain >= 0:
                st.success(f"📈 Plusvalía latente (NO tributa ahora): +{latent_gain:,.2f}€ ({latent_pct:+.2f}%)")
            else:
                st.warning(f"📉 Minusvalía latente (NO se pierde): {latent_gain:,.2f}€ ({latent_pct:+.2f}%)")
        
        transfer_notes = st.text_area("Notas (opcional)", key="transfer_notes", height=68)
        
        submitted_transfer = st.form_submit_button("💾 Guardar Traspaso", use_container_width=True)
        
        if submitted_transfer:
            if not transfer_from_ticker or not transfer_to_ticker:
                st.error("❌ Los tickers de origen y destino son obligatorios")
            elif transfer_quantity <= 0 or transfer_to_quantity <= 0:
                st.error("❌ Las cantidades deben ser mayores que 0")
            elif transfer_value <= 0:
                st.error("❌ El valor de mercado debe ser mayor que 0")
            elif transfer_cost_basis <= 0:
                st.error("❌ El coste fiscal es obligatorio para calcular correctamente la fiscalidad futura")
            else:
                try:
                    db = Database()
                    
                    # Registrar salida (transfer_out)
                    # Guardamos el coste fiscal que SALE del fondo origen
                    out_id = db.add_transaction({
                        'date': transfer_date.strftime('%Y-%m-%d'),
                        'type': 'transfer_out',
                        'ticker': transfer_from_ticker.upper(),
                        'name': transfer_from_name or transfer_from_ticker,
                        'asset_type': 'fondo',
                        'quantity': transfer_quantity,
                        'price': transfer_value / transfer_quantity,  # Precio de mercado
                        'cost_basis_eur': transfer_cost_basis,  # Coste fiscal que sale
                        'currency': 'EUR',
                        'notes': f"Traspaso a {transfer_to_ticker.upper()}. {transfer_notes}".strip()
                    })
                    
                    # Registrar entrada (transfer_in)
                    # Guardamos el coste fiscal que ENTRA al fondo destino (el mismo)
                    in_id = db.add_transaction({
                        'date': transfer_date.strftime('%Y-%m-%d'),
                        'type': 'transfer_in',
                        'ticker': transfer_to_ticker.upper(),
                        'name': transfer_to_name or transfer_to_ticker,
                        'asset_type': 'fondo',
                        'quantity': transfer_to_quantity,
                        'price': transfer_value / transfer_to_quantity,  # Precio de mercado (informativo)
                        'cost_basis_eur': transfer_cost_basis,  # ¡COSTE FISCAL HEREDADO!
                        'transfer_link_id': out_id,  # Vincular con el transfer_out
                        'currency': 'EUR',
                        'notes': f"Traspaso desde {transfer_from_ticker.upper()}. Coste fiscal: {transfer_cost_basis:.2f}€. {transfer_notes}".strip()
                    })
                    
                    # Actualizar el transfer_out con el link al transfer_in
                    db.update_transaction(out_id, {'transfer_link_id': in_id})
                    
                    db.close()
                    
                    st.success(f"""✅ Traspaso registrado correctamente
                    - Salida de {transfer_from_ticker.upper()}: ID {out_id}
                    - Entrada a {transfer_to_ticker.upper()}: ID {in_id}
                    - Coste fiscal transferido: {transfer_cost_basis:,.2f}€
                    """)
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# =============================================================================
# ÚLTIMAS OPERACIONES
# =============================================================================
st.divider()
st.markdown("### 📝 Últimas Operaciones Registradas")

try:
    db = Database()
    transactions = db.get_transactions(limit=10, order='DESC')
    db.close()
    
    if transactions:
        # Crear DataFrame
        data = []
        for t in transactions:
            type_emoji = {
                'buy': '🟢',
                'sell': '🔴',
                'transfer_in': '➡️',
                'transfer_out': '⬅️'
            }
            data.append({
                'ID': t.id,
                'Fecha': t.date.strftime('%Y-%m-%d'),
                'Tipo': f"{type_emoji.get(t.type, '❓')} {t.type}",
                'Ticker': t.ticker,
                'Nombre': t.name or '-',
                'Cantidad': f"{t.quantity:,.2f}",
                'Precio': f"{t.price:,.4f}",
                'Total': f"{t.total:,.2f}€" if t.total else '-'
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay operaciones registradas")
        
except Exception as e:
    st.error(f"Error cargando operaciones: {e}")
