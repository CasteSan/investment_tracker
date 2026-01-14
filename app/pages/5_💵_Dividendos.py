"""
Página: Dividendos
Tracking de dividendos, calendario, yields y análisis
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
if not require_auth("Dividendos", "💵"):
    st.stop()

from src.dividends import DividendManager
from src.database import Database

# Importar componentes
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.charts import plot_dividend_calendar, plot_allocation_donut
from components.tables import create_dividends_table

st.title("💵 Dividendos")

# Sidebar - Filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Año
    current_year = datetime.now().year
    div_year = st.selectbox(
        "Año",
        list(range(current_year, current_year - 5, -1)),
        index=0
    )
    
    # Ticker específico
    db_path = st.session_state.get('db_path')
    db = Database(db_path=db_path)
    tickers = db.get_all_tickers()
    db.close()
    
    ticker_filter = st.selectbox(
        "Activo",
        ["Todos"] + tickers
    )

try:
    dm = DividendManager(db_path=db_path)
    
    # =========================================================================
    # RESUMEN DE DIVIDENDOS
    # =========================================================================
    st.markdown(f"### 📊 Resumen {div_year}")
    
    totals = dm.get_total_dividends(year=div_year)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Cobros", totals['count'])
    
    with col2:
        st.metric("Bruto Total", f"{totals['total_gross']:,.2f}€")
    
    with col3:
        st.metric("Neto Total", f"{totals['total_net']:,.2f}€")
    
    with col4:
        st.metric("Retenciones", f"{totals['total_withholding']:,.2f}€")
    
    with col5:
        avg_rate = totals.get('avg_withholding_rate', 0)
        st.metric("Tasa Media", f"{avg_rate:.1f}%")
    
    st.divider()
    
    # =========================================================================
    # CALENDARIO DE DIVIDENDOS
    # =========================================================================
    st.markdown(f"### 📅 Calendario {div_year}")
    
    calendar = dm.get_dividend_calendar(div_year)
    
    if calendar:
        # Convertir a DataFrame
        months_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        cal_data = []
        for month_num in range(1, 13):
            month_data = calendar.get(month_num, {'gross': 0, 'net': 0, 'count': 0})
            cal_data.append({
                'month': month_num,
                'month_name': months_es[month_num - 1],
                'gross': month_data['gross'],
                'net': month_data['net'],
                'count': month_data['count']
            })
        
        cal_df = pd.DataFrame(cal_data)
        
        # Gráfico de barras
        fig = plot_dividend_calendar(cal_df, 'month_name', 'net', f"Dividendos Netos por Mes ({div_year})")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla mensual
        with st.expander("Ver detalle mensual"):
            display_cal = cal_df[['month_name', 'count', 'gross', 'net']].copy()
            display_cal.columns = ['Mes', 'Cobros', 'Bruto', 'Neto']
            display_cal['Bruto'] = display_cal['Bruto'].apply(lambda x: f"{x:,.2f}€")
            display_cal['Neto'] = display_cal['Neto'].apply(lambda x: f"{x:,.2f}€")
            st.dataframe(display_cal, use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay dividendos registrados en {div_year}")
    
    st.divider()
    
    # =========================================================================
    # DIVIDENDOS POR ACTIVO
    # =========================================================================
    st.markdown(f"### 🏆 Dividendos por Activo")
    
    by_asset = dm.get_dividends_by_asset(year=div_year)
    
    if not by_asset.empty:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Tabla
            display_asset = by_asset.copy()
            display_asset['total_gross'] = display_asset['total_gross'].apply(lambda x: f"{x:,.2f}€")
            display_asset['total_net'] = display_asset['total_net'].apply(lambda x: f"{x:,.2f}€")
            display_asset['pct_of_total'] = display_asset['pct_of_total'].apply(lambda x: f"{x:.1f}%")
            
            display_asset.columns = ['Ticker', 'Cobros', 'Bruto', 'Neto', '% del Total']
            st.dataframe(display_asset, use_container_width=True, hide_index=True)
        
        with col2:
            # Donut chart
            fig = plot_allocation_donut(
                by_asset,
                labels_col='ticker',
                values_col='total_net',
                title="Distribución de Dividendos"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de dividendos por activo")
    
    st.divider()
    
    # =========================================================================
    # YIELD ON COST
    # =========================================================================
    st.markdown("### 📈 Yield on Cost (YOC)")
    
    portfolio_yield = dm.get_portfolio_yield()
    
    if portfolio_yield and portfolio_yield.get('portfolio_yoc_net', 0) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "YOC Cartera (Neto)",
                f"{portfolio_yield['portfolio_yoc_net']:.2f}%",
                help="Dividendos netos anuales / Coste de adquisición"
            )
        
        with col2:
            st.metric(
                "YOC Cartera (Bruto)",
                f"{portfolio_yield['portfolio_yoc_gross']:.2f}%"
            )
        
        with col3:
            st.metric(
                "Activos con dividendos",
                f"{portfolio_yield['assets_with_dividends']} de {portfolio_yield['total_positions']}"
            )
        
        # YOC por activo
        st.markdown("#### YOC por Activo")
        
        yoc_data = []
        for ticker in dm.db.get_all_tickers():
            try:
                yoc = dm.get_dividend_yield(ticker)
                if yoc and yoc.get('yoc_net', 0) > 0:
                    yoc_data.append({
                        'Ticker': ticker,
                        'YOC Bruto': f"{yoc['yoc_gross']:.2f}%",
                        'YOC Neto': f"{yoc['yoc_net']:.2f}%",
                        'Dividendo Anual': f"{yoc.get('annual_dividend', 0):.2f}€",
                        'Coste Base': f"{yoc.get('cost_basis', 0):,.2f}€"
                    })
            except:
                pass
        
        if yoc_data:
            yoc_df = pd.DataFrame(yoc_data)
            st.dataframe(yoc_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de YOC disponibles")
    else:
        st.info("No hay suficientes datos para calcular el yield")
    
    st.divider()
    
    # =========================================================================
    # HISTORIAL DE DIVIDENDOS
    # =========================================================================
    st.markdown("### 📋 Historial de Dividendos")
    
    # Obtener dividendos según filtros
    if ticker_filter == "Todos":
        dividends = dm.get_dividends(year=div_year)
    else:
        dividends = dm.get_dividends(ticker=ticker_filter, year=div_year)
    
    if dividends:
        # Convertir a DataFrame
        div_data = []
        for d in dividends:
            div_data.append({
                'id': d.id,
                'date': d.date.strftime('%Y-%m-%d'),
                'ticker': d.ticker,
                'name': d.name or d.ticker,
                'gross_amount': d.gross_amount,
                'net_amount': d.net_amount,
                'withholding_tax': d.withholding_tax,
                'currency': d.currency
            })
        
        div_df = pd.DataFrame(div_data)
        
        # Formatear para mostrar
        display_div = div_df.copy()
        display_div['gross_amount'] = display_div['gross_amount'].apply(lambda x: f"{x:.2f}€")
        display_div['net_amount'] = display_div['net_amount'].apply(lambda x: f"{x:.2f}€")
        display_div['withholding_tax'] = display_div['withholding_tax'].apply(lambda x: f"{x:.2f}€")
        
        display_div.columns = ['ID', 'Fecha', 'Ticker', 'Nombre', 'Bruto', 'Neto', 'Retención', 'Divisa']
        
        st.dataframe(display_div.drop('ID', axis=1), use_container_width=True, hide_index=True)
        
        # Exportar
        csv = div_df.to_csv(index=False)
        st.download_button(
            label="📥 Exportar a CSV",
            data=csv,
            file_name=f"dividendos_{div_year}.csv",
            mime="text/csv"
        )
    else:
        st.info(f"No hay dividendos registrados" + (f" para {ticker_filter}" if ticker_filter != "Todos" else ""))
    
    st.divider()
    
    # =========================================================================
    # PROYECCIÓN ANUAL
    # =========================================================================
    st.markdown("### 🔮 Proyección de Dividendos")
    
    projection = dm.estimate_annual_dividends()
    
    if projection:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Estimación Anual (Neto)",
                f"{projection.get('estimated_annual_net', 0):,.2f}€",
                help="Basado en los dividendos de los últimos 12 meses"
            )
        
        with col2:
            confidence = projection.get('confidence', 'low')
            confidence_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}
            confidence_text = {'high': 'Alta', 'medium': 'Media', 'low': 'Baja'}
            
            st.metric(
                "Confianza",
                f"{confidence_emoji.get(confidence, '❓')} {confidence_text.get(confidence, 'Desconocida')}"
            )
        
        if projection.get('by_ticker'):
            with st.expander("Ver proyección por activo"):
                proj_data = []
                for ticker, data in projection['by_ticker'].items():
                    proj_data.append({
                        'Ticker': ticker,
                        'Estimado Anual': f"{data.get('estimated_annual', 0):.2f}€",
                        'Pagos últimos 12m': data.get('payments_last_year', 0),
                        'Frecuencia': data.get('frequency', 'unknown')
                    })
                
                st.dataframe(pd.DataFrame(proj_data), use_container_width=True, hide_index=True)
    else:
        st.info("No hay suficientes datos para proyectar dividendos")
    
    st.divider()
    
    # =========================================================================
    # EXPORTAR
    # =========================================================================
    st.markdown("### 📄 Exportar Informe")
    
    if st.button("📥 Generar Informe Excel", use_container_width=True):
        try:
            filepath = dm.export_dividends(
                filepath=f"data/exports/dividendos_{div_year}.xlsx",
                year=div_year
            )
            st.success(f"✅ Informe generado: {filepath}")
            
            with open(filepath, 'rb') as f:
                st.download_button(
                    label="📥 Descargar Informe",
                    data=f,
                    file_name=f"dividendos_{div_year}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"Error generando informe: {e}")
    
    dm.close()

except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.exception(e)
