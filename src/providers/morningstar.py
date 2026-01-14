"""
Morningstar Provider - Obtiene datos de fondos via mstarpy

Proporciona acceso a datos de Morningstar para fondos de inversion y ETFs.
Utiliza la libreria mstarpy para consultar la API de Morningstar.

Uso:
    from src.providers.morningstar import FundDataProvider

    provider = FundDataProvider()
    data = provider.get_fund_data('IE00B3RBWM25')

    print(data['name'])  # Vanguard FTSE All-World UCITS ETF
    print(data['ter'])   # 0.19
"""

import logging
from datetime import date, datetime
from typing import Optional
import pandas as pd

try:
    import mstarpy
except ImportError:
    mstarpy = None

logger = logging.getLogger(__name__)


class FundDataProviderError(Exception):
    """Error al obtener datos del proveedor."""
    pass


class FundNotFoundError(FundDataProviderError):
    """Fondo no encontrado en Morningstar."""
    pass


class FundDataProvider:
    """
    Proveedor de datos de fondos via Morningstar.

    Encapsula mstarpy para obtener informacion de fondos/ETFs:
    - Info basica (nombre, ISIN, categoria)
    - Metricas de rendimiento (1a, 3a, 5a)
    - Metricas de riesgo (volatilidad, Sharpe)
    - Cartera (asset allocation, top holdings)
    - Historico de precios (NAV)

    Args:
        language: Idioma para los datos ('en-gb', 'es-es', etc.)

    Ejemplo:
        >>> provider = FundDataProvider()
        >>> data = provider.get_fund_data('IE00B3RBWM25')
        >>> print(f"{data['name']}: TER {data['ter']}%")
    """

    def __init__(self, language: str = 'en-gb'):
        if mstarpy is None:
            raise ImportError(
                "mstarpy no esta instalado. "
                "Ejecuta: pip install mstarpy"
            )
        self.language = language

    def get_fund_data(self, isin: str) -> dict:
        """
        Obtiene datos completos de un fondo por ISIN.

        Args:
            isin: Codigo ISIN del fondo (ej: 'IE00B3RBWM25')

        Returns:
            dict con toda la informacion del fondo:
            - info: datos basicos
            - returns: rentabilidades
            - risk: metricas de riesgo
            - allocation: asset allocation
            - holdings: top 10 holdings
            - nav_history: historico NAV (3 anos)

        Raises:
            FundNotFoundError: Si no se encuentra el fondo
            FundDataProviderError: Si hay error obteniendo datos
        """
        try:
            fund = mstarpy.Funds(isin, pageSize=1, language=self.language)

            if not fund.name:
                raise FundNotFoundError(f"Fondo no encontrado: {isin}")

        except ValueError as e:
            raise FundNotFoundError(f"Fondo no encontrado: {isin}") from e
        except Exception as e:
            raise FundDataProviderError(f"Error consultando {isin}: {e}") from e

        result = {
            'isin': fund.isin,
            'name': fund.name,
            'asset_type': fund.asset_type,
            'morningstar_code': fund.code,
        }

        # Obtener datos adicionales de cada endpoint
        result.update(self._get_snapshot_data(fund))
        result.update(self._get_return_data(fund))
        result.update(self._get_risk_data(fund))
        result['allocation'] = self._get_allocation_data(fund)
        result['holdings'] = self._get_holdings_data(fund)

        return result

    def get_nav_history(
        self,
        isin: str,
        years: int = 3
    ) -> pd.DataFrame:
        """
        Obtiene historico de NAV para un fondo.

        Args:
            isin: Codigo ISIN del fondo
            years: Anos de historia (default 3)

        Returns:
            DataFrame con columnas: date, nav, total_return
        """
        try:
            fund = mstarpy.Funds(isin, pageSize=1, language=self.language)

            end_date = date.today()
            start_date = date(end_date.year - years, end_date.month, end_date.day)

            nav_data = fund.nav(
                start_date=start_date,
                end_date=end_date,
                frequency='daily'
            )

            if not nav_data:
                return pd.DataFrame()

            df = pd.DataFrame(nav_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            logger.warning(f"Error obteniendo NAV para {isin}: {e}")
            return pd.DataFrame()

    def _get_snapshot_data(self, fund) -> dict:
        """Extrae datos del snapshot general."""
        data = {}
        try:
            snapshot = fund.snapshot()

            data['legal_name'] = snapshot.get('LegalName')
            data['currency'] = snapshot.get('Currency', {}).get('Id', 'EUR')
            data['ter'] = snapshot.get('TotalExpenseRatio')
            data['ongoing_charges'] = float(snapshot.get('OngoingCharge', 0)) if snapshot.get('OngoingCharge') else None
            data['management_fee'] = snapshot.get('ManagementFee')

            # Fecha de inicio
            inception = snapshot.get('InceptionDate')
            if inception:
                data['inception_date'] = datetime.fromisoformat(
                    inception.replace('T', ' ').split('.')[0]
                ).date()

            # Gestora
            provider = snapshot.get('ProviderCompany', {})
            data['manager'] = provider.get('Name')
            data['manager_country'] = provider.get('Country')

            # Domicilio
            data['fund_domicile'] = snapshot.get('Domicile')

            # Riesgo SRRI (1-7)
            srri = snapshot.get('CollectedSRRI', {})
            data['risk_level'] = srri.get('Rank')

            # Categoria
            data['morningstar_category'] = snapshot.get('IMASector', {}).get('Name')
            asset_class = snapshot.get('CategoryBroadAssetClass', {}).get('Name')
            data['asset_class'] = asset_class

            # AUM (Assets Under Management)
            navs = snapshot.get('NetAssetValues', [])
            if navs:
                # Convertir a millones EUR
                aum = navs[0].get('DayEndValue', 0)
                data['aum'] = aum / 1_000_000 if aum else None

            # Distribucion
            dist_freq = snapshot.get('DividendDistributionFrequency')
            if dist_freq:
                freq_map = {
                    'Q$': 'quarterly',
                    'A$': 'annual',
                    'M$': 'monthly',
                    'S$': 'semiannual'
                }
                data['dividend_frequency'] = freq_map.get(dist_freq, dist_freq)
                data['distribution_policy'] = 'distribution' if snapshot.get('IncomeDistribution') == 'true' else 'accumulation'

            # URL
            data['url'] = f"https://www.morningstar.es/es/etf/snapshot/snapshot.aspx?id={fund.code}"

        except Exception as e:
            logger.warning(f"Error obteniendo snapshot: {e}")

        return data

    def _get_return_data(self, fund) -> dict:
        """Extrae datos de rentabilidad."""
        data = {}
        try:
            returns = fund.trailingReturn()

            columns = returns.get('columnDefs', [])
            values = returns.get('totalReturnNAV', [])

            # Mapear indices de columnas
            col_map = {col: idx for idx, col in enumerate(columns)}

            def get_return(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(values):
                    val = values[idx]
                    return float(val) if val else None
                return None

            data['return_ytd'] = get_return('YearToDate')
            data['return_1y'] = get_return('1Year')
            data['return_3y'] = get_return('3Year')
            data['return_5y'] = get_return('5Year')
            data['return_10y'] = get_return('10Year')

        except Exception as e:
            logger.warning(f"Error obteniendo returns: {e}")

        return data

    def _get_risk_data(self, fund) -> dict:
        """Extrae datos de riesgo y volatilidad."""
        data = {}
        try:
            risk = fund.riskVolatility()

            fund_risk = risk.get('fundRiskVolatility', {})

            # 1 ano
            for1y = fund_risk.get('for1Year', {})
            data['volatility_1y'] = for1y.get('standardDeviation')
            data['sharpe_1y'] = for1y.get('sharpeRatio')

            # 3 anos
            for3y = fund_risk.get('for3Year', {})
            data['volatility_3y'] = for3y.get('standardDeviation')
            data['sharpe_3y'] = for3y.get('sharpeRatio')

            # 5 anos
            for5y = fund_risk.get('for5Year', {})
            data['volatility_5y'] = for5y.get('standardDeviation')
            data['sharpe_5y'] = for5y.get('sharpeRatio')

            # Categoria/benchmark
            data['category_name'] = risk.get('categoryName')
            data['benchmark_name'] = risk.get('indexName')

        except Exception as e:
            logger.warning(f"Error obteniendo risk data: {e}")

        return data

    def _get_allocation_data(self, fund) -> dict:
        """Extrae asset allocation."""
        allocation = {}
        try:
            alloc_map = fund.allocationMap()

            alloc_data = alloc_map.get('allocationMap', {})

            # Extraer valores netos
            mapping = {
                'cash': 'AssetAllocCash',
                'us_equity': 'AssetAllocUSEquity',
                'non_us_equity': 'AssetAllocNonUSEquity',
                'bond': 'AssetAllocBond',
                'other': 'AssetAllocOther',
            }

            for key, alloc_key in mapping.items():
                item = alloc_data.get(alloc_key, {})
                val = item.get('netAllocation')
                allocation[key] = float(val) if val else 0.0

            # Calcular equity total
            allocation['equity'] = allocation.get('us_equity', 0) + allocation.get('non_us_equity', 0)

        except Exception as e:
            logger.warning(f"Error obteniendo allocation: {e}")

        return allocation

    def _get_holdings_data(self, fund, top_n: int = 10) -> list:
        """Extrae top holdings."""
        holdings = []
        try:
            holdings_df = fund.holdings(holdingType='equity')

            if isinstance(holdings_df, pd.DataFrame) and not holdings_df.empty:
                # Seleccionar top N
                top = holdings_df.head(top_n)

                for _, row in top.iterrows():
                    holding = {
                        'name': row.get('securityName'),
                        'weight': row.get('weighting'),
                        'sector': row.get('sector'),
                    }
                    holdings.append(holding)

        except Exception as e:
            logger.warning(f"Error obteniendo holdings: {e}")

        return holdings

    def search_funds(
        self,
        term: str,
        page_size: int = 10
    ) -> list[dict]:
        """
        Busca fondos por nombre o termino.

        Args:
            term: Termino de busqueda
            page_size: Numero de resultados

        Returns:
            Lista de diccionarios con info basica de fondos encontrados
        """
        results = []
        try:
            # mstarpy devuelve solo 1 fondo por defecto
            # Para busquedas multiples usamos el API directamente
            fund = mstarpy.Funds(term, pageSize=page_size, language=self.language)

            # Por ahora retornamos el fondo encontrado
            results.append({
                'isin': fund.isin,
                'name': fund.name,
                'asset_type': fund.asset_type,
            })

        except Exception as e:
            logger.warning(f"Error buscando '{term}': {e}")

        return results


# Funcion de conveniencia
def get_fund_provider(language: str = 'en-gb') -> FundDataProvider:
    """Obtiene una instancia del proveedor de datos."""
    return FundDataProvider(language=language)
