"""
Data Loader Module - Importador/Exportador de Datos
Sesión 2 del Investment Tracker (Actualizado v2)

CAMBIOS v2:
- Importa campos nuevos: currency, market, realized_gain_eur, unrealized_gain_eur
- Compatible con CSV generado por convert_investing_csv_v4.py

Este módulo gestiona la importación y exportación de datos desde/hacia
archivos CSV y Excel.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from src.database import Database
except ImportError:
    from database import Database


class DataLoader:
    """
    Clase para importar y exportar datos de transacciones.
    
    Uso:
        loader = DataLoader()
        
        # Importar desde CSV
        result = loader.import_from_csv('mis_operaciones.csv')
        print(f"Importadas: {result['success']}")
        
        # Exportar a CSV
        loader.export_to_csv('backup.csv')
        
        loader.close()
    """
    
    # Mapeo de columnas del CSV a campos de la base de datos
    COLUMN_MAPPING = {
        # Columnas estándar
        'date': 'date',
        'fecha': 'date',
        'type': 'type',
        'tipo': 'type',
        'ticker': 'ticker',
        'symbol': 'ticker',
        'simbolo': 'ticker',
        'name': 'name',
        'nombre': 'name',
        'asset_type': 'asset_type',
        'tipo_activo': 'asset_type',
        'quantity': 'quantity',
        'cantidad': 'quantity',
        'qty': 'quantity',
        'price': 'price',
        'precio': 'price',
        'commission': 'commission',
        'comision': 'commission',
        'comisión': 'commission',
        'total': 'total',
        'notes': 'notes',
        'notas': 'notes',
        
        # CAMPOS NUEVOS v2
        'currency': 'currency',
        'divisa': 'currency',
        'market': 'market',
        'mercado': 'market',
        'realized_gain_eur': 'realized_gain_eur',
        'bp_neto_eur': 'realized_gain_eur',
        'ganancia_realizada': 'realized_gain_eur',
        'unrealized_gain_eur': 'unrealized_gain_eur',
        'bp_latente_eur': 'unrealized_gain_eur',
        'ganancia_latente': 'unrealized_gain_eur',
    }
    
    # Campos requeridos
    REQUIRED_FIELDS = ['date', 'type', 'ticker', 'quantity', 'price']
    
    # Campos opcionales con valores por defecto
    OPTIONAL_FIELDS = {
        'name': None,
        'asset_type': 'unknown',
        'commission': 0.0,
        'total': None,
        'notes': None,
        'currency': 'EUR',
        'market': None,
        'realized_gain_eur': None,
        'unrealized_gain_eur': None,
    }
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el DataLoader.
        
        Args:
            db_path: Ruta a la base de datos. Si es None, usa la ruta por defecto.
        """
        self.db = Database(db_path) if db_path else Database()
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()
    
    def _normalize_column_name(self, column: str) -> str:
        """Normaliza el nombre de una columna al formato interno"""
        column_lower = column.lower().strip()
        return self.COLUMN_MAPPING.get(column_lower, column_lower)
    
    def _parse_date(self, date_value: Any) -> str:
        """Convierte varios formatos de fecha a YYYY-MM-DD"""
        if date_value is None or date_value == '':
            return None
        
        date_str = str(date_value).strip()
        
        # Formatos a probar
        formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%d/%m/%Y',      # 15/01/2024
            '%d-%m-%Y',      # 15-01-2024
            '%Y/%m/%d',      # 2024/01/15
            '%d.%m.%Y',      # 15.01.2024
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Si es timestamp de pandas
        if HAS_PANDAS:
            try:
                dt = pd.to_datetime(date_str)
                return dt.strftime('%Y-%m-%d')
            except:
                pass
        
        return None
    
    def _parse_number(self, value: Any) -> float:
        """Convierte varios formatos numéricos a float"""
        if value is None or value == '' or value == '--':
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        value_str = str(value).strip()
        
        # Detectar negativo
        is_negative = value_str.startswith('-') or (value_str.count('-') == 1 and not value_str.endswith('-'))
        
        # Limpiar caracteres
        value_str = value_str.replace('€', '').replace('$', '').replace('%', '')
        value_str = value_str.replace('£', '').replace(' ', '').strip()
        value_str = value_str.replace('-', '').replace('+', '')
        
        # Formato europeo: 1.234,56 -> 1234.56
        if '.' in value_str and ',' in value_str:
            value_str = value_str.replace('.', '').replace(',', '.')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        try:
            result = float(value_str)
            return -result if is_negative else result
        except ValueError:
            return 0.0
    
    def _parse_type(self, type_value: Any) -> str:
        """Normaliza el tipo de transacción"""
        if type_value is None:
            return 'buy'
        
        type_str = str(type_value).lower().strip()
        
        type_mapping = {
            'buy': 'buy',
            'compra': 'buy',
            'purchase': 'buy',
            'sell': 'sell',
            'venta': 'sell',
            'sale': 'sell',
            'transfer_in': 'transfer_in',
            'traspaso_entrada': 'transfer_in',
            'transfer_out': 'transfer_out',
            'traspaso_salida': 'transfer_out',
            'dividend': 'dividend',
            'dividendo': 'dividend',
        }
        
        return type_mapping.get(type_str, 'buy')
    
    def import_from_csv(self, 
                       file_path: str,
                       column_mapping: Dict[str, str] = None,
                       validate: bool = True,
                       skip_duplicates: bool = True) -> Dict:
        """
        Importa transacciones desde un archivo CSV.
        
        Args:
            file_path: Ruta al archivo CSV
            column_mapping: Mapeo adicional de columnas {columna_csv: campo_db}
            validate: Si True, valida datos antes de importar
            skip_duplicates: Si True, omite registros duplicados
        
        Returns:
            Dict con:
            - success: Número de registros importados
            - errors: Lista de errores encontrados
            - duplicates: Número de duplicados omitidos
            - total: Total de filas procesadas
        """
        result = {
            'success': 0,
            'errors': [],
            'duplicates': 0,
            'total': 0
        }
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            result['errors'].append(f"Archivo no encontrado: {file_path}")
            return result
        
        # Combinar mapeos
        full_mapping = {**self.COLUMN_MAPPING}
        if column_mapping:
            full_mapping.update({k.lower(): v for k, v in column_mapping.items()})
        
        # Leer CSV
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            result['errors'].append(f"Error leyendo CSV: {str(e)}")
            return result
        
        result['total'] = len(rows)
        
        # Mapear columnas del CSV
        if rows:
            csv_columns = {self._normalize_column_name(col): col for col in rows[0].keys()}
        
        # Procesar cada fila
        for i, row in enumerate(rows, 1):
            try:
                # Crear diccionario con datos normalizados
                transaction = {}
                
                # Mapear columnas
                for csv_col, csv_value in row.items():
                    normalized = self._normalize_column_name(csv_col)
                    if normalized in self.REQUIRED_FIELDS or normalized in self.OPTIONAL_FIELDS:
                        transaction[normalized] = csv_value
                
                # Parsear campos requeridos
                transaction['date'] = self._parse_date(transaction.get('date'))
                transaction['type'] = self._parse_type(transaction.get('type'))
                transaction['ticker'] = str(transaction.get('ticker', '')).strip().upper()
                transaction['quantity'] = self._parse_number(transaction.get('quantity'))
                transaction['price'] = self._parse_number(transaction.get('price'))
                
                # Validar campos requeridos
                if validate:
                    if not transaction['date']:
                        result['errors'].append(f"Fila {i}: Fecha inválida")
                        continue
                    if not transaction['ticker']:
                        result['errors'].append(f"Fila {i}: Ticker vacío")
                        continue
                    if transaction['quantity'] <= 0:
                        result['errors'].append(f"Fila {i}: Cantidad debe ser > 0")
                        continue
                    if transaction['price'] < 0:
                        result['errors'].append(f"Fila {i}: Precio negativo")
                        continue
                
                # Parsear campos opcionales
                transaction['name'] = transaction.get('name', '').strip() or None
                transaction['asset_type'] = transaction.get('asset_type', 'unknown').strip() or 'unknown'
                transaction['commission'] = self._parse_number(transaction.get('commission', 0))
                transaction['notes'] = transaction.get('notes', '').strip() or None
                
                # CAMPOS NUEVOS v2
                transaction['currency'] = transaction.get('currency', 'EUR').strip() or 'EUR'
                transaction['market'] = transaction.get('market', '').strip() or None
                
                # realized_gain_eur - IMPORTANTE para el cálculo correcto de plusvalías
                realized_gain = transaction.get('realized_gain_eur')
                if realized_gain is not None and realized_gain != '':
                    transaction['realized_gain_eur'] = self._parse_number(realized_gain)
                else:
                    transaction['realized_gain_eur'] = None
                
                # unrealized_gain_eur - para posiciones abiertas
                unrealized_gain = transaction.get('unrealized_gain_eur')
                if unrealized_gain is not None and unrealized_gain != '':
                    transaction['unrealized_gain_eur'] = self._parse_number(unrealized_gain)
                else:
                    transaction['unrealized_gain_eur'] = None
                
                # Calcular total si no está especificado
                if not transaction.get('total'):
                    qty = transaction['quantity']
                    price = transaction['price']
                    commission = transaction['commission']
                    
                    if transaction['type'] in ['buy', 'transfer_in']:
                        transaction['total'] = qty * price + commission
                    else:
                        transaction['total'] = qty * price - commission
                else:
                    transaction['total'] = self._parse_number(transaction['total'])
                
                # Insertar en base de datos
                self.db.add_transaction(transaction)
                result['success'] += 1
                
            except Exception as e:
                result['errors'].append(f"Fila {i}: {str(e)}")
        
        return result
    
    def export_to_csv(self, 
                     file_path: str,
                     filters: Dict = None,
                     include_header: bool = True) -> bool:
        """
        Exporta transacciones a un archivo CSV.
        
        Args:
            file_path: Ruta del archivo de salida
            filters: Filtros para las transacciones (ticker, type, year, etc.)
            include_header: Si True, incluye fila de encabezado
        
        Returns:
            True si la exportación fue exitosa
        """
        # Obtener transacciones
        if filters:
            transactions = self.db.get_transactions(**filters)
        else:
            transactions = self.db.get_transactions()
        
        if not transactions:
            print("No hay transacciones para exportar")
            return False
        
        # Preparar datos
        fieldnames = [
            'date', 'type', 'ticker', 'name', 'asset_type', 
            'quantity', 'price', 'commission', 'total',
            'currency', 'market', 'realized_gain_eur', 'unrealized_gain_eur',
            'notes'
        ]
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if include_header:
                    writer.writeheader()
                
                for trans in transactions:
                    row = {
                        'date': trans.date.isoformat() if trans.date else '',
                        'type': trans.type,
                        'ticker': trans.ticker,
                        'name': trans.name or '',
                        'asset_type': trans.asset_type or '',
                        'quantity': trans.quantity,
                        'price': trans.price,
                        'commission': trans.commission or 0,
                        'total': trans.total or 0,
                        'currency': trans.currency or 'EUR',
                        'market': trans.market or '',
                        'realized_gain_eur': trans.realized_gain_eur if trans.realized_gain_eur else '',
                        'unrealized_gain_eur': trans.unrealized_gain_eur if trans.unrealized_gain_eur else '',
                        'notes': trans.notes or ''
                    }
                    writer.writerow(row)
            
            print(f"✅ Exportadas {len(transactions)} transacciones a {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error exportando: {e}")
            return False
    
    def validate_import_file(self, file_path: str) -> List[str]:
        """
        Valida un archivo CSV antes de importar (sin guardar nada).
        
        Args:
            file_path: Ruta al archivo CSV
        
        Returns:
            Lista de problemas encontrados (vacía si todo está bien)
        """
        problems = []
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return [f"Archivo no encontrado: {file_path}"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            return [f"Error leyendo archivo: {e}"]
        
        if not rows:
            return ["El archivo está vacío"]
        
        # Verificar columnas requeridas
        csv_columns = [self._normalize_column_name(col) for col in rows[0].keys()]
        
        for required in self.REQUIRED_FIELDS:
            if required not in csv_columns:
                problems.append(f"Falta columna requerida: {required}")
        
        # Verificar datos
        for i, row in enumerate(rows[:10], 1):  # Solo verificar primeras 10 filas
            # Fecha
            date_col = next((c for c in row.keys() if self._normalize_column_name(c) == 'date'), None)
            if date_col and not self._parse_date(row.get(date_col)):
                problems.append(f"Fila {i}: Formato de fecha no reconocido")
            
            # Cantidad
            qty_col = next((c for c in row.keys() if self._normalize_column_name(c) == 'quantity'), None)
            if qty_col:
                qty = self._parse_number(row.get(qty_col))
                if qty <= 0:
                    problems.append(f"Fila {i}: Cantidad debe ser > 0")
        
        return problems
    
    def get_import_stats(self) -> Dict:
        """Retorna estadísticas de la base de datos"""
        return self.db.get_database_stats()


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def quick_import(file_path: str, db_path: str = None) -> Dict:
    """
    Importación rápida de un archivo CSV.
    
    Uso:
        from src.data_loader import quick_import
        result = quick_import('mis_operaciones.csv')
        print(f"Importadas: {result['success']}")
    """
    loader = DataLoader(db_path)
    result = loader.import_from_csv(file_path)
    loader.close()
    return result


def quick_export(file_path: str, db_path: str = None, **filters) -> bool:
    """
    Exportación rápida a CSV.
    
    Uso:
        from src.data_loader import quick_export
        quick_export('backup.csv')
        quick_export('ventas_2024.csv', type='sell', year=2024)
    """
    loader = DataLoader(db_path)
    result = loader.export_to_csv(file_path, filters if filters else None)
    loader.close()
    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 TEST DEL MÓDULO DATA_LOADER v2")
    print("="*60)
    
    loader = DataLoader()
    
    # Estadísticas actuales
    stats = loader.get_import_stats()
    print(f"\n📊 Estado actual de la base de datos:")
    print(f"   Transacciones: {stats['total_transactions']}")
    print(f"   Tickers únicos: {stats['unique_tickers']}")
    
    # Test: Verificar campos nuevos
    print("\n📋 Verificando campos importados...")
    
    transactions = loader.db.get_transactions(limit=5)
    if transactions:
        print(f"   Primeras {len(transactions)} transacciones:")
        for t in transactions:
            currency = t.currency or 'N/A'
            market = t.market or 'N/A'
            rgain = f"{t.realized_gain_eur:+.2f}€" if t.realized_gain_eur else 'N/A'
            print(f"   {t.date} {t.type:4} {t.ticker[:15]:<15} | {currency} | {market} | B/P: {rgain}")
    else:
        print("   No hay transacciones")
    
    loader.close()
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETADO")
    print("="*60 + "\n")
