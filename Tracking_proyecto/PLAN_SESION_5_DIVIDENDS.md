# =============================================================================
# SESIÓN 5: Dividends Module - Plan de Implementación
# =============================================================================

## 🎯 Objetivo

Crear un módulo completo para gestionar dividendos: registro, análisis, 
tracking de yield, calendario de cobros e integración fiscal.

---

## 📦 Archivo a crear: `src/dividends.py`

---

## 🔧 Funcionalidades a implementar

### 1️⃣ **Registro de Dividendos**
```python
class DividendManager:
    def __init__(self, db_path=None)
    
    def add_dividend(self, ticker, gross_amount, net_amount, date, 
                     currency='EUR', notes=None) -> int
        # Registra un dividendo, calcula retención automáticamente
        # Retorna: ID del dividendo creado
    
    def update_dividend(self, dividend_id, **kwargs) -> bool
        # Actualiza un dividendo existente
    
    def delete_dividend(self, dividend_id) -> bool
        # Elimina un dividendo
    
    def get_dividend(self, dividend_id) -> Dict
        # Obtiene un dividendo por ID
```

### 2️⃣ **Consultas y Filtros**
```python
    def get_dividends(self, ticker=None, year=None, 
                      start_date=None, end_date=None) -> List[Dict]
        # Lista dividendos con filtros
    
    def get_dividends_by_ticker(self, ticker) -> pd.DataFrame
        # Todos los dividendos de un activo
    
    def get_dividends_by_year(self, year) -> pd.DataFrame
        # Todos los dividendos de un año
    
    def get_dividend_history(self, ticker) -> pd.DataFrame
        # Historial completo de dividendos de un activo
```

### 3️⃣ **Análisis y Métricas**
```python
    def get_total_dividends(self, year=None) -> Dict
        # Total bruto, neto, retenciones
        # Por año o total histórico
    
    def get_dividends_by_asset(self, year=None) -> pd.DataFrame
        # Desglose por activo: bruto, neto, % del total
    
    def get_dividend_yield(self, ticker) -> Dict
        # Yield sobre precio medio de compra (YOC - Yield on Cost)
        # Yield sobre precio actual (si disponible)
    
    def get_portfolio_yield(self) -> Dict
        # Yield medio de toda la cartera
    
    def get_top_dividend_payers(self, n=10, year=None) -> pd.DataFrame
        # Activos que más dividendos generan
    
    def get_dividend_growth(self, ticker) -> Dict
        # Crecimiento de dividendos año a año
```

### 4️⃣ **Calendario y Proyecciones**
```python
    def get_dividend_calendar(self, year=None) -> pd.DataFrame
        # Calendario de dividendos cobrados por mes
    
    def get_monthly_income(self, year=None) -> pd.DataFrame
        # Ingresos por dividendos por mes
    
    def estimate_annual_dividends(self) -> Dict
        # Estimación de dividendos anuales basado en historial
        # Proyección para el año en curso
    
    def get_dividend_frequency(self, ticker) -> Dict
        # Frecuencia de pago: mensual, trimestral, semestral, anual
```

### 5️⃣ **Integración con Portfolio**
```python
    def get_total_return_with_dividends(self, ticker=None) -> Dict
        # Rentabilidad total = plusvalía + dividendos
        # Por activo o cartera completa
    
    def get_dividend_contribution(self) -> Dict
        # % de la rentabilidad total que viene de dividendos
```

### 6️⃣ **Integración Fiscal**
```python
    def get_fiscal_summary(self, year) -> Dict
        # Resumen fiscal de dividendos
        # Total bruto, retenciones, neto
        # Ya integrado con tax_calculator.get_dividends_fiscal_summary()
    
    def get_withholding_tax_detail(self, year) -> pd.DataFrame
        # Detalle de retenciones por dividendo
```

### 7️⃣ **Exportación y Reportes**
```python
    def export_dividends(self, filepath, year=None, format='excel') -> str
        # Exporta dividendos a Excel/CSV
    
    def generate_dividend_report(self, year) -> Dict
        # Informe completo de dividendos del año
```

### 8️⃣ **Funciones de Conveniencia (Print)**
```python
    def print_dividend_summary(self, year=None)
        # Imprime resumen formateado
    
    def print_dividend_calendar(self, year=None)
        # Imprime calendario mensual
    
    def print_top_payers(self, n=10)
        # Imprime top pagadores de dividendos
    
    def print_yield_analysis(self)
        # Imprime análisis de yield por activo
```

---

## 📊 Estructura del Output

