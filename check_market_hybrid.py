#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    PROFETA - MARKET STATUS (Hybrid)                                      ║
║                                                                                            ║
║  Verifica stato mercati con approccio ibrido:                                             ║
║  1. TradingHours API (primario)                                                           ║
║  2. Fallback locale con festività per mercato (fallback)                                  ║
║  3. Procedi comunque (ultimo fallback)                                                    ║
║                                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import configparser
import logging
import requests
from datetime import datetime, timezone, date
from typing import Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger("MarketStatusHybrid")

# Market Type Mapping
MARKET_TYPE_MAP = {
    # Forex
    'EURUSD': 'forex', 'GBPUSD': 'forex', 'USDJPY': 'forex',
    'AUDUSD': 'forex', 'USDCAD': 'forex', 'USDCHF': 'forex',
    # Crypto
    'BTCUSD': 'crypto', 'ETHUSD': 'crypto', 'XRPUSD': 'crypto',
    # US Stocks
    'AAPL': 'stocks_us', 'TSLA': 'stocks_us', 'NVDA': 'stocks_us',
    'MSFT': 'stocks_us', 'GOOGL': 'stocks_us', 'AMZN': 'stocks_us',
    'META': 'stocks_us', 'AMD': 'stocks_us', 'INTC': 'stocks_us',
    # UK Stocks
    'VODL': 'stocks_uk', 'BP': 'stocks_uk', 'HSBA': 'stocks_uk',
    # Commodities (orari simili al forex: 23/5)
    'GOLD': 'commodity', 'SILVER': 'commodity', 'OIL_CRUDE': 'commodity',
    'XAUUSD': 'commodity', 'XAGUSD': 'commodity',
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    HOLIDAY DATABASE
# ═══════════════════════════════════════════════════════════════════════════════════════════

class MarketHolidays:
    """
    Database festività per mercato.
    Aggiornare annualmente.
    """
    
    # Festività Forex (mercati globali, chiuso solo Natale/Capodanno)
    FOREX_HOLIDAYS = {
        2026: [
            date(2026, 1, 1),      # Capodanno
            date(2026, 4, 3),      # Venerdì Santo
            date(2026, 5, 1),      # Labour Day (Europa)
            date(2026, 12, 25),    # Natale
            date(2026, 12, 26),    # Boxing Day
        ],
        2027: [
            date(2027, 1, 1),
            date(2027, 4, 2),
            date(2027, 5, 3),
            date(2027, 12, 25),
            date(2027, 12, 26),
        ]
    }
    
    # Festività US Stocks
    STOCKS_US_HOLIDAYS = {
        2026: [
            date(2026, 1, 1),      # Capodanno
            date(2026, 1, 19),     # MLK Day
            date(2026, 2, 16),     # Presidents Day
            date(2026, 4, 3),      # Good Friday
            date(2026, 5, 25),     # Memorial Day
            date(2026, 6, 19),     # Juneteenth
            date(2026, 7, 3),      # Independence Day (observed)
            date(2026, 9, 7),      # Labor Day
            date(2026, 11, 26),    # Thanksgiving
            date(2026, 11, 27),    # Day after Thanksgiving
            date(2026, 12, 24),    # Christmas Eve
            date(2026, 12, 25),    # Natale
        ],
        2027: [
            date(2027, 1, 1),
            date(2027, 1, 18),
            date(2027, 2, 15),
            date(2027, 3, 26),
            date(2027, 5, 31),
            date(2027, 6, 18),
            date(2027, 7, 5),
            date(2027, 9, 6),
            date(2027, 11, 25),
            date(2027, 11, 26),
            date(2027, 12, 24),
            date(2027, 12, 25),
        ]
    }
    
    # Festività UK Stocks
    STOCKS_UK_HOLIDAYS = {
        2026: [
            date(2026, 1, 1),
            date(2026, 4, 3),      # Good Friday
            date(2026, 4, 6),      # Easter Monday
            date(2026, 5, 4),      # Early May
            date(2026, 5, 25),     # Spring Bank Holiday
            date(2026, 8, 31),     # Summer Bank Holiday
            date(2026, 12, 25),    # Christmas
            date(2026, 12, 28),    # Boxing Day (observed)
        ],
        2027: [
            date(2027, 1, 1),
            date(2027, 4, 2),
            date(2027, 4, 5),
            date(2027, 5, 3),
            date(2027, 5, 31),
            date(2027, 8, 30),
            date(2027, 12, 27),
            date(2027, 12, 28),
        ]
    }
    
    @classmethod
    def is_holiday(cls, market_type: str, check_date: date = None) -> tuple:
        """
        Verifica se una data è festività per un mercato.
        
        Returns:
            (is_holiday: bool, holiday_name: str)
        """
        if check_date is None:
            check_date = date.today()
        
        year = check_date.year
        
        # Seleziona database festività
        holidays_db = cls.FOREX_HOLIDAYS
        if market_type == 'stocks_us':
            holidays_db = cls.STOCKS_US_HOLIDAYS
        elif market_type == 'stocks_uk':
            holidays_db = cls.STOCKS_UK_HOLIDAYS
        
        # Controlla se la data è nelle festività
        if year in holidays_db:
            if check_date in holidays_db[year]:
                return True, cls._get_holiday_name(check_date, market_type)
        
        return False, None
    
    @staticmethod
    def _get_holiday_name(check_date: date, market_type: str) -> str:
        """Restituisce nome festività (semplificato)"""
        month_day = (check_date.month, check_date.day)
        
        names = {
            (1, 1): "Capodanno",
            (4, 3): "Venerdì Santo",
            (5, 1): "Labour Day",
            (12, 25): "Natale",
            (12, 26): "Boxing Day",
        }
        
        if market_type == 'stocks_us':
            names.update({
                (1, 19): "MLK Day",
                (2, 16): "Presidents Day",
                (5, 25): "Memorial Day",
                (7, 3): "Independence Day",
                (9, 7): "Labor Day",
                (11, 26): "Thanksgiving",
            })
        elif market_type == 'stocks_uk':
            names.update({
                (4, 6): "Easter Monday",
                (5, 4): "Early May",
                (8, 31): "Summer Bank Holiday",
            })
        
        return names.get(month_day, "Festività")

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MARKET CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════

def check_market_local(epic: str) -> dict:
    """
    Verifica stato mercato con check locale (no API).
    
    Rules:
    - Crypto: sempre aperto
    - Forex: Lun-Ven, 24h, chiuso weekend e festività
    - Stocks: orari di borsa + festività specifiche
    """
    from datetime import time
    
    market_type = MARKET_TYPE_MAP.get(epic.upper(), 'forex')
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=Lun, 6=Dom
    
    # Crypto: sempre aperto
    if market_type == 'crypto':
        return {
            'is_open': True,
            'status': 'OPEN',
            'message': f'{epic}: Crypto - mercato sempre aperto',
            'provider': 'local'
        }
    
    # Weekend check (Sabato=5, Domenica=6)
    if weekday >= 5:
        return {
            'is_open': False,
            'status': 'CLOSED',
            'message': f'{epic}: Weekend',
            'reason': 'Weekend',
            'provider': 'local'
        }
    
    # Festività check
    is_holiday, holiday_name = MarketHolidays.is_holiday(market_type, now.date())
    if is_holiday:
        return {
            'is_open': False,
            'status': 'CLOSED',
            'message': f'{epic}: {holiday_name}',
            'reason': holiday_name,
            'provider': 'local'
        }
    
    # Commodity (GOLD, SILVER, OIL): aperto 23h/5gg con pausa giornaliera 20:59-22:00 UTC
    if market_type == 'commodity':
        from datetime import time as dtime
        current_time_utc = now.time()
        in_daily_break = dtime(20, 59) <= current_time_utc < dtime(22, 0)
        if in_daily_break:
            return {
                'is_open': False,
                'status': 'CLOSED',
                'message': f'{epic}: Commodity - pausa giornaliera (20:59-22:00 UTC)',
                'reason': 'daily_break_20:59-22:00_UTC',
                'provider': 'local'
            }
        return {
            'is_open': True,
            'status': 'OPEN',
            'message': f'{epic}: Commodity - mercato aperto',
            'provider': 'local'
        }

    # Forex: aperto 24/5
    if market_type == 'forex':
        # Forex apre Domenica 22:00 UTC, chiude Venerdì 22:00 UTC
        return {
            'is_open': True,
            'status': 'OPEN',
            'message': f'{epic}: Forex - mercato aperto',
            'provider': 'local'
        }
    
    # Stocks: verifica orari di borsa
    if market_type in ['stocks_us', 'stocks_uk']:
        current_time = now.time()
        
        if market_type == 'stocks_us':
            # NYSE: 14:30-21:00 UTC
            market_open = time(14, 30)
            market_close = time(21, 0)
        else:  # stocks_uk
            # LSE: 08:00-16:30 UTC
            market_open = time(8, 0)
            market_close = time(16, 30)
        
        if market_open <= current_time <= market_close:
            return {
                'is_open': True,
                'status': 'OPEN',
                'message': f'{epic}: Stocks - mercato aperto',
                'provider': 'local'
            }
        else:
            return {
                'is_open': False,
                'status': 'CLOSED',
                'message': f'{epic}: Stocks - fuori orario di borsa',
                'reason': 'After hours',
                'provider': 'local'
            }
    
    # Default: procedi
    return {
        'is_open': True,
        'status': 'UNKNOWN',
        'message': f'{epic}: Check non disponibile, procedo',
        'provider': 'local'
    }


def check_market_tradinghours(epic: str, api_key: str) -> dict:
    """
    Verifica stato mercato usando TradingHours API v3.
    """
    market_type = MARKET_TYPE_MAP.get(epic.upper(), 'forex')
    
    th_exchange_map = {
        'forex': 'FOREX',
        'crypto': 'CRYPTO',
        'stocks_us': 'STOCK',
        'stocks_uk': 'STOCK'
    }
    th_exchange = th_exchange_map.get(market_type, 'FOREX')
    
    url = 'https://api.tradinghours.com/v3/market/status'
    params = {'exchange': th_exchange, 'key': api_key}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 401:
            logger.warning("TradingHours API: 401 Unauthorized - API key non valida")
            return None  # Fallback a locale
        
        if response.status_code == 404:
            logger.warning("TradingHours API: 404 Not Found - endpoint errato")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        market_data = data.get('data', data)
        is_open = market_data.get('is_open', False)
        
        return {
            'is_open': is_open,
            'status': 'OPEN' if is_open else 'CLOSED',
            'message': f'{epic}: {market_data.get("status", "UNKNOWN")}',
            'provider': 'TradingHours'
        }
        
    except Exception as e:
        logger.warning(f"TradingHours API fallita: {e}")
        return None


def check_market_status(epic: str, config_path: str = None) -> dict:
    """
    Hybrid market status check.
    
    Priority:
    1. TradingHours API (se configurata e funziona)
    2. Local check (fallback)
    """
    logger.info(f"Market check per {epic}...")
    
    # Carica config
    if config_path is None:
        config_path = 'BKTEST/config-lstm-backtest.ini'
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Prova TradingHours API
    try:
        api_key = config['MARKET_CHECK']['api_key']
        provider = config['MARKET_CHECK'].get('provider', 'tradinghours')
        
        if provider == 'tradinghours' and api_key:
            logger.info("Tentativo con TradingHours API...")
            result = check_market_tradinghours(epic, api_key)
            
            if result:
                logger.info(f"✅ TradingHours: {result['message']}")
                return result
    except KeyError:
        logger.info("TradingHours non configurato, uso fallback locale")
    
    # Fallback: Local check
    logger.info("Uso fallback locale...")
    result = check_market_local(epic)
    logger.info(f"✅ Local: {result['message']}")
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_market_hybrid.py [EPIC]")
        print("Example: python check_market_hybrid.py EURUSD")
        sys.exit(1)
    
    epic = sys.argv[1].upper()
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     PROFETA - MARKET STATUS (Hybrid)                           ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("")
    
    result = check_market_status(epic)
    
    print("")
    print("═" * 60)
    print(f"EPIC: {epic}")
    print(f"Status: {result.get('status', 'UNKNOWN')}")
    print(f"Is Open: {'✅ YES' if result.get('is_open') else '❌ NO'}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    if result.get('reason'):
        print(f"Reason: {result['reason']}")
    print(f"Provider: {result.get('provider', 'N/A')}")
    print("═" * 60)
    print("")
    
    sys.exit(0 if result.get('is_open') else 1)

if __name__ == "__main__":
    main()
