"""
Conversor de CSV de Investing.com al formato de Investment Tracker
Versión corregida para el formato real de Investing.com
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime


def detect_asset_type(ticker, name, market):
    """Detecta el tipo de activo"""
    ticker_upper = ticker.upper()
    name_lower = name.lower() if name else ""
    
    # Fondos: códigos ISIN que empiezan con LP o 0P
    if ticker.startswith(('LP', '0P')):
        return 'fondo'
    
    # ETFs: por palabras clave
    etf_keywords = ['etf', 'index fund', 'tracker', 'physical gold', 'physical silver', 
                    'leveraged', 'wisdomtree', 'vaneck', 'vanguard']
    if any(keyword in name_lower for keyword in etf_keywords):
        return 'etf'
    
    # Acciones: tickers cortos en bolsas conocidas
    if len(ticker_upper) <= 6 and market in ['BME', 'NYSE', 'TSXV', 'NASDAQ', 'LON', 'K', 'O', 'BIT', 'ETR', 'MI', 'DE']:
        return 'accion'
    
    # Por mercado
    if market in ['LU', 'IR']:
        return 'fondo'
    
    return 'fondo'


def clean_numeric_value(value_str):
    """
    Limpia valores numéricos del formato europeo de Investing
    "3.843.246" → 3843246
    "0,369" → 0.369
    "1.439,10 €" → 1439.10
    """
    if pd.isna(value_str) or value_str == '' or value_str == '--' or value_str == '"-"':
        return 0.0
    
    value_str = str(value_str).strip('"')
    
    # Quitar símbolos de moneda y espacios
    value_str = value_str.replace('€', '').replace('$', '').replace('C$', '').strip()
    
    # Formato europeo: punto = miles, coma = decimal
    # "1.234.567,89" → "1234567.89"
    if '.' in value_str and ',' in value_str:
        # Tiene punto Y coma: quitar puntos (miles), cambiar coma por punto (decimal)
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str and '.' not in value_str:
        # Solo tiene coma: es decimal europeo
        value_str = value_str.replace(',', '.')
    # Si solo tiene punto, probablemente sea decimal (formato US) - dejar como está
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0


def parse_investing_date(date_str):
    """Convierte fecha DD/MM/YYYY a YYYY-MM-DD"""
    if pd.isna(date_str) or date_str == '':
        return None
    
    # Quitar comillas si las tiene
    date_str = str(date_str).strip('"')
    
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        print(f"⚠️  Fecha inválida: {date_str}")
        return None


def extract_section_content(lines, start_marker, end_marker=None):
    """
    Extrae líneas entre dos marcadores
    start_marker: línea que contiene este texto
    end_marker: línea que contiene este texto (o None para hasta el final)
    """
    start_idx = None
    end_idx = len(lines)
    
    # Buscar inicio
    for i, line in enumerate(lines):
        if start_marker in line:
            start_idx = i
            break
    
    if start_idx is None:
        return None
    
    # Buscar fin (si hay end_marker)
    if end_marker:
        for i in range(start_idx + 1, len(lines)):
            if end_marker in lines[i]:
                end_idx = i
                break
    
    # Extraer líneas
    section_lines = lines[start_idx:end_idx]
    
    # Buscar header (línea con "Nombre","Símbolo", etc)
    header_idx = None
    for i, line in enumerate(section_lines):
        if '"Nombre"' in line and '"Símbolo"' in line:
            header_idx = i
            break
    
    if header_idx is None:
        return None
    
    # Extraer header y datos
    header = section_lines[header_idx]
    data_lines = []
    
    for line in section_lines[header_idx + 1:]:
        # Parar si línea vacía o línea de resumen
        if not line.strip() or line.startswith('"Val. mercado"') or line.startswith('"B/P'):
            break
        # Solo incluir líneas que empiecen con "",
        if line.startswith('""'):
            data_lines.append(line)
    
    if not data_lines:
        return None
    
    return header + '\n' + '\n'.join(data_lines)


def process_open_positions(csv_content):
    """Procesa posiciones abiertas"""
    from io import StringIO
    
    try:
        df = pd.read_csv(StringIO(csv_content), skipinitialspace=True)
    except Exception as e:
        print(f"   ❌ Error al leer CSV de posiciones abiertas: {e}")
        return []
    
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            # Extraer campos (la primera columna sin nombre está vacía)
            nombre = row.get('Nombre', '')
            simbolo = row.get('Símbolo', '')
            mercado = row.get('Mercado', '')
            fecha_apertura = row.get('Fecha apertura', '')
            tipo = row.get('Tipo', 'Compra')
            cantidad = row.get('Cantidad', 0)
            precio_entrada = row.get('Precio entrada', 0)
            comision = row.get('Comisión', 0)
            
            # Limpiar valores
            fecha_limpia = parse_investing_date(fecha_apertura)
            if not fecha_limpia:
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
                'notes': f'Posición abierta - {mercado}'
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"   ⚠️  Error en fila {idx + 1}: {str(e)}")
            continue
    
    return transactions


def process_closed_positions(csv_content):
    """Procesa posiciones cerradas (compra + venta)"""
    from io import StringIO
    
    try:
        df = pd.read_csv(StringIO(csv_content), skipinitialspace=True)
    except Exception as e:
        print(f"   ❌ Error al leer CSV de posiciones cerradas: {e}")
        return []
    
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            nombre = row.get('Nombre', '')
            simbolo = row.get('Símbolo', '')
            mercado = row.get('Mercado', '')
            fecha_apertura = row.get('F. apertura', '')
            tipo = row.get('Tipo', 'Compra')
            cantidad = row.get('Cantidad', 0)
            precio_entrada = row.get('Precio entrada', 0)
            fecha_cierre = row.get('Fecha cierre', '')
            precio_cierre = row.get('Precio cierre', 0)
            beneficio_pct = row.get('%Beneficio', '')
            beneficio_neto = row.get('B/P neto', '')
            
            # Limpiar valores
            fecha_compra = parse_investing_date(fecha_apertura)
            fecha_venta = parse_investing_date(fecha_cierre)
            
            if not fecha_compra or not fecha_venta:
                continue
            
            cantidad_limpia = clean_numeric_value(cantidad)
            precio_compra_limpio = clean_numeric_value(precio_entrada)
            precio_venta_limpio = clean_numeric_value(precio_cierre)
            beneficio_limpio = clean_numeric_value(beneficio_neto)
            
            if cantidad_limpia <= 0:
                continue
            
            tipo_activo = detect_asset_type(simbolo, nombre, mercado)
            
            # Crear COMPRA
            if precio_compra_limpio > 0:
                trans_compra = {
                    'date': fecha_compra,
                    'type': 'buy',
                    'ticker': simbolo,
                    'name': nombre,
                    'asset_type': tipo_activo,
                    'quantity': cantidad_limpia,
                    'price': precio_compra_limpio,
                    'commission': 0.0,
                    'notes': f'Compra cerrada - {mercado}'
                }
                transactions.append(trans_compra)
            
            # Crear VENTA
            if precio_venta_limpio > 0:
                trans_venta = {
                    'date': fecha_venta,
                    'type': 'sell',
                    'ticker': simbolo,
                    'name': nombre,
                    'asset_type': tipo_activo,
                    'quantity': cantidad_limpia,
                    'price': precio_venta_limpio,
                    'commission': 0.0,
                    'notes': f'Venta - B/P: {beneficio_limpio:.2f}€ ({beneficio_pct})'
                }
                transactions.append(trans_venta)
            
        except Exception as e:
            print(f"   ⚠️  Error en fila {idx + 1}: {str(e)}")
            continue
    
    return transactions


def convert_investing_to_tracker_format(investing_csv_path, output_csv_path=None):
    """
    Convierte CSV de Investing.com al formato del tracker
    """
    print("\n" + "="*70)
    print("🔄 CONVERSOR DE CSV DE INVESTING.COM")
    print("="*70 + "\n")
    
    investing_csv_path = Path(investing_csv_path)
    
    if not investing_csv_path.exists():
        print(f"❌ Archivo no encontrado: {investing_csv_path}")
        return None
    
    print(f"📥 Leyendo archivo: {investing_csv_path}")
    
    # Leer archivo completo
    with open(investing_csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    all_transactions = []
    
    # ===== POSICIONES ABIERTAS =====
    print(f"\n1️⃣ Procesando 'Posiciones abiertas'...")
    open_content = extract_section_content(lines, '"Posiciones abiertas"', '"Posiciones cerradas"')
    
    if open_content:
        open_trans = process_open_positions(open_content)
        all_transactions.extend(open_trans)
        print(f"   ✅ {len(open_trans)} posiciones abiertas procesadas")
    else:
        print(f"   ⚠️  No se encontró la sección 'Posiciones abiertas'")
    
    # ===== POSICIONES CERRADAS =====
    print(f"\n2️⃣ Procesando 'Posiciones cerradas'...")
    closed_content = extract_section_content(lines, '"Posiciones cerradas"')
    
    if closed_content:
        closed_trans = process_closed_positions(closed_content)
        all_transactions.extend(closed_trans)
        compras = [t for t in closed_trans if t['type'] == 'buy']
        ventas = [t for t in closed_trans if t['type'] == 'sell']
        print(f"   ✅ {len(compras)} compras históricas procesadas")
        print(f"   ✅ {len(ventas)} ventas procesadas")
    else:
        print(f"   ⚠️  No se encontró la sección 'Posiciones cerradas'")
    
    if not all_transactions:
        print("\n❌ No se pudieron extraer transacciones del CSV")
        return None
    
    # Crear DataFrame
    df = pd.DataFrame(all_transactions)
    
    # Ordenar por fecha
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Generar archivo de salida
    if output_csv_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_csv_path = Path('data') / f'investing_converted_{timestamp}.csv'
    else:
        output_csv_path = Path(output_csv_path)
    
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv_path, index=False)
    
    print(f"\n✅ Conversión completada!")
    print(f"   💾 Archivo: {output_csv_path}")
    
    # Resumen
    print(f"\n📋 Resumen:")
    print(f"   📊 Total operaciones: {len(all_transactions)}")
    print(f"   🛒 Compras: {len(df[df['type'] == 'buy'])}")
    print(f"   💰 Ventas: {len(df[df['type'] == 'sell'])}")
    print(f"   🏷️  Tickers únicos: {df['ticker'].nunique()}")
    
    for asset_type in ['accion', 'fondo', 'etf']:
        count = len(df[df['asset_type'] == asset_type])
        if count > 0:
            print(f"   - {asset_type.capitalize()}: {count} ops")
    
    print(f"\n   📅 Rango: {df['date'].min()} → {df['date'].max()}")
    
    print(f"\n👀 Preview (primeras 10):")
    preview = df.head(10)[['date', 'type', 'ticker', 'quantity', 'price']]
    print(preview.to_string(index=False))
    
    print(f"\n💡 Próximo paso:")
    print(f"   >>> from src.data_loader import DataLoader")
    print(f"   >>> loader = DataLoader()")
    print(f"   >>> loader.import_from_csv('{output_csv_path}')\n")
    
    return output_csv_path


def main():
    """Función para ejecutar desde línea de comandos"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python convert_investing_csv.py <archivo_investing.csv> [salida.csv]")
        print("\nEjemplo:")
        print("  python convert_investing_csv.py data/portfolio_investing.csv")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_investing_to_tracker_format(input_file, output_file)
    
    if result:
        print(f"🎉 ¡Listo! Archivo convertido: {result}")


if __name__ == '__main__':
    main()