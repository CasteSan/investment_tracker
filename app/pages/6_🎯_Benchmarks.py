"""
Página: Benchmarks y Evolución de Cartera
Comparación con índices de referencia y análisis de valor real

Incluye:
- Descarga de precios de activos de la cartera
- Comparación con benchmark (base 100)
- Dos modos: Solo posiciones abiertas vs Cartera completa
- Gráfico estilo Investing.com (valor real en €)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configurar path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.benchmarks import BenchmarkComparator, BENCHMARK_SYMBOLS, YFINANCE_AVAILABLE
from src.market_data import MarketDataManager

st.set_page_config(page_title="Benchmarks", page_icon="🎯", layout="wide")

st.title("🎯 Comparación con Benchmarks")

# Verificar yfinance
if not YFINANCE_AVAILABLE:
    st.error("⚠️ yfinance no está instalado. Ejecuta: `pip install yfinance`")
    st.stop()

# =============================================================================
# SIDEBAR - CONFIGURACIÓN
# =============================================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Benchmark
    st.markdown("**Selecciona benchmark:**")
    benchmark_options = list(BENCHMARK_SYMBOLS.keys())
    selected_benchmark = st.selectbox(
        "Benchmark",
        benchmark_options,
        format_func=lambda x: f"{x} ({BENCHMARK_SYMBOLS[x]})",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Período
    st.markdown("**Período de análisis:**")
    period_options = {
        "1 mes": 30,
        "3 meses": 90,
        "6 meses": 180,
        "1 año": 365,
        "2 años": 730,
        "3 años": 1095,
        "Máximo": 3650
    }
    
    selected_period = st.selectbox("Período", list(period_options.keys()), index=3)
    days = period_options[selected_period]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    st.caption(f"Desde: {start_date.strftime('%Y-%m-%d')}")
    st.caption(f"Hasta: {end_date.strftime('%Y-%m-%d')}")
    
    st.divider()
    
    # Modo de comparación
    st.markdown("**Modo de comparación:**")
    comparison_mode = st.radio(
        "Qué comparar",
        ["Posiciones actuales", "Cartera completa"],
        help="""
        **Posiciones actuales**: Solo activos que tienes HOY (ignora ventas pasadas)
        
        **Cartera completa**: Incluye el P&L de posiciones cerradas
        """,
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Tasa libre de riesgo
    risk_free_rate = st.slider(
        "Tasa libre de riesgo (%)",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="Para cálculo del Sharpe Ratio"
    ) / 100

# =============================================================================
# INICIALIZAR GESTORES
# =============================================================================
# Obtener db_path de la cartera seleccionada
db_path = st.session_state.get('db_path')

try:
    bc = BenchmarkComparator(db_path=db_path)
    mdm = MarketDataManager(db_path=db_path)
    
    # Limpiar caché para asegurar datos actualizados
    mdm.clear_price_cache()
    
    # =========================================================================
    # SECCIÓN 1: GESTIÓN DE DATOS
    # =========================================================================
    st.markdown("### 📥 Gestión de Datos de Mercado")
    
    tab_benchmark, tab_portfolio = st.tabs(["📊 Datos del Benchmark", "💼 Precios de mi Cartera"])
    
    # --- TAB 1: Benchmark ---
    with tab_benchmark:
        available_benchmarks = bc.get_available_benchmarks()
        available_names = [b['name'] for b in available_benchmarks]
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if selected_benchmark in available_names:
                bench_info = next(b for b in available_benchmarks if b['name'] == selected_benchmark)
                st.success(f"✅ {selected_benchmark}: {bench_info['records']} registros ({bench_info['start_date']} → {bench_info['end_date']})")
            else:
                st.warning(f"⚠️ No hay datos de {selected_benchmark}")
        
        with col2:
            if st.button("📥 Descargar Benchmark", use_container_width=True):
                with st.spinner(f"Descargando {selected_benchmark}..."):
                    count = bc.download_benchmark(
                        selected_benchmark,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    )
                    if count > 0:
                        st.success(f"✅ {count} registros")
                        st.rerun()
                    else:
                        st.error("No se pudieron descargar")
    
    # --- TAB 2: Precios de cartera ---
    with tab_portfolio:
        st.markdown("""
        **¿Por qué descargar precios?**
        
        Para calcular el **valor de mercado REAL** de tu cartera (no solo el coste),
        necesitamos los precios históricos de tus activos.
        """)
        
        # Mostrar estado de precios
        download_status = mdm.get_download_status()
        
        if not download_status.empty:
            st.dataframe(
                download_status,
                column_config={
                    'ticker': 'Ticker',
                    'name': 'Nombre',
                    'has_prices': st.column_config.CheckboxColumn('Tiene precios'),
                    'records': 'Registros',
                    'start_date': 'Desde',
                    'end_date': 'Hasta'
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Botones de acción
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Descargar TODOS los precios", use_container_width=True):
                    with st.spinner("Descargando precios de todos los activos..."):
                        results = mdm.download_portfolio_prices(
                            start_date.strftime('%Y-%m-%d'),
                            end_date.strftime('%Y-%m-%d')
                        )
                        
                        success = sum(1 for v in results.values() if v > 0)
                        st.success(f"✅ Descargados precios de {success}/{len(results)} activos")
                        st.rerun()
            
            with col2:
                # Descargar solo los que faltan
                missing = download_status[~download_status['has_prices']]['ticker'].tolist()
                if missing:
                    if st.button(f"📥 Descargar faltantes ({len(missing)})", use_container_width=True):
                        with st.spinner("Descargando..."):
                            results = mdm.download_portfolio_prices(
                                start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d'),
                                tickers=missing
                            )
                            st.rerun()
        else:
            st.info("No hay activos en la cartera")
    
    st.divider()
    
    # =========================================================================
    # SECCIÓN 2: GRÁFICO ESTILO INVESTING.COM (Valor Real)
    # =========================================================================
    st.markdown("### 📈 Evolución de la Cartera (Valor Real en €)")
    
    st.caption("""
    Este gráfico muestra el **valor real en euros** de tu cartera, 
    similar a como lo hace Investing.com.
    """)
    
    # Obtener datos estilo Investing
    investing_data = mdm.get_investing_style_data(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    if not investing_data.empty:
        # Crear gráfico con múltiples líneas
        fig = go.Figure()
        
        # Línea 1: Valor total de la cartera
        fig.add_trace(go.Scatter(
            x=investing_data['date'],
            y=investing_data['total_portfolio_value'],
            mode='lines',
            name='Valor Total (con P&L cerrado)',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='%{x}<br>Total: %{y:,.2f}€<extra></extra>'
        ))
        
        # Línea 2: Valor de posiciones abiertas
        fig.add_trace(go.Scatter(
            x=investing_data['date'],
            y=investing_data['open_positions_value'],
            mode='lines',
            name='Posiciones Abiertas',
            line=dict(color='#28A745', width=2),
            hovertemplate='%{x}<br>Abiertas: %{y:,.2f}€<extra></extra>'
        ))
        
        # Línea 3: Capital invertido (coste)
        fig.add_trace(go.Scatter(
            x=investing_data['date'],
            y=investing_data['invested_capital'],
            mode='lines',
            name='Capital Invertido',
            line=dict(color='#6C757D', width=1, dash='dash'),
            hovertemplate='%{x}<br>Invertido: %{y:,.2f}€<extra></extra>'
        ))
        
        # Línea 4: P&L cerrado (como área si hay valores)
        if investing_data['closed_positions_pnl'].abs().sum() > 0:
            fig.add_trace(go.Scatter(
                x=investing_data['date'],
                y=investing_data['closed_positions_pnl'],
                mode='lines',
                name='P&L Posiciones Cerradas',
                line=dict(color='#FFC107', width=1),
                fill='tozeroy',
                fillcolor='rgba(255, 193, 7, 0.2)',
                hovertemplate='%{x}<br>P&L Cerrado: %{y:+,.2f}€<extra></extra>'
            ))
        
        fig.update_layout(
            title="Evolución del Valor de la Cartera",
            xaxis_title="Fecha",
            yaxis_title="Valor (€)",
            hovermode='x unified',
            height=450,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Métricas resumen
        if len(investing_data) > 0:
            last_row = investing_data.iloc[-1]
            first_row = investing_data.iloc[0]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Valor Actual",
                    f"{last_row['total_portfolio_value']:,.2f}€"
                )
            
            with col2:
                st.metric(
                    "Capital Invertido",
                    f"{last_row['invested_capital']:,.2f}€"
                )
            
            with col3:
                pnl_total = last_row['unrealized_pnl'] + last_row['closed_positions_pnl']
                pct = (pnl_total/last_row['invested_capital']*100) if last_row['invested_capital'] > 0 else 0
                st.metric(
                    "P&L Total",
                    f"{pnl_total:+,.2f}€",
                    delta=f"{pct:+.2f}%"
                )
            
            with col4:
                st.metric(
                    "P&L Cerrado",
                    f"{last_row['closed_positions_pnl']:+,.2f}€"
                )
    else:
        st.info("""
        📊 No hay datos suficientes para mostrar el gráfico.
        
        **Posibles causas:**
        - No hay transacciones en la cartera
        - No se han descargado los precios de los activos
        
        👆 Ve a la pestaña "Precios de mi Cartera" y descarga los precios.
        """)
    
    st.divider()
    
    # =========================================================================
    # SECCIÓN 3: COMPARACIÓN CON BENCHMARK (Base 100)
    # =========================================================================
    st.markdown("### 🎯 Comparación con Benchmark (Base 100)")
    
    st.caption("""
    **Nota importante:** Este gráfico compara el **rendimiento porcentual** de tu cartera 
    vs el benchmark, no el valor absoluto. Así las aportaciones/retiradas no afectan la comparación.
    """)
    
    # Verificar que hay datos del benchmark
    if selected_benchmark not in available_names:
        st.warning(f"👆 Descarga primero los datos del {selected_benchmark}")
    else:
        # Obtener serie de cartera según modo
        if comparison_mode == "Posiciones actuales":
            portfolio_df = mdm.get_open_positions_only_series(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            mode_description = "Solo las posiciones que tienes ACTUALMENTE"
        else:
            portfolio_df = mdm.get_portfolio_market_value_series(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                include_closed=True
            )
            mode_description = "Toda la cartera incluyendo posiciones cerradas"
        
        if not portfolio_df.empty and len(portfolio_df) > 1:
            st.caption(f"📊 Modo: {mode_description}")

            # Filtrar solo días con precios reales de mercado (evitar línea plana)
            if 'has_market_prices' in portfolio_df.columns:
                portfolio_with_prices = portfolio_df[portfolio_df['has_market_prices'] == True].copy()
                if portfolio_with_prices.empty:
                    st.warning("""
                    ⚠️ **No hay precios de mercado descargados** para los activos de esta cartera.

                    Los datos mostrados usan el precio de compra como aproximación.
                    Para ver valores de mercado reales, ve a la pestaña "Precios de mi Cartera"
                    y descarga los precios de tus activos.
                    """)
                    portfolio_df = portfolio_df.copy()
                else:
                    # Informar si hay días sin datos
                    days_without_prices = len(portfolio_df) - len(portfolio_with_prices)
                    if days_without_prices > 0:
                        st.info(f"ℹ️ Se omiten {days_without_prices} días sin precios de mercado disponibles.")
                    portfolio_df = portfolio_with_prices
            else:
                portfolio_df = portfolio_df.copy()

            # Obtener serie del benchmark
            benchmark_series = bc.get_benchmark_series(
                selected_benchmark,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if not benchmark_series.empty:
                # =================================================================
                # CALCULAR RENDIMIENTO SOBRE COSTE (no valor absoluto)
                # Esto evita que las aportaciones afecten la comparación
                # =================================================================

                # Calcular rendimiento diario de la cartera como % sobre coste
                # return_pct = (market_value / cost_basis - 1) * 100
                portfolio_df['return_pct'] = 0.0

                for i, row in portfolio_df.iterrows():
                    cost = row.get('cost_basis', row.get('invested_capital', 1))
                    value = row.get('market_value', row.get('total_value', cost))
                    if cost > 0:
                        portfolio_df.loc[i, 'return_pct'] = (value / cost - 1) * 100
                
                # Crear serie de rendimiento de cartera (base 100)
                portfolio_return_series = pd.Series(
                    100 + portfolio_df['return_pct'].values,  # Base 100 + rendimiento%
                    index=pd.DatetimeIndex(portfolio_df['date']),
                    name='Portfolio'
                )
                
                # Normalizar benchmark a base 100 desde la primera fecha de la cartera
                first_portfolio_date = portfolio_return_series.index.min()
                
                # Filtrar benchmark desde la primera fecha de la cartera
                benchmark_filtered = benchmark_series[benchmark_series.index >= first_portfolio_date]
                
                if len(benchmark_filtered) > 0:
                    # Normalizar benchmark a base 100
                    benchmark_base = benchmark_filtered.iloc[0]
                    benchmark_norm = (benchmark_filtered / benchmark_base) * 100
                    
                    # Alinear fechas usando merge para evitar problemas de índices
                    portfolio_temp = portfolio_return_series.reset_index()
                    portfolio_temp.columns = ['date', 'portfolio']
                    
                    benchmark_temp = benchmark_norm.reset_index()
                    benchmark_temp.columns = ['date', 'benchmark']
                    
                    # Merge por fecha
                    merged = pd.merge(portfolio_temp, benchmark_temp, on='date', how='inner')
                    
                    if len(merged) < 2:
                        # Si no hay suficientes fechas comunes, hacer outer merge y ffill
                        merged = pd.merge(portfolio_temp, benchmark_temp, on='date', how='outer')
                        merged = merged.sort_values('date')
                        merged['portfolio'] = merged['portfolio'].fillna(method='ffill').fillna(method='bfill')
                        merged['benchmark'] = merged['benchmark'].fillna(method='ffill').fillna(method='bfill')
                        merged = merged.dropna()
                    
                    if len(merged) >= 2:
                        # Crear gráfico
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=merged['date'],
                            y=merged['portfolio'],
                            mode='lines',
                            name='Mi Cartera (Rendimiento)',
                            line=dict(color='#2E86AB', width=2),
                            hovertemplate='%{x}<br>Cartera: %{y:.2f}<extra></extra>'
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=merged['date'],
                            y=merged['benchmark'],
                            mode='lines',
                            name=selected_benchmark,
                            line=dict(color='#DC3545', width=2, dash='dash'),
                            hovertemplate='%{x}<br>' + selected_benchmark + ': %{y:.2f}<extra></extra>'
                        ))
                        
                        # Línea base 100
                        fig.add_hline(y=100, line_dash="dot", line_color="gray", 
                                      annotation_text="Base 100")
                        
                        fig.update_layout(
                            title=f"Mi Cartera vs {selected_benchmark} (Base 100)",
                            xaxis_title="Fecha",
                            yaxis_title="Valor (Base 100)",
                            hovermode='x unified',
                            height=400,
                            template='plotly_white'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Calcular rendimientos finales
                        portfolio_return = merged['portfolio'].iloc[-1] - 100
                        benchmark_return = merged['benchmark'].iloc[-1] - 100
                        outperformance = portfolio_return - benchmark_return
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Mi Cartera", f"{portfolio_return:+.2f}%")
                        
                        with col2:
                            st.metric(selected_benchmark, f"{benchmark_return:+.2f}%")
                        
                        with col3:
                            st.metric(
                                "Outperformance",
                                f"{outperformance:+.2f}%",
                                delta=f"{'Mejor' if outperformance >= 0 else 'Peor'} que {selected_benchmark}"
                            )
                        
                        with col4:
                            days_elapsed = (merged['date'].iloc[-1] - merged['date'].iloc[0]).days
                            st.metric("Período", f"{days_elapsed} días")
                    else:
                        st.warning("No hay suficientes datos comunes entre cartera y benchmark")
                else:
                    st.warning("No hay datos del benchmark para el período de la cartera")
            else:
                st.warning("No hay datos del benchmark para el período seleccionado")
        else:
            st.info("""
            No hay datos de cartera para el período seleccionado.
            
            **Posibles causas:**
            - El período seleccionado es anterior a tu primera compra
            - No se han descargado los precios de los activos
            """)
    
    st.divider()
    
    # =========================================================================
    # SECCIÓN 4: MÉTRICAS DE RIESGO (simplificadas)
    # =========================================================================
    st.markdown("### 📊 Métricas de Riesgo")
    
    try:
        risk_metrics = bc.calculate_risk_metrics(
            selected_benchmark,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            risk_free_rate
        )
        
        if 'error' not in risk_metrics:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                vol = risk_metrics.get('portfolio_volatility', 0)
                st.metric(
                    "Volatilidad Cartera",
                    f"{vol:.2f}%",
                    help="Desviación estándar anualizada de los rendimientos"
                )
            
            with col2:
                vol_bench = risk_metrics.get('benchmark_volatility', 0)
                st.metric(
                    f"Volatilidad {selected_benchmark}",
                    f"{vol_bench:.2f}%"
                )
            
            with col3:
                sharpe = risk_metrics.get('sharpe_ratio', 0)
                st.metric(
                    "Sharpe Ratio",
                    f"{sharpe:.2f}",
                    help="Rendimiento ajustado por riesgo. >1 es bueno, >2 es excelente"
                )
            
            with col4:
                max_dd = risk_metrics.get('max_drawdown', 0)
                st.metric(
                    "Max Drawdown",
                    f"{max_dd:.2f}%",
                    help="Máxima caída desde máximo anterior"
                )
        else:
            st.info("No hay datos suficientes para calcular métricas de riesgo")
    except Exception as e:
        st.info(f"No se pudieron calcular métricas de riesgo")
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    bc.close()
    mdm.close()

except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.code(traceback.format_exc())
