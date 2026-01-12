# 📅 Plan de Implementación: Investment Tracker 2.0

Este documento detalla el plan de trabajo para refactorizar el proyecto hacia una arquitectura escalable (Hexagonal/Capas) e implementar nuevas funcionalidades avanzadas.

**Objetivos:**
1.  **Escalabilidad:** Separar lógica de negocio (Core/Services) de la UI (Streamlit), permitiendo futura migración fácil a FastAPI.
2.  **Funcionalidad:** Añadir métricas avanzadas (Sharpe, Beta) y catálogo de fondos.
3.  **Calidad:** Mejorar estructura de directorios y testing.

---

## 🏗️ Fase 1: Cimientos y Arquitectura

### Sesión 1: Reestructuración de Directorios y Capa de Servicios
**Objetivo:** Establecer la nueva estructura de carpetas y crear la abstracción base de la capa de servicios. Mover archivos sin romper la ejecución actual.

*   **Acciones:**
    1.  Crear estructura: `src/core`, `src/services`, `src/data`, `src/providers`, `api/`.
    2.  Mover `database.py` a `src/data/database.py`.
    3.  **Crear archivo de compatibilidad** `src/database.py` que re-exporte desde `src/data/database.py` para no romper imports existentes.
    4.  Crear `src/services/base.py` (clase base o protocolo para servicios).
    5.  Crear `src/exceptions.py` para errores de dominio personalizados.
    6.  Crear `src/data/__init__.py` y `src/services/__init__.py` con exports públicos.
*   **Archivos Afectados:**
    *   `src/database.py` -> `src/data/database.py` (movido)
    *   [NEW] `src/database.py` (compatibilidad - re-exporta desde src/data/)
    *   [NEW] `src/data/__init__.py`
    *   [NEW] `src/services/__init__.py`
    *   [NEW] `src/services/base.py`
    *   [NEW] `src/exceptions.py`
    *   [NEW] `src/core/__init__.py`
    *   [NEW] `src/providers/__init__.py`
    *   [NEW] `api/__init__.py`
*   **Validación:** Ejecutar la app actual (`streamlit run ...`) y verificar que funciona sin modificar ningún import existente.
*   **Commit:** `refactor: restructure project folders and add service layer base`
*   **Documentación:** Generar `Plan_escalabilidad/commit_session1.md` con descripción detallada.

### Sesión 2: Creación de PortfolioService (El Puente)
**Objetivo:** Desacoplar la lógica de visualización de la lógica de negocio. Streamlit dejará de llamar directamente a `Portfolio` para cálculos complejos.

*   **Acciones:**
    1.  Crear `src/services/portfolio_service.py`.
    2.  Mover lógica de orquestación (ej: preparar datos para el dashboard) de `app/pages/1_Dashboard.py` al servicio.
    3.  El servicio debe devolver dicts o objetos de dominio, no elementos UI.
    4.  Refactorizar `app/pages/1_Dashboard.py` para instanciar `PortfolioService` y consumir sus métodos.
*   **Archivos Afectados:**
    *   [NEW] `src/services/portfolio_service.py`
    *   `app/pages/1_Dashboard.py`
    *   `src/portfolio.py` (limpieza menor si aplica)
*   **Validación:** El Dashboard debe verse idéntico, pero el código de la página debe ser mucho más limpio y corto.
*   **Commit:** `feat: introduce PortfolioService and refactor dashboard page`

### Sesión 3: Infraestructura de Testing (Pytest)
**Objetivo:** Establecer un entorno de pruebas robusto antes de implementar lógica compleja de métricas.

*   **Acciones:**
    1.  Crear `tests/conftest.py` con fixtures para BD en memoria y datos de prueba (mocks).
    2.  Migrar un test existente (ej: `test_portfolio.py`) a formato `pytest` en `tests/unit/test_portfolio_service.py`.
    3.  Configurar script para correr tests fácilmente.
*   **Archivos Afectados:**
    *   [NEW] `tests/conftest.py`
    *   [NEW] `tests/unit/test_portfolio_service.py`
    *   `requirements.txt` (asegurar pytest)
*   **Validación:** Ejecutar `pytest` y obtener "All passed".
*   **Commit:** `test: setup pytest infrastructure and migrate portfolio tests`

---

## 📈 Fase 2: Analítica Avanzada

### Sesión 4: Módulo Core de Analytics (Risk & Performance)
**Objetivo:** Implementar la lógica matemática de las métricas avanzadas en una capa pura (Core), sin dependencias de UI ni BD.

