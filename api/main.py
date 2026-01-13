"""
FastAPI REST API - Investment Tracker

Demuestra que la arquitectura de capas permite exponer la misma
logica de negocio via API REST, reutilizando los servicios existentes.

Uso:
    uvicorn api.main:app --reload

Endpoints:
    GET  /                    - Health check e info
    GET  /dashboard           - Datos del dashboard (posiciones, metricas)
    GET  /dashboard/metrics   - Metricas avanzadas (Sharpe, Beta, etc.)
    GET  /funds               - Buscar fondos con filtros
    GET  /funds/{isin}        - Detalle de un fondo
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Importar servicios - la misma capa que usa Streamlit
from src.services import PortfolioService, FundService


# =============================================================================
# MODELOS PYDANTIC (Schemas de respuesta)
# =============================================================================

class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str = "ok"
    version: str = "1.0.0"
    timestamp: str
    services: Dict[str, bool]


class MetricsResponse(BaseModel):
    """Metricas basicas de cartera."""
    total_value: float = Field(description="Valor total de mercado en EUR")
    total_cost: float = Field(description="Coste total de adquisicion en EUR")
    unrealized_gain: float = Field(description="Ganancia/perdida no realizada en EUR")
    unrealized_pct: float = Field(description="Ganancia/perdida en porcentaje")
    num_positions: int = Field(description="Numero de posiciones")


class FiscalSummaryResponse(BaseModel):
    """Resumen fiscal del ano."""
    realized_gain: float
    year: int
    method: str


class DividendTotalsResponse(BaseModel):
    """Totales de dividendos."""
    count: int
    total_gross: float
    total_net: float
    total_withholding: float
    year: int


class PositionResponse(BaseModel):
    """Posicion individual."""
    ticker: str
    name: str
    asset_type: str
    shares: float
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_gain: float
    unrealized_gain_pct: float
    currency: str


class DashboardResponse(BaseModel):
    """Respuesta completa del dashboard."""
    metrics: MetricsResponse
    fiscal_summary: FiscalSummaryResponse
    dividend_totals: DividendTotalsResponse
    positions: List[Dict[str, Any]]
    generated_at: str


class RiskMetricsResponse(BaseModel):
    """Metricas de riesgo."""
    volatility: float = Field(description="Volatilidad anualizada")
    var_95: float = Field(description="Value at Risk al 95%")
    max_drawdown: float = Field(description="Maxima caida historica")
    beta: float = Field(description="Beta vs benchmark")


class PerformanceMetricsResponse(BaseModel):
    """Metricas de rendimiento."""
    total_return: float = Field(description="Retorno total acumulado")
    cagr: float = Field(description="Tasa de crecimiento anual compuesto")
    sharpe_ratio: float = Field(description="Ratio de Sharpe")
    sortino_ratio: float = Field(description="Ratio de Sortino")
    alpha: float = Field(description="Alpha de Jensen")


class MetaInfoResponse(BaseModel):
    """Metadata de las metricas."""
    start_date: str
    end_date: str
    benchmark: str
    trading_days: int
    has_benchmark_data: bool


class AdvancedMetricsResponse(BaseModel):
    """Metricas avanzadas completas."""
    risk: RiskMetricsResponse
    performance: PerformanceMetricsResponse
    meta: MetaInfoResponse


class FundResponse(BaseModel):
    """Respuesta de fondo individual."""
    isin: str
    name: str
    category: Optional[str] = None
    manager: Optional[str] = None
    ter: Optional[float] = None
    risk_level: Optional[int] = None
    morningstar_rating: Optional[int] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    region: Optional[str] = None
    currency: Optional[str] = None


class FundSearchResponse(BaseModel):
    """Respuesta de busqueda de fondos."""
    funds: List[FundResponse]
    total: int
    filters_applied: Dict[str, Any]


# =============================================================================
# APLICACION FASTAPI
# =============================================================================

app = FastAPI(
    title="Investment Tracker API",
    description="""
API REST para el gestor de carteras de inversion.

