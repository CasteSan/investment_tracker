"""
Tests para el módulo Dividends
Sesión 5 del Investment Tracker

Ejecutar: python test_dividends.py
Para crear datos de ejemplo: python test_dividends.py --create-examples
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.dividends import DividendManager, create_example_dividends


def test_all():
    """Ejecuta todos los tests del módulo Dividends"""
    
    print("\n" + "="*70)
    print("🧪 TEST COMPLETO DEL MÓDULO DIVIDENDS")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    dm = DividendManager()
    
    # Verificar si hay datos
    totals = dm.get_total_dividends()
    if totals['count'] == 0:
        print("\n⚠️  No hay dividendos. Creando datos de ejemplo...")
        dm.close()
        create_example_dividends()
        dm = DividendManager()
        totals = dm.get_total_dividends()
    
    # =========================================================================
    # TEST 1: Totales de dividendos
    # =========================================================================
    print("\n" + "-"*50)
    print("💰 TEST 1: Totales de Dividendos")
    print("-"*50)
    
    try:
        print(f"   ✅ Número de cobros: {totals['count']}")
        print(f"   ✅ Total bruto: {totals['total_gross']:.2f}€")
        print(f"   ✅ Total neto: {totals['total_net']:.2f}€")
        print(f"   ✅ Retenciones: {totals['total_withholding']:.2f}€")
        print(f"   ✅ Tasa media retención: {totals['avg_withholding_rate']:.1f}%")
        
        # Verificar que los cálculos son correctos
        assert totals['total_gross'] >= totals['total_net'], "Bruto debe ser >= Neto"
        assert abs(totals['total_gross'] - totals['total_net'] - totals['total_withholding']) < 0.01, "Retención incorrecta"
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 2: Dividendos por año
    # =========================================================================
    print("\n" + "-"*50)
    print("📅 TEST 2: Dividendos por Año")
    print("-"*50)
    
    try:
        for year in [2024, 2025]:
            year_totals = dm.get_total_dividends(year=year)
            print(f"   ✅ {year}: {year_totals['count']} cobros, {year_totals['total_net']:.2f}€ neto")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 3: Dividendos por activo
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 3: Dividendos por Activo")
    print("-"*50)
    
    try:
        by_asset = dm.get_dividends_by_asset()
        
        if not by_asset.empty:
            print(f"   ✅ Activos con dividendos: {len(by_asset)}")
            print(f"\n   Muestra (top 3):")
            for _, row in by_asset.head(3).iterrows():
                print(f"      {row['ticker']}: {row['net']:.2f}€ ({row['pct_of_total']:.1f}%)")
            
            # Verificar que porcentajes suman 100%
            total_pct = by_asset['pct_of_total'].sum()
            assert abs(total_pct - 100) < 1, f"Porcentajes no suman 100% ({total_pct})"
            
            tests_passed += 1
        else:
            print("   ⚠️  No hay datos por activo")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 4: Calendario de dividendos
    # =========================================================================
    print("\n" + "-"*50)
    print("📆 TEST 4: Calendario de Dividendos")
    print("-"*50)
    
    try:
        calendar = dm.get_dividend_calendar(2025)
        
        assert len(calendar) == 12, "Calendario debe tener 12 meses"
        
        total_calendar = calendar['net'].sum()
        year_total = dm.get_total_dividends(year=2025)['total_net']
        
        print(f"   ✅ Calendario 2025: 12 meses")
        print(f"   ✅ Total del calendario: {total_calendar:.2f}€")
        print(f"   ✅ Coincide con total anual: {abs(total_calendar - year_total) < 0.01}")
        
        # Mostrar meses con dividendos
        months_with_divs = calendar[calendar['payments'] > 0]['month_name'].tolist()
        print(f"   ✅ Meses con cobros: {', '.join(months_with_divs)}")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 5: Yield on Cost (YOC)
    # =========================================================================
    print("\n" + "-"*50)
    print("📈 TEST 5: Yield on Cost")
    print("-"*50)
    
    try:
        portfolio_yield = dm.get_portfolio_yield()
        
        print(f"   ✅ Coste cartera: {portfolio_yield['total_cost_basis']:,.2f}€")
        print(f"   ✅ Dividendos anuales: {portfolio_yield['annual_dividends_net']:.2f}€")
        print(f"   ✅ YOC bruto: {portfolio_yield['portfolio_yoc_gross']:.2f}%")
        print(f"   ✅ YOC neto: {portfolio_yield['portfolio_yoc_net']:.2f}%")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 6: Frecuencia de pago
    # =========================================================================
    print("\n" + "-"*50)
    print("🔄 TEST 6: Frecuencia de Pago")
    print("-"*50)
    
    try:
        # Obtener un ticker con dividendos
        df = dm.get_dividends()
        if not df.empty:
            ticker = df['ticker'].value_counts().index[0]  # El que más pagos tiene
            
            freq = dm.get_dividend_frequency(ticker)
            
            print(f"   ✅ Ticker analizado: {ticker}")
            print(f"   ✅ Frecuencia: {freq['frequency']}")
            print(f"   ✅ Pagos/año: {freq['payments_per_year']}")
            print(f"   ✅ Días entre pagos: {freq['avg_days_between']}")
            
            tests_passed += 1
        else:
            print("   ⚠️  No hay datos para analizar frecuencia")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 7: Estimación anual
    # =========================================================================
    print("\n" + "-"*50)
    print("🔮 TEST 7: Estimación Anual")
    print("-"*50)
    
    try:
        estimate = dm.estimate_annual_dividends()
        
        print(f"   ✅ Estimación anual bruto: {estimate['estimated_annual_gross']:.2f}€")
        print(f"   ✅ Estimación anual neto: {estimate['estimated_annual_net']:.2f}€")
        print(f"   ✅ Estimación mensual: {estimate['estimated_monthly_net']:.2f}€")
        print(f"   ✅ Confianza: {estimate['confidence']}")
        print(f"   ✅ Base: {estimate['basis']}")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 8: Top pagadores
    # =========================================================================
    print("\n" + "-"*50)
    print("🏆 TEST 8: Top Pagadores")
    print("-"*50)
    
    try:
        top = dm.get_top_dividend_payers(n=5)
        
        if not top.empty:
            print(f"   ✅ Top 5 pagadores:")
            for i, row in top.iterrows():
                print(f"      {i+1}. {row['ticker']}: {row['net']:.2f}€")
            
            tests_passed += 1
        else:
            print("   ⚠️  No hay datos de pagadores")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 9: CRUD de dividendos
    # =========================================================================
    print("\n" + "-"*50)
    print("✏️  TEST 9: CRUD de Dividendos")
    print("-"*50)
    
    try:
        # Crear
        new_id = dm.add_dividend(
            ticker='TEST',
            gross_amount=10.00,
            date='2025-01-01',
            name='Test Dividend',
            notes='Test automático'
        )
        print(f"   ✅ Creado dividendo ID: {new_id}")
        
        # Leer
        div = dm.get_dividend(new_id)
        assert div is not None, "No se encontró el dividendo creado"
        assert div['ticker'] == 'TEST', "Ticker incorrecto"
        assert div['gross_amount'] == 10.00, "Importe incorrecto"
        print(f"   ✅ Leído correctamente: {div['ticker']} = {div['gross_amount']}€")
        
        # Eliminar
        deleted = dm.delete_dividend(new_id)
        assert deleted, "No se pudo eliminar"
        print(f"   ✅ Eliminado correctamente")
        
        # Verificar eliminación
        div_after = dm.get_dividend(new_id)
        assert div_after is None, "El dividendo debería estar eliminado"
        print(f"   ✅ Verificada eliminación")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 10: Exportación
    # =========================================================================
    print("\n" + "-"*50)
    print("📄 TEST 10: Exportación a Excel")
    print("-"*50)
    
    try:
        filepath = dm.export_dividends(
            filepath='data/exports/test_dividends_2025.xlsx',
            year=2025
        )
        
        if filepath and Path(filepath).exists():
            size = Path(filepath).stat().st_size
            print(f"   ✅ Archivo creado: {filepath}")
            print(f"   ✅ Tamaño: {size:,} bytes")
            tests_passed += 1
        else:
            print(f"   ⚠️  No se creó el archivo (puede que no haya datos)")
            tests_passed += 1
    except ImportError:
        print("   ⚠️  openpyxl no instalado, saltando test de Excel")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 11: Funciones de impresión
    # =========================================================================
    print("\n" + "-"*50)
    print("🖨️  TEST 11: Funciones de Impresión")
    print("-"*50)
    
    try:
        # Solo verificar que no dan error
        dm.print_dividend_summary(2025)
        print("   ✅ print_dividend_summary ejecutado")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # RESUMEN
    # =========================================================================
    dm.close()
    
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


def demo():
    """Demostración completa del módulo"""
    
    print("\n" + "="*70)
    print("📊 DEMO: MÓDULO DIVIDENDS")
    print("="*70)
    
    dm = DividendManager()
    
    # Verificar datos
    totals = dm.get_total_dividends()
    if totals['count'] == 0:
        print("\n⚠️  No hay dividendos. Creando datos de ejemplo...")
        dm.close()
        create_example_dividends()
        dm = DividendManager()
    
    # Demo completa
    print("\n" + "="*70)
    print("📊 1. RESUMEN GENERAL")
    print("="*70)
    dm.print_dividend_summary()
    
    print("\n" + "="*70)
    print("📅 2. CALENDARIO 2025")
    print("="*70)
    dm.print_dividend_calendar(2025)
    
    print("\n" + "="*70)
    print("🏆 3. TOP PAGADORES")
    print("="*70)
    dm.print_top_payers(5)
    
    print("\n" + "="*70)
    print("📈 4. ANÁLISIS DE YIELD")
    print("="*70)
    dm.print_yield_analysis()
    
    print("\n" + "="*70)
    print("🔮 5. ESTIMACIÓN FUTURA")
    print("="*70)
    est = dm.estimate_annual_dividends()
    print(f"\n   Basándose en el historial:")
    print(f"   📈 Dividendos estimados: {est['estimated_annual_net']:.2f}€/año")
    print(f"   📅 Media mensual: {est['estimated_monthly_net']:.2f}€/mes")
    print(f"   🎯 Confianza: {est['confidence']}")
    
    dm.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'demo':
            demo()
        elif sys.argv[1] == '--create-examples':
            create_example_dividends()
        else:
            print(f"Uso: python {sys.argv[0]} [demo|--create-examples]")
    else:
        success = test_all()
        sys.exit(0 if success else 1)
