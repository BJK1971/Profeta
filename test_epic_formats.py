#!/usr/bin/env python3
"""Test diversi epic per EURUSD"""

import configparser, requests

config = configparser.ConfigParser()
config.read('BKTEST/config-lstm-backtest.ini')

api_key = config['CAPITAL_DEMO']['api_key']
api_secret = config['CAPITAL_DEMO']['api_secret']
api_pass = config['CAPITAL_DEMO']['api_pass']

base_url = 'https://demo-api-capital.backend-capital.com/api/v1/'
headers = {'X-CAP-API-KEY': api_key}

# Auth
payload = {'identifier': api_secret, 'password': api_pass}
resp = requests.post(f'{base_url}session', json=payload, headers=headers)
headers['CST'] = resp.headers.get('CST')
headers['X-SECURITY-TOKEN'] = resp.headers.get('X-SECURITY-TOKEN')

print("Test diversi formati epic per EURUSD:")
print("=" * 60)

# Test con epic diverso
epics_to_test = [
    'EURUSD',
    'EUR/USD',
    'FOREX_EURUSD',
    'EUR_USD',
]

for epic in epics_to_test:
    try:
        resp = requests.get(f'{base_url}prices/{epic}', headers=headers)
        print(f"{epic:15} → {resp.status_code} {'✅' if resp.status_code == 200 else '❌'}")
        
        if resp.status_code == 200:
            data = resp.json()
            prices = data.get('prices', [])
            if prices:
                last = prices[-1]
                bid = last.get('closePrice', {}).get('bid', 'N/A')
                print(f"                Last bid: {bid}")
    except Exception as e:
        print(f"{epic:15} → ERROR: {e}")

print("=" * 60)
