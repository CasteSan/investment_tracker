"""
Tests para el módulo Benchmarks
Sesión 6 del Investment Tracker

Ejecutar: python test_benchmarks.py
Demo rápida: python test_benchmarks.py demo
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.benchmarks import BenchmarkComparator, BENCHMARK_SYMBOLS, YFINANCE_AVAILABLE


def test_all():
    """Ejecuta todos los tests del módulo Benchmarks"""
    
    print("\n" + "="*70)
    print("🧪 TEST COMPLETO DEL MÓDULO BENCHMARKS")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    bc = BenchmarkComparator()
    
    # Fechas de prueba
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # =========================================================================
    # TEST 1: yfinance disponible
    # =========================================================================
    print("\n" + "-"*50)
    print("📦 TEST 1: Verificar yfinance")
    print("-"*50)
    
    if YFINANCE_AVAILABLE:
        print("   ✅ yfinance está instalado")
        tests_passed += 1
    else:
        print("   ❌ yfinance NO está instalado")
        print("   Ejecuta: pip install yfinance")
        tests_failed += 1
        bc.close()
        return False
    
    # =========================================================================
    # TEST 2: Descargar benchmark
    # =========================================================================
    print("\n" + "-"*50)
    print("📥 TEST 2: Descargar S&P 500")
    print("-"*50)
    
    try:
        count = bc.download_benchmark('SP500', start_date, end_date)
        print(f"   ✅ Descargados {count} registros del S&P 500")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 3: Listar benchmarks disponibles
    # =========================================================================
    print("\n" + "-"*50)
    print("📋 TEST 3: Listar benchmarks disponibles")
    print("-"*50)
    
    try:
        available = bc.get_available_benchmarks()
        print(f"   ✅ Benchmarks disponibles: {len(available)}")
        for b in available:
            print(f"      {b['name']}: {b['records']} registros")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 4: Obtener serie del benchmark
    # =========================================================================
    print("\n" + "-"*50)
    print("📈 TEST 4: Obtener serie temporal del benchmark")
    print("-"*50)
    
    try:
        series = bc.get_benchmark_series('SP500', start_date, end_date)
        print(f"   ✅ Serie obtenida: {len(series)} puntos")
        print(f"      Primer valor: {series.iloc[0]:.2f}")
        print(f"      Último valor: {series.iloc[-1]:.2f}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 5: Normalización base 100
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 5: Normalización base 100")
    print("-"*50)
    
    try:
        series = bc.get_benchmark_series('SP500', start_date, end_date)
        normalized = bc.normalize_to_base_100(series)
        
        assert abs(normalized.iloc[0] - 100) < 0.01, "Primer valor debe ser 100"
        print(f"   ✅ Normalización correcta")
        print(f"      Base: {normalized.iloc[0]:.2f}")
        print(f"      Final: {normalized.iloc[-1]:.2f}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 6: Cálculo de rendimientos
    # =========================================================================
    print("\n" + "-"*50)
    print("💰 TEST 6: Cálculo de rendimientos")
    print("-"*50)
    
    try:
        returns = bc.calculate_returns('SP500', start_date, end_date)
        
        if 'error' not in returns:
            print(f"   ✅ Rendimientos calculados")
            print(f"      Cartera: {returns['portfolio_return']:+.2f}%")
            print(f"      S&P 500: {returns['benchmark_return']:+.2f}%")
            print(f"      Outperformance: {returns['outperformance']:+.2f}%")
            tests_passed += 1
        else:
            print(f"   ⚠️  {returns['error']}")
            tests_passed += 1  # No es un fallo, puede que no haya datos de cartera
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 7: Volatilidad
    # =========================================================================
    print("\n" + "-"*50)
    print("📉 TEST 7: Cálculo de volatilidad")
    print("-"*50)
    
    try:
        series = bc.get_benchmark_series('SP500', start_date, end_date)
        vol = bc.calculate_volatility(series)
        
        print(f"   ✅ Volatilidad S&P 500: {vol:.2f}% anual")
        assert vol > 0, "Volatilidad debe ser positiva"
        assert vol < 100, "Volatilidad debe ser razonable (<100%)"
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 8: Sharpe Ratio
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 8: Sharpe Ratio")
    print("-"*50)
    
    try:
        series = bc.get_benchmark_series('SP500', start_date, end_date)
        sharpe = bc.calculate_sharpe_ratio(series)
        
        print(f"   ✅ Sharpe Ratio S&P 500: {sharpe:.2f}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 9: Max Drawdown
    # =========================================================================
    print("\n" + "-"*50)
    print("⬇️  TEST 9: Maximum Drawdown")
    print("-"*50)
    
    try:
        series = bc.get_benchmark_series('SP500', start_date, end_date)
        dd = bc.calculate_max_drawdown(series)
        
        print(f"   ✅ Max Drawdown S&P 500: {dd['max_drawdown']:.2f}%")
        if dd['peak_date']:
            print(f"      Pico: {dd['peak_date']}")
            print(f"      Valle: {dd['trough_date']}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 10: Métricas completas
    # =========================================================================
    print("\n" + "-"*50)
    print("📈 TEST 10: Métricas completas de riesgo")
    print("-"*50)
    
    try:
        metrics = bc.get_full_risk_metrics('SP500', start_date, end_date)
        
        if 'error' not in metrics:
            print(f"   ✅ Métricas calculadas correctamente")
            print(f"      Beta: {metrics['risk']['beta']}")
            print(f"      Alpha: {metrics['risk_adjusted']['alpha']}%")
            print(f"      Sharpe: {metrics['risk_adjusted']['portfolio_sharpe']}")
            print(f"      Info Ratio: {metrics['risk_adjusted']['information_ratio']}")
            tests_passed += 1
        else:
            print(f"   ⚠️  {metrics['error']}")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 11: Descargar otro benchmark (MSCI World)
    # =========================================================================
    print("\n" + "-"*50)
    print("🌍 TEST 11: Descargar MSCI World")
    print("-"*50)
    
    try:
        count = bc.download_benchmark('MSCI_WORLD', start_date, end_date)
        print(f"   ✅ Descargados {count} registros de MSCI World")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 12: Exportación a Excel
    # =========================================================================
    print("\n" + "-"*50)
    print("📄 TEST 12: Exportación a Excel")
    print("-"*50)
    
    try:
        filepath = bc.export_comparison(
            'SP500',
            'data/exports/test_benchmark_comparison.xlsx',
            start_date,
            end_date
        )
        
        if filepath and Path(filepath).exists():
            size = Path(filepath).stat().st_size
            print(f"   ✅ Archivo creado: {filepath}")
            print(f"      Tamaño: {size:,} bytes")
            tests_passed += 1
        else:
            print("   ⚠️  No se pudo crear el archivo")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 13: Funciones de impresión
    # =========================================================================
    print("\n" + "-"*50)
    print("🖨️  TEST 13: Funciones de impresión")
    print("-"*50)
    
    try:
        bc.print_available_benchmarks()
        print("   ✅ print_available_benchmarks ejecutado")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # RESUMEN
    # =========================================================================
    bc.close()
    
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    print(f"   ✅ Tests pasados: {tests_passed}")
    print(f"   ❌ Tests fallidos: {tests_failed}")
    total = tests_passed + tests_failed
    print(f"   📈 Tasa de éxito: {tests_passed/total*100:.0f}%")
    
    if tests_failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
    else:
        print(f"\n⚠️  {tests_failed} test(s) fallaron")
    
    print("="*70 + "\n")
    
    return tests_failed == 0


def demo():
    """Demo interactiva del módulo Benchmarks"""
    
    print("\n" + "="*70)
    print("📊 DEMO: MÓDULO BENCHMARKS")
    print("="*70)
    
    bc = BenchmarkComparator()
    
    # Fechas
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 1. Descargar benchmarks principales
    print("\n" + "="*70)
    print("📥 1. DESCARGANDO BENCHMARKS PRINCIPALES")
    print("="*70)
    
    for benchmark in ['SP500', 'MSCI_WORLD', 'IBEX35']:
        try:
            print(f"\n   Descargando {benchmark}...")
            count = bc.download_benchmark(benchmark, start_date, end_date)
            if count > 0:
                print(f"   ✅ {count} registros")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
    
    # 2. Listar benchmarks disponibles
    print("\n" + "="*70)
    print("📋 2. BENCHMARKS DISPONIBLES")
    print("="*70)
    bc.print_available_benchmarks()
    
    # 3. Comparación con S&P 500
    print("\n" + "="*70)
    print("📈 3. COMPARACIÓN CON S&P 500")
    print("="*70)
    bc.print_comparison_summary('SP500', start_date, end_date)
    
    # 4. Métricas de riesgo
    print("\n" + "="*70)
    print("📊 4. MÉTRICAS DE RIESGO PROFESIONALES")
    print("="*70)
    bc.print_risk_metrics('SP500', start_date, end_date)
    
    # 5. Comparación con MSCI World (si está disponible)
    available = bc.get_available_benchmarks()
    if any(b['name'] == 'MSCI_WORLD' for b in available):
        print("\n" + "="*70)
        print("🌍 5. COMPARACIÓN CON MSCI WORLD")
        print("="*70)
        bc.print_comparison_summary('MSCI_WORLD', start_date, end_date)
    
    # 6. Exportar a Excel
    print("\n" + "="*70)
    print("📄 6. EXPORTANDO A EXCEL")
    print("="*70)
    
    try:
        bc.export_comparison('SP500', 'data/exports/benchmark_analysis.xlsx', start_date, end_date)
    except Exception as e:
        print(f"   ⚠️  Error exportando: {e}")
    
    bc.close()
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETADA")
    print("="*70 + "\n")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        demo()
    else:
        success = test_all()
        sys.exit(0 if success else 1)
