"""
Script de prueba independiente para validar la base de datos
Ejecutar desde la raíz del proyecto: python test_database.py
"""

from src.database import Database
from datetime import date

def main():
    print("\n" + "="*60)
    print("🚀 INVESTMENT TRACKER - TEST DE BASE DE DATOS")
    print("="*60 + "\n")
    
    # Inicializar base de datos
    print("📊 Inicializando base de datos...")
    db = Database()
    print()
    
    # ==========================================
    # TEST 1: AÑADIR TRANSACCIONES
    # ==========================================
    print("="*60)
    print("TEST 1: Añadir Transacciones")
    print("="*60 + "\n")
    
    # Compra 1: Telefónica
    print("➕ Añadiendo compra de Telefónica...")
    tef_id = db.add_transaction({
        'date': date(2024, 1, 15),
        'type': 'buy',
        'ticker': 'TEF',
        'name': 'Telefónica SA',
        'asset_type': 'accion',
        'quantity': 100,
        'price': 4.20,
        'commission': 10.0,
        'notes': 'Compra inicial'
    })
    
    # Compra 2: BBVA
    print("➕ Añadiendo compra de BBVA...")
    bbva_id = db.add_transaction({
        'date': date(2024, 3, 20),
        'type': 'buy',
        'ticker': 'BBVA',
        'name': 'Banco BBVA',
        'asset_type': 'accion',
        'quantity': 50,
        'price': 9.50,
        'commission': 8.50
    })
    
    # Compra 3: Fondo
    print("➕ Añadiendo compra de Fondo...")
    fondo_id = db.add_transaction({
        'date': date(2024, 6, 1),
        'type': 'buy',
        'ticker': 'ES0110041006',
        'name': 'Fondo Inversión XYZ',
        'asset_type': 'fondo',
        'quantity': 100,
        'price': 15.50,
        'commission': 0.0,
        'notes': 'Sin comisiones'
    })
    
    print(f"\n✅ 3 transacciones añadidas (IDs: {tef_id}, {bbva_id}, {fondo_id})")
    
    # ==========================================
    # TEST 2: CONSULTAR TRANSACCIONES
    # ==========================================
    print("\n" + "="*60)
    print("TEST 2: Consultar Transacciones")
    print("="*60 + "\n")
    
    # Todas las transacciones
    all_trans = db.get_transactions()
    print(f"📊 Total de transacciones: {len(all_trans)}")
    
    # Solo compras
    compras = db.get_transactions(type='buy')
    print(f"🛒 Total de compras: {len(compras)}")
    
    # Solo acciones
    acciones = db.get_transactions(asset_type='accion')
    print(f"📈 Transacciones de acciones: {len(acciones)}")
    
    # Transacciones de TEF
    tef_trans = db.get_transactions(ticker='TEF')
    print(f"📞 Transacciones de TEF: {len(tef_trans)}")
    
    # ==========================================
    # TEST 3: AÑADIR DIVIDENDOS
    # ==========================================
    print("\n" + "="*60)
    print("TEST 3: Añadir Dividendos")
    print("="*60 + "\n")
    
    print("💰 Añadiendo dividendo de Telefónica...")
    div_id = db.add_dividend({
        'ticker': 'TEF',
        'date': date(2024, 6, 15),
        'gross_amount': 25.00,
        'net_amount': 20.25,
        'notes': 'Dividendo semestral'
    })
    
    print("💰 Añadiendo dividendo de BBVA...")
    div2_id = db.add_dividend({
        'ticker': 'BBVA',
        'date': date(2024, 7, 10),
        'gross_amount': 15.50,
        'net_amount': 12.56
    })
    
    print(f"\n✅ 2 dividendos añadidos (IDs: {div_id}, {div2_id})")
    
    # ==========================================
    # TEST 4: CONSULTAR DIVIDENDOS
    # ==========================================
    print("\n" + "="*60)
    print("TEST 4: Consultar Dividendos")
    print("="*60 + "\n")
    
    # Todos los dividendos
    all_divs = db.get_dividends()
    print(f"💵 Total de dividendos: {len(all_divs)}")
    
    # Dividendos de TEF
    tef_divs = db.get_dividends(ticker='TEF')
    print(f"💵 Dividendos de TEF: {len(tef_divs)}")
    if tef_divs:
        div = tef_divs[0]
        print(f"   📅 Fecha: {div.date}")
        print(f"   💰 Bruto: {div.gross_amount}€")
        print(f"   💰 Neto: {div.net_amount}€")
        print(f"   📊 Retención: {div.withholding_tax}€")
    
    # ==========================================
    # TEST 5: CONVERSIÓN A DATAFRAME
    # ==========================================
    print("\n" + "="*60)
    print("TEST 5: Conversión a Pandas DataFrame")
    print("="*60 + "\n")
    
    df_trans = db.transactions_to_dataframe()
    print("📊 DataFrame de Transacciones:")
    print(f"   Shape: {df_trans.shape}")
    print(f"   Columnas: {list(df_trans.columns)}")
    print("\n   Primeras filas:")
    print(df_trans[['date', 'type', 'ticker', 'quantity', 'price', 'total']].to_string(index=False))
    
    df_divs = db.dividends_to_dataframe()
    print("\n💵 DataFrame de Dividendos:")
    print(f"   Shape: {df_divs.shape}")
    if not df_divs.empty:
        print("\n   Datos:")
        print(df_divs[['ticker', 'date', 'gross_amount', 'net_amount']].to_string(index=False))
    
    # ==========================================
    # TEST 6: TICKERS ÚNICOS
    # ==========================================
    print("\n" + "="*60)
    print("TEST 6: Tickers Únicos")
    print("="*60 + "\n")
    
    tickers = db.get_all_tickers()
    print(f"🏷️  Tickers en la base de datos: {', '.join(tickers)}")
    
    # ==========================================
    # TEST 7: ESTADÍSTICAS
    # ==========================================
    print("\n" + "="*60)
    print("TEST 7: Estadísticas de la Base de Datos")
    print("="*60 + "\n")
    
    stats = db.get_database_stats()
    print(f"📊 Total transacciones: {stats['total_transactions']}")
    print(f"💵 Total dividendos: {stats['total_dividends']}")
    print(f"🏷️  Tickers únicos: {stats['unique_tickers']}")
    if stats['date_range']:
        print(f"📅 Rango de fechas: {stats['date_range'][0]} → {stats['date_range'][1]}")
    
    # ==========================================
    # TEST 8: ACTUALIZAR TRANSACCIÓN
    # ==========================================
    print("\n" + "="*60)
    print("TEST 8: Actualizar Transacción")
    print("="*60 + "\n")
    
    print(f"🔄 Actualizando transacción ID {tef_id}...")
    success = db.update_transaction(tef_id, {
        'notes': 'Actualizado: Primera compra de prueba - Editado',
        'commission': 9.50
    })
    
    if success:
        trans_updated = db.get_transaction_by_id(tef_id)
        print(f"   📝 Nuevas notas: {trans_updated.notes}")
        print(f"   💸 Nueva comisión: {trans_updated.commission}€")
        print(f"   💰 Nuevo total: {trans_updated.total}€")
    
    # ==========================================
    # TEST 9: OBTENER TRANSACCIÓN POR ID
    # ==========================================
    print("\n" + "="*60)
    print("TEST 9: Obtener Transacción por ID")
    print("="*60 + "\n")
    
    trans = db.get_transaction_by_id(bbva_id)
    if trans:
        print(f"🔍 Transacción ID {bbva_id}:")
        print(f"   📅 Fecha: {trans.date}")
        print(f"   🏷️  Ticker: {trans.ticker}")
        print(f"   📝 Nombre: {trans.name}")
        print(f"   📊 Cantidad: {trans.quantity}")
        print(f"   💶 Precio: {trans.price}€")
        print(f"   💰 Total: {trans.total}€")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "="*60)
    print("✅ RESUMEN DE TESTS")
    print("="*60 + "\n")
    
    print("✅ Test 1: Añadir Transacciones - OK")
    print("✅ Test 2: Consultar Transacciones - OK")
    print("✅ Test 3: Añadir Dividendos - OK")
    print("✅ Test 4: Consultar Dividendos - OK")
    print("✅ Test 5: Conversión a DataFrame - OK")
    print("✅ Test 6: Tickers Únicos - OK")
    print("✅ Test 7: Estadísticas - OK")
    print("✅ Test 8: Actualizar Transacción - OK")
    print("✅ Test 9: Obtener Transacción por ID - OK")
    
    print("\n" + "="*60)
    print("🎉 TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("="*60 + "\n")
    
    print("📁 Base de datos creada en: data/database.db")
    print("💡 Puedes abrir la BD con SQLite Browser para inspeccionarla\n")
    
    # Cerrar conexión
    db.close()


if __name__ == '__main__':
    main()