Esta API demuestra la arquitectura de capas del proyecto:
- **Capa de Presentacion**: FastAPI (esta API) y Streamlit (UI web)
- **Capa de Servicios**: PortfolioService, FundService
- **Capa Core**: Calculos de analytics (Sharpe, Beta, VaR, etc.)
- **Capa de Datos**: SQLite + SQLAlchemy

Ambas interfaces (API y UI) consumen los mismos servicios.
    """,
    version="1.0.0",
    contact={
        "name": "Investment Tracker",
    },
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check y estado de la API.

    Verifica que los servicios esten disponibles.
    """
    services_status = {}

    # Verificar PortfolioService
    try:
        with PortfolioService() as ps:
            services_status["portfolio_service"] = True
    except Exception:
        services_status["portfolio_service"] = False

    # Verificar FundService
    try:
        with FundService() as fs:
            services_status["fund_service"] = True
    except Exception:
        services_status["fund_service"] = False

    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        services=services_status
    )


@app.get("/dashboard", response_model=DashboardResponse, tags=["Portfolio"])
async def get_dashboard(
    fiscal_year: int = Query(
        default=None,
        description="Ano fiscal. Default: ano actual"
    )
):
    """
    Obtiene datos completos del dashboard.

    Incluye:
    - Metricas de cartera (valor, coste, ganancia)
    - Posiciones actuales con precios de mercado
    - Resumen fiscal del ano
    - Totales de dividendos

    Este endpoint usa PortfolioService, el mismo servicio que usa
    la pagina Dashboard de Streamlit.
    """
    if fiscal_year is None:
        fiscal_year = datetime.now().year

    try:
        with PortfolioService() as service:
            data = service.get_dashboard_data(fiscal_year=fiscal_year)

            # Convertir DataFrame de posiciones a lista de dicts
            positions_list = []
            if not data['positions'].empty:
                positions_list = data['positions'].to_dict('records')

            return DashboardResponse(
                metrics=MetricsResponse(**data['metrics']),
                fiscal_summary=FiscalSummaryResponse(**data['fiscal_summary']),
                dividend_totals=DividendTotalsResponse(**data['dividend_totals']),
                positions=positions_list,
                generated_at=datetime.now().isoformat()
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos del dashboard: {str(e)}"
        )


@app.get("/dashboard/metrics", response_model=AdvancedMetricsResponse, tags=["Portfolio"])
async def get_advanced_metrics(
    start_date: str = Query(
        default=None,
        description="Fecha inicio (YYYY-MM-DD). Default: 1 ano atras"
    ),
    end_date: str = Query(
        default=None,
        description="Fecha fin (YYYY-MM-DD). Default: hoy"
    ),
    benchmark: str = Query(
        default="SP500",
        description="Benchmark para comparacion: SP500, IBEX35, MSCIWORLD"
    ),
    risk_free_rate: float = Query(
        default=0.02,
        description="Tasa libre de riesgo anual (decimal)"
    )
):
    """
    Obtiene metricas avanzadas de riesgo y rendimiento.

    Calcula:
    - **Riesgo**: Volatilidad, VaR, Max Drawdown, Beta
    - **Rendimiento**: Total Return, CAGR, Sharpe, Sortino, Alpha

    Usa los calculos del modulo src/core/analytics/.
    """
    try:
        with PortfolioService() as service:
            metrics = service.get_portfolio_metrics(
                start_date=start_date,
                end_date=end_date,
                benchmark_name=benchmark,
                risk_free_rate=risk_free_rate
            )

            return AdvancedMetricsResponse(
                risk=RiskMetricsResponse(**metrics['risk']),
                performance=PerformanceMetricsResponse(**metrics['performance']),
                meta=MetaInfoResponse(**metrics['meta'])
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando metricas: {str(e)}"
        )


