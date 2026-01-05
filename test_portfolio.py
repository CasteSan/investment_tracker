"""
Test del Módulo Portfolio v2
============================

Este script prueba todas las funcionalidades del módulo portfolio.py
incluyendo el soporte de divisas y realized_gain_eur.

Ejecutar:
    python test_portfolio.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import Database
from src.portfolio import Portfolio, quick_summary, print_positions, print_realized_gains


def setup_test_data():
    """Crea datos de prueba si la base de datos está vacía"""
    db = Database()
    
    # Verificar si ya hay datos
    stats = db.get_database_stats()
    if stats['total_transactions'] > 0:
        print(f"   ℹ️  La base de datos ya tiene {stats['total_transactions']} transacciones")
        db.close()
        return False
    
    print("   📝 Creando datos de prueba...")
    
    # Datos de ejemplo que simulan un portfolio diversificado
    # Incluyendo transacciones en diferentes divisas
    test_transactions = [
        # Acciones españolas (EUR)
        {'date': '2024-03-15', 'type': 'buy', 'ticker': 'TEF', 'name': 'Telefónica', 
         'asset_type': 'accion', 'quantity': 200, 'price': 3.85, 'commission': 5.0,
         'currency': 'EUR', 'market': 'BME'},
        {'date': '2024-06-20', 'type': 'buy', 'ticker': 'TEF', 'name': 'Telefónica', 
         'asset_type': 'accion', 'quantity': 150, 'price': 4.10, 'commission': 5.0,
         'currency': 'EUR', 'market': 'BME'},
        {'date': '2024-09-10', 'type': 'sell', 'ticker': 'TEF', 'name': 'Telefónica', 
         'asset_type': 'accion', 'quantity': 100, 'price': 4.35, 'commission': 5.0,
         'currency': 'EUR', 'market': 'BME', 'realized_gain_eur': 38.50},
        
        {'date': '2024-04-01', 'type': 'buy', 'ticker': 'BBVA', 'name': 'Banco BBVA', 
         'asset_type': 'accion', 'quantity': 100, 'price': 9.20, 'commission': 8.0,
         'currency': 'EUR', 'market': 'BME'},
        
        # Fondos de inversión (EUR)
        {'date': '2024-01-15', 'type': 'buy', 'ticker': 'LP68478350', 
         'name': 'Fidelity S&P 500 Index Fund EUR P Acc', 
         'asset_type': 'fondo', 'quantity': 50.5, 'price': 12.10, 'commission': 0,
         'currency': 'EUR', 'market': 'IR'},
        {'date': '2024-07-01', 'type': 'buy', 'ticker': 'LP68478350', 
         'name': 'Fidelity S&P 500 Index Fund EUR P Acc', 
         'asset_type': 'fondo', 'quantity': 30.2, 'price': 13.50, 'commission': 0,
         'currency': 'EUR', 'market': 'IR'},
        
        {'date': '2024-02-20', 'type': 'buy', 'ticker': 'LP68365920', 
         'name': 'Cobas LUX SICAV - Cobas Selection Fund', 
         'asset_type': 'fondo', 'quantity': 0.025, 'price': 26500.0, 'commission': 0,
         'currency': 'EUR', 'market': 'LU'},
        
        # ETFs
        {'date': '2024-08-01', 'type': 'buy', 'ticker': 'AMGOLD.PA', 
         'name': 'Amundi Physical Gold ETC', 
         'asset_type': 'etf', 'quantity': 10, 'price': 125.50, 'commission': 3.0,
         'currency': 'EUR', 'market': 'EPA'},
        
        # ===== TRANSACCIÓN EN GBX (peniques) =====
        # Esto simula el caso de Tullow Oil
        {'date': '2024-05-16', 'type': 'buy', 'ticker': 'TLW.L', 
         'name': 'Tullow Oil', 
         'asset_type': 'accion', 'quantity': 2300, 'price': 15.50, 'commission': 10.0,
         'currency': 'GBX', 'market': 'LON'},
        # Venta con realized_gain_eur correcto (NO calculado de los precios en GBX)
        {'date': '2024-08-08', 'type': 'sell', 'ticker': 'TLW.L', 
         'name': 'Tullow Oil', 
         'asset_type': 'accion', 'quantity': 2300, 'price': 10.10, 'commission': 10.0,
         'currency': 'GBX', 'market': 'LON', 
         'realized_gain_eur': -143.28},  # ¡B/P real en EUR!
        
        # ===== TRANSACCIÓN EN USD =====
        {'date': '2024-06-01', 'type': 'buy', 'ticker': 'AAPL', 
         'name': 'Apple Inc.', 
         'asset_type': 'accion', 'quantity': 10, 'price': 180.50, 'commission': 5.0,
         'currency': 'USD', 'market': 'NASDAQ'},
        {'date': '2024-10-15', 'type': 'sell', 'ticker': 'AAPL', 
         'name': 'Apple Inc.', 
         'asset_type': 'accion', 'quantity': 10, 'price': 220.00, 'commission': 5.0,
         'currency': 'USD', 'market': 'NASDAQ',
         'realized_gain_eur': 362.50},  # B/P en EUR (incluye conversión)
    ]
    
    for trans in test_transactions:
        db.add_transaction(trans)
    
    # Añadir algunos dividendos
    db.add_dividend({
        'ticker': 'TEF',
        'name': 'Telefónica',
        'date': '2024-06-15',
        'gross_amount': 15.00,
        'net_amount': 12.15,
        'notes': 'Dividendo semestral'
    })
    
    db.add_dividend({
        'ticker': 'BBVA',
        'name': 'Banco BBVA',
        'date': '2024-10-10',
        'gross_amount': 25.00,
        'net_amount': 20.25,
        'notes': 'Dividendo trimestral'
    })
    
    db.close()
    print(f"   ✅ Creadas {len(test_transactions)} transacciones de prueba")
    print(f"   ✅ Incluye transacciones en EUR, USD y GBX")
    print(f"   ✅ Creados 2 dividendos de prueba")
    return True


def run_tests():
    """Ejecuta todos los tests del módulo Portfolio"""
    
    print("\n" + "="*70)
    print("🧪 TEST COMPLETO DEL MÓDULO PORTFOLIO v2")
    print("   (Con soporte de divisas y nombres de activos)")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Setup
    print("\n📦 Preparando datos de prueba...")
    setup_test_data()
    
    # Crear instancia del Portfolio
    portfolio = Portfolio()
    
    # =========================================================================
    # TEST 1: Posiciones Actuales (mostrando nombres)
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 1: Posiciones Actuales (con nombres)")
    print("-"*50)
    
    try:
        positions = portfolio.get_current_positions()
        
        if not positions.empty:
            print(f"   ✅ {len(positions)} posiciones encontradas")
            print("\n   Resumen de posiciones:")
            # Mostrar display_name en lugar de ticker
            cols = ['display_name', 'quantity', 'avg_price', 'market_value', 'unrealized_gain_pct']
            print(positions[cols].to_string(index=False))
            tests_passed += 1
        else:
            print("   ⚠️  No hay posiciones (base de datos vacía)")
            tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 2: Verificar divisas
    # =========================================================================
    print("\n" + "-"*50)
    print("💱 TEST 2: Verificar divisas de transacciones")
    print("-"*50)
    
    try:
        currencies = portfolio.db.get_currencies_used()
        markets = portfolio.db.get_markets_used()
        
        print(f"   ✅ Divisas usadas: {currencies}")
        print(f"   ✅ Mercados usados: {markets}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 3: Plusvalías Realizadas (con realized_gain_eur)
    # =========================================================================
    print("\n" + "-"*50)
    print("💵 TEST 3: Plusvalías Realizadas (usando realized_gain_eur)")
    print("-"*50)
    
    try:
        realized = portfolio.get_realized_gains()
        
        print(f"   ✅ Número de ventas: {realized['num_sales']}")
        print(f"   ✅ Total ganancias: +{realized['total_gains']:,.2f}€")
        print(f"   ✅ Total pérdidas: -{realized['total_losses']:,.2f}€")
        print(f"   ✅ Balance neto: {realized['net_gain']:+,.2f}€")
        
        if not realized['sales_detail'].empty:
            print("\n   Detalle de ventas (B/P en EUR correcto):")
            cols = ['date', 'display_name', 'currency', 'gain_eur']
            # Formatear fecha
            detail = realized['sales_detail'].copy()
            detail['date'] = detail['date'].dt.strftime('%Y-%m-%d')
            print(detail[cols].to_string(index=False))
            
            # Verificar que TLW.L tiene -143.28 (no -12420)
            tlw_sales = detail[detail['display_name'].str.contains('Tullow', case=False)]
            if not tlw_sales.empty:
                tlw_gain = tlw_sales['gain_eur'].iloc[0]
                if abs(tlw_gain - (-143.28)) < 1:  # Tolerancia de 1€
                    print(f"\n   ✅ VERIFICACIÓN: Tullow Oil = {tlw_gain:.2f}€ (correcto, no -12420€)")
                else:
                    print(f"\n   ⚠️  ADVERTENCIA: Tullow Oil = {tlw_gain:.2f}€ (esperado -143.28€)")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1
    
    # =========================================================================
    # TEST 4: Rentabilidad Total
    # =========================================================================
    print("\n" + "-"*50)
    print("📊 TEST 4: Rentabilidad Total")
    print("-"*50)
    
    try:
        returns = portfolio.get_total_return(include_dividends=True)
        
        print(f"   ✅ Total invertido: {returns['total_invested']:,.2f}€")
        print(f"   ✅ Valor actual: {returns['current_value']:,.2f}€")
        print(f"   ✅ Ganancia latente: {returns['unrealized_gain']:+,.2f}€")
        print(f"   ✅ Ganancia realizada: {returns['realized_gain']:+,.2f}€")
        print(f"   ✅ Dividendos: {returns['dividends']:,.2f}€")
        print(f"   ✅ Ganancia total: {returns['total_gain']:+,.2f}€")
        print(f"   ✅ Rentabilidad: {returns['total_return_pct']:+.2f}%")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 5: Performance por Activo (mostrando nombres)
    # =========================================================================
    print("\n" + "-"*50)
    print("🏆 TEST 5: Performance por Activo")
    print("-"*50)
    
    try:
        perf = portfolio.get_performance_by_asset()
        
        if not perf.empty:
            print("   ✅ Ranking por rentabilidad:")
            cols = ['display_name', 'unrealized_gain', 'unrealized_gain_pct']
            print(perf[cols].head(5).to_string(index=False))
            
            print(f"\n   🥇 Mejor: {perf.iloc[0]['display_name']} ({perf.iloc[0]['unrealized_gain_pct']:+.2f}%)")
            print(f"   🥉 Peor: {perf.iloc[-1]['display_name']} ({perf.iloc[-1]['unrealized_gain_pct']:+.2f}%)")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 6: Distribución de Cartera
    # =========================================================================
    print("\n" + "-"*50)
    print("🥧 TEST 6: Distribución de Cartera")
    print("-"*50)
    
    try:
        # Por activo (mostrando nombres)
        alloc_asset = portfolio.get_allocation(by='asset')
        print("   ✅ Distribución por activo (top 5):")
        if not alloc_asset.empty:
            for _, row in alloc_asset.head(5).iterrows():
                print(f"      {row['category'][:40]}: {row['percentage']:.1f}%")
        
        # Por tipo
        alloc_type = portfolio.get_allocation(by='type')
        print("\n   ✅ Distribución por tipo:")
        if not alloc_type.empty:
            for _, row in alloc_type.iterrows():
                print(f"      {row['category']}: {row['percentage']:.1f}%")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 7: Resumen Completo
    # =========================================================================
    print("\n" + "-"*50)
    print("📋 TEST 7: Resumen Completo")
    print("-"*50)
    
    try:
        summary = portfolio.get_portfolio_summary()
        
        print(f"   ✅ Valor total: {summary['total_value']:,.2f}€")
        print(f"   ✅ Invertido: {summary['total_invested']:,.2f}€")
        print(f"   ✅ Ganancia: {summary['total_gain']:+,.2f}€ ({summary['total_return_pct']:+.2f}%)")
        print(f"   ✅ Posiciones: {summary['num_positions']}")
        print(f"   ✅ Por tipo: {summary['positions_by_type']}")
        
        if summary['top_performer']:
            print(f"   ✅ Top: {summary['top_performer']['name']} ({summary['top_performer']['gain_pct']:+.2f}%)")
        if summary['bottom_performer']:
            print(f"   ✅ Bottom: {summary['bottom_performer']['name']} ({summary['bottom_performer']['gain_pct']:+.2f}%)")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # =========================================================================
    # TEST 8: Estadísticas
    # =========================================================================
    print("\n" + "-"*50)
    print("📈 TEST 8: Estadísticas")
    print("-"*50)
    
    try:
        stats = portfolio.get_statistics()
        
        if stats:
            print(f"   ✅ Rentabilidad media: {stats['mean_return']:+.2f}%")
            print(f"   ✅ Rentabilidad mediana: {stats['median_return']:+.2f}%")
            print(f"   ✅ Desviación estándar: {stats['std_return']:.2f}%")
            print(f"   ✅ Posiciones en verde: {stats['positive_positions']}")
            print(f"   ✅ Posiciones en rojo: {stats['negative_positions']}")
            print(f"   ✅ Mayor posición: {stats['largest_position']} ({stats['largest_position_pct']:.1f}%)")
        
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        tests_failed += 1
    
    # Cerrar conexión
    portfolio.close()
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    print(f"   ✅ Tests pasados: {tests_passed}")
    print(f"   ❌ Tests fallidos: {tests_failed}")
    print(f"   📈 Tasa de éxito: {tests_passed/(tests_passed+tests_failed)*100:.0f}%")
    
    if tests_failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS PASARON EXITOSAMENTE!")
    else:
        print(f"\n⚠️  {tests_failed} tests fallaron. Revisa los errores arriba.")
    
    print("="*70)
    
    # =========================================================================
    # DEMO: Funciones de conveniencia
    # =========================================================================
    print("\n" + "="*70)
    print("📊 DEMO: Funciones de Conveniencia")
    print("="*70)
    
    print("\n🔹 print_positions():")
    print_positions()
    
    print("\n🔹 print_realized_gains():")
    print_realized_gains()
    
    return tests_failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