### Resumen Anual
```
📊 DIVIDENDOS 2025
==================

💰 TOTALES
   Total bruto:      1,234.56€
   Retenciones:        234.57€ (19%)
   Total neto:         999.99€

📈 POR ACTIVO
   Ticker          Nombre                    Bruto    Neto    % Total
   --------------------------------------------------------------------------
   TEF             Telefónica               150.00€  121.50€   12.2%
   BBVA            Banco BBVA               200.00€  162.00€   16.2%
   ...

📅 POR MES
   Ene: 100€ | Feb: 0€ | Mar: 150€ | Abr: 0€ | May: 100€ | Jun: 200€
   Jul: 50€  | Ago: 0€ | Sep: 100€ | Oct: 0€ | Nov: 150€ | Dic: 150€

📊 YIELD
   Yield medio cartera (YOC): 3.75%
   Yield sobre valor actual:  3.21%
```

### Análisis de Yield
```
📈 ANÁLISIS DE YIELD POR ACTIVO
================================

   Ticker    Nombre              Coste    Divs/Año   YOC    Frec.
   ---------------------------------------------------------------------
   TEF       Telefónica          420€     30.00€    7.14%   Semestral
   BBVA      Banco BBVA          950€     40.00€    4.21%   Trimestral
   ...
   
   📊 Cartera total:
      Coste base:        33,000€
      Dividendos/año:     1,200€
      Yield on Cost:      3.64%
```

---

## 🔗 Integración con Módulos Existentes

| Módulo | Qué usamos | Qué aportamos |
|--------|------------|---------------|
| `database.py` | Modelo Dividend, CRUD | - |
| `portfolio.py` | Posiciones, cost_basis | `get_total_return_with_dividends()` |
| `tax_calculator.py` | `get_dividends_fiscal_summary()` | Datos de retenciones |

---

## 📝 Cambios en database.py (si necesarios)

El modelo Dividend ya existe pero podríamos añadir:
```python
class Dividend:
    # Campos existentes
    id, ticker, date, gross_amount, net_amount, withholding_tax, notes
    
    # Campos a añadir (si no existen)
    name            # Nombre del activo
    currency        # Divisa del dividendo (EUR, USD, etc.)
    ex_date         # Fecha ex-dividendo (opcional)
    payment_type    # 'ordinary', 'special', 'return_of_capital'
```

---

## 📋 Tests a crear: `test_dividends.py`

1. **Test registro**: Añadir, actualizar, eliminar dividendo
2. **Test consultas**: Filtros por ticker, año, rango de fechas
3. **Test totales**: Suma bruto, neto, retenciones
4. **Test por activo**: Desglose correcto por ticker
5. **Test yield**: Cálculo YOC correcto
6. **Test calendario**: Dividendos por mes
7. **Test proyección**: Estimación anual
8. **Test rentabilidad total**: Plusvalía + dividendos
9. **Test exportación**: Genera Excel correctamente
10. **Test print**: Funciones de impresión sin errores

---

## ⏱️ Orden de implementación

```
1. Clase base + métodos CRUD                    (~20 min)
2. Consultas y filtros                          (~20 min)
3. get_total_dividends, get_dividends_by_asset  (~20 min)
4. Cálculo de yield (YOC)                       (~30 min)
5. Calendario y proyecciones                    (~30 min)
6. Integración con portfolio (total return)     (~20 min)
7. Exportación a Excel                          (~20 min)
8. Funciones print                              (~20 min)
9. Tests                                        (~30 min)
```

**Tiempo estimado total: ~3.5 horas**

---

## ❓ Preguntas antes de empezar

1. **¿Tienes dividendos registrados actualmente?** 
   - Si no, ¿quieres que cree datos de ejemplo para testing?
   - O prefieres que te prepare un script para importar dividendos desde un CSV?

2. **¿Qué activos de tu cartera pagan dividendos?**
   - Acciones españolas (TEF, BBVA, SAN, IBE...)
   - Acciones USA
   - ETFs de distribución
   - Fondos (estos no suelen pagar dividendos)

3. **¿Te interesa el tracking de fechas ex-dividendo?**
   - Para saber cuándo tienes que tener las acciones para cobrar

4. **¿Quieres estimación de dividendos futuros?**
   - Basado en historial + anuncios de empresas
   - Requeriría datos externos o entrada manual

---

## 📎 Nota sobre datos

El CSV de Investing.com parece incluir dividendos en las transacciones. 
Podríamos:
- **Opción A**: Extraerlos del conversor actual (si tipo='dividend')
- **Opción B**: Crear importador específico para dividendos
- **Opción C**: Registro manual a través de la futura UI

¿Cuál prefieres?