*   **Acciones:**
    1.  Crear `src/core/analytics/`.
    2.  Implementar `risk.py`: Cálculo de Volatilidad, VaR, Beta (req. benchmark).
    3.  Implementar `performance.py`: Sharpe Ratio, Sortino Ratio, Alpha.
    4.  Estas funciones deben recibir DataFrames/Series genéricos y devolver floats.
*   **Archivos Afectados:**
    *   [NEW] `src/core/analytics/risk.py`
    *   [NEW] `src/core/analytics/performance.py`
    *   [NEW] `tests/unit/test_analytics.py` (Tests unitarios matemáticos)
*   **Validación:** Tests unitarios verificando los cálculos con datos conocidos.
*   **Commit:** `feat: add core analytics module for risk and performance metrics`

### Sesión 5: Integración de Analytics en Servicio y UI
**Objetivo:** Conectar los cálculos matemáticos con los datos reales del usuario y mostrarlos.

*   **Acciones:**
    1.  Actualizar `PortfolioService.get_portfolio_metrics()` para usar `src/core/analytics`.
    2.  El servicio se encarga de obtener precios históricos y benchmark necesarios para los cálculos.
    3.  Crear/Actualizar sección en `app/pages/3_Análisis.py` para mostrar las nuevas tarjetas de métricas.
*   **Archivos Afectados:**
    *   `src/services/portfolio_service.py`
    *   `app/pages/3_Análisis.py`
    *   `src/portfolio.py` (posibles helpers para data histórica)
*   **Validación:** Verificar en Streamlit que aparecen los KPIs de Sharpe, Beta, etc.
*   **Commit:** `feat: integrate advanced metrics into analysis page`

---

## 📋 Fase 3: Catálogo de Fondos

### Sesión 6: Modelo de Datos y Repositorio de Fondos
**Objetivo:** Crear la estructura para almacenar y consultar el catálogo de fondos.

*   **Acciones:**
    1.  Crear modelo `Fund` en `src/data/models.py` (ticker, nombre, sector, riesgo, gastos, etc.).
    2.  Crear migración o script para actualizar la BD existente.
    3.  Crear `src/data/repositories/fund_repository.py` con métodos de filtrado (por sector, riesgo).
*   **Archivos Afectados:**
    *   `src/data/models.py`
    *   [NEW] `src/data/repositories/fund_repository.py`
    *   [NEW] `src/data/migrations/xxx_add_fund_table.py`
*   **Validación:** Verificar creación de tabla en SQLite y funcionamiento de queries básicas.
*   **Commit:** `feat: add fund data model and repository`

### Sesión 7: Servicio y UI de Catálogo
**Objetivo:** Permitir al usuario explorar y buscar fondos.

*   **Acciones:**
    1.  Crear `src/services/fund_service.py`.
    2.  Crear nueva página `app/pages/8_🔍_Buscador_Fondos.py`.
    3.  Implementar filtros visuales en Streamlit conectados al `FundService`.
*   **Archivos Afectados:**
    *   [NEW] `src/services/fund_service.py`
    *   [NEW] `app/pages/8_🔍_Buscador_Fondos.py`
*   **Validación:** Página funcional donde se puede buscar y filtrar fondos.
*   **Commit:** `feat: implement fund catalog browser UI`

---

## 🚀 Fase 4: Prueba de Escalabilidad (FastAPI)

### Sesión 8: Endpoint Demo con FastAPI (Port & Adapter)
**Objetivo:** Demostrar que la arquitectura permite exponer la MISMA lógica vía API sin reescribir nada.

*   **Acciones:**
    1.  Instalar `fastapi` `uvicorn`.
    2.  Crear `api/main.py`.
    3.  Crear ruta `GET /dashboard` que inyecte `PortfolioService` y retorne su JSON.
*   **Archivos Afectados:**
    *   `requirements.txt`
    *   [NEW] `api/main.py`
*   **Validación:** Ejecutar `uvicorn api.main:app --reload` y ver el JSON del dashboard en el navegador/Postman, idéntico a los datos de Streamlit.
*   **Commit:** `feat: add fastapi skeleton and dashboard endpoint proof of concept`

---

## 📝 Instrucciones para el Agente (Claude)

Para ejecutar este plan, sigue estos pasos en cada turno:

1.  **Leer sesión actual:** Revisa el objetivo y archivos de la sesión correspondiente.
2.  **Verificar estado:** Comprueba que la sesión anterior funciona (ej: tests pasan).
3.  **Implementar:** Escribe/Edita el código siguiendo la arquitectura hexagonal (Core <- Services <- UI/API).
4.  **Validar:** Ejecuta tests o comandos de verificación.
5.  **Commit:** Usa `git commit` con el mensaje sugerido (o simúlalo si no hay git activo, pero mantén el orden lógico).
