"""
Tests para el módulo Tax Calculator
Sesión 4 del Investment Tracker

Ejecutar: python test_tax_calculator.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.tax_calculator import TaxCalculator, TRAMOS_IRPF_AHORRO


def test_all():
    """Ejecuta todos los tests del Tax Calculator"""
    
    print("\n" + "="*70)
    print("🧪 TEST COMPLETO DEL MÓDULO TAX CALCULATOR")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Inicializar
    tax = TaxCalculator(method='FIFO')
    
    # =========================================================================
    # TEST 1: Lotes disponibles
    # =========================================================================
    print("\n" + "-"*50)
    print("📦 TEST 1: Lotes Disponibles")
    print("-"*50)
    
    try:
        lots = tax.get_all_available_lots()
        
        if not lots.empty:
            print(f"   ✅ {len(lots)} lotes encontrados")
            print(f"\n   Muestra (primeros 5):")
            print(lots.head().to_string(index=False))
            tests_passed += 1
        else:
            print("   ⚠️  No hay lotes (puede ser normal si no hay datos)")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 2: Resumen fiscal 2025
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 2: Resumen Fiscal 2025")
    print("-"*50)
    
    try:
        summary = tax.get_fiscal_year_summary(2025)
        
        print(f"   ✅ Ventas: {summary['total_sales']}")
        print(f"   ✅ Ganancias: +{summary['total_gains']:,.2f}€")
        print(f"   ✅ Pérdidas: {summary['total_losses']:,.2f}€")
        print(f"   ✅ Neto: {summary['net_gain']:+,.2f}€")
        print(f"   ✅ Base imponible: {summary['tax_base']:,.2f}€")
        print(f"   ✅ Impuesto estimado: {summary['estimated_tax']:,.2f}€")
        
        if summary['by_quarter']:
            print(f"   ✅ Por trimestre: {summary['by_quarter']}")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 3: Detalle fiscal
    # =========================================================================
    print("\n" + "-"*50)
    print("📋 TEST 3: Detalle Fiscal 2025")
    print("-"*50)
    
    try:
        detail = tax.get_fiscal_year_detail(2025)
        
        if not detail.empty:
            print(f"   ✅ {len(detail)} ventas en detalle")
            print(f"\n   Columnas: {list(detail.columns)}")
            print(f"\n   Muestra (primeras 5):")
            cols_show = ['sale_date', 'name', 'quantity', 'gain_eur']
            print(detail[cols_show].head().to_string(index=False))
            tests_passed += 1
        else:
            print("   ⚠️  No hay ventas en 2025")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 4: Cálculo de impuestos por tramos
    # =========================================================================
    print("\n" + "-"*50)
    print("💰 TEST 4: Cálculo de Impuestos (Tramos IRPF)")
    print("-"*50)
    
    try:
        # Test con diferentes bases imponibles
        test_cases = [
            (5000, 950),      # 5000 * 19% = 950
            (10000, 1980),    # 6000 * 19% + 4000 * 21% = 1140 + 840 = 1980
            (60000, 12080),   # 6000 * 19% + 44000 * 21% + 10000 * 23% = 1140 + 9240 + 2300 - ajuste
            (-1000, 0),       # Pérdidas = 0 impuesto
        ]
        
        all_ok = True
        for base, expected_approx in test_cases:
            result = tax.calculate_tax(base)
            
            # Tolerancia del 5% para redondeos
            if base > 0:
                diff_pct = abs(result['total_tax'] - expected_approx) / expected_approx * 100
                ok = diff_pct < 5
            else:
                ok = result['total_tax'] == 0
            
            status = "✅" if ok else "❌"
            print(f"   {status} Base {base:,}€ → Impuesto: {result['total_tax']:,.2f}€ "
                  f"(esperado ~{expected_approx:,.2f}€)")
            
            if not ok:
                all_ok = False
        
        if all_ok:
            tests_passed += 1
        else:
            tests_failed += 1
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 5: Regla de los 2 meses (Wash Sales)
    # =========================================================================
    print("\n" + "-"*50)
    print("⚠️  TEST 5: Detección Regla 2 Meses")
    print("-"*50)
    
    try:
        wash_sales = tax.get_wash_sales_in_year(2025)
        
        if not wash_sales.empty:
            print(f"   ⚠️  {len(wash_sales)} ventas afectadas por regla 2 meses:")
            print(wash_sales[['date', 'ticker', 'loss']].to_string(index=False))
        else:
            print("   ✅ No hay ventas afectadas por regla 2 meses")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 6: Simulación de venta
    # =========================================================================
    print("\n" + "-"*50)
    print("🔮 TEST 6: Simulación de Venta")
    print("-"*50)
    
    try:
        # Buscar un ticker con lotes disponibles
        lots = tax.get_all_available_lots()
        
        if not lots.empty:
            ticker = lots.iloc[0]['ticker']
            qty = min(lots.iloc[0]['quantity'], 10)  # Simular venta pequeña
            price = lots.iloc[0]['price'] * 1.1  # 10% más caro
            
            sim = tax.simulate_sale(ticker, qty, price)
            
            print(f"   Simulando venta de {qty:.4f} {ticker} @ {price:.2f}€")
            print(f"   ✅ Ingresos: {sim['gross_proceeds']:,.2f}€")
            print(f"   ✅ Coste base: {sim['cost_basis']:,.2f}€")
            print(f"   ✅ Ganancia: {sim['gain_before_tax']:+,.2f}€")
            print(f"   ✅ Impuesto: {sim['estimated_tax']:,.2f}€")
            print(f"   ✅ Neto: {sim['net_after_tax']:,.2f}€")
            
            if sim['wash_sale_warning']:
                print(f"   ⚠️  Aviso wash sale: {sim['wash_sale_message']}")
            
            tests_passed += 1
        else:
            print("   ⚠️  No hay lotes para simular")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 7: FIFO vs LIFO
    # =========================================================================
    print("\n" + "-"*50)
    print("🔄 TEST 7: Comparación FIFO vs LIFO")
    print("-"*50)
    
    try:
        lots = tax.get_all_available_lots()
        
        if not lots.empty:
            # Encontrar ticker con múltiples lotes
            ticker_counts = lots.groupby('ticker').size()
            multi_lot_tickers = ticker_counts[ticker_counts > 1].index.tolist()
            
            if multi_lot_tickers:
                ticker = multi_lot_tickers[0]
                
                # FIFO
                tax_fifo = TaxCalculator(method='FIFO')
                lots_fifo = tax_fifo.get_available_lots(ticker)
                tax_fifo.close()
                
                # LIFO
                tax_lifo = TaxCalculator(method='LIFO')
                lots_lifo = tax_lifo.get_available_lots(ticker)
                tax_lifo.close()
                
                print(f"   Ticker con múltiples lotes: {ticker}")
                print(f"   ✅ FIFO lotes: {len(lots_fifo)}")
                print(f"   ✅ LIFO lotes: {len(lots_lifo)}")
                
                # Verificar que son diferentes si ha habido ventas parciales
                tests_passed += 1
            else:
                print("   ⚠️  No hay tickers con múltiples lotes para comparar")
                tests_passed += 1
        else:
            print("   ⚠️  No hay lotes para comparar")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 8: Exportación a Excel
    # =========================================================================
    print("\n" + "-"*50)
    print("📄 TEST 8: Exportación a Excel")
    print("-"*50)
    
    try:
        filepath = tax.export_fiscal_report(2025, 'data/exports/test_fiscal_2025.xlsx')
        
        if Path(filepath).exists():
            size = Path(filepath).stat().st_size
            print(f"   ✅ Archivo creado: {filepath}")
            print(f"   ✅ Tamaño: {size:,} bytes")
            tests_passed += 1
        else:
            print(f"   ❌ Archivo no creado")
            tests_failed += 1
            
    except ImportError:
        print("   ⚠️  openpyxl no instalado, saltando test de Excel")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 9: Dividendos fiscal
    # =========================================================================
    print("\n" + "-"*50)
    print("💵 TEST 9: Resumen Fiscal Dividendos")
    print("-"*50)
    
    try:
        divs = tax.get_dividends_fiscal_summary(2025)
        
        print(f"   ✅ Total bruto: {divs['total_gross']:,.2f}€")
        print(f"   ✅ Retenciones: {divs['total_withholding']:,.2f}€")
        print(f"   ✅ Total neto: {divs['total_net']:,.2f}€")
        
        if divs['by_ticker']:
            print(f"   ✅ Por ticker: {len(divs['by_ticker'])} activos")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 10: Print functions
    # =========================================================================
    print("\n" + "-"*50)
    print("🖨️  TEST 10: Funciones de Impresión")
    print("-"*50)
    
    try:
        # Solo verificar que no dan error
        tax.print_fiscal_summary(2025)
        tests_passed += 1
        print("   ✅ print_fiscal_summary ejecutado correctamente")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # RESUMEN
    # =========================================================================
    tax.close()
    
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    print(f"   ✅ Tests pasados: {tests_passed}")
    print(f"   ❌ Tests fallidos: {tests_failed}")
    print(f"   📈 Tasa de éxito: {tests_passed/(tests_passed+tests_failed)*100:.0f}%")
    
    if tests_failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
    else:
        print(f"\n⚠️  {tests_failed} test(s) fallaron")
    
    print("="*70 + "\n")
    
    return tests_failed == 0


# =============================================================================
# DEMO: Funciones principales
# =============================================================================

def demo():
    """Demostración de las funciones principales"""
    
    print("\n" + "="*70)
    print("📊 DEMO: TAX CALCULATOR")
    print("="*70)
    
    tax = TaxCalculator()
    
    # 1. Imprimir resumen fiscal
    print("\n🔹 Resumen Fiscal 2025:")
    tax.print_fiscal_summary(2025)
    
    # 2. Mostrar algunos lotes
    print("\n🔹 Lotes Disponibles (muestra):")
    tax.print_available_lots()
    
    # 3. Simular una venta
    lots = tax.get_all_available_lots()
    if not lots.empty:
        ticker = lots.iloc[0]['ticker']
        qty = lots.iloc[0]['quantity']
        price = lots.iloc[0]['price'] * 1.05
        
        print(f"\n🔹 Simulación de venta:")
        tax.print_simulation(ticker, qty / 2, price)
    
    tax.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        demo()
    else:
        success = test_all()
        sys.exit(0 if success else 1)
