"""
Componentes de Gráficos - Plotly
Funciones reutilizables para crear gráficos en Streamlit
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Optional


# Colores del tema
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ffbb33',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40'
}

# Paleta para múltiples series
COLOR_PALETTE = px.colors.qualitative.Set2


def plot_portfolio_evolution(df: pd.DataFrame, 
                            date_col: str = 'date',
                            value_col: str = 'value',
                            title: str = "Evolución de la Cartera") -> go.Figure:
    """
    Gráfico de línea de la evolución temporal de la cartera.
    
    Args:
        df: DataFrame con fechas y valores
        date_col: Nombre de la columna de fecha
        value_col: Nombre de la columna de valor
        title: Título del gráfico
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[value_col],
        mode='lines',
        name='Valor Cartera',
        line=dict(color=COLORS['primary'], width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Valor (€)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    # Formato de hover
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Valor: %{y:,.2f}€<extra></extra>"
    )
    
    return fig


def plot_allocation_donut(df: pd.DataFrame,
                         labels_col: str = 'display_name',
                         values_col: str = 'market_value',
                         names_col: str = 'name',
                         title: str = "Distribución de Cartera") -> go.Figure:
    """
    Gráfico de donut con la distribución de la cartera.

    Args:
        df: DataFrame con activos y valores
        labels_col: Columna para etiquetas (truncadas para visualización)
        values_col: Columna para valores
        names_col: Columna para nombres completos (en tooltip)
        title: Título del gráfico

    Returns:
        Figura de Plotly
    """
    labels = df[labels_col].tolist() if labels_col in df.columns else df['ticker'].tolist()
    values = df[values_col].tolist()

    # Usar nombres completos para hover si están disponibles
    if names_col and names_col in df.columns:
        hover_names = df[names_col].tolist()
    else:
        hover_names = labels

    # Crear customdata para el hover con nombres completos
    customdata = hover_names

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        textinfo='label+percent',
        textposition='outside',
        customdata=customdata,
        hovertemplate="<b>%{customdata}</b><br>Valor: %{value:,.2f}€<br>Peso: %{percent}<extra></extra>",
        marker=dict(colors=COLOR_PALETTE)
    )])

    fig.update_layout(
        title=title,
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )

    return fig


def plot_performance_bar(df: pd.DataFrame,
                        ticker_col: str = 'ticker',
                        performance_col: str = 'unrealized_gain_pct',
                        name_col: str = 'name',
                        display_name_col: str = 'display_name',
                        title: str = "Rentabilidad por Activo",
                        top_n: int = 10) -> go.Figure:
    """
    Gráfico de barras horizontales de rentabilidad.

    Args:
        df: DataFrame con activos y rentabilidad
        ticker_col: Columna de tickers (fallback)
        performance_col: Columna de rentabilidad
        name_col: Columna de nombres completos (para tooltip)
        display_name_col: Columna de nombres truncados (para labels)
        title: Título del gráfico
        top_n: Número de activos a mostrar

    Returns:
        Figura de Plotly
    """
    # Ordenar y tomar top_n
    df_sorted = df.nlargest(top_n, performance_col)

    # Colores según ganancia/pérdida
    colors = [COLORS['success'] if x >= 0 else COLORS['danger']
              for x in df_sorted[performance_col]]

    # Labels para el eje Y (preferir display_name)
    if display_name_col and display_name_col in df_sorted.columns:
        labels = df_sorted[display_name_col].tolist()
    elif name_col and name_col in df_sorted.columns:
        labels = df_sorted[name_col].tolist()
    else:
        labels = df_sorted[ticker_col].tolist()

    # Nombres completos para hover
    if name_col and name_col in df_sorted.columns:
        hover_names = df_sorted[name_col].tolist()
    else:
        hover_names = labels

    fig = go.Figure(go.Bar(
        x=df_sorted[performance_col],
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"{x:+.2f}%" for x in df_sorted[performance_col]],
        textposition='outside',
        customdata=hover_names,
        hovertemplate="<b>%{customdata}</b><br>Rentabilidad: %{x:+.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Rentabilidad (%)",
        yaxis_title="",
        template='plotly_white',
        height=max(300, top_n * 35),
        yaxis=dict(autorange="reversed")
    )

    # Línea vertical en 0
    fig.add_vline(x=0, line_dash="dash", line_color="gray")

    return fig


