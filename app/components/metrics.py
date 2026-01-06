"""
Componentes de Métricas - Tarjetas y visualizaciones de KPIs
"""

import streamlit as st
from typing import Dict, List, Optional, Union


def metric_card(title: str, 
                value: Union[str, float], 
                delta: Union[str, float] = None,
                delta_color: str = "normal",
                help_text: str = None):
    """
    Muestra una tarjeta de métrica estilizada.
    
    Args:
        title: Título de la métrica
        value: Valor principal
        delta: Cambio/delta (opcional)
        delta_color: "normal", "inverse" u "off"
        help_text: Texto de ayuda
    """
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def metrics_row(metrics: List[Dict], columns: int = 4):
    """
    Muestra una fila de métricas.
    
    Args:
        metrics: Lista de dicts con keys: title, value, delta (opcional)
        columns: Número de columnas
    """
    cols = st.columns(columns)
    
    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            st.metric(
                label=metric.get('title', ''),
                value=metric.get('value', ''),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal'),
                help=metric.get('help')
            )


def portfolio_summary_metrics(total_value: float,
                             total_cost: float,
                             unrealized_gain: float,
                             realized_gain: float = 0,
                             dividends: float = 0):
    """
    Muestra métricas resumen del portfolio.
    """
    unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0
    
    metrics = [
        {
            'title': '💰 Valor Total',
            'value': f"{total_value:,.2f}€",
            'help': 'Valor de mercado actual'
        },
        {
            'title': '📊 Invertido',
            'value': f"{total_cost:,.2f}€",
            'help': 'Coste de adquisición'
        },
        {
            'title': '📈 Plusvalía Latente',
            'value': f"{unrealized_gain:+,.2f}€",
            'delta': f"{unrealized_pct:+.2f}%",
            'delta_color': 'normal' if unrealized_gain >= 0 else 'inverse'
        },
        {
            'title': '💵 Realizado',
            'value': f"{realized_gain:+,.2f}€",
            'delta_color': 'normal' if realized_gain >= 0 else 'inverse'
        }
    ]
    
    if dividends > 0:
        metrics.append({
            'title': '💰 Dividendos',
            'value': f"{dividends:,.2f}€"
        })
    
    metrics_row(metrics, columns=len(metrics))


def risk_metrics_cards(metrics: Dict):
    """
    Muestra tarjetas de métricas de riesgo.
    
    Args:
        metrics: Dict con métricas de benchmarks
    """
    if not metrics or 'error' in metrics:
        st.warning("No hay métricas disponibles")
        return
    
    risk = metrics.get('risk', {})
    ra = metrics.get('risk_adjusted', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Volatilidad",
            f"{risk.get('portfolio_volatility', 0):.2f}%",
            help="Desviación estándar anualizada"
        )
    
    with col2:
        beta = risk.get('beta', 1)
        st.metric(
            "Beta",
            f"{beta:.2f}",
            delta="Defensivo" if beta < 1 else "Agresivo" if beta > 1 else "Neutral"
        )
    
    with col3:
        sharpe = ra.get('portfolio_sharpe', 0)
        interpretation = "Excelente" if sharpe >= 2 else "Bueno" if sharpe >= 1 else "Aceptable" if sharpe >= 0 else "Malo"
        st.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            delta=interpretation
        )
    
    with col4:
        alpha = ra.get('alpha', 0)
        st.metric(
            "Alpha",
            f"{alpha:+.2f}%",
            delta="Genera valor" if alpha > 0 else "Destruye valor",
            delta_color="normal" if alpha >= 0 else "inverse"
        )


def gain_loss_indicator(value: float, show_icon: bool = True) -> str:
    """
    Retorna un indicador visual de ganancia/pérdida.
    
    Args:
        value: Valor numérico
        show_icon: Si mostrar emoji
    
    Returns:
        String formateado con color/emoji
    """
    if value > 0:
        icon = "🟢 " if show_icon else ""
        return f"{icon}+{value:,.2f}€"
    elif value < 0:
        icon = "🔴 " if show_icon else ""
        return f"{icon}{value:,.2f}€"
    else:
        icon = "⚪ " if show_icon else ""
        return f"{icon}{value:,.2f}€"


def performance_badge(value: float, thresholds: Dict = None) -> None:
    """
    Muestra un badge de rendimiento coloreado.
    
    Args:
        value: Valor de la métrica
        thresholds: Dict con umbrales para colores
    """
    if thresholds is None:
        thresholds = {'excellent': 2, 'good': 1, 'ok': 0}
    
    if value >= thresholds.get('excellent', 2):
        st.success(f"🌟 Excelente: {value:.2f}")
    elif value >= thresholds.get('good', 1):
        st.info(f"✅ Bueno: {value:.2f}")
    elif value >= thresholds.get('ok', 0):
        st.warning(f"🆗 Aceptable: {value:.2f}")
    else:
        st.error(f"❌ Mejorable: {value:.2f}")


def info_card(title: str, content: str, icon: str = "ℹ️"):
    """
    Muestra una tarjeta informativa.
    """
    st.markdown(f"""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 15px; margin: 10px 0;">
        <h4>{icon} {title}</h4>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)


def progress_to_goal(current: float, goal: float, title: str = "Progreso"):
    """
    Muestra una barra de progreso hacia un objetivo.
    """
    progress = min(current / goal, 1.0) if goal > 0 else 0
    
    st.markdown(f"**{title}**")
    st.progress(progress)
    st.caption(f"{current:,.2f}€ de {goal:,.2f}€ ({progress*100:.1f}%)")