@app.get("/funds", response_model=FundSearchResponse, tags=["Funds"])
async def search_funds(
    name: str = Query(default=None, description="Buscar en nombre (parcial)"),
    category: str = Query(default=None, description="Categoria del fondo"),
    manager: str = Query(default=None, description="Gestora"),
    region: str = Query(default=None, description="Region geografica"),
    max_ter: float = Query(default=None, description="TER maximo (%)"),
    min_rating: int = Query(default=None, ge=1, le=5, description="Rating Morningstar minimo"),
    max_risk: int = Query(default=None, ge=1, le=7, description="Nivel de riesgo maximo"),
    min_return_1y: float = Query(default=None, description="Rentabilidad 1A minima (%)"),
    order_by: str = Query(default="name", description="Campo para ordenar"),
    order_desc: bool = Query(default=False, description="Orden descendente"),
    limit: int = Query(default=50, ge=1, le=200, description="Limite de resultados"),
    offset: int = Query(default=0, ge=0, description="Desplazamiento")
):
    """
    Busca fondos en el catalogo con filtros.

    Filtros disponibles:
    - Texto: nombre, categoria, gestora, region
    - Numericos: TER maximo, rating minimo, riesgo maximo, rentabilidad minima
    - Ordenamiento y paginacion

    Este endpoint usa FundService, el mismo servicio que usa
    la pagina Buscador de Fondos de Streamlit.
    """
    try:
        with FundService() as service:
            funds = service.search_funds(
                name=name,
                category=category,
                manager=manager,
                region=region,
                max_ter=max_ter,
                min_rating=min_rating,
                max_risk_level=max_risk,
                min_return_1y=min_return_1y,
                order_by=order_by,
                order_desc=order_desc,
                limit=limit,
                offset=offset
            )

            # Convertir a respuesta
            funds_response = []
            for fund in funds:
                funds_response.append(FundResponse(
                    isin=fund.isin,
                    name=fund.name,
                    category=fund.category,
                    manager=fund.manager,
                    ter=fund.ter,
                    risk_level=fund.risk_level,
                    morningstar_rating=fund.morningstar_rating,
                    return_1y=fund.return_1y,
                    return_3y=fund.return_3y,
                    return_5y=fund.return_5y,
                    region=fund.region,
                    currency=fund.currency
                ))

            # Construir filtros aplicados
            filters = {
                k: v for k, v in {
                    "name": name,
                    "category": category,
                    "manager": manager,
                    "region": region,
                    "max_ter": max_ter,
                    "min_rating": min_rating,
                    "max_risk": max_risk,
                    "min_return_1y": min_return_1y,
                }.items() if v is not None
            }

            return FundSearchResponse(
                funds=funds_response,
                total=len(funds_response),
                filters_applied=filters
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error buscando fondos: {str(e)}"
        )


@app.get("/funds/{isin}", response_model=FundResponse, tags=["Funds"])
async def get_fund(isin: str):
    """
    Obtiene detalles de un fondo por ISIN.

    Args:
        isin: Codigo ISIN del fondo (ej: IE00B3RBWM25)
    """
    try:
        with FundService() as service:
            fund = service.get_fund_by_isin(isin)

            if fund is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Fondo con ISIN '{isin}' no encontrado"
                )

            return FundResponse(
                isin=fund.isin,
                name=fund.name,
                category=fund.category,
                manager=fund.manager,
                ter=fund.ter,
                risk_level=fund.risk_level,
                morningstar_rating=fund.morningstar_rating,
                return_1y=fund.return_1y,
                return_3y=fund.return_3y,
                return_5y=fund.return_5y,
                region=fund.region,
                currency=fund.currency
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo fondo: {str(e)}"
        )


# =============================================================================
# ENDPOINTS ADICIONALES
# =============================================================================

@app.get("/benchmarks", tags=["Portfolio"])
async def get_benchmarks():
    """
    Lista los benchmarks disponibles para comparacion.
    """
    try:
        with PortfolioService() as service:
            benchmarks = service.get_available_benchmarks()
            return {"benchmarks": benchmarks}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo benchmarks: {str(e)}"
        )


@app.get("/funds/stats/catalog", tags=["Funds"])
async def get_catalog_stats():
    """
    Obtiene estadisticas del catalogo de fondos.
    """
    try:
        with FundService() as service:
            stats = service.get_catalog_stats()
            return {"stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadisticas: {str(e)}"
        )
