#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    PROFETA - MARKET STATUS CHECK                                         ║
║                                                                                            ║
║  Utility per verificare lo stato dei mercati usando Capital.com API                       ║
║                                                                                            ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║  Usage: python check_market_status.py [EPIC]                                             ║
║         python check_market_status.py EURUSD                                              ║
║         python check_market_status.py BTCUSD                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import configparser
import logging
from datetime import datetime, timezone

# Aggiungi Profeta al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from profeta_trading_bot import CapitalDemoBroker

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger("MarketStatusCheck")

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MARKET STATUS CHECK
# ═══════════════════════════════════════════════════════════════════════════════════════════

def check_market_status(epic: str, config_path: str = None) -> dict:
    """
    Verifica lo stato del mercato per un dato epic.
    
    Args:
        epic: Strumento da verificare (es: EURUSD, BTCUSD)
        config_path: Percorso file di configurazione (default: BKTEST/config-lstm-backtest.ini)
        
    Returns:
        dict: Risultato del check
    """
    
    # Carica configurazione
    if config_path is None:
        config_path = "BKTEST/config-lstm-backtest.ini"
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Estrai credenziali
    try:
        api_key = config["CAPITAL_DEMO"]["api_key"]
        api_secret = config["CAPITAL_DEMO"]["api_secret"]
        api_pass = config["CAPITAL_DEMO"]["api_pass"]
    except KeyError:
        logger.error("Credenziali CAPITAL_DEMO non trovate nel config!")
        return {
            'success': False,
            'error': 'Credenziali non trovate',
            'is_open': False
        }
    
    # Inizializza broker
    broker = CapitalDemoBroker(api_key, api_secret, api_pass)
    
    # Autentica
    logger.info(f"Autenticazione su Capital.com...")
    if not broker.authenticate():
        logger.error("Autenticazione fallita!")
        return {
            'success': False,
            'error': 'Autenticazione fallita',
            'is_open': False
        }
    
    # Check mercato
    logger.info(f"Verifica stato mercato per {epic}...")
    result = broker.check_market_status(epic)
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

def main():
    # Parse argomenti
    if len(sys.argv) < 2:
        print("Usage: python check_market_status.py [EPIC]")
        print("Example: python check_market_status.py EURUSD")
        print("         python check_market_status.py BTCUSD")
        sys.exit(1)
    
    epic = sys.argv[1].upper()
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          PROFETA - MARKET STATUS CHECK                         ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("")
    
    # Esegui check
    result = check_market_status(epic)
    
    # Output risultato
    print("")
    print("═" * 60)
    print(f"EPIC: {result.get('epic', 'N/A')}")
    print(f"Status: {result.get('status', 'UNKNOWN')}")
    print(f"Is Open: {'✅ YES' if result.get('is_open') else '❌ NO'}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    if result.get('bid'):
        print(f"Bid: {result['bid']}")
    if result.get('offer'):
        print(f"Offer: {result['offer']}")
    
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
