"""
Módulo de carga e importación de datos
Permite importar transacciones desde CSV/Excel y exportar datos
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Añadir directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.database import Database
from config import EXPORTS_DIR, TRANSACTION_TYPES


class DataLoader:
    """
    Clase para importar y exportar datos de transacciones
    Soporta CSV y Excel con validación y mapeo flexible de columnas
    """
    
    def __init__(self):
        """Inicializa el cargador de datos"""
        self.db = Database()
        
        # Columnas esperadas (nombres estándar)
        self.expected_columns = [
            'date', 'type', 'ticker', 'name', 'asset_type',
            'quantity', 'price', 'commission', 'notes'
        ]
        
        # Columnas obligatorias (mínimo necesario)
        self.required_columns = ['date', 'type', 'ticker', 'quantity', 'price']
    
    # ==========================================
    # IMPORTACIÓN
    # ==========================================
    
    def import_from_csv(self, file_path, column_mapping=None, validate=True, 
                        skip_duplicates=True, delimiter=','):
        """
        Importa transacciones desde archivo CSV
        
        Args:
            file_path: Ruta al archivo CSV
            column_mapping: Dict para mapear nombres de columnas personalizados
                Ejemplo: {'Fecha': 'date', 'Operación': 'type', 'Ticker': 'ticker'}
            validate: Si True, valida datos antes de importar
            skip_duplicates: Si True, omite transacciones duplicadas
            delimiter: Separador del CSV (por defecto ',')
        
        Returns:
            Dict con resultados:
            {
                'success': int,           # Registros importados
                'errors': List[str],      # Errores encontrados
                'skipped': int,          # Duplicados omitidos
                'total_processed': int   # Total procesado
            }
        """
        print(f"\n📥 Importando desde CSV: {file_path}")
        
        # Verificar que el archivo existe
        file_path = Path(file_path)
        if not file_path.exists():
            return {
                'success': 0,
                'errors': [f"Archivo no encontrado: {file_path}"],
                'skipped': 0,
                'total_processed': 0
            }
        
        try:
            # Leer CSV
            df = pd.read_csv(file_path, delimiter=delimiter)
            print(f"   📊 Leídas {len(df)} filas del CSV")
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping:
                df = df.rename(columns=column_mapping)
                print(f"   🔄 Aplicado mapeo de columnas")
            
            # Procesar DataFrame
            return self._process_dataframe(df, validate, skip_duplicates)
            
        except Exception as e:
            return {
                'success': 0,
                'errors': [f"Error al leer CSV: {str(e)}"],
                'skipped': 0,
                'total_processed': 0
            }
    
    def import_from_excel(self, file_path, sheet_name=0, column_mapping=None, 
                         validate=True, skip_duplicates=True):
        """
        Importa transacciones desde archivo Excel
        
        Args:
            file_path: Ruta al archivo Excel
            sheet_name: Nombre o índice de la hoja (0 por defecto = primera hoja)
            column_mapping: Dict para mapear columnas
            validate: Si True, valida datos
            skip_duplicates: Si True, omite duplicados
        
        Returns:
            Dict con resultados (igual que import_from_csv)
        """
        print(f"\n📥 Importando desde Excel: {file_path}")
        
        file_path = Path(file_path)
        if not file_path.exists():
            return {
                'success': 0,
                'errors': [f"Archivo no encontrado: {file_path}"],
                'skipped': 0,
                'total_processed': 0
            }
        
        try:
            # Leer Excel
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"   📊 Leídas {len(df)} filas del Excel (hoja: {sheet_name})")
            
            # Aplicar mapeo de columnas
            if column_mapping:
                df = df.rename(columns=column_mapping)
                print(f"   🔄 Aplicado mapeo de columnas")
            
            # Procesar DataFrame
            return self._process_dataframe(df, validate, skip_duplicates)
            
        except Exception as e:
            return {
                'success': 0,
                'errors': [f"Error al leer Excel: {str(e)}"],
                'skipped': 0,
                'total_processed': 0
            }
    
    def _process_dataframe(self, df, validate=True, skip_duplicates=True):
        """
        Procesa un DataFrame y guarda las transacciones en la base de datos
        
        Args:
            df: pandas DataFrame con transacciones
            validate: Si True, valida antes de guardar
            skip_duplicates: Si True, omite duplicados
        
        Returns:
            Dict con resultados de importación
        """
        results = {
            'success': 0,
            'errors': [],
            'skipped': 0,
            'total_processed': len(df)
        }
        
        # Validar estructura si está habilitado
        if validate:
            validation_errors = self._validate_dataframe(df)
            if validation_errors:
                results['errors'].extend(validation_errors)
                print(f"   ❌ Errores de validación encontrados: {len(validation_errors)}")
                return results
        
        # Normalizar columnas (minúsculas, sin espacios)
        df.columns = df.columns.str.lower().str.strip()
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            try:
                # Convertir fila a dict
                transaction_data = self._row_to_transaction(row)
                
                # Verificar duplicados si está habilitado
                if skip_duplicates and self._is_duplicate(transaction_data):
                    results['skipped'] += 1
                    continue
                
                # Guardar en base de datos
                self.db.add_transaction(transaction_data)
                results['success'] += 1
                
            except Exception as e:
                results['errors'].append(f"Fila {idx + 2}: {str(e)}")
        
        # Resumen
        print(f"\n   ✅ Importadas: {results['success']}")
        print(f"   ⏭️  Omitidas (duplicados): {results['skipped']}")
        print(f"   ❌ Errores: {len(results['errors'])}")
        
        return results
    
    def _validate_dataframe(self, df):
        """
        Valida que el DataFrame tenga la estructura correcta
        
        Returns:
            Lista de errores (vacía si todo está bien)
        """
        errors = []
        
        # Normalizar nombres de columnas para la validación
        df_columns = df.columns.str.lower().str.strip()
        
        # Verificar columnas obligatorias
        for col in self.required_columns:
            if col not in df_columns:
                errors.append(f"Columna obligatoria faltante: '{col}'")
        
        if errors:
            return errors
        
        # Validar tipos de datos básicos
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 porque Excel empieza en 1 y tiene header
            
            # Validar fecha
            try:
                date_val = row.get('date', row.get('fecha', None))
                if pd.isna(date_val):
                    errors.append(f"Fila {row_num}: Fecha vacía")
            except:
                errors.append(f"Fila {row_num}: Fecha inválida")
            
            # Validar quantity
            try:
                qty = float(row.get('quantity', row.get('cantidad', 0)))
                if qty <= 0:
                    errors.append(f"Fila {row_num}: Cantidad debe ser > 0")
            except:
                errors.append(f"Fila {row_num}: Cantidad inválida")
            
            # Validar price
            try:
                price = float(row.get('price', row.get('precio', 0)))
                if price <= 0:
                    errors.append(f"Fila {row_num}: Precio debe ser > 0")
            except:
                errors.append(f"Fila {row_num}: Precio inválido")
            
            # Detener si hay muchos errores (para no saturar)
            if len(errors) > 10:
                errors.append("... (más errores omitidos)")
                break
        
        return errors
    
    def _row_to_transaction(self, row):
        """
        Convierte una fila de DataFrame a dict de transacción
        
        Args:
            row: pandas Series (fila del DataFrame)
        
        Returns:
            Dict con datos de transacción
        """
        # Función auxiliar para obtener valor (maneja diferentes nombres)
        def get_value(row, *possible_names, default=None):
            for name in possible_names:
                if name in row and not pd.isna(row[name]):
                    return row[name]
            return default
        
        # Parsear fecha
        date_val = get_value(row, 'date', 'fecha')
        if isinstance(date_val, str):
            # Intentar diferentes formatos
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_val = datetime.strptime(date_val, fmt).date()
                    break
                except:
                    continue
        elif isinstance(date_val, datetime):
            date_val = date_val.date()
        
        # Construir dict de transacción
        transaction = {
            'date': date_val,
            'type': get_value(row, 'type', 'tipo', 'operacion', default='buy').lower(),
            'ticker': get_value(row, 'ticker', 'simbolo', default='').upper(),
            'name': get_value(row, 'name', 'nombre'),
            'asset_type': get_value(row, 'asset_type', 'tipo_activo'),
            'quantity': float(get_value(row, 'quantity', 'cantidad', default=0)),
            'price': float(get_value(row, 'price', 'precio', default=0)),
            'commission': float(get_value(row, 'commission', 'comision', default=0)),
            'notes': get_value(row, 'notes', 'notas')
        }
        
        # Limpiar valores None
        transaction = {k: v for k, v in transaction.items() if v is not None}
        
        return transaction
    
    def _is_duplicate(self, transaction_data):
        """
        Verifica si una transacción ya existe en la base de datos
        
        Criterio de duplicado: misma fecha, tipo, ticker y cantidad
        """
        existing = self.db.get_transactions(
            type=transaction_data['type'],
            ticker=transaction_data['ticker']
        )
        
        for trans in existing:
            if (trans.date == transaction_data['date'] and 
                trans.quantity == transaction_data['quantity'] and
                trans.price == transaction_data['price']):
                return True
        
        return False
    
    # ==========================================
    # VALIDACIÓN
    # ==========================================
    
    def validate_file(self, file_path, file_type='csv'):
        """
        Valida un archivo sin importarlo (modo dry-run)
        
        Args:
            file_path: Ruta al archivo
            file_type: 'csv' o 'excel'
        
        Returns:
            Dict con resultados de validación:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'rows': int
            }
        """
        print(f"\n🔍 Validando archivo: {file_path}")
        
        try:
            # Leer archivo
            if file_type == 'csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Validar estructura
            errors = self._validate_dataframe(df)
            
            # Advertencias (no críticas)
            warnings = []
            
            # Verificar columnas opcionales faltantes
            optional_cols = ['name', 'asset_type', 'notes']
            for col in optional_cols:
                if col not in df.columns:
                    warnings.append(f"Columna opcional '{col}' no encontrada")
            
            result = {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'rows': len(df)
            }
            
            if result['valid']:
                print(f"   ✅ Archivo válido: {result['rows']} filas")
            else:
                print(f"   ❌ Archivo inválido: {len(errors)} errores")
            
            return result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Error al leer archivo: {str(e)}"],
                'warnings': [],
                'rows': 0
            }
    
    # ==========================================
    # EXPORTACIÓN
    # ==========================================
    
    def export_to_csv(self, output_path=None, filters=None):
        """
        Exporta transacciones a CSV
        
        Args:
            output_path: Ruta del archivo de salida (auto-genera si es None)
            filters: Dict con filtros (igual que db.get_transactions)
        
        Returns:
            Ruta del archivo generado
        """
        # Generar nombre de archivo si no se proporciona
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = EXPORTS_DIR / f'transactions_{timestamp}.csv'
        else:
            output_path = Path(output_path)
        
        # Obtener transacciones
        if filters:
            transactions = self.db.get_transactions(**filters)
        else:
            transactions = self.db.get_transactions()
        
        # Convertir a DataFrame
        df = self.db.transactions_to_dataframe(transactions)
        
        # Guardar CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"✅ {len(df)} transacciones exportadas a: {output_path}")
        return output_path
    
    def export_to_excel(self, output_path=None, include_summary=True, filters=None):
        """
        Exporta transacciones a Excel (puede incluir múltiples hojas)
        
        Args:
            output_path: Ruta del archivo de salida
            include_summary: Si True, añade hoja con resumen
            filters: Dict con filtros
        
        Returns:
            Ruta del archivo generado
        """
        # Generar nombre de archivo si no se proporciona
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = EXPORTS_DIR / f'portfolio_export_{timestamp}.xlsx'
        else:
            output_path = Path(output_path)
        
        # Obtener datos
        if filters:
            transactions = self.db.get_transactions(**filters)
        else:
            transactions = self.db.get_transactions()
        
        df_trans = self.db.transactions_to_dataframe(transactions)
        
        # Crear Excel con múltiples hojas
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Hoja 1: Transacciones
            df_trans.to_excel(writer, sheet_name='Transacciones', index=False)
            
            # Hoja 2: Resumen (si está habilitado)
            if include_summary:
                summary_data = {
                    'Total Transacciones': [len(df_trans)],
                    'Compras': [len(df_trans[df_trans['type'] == 'buy'])],
                    'Ventas': [len(df_trans[df_trans['type'] == 'sell'])],
                    'Tickers Únicos': [df_trans['ticker'].nunique()],
                    'Fecha Primera Operación': [df_trans['date'].min()],
                    'Fecha Última Operación': [df_trans['date'].max()]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja 3: Dividendos
            dividends = self.db.get_dividends()
            if dividends:
                df_divs = self.db.dividends_to_dataframe(dividends)
                df_divs.to_excel(writer, sheet_name='Dividendos', index=False)
        
        print(f"✅ Exportado a Excel: {output_path}")
        print(f"   📊 {len(df_trans)} transacciones")
        if include_summary:
            print(f"   📋 Incluye hoja de resumen")
        
        return output_path
    
    def export_template_csv(self, output_path=None):
        """
        Genera un archivo CSV de plantilla con las columnas correctas
        Útil para que el usuario vea el formato esperado
        
        Returns:
            Ruta del archivo generado
        """
        if output_path is None:
            output_path = EXPORTS_DIR / 'template_transactions.csv'
        else:
            output_path = Path(output_path)
        
        # Crear DataFrame de ejemplo
        template_data = {
            'date': ['2024-01-15', '2024-03-20'],
            'type': ['buy', 'sell'],
            'ticker': ['TEF', 'BBVA'],
            'name': ['Telefónica SA', 'Banco BBVA'],
            'asset_type': ['accion', 'accion'],
            'quantity': [100, 50],
            'price': [4.20, 9.50],
            'commission': [10.0, 8.5],
            'notes': ['Primera compra', 'Venta parcial']
        }
        
        df = pd.DataFrame(template_data)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"✅ Plantilla CSV generada: {output_path}")
        return output_path
    
    def close(self):
        """Cierra conexión a la base de datos"""
        self.db.close()


# ==========================================
# FUNCIÓN DE PRUEBA
# ==========================================

def test_data_loader():
    """Función de prueba para el data loader"""
    print("\n" + "="*60)
    print("🧪 PROBANDO DATA LOADER")
    print("="*60 + "\n")
    
    loader = DataLoader()
    
    # 1. Generar plantilla
    print("1️⃣ Generando plantilla CSV...")
    template_path = loader.export_template_csv()
    
    # 2. Importar desde la plantilla
    print("\n2️⃣ Importando desde plantilla...")
    result = loader.import_from_csv(template_path)
    
    print(f"\nResultado de importación:")
    print(f"   ✅ Éxitos: {result['success']}")
    print(f"   ⏭️  Omitidos: {result['skipped']}")
    print(f"   ❌ Errores: {len(result['errors'])}")
    
    # 3. Exportar a Excel
    print("\n3️⃣ Exportando a Excel...")
    excel_path = loader.export_to_excel(include_summary=True)
    
    print("\n" + "="*60)
    print("✅ TESTS COMPLETADOS")
    print("="*60 + "\n")
    
    loader.close()


if __name__ == '__main__':
    test_data_loader()