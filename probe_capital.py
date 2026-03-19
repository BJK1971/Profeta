import configparser
import requests
from datetime import datetime, timezone, timedelta

class MinimalBroker:
    def __init__(self, api_key, api_secret, api_pass):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_pass = api_pass
        self.base_url = "https://demo-api-capital.backend-capital.com/api/v1/"
        self.headers = {"X-CAP-API-KEY": self.api_key}

    def authenticate(self):
        url = f"{self.base_url}session"
        payload = {"identifier": self.api_secret, "password": self.api_pass}
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        self.headers["CST"] = response.headers.get("CST")
        self.headers["X-SECURITY-TOKEN"] = response.headers.get("X-SECURITY-TOKEN")
        return True

def run_probe():
    config = configparser.ConfigParser()
    config.read("/mnt/c/work/gitrepo/Profeta/BKTEST/config-lstm-backtest.ini")
    
    k_key = config["CAPITAL_DEMO"]["api_key"]
    k_sec = config["CAPITAL_DEMO"]["api_secret"]
    k_pas = config["CAPITAL_DEMO"]["api_pass"]
    epic = config["CAPITAL_DEMO"].get("epic", "BTCUSD")

    broker = MinimalBroker(api_key=k_key, api_secret=k_sec, api_pass=k_pas)
    if broker.authenticate():
        url = f"{broker.base_url}prices/{epic}"
        now = datetime.now(timezone.utc)
        
        # Testiamo diverse dimensioni di ore (1000 era fallito)
        for hours in [800, 600, 500, 400, 250, 168]: # 168 = 1 settimana
            start = now - timedelta(hours=hours)
            from_str = start.strftime("%Y-%m-%dT%H:%M:%S")
            to_str = now.strftime("%Y-%m-%dT%H:%M:%S")
            
            params = {"resolution": "HOUR", "from": from_str, "to": to_str}
            print(f"Testing chunk size: {hours} hours...")
            res = requests.get(url, headers=broker.headers, params=params)
            if res.ok:
                data = res.json()
                prices = data.get("prices", [])
                print(f"SUCCESS for {hours} hours! Retrieved {len(prices)} candles.")
                break
            else:
                print(f"FAILED for {hours} hours. {res.text}")

if __name__ == "__main__":
    run_probe()
