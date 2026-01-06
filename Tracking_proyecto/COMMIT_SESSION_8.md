# 📝 COMMIT MESSAGE - Sesión 8: Mejoras Benchmarks y Correcciones

## Título del commit
```
feat: Precios de mercado reales, traspasos fiscales y correcciones múltiples (Sesión 8)
```

## Descripción completa del commit
```
feat: Precios de mercado reales, traspasos fiscales y correcciones múltiples

MEJORAS PRINCIPALES:

1. SISTEMA DE PRECIOS DE MERCADO REALES
   - Nuevo módulo src/market_data.py para descargar precios históricos
   - Nueva tabla asset_prices en database.py
   - Dashboard y Análisis ahora usan precios de mercado descargados
   - Método get_all_latest_prices() para obtener últimos precios
   
2. BENCHMARKS CON VALOR REAL DE CARTERA
   - Gráfico estilo Investing.com con valor real en €
   - Tres líneas: Valor Total, Posiciones Abiertas, Capital Invertido
   - Comparación Base 100 usando rendimiento sobre coste (no valor absoluto)
   - Dos modos: Solo posiciones actuales vs Cartera completa
   - Fix: Las aportaciones ya no afectan el gráfico de comparación
   
3. TRASPASOS FISCALES CORREGIDOS
   - Traspasos entre fondos ahora mantienen coste fiscal (ley española)
   - Nuevos campos en Transaction: cost_basis_eur, transfer_link_id
   - tax_calculator.py actualizado para manejar transfer_in/transfer_out
   - Formulario de traspaso mejorado con campo de coste fiscal
   
4. CORRECCIONES DE ERRORES
   - Fix: Slider en Análisis con pocas posiciones (min_value > max_value)
   - Fix: Error de índices en Benchmarks al comparar series
   - Fix: get_fiscal_detail → get_fiscal_year_detail en Fiscal.py
   - Fix: check_wash_sale_rule → get_wash_sales_in_year en Fiscal.py
   - Fix: Ganancia latente = 0 cuando no hay precios descargados

ARCHIVOS MODIFICADOS:
- src/database.py (AssetPrice model, métodos de precios)
- src/market_data.py (NUEVO - gestión precios de mercado)
- src/benchmarks.py (valor real, rendimiento sobre coste)
- src/tax_calculator.py (traspasos fiscales)
- src/portfolio.py (traspasos fiscales)
- app/pages/1_📊_Dashboard.py (precios de mercado)
- app/pages/2_➕_Añadir_Operación.py (formulario traspasos)
- app/pages/3_📈_Análisis.py (precios mercado, slider fix)
- app/pages/4_💰_Fiscal.py (corrección métodos)
- app/pages/6_🎯_Benchmarks.py (reescrito completo)

NOTAS:
- Requiere ejecutar ALTER TABLE para añadir columnas si BD existente
- Los precios se descargan desde Yahoo Finance (yfinance)
- Compatible con legislación fiscal española para traspasos
```

---

# 📋 RESUMEN DETALLADO DE CAMBIOS

## 1. Nuevo módulo: `src/market_data.py`

**Propósito:** Descargar y gestionar precios históricos de los activos de la cartera.

**Funcionalidades:**
- `download_ticker_prices()` - Descarga precios desde Yahoo Finance
- `download_portfolio_prices()` - Descarga precios de todos los activos
- `get_portfolio_market_value_series()` - Valor de mercado real por día
- `get_investing_style_data()` - Datos para gráfico estilo Investing.com
- `get_open_positions_only_series()` - Solo posiciones actualmente abiertas
- `get_download_status()` - Estado de precios descargados

## 2. Cambios en `src/database.py`

**Nueva tabla:**
```python
class AssetPrice(Base):
    __tablename__ = 'asset_prices'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    adj_close_price = Column(Float)
```

**Nuevos campos en Transaction:**
```python
cost_basis_eur = Column(Float)      # Coste fiscal heredado (traspasos)
transfer_link_id = Column(Integer)  # Vinculación entre transfer_in/out
```

**Nuevos métodos:**
- `add_asset_price()` - Guardar precio de activo
- `get_asset_prices()` - Obtener precios históricos
- `get_latest_price()` - Último precio de un ticker
- `get_all_latest_prices()` - Últimos precios de todos los tickers
- `get_tickers_with_prices()` - Tickers con precios descargados
- `delete_asset_prices()` - Eliminar precios

## 3. Cambios en `src/benchmarks.py`

**`get_portfolio_series()` reescrito:**
- Usa coste acumulado como proxy del valor
- Solo incluye fechas desde la primera transacción
- Maneja correctamente transfer_in/transfer_out

**`compare_to_benchmark()` mejorado:**
- Usa pd.merge() para alinear fechas (más robusto)
- Recorta benchmark a período de la cartera
- Evita errores de índices

## 4. Cambios en `src/tax_calculator.py`

