# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.0] - 2026-01-14

### Added

- **Catalogo Inteligente de Fondos con Morningstar**
  - Importar fondos por ISIN desde Morningstar API (`mstarpy`)
  - Vista previa de datos antes de guardar
  - Dashboard profesional por fondo con graficos interactivos
  - Boton "Actualizar datos" para refrescar desde Morningstar

- **Dashboard de Fondo**
  - Grafico NAV con rentabilidad del periodo y zoom interactivo
  - Barras de rentabilidad por periodo (YTD, 1A, 3A, 5A) con colores
  - Treemap de holdings agrupado por sector
  - Donuts de sectores y paises con etiquetas externas
  - KPIs: ISIN, categoria, TER, riesgo SRRI, rentabilidad YTD

- **Categorias Personalizadas Dinamicas**
  - Nueva tabla `categories` en base de datos
  - Crear categorias desde la UI (importar y editar)
  - Filtro por categoria en catalogo (pills horizontales)
  - 10 categorias por defecto: RV Global, RV USA, RF Corto Plazo, etc.

- **Paginacion de Catalogo**
  - 10 fondos por pagina
  - Controles Anterior/Siguiente
  - Indicador de pagina actual

- **Providers** (`src/providers/`)
  - `FundDataProvider` para Morningstar
  - Extraccion de: datos basicos, rentabilidades, volatilidad, holdings, sectores, paises
  - Conversion de rentabilidades acumuladas a anualizadas

### Changed

- `FundService` ampliado con gestion de categorias
- `FundRepository.upsert_from_provider()` para mapeo de datos Morningstar
- Migraciones actualizadas para soportar multi-portfolio

### Fixed

- Grafico NAV con manejo defensivo de errores 401 de API
- Parseo robusto de JSON para sectores/paises
- Cache invalidation incluye categorias

### Technical

- `scripts/apply_migrations.py` - Script de migraciones multi-BD
- Campos JSON en modelo Fund: `top_holdings`, `asset_allocation`
- Fuentes XXL (16-22px) para mejor legibilidad

---

## [1.2.0] - 2026-01-13

### Added

- **Multi-Portfolio (Multi-Cartera)**
  - Soporte para multiples carteras independientes
  - Cada cartera usa su propio archivo SQLite en `data/portfolios/`
  - `ProfileManager` para gestionar perfiles de cartera
  - Selector de cartera en sidebar con opcion de crear nuevas
  - Funcionalidad de renombrar carteras
  - Migracion automatica de `database.db` existente a `portfolios/Principal.db`

- **Indicador de precios de mercado**
  - Nueva columna `has_market_prices` en series de cartera
  - Benchmarks filtra dias sin precios reales (evita linea plana)
  - Advertencia clara cuando faltan precios de mercado

### Fixed

- **Sincronizacion de db_path en todas las paginas**
  - `main.py` ahora usa precios de mercado (igual que Dashboard)
  - `Benchmarks.py` usa db_path de cartera seleccionada
  - `TaxCalculator` y `DividendManager` en PortfolioService usan db_path
  - `Configuracion.py` usa db_path para limpiar cache y mostrar tamano BD

### Testing

- 184 tests unitarios (+21 nuevos para ProfileManager)
- Tests de creacion, renombrado, duplicacion y eliminacion de perfiles

---

## [1.1.0] - 2026-01-13

### Added

- **Heatmap interactivo en Dashboard**
  - Treemap con tamano proporcional al peso en cartera
  - Color basado en variacion del ultimo dia de mercado (rojo/gris/verde)
  - Filtros por categoria (Todos, Fondos/ETF, Acciones)
  - Escala de color dinamica con percentil 95
  - `MarketDataManager.get_latest_price_and_change()` para calculo robusto

- **Etiquetas inteligentes en graficos**
  - Nombres de activos en lugar de tickers
  - Truncado inteligente (`smart_truncate()`) para nombres > 15 caracteres
  - Nombres completos en tooltips

### Changed

- `PortfolioService.get_heatmap_data()` usa logica robusta de variacion diaria
- `PortfolioService.enrich_with_display_names()` nuevo metodo
- Graficos de donut, barras y treemap usan `display_name`

### Testing

- 163 tests unitarios (+25 nuevos)
- Tests para `smart_truncate()` y `get_latest_price_and_change()`

---

## [1.0.0] - 2026-01-13

### Arquitectura Hexagonal Refactor

Refactorizacion completa del proyecto en 8 sesiones para implementar
arquitectura hexagonal (puertos y adaptadores).

### Added

- **Capa de Servicios** (`src/services/`)
  - `PortfolioService` - Orquestador de operaciones de cartera
  - `FundService` - Gestion de catalogo de fondos
  - `BaseService` - Clase base con context manager

- **Capa Core** (`src/core/analytics/`)
  - Metricas de riesgo: Volatilidad, VaR, CVaR, Beta, Max Drawdown
  - Metricas de rendimiento: Sharpe, Sortino, Alpha, CAGR

- **Capa de Datos** (`src/data/`)
  - Modelo `Fund` para catalogo de fondos
  - `FundRepository` con busqueda avanzada
  - Migraciones para nuevas tablas

- **API REST** (`api/`)
  - FastAPI con documentacion Swagger automatica
  - Endpoints: `/dashboard`, `/dashboard/metrics`, `/funds`
  - Mismos servicios que Streamlit

- **UI Buscador de Fondos** (`app/pages/8_Buscador_Fondos.py`)
  - Filtros avanzados (categoria, TER, rating, riesgo)
  - Exportacion a CSV

- **Testing**
  - 138 tests unitarios con pytest
  - Fixtures para BD temporal
  - Cobertura de servicios, repositorios y analytics

### Changed

- Dashboard refactorizado para usar `PortfolioService`
- Pagina de Analisis usa metricas del modulo Core
- Estructura de carpetas reorganizada

### Fixed

- `Database.get_transaction_by_id()` - Metodo faltante
- `calculate_cagr()` - Corregido a `calculate_cagr_from_prices()`
- yfinance con ISINs - Mejorado manejo de errores

### Documentation

- README.md completamente reescrito (educativo)
- CLAUDE.md actualizado con convenciones
- Plan de escalabilidad consolidado en `docs/`

---

## [0.3.0] - 2026-01-06

### Added
- Modulo de benchmarks
- Comparacion con indices (SP500, IBEX35)
- Graficos de rendimiento relativo

---

## [0.2.0] - 2026-01-04

### Added
- Modulo de dividendos
- Calculo de rentabilidad por dividendo
- Calendario de cobros

---

## [0.1.0] - 2026-01-02

### Added
- Estructura inicial del proyecto
- Base de datos SQLite
- UI basica con Streamlit
- Calculo de posiciones y rentabilidad
- Tax calculator (metodo FIFO)
