#!/usr/bin/env python3
"""Test Capital.com API per market status"""

import configparser
import requests
import json

config = configparser.ConfigParser()
config.read('BKTEST/config-lstm-backtest.ini')

api_key = config['CAPITAL_DEMO']['api_key']
api_secret = config['CAPITAL_DEMO']['api_secret']
api_pass = config['CAPITAL_DEMO']['api_pass']

base_url = 'https://demo-api-capital.backend-capital.com/api/v1/'
headers = {'X-CAP-API-KEY': api_key}

print("=" * 60)
print("TEST CAPITAL.COM API - Market Status")
print("=" * 60)
print()

# Auth
print("1. Autenticazione...")
payload = {'identifier': api_secret, 'password': api_pass}
resp = requests.post(f'{base_url}session', json=payload, headers=headers)
print(f"   Status: {resp.status_code}")

if resp.status_code == 200:
    headers['CST'] = resp.headers.get('CST')
    headers['X-SECURITY-TOKEN'] = resp.headers.get('X-SECURITY-TOKEN')
    print("   ✅ Autenticazione OK")
else:
    print(f"   ❌ Autenticazione FALLITA: {resp.text}")
    exit(1)

print()

# Test diversi endpoint
endpoints = [
    'markets/EURUSD',
    'markets/BTCUSD',
    'prices/EURUSD',
]

for endpoint in endpoints:
    print(f"2. Test endpoint: {endpoint}")
    try:
        resp = requests.get(f'{base_url}{endpoint}', headers=headers)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ OK")
            print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'List/Other'}")
            
            # Stampa primi campi rilevanti
            if isinstance(data, dict):
                if 'markets' in data and len(data['markets']) > 0:
                    market = data['markets'][0]
                    print(f"   Market data: bid={market.get('bid')}, offer={market.get('offer')}")
                else:
                    print(f"   Data sample: {json.dumps(data, indent=2)[:300]}")
        else:
            print(f"   ❌ ERROR: {resp.text[:200]}")
        
        print()
        
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
        print()

print("=" * 60)
