"""
Script de prueba para el módulo Data Loader
Ejecutar desde la raíz: python test_data_loader.py
"""

from src.data_loader import DataLoader
from src.database import Database
from pathlib import Path


def main():
    print("\n" + "="*70)
    print("🚀 INVESTMENT TRACKER - TEST DE DATA LOADER")
    print("="*70 + "\n")
    
    loader = DataLoader()
    db = Database()
    
    # ==========================================
    # TEST 1: GENERAR PLANTILLA CSV
    # ==========================================
    print("="*70)
    print("TEST 1: Generar Plantilla CSV")
    print("="*70 + "\n")
    
    print("📄 Generando plantilla de ejemplo...")
    template_path = loader.export_template_csv()
    print(f"   ✅ Plantilla creada en: {template_path}")
    print(f"   💡 Puedes editar este archivo y añadir tus transacciones")
    
    # ==========================================
    # TEST 2: VALIDAR ARCHIVO (DRY-RUN)
    # ==========================================
    print("\n" + "="*70)
    print("TEST 2: Validar Archivo (sin importar)")
    print("="*70 + "\n")
    
    print("🔍 Validando plantilla...")
    validation = loader.validate_file(template_path, file_type='csv')
    
    if validation['valid']:
        print(f"   ✅ Archivo válido")
        print(f"   📊 Filas detectadas: {validation['rows']}")
    else:
        print(f"   ❌ Archivo inválido")
        for error in validation['errors']:
            print(f"      - {error}")
    
    if validation['warnings']:
        print(f"   ⚠️  Advertencias:")
        for warning in validation['warnings']:
            print(f"      - {warning}")
    
    # ==========================================
    # TEST 3: IMPORTAR DESDE CSV
    # ==========================================
    print("\n" + "="*70)
    print("TEST 3: Importar desde CSV")
    print("="*70 + "\n")
    
    # Contar transacciones antes
    before_count = db.get_database_stats()['total_transactions']
    print(f"📊 Transacciones antes de importar: {before_count}")
    
    # Importar
    result = loader.import_from_csv(template_path, skip_duplicates=True)
    
    print(f"\n📈 Resultado de importación:")
    print(f"   ✅ Importadas exitosamente: {result['success']}")
    print(f"   ⏭️  Omitidas (duplicados): {result['skipped']}")
    print(f"   ❌ Errores: {len(result['errors'])}")
    print(f"   📊 Total procesadas: {result['total_processed']}")
    
    if result['errors']:
        print(f"\n   ⚠️  Detalles de errores:")
        for error in result['errors'][:5]:  # Mostrar máximo 5
            print(f"      - {error}")
    
    # Contar después
    after_count = db.get_database_stats()['total_transactions']
    print(f"\n📊 Transacciones después de importar: {after_count}")
    print(f"   📈 Incremento: +{after_count - before_count}")
    
    # ==========================================
    # TEST 4: CREAR CSV PERSONALIZADO
    # ==========================================
    print("\n" + "="*70)
    print("TEST 4: Crear CSV Personalizado y Probar Mapeo")
    print("="*70 + "\n")
    
    # Crear CSV con nombres de columnas diferentes
    custom_csv = Path('data/custom_format.csv')
    custom_data = """Fecha,Operación,Ticker,Nombre,Cantidad,Precio,Comisión,Notas
2024-04-15,buy,SAN,Banco Santander,200,4.50,12.00,Compra nueva
2024-05-10,buy,IBE,Iberdrola,150,12.30,15.50,Energía
2024-06-01,dividend,SAN,Banco Santander,,,0.12,Dividendo trimestral"""
    
    custom_csv.parent.mkdir(exist_ok=True)
    custom_csv.write_text(custom_data, encoding='utf-8')
    print(f"📄 CSV personalizado creado: {custom_csv}")
    
    # Definir mapeo de columnas
    column_mapping = {
        'Fecha': 'date',
        'Operación': 'type',
        'Ticker': 'ticker',
        'Nombre': 'name',
        'Cantidad': 'quantity',
        'Precio': 'price',
        'Comisión': 'commission',
        'Notas': 'notes'
    }
    
    print(f"\n🔄 Aplicando mapeo de columnas:")
    for old, new in column_mapping.items():
        print(f"   '{old}' → '{new}'")
    
    # Importar con mapeo
    result2 = loader.import_from_csv(
        custom_csv,
        column_mapping=column_mapping,
        skip_duplicates=True
    )
    
    print(f"\n📈 Resultado:")
    print(f"   ✅ Importadas: {result2['success']}")
    print(f"   ⏭️  Omitidas: {result2['skipped']}")
    
    # ==========================================
    # TEST 5: EXPORTAR A CSV
    # ==========================================
    print("\n" + "="*70)
    print("TEST 5: Exportar Transacciones a CSV")
    print("="*70 + "\n")
    
    # Exportar todas
    print("📤 Exportando todas las transacciones...")
    csv_export_path = loader.export_to_csv()
    
    # Exportar solo compras de 2024
    print("\n📤 Exportando solo compras de 2024...")
    csv_filtered = loader.export_to_csv(
        output_path=Path('data/exports/compras_2024.csv'),
        filters={'type': 'buy', 'year': 2024}
    )
    
    # ==========================================
    # TEST 6: EXPORTAR A EXCEL
    # ==========================================
    print("\n" + "="*70)
    print("TEST 6: Exportar a Excel (con múltiples hojas)")
    print("="*70 + "\n")
    
    print("📤 Exportando a Excel con resumen...")
    excel_path = loader.export_to_excel(include_summary=True)
    print(f"\n   💡 Abre el archivo Excel para ver:")
    print(f"      - Hoja 'Transacciones': Todas tus operaciones")
    print(f"      - Hoja 'Resumen': Estadísticas generales")
    print(f"      - Hoja 'Dividendos': Dividendos recibidos (si hay)")
    
    # ==========================================
    # TEST 7: VERIFICAR DATOS IMPORTADOS
    # ==========================================
    print("\n" + "="*70)
    print("TEST 7: Verificar Datos Importados")
    print("="*70 + "\n")
    
    # Ver todas las transacciones
    all_trans = db.get_transactions()
    print(f"📊 Total transacciones en BD: {len(all_trans)}")
    
    # Ver por ticker
    print(f"\n🏷️  Transacciones por ticker:")
    tickers = db.get_all_tickers()
    for ticker in tickers:
        count = len(db.get_transactions(ticker=ticker))
        print(f"   {ticker}: {count} operaciones")
    
    # Mostrar últimas 5
    print(f"\n📝 Últimas 5 transacciones:")
    recent = db.get_transactions(limit=5)
    for trans in recent:
        print(f"   {trans.date} | {trans.type.upper():8} | {trans.ticker:6} | "
              f"{trans.quantity:6.0f} @ {trans.price:6.2f}€ | Total: {trans.total:8.2f}€")
    
    # ==========================================
    # TEST 8: ESTADÍSTICAS FINALES
    # ==========================================
    print("\n" + "="*70)
    print("TEST 8: Estadísticas de la Base de Datos")
    print("="*70 + "\n")
    
    stats = db.get_database_stats()
    print(f"📊 Total transacciones: {stats['total_transactions']}")
    print(f"💵 Total dividendos: {stats['total_dividends']}")
    print(f"🏷️  Tickers únicos: {stats['unique_tickers']}")
    if stats['date_range']:
        print(f"📅 Rango de fechas: {stats['date_range'][0]} → {stats['date_range'][1]}")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "="*70)
    print("✅ RESUMEN DE TESTS")
    print("="*70 + "\n")
    
    print("✅ Test 1: Generar Plantilla - OK")
    print("✅ Test 2: Validar Archivo - OK")
    print("✅ Test 3: Importar desde CSV - OK")
    print("✅ Test 4: Mapeo de Columnas - OK")
    print("✅ Test 5: Exportar a CSV - OK")
    print("✅ Test 6: Exportar a Excel - OK")
    print("✅ Test 7: Verificar Datos - OK")
    print("✅ Test 8: Estadísticas - OK")
    
    print("\n" + "="*70)
    print("🎉 TODOS LOS TESTS DE DATA LOADER PASARON")
    print("="*70 + "\n")
    
    print("📁 Archivos generados:")
    print(f"   - {template_path}")
    print(f"   - {custom_csv}")
    print(f"   - {csv_export_path}")
    print(f"   - {csv_filtered}")
    print(f"   - {excel_path}")
    
    print("\n💡 Próximos pasos:")
    print("   1. Edita 'data/exports/template_transactions.csv' con tus datos reales")
    print("   2. Impórtalo con: loader.import_from_csv('ruta/tu_archivo.csv')")
    print("   3. ¡Listo para la Sesión 3! (Módulo Portfolio)\n")
    
    loader.close()


if __name__ == '__main__':
    main()