**`get_available_lots()` actualizado:**
- Maneja transfer_in con cost_basis_eur heredado
- Maneja transfer_out reduciendo lotes sin generar plusvalía
- Preserva fecha de compra original en traspasos
- Nuevos campos en lotes: `is_transfer`, `original_purchase_date`

## 5. Cambios en `src/portfolio.py`

**`get_current_positions()` actualizado:**
- Acepta parámetro `current_prices` para usar precios de mercado
- Maneja transfer_in con cost_basis_eur heredado
- Maneja transfer_out reduciendo lotes correctamente

## 6. Cambios en páginas Streamlit

### `1_📊_Dashboard.py`
- Obtiene precios de mercado descargados
- Pasa `current_prices` a `get_current_positions()`
- Ganancia latente ahora refleja valor real de mercado

### `2_➕_Añadir_Operación.py`
- Formulario de traspaso mejorado
- Campo "Coste fiscal a traspasar" (obligatorio)
- Guarda cost_basis_eur en ambas transacciones
- Muestra plusvalía latente (que NO tributa)

### `3_📈_Análisis.py`
- Usa precios de mercado descargados
- Slider arreglado para funcionar con cualquier número de posiciones

### `4_💰_Fiscal.py`
- Corregido: `get_fiscal_detail` → `get_fiscal_year_detail`
- Corregido: `check_wash_sale_rule` → `get_wash_sales_in_year`
- Manejo de DataFrame en lugar de lista para wash sales

### `6_🎯_Benchmarks.py` (reescrito completo)
- Dos pestañas: Datos Benchmark / Precios de Cartera
- Gráfico "Evolución de Cartera (Valor Real en €)"
  - Valor Total (con P&L cerrado)
  - Posiciones Abiertas
  - Capital Invertido
  - P&L Cerrado
- Comparación Base 100 usando rendimiento sobre coste
- Dos modos: Posiciones actuales / Cartera completa
- Métricas de riesgo simplificadas

---

# 🔧 INSTRUCCIONES DE ACTUALIZACIÓN

## Si tienes base de datos existente:

```bash
cd investment_tracker

# Activar entorno virtual
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# Ejecutar actualización de BD
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///data/database.db')
with engine.connect() as conn:
    # Añadir columnas a transactions
    try:
        conn.execute(text('ALTER TABLE transactions ADD COLUMN cost_basis_eur FLOAT'))
        print('✅ Añadida columna cost_basis_eur')
    except: print('cost_basis_eur ya existe')
    
    try:
        conn.execute(text('ALTER TABLE transactions ADD COLUMN transfer_link_id INTEGER'))
        print('✅ Añadida columna transfer_link_id')
    except: print('transfer_link_id ya existe')
    
    # Crear tabla asset_prices
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS asset_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            close_price FLOAT NOT NULL,
            adj_close_price FLOAT
        )
    '''))
    print('✅ Tabla asset_prices creada')
    
    conn.commit()
"
```

## Si empiezas desde cero:

```bash
# Simplemente elimina la BD existente (si la hay)
del data\database.db  # Windows
# rm data/database.db  # Mac/Linux

# La BD se creará automáticamente al ejecutar Streamlit
streamlit run app/main.py
```

---

# 📝 COMANDOS GIT

```bash
# Añadir todos los archivos modificados
git add src/database.py
git add src/market_data.py
git add src/benchmarks.py
git add src/tax_calculator.py
git add src/portfolio.py
git add app/pages/1_📊_Dashboard.py
git add app/pages/2_➕_Añadir_Operación.py
git add app/pages/3_📈_Análisis.py
git add app/pages/4_💰_Fiscal.py
git add app/pages/6_🎯_Benchmarks.py

# Commit
git commit -m "feat: Precios de mercado reales, traspasos fiscales y correcciones múltiples (Sesión 8)

MEJORAS:
- Nuevo módulo market_data.py para precios de mercado
- Nueva tabla asset_prices en database.py
- Benchmarks con valor real en € (estilo Investing.com)
- Comparación Base 100 usando rendimiento sobre coste
- Traspasos fiscales mantienen coste según ley española
- Dashboard/Análisis usan precios de mercado descargados

CORRECCIONES:
- Slider en Análisis con pocas posiciones
- Error de índices en Benchmarks
- Métodos inexistentes en Fiscal.py
- Ganancia latente = 0 sin precios descargados

ARCHIVOS: database.py, market_data.py (nuevo), benchmarks.py,
tax_calculator.py, portfolio.py, Dashboard.py, Añadir_Operación.py,
Análisis.py, Fiscal.py, Benchmarks.py"

# Push
git push origin main
```

---

# ✅ VERIFICACIÓN POST-ACTUALIZACIÓN

1. **Dashboard:** Debe mostrar ganancia latente correcta (no 0€)
2. **Análisis:** Slider debe funcionar con cualquier número de posiciones
3. **Fiscal:** No debe haber errores, detalle de operaciones visible
4. **Benchmarks:** 
   - Gráfico de valor real con 3-4 líneas
   - Comparación Base 100 sin saltos por aportaciones
   - Ventas reflejadas correctamente