def plot_benchmark_comparison(df: pd.DataFrame,
                             date_col: str = 'date',
                             portfolio_col: str = 'portfolio_normalized',
                             benchmark_col: str = 'benchmark_normalized',
                             benchmark_name: str = 'Benchmark',
                             title: str = "Cartera vs Benchmark (Base 100)") -> go.Figure:
    """
    Gráfico de líneas comparando cartera vs benchmark.
    
    Args:
        df: DataFrame con series normalizadas
        date_col: Columna de fechas
        portfolio_col: Columna de valores de cartera
        benchmark_col: Columna de valores del benchmark
        benchmark_name: Nombre del benchmark para la leyenda
        title: Título del gráfico
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    
    # Línea de cartera
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[portfolio_col],
        mode='lines',
        name='Mi Cartera',
        line=dict(color=COLORS['primary'], width=3)
    ))
    
    # Línea de benchmark
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[benchmark_col],
        mode='lines',
        name=benchmark_name,
        line=dict(color=COLORS['secondary'], width=2, dash='dash')
    ))
    
    # Línea base 100
    fig.add_hline(y=100, line_dash="dot", line_color="gray",
                  annotation_text="Base 100")
    
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Valor (Base 100)",
        hovermode='x unified',
        template='plotly_white',
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_dividend_calendar(df: pd.DataFrame,
                          month_col: str = 'month_name',
                          value_col: str = 'net',
                          title: str = "Dividendos por Mes") -> go.Figure:
    """
    Gráfico de barras de dividendos por mes.
    
    Args:
        df: DataFrame con meses y dividendos
        month_col: Columna de nombres de mes
        value_col: Columna de valores
        title: Título del gráfico
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure(go.Bar(
        x=df[month_col],
        y=df[value_col],
        marker_color=COLORS['success'],
        text=[f"{x:.0f}€" if x > 0 else "" for x in df[value_col]],
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Dividendos: %{y:,.2f}€<extra></extra>"
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis_title="Dividendos Netos (€)",
        template='plotly_white',
        height=350
    )
    
    return fig


def plot_gains_waterfall(gains: float, losses: float, dividends: float = 0,
                        title: str = "Desglose de Rendimientos") -> go.Figure:
    """
    Gráfico de cascada (waterfall) mostrando ganancias, pérdidas y dividendos.
    
    Args:
        gains: Ganancias realizadas
        losses: Pérdidas realizadas (valor positivo)
        dividends: Dividendos recibidos
        title: Título del gráfico
    
    Returns:
        Figura de Plotly
    """
    categories = ["Ganancias", "Pérdidas", "Dividendos", "Neto"]
    values = [gains, -losses, dividends, None]  # None para que calcule el total
    
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=categories,
        y=[gains, -losses, dividends, 0],
        textposition="outside",
        text=[f"+{gains:,.0f}€", f"-{losses:,.0f}€", f"+{dividends:,.0f}€", ""],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": COLORS['success']}},
        decreasing={"marker": {"color": COLORS['danger']}},
        totals={"marker": {"color": COLORS['primary']}}
    ))
    
    fig.update_layout(
        title=title,
        template='plotly_white',
        height=350,
        showlegend=False
    )
    
    return fig


def plot_risk_gauge(value: float, 
                   title: str = "Sharpe Ratio",
                   min_val: float = -1,
                   max_val: float = 3) -> go.Figure:
    """
    Gráfico de gauge (velocímetro) para métricas de riesgo.
    
    Args:
        value: Valor de la métrica
        title: Título
        min_val: Valor mínimo de la escala
        max_val: Valor máximo de la escala
    
    Returns:
        Figura de Plotly
    """
    # Determinar color según valor
    if value >= 2:
        color = COLORS['success']
    elif value >= 1:
        color = COLORS['info']
    elif value >= 0:
        color = COLORS['warning']
    else:
        color = COLORS['danger']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_val, 0], 'color': "rgba(214, 39, 40, 0.3)"},
                {'range': [0, 1], 'color': "rgba(255, 187, 51, 0.3)"},
                {'range': [1, 2], 'color': "rgba(23, 162, 184, 0.3)"},
                {'range': [2, max_val], 'color': "rgba(44, 160, 44, 0.3)"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


def plot_top_bottom_performers(df: pd.DataFrame,
                               ticker_col: str = 'ticker',
                               perf_col: str = 'unrealized_gain_pct',
                               name_col: str = 'name',
                               display_name_col: str = 'display_name',
                               n: int = 5) -> go.Figure:
    """
    Gráfico de los mejores y peores performers.

    Args:
        df: DataFrame con activos y rentabilidad
        ticker_col: Columna de tickers (fallback si no hay nombres)
        perf_col: Columna de rentabilidad
        name_col: Columna de nombres completos (para tooltip)
        display_name_col: Columna de nombres truncados (para labels)
        n: Número de mejores/peores a mostrar

    Returns:
        Figura de Plotly con subplots
    """
    from plotly.subplots import make_subplots

    # Top n mejores
    top = df.nlargest(n, perf_col)
    # Top n peores
    bottom = df.nsmallest(n, perf_col)

    # Determinar columna para labels (preferir display_name si existe)
    if display_name_col in df.columns:
        top_labels = top[display_name_col].tolist()
        bottom_labels = bottom[display_name_col].tolist()
    elif name_col in df.columns:
        top_labels = top[name_col].tolist()
        bottom_labels = bottom[name_col].tolist()
    else:
        top_labels = top[ticker_col].tolist()
        bottom_labels = bottom[ticker_col].tolist()

    # Nombres completos para hover
    if name_col in df.columns:
        top_hover = top[name_col].tolist()
        bottom_hover = bottom[name_col].tolist()
    else:
        top_hover = top_labels
        bottom_hover = bottom_labels

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=(f"Top {n} Mejores", f"Top {n} Peores"),
                        horizontal_spacing=0.15)

    # Mejores
    fig.add_trace(go.Bar(
        y=top_labels,
        x=top[perf_col],
        orientation='h',
        marker_color=COLORS['success'],
        text=[f"+{x:.1f}%" for x in top[perf_col]],
        textposition='outside',
        customdata=top_hover,
        hovertemplate="<b>%{customdata}</b><br>Rentabilidad: %{x:+.2f}%<extra></extra>",
        showlegend=False
    ), row=1, col=1)

    # Peores
    fig.add_trace(go.Bar(
        y=bottom_labels,
        x=bottom[perf_col],
        orientation='h',
        marker_color=COLORS['danger'],
        text=[f"{x:.1f}%" for x in bottom[perf_col]],
        textposition='outside',
        customdata=bottom_hover,
        hovertemplate="<b>%{customdata}</b><br>Rentabilidad: %{x:+.2f}%<extra></extra>",
        showlegend=False
    ), row=1, col=2)

    fig.update_layout(
        height=300,
        template='plotly_white'
    )

    # Invertir orden del eje Y
    fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=2)

    return fig
