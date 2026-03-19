import json
from cfx_markets.api_client.client import ApiClient
from cfx_markets.api_client.auth import AwsApiAuth
import requests

def probe_api():
    client = ApiClient(
        username="testcfxquantum@gmail.com",
        password="Test1234!",
        base_url="https://api.aizenq.com"
    )

    # Elenco di possibili endpoints nascosti usati solitamente negli Swagger
    endpoints = [
        "/api/Instrument",
        "/api/Instruments",
        "/api/Market",
        "/api/Markets",
        "/api/Price/Instruments",
        "/api/Dictionary/Instruments",
        "/api/Dictionary/Markets"
    ]

    found = False
    
    for ep in endpoints:
        url = f"{client.base_url}{ep}"
        req = requests.Request("GET", url)
        res = client._execute_request(req)
        
        if res.success:
            print(f"\n[SUCCESSO] Endpoint Trovato: {url}")
            try:
                # Cerca EURUSD nel JSON
                data_str = json.dumps(res.data, indent=2)
                if "EUR" in data_str or "USD" in data_str:
                    print("Trovato riferimento a valute fiduciarie!!")
                print(data_str[:1500]) # Stampa il primo pezzo
                found = True
                break
            except Exception as e:
                print(f"Errore parsing: {e}")
        else:
            print(f"Fallito: {url}")
            
    if not found:
        print("\nNessun endpoint dizionario standard trovato. Controlleremo documentazione.")

if __name__ == "__main__":
    probe_api()
