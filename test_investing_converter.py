"""
Conversor de CSV de Investing.com al formato de Investment Tracker
Convierte el export de Investing.com (posiciones abiertas Y cerradas) a formato compatible
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime


def detect_asset_type(ticker, name, market):
    """
    Detecta el tipo de activo basándose en ticker, nombre y mercado
    
    Returns:
        'accion', 'fondo', o 'etf'
    """
    ticker_upper = ticker.upper()
    name_lower = name.lower() if name else ""
    
    # Fondos: empiezan con LP o 0P (códigos ISIN de fondos)
    if ticker.startswith(('LP', '0P')):
        return 'fondo'
    
    # ETFs: nombres comunes
    etf_keywords = ['etf', 'index fund', 'tracker', 'physical gold', 'physical silver', 
                    'leveraged', 'wisdomtree', 'vaneck', 'vanguard']
    if any(keyword in name_lower for keyword in etf_keywords):
        return 'etf'
    
    # Por defecto, si tiene ticker corto y está en bolsa, es acción
    if len(ticker_upper) <= 5 and market in ['BME', 'NYSE', 'TSXV', 'NASDAQ', 'LON', 'K', 'O']:
        return 'accion'
    
    # Casos especiales por mercado
    if market in ['LU', 'IR']:  # Luxemburgo, Irlanda = típicamente fondos
        return 'fondo'
    
    # Por defecto: fondo
    return 'fondo'


def clean_numeric_value(value_str):
    """
    Limpia un valor numérico del formato de Investing
    Ejemplos: "1.234,56" → 1234.56, "128,76" → 128.76
    """
    if pd.isna(value_str) or value_str == '' or value_str == '--':
        return 0.0
    
    # Convertir a string si no lo es
    value_str = str(value_str)
    
    # Quitar símbolos de moneda y espacios
    value_str = value_str.replace('€', '').replace('$', '').replace('C$', '').strip()
    
    # Si tiene punto como separador de miles y coma como decimal (formato europeo)
    # Ejemplo: "1.234,56" → "1234.56"
    if '.' in value_str and ',' in value_str:
        # Formato: 1.234,56 (europeo)
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str and value_str.count(',') == 1:
        # Formato: 1234,56 (europeo sin miles)
        value_str = value_str.replace(',', '.')
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0


def parse_investing_date(date_str):
    """
    Convierte fecha del formato de Investing (DD/MM/YYYY) a YYYY-MM-DD
    """
    if pd.isna(date_str) or date_str == '':
        return None
    
    try:
        # Formato: DD/MM/YYYY
        date_obj = datetime.strptime(str(date_str), '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        print(f"⚠️  Advertencia: No se pudo parsear fecha: {date_str}")
        return None


def extract_section(content, section_name, next_section_name=None):
    """
    Extrae una sección específica del CSV de Investing
    """
    if section_name not in content:
        return None
    
    section_start = content.find(section_name)
    
    if next_section_name and next_section_name in content:
        section_end = content.find(next_section_name, section_start)
        section_text = content[section_start:section_end]
    else:
        section_text = content[section_start:]
    
    lines = section_text.split('\n')
    
    # Encontrar header
    header_line_idx = 0
    for i, line in enumerate(lines):
        if line.startswith(',"Nombre"') or line.startswith(',"nombre"'):
            header_line_idx = i
            break
    
    if header_line_idx == 0 and not lines[0].startswith(',"Nombre"'):
        return None
    
    # Extraer header y datos
    header = lines[header_line_idx]
    data_lines = []
    
    for line in lines[header_line_idx + 1:]:
        if not line.strip() or not line.startswith(','):
            break
        data_lines.append(line)
    
    if not data_lines:
        return None
    
    # Crear CSV temporal
    csv_content = header + '\n' + '\n'.join(data_lines)
    
    return csv_content


def process_open_positions(csv_content):
    """
    Procesa la sección "Posiciones abiertas" (compras actuales)
    """
    from io import StringIO
    df = pd.read_csv(StringIO(csv_content))
    
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            nombre = row.get('Nombre', '')
            simbolo = row.get('Símbolo', '')
            mercado = row.get('Mercado', '')
            fecha_apertura = row.get('Fecha apertura', '')
            tipo = row.get('Tipo', 'Compra')
            cantidad = row.get('Cantidad', 0)
            precio_entrada = row.get('Precio entrada', 0)
            comision = row.get('Comisión', 0)
            
            # Limpiar y convertir
            fecha_limpia = parse_investing_date(fecha_apertura)
            
            if fecha_limpia is None:
                continue
            
            cantidad_limpia = clean_numeric_value(cantidad)
            precio_limpio = clean_numeric_value(precio_entrada)
            comision_limpia = clean_numeric_value(comision)
            
            if cantidad_limpia <= 0 or precio_limpio <= 0:
                continue
            
            tipo_activo = detect_asset_type(simbolo, nombre, mercado)
            tipo_operacion = 'buy' if tipo == 'Compra' else 'sell'
            
            transaction = {
                'date': fecha_limpia,
                'type': tipo_operacion,
                'ticker': simbolo,
                'name': nombre,
                'asset_type': tipo_activo,
                'quantity': cantidad_limpia,
                'price': precio_limpio,
                'commission': comision_limpia,
                'notes': f'Posición abierta - Mercado: {mercado}'
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"   ⚠️  Error en posición abierta fila {idx + 1}: {str(e)}")
            continue
    
    return transactions


def process_closed_positions(csv_content):
    """
    Procesa la sección "Posiciones cerradas" (ventas realizadas)
    """
    from io import StringIO
    df = pd.read_csv(StringIO(csv_content))
    
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            nombre = row.get('Nombre', '')
            simbolo = row.get('Símbolo', '')
            mercado = row.get('Mercado', '')
            fecha_apertura = row.get('F. apertura', '')  # Fecha compra original
            tipo = row.get('Tipo', 'Compra')
            cantidad = row.get('Cantidad', 0)
            precio_entrada = row.get('Precio entrada', 0)
            fecha_cierre = row.get('Fecha cierre', '')  # Fecha venta
            precio_cierre = row.get('Precio cierre', 0)  # Precio de venta
            beneficio_pct = row.get('%Beneficio', '')
            beneficio_neto = row.get('B/P neto', '')
            
            # Limpiar y convertir
            fecha_compra = parse_investing_date(fecha_apertura)
            fecha_venta = parse_investing_date(fecha_cierre)
            
            if fecha_compra is None or fecha_venta is None:
                continue
            
            cantidad_limpia = clean_numeric_value(cantidad)
            precio_compra_limpio = clean_numeric_value(precio_entrada)
            precio_venta_limpio = clean_numeric_value(precio_cierre)
            beneficio_limpio = clean_numeric_value(beneficio_neto)
            
            if cantidad_limpia <= 0:
                continue
            
            tipo_activo = detect_asset_type(simbolo, nombre, mercado)
            
            # IMPORTANTE: Crear DOS transacciones (compra Y venta)
            
            # 1. Transacción de COMPRA original
            if precio_compra_limpio > 0:
                transaccion_compra = {
                    'date': fecha_compra,
                    'type': 'buy',
                    'ticker': simbolo,
                    'name': nombre,
                    'asset_type': tipo_activo,
                    'quantity': cantidad_limpia,
                    'price': precio_compra_limpio,
                    'commission': 0.0,  # Investing no proporciona comisión por transacción
                    'notes': f'Compra (posición cerrada) - Mercado: {mercado}'
                }
                transactions.append(transaccion_compra)
            
            # 2. Transacción de VENTA
            if precio_venta_limpio > 0:
                transaccion_venta = {
                    'date': fecha_venta,
                    'type': 'sell',
                    'ticker': simbolo,
                    'name': nombre,
                    'asset_type': tipo_activo,
                    'quantity': cantidad_limpia,
                    'price': precio_venta_limpio,
                    'commission': 0.0,
                    'notes': f'Venta - Beneficio: {beneficio_limpio:.2f}€ ({beneficio_pct})'
                }
                transactions.append(transaccion_venta)
            
        except Exception as e:
            print(f"   ⚠️  Error en posición cerrada fila {idx + 1}: {str(e)}")
            continue
    
    return transactions


def convert_investing_to_tracker_format(investing_csv_path, output_csv_path=None):
    """
    Convierte CSV de Investing.com al formato de Investment Tracker
    Procesa tanto posiciones abiertas como cerradas
    
    Args:
        investing_csv_path: Ruta al CSV exportado de Investing.com
        output_csv_path: Ruta del CSV de salida (opcional)
    
    Returns:
        Path del archivo generado
    """
    print("\n" + "="*70)
    print("🔄 CONVERSOR DE CSV DE INVESTING.COM (COMPLETO)")
    print("="*70 + "\n")
    
    investing_csv_path = Path(investing_csv_path)
    
    if not investing_csv_path.exists():
        print(f"❌ Error: Archivo no encontrado: {investing_csv_path}")
        return None
    
    print(f"📥 Leyendo archivo: {investing_csv_path}")
    
    # Leer el archivo completo
    with open(investing_csv_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_transactions = []
    
    # ===== PROCESAR POSICIONES ABIERTAS =====
    print(f"\n1️⃣ Procesando 'Posiciones abiertas'...")
    open_csv = extract_section(content, 'Posiciones abiertas', 'Posiciones cerradas')
    
    if open_csv:
        open_trans = process_open_positions(open_csv)
        all_transactions.extend(open_trans)
        print(f"   ✅ {len(open_trans)} compras actuales procesadas")
    else:
        print(f"   ⚠️  No se encontró la sección 'Posiciones abiertas'")
    
    # ===== PROCESAR POSICIONES CERRADAS =====
    print(f"\n2️⃣ Procesando 'Posiciones cerradas' (ventas)...")
    closed_csv = extract_section(content, 'Posiciones cerradas')
    
    if closed_csv:
        closed_trans = process_closed_positions(closed_csv)
        all_transactions.extend(closed_trans)
        # Dividir entre compras y ventas
        compras_cerradas = [t for t in closed_trans if t['type'] == 'buy']
        ventas = [t for t in closed_trans if t['type'] == 'sell']
        print(f"   ✅ {len(compras_cerradas)} compras históricas procesadas")
        print(f"   ✅ {len(ventas)} ventas procesadas")
    else:
        print(f"   ⚠️  No se encontró la sección 'Posiciones cerradas'")
    
    if not all_transactions:
        print("\n❌ No se pudieron extraer transacciones del CSV")
        return None
    
    # Crear DataFrame con todas las transacciones
    df_converted = pd.DataFrame(all_transactions)
    
    # Ordenar por fecha
    df_converted['date'] = pd.to_datetime(df_converted['date'])
    df_converted = df_converted.sort_values('date')
    df_converted['date'] = df_converted['date'].dt.strftime('%Y-%m-%d')
    
    # Generar nombre de archivo de salida
    if output_csv_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_csv_path = Path('data') / f'investing_converted_{timestamp}.csv'
    else:
        output_csv_path = Path(output_csv_path)
    
    # Crear directorio si no existe
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar CSV convertido
    df_converted.to_csv(output_csv_path, index=False)
    
    print(f"\n✅ Conversión completada exitosamente!")
    print(f"   💾 Archivo guardado en: {output_csv_path}")
    
    # Mostrar resumen detallado
    print(f"\n📋 Resumen de conversión:")
    print(f"   📊 Total operaciones: {len(all_transactions)}")
    print(f"   🛒 Compras: {len(df_converted[df_converted['type'] == 'buy'])}")
    print(f"   💰 Ventas: {len(df_converted[df_converted['type'] == 'sell'])}")
    print(f"   🏷️  Tickers únicos: {df_converted['ticker'].nunique()}")
    
    # Desglose por tipo de activo
    print(f"\n   Por tipo de activo:")
    for asset_type in ['accion', 'fondo', 'etf']:
        count = len(df_converted[df_converted['asset_type'] == asset_type])
        if count > 0:
            print(f"   - {asset_type.capitalize()}: {count} operaciones")
    
    # Rango de fechas
    print(f"\n   📅 Rango temporal:")
    print(f"   - Primera operación: {df_converted['date'].min()}")
    print(f"   - Última operación: {df_converted['date'].max()}")
    
    # Mostrar primeras filas
    print(f"\n👀 Preview (primeras 10 operaciones):")
    preview = df_converted.head(10)[['date', 'type', 'ticker', 'quantity', 'price']]
    print(preview.to_string(index=False))
    
    print(f"\n💡 Próximo paso:")
    print(f"   Importa este archivo con:")
    print(f"   >>> from src.data_loader import DataLoader")
    print(f"   >>> loader = DataLoader()")
    print(f"   >>> result = loader.import_from_csv('{output_csv_path}')")
    
    return output_csv_path


def main():
    """Función principal para ejecutar desde línea de comandos"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python convert_investing_csv.py <archivo_investing.csv> [archivo_salida.csv]")
        print("\nEjemplo:")
        print("  python convert_investing_csv.py mi_portfolio_investing.csv")
        print("  python convert_investing_csv.py mi_portfolio.csv data/mis_operaciones.csv")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_investing_to_tracker_format(input_file, output_file)
    
    if result:
        print(f"\n🎉 ¡Listo! Ahora puedes importar {result} a tu sistema")


if __name__ == '__main__':
    main()