"""
Conversor de CSV de Investing.com al formato de Investment Tracker
Versión 4.0 - Con soporte de divisas y B/P neto directo

MEJORAS:
- Captura la divisa basándose en el mercado
- Usa el B/P neto ya convertido a EUR del CSV (evita errores de conversión)
- Detecta correctamente peniques (GBX) vs libras (GBP)
- Incluye el nombre del activo en todas las transacciones
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from io import StringIO


# Mapeo de mercados a divisas
MARKET_CURRENCY_MAP = {
    'BME': 'EUR',      # Bolsa de Madrid
    'EPA': 'EUR',      # Euronext Paris
    'ETR': 'EUR',      # Deutsche Börse (Xetra)
    'BIT': 'EUR',      # Borsa Italiana (Milán)
    'MI': 'EUR',       # Milán
    'DE': 'EUR',       # Alemania
    'NYSE': 'USD',     # New York Stock Exchange
    'NASDAQ': 'USD',   # NASDAQ
    'K': 'USD',        # NYSE (alternativo)
    'O': 'USD',        # NASDAQ (alternativo)
    'LON': 'GBX',      # Londres (en peniques!)
    'L': 'GBX',        # Londres alternativo
    'TSXV': 'CAD',     # Toronto Venture
    'TSX': 'CAD',      # Toronto
    'LU': 'EUR',       # Luxemburgo (fondos)
    'IR': 'EUR',       # Irlanda (fondos)
}


def detect_asset_type(ticker, name, market):
    """Detecta el tipo de activo basándose en ticker, nombre y mercado"""
    ticker_upper = str(ticker).upper()
    name_lower = str(name).lower() if name else ""
    
    # Fondos: códigos ISIN que empiezan con LP o 0P
    if ticker_upper.startswith(('LP', '0P')):
        return 'fondo'
    
    # ETFs: por palabras clave en el nombre
    etf_keywords = ['etf', 'ucits', 'tracker', 'physical gold', 'physical silver', 
                    'leveraged', 'leverage shares', 'wisdomtree', 'vaneck', 
                    'ishares', 'spdr', 'lyxor', 'amundi physical', 'vanguard']
    if any(keyword in name_lower for keyword in etf_keywords):
        return 'etf'
    
    # Acciones: tickers cortos en bolsas de acciones
    stock_markets = ['BME', 'NYSE', 'NASDAQ', 'LON', 'TSXV', 'TSX', 'K', 'O', 'L']
    if market in stock_markets and len(ticker_upper) <= 8:
        return 'accion'
    
    # Por mercado de fondos
    if market in ['LU', 'IR']:
        return 'fondo'
    
    return 'fondo'  # Por defecto


def get_currency_from_market(market):
    """Obtiene la divisa basándose en el mercado"""
    return MARKET_CURRENCY_MAP.get(market, 'EUR')


def clean_numeric_value(value_str):
    """
    Limpia valores numéricos del formato europeo de Investing
    Ejemplos:
        "3.843.246" → 3843246
        "0,369" → 0.369
        "1.439,10 €" → 1439.10
        "-143,28 €" → -143.28
    """
    if pd.isna(value_str) or value_str == '' or value_str == '--' or value_str == '"-"':
        return 0.0
    
    value_str = str(value_str).strip().strip('"')
    
    # Detectar si es negativo
    is_negative = value_str.startswith('-') or '-' in value_str
    
    # Quitar símbolos de moneda y espacios
    value_str = value_str.replace('€', '').replace('$', '').replace('C$', '')
    value_str = value_str.replace('£', '').replace('%', '').strip()
    
    # Quitar el signo negativo temporalmente para procesar
    value_str = value_str.replace('-', '').replace('+', '')
    
    # Formato europeo: punto = miles, coma = decimal
    if '.' in value_str and ',' in value_str:
        # Tiene punto Y coma: quitar puntos (miles), cambiar coma por punto (decimal)
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str and '.' not in value_str:
        # Solo tiene coma: es decimal europeo
        value_str = value_str.replace(',', '.')
    # Si solo tiene punto, es decimal (formato US/internacional)
    
    try:
        result = float(value_str)
        return -result if is_negative else result
    except ValueError:
        return 0.0


def parse_investing_date(date_str):
    """Convierte fecha DD/MM/YYYY a YYYY-MM-DD"""
    if pd.isna(date_str) or date_str == '' or date_str == '--':
        return None
    
    date_str = str(date_str).strip().strip('"')
    
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Intentar otros formatos
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            print(f"   ⚠️  Fecha inválida: {date_str}")
            return None


def find_section_bounds(lines, section_name):
    """
    Encuentra los límites de una sección en el CSV.
    Retorna (start_idx, end_idx) o (None, None) si no se encuentra.
    """
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        # Buscar inicio de sección
        if f'"{section_name}"' in line or section_name in line:
            start_idx = i
            continue
        
        # Si ya encontramos el inicio, buscar el fin
        if start_idx is not None:
            # El fin es cuando encontramos otra sección o línea de resumen
            if (line.startswith('"Posiciones') or 
                line.startswith('"Val. mercado"') or
                line.startswith('"B/P ') or
                line.startswith('"Resumen')):
                end_idx = i
                break
    
    # Si no encontramos fin, usar hasta el final
    if start_idx is not None and end_idx is None:
        end_idx = len(lines)
    
    return start_idx, end_idx


def extract_section_dataframe(lines, section_name):
    """
    Extrae una sección del CSV y la convierte a DataFrame.
    """
    start_idx, end_idx = find_section_bounds(lines, section_name)
    
    if start_idx is None:
        return None
    
    # Encontrar la línea del header (contiene "Nombre" y "Símbolo")
    header_idx = None
    for i in range(start_idx, min(start_idx + 5, end_idx)):
        if '"Nombre"' in lines[i] and '"Símbolo"' in lines[i]:
            header_idx = i
            break
    
    if header_idx is None:
        return None
    
    # Extraer líneas de datos (empiezan con "","")
    data_lines = []
    for i in range(header_idx + 1, end_idx):
        line = lines[i].strip()
        if line.startswith('"","') or line.startswith(',"'):
            data_lines.append(line)
        elif line == '' or line.startswith('"Val.') or line.startswith('"B/P'):
            break
    
    if not data_lines:
        return None
    
    # Crear CSV string y leer con pandas
    csv_content = lines[header_idx] + '\n' + '\n'.join(data_lines)
    
    try:
        df = pd.read_csv(StringIO(csv_content), skipinitialspace=True)
        # Renombrar primera columna vacía
        if df.columns[0] == '' or pd.isna(df.columns[0]):
            df = df.rename(columns={df.columns[0]: '_empty'})
        return df
    except Exception as e:
        print(f"   ❌ Error parseando sección {section_name}: {e}")
        return None


def process_open_positions(df):
    """
    Procesa posiciones abiertas.
    Columnas esperadas: Nombre, Símbolo, Mercado, Fecha apertura, Tipo, Cantidad, 
                        Precio entrada, ..., B/P neto
    """
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            nombre = str(row.get('Nombre', '')).strip()
            simbolo = str(row.get('Símbolo', '')).strip()
            mercado = str(row.get('Mercado', '')).strip()
            fecha = row.get('Fecha apertura', '')
            tipo = str(row.get('Tipo', 'Compra')).strip()
            cantidad = row.get('Cantidad', 0)
            precio = row.get('Precio entrada', 0)
            comision = row.get('Comisión', 0)
            bp_neto = row.get('B/P neto', 0)  # Beneficio/Pérdida ya en EUR
            
            # Limpiar valores
            fecha_limpia = parse_investing_date(fecha)
            if not fecha_limpia:
                continue
            
            cantidad_limpia = clean_numeric_value(cantidad)
            precio_limpio = clean_numeric_value(precio)
            comision_limpia = clean_numeric_value(comision)
            bp_neto_limpio = clean_numeric_value(bp_neto)
            
            if cantidad_limpia <= 0:
                continue
            
            # Detectar divisa y tipo de activo
            currency = get_currency_from_market(mercado)
            asset_type = detect_asset_type(simbolo, nombre, mercado)
            
            # Tipo de operación
            tipo_op = 'sell' if 'Venta' in tipo else 'buy'
            
            transaction = {
                'date': fecha_limpia,
                'type': tipo_op,
                'ticker': simbolo,
                'name': nombre,
                'asset_type': asset_type,
                'quantity': cantidad_limpia,
                'price': precio_limpio,
                'commission': comision_limpia,
                'currency': currency,
                'market': mercado,
                'unrealized_gain_eur': bp_neto_limpio,  # B/P latente ya en EUR
                'notes': f'Posición abierta - {mercado} ({currency})'
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"   ⚠️  Error en posición abierta fila {idx + 1}: {str(e)[:50]}")
            continue
    
    return transactions


def process_closed_positions(df):
    """
    Procesa posiciones cerradas.
    Columnas: Nombre, Símbolo, Mercado, F. apertura, Tipo, Cantidad, 
              Precio entrada, Fecha cierre, Precio cierre, %Beneficio, B/P neto
    
    IMPORTANTE: Usa el B/P neto del CSV directamente (ya está en EUR)
    """
    transactions = []
    
    for idx, row in df.iterrows():
        try:
            nombre = str(row.get('Nombre', '')).strip()
            simbolo = str(row.get('Símbolo', '')).strip()
            mercado = str(row.get('Mercado', '')).strip()
            fecha_apertura = row.get('F. apertura', '')
            tipo = str(row.get('Tipo', 'Compra')).strip()
            cantidad = row.get('Cantidad', 0)
            precio_entrada = row.get('Precio entrada', 0)
            fecha_cierre = row.get('Fecha cierre', '')
            precio_cierre = row.get('Precio cierre', 0)
            beneficio_pct = row.get('%Beneficio', '')
            bp_neto = row.get('B/P neto', 0)  # ¡CLAVE! Ya está en EUR
            
            # Limpiar valores
            fecha_compra = parse_investing_date(fecha_apertura)
            fecha_venta = parse_investing_date(fecha_cierre)
            
            if not fecha_compra or not fecha_venta:
                continue
            
            cantidad_limpia = clean_numeric_value(cantidad)
            precio_compra = clean_numeric_value(precio_entrada)
            precio_venta = clean_numeric_value(precio_cierre)
            bp_neto_eur = clean_numeric_value(bp_neto)  # Beneficio REAL en EUR
            
            if cantidad_limpia <= 0:
                continue
            
            # Detectar divisa y tipo de activo
            currency = get_currency_from_market(mercado)
            asset_type = detect_asset_type(simbolo, nombre, mercado)
            
            # Crear transacción de COMPRA
            trans_compra = {
                'date': fecha_compra,
                'type': 'buy',
                'ticker': simbolo,
                'name': nombre,
                'asset_type': asset_type,
                'quantity': cantidad_limpia,
                'price': precio_compra,
                'commission': 0.0,
                'currency': currency,
                'market': mercado,
                'notes': f'Compra (cerrada) - {mercado} ({currency})'
            }
            transactions.append(trans_compra)
            
            # Crear transacción de VENTA con el B/P neto REAL
            trans_venta = {
                'date': fecha_venta,
                'type': 'sell',
                'ticker': simbolo,
                'name': nombre,
                'asset_type': asset_type,
                'quantity': cantidad_limpia,
                'price': precio_venta,
                'commission': 0.0,
                'currency': currency,
                'market': mercado,
                'realized_gain_eur': bp_neto_eur,  # ¡IMPORTANTE! Ganancia real en EUR
                'notes': f'Venta - B/P: {bp_neto_eur:+.2f}€ ({beneficio_pct})'
            }
            transactions.append(trans_venta)
            
        except Exception as e:
            print(f"   ⚠️  Error en posición cerrada fila {idx + 1}: {str(e)[:50]}")
            continue
    
    return transactions


def convert_investing_to_tracker(input_path, output_path=None):
    """
    Convierte CSV de Investing.com al formato del Investment Tracker.
    
    Args:
        input_path: Ruta al CSV de Investing.com
        output_path: Ruta de salida (opcional)
    
    Returns:
        Path del archivo generado o None si falla
    """
    print("\n" + "="*70)
    print("🔄 CONVERSOR DE CSV DE INVESTING.COM v4.0")
    print("   (Con soporte de divisas y B/P neto)")
    print("="*70)
    
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"\n❌ Archivo no encontrado: {input_path}")
        return None
    
    print(f"\n📥 Leyendo: {input_path}")
    
    # Leer archivo
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    all_transactions = []
    
    # ===== POSICIONES ABIERTAS =====
    print(f"\n1️⃣  Procesando 'Posiciones abiertas'...")
    
    df_open = extract_section_dataframe(lines, 'Posiciones abiertas')
    
    if df_open is not None and not df_open.empty:
        open_trans = process_open_positions(df_open)
        all_transactions.extend(open_trans)
        print(f"   ✅ {len(open_trans)} posiciones abiertas")
    else:
        print(f"   ⚠️  No se encontró sección 'Posiciones abiertas'")
    
    # ===== POSICIONES CERRADAS =====
    print(f"\n2️⃣  Procesando 'Posiciones cerradas'...")
    
    df_closed = extract_section_dataframe(lines, 'Posiciones cerradas')
    
    if df_closed is not None and not df_closed.empty:
        closed_trans = process_closed_positions(df_closed)
        all_transactions.extend(closed_trans)
        
        compras = len([t for t in closed_trans if t['type'] == 'buy'])
        ventas = len([t for t in closed_trans if t['type'] == 'sell'])
        print(f"   ✅ {compras} compras históricas")
        print(f"   ✅ {ventas} ventas (con B/P en EUR)")
    else:
        print(f"   ⚠️  No se encontró sección 'Posiciones cerradas'")
    
    if not all_transactions:
        print("\n❌ No se pudieron extraer transacciones")
        return None
    
    # Crear DataFrame
    df = pd.DataFrame(all_transactions)
    
    # Ordenar por fecha
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Generar archivo de salida
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path('data') / f'investing_converted_{timestamp}.csv'
    else:
        output_path = Path(output_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar
    df.to_csv(output_path, index=False)
    
    # ===== RESUMEN =====
    print(f"\n" + "="*70)
    print("✅ CONVERSIÓN COMPLETADA")
    print("="*70)
    print(f"\n💾 Archivo: {output_path}")
    
    print(f"\n📊 Resumen:")
    print(f"   Total operaciones: {len(df)}")
    print(f"   🛒 Compras: {len(df[df['type'] == 'buy'])}")
    print(f"   💰 Ventas: {len(df[df['type'] == 'sell'])}")
    print(f"   🏷️  Tickers: {df['ticker'].nunique()}")
    
    # Por tipo de activo
    print(f"\n   Por tipo:")
    for asset_type in df['asset_type'].unique():
        count = len(df[df['asset_type'] == asset_type])
        print(f"   - {asset_type}: {count}")
    
    # Por divisa
    if 'currency' in df.columns:
        print(f"\n   Por divisa:")
        for currency in df['currency'].unique():
            count = len(df[df['currency'] == currency])
            print(f"   - {currency}: {count}")
    
    # Rango temporal
    print(f"\n   📅 Rango: {df['date'].min()} → {df['date'].max()}")
    
    # B/P de ventas (usando el campo correcto)
    if 'realized_gain_eur' in df.columns:
        ventas_df = df[df['type'] == 'sell']
        if not ventas_df.empty:
            total_bp = ventas_df['realized_gain_eur'].sum()
            ganancias = ventas_df[ventas_df['realized_gain_eur'] > 0]['realized_gain_eur'].sum()
            perdidas = abs(ventas_df[ventas_df['realized_gain_eur'] < 0]['realized_gain_eur'].sum())
            print(f"\n   💵 B/P Ventas (ya en EUR):")
            print(f"   - Ganancias: +{ganancias:,.2f}€")
            print(f"   - Pérdidas: -{perdidas:,.2f}€")
            print(f"   - Neto: {total_bp:+,.2f}€")
    
    # Preview
    print(f"\n👀 Preview (primeras 10):")
    cols_preview = ['date', 'type', 'ticker', 'name', 'quantity', 'price', 'currency']
    if 'realized_gain_eur' in df.columns:
        cols_preview.append('realized_gain_eur')
    cols_available = [c for c in cols_preview if c in df.columns]
    print(df.head(10)[cols_available].to_string(index=False))
    
    print(f"\n💡 Próximo paso:")
    print(f"   from src.data_loader import DataLoader")
    print(f"   loader = DataLoader()")
    print(f"   loader.import_from_csv('{output_path}')")
    
    print("\n" + "="*70 + "\n")
    
    return output_path


def main():
    """Función principal para ejecutar desde línea de comandos"""
    import sys
    
    if len(sys.argv) < 2:
        print("\nUso: python convert_investing_csv.py <archivo_investing.csv> [salida.csv]")
        print("\nEjemplo:")
        print("  python convert_investing_csv.py data/mi_portfolio_investing.csv")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_investing_to_tracker(input_file, output_file)
    
    if result:
        print(f"🎉 ¡Listo! Archivo convertido: {result}")


if __name__ == '__main__':
    main()
