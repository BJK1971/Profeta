#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    PROFETA - MARKET STATUS CHECK (TradingHours)                          ║
║                                                                                            ║
║  Verifica stato mercati usando TradingHours API                                           ║
║  https://docs.tradinghours.com/                                                            ║
║                                                                                            ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║  Usage: python check_market_th.py [EPIC]                                                 ║
║         python check_market_th.py EURUSD                                                  ║
║         python check_market_th.py BTCUSD                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import configparser
import logging
import requests
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger("TradingHoursCheck")

# Mapping Epic → TradingHours Market Type
MARKET_TYPE_MAP = {
    'EURUSD': 'forex',
    'GBPUSD': 'forex',
    'USDJPY': 'forex',
    'AUDUSD': 'forex',
    'USDCAD': 'forex',
    'USDCHF': 'forex',
    'BTCUSD': 'crypto',
    'ETHUSD': 'crypto',
    'XRPUSD': 'crypto',
    'AAPL': 'stocks',
    'TSLA': 'stocks',
    'NVDA': 'stocks',
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    TRADINGHOURS CHECK
# ═══════════════════════════════════════════════════════════════════════════════════════════

def check_market_tradinghours(epic: str, api_key: str = None) -> dict:
    """
    Verifica stato mercato usando TradingHours API.
    
    Docs: https://docs.tradinghours.com/
    
    Args:
        epic: Strumento (es: EURUSD, BTCUSD)
        api_key: TradingHours API key (opzionale, cerca nel config se None)
        
    Returns:
        dict: {
            'is_open': bool,
            'status': str,
            'epic': str,
            'message': str,
            'market_type': str,
            'next_open': str,
            'next_close': str
        }
    """
    
    # Carica API key dal config se non fornita
    if api_key is None:
        config = configparser.ConfigParser()
        config.read('BKTEST/config-lstm-backtest.ini')
        try:
            api_key = config['MARKET_CHECK']['api_key']
        except KeyError:
            return {
                'success': False,
                'error': 'API key non trovata',
                'is_open': True,  # Fallback: procedi
                'message': 'API key TradingHours non configurata'
            }
    
    # Determina market type
    market_type = MARKET_TYPE_MAP.get(epic.upper(), 'forex')
    
    # TradingHours API v3 endpoint
    # https://docs.tradinghours.com/3.x/endpoints/market-status
    base_url = 'https://api.tradinghours.com/v3'
    
    # Mappa market type per TradingHours
    # TradingHours usa "exchange" parameter: FOREX, CRYPTO, STOCK
    th_exchange_map = {
        'forex': 'FOREX',
        'crypto': 'CRYPTO',
        'stocks': 'STOCK'
    }
    th_exchange = th_exchange_map.get(market_type, 'FOREX')
    
    # Endpoint corretto: /market/status?exchange=FOREX&key=YOUR_KEY
    url = f"{base_url}/market/status"
    params = {
        'exchange': th_exchange,
        'key': api_key
    }
    
    try:
        logger.info(f"TradingHours check: {epic} ({th_exchange})")
        
        response = requests.get(url, params=params, timeout=10)
        
        # Debug: stampa URL completo
        logger.debug(f"URL: {response.url}")
        logger.debug(f"Status: {response.status_code}")
        
        if response.status_code == 404:
            error_msg = f"Endpoint non trovato: {response.url}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': 'Endpoint non trovato',
                'is_open': True,  # Fallback: procedi
                'message': f'API endpoint errato: {error_msg}',
                'provider': 'TradingHours'
            }
        
        response.raise_for_status()
        
        data = response.json()
        
        # TradingHours v3 response format:
        # {
        #   "data": {
        #     "exchange": "FOREX",
        #     "is_open": true,
        #     "next_open": "...",
        #     "next_close": "..."
        #   }
        # }
        
        # Estrai dati (può essere nested in 'data')
        if 'data' in data:
            market_data = data['data']
        else:
            market_data = data
        
        is_open = market_data.get('is_open', False)
        status = 'OPEN' if is_open else 'CLOSED'
        next_open = market_data.get('next_open', 'N/A')
        next_close = market_data.get('next_close', 'N/A')
        
        # Costruisci messaggio
        if is_open:
            message = f"Mercato {epic} ({th_exchange}): APERTO"
        else:
            message = f"Mercato {epic} ({th_exchange}): CHIUSO"
            if next_open != 'N/A':
                message += f" - Riapre: {next_open}"
        
        result = {
            'success': True,
            'is_open': is_open,
            'status': status,
            'epic': epic,
            'market_type': market_type,
            'exchange': th_exchange,
            'message': message,
            'next_open': next_open,
            'next_close': next_close,
            'provider': 'TradingHours'
        }
        
        logger.info(message)
        return result
        
    except requests.exceptions.HTTPError as he:
        error_msg = f"Errore HTTP TradingHours: {he}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(he),
            'is_open': True,  # Fallback: procedi
            'message': f'Errore API: {he}',
            'provider': 'TradingHours'
        }
        
    except requests.exceptions.Timeout:
        error_msg = "Timeout TradingHours API"
        logger.error(error_msg)
        return {
            'success': False,
            'error': 'Timeout',
            'is_open': True,  # Fallback: procedi
            'message': 'Timeout API',
            'provider': 'TradingHours'
        }
        
    except Exception as e:
        error_msg = f"Errore TradingHours: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'is_open': True,  # Fallback: procedi
            'message': f'Errore: {e}',
            'provider': 'TradingHours'
        }

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

def main():
    # Parse argomenti
    if len(sys.argv) < 2:
        print("Usage: python check_market_th.py [EPIC]")
        print("Example: python check_market_th.py EURUSD")
        print("         python check_market_th.py BTCUSD")
        sys.exit(1)
    
    epic = sys.argv[1].upper()
    
    # Carica API key opzionale da config
    api_key = None
    config_path = 'BKTEST/config-lstm-backtest.ini'
    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        try:
            api_key = config['MARKET_CHECK']['api_key']
            logger.info(f"API key caricata dal config")
        except KeyError:
            logger.warning("API key TradingHours non configurata nel config")
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     PROFETA - MARKET STATUS (TradingHours API)                 ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("")
    
    # Esegui check
    result = check_market_tradinghours(epic, api_key)
    
    # Output risultato
    print("")
    print("═" * 60)
    print(f"EPIC: {result.get('epic', 'N/A')}")
    print(f"Market Type: {result.get('market_type', 'N/A')}")
    print(f"Status: {result.get('status', 'UNKNOWN')}")
    print(f"Is Open: {'✅ YES' if result.get('is_open') else '❌ NO'}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    if result.get('reason'):
        print(f"Reason: {result['reason']}")
    if result.get('next_open'):
        print(f"Next Open: {result['next_open']}")
    if result.get('next_close'):
        print(f"Next Close: {result['next_close']}")
    
    print(f"Provider: {result.get('provider', 'N/A')}")
    print("═" * 60)
    print("")
    
    # Exit code
    if result.get('is_open'):
        print("✅ Il mercato è APERTO - Training/Prediction OK")
        sys.exit(0)
    else:
        print("❌ Il mercato è CHIUSO - Skip training/prediction")
        sys.exit(1)

if __name__ == "__main__":
    main()
