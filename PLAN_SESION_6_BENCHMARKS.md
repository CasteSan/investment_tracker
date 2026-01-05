# =============================================================================
# SESIÓN 6: Benchmarks Module - Plan de Implementación
# =============================================================================

## 🎯 Objetivo

Crear un módulo para comparar el rendimiento de la cartera contra índices de
referencia (benchmarks), con normalización base 100, cálculo de outperformance
y estadísticas de riesgo.

---

## 📦 Archivo a crear: `src/benchmarks.py`

---

## 🔧 Funcionalidades a implementar

### 1️⃣ **Gestión de Datos de Benchmarks**
```python
class BenchmarkComparator:
    def __init__(self, db_path=None)
    
    def load_benchmark_from_csv(self, benchmark_name, csv_file) -> int
        # Carga datos históricos desde CSV
        # Formato esperado: date,close (o Date,Close)
        # Retorna: Número de registros importados
    
    def download_benchmark_data(self, benchmark_symbol, start_date, end_date) -> int
        # Descarga datos de yfinance (requiere internet)
        # Símbolos: ^IBEX, ^GSPC, ^STOXX50E, URTH
        # Retorna: Número de registros descargados
    
    def get_available_benchmarks(self) -> List[str]
        # Lista de benchmarks disponibles en la DB
    
    def get_benchmark_data(self, benchmark_name, start_date, end_date) -> pd.DataFrame
        # Obtiene serie temporal del benchmark
    
    def update_benchmark_data(self, benchmark_name) -> int
        # Actualiza datos del benchmark hasta hoy (requiere yfinance)
```

### 2️⃣ **Normalización Base 100**
```python
    def normalize_series(self, series: pd.Series, base_date: str = None) -> pd.Series
        # Normaliza una serie temporal a base 100
        # Si base_date es None, usa la primera fecha de la serie
        # Fórmula: valor_normalizado = (valor / valor_base) * 100
    
    def get_portfolio_series(self, start_date, end_date) -> pd.DataFrame
        # Obtiene serie temporal del valor de la cartera
        # Usa snapshots o calcula desde transacciones
```

### 3️⃣ **Comparación Cartera vs Benchmark**
```python
    def compare_to_benchmark(self, 
                            benchmark_name: str,
                            start_date: str,
                            end_date: str,
                            portfolio_filter: dict = None) -> pd.DataFrame
        # Compara cartera vs benchmark
        # 
        # Args:
        #   benchmark_name: 'IBEX35', 'SP500', etc.
        #   start_date, end_date: Rango de fechas
        #   portfolio_filter: Filtrar cartera (ej: {'asset_type': 'accion'})
        # 
        # Returns:
        #   DataFrame con columnas:
        #   - date
        #   - portfolio_value
        #   - portfolio_normalized (base 100)
        #   - benchmark_value
        #   - benchmark_normalized (base 100)
        #   - outperformance (diferencia)
    
    def compare_asset_to_benchmark(self,
                                   ticker: str,
                                   benchmark_name: str,
                                   start_date: str) -> pd.DataFrame
        # Compara un activo específico vs benchmark
```

### 4️⃣ **Cálculo de Rendimientos**
```python
    def calculate_returns(self, 
                         benchmark_name: str,
                         start_date: str,
                         end_date: str) -> Dict
        # Calcula métricas de rendimiento
        # 
        # Returns:
        #   portfolio_return: Rentabilidad % de la cartera
        #   benchmark_return: Rentabilidad % del benchmark
        #   outperformance: Diferencia (positivo = mejor que benchmark)
        #   alpha: Exceso de retorno ajustado
    
    def calculate_rolling_returns(self,
                                  benchmark_name: str,
                                  window: int = 30) -> pd.DataFrame
        # Rendimientos móviles (ej: 30 días)
```

### 5️⃣ **Estadísticas de Riesgo**
```python
    def calculate_volatility(self, series: pd.Series, annualize: bool = True) -> float
        # Volatilidad (desviación estándar de retornos)
        # annualize=True multiplica por sqrt(252) para anualizar
    
    def calculate_sharpe_ratio(self,
                               benchmark_name: str,
                               risk_free_rate: float = 0.03) -> Dict
        # Sharpe Ratio = (Return - Risk Free) / Volatility
        # Para cartera y benchmark
    
    def calculate_beta(self, benchmark_name: str, period: str = '1Y') -> float
        # Beta de la cartera respecto al benchmark
        # Beta > 1: más volátil que el mercado
        # Beta < 1: menos volátil
    
    def calculate_tracking_error(self, benchmark_name: str) -> float
        # Desviación estándar de la diferencia de retornos
        # Mide cuánto se desvía la cartera del benchmark
    
    def calculate_max_drawdown(self, series: pd.Series) -> Dict
        # Máxima caída desde un pico
        # Returns: max_drawdown, peak_date, trough_date, recovery_date
```

### 6️⃣ **Comparación Parcial de Cartera**
```python
    def compare_filtered_portfolio(self,
                                   benchmark_name: str,
                                   filters: dict,
                                   start_date: str,
                                   end_date: str) -> Dict
        # Compara solo parte de la cartera
        # 
        # Ejemplos de filtros:
        #   {'asset_type': 'accion'}  # Solo acciones
        #   {'market': 'BME'}  # Solo mercado español
        #   {'tickers': ['TEF', 'BBVA', 'SAN']}  # Activos específicos
```

### 7️⃣ **Exportación y Visualización**
```python
    def export_comparison(self,
                          benchmark_name: str,
                          filepath: str,
                          start_date: str = None,
                          end_date: str = None) -> str
        # Exporta comparación a Excel
        # Hojas: Datos, Métricas, Gráfico (imagen)
    
    def generate_comparison_chart_data(self,
                                       benchmark_name: str,
                                       start_date: str,
                                       end_date: str) -> Dict
        # Genera datos listos para Plotly/Matplotlib
```

