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


def _cumulative_to_annualized(cumulative_return: float, years: int) -> float:
    """
    Convierte retorno acumulado a anualizado.

    Args:
        cumulative_return: Retorno acumulado en porcentaje (ej: 54.44 para 54.44%)
        years: Numero de anos

    Returns:
        Retorno anualizado en porcentaje
    """
    if cumulative_return is None or years <= 0:
        return None
    # Formula: ((1 + r)^(1/n) - 1) * 100
    return (pow(1 + cumulative_return / 100, 1 / years) - 1) * 100


class FundDataProvider:
    """
    Proveedor de datos de fondos via Morningstar.

    Encapsula mstarpy para obtener informacion de fondos/ETFs:
    - Info basica (nombre, ISIN, categoria)
    - Metricas de rendimiento (1a, 3a, 5a) - ANUALIZADAS
    - Metricas de riesgo (volatilidad, Sharpe)
    - Cartera (asset allocation, sectores, paises, top holdings)
    - Historico de precios (NAV)

    Args:
        language: Idioma para los datos ('en-gb', 'es', etc.)

    Ejemplo:
        >>> provider = FundDataProvider()
        >>> data = provider.get_fund_data('IE00B3RBWM25')
        >>> print(f"{data['name']}: TER {data['ter']}%")
    """

    # Mapeo de nombres de paises
    COUNTRY_NAMES = {
        'unitedStates': 'Estados Unidos',
        'japan': 'Japon',
        'china': 'China',
        'unitedKingdom': 'Reino Unido',
        'canada': 'Canada',
        'switzerland': 'Suiza',
        'taiwan': 'Taiwan',
        'france': 'Francia',
        'germany': 'Alemania',
        'india': 'India',
        'australia': 'Australia',
        'southKorea': 'Corea del Sur',
        'netherlands': 'Paises Bajos',
        'sweden': 'Suecia',
        'spain': 'Espana',
        'italy': 'Italia',
        'brazil': 'Brasil',
        'hongKong': 'Hong Kong',
        'singapore': 'Singapur',
        'southAfrica': 'Sudafrica',
        'denmark': 'Dinamarca',
        'mexico': 'Mexico',
    }

    # Mapeo de nombres de sectores
    SECTOR_NAMES = {
        'basicMaterials': 'Materiales Basicos',
        'consumerCyclical': 'Consumo Ciclico',
        'financialServices': 'Servicios Financieros',
        'realEstate': 'Inmobiliario',
        'communicationServices': 'Comunicaciones',
        'energy': 'Energia',
        'industrials': 'Industrial',
        'technology': 'Tecnologia',
        'consumerDefensive': 'Consumo Defensivo',
        'healthcare': 'Salud',
        'utilities': 'Utilities',
    }

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
            - returns: rentabilidades ANUALIZADAS
            - risk: metricas de riesgo
            - allocation: asset allocation con sectores y paises
            - holdings: top 10 holdings (limitado por API)

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

            # URL correcta segun tipo de activo
            asset_type = fund.asset_type or 'fund'
            if asset_type == 'etf':
                data['url'] = f"https://www.morningstar.es/es/etf/snapshot/snapshot.aspx?id={fund.code}"
            else:
                data['url'] = f"https://www.morningstar.es/es/funds/snapshot/snapshot.aspx?id={fund.code}"

        except Exception as e:
            logger.warning(f"Error obteniendo snapshot: {e}")

        return data

    def _get_return_data(self, fund) -> dict:
        """
        Extrae datos de rentabilidad.

        IMPORTANTE: Los valores de trailingReturn son ACUMULADOS.
        - Periodos cortos (1D, 1W, 1M, 3M, 6M, YTD, 1Y): ya son "anualizados" o directos
        - 3Y, 5Y, 10Y: Convertimos de acumulado a anualizado
        """
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

            # Periodos cortos (valores directos)
            data['return_1d'] = get_return('1Day')
            data['return_1w'] = get_return('1Week')
            data['return_1m'] = get_return('1Month')
            data['return_3m'] = get_return('3Month')
            data['return_ytd'] = get_return('YearToDate')
            data['return_1y'] = get_return('1Year')

            # 3Y, 5Y, 10Y: convertir de acumulado a anualizado
            ret_3y_cum = get_return('3Year')
            ret_5y_cum = get_return('5Year')
            ret_10y_cum = get_return('10Year')

            data['return_3y'] = _cumulative_to_annualized(ret_3y_cum, 3)
            data['return_5y'] = _cumulative_to_annualized(ret_5y_cum, 5)
            data['return_10y'] = _cumulative_to_annualized(ret_10y_cum, 10)

            # Guardar tambien los acumulados para referencia
            data['return_3y_cumulative'] = ret_3y_cum
            data['return_5y_cumulative'] = ret_5y_cum

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
        """
        Extrae asset allocation completo incluyendo sectores y paises.

        Returns:
            dict con:
            - cash, us_equity, non_us_equity, bond, other, equity (asset types)
            - sectors: lista de {name, weight}
            - countries: lista de {name, weight}
            - regions: dict con regiones
        """
        allocation = {}
        try:
            # Asset allocation basico
            alloc_map = fund.allocationMap()
            alloc_data = alloc_map.get('allocationMap', {})

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

            allocation['equity'] = allocation.get('us_equity', 0) + allocation.get('non_us_equity', 0)

        except Exception as e:
            logger.warning(f"Error obteniendo allocation basico: {e}")

        # Sectores
        try:
            sector_data = fund.sector()
            equity_sectors = sector_data.get('EQUITY', {}).get('fundPortfolio', {})

            sectors = []
            for key, weight in equity_sectors.items():
                if key != 'portfolioDate' and weight and weight > 0.1:
                    name = self.SECTOR_NAMES.get(key, key)
                    sectors.append({'name': name, 'weight': weight})

            # Ordenar por peso descendente
            sectors.sort(key=lambda x: x['weight'], reverse=True)
            allocation['sectors'] = sectors[:10]  # Top 10

        except Exception as e:
            logger.warning(f"Error obteniendo sectores: {e}")
            allocation['sectors'] = []

        # Paises
        try:
            regional = fund.regionalSectorIncludeCountries()
            countries_data = regional.get('fundPortfolio', {}).get('countries', [])

            countries = []
            for item in countries_data:
                name_key = item.get('name')
                weight = item.get('percent', 0)
                if weight and weight > 0.1:
                    name = self.COUNTRY_NAMES.get(name_key, name_key)
                    countries.append({'name': name, 'weight': weight})

            # Ya vienen ordenados, tomamos top 10
            allocation['countries'] = countries[:10]

        except Exception as e:
            logger.warning(f"Error obteniendo paises: {e}")
            allocation['countries'] = []

        # Regiones
        try:
            regional_basic = fund.regionalSector()
            regions_data = regional_basic.get('fundPortfolio', {})

            regions = {}
            region_keys = [
                'northAmerica', 'unitedKingdom', 'europeDeveloped',
                'europeEmerging', 'japan', 'asiaDeveloped',
                'asiaEmerging', 'latinAmerica', 'africaMiddleEast', 'australasia'
            ]
            for key in region_keys:
                val = regions_data.get(key, 0)
                if val and val > 0.1:
                    regions[key] = val

            allocation['regions'] = regions

        except Exception as e:
            logger.warning(f"Error obteniendo regiones: {e}")
            allocation['regions'] = {}

        return allocation

    def _get_holdings_data(self, fund, top_n: int = 10) -> list:
        """
        Extrae top holdings.

        NOTA: La API publica de Morningstar limita a Top 10 holdings.
        """
        holdings = []
        try:
            holdings_df = fund.holdings(holdingType='equity')

            if isinstance(holdings_df, pd.DataFrame) and not holdings_df.empty:
                total_available = len(holdings_df)

                # Seleccionar top N
                top = holdings_df.head(top_n)

                for _, row in top.iterrows():
                    holding = {
                        'name': row.get('securityName'),
                        'weight': row.get('weighting'),
                        'sector': row.get('sector'),
                    }
                    holdings.append(holding)

                # Log si hay mas holdings disponibles
                if total_available > top_n:
                    logger.info(
                        f"Holdings limitados a Top {top_n} "
                        f"(disponibles: {total_available})"
                    )

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
            fund = mstarpy.Funds(term, pageSize=page_size, language=self.language)

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
