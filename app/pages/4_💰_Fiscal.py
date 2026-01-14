"""
Página: Fiscal
Información fiscal, plusvalías, simulador de ventas y exportación
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
if not require_auth("Fiscal", "💰"):
    st.stop()

from src.tax_calculator import TaxCalculator
from src.portfolio import Portfolio
from src.database import Database

# Importar componentes
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.charts import plot_gains_waterfall
from components.tables import create_fiscal_table

st.title("💰 Información Fiscal")

# Obtener db_path de la cartera seleccionada
db_path = st.session_state.get('db_path')

# Sidebar - Configuración
with st.sidebar:
    st.header("⚙️ Configuración Fiscal")
    
    # Año fiscal
    current_year = datetime.now().year
    fiscal_year = st.selectbox(
        "Año fiscal",
        list(range(current_year, current_year - 5, -1)),
        index=0
    )
    
    # Método de cálculo
    fiscal_method = st.selectbox(
        "Método de cálculo",
        ["FIFO", "LIFO"],
        help="FIFO: First In First Out (España)\nLIFO: Last In First Out"
    )
    
    st.divider()
    
    # Tramos IRPF
    st.markdown("**Tramos IRPF del Ahorro (España)**")
    st.markdown("""
    - 0€ - 6.000€: **19%**
    - 6.000€ - 50.000€: **21%**
    - 50.000€ - 200.000€: **23%**
    - 200.000€ - 300.000€: **27%**
    - >300.000€: **28%**
    """)

try:
    # Cargar datos
    tax = TaxCalculator(method=fiscal_method, db_path=db_path)
    
    # =========================================================================
    # RESUMEN FISCAL DEL AÑO
    # =========================================================================
    st.markdown(f"### 📊 Resumen Fiscal {fiscal_year}")
    
    summary = tax.get_fiscal_year_summary(fiscal_year)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gains = summary.get('total_gains', 0)
        st.metric(
            "✅ Ganancias",
            f"{gains:,.2f}€",
            help="Total de plusvalías realizadas"
        )
    
    with col2:
        losses = summary.get('total_losses', 0)
        st.metric(
            "❌ Pérdidas",
            f"{losses:,.2f}€",
            help="Total de minusvalías realizadas"
        )
    
    with col3:
        net = summary.get('net_gain', 0)
        st.metric(
            "📊 Balance Neto",
            f"{net:+,.2f}€",
            delta="Positivo" if net > 0 else "Negativo" if net < 0 else "Neutral",
            delta_color="normal" if net >= 0 else "inverse"
        )
    
    with col4:
        estimated_tax = summary.get('estimated_tax', 0)
        st.metric(
            "🏛️ Impuesto Estimado",
            f"{estimated_tax:,.2f}€",
            help="Estimación según tramos IRPF del ahorro"
        )
    
    st.divider()
    
    # =========================================================================
    # GRÁFICO WATERFALL
    # =========================================================================
    st.markdown("### 📊 Desglose de Rendimientos")
    
    # Obtener dividendos del año
    try:
        from src.dividends import DividendManager
        dm = DividendManager(db_path=db_path)
        div_totals = dm.get_total_dividends(year=fiscal_year)
        dividends = div_totals.get('total_net', 0)
        dm.close()
    except:
        dividends = 0
    
    fig = plot_gains_waterfall(
        gains=abs(gains),
        losses=abs(losses),
        dividends=dividends,
        title=f"Rendimientos del Capital {fiscal_year}"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # =========================================================================
    # DETALLE DE OPERACIONES
    # =========================================================================
    st.markdown(f"### 📋 Detalle de Operaciones {fiscal_year}")
    
    # Obtener detalle fiscal
    fiscal_detail = tax.get_fiscal_year_detail(fiscal_year)
    
    if not fiscal_detail.empty:
        # Formatear tabla
        display_df = fiscal_detail.copy()
        
        # Renombrar columnas si existen
        col_renames = {
            'sale_date': 'Fecha',
            'ticker': 'Ticker',
            'name': 'Nombre',
            'quantity': 'Cantidad',
            'cost_basis': 'Coste',
            'sale_proceeds': 'Venta',
            'gain': 'Ganancia',
            'holding_days': 'Días'
        }
        
        available_cols = [c for c in col_renames.keys() if c in display_df.columns]
        display_df = display_df[available_cols]
        display_df.columns = [col_renames[c] for c in available_cols]
        
        # Formatear valores
        if 'Cantidad' in display_df.columns:
            display_df['Cantidad'] = display_df['Cantidad'].apply(lambda x: f"{x:,.2f}")
        if 'Coste' in display_df.columns:
            display_df['Coste'] = display_df['Coste'].apply(lambda x: f"{x:,.2f}€")
        if 'Venta' in display_df.columns:
            display_df['Venta'] = display_df['Venta'].apply(lambda x: f"{x:,.2f}€")
        if 'Ganancia' in display_df.columns:
            display_df['Ganancia'] = display_df['Ganancia'].apply(lambda x: f"{x:+,.2f}€")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Estadísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Operaciones", len(fiscal_detail))
        with col2:
            st.metric("Operaciones ganadoras", len(fiscal_detail[fiscal_detail['gain'] > 0]))
        with col3:
            st.metric("Operaciones perdedoras", len(fiscal_detail[fiscal_detail['gain'] < 0]))
    else:
        st.info(f"No hay ventas registradas en {fiscal_year}")
    
    st.divider()
    
    # =========================================================================
    # ALERTAS FISCALES (Regla de los 2 meses)
    # =========================================================================
    st.markdown("### ⚠️ Alertas Fiscales")
    
    try:
        wash_sales_df = tax.get_wash_sales_in_year(fiscal_year)
        
        if not wash_sales_df.empty:
            st.warning(f"⚠️ Se detectaron {len(wash_sales_df)} posibles operaciones afectadas por la regla de los 2 meses")
            
            with st.expander("Ver detalles de wash sales"):
                st.markdown("""
                **Regla de los 2 meses (antiaplicación)**: 
                Las pérdidas de valores homogéneos no son deducibles si se recompran 
                en los 2 meses anteriores o posteriores a la venta.
                """)
                
                for _, ws in wash_sales_df.iterrows():
                    st.markdown(f"""
                    - **{ws.get('ticker', 'N/A')}** ({ws.get('name', '')}): 
                      Venta el {ws.get('date', 'N/A')} con pérdida de {ws.get('loss', 0):,.2f}€.
                    """)
        else:
            st.success("✅ No se detectaron operaciones afectadas por la regla de los 2 meses")
    except Exception as e:
        st.info("ℹ️ No se pudo verificar la regla de los 2 meses")
    
    st.divider()
    
    # =========================================================================
    # SIMULADOR DE VENTA
    # =========================================================================
    st.markdown("### 🎯 Simulador de Venta")
    st.info("💡 Simula el impacto fiscal de una venta antes de realizarla")
    
    # Obtener posiciones actuales para el selector
    portfolio = Portfolio(db_path=db_path)
    positions = portfolio.get_current_positions()
    portfolio.close()
    
    if not positions.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Selector de activo
            tickers_with_names = positions.apply(
                lambda x: f"{x['ticker']} - {x['name']}" if x['name'] else x['ticker'], 
                axis=1
            ).tolist()
            
            selected = st.selectbox("Selecciona activo", tickers_with_names)
            selected_ticker = selected.split(' - ')[0] if selected else None
            
            if selected_ticker:
                position = positions[positions['ticker'] == selected_ticker].iloc[0]
                st.info(f"Tienes {position['quantity']:.2f} unidades a precio medio {position['avg_price']:.4f}€")
        
        with col2:
            sim_quantity = st.number_input(
                "Cantidad a vender",
                min_value=0.01,
                max_value=float(position['quantity']) if selected_ticker else 100.0,
                value=min(1.0, float(position['quantity'])) if selected_ticker else 1.0,
                step=0.01
            )
            
            sim_price = st.number_input(
                "Precio de venta estimado (€)",
                min_value=0.01,
                value=float(position['avg_price']) if selected_ticker else 10.0,
                step=0.01
            )
        
        if st.button("🔮 Simular Venta", use_container_width=True):
            if selected_ticker:
                simulation = tax.simulate_sale(selected_ticker, sim_quantity, sim_price)
                
                if simulation:
                    st.markdown("#### Resultado de la simulación")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Coste de adquisición", f"{simulation.get('cost_basis', 0):,.2f}€")
                    
                    with col2:
                        st.metric("Ingresos de venta", f"{simulation.get('sale_proceeds', 0):,.2f}€")
                    
                    with col3:
                        gain = simulation.get('gain', 0)
                        st.metric(
                            "Ganancia/Pérdida",
                            f"{gain:+,.2f}€",
                            delta="Ganancia" if gain > 0 else "Pérdida",
                            delta_color="normal" if gain >= 0 else "inverse"
                        )
                    
                    # Impacto fiscal
                    if gain > 0:
                        tax_impact = gain * 0.19  # Primer tramo
                        st.warning(f"🏛️ Impuesto aproximado (19%): {tax_impact:,.2f}€")
                        st.caption("Nota: El impuesto real depende del total de ganancias del año y puede variar según los tramos.")
                    elif gain < 0:
                        st.success(f"✅ Esta pérdida de {abs(gain):,.2f}€ podría compensar otras ganancias")
                else:
                    st.error("No se pudo realizar la simulación. ¿Tienes suficientes unidades?")
    else:
        st.warning("No hay posiciones para simular")
    
    st.divider()
    
    # =========================================================================
    # LOTES DISPONIBLES
    # =========================================================================
    st.markdown("### 📦 Lotes Disponibles (FIFO)")
    
    if not positions.empty:
        selected_for_lots = st.selectbox(
            "Ver lotes de",
            positions['ticker'].tolist(),
            key="lots_selector"
        )
        
        if selected_for_lots:
            lots = tax.get_available_lots(selected_for_lots)
            
            if lots:
                lots_df = pd.DataFrame(lots)
                
                # Formatear
                if 'date' in lots_df.columns:
                    lots_df['date'] = pd.to_datetime(lots_df['date']).dt.strftime('%Y-%m-%d')
                if 'quantity' in lots_df.columns:
                    lots_df['quantity'] = lots_df['quantity'].apply(lambda x: f"{x:,.2f}")
                if 'price' in lots_df.columns:
                    lots_df['price'] = lots_df['price'].apply(lambda x: f"{x:,.4f}€")
                if 'total' in lots_df.columns:
                    lots_df['total'] = lots_df['total'].apply(lambda x: f"{x:,.2f}€")
                
                lots_df.columns = ['Fecha', 'Cantidad', 'Precio', 'Total'][:len(lots_df.columns)]
                
                st.dataframe(lots_df, use_container_width=True, hide_index=True)
                st.caption(f"Los lotes se venden en orden {fiscal_method} (primero el más {'antiguo' if fiscal_method == 'FIFO' else 'reciente'})")
            else:
                st.info("No hay lotes disponibles para este activo")
    
    st.divider()
    
    # =========================================================================
    # EXPORTAR INFORME FISCAL
    # =========================================================================
    st.markdown("### 📄 Exportar Informe Fiscal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Generar Informe Excel", use_container_width=True):
            try:
                filepath = tax.export_fiscal_report(
                    fiscal_year,
                    filepath=f"data/exports/informe_fiscal_{fiscal_year}.xlsx"
                )
                st.success(f"✅ Informe generado: {filepath}")
                
                # Ofrecer descarga
                with open(filepath, 'rb') as f:
                    st.download_button(
                        label="📥 Descargar Informe",
                        data=f,
                        file_name=f"informe_fiscal_{fiscal_year}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"Error generando informe: {e}")
    
    with col2:
        st.markdown("""
        El informe Excel incluye:
        - Resumen de ganancias y pérdidas
        - Detalle de cada operación
        - Alertas de wash sales
        - Lotes vendidos (FIFO/LIFO)
        - Información por trimestres
        - Desglose por tramos IRPF
        """)
    
    tax.close()

except Exception as e:
    st.error(f"Error cargando datos fiscales: {e}")
    st.exception(e)
