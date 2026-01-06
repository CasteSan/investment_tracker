# =============================================================================
# SESIÓN 7: Streamlit UI - Plan de Implementación
# =============================================================================

## 🎯 Objetivo

Crear una interfaz web interactiva con Streamlit que integre todos los módulos
desarrollados (portfolio, tax_calculator, dividends, benchmarks) en un dashboard
profesional y fácil de usar.

---

## 📁 Estructura de archivos a crear

```
app/
├── main.py                          # Página principal / punto de entrada
├── pages/
│   ├── 1_📊_Dashboard.py           # Vista general de cartera
│   ├── 2_➕_Añadir_Operación.py    # Formularios de registro
│   ├── 3_📈_Análisis.py            # Análisis detallado
│   ├── 4_💰_Fiscal.py              # Información fiscal
│   ├── 5_💵_Dividendos.py          # Tracking de dividendos
│   └── 6_🎯_Benchmarks.py          # Comparación con índices
└── components/
    ├── __init__.py
    ├── charts.py                    # Funciones de gráficos Plotly
    ├── tables.py                    # Tablas formateadas
    └── metrics.py                   # Tarjetas de métricas
```

---

## 📄 Páginas a implementar

### 1️⃣ **main.py** - Página Principal
- Configuración de Streamlit (título, icono, layout)
- Sidebar con navegación y configuración global
- Resumen ejecutivo de la cartera
- Links a las páginas principales

### 2️⃣ **Dashboard** (1_📊_Dashboard.py)
**Métricas en tarjetas:**
- Valor total de la cartera
- Plusvalía latente (€ y %)
- Plusvalía realizada del año
- Dividendos recibidos del año

**Gráficos:**
- Evolución temporal de la cartera (línea)
- Distribución por activo (donut)
- Top 5 mejores/peores performers

**Tabla:**
- Posiciones actuales con colores según ganancia/pérdida

### 3️⃣ **Añadir Operación** (2_➕_Añadir_Operación.py)
**Tabs:**
- Compra
- Venta
- Dividendo
- Traspaso (fondos)

**Formularios con:**
- Validación de datos
- Cálculo automático de totales
- Preview antes de guardar
- Confirmación visual al guardar

**Sección adicional:**
- Importar desde CSV
- Últimas 10 operaciones registradas

### 4️⃣ **Análisis** (3_📈_Análisis.py)
**Filtros:**
- Rango de fechas
- Tipo de activo
- Activos específicos

**Análisis:**
- Rentabilidad por activo (tabla ordenable)
- Gráfico de rendimiento comparativo
- Distribución de cartera (por tipo, sector)
- Timeline de aportaciones

### 5️⃣ **Fiscal** (4_💰_Fiscal.py)
**Selector de año**

**Resumen fiscal:**
- Plusvalías realizadas
- Minusvalías realizadas
- Balance neto
- Impuesto estimado (con tramos)
- Pérdidas compensables

**Tabla de ventas:**
- Detalle de cada venta del año
- Lotes vendidos (FIFO)

**Herramientas:**
- Simulador de venta (impacto fiscal)
- Lotes disponibles por activo
- Alertas de regla de 2 meses
- Botón exportar a Excel

### 6️⃣ **Dividendos** (5_💵_Dividendos.py)
**Resumen:**
- Total bruto/neto del año
- Retenciones
- Yield on Cost (YOC)

**Visualización:**
- Calendario mensual de dividendos
- Gráfico de dividendos por mes
- Top pagadores

**Análisis:**
- Yield por activo
- Frecuencia de pago
- Proyección anual

**Herramientas:**
- Registrar nuevo dividendo
- Exportar a Excel

### 7️⃣ **Benchmarks** (6_🎯_Benchmarks.py)
**Configuración:**
- Selector de benchmark (SP500, IBEX35, MSCI World...)
- Rango de fechas
- Botón para descargar/actualizar datos

**Gráfico principal:**
- Cartera vs Benchmark (base 100)
- Líneas superpuestas con leyenda

**Métricas de rendimiento:**
- Rentabilidad cartera vs benchmark
- Outperformance

**Métricas de riesgo:**
- Volatilidad
- Beta
- Alpha
- Sharpe Ratio
- Max Drawdown
- VaR

**Exportar:**
- Botón para exportar análisis a Excel

---

## 🎨 Componentes reutilizables

### charts.py
```python
def plot_portfolio_evolution(df): ...
def plot_allocation_donut(df): ...
def plot_performance_bar(df): ...
def plot_benchmark_comparison(df): ...
def plot_dividend_calendar(df): ...
```

### tables.py
```python
def format_positions_table(df): ...
def format_transactions_table(df): ...
def format_fiscal_table(df): ...
def highlight_gains_losses(df): ...
```

### metrics.py
```python
def metric_card(title, value, delta=None): ...
def metrics_row(metrics_list): ...
def risk_metrics_cards(metrics_dict): ...
```

---

## 🔧 Dependencias adicionales

```bash
pip install streamlit plotly
```

---

## ⏱️ Orden de implementación

```
1. main.py + estructura básica           (~30 min)
2. components/charts.py                  (~45 min)
3. components/tables.py                  (~30 min)
4. components/metrics.py                 (~20 min)
5. Dashboard (página más compleja)       (~60 min)
6. Añadir Operación (formularios)        (~45 min)
7. Análisis                              (~40 min)
8. Fiscal                                (~45 min)
9. Dividendos                            (~40 min)
10. Benchmarks                           (~40 min)
11. Testing y refinamiento               (~45 min)
```

**Tiempo estimado total: ~7 horas**

---

## 🚀 Cómo ejecutar

```bash
# Desde la carpeta del proyecto
streamlit run app/main.py

# Se abre automáticamente en http://localhost:8501
```

---

## 📋 Preguntas antes de empezar

1. **¿Tienes Streamlit instalado?**
   - `pip install streamlit plotly`

2. **¿Prefieres tema claro u oscuro?**
   - Podemos configurar el tema por defecto

3. **¿Quieres empezar por alguna página en particular?**
   - Recomiendo: Dashboard primero (la más útil)

4. **¿Alguna funcionalidad extra que quieras?**
   - Por ejemplo: modo demo con datos de ejemplo
   - Exportar informes desde la UI
   - Gráficos específicos

---

## 📎 Notas de diseño

- **Layout wide**: Aprovechar todo el ancho de pantalla
- **Sidebar**: Configuración global (FIFO/LIFO, año fiscal)
- **Colores**: Verde para ganancias, rojo para pérdidas
- **Responsive**: Funciona en móvil/tablet
- **Cache**: Usar @st.cache_data para evitar recálculos
