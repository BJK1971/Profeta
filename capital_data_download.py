import sys
import os
import configparser
import logging
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | CapitalDownloader | %(message)s")

class CapitalDataDownloader:
    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        
        self.api_key = config["CAPITAL_DEMO"]["api_key"]
        self.api_secret = config["CAPITAL_DEMO"]["api_secret"]
        self.api_pass = config["CAPITAL_DEMO"]["api_pass"]
        self.epic = config["CAPITAL_DEMO"].get("epic", "BTCUSD")
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

    def download_historical_data(self, bars_count: int, reference_datetime: datetime):
        if not self.authenticate():
            raise Exception("Fallimento autenticazione su Capital.com")
            
        all_bars = []
        # Capital regge un limite rigido per blocco su alcuni asset prima di dare invalid.max.daterange
        max_chunk = 400 
        
        # current_to rappresenta la "testa" della paginazione all'indietro
        current_to = reference_datetime
        
        while len(all_bars) < bars_count:
            url = f"{self.base_url}prices/{self.epic}"
            chunk_size = min(max_chunk, bars_count - len(all_bars))
            
            # Calcoliamo "from" togliendo X ore
            from_time = current_to - timedelta(hours=chunk_size)
            
            # Capital API accetta il formato YYYY-MM-DDTHH:MM:SS senza Z
            to_str = current_to.strftime("%Y-%m-%dT%H:%M:%S")
            from_str = from_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            params = {
                "resolution": "HOUR",
                "from": from_str,
                "to": to_str,
                "max": chunk_size
            }
            
            logging.info(f"Scaricamento blocco: {from_str} -> {to_str} ({chunk_size} candele)")
            res = requests.get(url, headers=self.headers, params=params)
            
            if not res.ok:
                logging.error(f"Errore API {res.status_code}: {res.text}")
                break
                
            data = res.json()
            prices = data.get("prices", [])
            
            if not prices:
                logging.warning("Capolinea storico raggiunto: API non restituisce altri dati antecedenti.")
                break
                
            # Siccome Capital restituisce dalla più vecchia alla più recente, inseriamole in testa alla lista
            all_bars = prices + all_bars
            current_to = from_time
            
        # Potremmo aver scaricato candele in esubero se i gap festivi falsavano la stima del timedelta, 
        # tuttavia 1500 ore lavorative nel forex sono meno di 1500 ore totali (chiusura weekend).
        # Adatteremo il troncamento finale alla fine
        return all_bars

    def format_and_save(self, bars, output_path, bars_count):
        records = []
        for b in bars:
            try:
                # Utilizziamo la stringa UTC di snapshot
                tms_str = b.get("snapshotTimeUTC")
                close_val = b["closePrice"]["bid"]
                # CapitalPrice {"bid": X, "ask": Y}
                
                records.append({
                    "timestamp_column": tms_str,
                    "close": close_val,
                    "open": b["openPrice"]["bid"],
                    "high": b["highPrice"]["bid"],
                    "low": b["lowPrice"]["bid"],
                    "volume": b["lastTradedVolume"]
                })
            except KeyError:
                continue

        df = pd.DataFrame(records)
        df["timestamp_column"] = pd.to_datetime(df["timestamp_column"])
        
        # Elimina eventuali duplicati ai bordi della paginazione
        df.drop_duplicates(subset="timestamp_column", inplace=True)
        
        # Ordina classicamente dal passato al presente
        df.sort_values(by="timestamp_column", ascending=True, inplace=True)
        
        # Mantiene solo le X candele richieste esatte, prendendo le più recenti
        # nel caso la stima ne abbia prese di più
        df = df.tail(bars_count)
        
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        df.to_csv(output_path, index=False)
        logging.info(f"Sincronizzazione di {len(df)} candele completata su {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        logging.error("Uso: python capital_data_download.py <target_file_csv> <bars_count> [reference_iso_datetime]")
        sys.exit(1)
        
    target_csv = sys.argv[1]
    raw_count = int(sys.argv[2])
    
    # Se un parametro orario è passato, usiamo quello, sennò NOW(UTC)
    ref_datetime = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if len(sys.argv) > 3:
        try:
            # Pulisce la Z di isoformat per datetime nativo
            clean_str = sys.argv[3].replace("Z", "+00:00")
            ref_datetime = datetime.fromisoformat(clean_str)
        except Exception:
            pass

    # Usiamo il config di backtest che è quello manipolato per contenere la configurazione unificata
    config_ini = "config-lstm.ini"
    if os.path.exists("./BKTEST/config-lstm-backtest.ini"):
        config_ini = "./BKTEST/config-lstm-backtest.ini"

    downloader = CapitalDataDownloader(config_ini)
    logging.info(f"Avvio Download {raw_count} candele per [{downloader.epic}] -> Destinazione: {target_csv}")
    
    bars = downloader.download_historical_data(raw_count, ref_datetime)
    downloader.format_and_save(bars, target_csv, raw_count)
    logging.info(f"Processo concluso per [{downloader.epic}].")
