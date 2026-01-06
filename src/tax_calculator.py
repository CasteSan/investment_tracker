"""
Tax Calculator Module - Gestión Fiscal de Inversiones
Sesión 4 del Investment Tracker (actualizado en Sesión 7)

Este módulo gestiona:
- Cálculo de plusvalías/minusvalías con FIFO (o LIFO)
- Asignación de lotes a ventas
- Informes fiscales anuales para la declaración de la renta
- Simulación de impacto fiscal antes de vender
- Detección de regla antiaplicación (2 meses)
- Cálculo de impuestos según tramos IRPF del ahorro
- TRASPASOS entre fondos (sin generar fiscalidad, manteniendo coste fiscal)

IMPORTANTE - Fiscalidad de traspasos en España:
- Los traspasos entre fondos de inversión NO generan plusvalía/minusvalía
- El coste fiscal se TRANSFIERE del fondo origen al fondo destino
- Solo al vender (reembolso) del fondo destino se calcula la plusvalía
- Se usa el coste fiscal ORIGINAL, no el valor de mercado del traspaso

Autor: Investment Tracker Project
Fecha: Enero 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
from collections import defaultdict

try:
    from src.database import Database
    from src.logger import get_logger
except ImportError:
    from database import Database
    from logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# CONFIGURACIÓN FISCAL ESPAÑA
# =============================================================================

# Tramos IRPF del ahorro 2024/2025 (España)
TRAMOS_IRPF_AHORRO = [
    (6000, 0.19),       # Hasta 6.000€: 19%
    (50000, 0.21),      # De 6.000€ a 50.000€: 21%
    (200000, 0.23),     # De 50.000€ a 200.000€: 23%
    (300000, 0.27),     # De 200.000€ a 300.000€: 27%
    (float('inf'), 0.28)  # Más de 300.000€: 28%
]

# Período de la regla antiaplicación (wash sale rule)
WASH_SALE_DAYS = 60  # 2 meses = ~60 días


class TaxCalculator:
    """
    Calculadora fiscal para inversiones.
    
    Gestiona el cálculo de plusvalías usando FIFO (o LIFO), genera informes
    fiscales y permite simular el impacto fiscal de ventas futuras.
    
    Uso básico:
        tax = TaxCalculator()
        
        # Ver lotes disponibles de un activo
        lotes = tax.get_available_lots('TEF')
        
        # Informe fiscal del año
        informe = tax.get_fiscal_year_summary(2025)
        
        # Simular una venta
        simulacion = tax.simulate_sale('TEF', 100, 4.50)
        
        # Exportar a Excel
        tax.export_fiscal_report(2025, 'informe_fiscal_2025.xlsx')
        
        tax.close()
    """
    
    def __init__(self, method: str = 'FIFO', db_path: str = None):
        """
        Inicializa el calculador fiscal.
        
        Args:
            method: Método de asignación de lotes ('FIFO' o 'LIFO')
            db_path: Ruta a la base de datos (opcional)
        """
        self.method = method.upper()
        if self.method not in ['FIFO', 'LIFO']:
            raise ValueError("Método debe ser 'FIFO' o 'LIFO'")
        
        logger.debug(f"Inicializando TaxCalculator con método {self.method}")
        self.db = Database(db_path) if db_path else Database()
        logger.info(f"TaxCalculator inicializado (método: {self.method})")
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()
        logger.debug("TaxCalculator cerrado")
    
    # =========================================================================
    # GESTIÓN DE LOTES
    # =========================================================================
    
    def get_available_lots(self, ticker: str) -> List[Dict]:
        """
        Obtiene los lotes de compra disponibles (no vendidos) de un ticker.
        
        Usa FIFO para determinar qué lotes quedan después de las ventas.
        
        IMPORTANTE - Manejo de traspasos (fiscalidad española):
        - transfer_out: Sale del fondo origen, reduce lotes (como venta pero SIN plusvalía)
        - transfer_in: Entra al fondo destino con el COSTE FISCAL ORIGINAL (no precio de mercado)
        
        Args:
            ticker: Símbolo del activo
        
        Returns:
            Lista de lotes disponibles, cada uno con:
            - date: Fecha de compra (o de transfer_in)
            - quantity: Cantidad restante
            - price: Precio unitario para cálculo fiscal (coste_basis / cantidad)
            - cost: Coste total del lote (coste fiscal)
            - days_held: Días desde la compra original
            - original_quantity: Cantidad original
            - is_transfer: True si viene de un traspaso
            - original_purchase_date: Fecha de compra original (para traspasos)
        """
        transactions = self.db.get_transactions(ticker=ticker)
        
        if not transactions:
            return []
        
        # Convertir a lista de dicts y ordenar por fecha
        trans_list = []
        for t in transactions:
            trans_list.append({
                'date': t.date if isinstance(t.date, datetime) else datetime.strptime(str(t.date), '%Y-%m-%d'),
                'type': t.type,
                'quantity': float(t.quantity),
                'price': float(t.price),
                'name': t.name,
                'cost_basis_eur': float(t.cost_basis_eur) if t.cost_basis_eur else None,
                'notes': t.notes or ''
            })
        
        trans_list.sort(key=lambda x: x['date'])
        
        # Construir lotes aplicando FIFO
        lots = []
        
        for trans in trans_list:
            if trans['type'] == 'buy':
                # Compra normal
                lots.append({
                    'date': trans['date'],
                    'quantity': trans['quantity'],
                    'original_quantity': trans['quantity'],
                    'price': trans['price'],
                    'cost': trans['quantity'] * trans['price'],
                    'name': trans['name'],
                    'is_transfer': False,
                    'original_purchase_date': trans['date']
                })
            
            elif trans['type'] == 'transfer_in':
                # Traspaso entrante: usar COSTE FISCAL, no precio de mercado
                if trans['cost_basis_eur'] and trans['cost_basis_eur'] > 0:
                    # Usar el coste fiscal proporcionado
                    cost_basis = trans['cost_basis_eur']
                    fiscal_price = cost_basis / trans['quantity']
                else:
                    # Fallback: intentar extraer de las notas (compatibilidad)
                    cost_basis = self._extract_cost_basis_from_notes(trans['notes'], trans['quantity'], trans['price'])
                    fiscal_price = cost_basis / trans['quantity'] if trans['quantity'] > 0 else trans['price']
                
                # Para la fecha original, intentamos extraerla de las notas o usamos la fecha del traspaso
                original_date = self._extract_original_date_from_notes(trans['notes']) or trans['date']
                
                lots.append({
                    'date': trans['date'],  # Fecha del traspaso
                    'quantity': trans['quantity'],
                    'original_quantity': trans['quantity'],
                    'price': fiscal_price,  # Precio fiscal (coste/cantidad)
                    'cost': cost_basis,  # Coste fiscal heredado
                    'name': trans['name'],
                    'is_transfer': True,
                    'original_purchase_date': original_date  # Fecha de compra original
                })
            
            elif trans['type'] == 'sell':
                # Venta: reduce lotes según FIFO/LIFO
                qty_to_sell = trans['quantity']
                
                if self.method == 'FIFO':
                    for lot in lots:
                        if qty_to_sell <= 0:
                            break
                        if lot['quantity'] > 0:
                            sell_from_lot = min(lot['quantity'], qty_to_sell)
                            lot['quantity'] -= sell_from_lot
                            lot['cost'] = lot['quantity'] * lot['price']
                            qty_to_sell -= sell_from_lot
                else:  # LIFO
                    for lot in reversed(lots):
                        if qty_to_sell <= 0:
                            break
                        if lot['quantity'] > 0:
                            sell_from_lot = min(lot['quantity'], qty_to_sell)
                            lot['quantity'] -= sell_from_lot
                            lot['cost'] = lot['quantity'] * lot['price']
                            qty_to_sell -= sell_from_lot
            
            elif trans['type'] == 'transfer_out':
                # Traspaso saliente: reduce lotes (como venta, pero SIN generar plusvalía)
                qty_to_transfer = trans['quantity']
                
                if self.method == 'FIFO':
                    for lot in lots:
                        if qty_to_transfer <= 0:
                            break
                        if lot['quantity'] > 0:
                            transfer_from_lot = min(lot['quantity'], qty_to_transfer)
                            lot['quantity'] -= transfer_from_lot
                            lot['cost'] = lot['quantity'] * lot['price']
                            qty_to_transfer -= transfer_from_lot
                else:  # LIFO
                    for lot in reversed(lots):
                        if qty_to_transfer <= 0:
                            break
                        if lot['quantity'] > 0:
                            transfer_from_lot = min(lot['quantity'], qty_to_transfer)
                            lot['quantity'] -= transfer_from_lot
                            lot['cost'] = lot['quantity'] * lot['price']
                            qty_to_transfer -= transfer_from_lot
        
        # Filtrar lotes con cantidad > 0 y añadir días de tenencia
        today = datetime.now()
        available_lots = []
        
        for lot in lots:
            if lot['quantity'] > 0.0001:  # Tolerancia para decimales
                # Para días de tenencia, usar la fecha de compra ORIGINAL
                original_date = lot.get('original_purchase_date', lot['date'])
                if isinstance(original_date, str):
                    original_date = datetime.strptime(original_date, '%Y-%m-%d')
                
                lot['days_held'] = (today - original_date).days
                lot['date'] = lot['date'].strftime('%Y-%m-%d') if isinstance(lot['date'], datetime) else lot['date']
                lot['original_purchase_date'] = original_date.strftime('%Y-%m-%d') if isinstance(original_date, datetime) else original_date
                available_lots.append(lot)
        
        return available_lots
    
    def _extract_cost_basis_from_notes(self, notes: str, quantity: float, price: float) -> float:
        """
        Extrae el coste fiscal de las notas (compatibilidad con datos antiguos).
        
        Busca patrones como "Coste fiscal: 1234.56€"
        
        Args:
            notes: Notas de la transacción
            quantity: Cantidad de participaciones
            price: Precio de mercado (fallback)
        
        Returns:
            Coste fiscal extraído o calculado
        """
        import re
        
        if not notes:
            return quantity * price
        
        # Buscar patrón "Coste fiscal: X€" o "Coste fiscal: X"
        pattern = r'[Cc]oste\s+fiscal:\s*([\d.,]+)\s*€?'
        match = re.search(pattern, notes)
        
        if match:
            try:
                cost_str = match.group(1).replace(',', '.')
                return float(cost_str)
            except ValueError:
                pass
        
        # Fallback: usar precio de mercado
        return quantity * price
    
    def _extract_original_date_from_notes(self, notes: str) -> Optional[datetime]:
        """
        Extrae la fecha de compra original de las notas (si está disponible).
        
        Args:
            notes: Notas de la transacción
        
        Returns:
            Fecha original o None
        """
        import re
        
        if not notes:
            return None
        
        # Buscar patrón "Fecha original: YYYY-MM-DD"
        pattern = r'[Ff]echa\s+original:\s*(\d{4}-\d{2}-\d{2})'
        match = re.search(pattern, notes)
        
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d')
            except ValueError:
                pass
        
        return None
    
    def get_all_available_lots(self) -> pd.DataFrame:
        """
        Obtiene todos los lotes disponibles de todos los tickers.
        
        Returns:
            DataFrame con todos los lotes, incluyendo ticker
        """
        # Obtener todos los tickers con posiciones
        transactions = self.db.get_transactions()
        
        if not transactions:
            return pd.DataFrame()
        
        # Calcular posiciones actuales por ticker
        positions = defaultdict(float)
        for t in transactions:
            if t.type == 'buy':
                positions[t.ticker] += t.quantity
            elif t.type == 'sell':
                positions[t.ticker] -= t.quantity
        
        # Filtrar tickers con posición > 0
        active_tickers = [ticker for ticker, qty in positions.items() if qty > 0.0001]
        
        # Obtener lotes de cada ticker
        all_lots = []
        for ticker in active_tickers:
            lots = self.get_available_lots(ticker)
            for lot in lots:
                lot['ticker'] = ticker
                all_lots.append(lot)
        
        if not all_lots:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_lots)
        
        # Reordenar columnas
        cols = ['ticker', 'name', 'date', 'quantity', 'original_quantity', 'price', 'cost', 'days_held']
        df = df[[c for c in cols if c in df.columns]]
        
        return df.sort_values(['ticker', 'date']).reset_index(drop=True)
    
    # =========================================================================
    # ASIGNACIÓN DE LOTES A VENTAS
    # =========================================================================
    
    def assign_lots_to_sale(self, 
                           ticker: str, 
                           quantity: float, 
                           sale_date: Union[str, datetime] = None) -> List[Dict]:
        """
        Asigna lotes de compra a una venta según FIFO/LIFO.
        
        Args:
            ticker: Símbolo del activo
            quantity: Cantidad a vender
            sale_date: Fecha de la venta (para calcular días de tenencia)
        
        Returns:
            Lista de lotes asignados, cada uno con:
            - lot_date: Fecha del lote
            - quantity_from_lot: Cantidad vendida de este lote
            - purchase_price: Precio de compra
            - cost_basis: Coste de adquisición de la parte vendida
            - days_held: Días de tenencia
        """
        if sale_date is None:
            sale_date = datetime.now()
        elif isinstance(sale_date, str):
            sale_date = datetime.strptime(sale_date, '%Y-%m-%d')
        
        # Obtener lotes disponibles
        lots = self.get_available_lots(ticker)
        
        if not lots:
            return []
        
        assigned = []
        qty_to_assign = quantity
        
        # Ordenar según método
        if self.method == 'LIFO':
            lots = list(reversed(lots))
        
        for lot in lots:
            if qty_to_assign <= 0:
                break
            
            lot_date = datetime.strptime(lot['date'], '%Y-%m-%d')
            available = lot['quantity']
            
            if available > 0:
                qty_from_lot = min(available, qty_to_assign)
                
                assigned.append({
                    'lot_date': lot['date'],
                    'quantity_from_lot': qty_from_lot,
                    'purchase_price': lot['price'],
                    'cost_basis': qty_from_lot * lot['price'],
                    'days_held': (sale_date - lot_date).days
                })
                
                qty_to_assign -= qty_from_lot
        
        return assigned
    
    # =========================================================================
    # CÁLCULO DE PLUSVALÍAS
    # =========================================================================
    
    def calculate_sale_gain(self, 
                           ticker: str,
                           quantity: float,
                           sale_price: float,
                           sale_date: Union[str, datetime] = None,
                           commission: float = 0.0) -> Dict:
        """
        Calcula la plusvalía/minusvalía de una venta.
        
        Args:
            ticker: Símbolo del activo
            quantity: Cantidad vendida
            sale_price: Precio de venta unitario
            sale_date: Fecha de la venta
            commission: Comisión de la venta
        
        Returns:
            Dict con:
            - gross_proceeds: Ingresos brutos (qty * price)
            - net_proceeds: Ingresos netos (menos comisión)
            - cost_basis: Coste de adquisición
            - gain: Ganancia/pérdida
            - gain_pct: Porcentaje de ganancia
            - lots_used: Lotes asignados a la venta
            - is_short_term: Si algún lote tiene < 1 año
        """
        if sale_date is None:
            sale_date = datetime.now()
        elif isinstance(sale_date, str):
            sale_date = datetime.strptime(sale_date, '%Y-%m-%d')
        
        # Asignar lotes
        lots_used = self.assign_lots_to_sale(ticker, quantity, sale_date)
        
        if not lots_used:
            return {
                'gross_proceeds': 0,
                'net_proceeds': 0,
                'cost_basis': 0,
                'gain': 0,
                'gain_pct': 0,
                'lots_used': [],
                'is_short_term': False,
                'error': f'No hay lotes disponibles para {ticker}'
            }
        
        # Calcular totales
        gross_proceeds = quantity * sale_price
        net_proceeds = gross_proceeds - commission
        cost_basis = sum(lot['cost_basis'] for lot in lots_used)
        gain = net_proceeds - cost_basis
        gain_pct = (gain / cost_basis * 100) if cost_basis > 0 else 0
        
        # Verificar si es corto plazo (< 1 año)
        is_short_term = any(lot['days_held'] < 365 for lot in lots_used)
        
        return {
            'gross_proceeds': round(gross_proceeds, 2),
            'net_proceeds': round(net_proceeds, 2),
            'cost_basis': round(cost_basis, 2),
            'gain': round(gain, 2),
            'gain_pct': round(gain_pct, 2),
            'lots_used': lots_used,
            'is_short_term': is_short_term
        }
    
    # =========================================================================
    # REGLA ANTIAPLICACIÓN (WASH SALE - 2 MESES)
    # =========================================================================
    
    def check_wash_sale(self, ticker: str, sale_date: Union[str, datetime]) -> Dict:
        """
        Verifica si una venta con pérdidas está afectada por la regla
        de los 2 meses (antiaplicación).
        
        En España, si vendes con pérdidas y recompras el mismo activo
        en los 2 meses anteriores o posteriores, NO puedes deducir
        la pérdida fiscalmente.
        
        Args:
            ticker: Símbolo del activo
            sale_date: Fecha de la venta
        
        Returns:
            Dict con:
            - is_wash_sale: True si aplica la regla
            - blocking_purchases: Lista de compras que bloquean la deducción
            - message: Explicación
        """
        if isinstance(sale_date, str):
            sale_date = datetime.strptime(sale_date, '%Y-%m-%d')
        
        # Rango de 2 meses antes y después
        start_window = sale_date - timedelta(days=WASH_SALE_DAYS)
        end_window = sale_date + timedelta(days=WASH_SALE_DAYS)
        
        # Buscar compras en ese rango
        transactions = self.db.get_transactions(ticker=ticker, type='buy')
        
        blocking_purchases = []
        
        for t in transactions:
            t_date = t.date if isinstance(t.date, datetime) else datetime.strptime(str(t.date), '%Y-%m-%d')
            
            # Excluir la compra original (antes de la venta)
            if t_date < sale_date - timedelta(days=WASH_SALE_DAYS):
                continue
            
            # Si hay compra en el rango (excluyendo el mismo día de venta hacia atrás)
            if start_window <= t_date <= end_window and t_date != sale_date:
                blocking_purchases.append({
                    'date': t_date.strftime('%Y-%m-%d'),
                    'quantity': t.quantity,
                    'price': t.price,
                    'days_from_sale': (t_date - sale_date).days
                })
        
        is_wash_sale = len(blocking_purchases) > 0
        
        if is_wash_sale:
            message = (f"⚠️ REGLA 2 MESES: Hay {len(blocking_purchases)} compra(s) de {ticker} "
                      f"dentro de los 2 meses de la venta. Si la venta genera pérdidas, "
                      f"NO podrás deducirlas fiscalmente.")
        else:
            message = f"✅ No hay compras de {ticker} en los 2 meses alrededor de la venta."
        
        return {
            'is_wash_sale': is_wash_sale,
            'blocking_purchases': blocking_purchases,
            'message': message
        }
    
    def get_wash_sales_in_year(self, year: int) -> pd.DataFrame:
        """
        Identifica todas las ventas del año que podrían estar afectadas
        por la regla de los 2 meses.
        
        Args:
            year: Año fiscal
        
        Returns:
            DataFrame con ventas potencialmente afectadas
        """
        # Obtener todas las ventas del año
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        sales = self.db.get_transactions(
            type='sell',
            start_date=start_date,
            end_date=end_date
        )
        
        if not sales:
            return pd.DataFrame()
        
        wash_sales = []
        
        for sale in sales:
            sale_date = sale.date if isinstance(sale.date, datetime) else datetime.strptime(str(sale.date), '%Y-%m-%d')
            
            # Verificar si tiene pérdida
            gain = sale.realized_gain_eur if sale.realized_gain_eur else 0
            
            if gain < 0:  # Solo nos preocupan las pérdidas
                wash_check = self.check_wash_sale(sale.ticker, sale_date)
                
                if wash_check['is_wash_sale']:
                    wash_sales.append({
                        'date': sale_date.strftime('%Y-%m-%d'),
                        'ticker': sale.ticker,
                        'name': sale.name,
                        'quantity': sale.quantity,
                        'loss': gain,
                        'blocking_purchases': len(wash_check['blocking_purchases']),
                        'deductible': False
                    })
        
        return pd.DataFrame(wash_sales)
    
    # =========================================================================
    # INFORMES FISCALES ANUALES
    # =========================================================================
    
    def get_fiscal_year_summary(self, year: int) -> Dict:
        """
        Genera un resumen fiscal del año.
        
        Args:
            year: Año fiscal
        
        Returns:
            Dict con resumen completo
        """
        detail = self.get_fiscal_year_detail(year)
        
        if detail.empty:
            return {
                'year': year,
                'total_sales': 0,
                'total_gains': 0,
                'total_losses': 0,
                'net_gain': 0,
                'tax_base': 0,
                'estimated_tax': 0,
                'wash_sales_loss': 0,
                'deductible_loss': 0,
                'by_quarter': {},
                'by_asset_type': {}
            }
        
        # Totales
        gains = detail[detail['gain_eur'] > 0]['gain_eur'].sum()
        losses = detail[detail['gain_eur'] < 0]['gain_eur'].sum()
        net_gain = gains + losses
        
        # Verificar wash sales
        wash_sales = self.get_wash_sales_in_year(year)
        wash_sales_loss = wash_sales['loss'].sum() if not wash_sales.empty else 0
        
        # Pérdidas deducibles (excluyendo wash sales)
        deductible_loss = losses - wash_sales_loss
        
        # Base imponible ajustada
        tax_base = gains + deductible_loss
        
        # Calcular impuesto
        if tax_base > 0:
            tax_info = self.calculate_tax(tax_base)
            estimated_tax = tax_info['total_tax']
        else:
            estimated_tax = 0
        
        # Por trimestre
        detail['quarter'] = pd.to_datetime(detail['sale_date']).dt.quarter
        by_quarter = detail.groupby('quarter')['gain_eur'].sum().to_dict()
        
        # Por tipo de activo
        if 'asset_type' in detail.columns:
            by_asset_type = detail.groupby('asset_type')['gain_eur'].sum().to_dict()
        else:
            by_asset_type = {}
        
        return {
            'year': year,
            'total_sales': len(detail),
            'total_gains': round(gains, 2),
            'total_losses': round(losses, 2),
            'net_gain': round(net_gain, 2),
            'wash_sales_loss': round(wash_sales_loss, 2),
            'deductible_loss': round(deductible_loss, 2),
            'tax_base': round(tax_base, 2),
            'estimated_tax': round(estimated_tax, 2),
            'by_quarter': {f'Q{k}': round(v, 2) for k, v in by_quarter.items()},
            'by_asset_type': {k: round(v, 2) for k, v in by_asset_type.items()}
        }
    
    def get_fiscal_year_detail(self, year: int) -> pd.DataFrame:
        """
        Genera el detalle de todas las ventas del año fiscal.
        
        Args:
            year: Año fiscal
        
        Returns:
            DataFrame con detalle de cada venta
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        # Obtener ventas del año
        sales = self.db.get_transactions(
            type='sell',
            start_date=start_date,
            end_date=end_date
        )
        
        if not sales:
            return pd.DataFrame()
        
        # Construir detalle
        details = []
        
        for sale in sales:
            sale_date = sale.date if isinstance(sale.date, datetime) else datetime.strptime(str(sale.date), '%Y-%m-%d')
            
            # Usar realized_gain_eur si está disponible
            if sale.realized_gain_eur is not None:
                gain = sale.realized_gain_eur
            else:
                # Calcular manualmente (menos preciso para multi-divisa)
                calc = self.calculate_sale_gain(
                    sale.ticker,
                    sale.quantity,
                    sale.price,
                    sale_date
                )
                gain = calc['gain']
            
            # Obtener información del lote de compra (aproximación)
            lots = self.assign_lots_to_sale(sale.ticker, sale.quantity, sale_date)
            
            if lots:
                purchase_date = lots[0]['lot_date']
                purchase_price = sum(l['cost_basis'] for l in lots) / sale.quantity if sale.quantity > 0 else 0
                days_held = lots[0]['days_held']
            else:
                purchase_date = 'N/A'
                purchase_price = 0
                days_held = 0
            
            details.append({
                'sale_date': sale_date.strftime('%Y-%m-%d'),
                'ticker': sale.ticker,
                'name': sale.name or sale.ticker,
                'asset_type': sale.asset_type or 'unknown',
                'quantity': sale.quantity,
                'purchase_date': purchase_date,
                'purchase_price_avg': round(purchase_price, 4),
                'sale_price': sale.price,
                'currency': sale.currency or 'EUR',
                'days_held': days_held,
                'cost_basis': round(purchase_price * sale.quantity, 2),
                'sale_proceeds': round(sale.quantity * sale.price, 2),
                'gain_eur': round(gain, 2),
                'gain_pct': round((gain / (purchase_price * sale.quantity) * 100) if purchase_price > 0 else 0, 2)
            })
        
        df = pd.DataFrame(details)
        df = df.sort_values('sale_date', ascending=False)
        
        return df.reset_index(drop=True)
    
    # =========================================================================
    # CÁLCULO DE IMPUESTOS
    # =========================================================================
    
    def calculate_tax(self, taxable_base: float) -> Dict:
        """
        Calcula el impuesto a pagar según los tramos del IRPF del ahorro.
        
        Args:
            taxable_base: Base imponible (ganancias - pérdidas deducibles)
        
        Returns:
            Dict con desglose del impuesto por tramos
        """
        if taxable_base <= 0:
            return {
                'taxable_base': round(taxable_base, 2),
                'total_tax': 0,
                'effective_rate': 0,
                'breakdown': [],
                'losses_to_offset': round(abs(taxable_base), 2)
            }
        
        remaining = taxable_base
        total_tax = 0
        breakdown = []
        prev_limit = 0
        
        for limit, rate in TRAMOS_IRPF_AHORRO:
            if remaining <= 0:
                break
            
            bracket_size = limit - prev_limit
            taxable_in_bracket = min(remaining, bracket_size)
            tax_in_bracket = taxable_in_bracket * rate
            
            if taxable_in_bracket > 0:
                breakdown.append({
                    'bracket': f'{prev_limit:,.0f}€ - {limit:,.0f}€' if limit != float('inf') else f'> {prev_limit:,.0f}€',
                    'rate': f'{rate*100:.0f}%',
                    'taxable_amount': round(taxable_in_bracket, 2),
                    'tax': round(tax_in_bracket, 2)
                })
            
            total_tax += tax_in_bracket
            remaining -= taxable_in_bracket
            prev_limit = limit
        
        effective_rate = (total_tax / taxable_base * 100) if taxable_base > 0 else 0
        
        return {
            'taxable_base': round(taxable_base, 2),
            'total_tax': round(total_tax, 2),
            'effective_rate': round(effective_rate, 2),
            'breakdown': breakdown,
            'losses_to_offset': 0
        }
    
    # =========================================================================
    # SIMULACIÓN DE VENTAS
    # =========================================================================
    
    def simulate_sale(self,
                     ticker: str,
                     quantity: float,
                     estimated_price: float,
                     commission: float = 0.0) -> Dict:
        """
        Simula una venta SIN ejecutarla para ver el impacto fiscal.
        
        Args:
            ticker: Símbolo del activo
            quantity: Cantidad a vender
            estimated_price: Precio estimado de venta
            commission: Comisión estimada
        
        Returns:
            Dict con simulación completa
        """
        # Calcular ganancia
        result = self.calculate_sale_gain(
            ticker, quantity, estimated_price, 
            sale_date=datetime.now(),
            commission=commission
        )
        
        if 'error' in result:
            return result
        
        # Verificar wash sale
        wash_check = self.check_wash_sale(ticker, datetime.now())
        
        # Calcular impuesto si hay ganancia
        if result['gain'] > 0:
            tax_info = self.calculate_tax(result['gain'])
            estimated_tax = tax_info['total_tax']
            net_after_tax = result['gain'] - estimated_tax
        else:
            estimated_tax = 0
            net_after_tax = result['gain']
            
            # Si hay pérdida, verificar si es deducible
            if wash_check['is_wash_sale']:
                net_after_tax = 0  # No se puede deducir
        
        # Obtener info del activo
        lots = self.get_available_lots(ticker)
        total_available = sum(l['quantity'] for l in lots)
        
        return {
            'ticker': ticker,
            'quantity_to_sell': quantity,
            'available_quantity': total_available,
            'estimated_price': estimated_price,
            'gross_proceeds': result['gross_proceeds'],
            'cost_basis': result['cost_basis'],
            'gain_before_tax': result['gain'],
            'gain_pct': result['gain_pct'],
            'estimated_tax': round(estimated_tax, 2),
            'net_after_tax': round(net_after_tax, 2),
            'lots_used': result['lots_used'],
            'is_short_term': result['is_short_term'],
            'wash_sale_warning': wash_check['is_wash_sale'],
            'wash_sale_message': wash_check['message'] if wash_check['is_wash_sale'] else None
        }
    
    def find_tax_loss_harvesting_opportunities(self, min_loss: float = 50) -> pd.DataFrame:
        """
        Encuentra oportunidades de tax-loss harvesting.
        
        Identifica posiciones con pérdidas latentes que podrían venderse
        para compensar ganancias realizadas.
        
        Args:
            min_loss: Pérdida mínima para considerar (€)
        
        Returns:
            DataFrame con oportunidades ordenadas por pérdida
        """
        lots = self.get_all_available_lots()
        
        if lots.empty:
            return pd.DataFrame()
        
        # Para cada lote, necesitaríamos el precio actual
        # Como no tenemos precios de mercado, usamos el precio de compra
        # En una implementación real, integrarías con yfinance
        
        # Por ahora, mostramos lotes que llevan mucho tiempo
        # (mayor probabilidad de tener pérdidas si el mercado ha bajado)
        
        opportunities = lots[lots['days_held'] > 30].copy()
        opportunities = opportunities.sort_values('days_held', ascending=False)
        
        return opportunities
    
    # =========================================================================
    # DIVIDENDOS (FISCALIDAD)
    # =========================================================================
    
    def get_dividends_fiscal_summary(self, year: int) -> Dict:
        """
        Resumen fiscal de dividendos del año.
        
        Args:
            year: Año fiscal
        
        Returns:
            Dict con resumen de dividendos
        """
        dividends = self.db.get_dividends(year=year)
        
        if not dividends:
            return {
                'year': year,
                'total_gross': 0,
                'total_withholding': 0,
                'total_net': 0,
                'by_ticker': {}
            }
        
        total_gross = 0
        total_net = 0
        by_ticker = defaultdict(lambda: {'gross': 0, 'net': 0, 'withholding': 0})
        
        for d in dividends:
            total_gross += d.gross_amount
            total_net += d.net_amount
            
            by_ticker[d.ticker]['gross'] += d.gross_amount
            by_ticker[d.ticker]['net'] += d.net_amount
            by_ticker[d.ticker]['withholding'] += (d.gross_amount - d.net_amount)
        
        total_withholding = total_gross - total_net
        
        return {
            'year': year,
            'total_gross': round(total_gross, 2),
            'total_withholding': round(total_withholding, 2),
            'total_net': round(total_net, 2),
            'by_ticker': {k: {kk: round(vv, 2) for kk, vv in v.items()} 
                         for k, v in by_ticker.items()}
        }
    
    # =========================================================================
    # EXPORTACIÓN
    # =========================================================================
    
    def export_fiscal_report(self, 
                            year: int, 
                            filepath: str = None,
                            include_lots: bool = True) -> str:
        """
        Exporta el informe fiscal completo a Excel.
        
        Args:
            year: Año fiscal
            filepath: Ruta del archivo (si None, genera nombre automático)
            include_lots: Si incluir hoja con detalle de lotes
        
        Returns:
            Ruta del archivo generado
        """
        if filepath is None:
            filepath = f'data/exports/informe_fiscal_{year}.xlsx'
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Obtener datos
        summary = self.get_fiscal_year_summary(year)
        detail = self.get_fiscal_year_detail(year)
        dividends = self.get_dividends_fiscal_summary(year)
        wash_sales = self.get_wash_sales_in_year(year)
        
        # Crear Excel con múltiples hojas
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            
            # Hoja 1: Resumen
            summary_data = {
                'Concepto': [
                    'Año Fiscal',
                    '',
                    'GANANCIAS PATRIMONIALES',
                    'Número de ventas',
                    'Total ganancias',
                    'Total pérdidas',
                    'Resultado neto',
                    '',
                    'AJUSTES FISCALES',
                    'Pérdidas no deducibles (regla 2 meses)',
                    'Pérdidas deducibles',
                    '',
                    'BASE IMPONIBLE DEL AHORRO',
                    'Base imponible',
                    'Impuesto estimado',
                    '',
                    'DIVIDENDOS',
                    'Total bruto',
                    'Retenciones (19%)',
                    'Total neto',
                ],
                'Valor': [
                    year,
                    '',
                    '',
                    summary['total_sales'],
                    f"+{summary['total_gains']:,.2f}€",
                    f"{summary['total_losses']:,.2f}€",
                    f"{summary['net_gain']:+,.2f}€",
                    '',
                    '',
                    f"{summary['wash_sales_loss']:,.2f}€",
                    f"{summary['deductible_loss']:,.2f}€",
                    '',
                    '',
                    f"{summary['tax_base']:,.2f}€",
                    f"{summary['estimated_tax']:,.2f}€",
                    '',
                    '',
                    f"{dividends['total_gross']:,.2f}€",
                    f"{dividends['total_withholding']:,.2f}€",
                    f"{dividends['total_net']:,.2f}€",
                ]
            }
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja 2: Detalle de ventas
            if not detail.empty:
                # Renombrar columnas para Excel
                detail_export = detail.rename(columns={
                    'sale_date': 'Fecha Venta',
                    'ticker': 'Ticker',
                    'name': 'Nombre',
                    'asset_type': 'Tipo',
                    'quantity': 'Cantidad',
                    'purchase_date': 'Fecha Compra',
                    'purchase_price_avg': 'Precio Compra',
                    'sale_price': 'Precio Venta',
                    'currency': 'Divisa',
                    'days_held': 'Días',
                    'cost_basis': 'Coste Adquisición',
                    'sale_proceeds': 'Importe Venta',
                    'gain_eur': 'Ganancia/Pérdida (€)',
                    'gain_pct': 'Ganancia %'
                })
                detail_export.to_excel(writer, sheet_name='Detalle Ventas', index=False)
            
            # Hoja 3: Wash Sales (si hay)
            if not wash_sales.empty:
                wash_export = wash_sales.rename(columns={
                    'date': 'Fecha Venta',
                    'ticker': 'Ticker',
                    'name': 'Nombre',
                    'quantity': 'Cantidad',
                    'loss': 'Pérdida',
                    'blocking_purchases': 'Compras Bloqueantes',
                    'deductible': '¿Deducible?'
                })
                wash_export.to_excel(writer, sheet_name='Regla 2 Meses', index=False)
            
            # Hoja 4: Lotes disponibles (si se solicita)
            if include_lots:
                lots = self.get_all_available_lots()
                if not lots.empty:
                    lots_export = lots.rename(columns={
                        'ticker': 'Ticker',
                        'name': 'Nombre',
                        'date': 'Fecha Compra',
                        'quantity': 'Cantidad',
                        'original_quantity': 'Cantidad Original',
                        'price': 'Precio',
                        'cost': 'Coste',
                        'days_held': 'Días Tenencia'
                    })
                    lots_export.to_excel(writer, sheet_name='Lotes Disponibles', index=False)
            
            # Hoja 5: Por trimestre
            if summary['by_quarter']:
                quarter_data = {
                    'Trimestre': list(summary['by_quarter'].keys()),
                    'Ganancia/Pérdida': list(summary['by_quarter'].values())
                }
                df_quarter = pd.DataFrame(quarter_data)
                df_quarter.to_excel(writer, sheet_name='Por Trimestre', index=False)
            
            # Hoja 6: Tramos IRPF (informativo)
            tax_info = self.calculate_tax(max(summary['tax_base'], 0))
            if tax_info['breakdown']:
                df_tax = pd.DataFrame(tax_info['breakdown'])
                df_tax = df_tax.rename(columns={
                    'bracket': 'Tramo',
                    'rate': 'Tipo',
                    'taxable_amount': 'Base',
                    'tax': 'Cuota'
                })
                df_tax.to_excel(writer, sheet_name='Desglose Impuesto', index=False)
        
        print(f"✅ Informe fiscal exportado a: {filepath}")
        return str(filepath)
    
    # =========================================================================
    # FUNCIONES DE CONVENIENCIA (PRINT)
    # =========================================================================
    
    def print_fiscal_summary(self, year: int):
        """Imprime el resumen fiscal del año de forma legible"""
        summary = self.get_fiscal_year_summary(year)
        dividends = self.get_dividends_fiscal_summary(year)
        
        print("\n" + "="*70)
        print(f"📊 INFORME FISCAL {year}")
        print("="*70)
        
        print(f"\n📈 GANANCIAS PATRIMONIALES")
        print("-"*50)
        print(f"   Ventas realizadas:     {summary['total_sales']}")
        print(f"   Total ganancias:       +{summary['total_gains']:,.2f}€")
        print(f"   Total pérdidas:        {summary['total_losses']:,.2f}€")
        print(f"   Resultado neto:        {summary['net_gain']:+,.2f}€")
        
        if summary['wash_sales_loss'] != 0:
            print(f"\n⚠️  AJUSTES (Regla 2 meses)")
            print("-"*50)
            print(f"   Pérdidas no deducibles: {summary['wash_sales_loss']:,.2f}€")
            print(f"   Pérdidas deducibles:    {summary['deductible_loss']:,.2f}€")
        
        print(f"\n💰 BASE IMPONIBLE DEL AHORRO")
        print("-"*50)
        print(f"   Base imponible:        {summary['tax_base']:,.2f}€")
        
        if summary['tax_base'] > 0:
            print(f"   Impuesto estimado:     {summary['estimated_tax']:,.2f}€")
            
            # Mostrar desglose por tramos
            tax_info = self.calculate_tax(summary['tax_base'])
            if tax_info['breakdown']:
                print(f"\n   Desglose por tramos:")
                for b in tax_info['breakdown']:
                    print(f"      {b['bracket']}: {b['taxable_amount']:,.2f}€ × {b['rate']} = {b['tax']:,.2f}€")
                print(f"\n   Tipo efectivo: {tax_info['effective_rate']:.2f}%")
        else:
            print(f"   Impuesto a pagar:      0.00€")
            print(f"   Pérdidas a compensar:  {abs(summary['tax_base']):,.2f}€")
            print(f"   (Compensables en los 4 años siguientes)")
        
        if dividends['total_gross'] > 0:
            print(f"\n💵 DIVIDENDOS")
            print("-"*50)
            print(f"   Total bruto:           {dividends['total_gross']:,.2f}€")
            print(f"   Retenciones (19%):     {dividends['total_withholding']:,.2f}€")
            print(f"   Total neto:            {dividends['total_net']:,.2f}€")
        
        if summary['by_quarter']:
            print(f"\n📅 POR TRIMESTRE")
            print("-"*50)
            for q, val in summary['by_quarter'].items():
                emoji = "📈" if val >= 0 else "📉"
                print(f"   {emoji} {q}: {val:+,.2f}€")
        
        print("\n" + "="*70)
    
    def print_available_lots(self, ticker: str = None):
        """Imprime los lotes disponibles de forma legible"""
        if ticker:
            lots = self.get_available_lots(ticker)
            title = f"LOTES DISPONIBLES: {ticker}"
        else:
            lots_df = self.get_all_available_lots()
            if lots_df.empty:
                print("\n❌ No hay lotes disponibles")
                return
            lots = lots_df.to_dict('records')
            title = "TODOS LOS LOTES DISPONIBLES"
        
        print("\n" + "="*70)
        print(f"📦 {title}")
        print("="*70)
        
        if not lots:
            print(f"\n   No hay lotes disponibles" + (f" para {ticker}" if ticker else ""))
            return
        
        current_ticker = None
        for lot in lots:
            if 'ticker' in lot and lot['ticker'] != current_ticker:
                current_ticker = lot['ticker']
                print(f"\n📈 {lot.get('name', current_ticker)} ({current_ticker})")
                print("-"*50)
            
            print(f"   📅 {lot['date']} | {lot['quantity']:,.4f} uds @ {lot['price']:,.4f}€ | "
                  f"Coste: {lot['cost']:,.2f}€ | {lot['days_held']} días")
        
        print("\n" + "="*70)
    
    def print_simulation(self, ticker: str, quantity: float, price: float):
        """Imprime simulación de venta de forma legible"""
        sim = self.simulate_sale(ticker, quantity, price)
        
        print("\n" + "="*70)
        print(f"🔮 SIMULACIÓN DE VENTA: {ticker}")
        print("="*70)
        
        if 'error' in sim:
            print(f"\n❌ {sim['error']}")
            return
        
        print(f"\n📊 OPERACIÓN")
        print("-"*50)
        print(f"   Cantidad a vender:     {sim['quantity_to_sell']:,.4f}")
        print(f"   Cantidad disponible:   {sim['available_quantity']:,.4f}")
        print(f"   Precio estimado:       {sim['estimated_price']:,.2f}€")
        
        print(f"\n💰 RESULTADO")
        print("-"*50)
        print(f"   Ingresos brutos:       {sim['gross_proceeds']:,.2f}€")
        print(f"   Coste adquisición:     {sim['cost_basis']:,.2f}€")
        
        emoji = "📈" if sim['gain_before_tax'] >= 0 else "📉"
        print(f"   {emoji} Ganancia/Pérdida:     {sim['gain_before_tax']:+,.2f}€ ({sim['gain_pct']:+.2f}%)")
        
        if sim['gain_before_tax'] > 0:
            print(f"\n🏛️  FISCALIDAD")
            print("-"*50)
            print(f"   Impuesto estimado:     {sim['estimated_tax']:,.2f}€")
            print(f"   Beneficio neto:        {sim['net_after_tax']:,.2f}€")
        
        if sim['wash_sale_warning']:
            print(f"\n⚠️  ADVERTENCIA")
            print("-"*50)
            print(f"   {sim['wash_sale_message']}")
        
        if sim['lots_used']:
            print(f"\n📦 LOTES QUE SE VENDERÍAN ({self.method})")
            print("-"*50)
            for lot in sim['lots_used']:
                print(f"   📅 {lot['lot_date']} | {lot['quantity_from_lot']:,.4f} uds @ {lot['purchase_price']:,.4f}€ | "
                      f"{lot['days_held']} días")
        
        print("\n" + "="*70)


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def quick_fiscal_report(year: int, filepath: str = None) -> str:
    """Genera informe fiscal rápido"""
    tax = TaxCalculator()
    result = tax.export_fiscal_report(year, filepath)
    tax.close()
    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 TEST DEL MÓDULO TAX CALCULATOR")
    print("="*70)
    
    tax = TaxCalculator(method='FIFO')
    
    # Test 1: Resumen fiscal
    print("\n📊 Test 1: Resumen Fiscal 2025")
    tax.print_fiscal_summary(2025)
    
    # Test 2: Lotes disponibles
    print("\n📦 Test 2: Algunos lotes disponibles")
    lots = tax.get_all_available_lots()
    if not lots.empty:
        print(lots.head(10).to_string())
    
    # Test 3: Wash sales
    print("\n⚠️  Test 3: Wash Sales 2025")
    wash = tax.get_wash_sales_in_year(2025)
    if not wash.empty:
        print(wash.to_string())
    else:
        print("   No hay wash sales detectados")
    
    tax.close()
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETADOS")
    print("="*70 + "\n")