### 8️⃣ **Funciones de Conveniencia (Print)**
```python
    def print_comparison_summary(self,
                                 benchmark_name: str,
                                 start_date: str = None,
                                 end_date: str = None)
        # Imprime resumen de comparación
    
    def print_risk_metrics(self, benchmark_name: str)
        # Imprime métricas de riesgo
    
    def print_available_benchmarks(self)
        # Lista benchmarks disponibles con sus rangos de fechas
```

---

## 📊 Estructura del Output

### Comparación Cartera vs Benchmark
```
📊 COMPARACIÓN: Mi Cartera vs IBEX 35
=====================================
Período: 01/01/2025 - 05/01/2026

📈 RENDIMIENTOS
   Mi Cartera:     +12.45%
   IBEX 35:        +8.23%
   Outperformance: +4.22% ✅

📉 RIESGO
   Volatilidad Cartera:  15.2% anual
   Volatilidad IBEX:     18.5% anual
   Beta:                 0.82
   Tracking Error:       5.3%

📊 RATIOS
   Sharpe Ratio Cartera: 0.65
   Sharpe Ratio IBEX:    0.42
   
⬇️ DRAWDOWN MÁXIMO
   Cartera: -8.5% (Mar 2025)
   IBEX:    -12.3% (Mar 2025)

📈 BASE 100 (01/01/2025)
   Fecha        Cartera    IBEX 35    Diferencia
   ------------------------------------------------
   01/01/2025   100.00     100.00     0.00
   01/04/2025   103.50     102.10     +1.40
   01/07/2025   108.20     105.80     +2.40
   01/10/2025   110.50     106.90     +3.60
   05/01/2026   112.45     108.23     +4.22
```

---

## 🔗 Benchmarks Sugeridos

| Benchmark | Símbolo yfinance | Descripción |
|-----------|------------------|-------------|
| IBEX 35 | `^IBEX` | Índice español |
| S&P 500 | `^GSPC` | Índice USA |
| Euro Stoxx 50 | `^STOXX50E` | Índice Europa |
| MSCI World | `URTH` (ETF) | Índice mundial |
| NASDAQ 100 | `^NDX` | Tecnológicas USA |
| DAX | `^GDAXI` | Índice alemán |

---

## 📥 Fuentes de Datos

### Opción A: Descarga automática con yfinance
```python
import yfinance as yf

# Descargar datos del IBEX 35
ibex = yf.download('^IBEX', start='2024-01-01', end='2026-01-05')
# Columnas: Open, High, Low, Close, Volume
```

### Opción B: CSV manual
Descargar de:
- Yahoo Finance: https://finance.yahoo.com
- Investing.com: https://www.investing.com

Formato esperado:
```csv
Date,Close
2024-01-02,10234.50
2024-01-03,10301.20
...
```

---

## 🔗 Integración con Módulos Existentes

| Módulo | Qué usamos | Qué aportamos |
|--------|------------|---------------|
| `database.py` | Modelo BenchmarkData, add/get_benchmark_data | - |
| `portfolio.py` | get_historical_value(), posiciones | Datos para comparar |

---

## 📝 Tests a crear: `test_benchmarks.py`

1. **Test carga CSV**: Importar datos desde archivo
2. **Test descarga yfinance**: Descargar datos (requiere internet)
3. **Test normalización**: Base 100 correcta
4. **Test comparación**: Portfolio vs benchmark
5. **Test rendimientos**: Cálculo correcto de returns
6. **Test volatilidad**: Cálculo correcto
7. **Test Sharpe ratio**: Cálculo correcto
8. **Test beta**: Correlación con benchmark
9. **Test comparación parcial**: Filtros funcionan
10. **Test exportación**: Genera Excel correctamente

---

## ⏱️ Orden de implementación

```
1. Clase base + gestión de datos benchmark     (~30 min)
2. Normalización base 100                       (~20 min)
3. compare_to_benchmark()                       (~40 min)
4. calculate_returns()                          (~20 min)
5. Estadísticas de riesgo (volatilidad, beta)  (~40 min)
6. Sharpe ratio, tracking error, drawdown      (~30 min)
7. Comparación parcial con filtros             (~20 min)
8. Exportación a Excel                         (~20 min)
9. Funciones print                             (~20 min)
10. Tests                                      (~30 min)
```

**Tiempo estimado total: ~4.5 horas**

---

## ❓ Preguntas antes de empezar

1. **¿Tienes yfinance instalado?**
   - Si no: `pip install yfinance`
   - Alternativa: cargar datos desde CSV manualmente

2. **¿Contra qué benchmarks quieres comparar principalmente?**
   - IBEX 35 (para acciones españolas)
   - S&P 500 (para USA)
   - MSCI World (para cartera global)

3. **¿Tienes conexión a internet estable para descargar datos?**
   - Si no, prepararé sistema solo con CSV

4. **¿Te interesa el cálculo de beta y Sharpe ratio?**
   - Son métricas más avanzadas
   - Requieren datos diarios durante al menos 1 año

5. **¿Quieres poder comparar subconjuntos de tu cartera?**
   - Ej: Solo acciones españolas vs IBEX
   - Ej: Solo fondos vs MSCI World

---

## 📎 Dependencias adicionales

```bash
# Para descarga automática de datos
pip install yfinance

# Ya instaladas (de sesiones anteriores)
# pandas, numpy, openpyxl, sqlalchemy
```

---

## 🗂️ Archivos CSV de ejemplo (si no hay internet)

Puedo crear un script que genere CSVs de ejemplo con datos simulados
para testing si no tienes acceso a yfinance.
