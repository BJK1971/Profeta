# Real Time Trading Predictor Data Download
"""Lo script si collega alla banca dati utilizzando la stringa fornita, scarica i dati e li salva nel file dati-trading.json.
Assicurati di avere la libreria requests installata. Se non è installata, puoi aggiungerla eseguendo:

pip install requests
"""

# Codice:
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

from cfx_markets.api_client.client import ApiClient
from cfx_markets.models import AggMethod, IntervalUnit


# URL e intestazioni per la richiesta
def download_data(reference_datetime: datetime):
    client = ApiClient(
        username="testcfxquantum@gmail.com",
        password="Test1234!",
        base_url="https://api.aizenq.com",
    )

    # url = "https://cfxqprod00.develop.portguardian.com/api/Price/candle/Minute/1/1/1?method=AggregatedCandlesticks&count=13380"
    # url = "https://cfxqprod00.develop.portguardian.com/api/Price/candle/Minute/1/1/1?method=AggregatedCandlesticks&count=600"
    # headers = {
    #     "accept": "text/plain",
    #     "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0IiwianRpIjoiZjZiNjhkYTgtNWVjOS00MmNkLTg3MmEtMjJhODBhOWUwMzc5IiwidXNlcm5hbWUiOiIxMjM0IiwiZGlzcGxheW5hbWUiOiIxMjM0IiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiRGF0YVJlYWRlciIsImV4cCI6MTc3MDEwODEyNSwiaXNzIjoiQ0ZYUVRlY2hTZXJ2aWNlcyIsImF1ZCI6IkNGWFFUZWNoU2VydmljZXMifQ.j_yGSQ_Zojz6nJVaNo-_07ZzEiGPqUwYo3Ar9NbSpao",
    # }

    # Directory di output
    output_dir = r"./Trading_live_data"
    # output_dir = r"Trading_live_data"

    os.makedirs(output_dir, exist_ok=True)

    # File di output JSON
    json_file_path = os.path.join(output_dir, "dati-trading.json")

    try:
        # response = requests.get(url, headers=headers)
        # response.raise_for_status()
        #Instrumneti ID,(1=bitcoin 2=ethereum) Market ID
        data = client.get_exchange_candles(
            1,
            1,
            IntervalUnit.minute,
            1,
            AggMethod.agg_candlesticks,
            count=13380,
            sort_mode=None,
            end=reference_datetime,
        )
        # Salva i dati in un file JSON
        with open(json_file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Dati scaricati e salvati in '{json_file_path}'")

    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta: {e}")
    except Exception as e:
        print(f"Errore generale: {e}")

    return json_file_path


def convert_json_to_csv(json_file_path, csv_file_path):
    """
    Converte un file JSON in un file CSV e ordina i dati dal più lontano al più recente in base al timestamp.

    :param json_file_path: Percorso del file JSON di input
    :param csv_file_path: Percorso del file CSV di output
    """
    try:
        # Legge il file JSON
        with open(json_file_path, "r") as file:
            data = json.load(file)

        # Estrae i dati dalla chiave "$values"
        records = data.get("$values", [])

        # Converte i dati in un DataFrame Pandas
        df = pd.DataFrame(records)

        # Verifica che la colonna tms esista
        if "tms" not in df.columns:
            raise KeyError("La colonna 'tms' non esiste nei dati JSON.")

        # Rinomina il campo "last" in "close" se esiste
        if "last" in df.columns:
            df.rename(columns={"last": "close"}, inplace=True)

        # Rinomina la colonna "tms" in "timestamp_column"
        df.rename(columns={"tms": "timestamp_column"}, inplace=True)

        # Converte il timestamp in formato datetime e ordina i dati
        df["timestamp_column"] = pd.to_datetime(df["timestamp_column"])
        df.sort_values(by="timestamp_column", ascending=True, inplace=True)

        # Salva il DataFrame come file CSV
        df.to_csv(csv_file_path, index=False)
        print(
            f"Conversione completata e dati ordinati. File CSV salvato in: {csv_file_path}"
        )

    except KeyError as e:
        print(f"Errore nella struttura dei dati: {e}")
    except Exception as e:
        print(f"Errore durante la conversione: {e}")


# Percorsi dei file
output_dir = r"./Trading_live_data"
# output_dir = r"Trading_live_data"

os.makedirs(output_dir, exist_ok=True)
json_file_path = os.path.join(output_dir, "dati-trading.json")
csv_file_path = os.path.join(output_dir, "dati-trading.csv")
reference_datetime = datetime.now(timezone.utc)  # Data e ora di riferimento
if len(sys.argv) > 1:
    reference_datetime = datetime.fromisoformat(sys.argv[1])
# Scarica i dati e convertili in CSV
if os.path.exists(download_data(reference_datetime)):
    convert_json_to_csv(json_file_path, csv_file_path)
else:
    print(f"Errore: Il file JSON non è stato trovato in {json_file_path}")


