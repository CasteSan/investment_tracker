# 📊 SESIÓN 3: Portfolio Module - Guía de Implementación

## 🎯 Resumen
El módulo `portfolio.py` es el "cerebro financiero" del sistema. Calcula todas las métricas de tu cartera:
- Posiciones actuales con precio medio
- Plusvalías latentes y realizadas
- Rentabilidad por activo y global
- Distribución de cartera
- Estadísticas avanzadas

## ⚡ Implementación Rápida (5-10 minutos)

### Paso 1: Copiar archivos nuevos

Copia estos archivos a tu proyecto:

```
investment_tracker/
├── src/
│   └── portfolio.py          ← NUEVO (copiar de este paquete)
└── test_portfolio.py         ← NUEVO (copiar de este paquete)
```

### Paso 2: Verificar que funciona

```bash
# Activar entorno virtual
venv\Scripts\activate

# Ejecutar test
python test_portfolio.py
```

Deberías ver todos los tests pasando (15/15).

## 📝 Mensaje de Commit

```bash
git add .
git commit -m "feat: Sesión 3 - Portfolio Module (análisis de cartera)

✨ Funcionalidades añadidas:
- Módulo completo de análisis de cartera (portfolio.py)
- Cálculo de posiciones actuales con precio medio FIFO
- Plusvalías latentes (no realizadas) por activo y totales
- Plusvalías realizadas (ventas) con detalle por operación
- Rentabilidad total incluyendo dividendos
- Distribución de cartera por activo y por tipo
- Performance ranking de activos (mejores/peores)
- Estadísticas avanzadas (media, mediana, desviación, etc.)
- Evolución histórica del capital invertido
- Timeline de aportaciones/retiradas
- Lotes disponibles para planificación FIFO
- Funciones de conveniencia (quick_summary, print_positions)

📁 Nuevos archivos:
- src/portfolio.py: Módulo principal (700+ líneas, completamente funcional)
- test_portfolio.py: Suite de pruebas completa (15 tests)

✅ Tests: Todos pasando (15/15)

📊 Funcionalidades del Portfolio:
  - get_current_positions(): Posiciones actuales con filtros
  - get_position(ticker): Detalle de posición específica
  - get_available_lots(ticker): Lotes FIFO disponibles
  - get_total_value(): Valor total de cartera
  - get_unrealized_gains(): Plusvalías latentes
  - get_realized_gains(year): Plusvalías realizadas
  - get_total_return(): Rentabilidad total
  - get_performance_by_asset(): Ranking de rendimiento
  - get_allocation(by): Distribución porcentual
  - get_historical_value(): Evolución temporal
  - get_portfolio_summary(): Resumen completo
  - get_statistics(): Métricas estadísticas

🎯 Estado: Sesión 3 completada - Análisis de cartera operativo

💡 Próximo paso: Sesión 4 - Tax Calculator (cálculos fiscales FIFO/LIFO)"
```

## 🔧 Uso del Módulo Portfolio

### Uso básico

```python
from src.portfolio import Portfolio

# Crear instancia
portfolio = Portfolio()

# Ver posiciones actuales
positions = portfolio.get_current_positions()
print(positions)

# Valor total de la cartera
total = portfolio.get_total_value()
print(f"Valor: {total:,.2f}€")

# Plusvalías latentes
unrealized = portfolio.get_unrealized_gains()
print(f"Ganancia latente: {unrealized['total_gain']:+,.2f}€")

# Cerrar conexión
portfolio.close()
```

### Con precios actuales de mercado

```python
# Si tienes precios actuales (de yfinance, manual, etc.)
current_prices = {
    'TEF': 4.25,
    'BBVA': 10.80,
    'LP68478350': 14.50,
    # ...
}

positions = portfolio.get_current_positions(current_prices=current_prices)
total_value = portfolio.get_total_value(current_prices=current_prices)
```

### Filtrar por tipo de activo

```python
# Solo acciones
acciones = portfolio.get_current_positions(asset_type='accion')

# Solo fondos
fondos = portfolio.get_current_positions(asset_type='fondo')

# Solo ETFs
etfs = portfolio.get_current_positions(asset_type='etf')
```

### Análisis de rentabilidad

```python
# Rentabilidad total (incluyendo dividendos)
returns = portfolio.get_total_return()
print(f"Invertido: {returns['total_invested']:,.2f}€")
print(f"Valor actual: {returns['current_value']:,.2f}€")
print(f"Ganancia total: {returns['total_gain']:+,.2f}€")
print(f"Rentabilidad: {returns['total_return_pct']:+.2f}%")

# Ranking de activos por rendimiento
perf = portfolio.get_performance_by_asset()
print("Mejores activos:")
print(perf.head())
```

### Plusvalías realizadas (para fiscalidad)

```python
# Ventas del año 2024
realized_2024 = portfolio.get_realized_gains(year=2024)
print(f"Ganancias: {realized_2024['total_gains']:+,.2f}€")
print(f"Pérdidas: {realized_2024['total_losses']:,.2f}€")
print(f"Neto: {realized_2024['net_gain']:+,.2f}€")

# Detalle de cada venta
print(realized_2024['sales_detail'])
```

### Distribución de cartera

```python
# Por activo
alloc_asset = portfolio.get_allocation(by='asset')
print(alloc_asset)

# Por tipo (accion/fondo/etf)
alloc_type = portfolio.get_allocation(by='type')
print(alloc_type)
```

### Resumen completo

```python
summary = portfolio.get_portfolio_summary()
print(f"""
📊 Resumen de Cartera
=====================
Valor total: {summary['total_value']:,.2f}€
Invertido: {summary['total_invested']:,.2f}€
Ganancia: {summary['total_gain']:+,.2f}€ ({summary['total_return_pct']:+.2f}%)
Posiciones: {summary['num_positions']}

🏆 Mejor: {summary['top_performer']['ticker']} ({summary['top_performer']['gain_pct']:+.2f}%)
🥉 Peor: {summary['bottom_performer']['ticker']} ({summary['bottom_performer']['gain_pct']:+.2f}%)
""")
```

### Funciones de conveniencia

```python
from src.portfolio import quick_summary, print_positions

# Resumen rápido
summary = quick_summary()
print(f"Valor: {summary['total_value']:,.2f}€")

# Imprimir posiciones formateadas
print_positions()
```

## 🎯 Próximos Pasos

### Sesión 4: Tax Calculator
- Cálculos fiscales FIFO/LIFO configurables
- Generación de informes fiscales
- Simulación de ventas
- Identificación de lotes para optimización fiscal

### Sesión 5: Dividends Module
- Tracking detallado de dividendos
- Cálculo de dividend yield
- Rentabilidad total con dividendos

### Sesión 6: Benchmarks Module
- Comparación con índices (IBEX, S&P 500, etc.)
- Normalización base 100
- Cálculo de outperformance

### Sesión 7: Streamlit Dashboard
- Interface visual completa
- Gráficos interactivos
- Formularios de entrada

## ❓ Troubleshooting

### "No hay posiciones en la cartera"
Asegúrate de haber importado transacciones primero:
```python
from src.data_loader import DataLoader
loader = DataLoader()
loader.import_from_csv('data/mi_portfolio.csv')
```

### "ModuleNotFoundError"
Verifica que estás en el entorno virtual:
```bash
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### Los precios no son correctos
Sin integración con API de mercado, el módulo usa el último precio de compra como aproximación. Para precios reales, pasa el dict `current_prices`.
