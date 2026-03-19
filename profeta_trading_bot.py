import configparser
import logging
import time
from datetime import datetime, timezone

import pandas as pd
import requests

# Nota: per Capital.com integreremo le REST API ufficiali (demo-api-capital).
# Il bot si interpone tra il file output_predictions_path prodotto da "Run_profeta_real_time.py"
# ed il broker vero e proprio.


class CapitalDemoBroker:
    """Wrapper per le chiamate API verso Capital.com (Demo)"""

    def __init__(self, api_key: str, api_secret: str, api_pass: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_pass = api_pass
        self.base_url = "https://demo-api-capital.backend-capital.com/api/v1/"
        self.headers = {
            "X-CAP-API-KEY": self.api_key,
            # Placeholder: (Aggiungere logica di sessionToken auth, CST e X-SECURITY-TOKEN)
        }
        self.logger = logging.getLogger("CapitalDemo")
        self.logger.info("Broker Capital.com Demo Inizializzato.")

    def authenticate(self):
        """Autenticazione effettiva su Capital.com Demo API."""
        url = f"{self.base_url}session"
        payload = {
            "identifier": self.api_secret,  # In Capital.com l'identifier è tipicamente l'email/username
            "password": self.api_pass
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            # Estrae i token di sessione dagli header di risposta
            cst = response.headers.get("CST")
            sec_token = response.headers.get("X-SECURITY-TOKEN")
            
            if cst and sec_token:
                self.headers["CST"] = cst
                self.headers["X-SECURITY-TOKEN"] = sec_token
                self.logger.info("Autenticazione su Capital.com completata con successo. Token acquisiti.")
                return True
            else:
                self.logger.error("Autenticazione fallita: Token CST/X-SECURITY-TOKEN mancanti.")
                return False
                
        except Exception as e:
            self.logger.error(f"Errore durante l'autenticazione: {e}")
            return False

    def place_market_order(self, epic: str, direction: str, size: float, sl_points: int = None, tp_points: int = None):
        """
        Piazza un ordine a mercato sul conto usando le REST API reali.
        """
        url = f"{self.base_url}positions"
        payload = {
            "epic": epic,
            "direction": direction,
            "size": size,
            "guaranteedStop": False
        }
        
        # Aggiunta opzionale di Stop Loss e Take Profit in punti (distanza)
        if sl_points is not None:
            payload["stopDistance"] = str(sl_points)
        if tp_points is not None:
            payload["profitDistance"] = str(tp_points)
            
        
        try:
            self.logger.info(f"Invio ordine {direction} su {epic} (Size: {size})")
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Ordine eseguito: {data}")
            return data
        except requests.exceptions.HTTPError as he:
            if he.response.status_code == 401:
                self.logger.warning("Token scaduto (401) in place_order. Rialineamento e retry...")
                if self.authenticate():
                    return self.place_market_order(epic, direction, size, sl_points, tp_points)
            self.logger.error(f"Errore HTTP piazzamento ordine: {he}")
            return None
        except Exception as e:
            self.logger.error(f"Errore piazzamento ordine: {e}")
            return None

    def get_open_positions(self):
        """Ritorna le posizioni aperte sul conto."""
        url = f"{self.base_url}positions"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("positions", [])
        except requests.exceptions.HTTPError as he:
            if he.response.status_code == 401:
                self.logger.warning("Token scaduto (401). Tento la ri-autenticazione...")
                if self.authenticate():
                    return self.get_open_positions() # Riprova 1 volta
            self.logger.error(f"Errore HTTP recupero posizioni: {he}")
            return []
        except Exception as e:
            self.logger.error(f"Errore recupero posizioni: {e}")
            return []

    def get_accounts(self):
        """Recupera le informazioni sui conti (saldi, fondi disponibili, margini, ecc)."""
        url = f"{self.base_url}accounts"
        try:
            self.logger.info("Richiesta informazioni conto (Accounts)...")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Errore recupero conti: {e}")
            return None

    def close_all_positions(self, epic: str = None):
        """Chiude le posizioni dell'asset specifiato richiamando il DELETE."""
        positions = self.get_open_positions()
        closed_count = 0
        
        for pos in positions:
            market = pos.get("market", {})
            position_epic = market.get("epic", "")
            
            if epic is None or position_epic == epic:
                pos_details = pos.get("position", {})
                deal_id = pos_details.get("dealId")
                if deal_id:
                    url = f"{self.base_url}positions/{deal_id}"
                    try:
                        resp = requests.delete(url, headers=self.headers)
                        resp.raise_for_status()
                        self.logger.info(f"Posizione {deal_id} su {position_epic} chiusa.")
                        closed_count += 1
                    except requests.exceptions.HTTPError as he:
                        if he.response.status_code == 401:
                            if self.authenticate():
                                return self.close_all_positions(epic) # Ricomincia dall'inizio con posizioni fresche
                        self.logger.error(f"Errore HTTP chiusura {deal_id}: {he}")
                    except Exception as e:
                        self.logger.error(f"Errore in chiusura {deal_id}: {e}")
                        
        return True if closed_count > 0 else False


class ProfetaTradingBot:
    """Bot esecutivo che collega l'intelligenza di Profeta a Capital.com"""

    def __init__(self, config_path: str):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        # Estrai Epic
        try:
            self.epic = self.config["CAPITAL_DEMO"].get("epic", "BTCUSD")
        except KeyError:
            self.epic = "BTCUSD"

        # Percorso in cui l'Ensemble salva le previsioni ad ogni step dal file .ini
        base_predictions_path = self.config["PREDICTION"]["output_predictions_path"]
        
        # Se il file base esiste, usalo, altrimenti applica il suffisso dell'epic
        # Per coerenza, preferiamo il file con suffisso se l'epic è definito
        if self.epic:
            self.predictions_path = base_predictions_path.replace(".csv", f"_{self.epic}.csv")
        else:
            self.predictions_path = base_predictions_path
        
        # Inizializza logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        self.logger = logging.getLogger("ProfetaTradingBot")
        
        # Estrai chiavi se configurate, altrimenti mock fallback
        try:
            k_key = self.config["CAPITAL_DEMO"]["api_key"]
            k_sec = self.config["CAPITAL_DEMO"]["api_secret"]
            k_pas = self.config["CAPITAL_DEMO"]["api_pass"]
        except KeyError:
            k_key, k_sec, k_pas = "DEMO_KEY", "DEMO_SECRET", "DEMO_PASS"

        # Inizializza Broker e tenta Auth (in locale potrebbe fallire se non hai messo le chiavi)
        self.broker = CapitalDemoBroker(api_key=k_key, api_secret=k_sec, api_pass=k_pas)
        self.broker.authenticate()

        self.last_processed_tms = None

        # Parametri Operativi e di Rischio (Risk Management) dal file INI
        self.epic = self.config.get("CAPITAL_DEMO", "epic", fallback="BTCUSD")
        self.trade_size = self.config.getfloat("CAPITAL_DEMO", "trade_size", fallback=0.01)
        self.sl_pts = self.config.getint("CAPITAL_DEMO", "sl_pts", fallback=100)
        self.tp_pts = self.config.getint("CAPITAL_DEMO", "tp_pts", fallback=300)
        self.activation_threshold = self.config.getfloat("CAPITAL_DEMO", "activation_threshold", fallback=0.001)


    def run_cycle(self):
        """Legge periodicamente l'ultimo file CSV dell'ensemble."""
        # --- Monitoraggio P/L Posizioni Aperte ---
        try:
            open_pos = self.broker.get_open_positions()
            if open_pos:
                total_upl = 0.0
                log_entries = []
                for p in open_pos:
                    epic_name = p.get("market", {}).get("epic", "UNKNOWN")
                    pos = p.get("position", {})
                    direction = pos.get("direction", "")
                    size = float(pos.get("size", 0))
                    open_level = float(pos.get("level", 0))
                    
                    # Estrazione P/L dal JSON restituito da Capital.com (spesso definito 'upl').
                    upl = float(pos.get("upl", 0.0))
                    total_upl += upl
                    
                    upl_pct = 0.0
                    if size > 0 and open_level > 0:
                        trade_value = size * open_level
                        upl_pct = (upl / trade_value) * 100 if trade_value > 0 else 0.0
                    
                    log_entries.append(f"[{direction} {size} {epic_name} -> P/L: {upl:.2f} $ ({upl_pct:+.2f}%)]")
                
                self.logger.info(f"STATUS TRADES: {', '.join(log_entries)} | TOTALE P/L: {total_upl:.2f} $")
        except Exception:
             pass # Silenzioso su errori di rete isolati
        # ----------------------------------------

        try:
            # Carica in poling le previsioni appena sfornate
            df = pd.read_csv(self.predictions_path)
            
            if df.empty:
                return

            # --- Ricerca del Segnale Migliore sull'intero Orizzonte ---
            # Invece di guardare solo horizon=1 (spesso piatto per candele orarie), cerchiamo l'orizzonte
            # con il segnale direzionale più forte tra tutti quelli predetti.
            best_row = None
            max_abs_change = -1.0

            for idx, row in df.iterrows():
                try:
                    chg = float(row.get("change_pct", 0))
                    d = int(row.get("direction", 0))
                    # Consideriamo solo se la direzione non è FLAT (0)
                    if d != 0 and abs(chg) > max_abs_change:
                        max_abs_change = abs(chg)
                        best_row = row
                except Exception:
                    pass

            if best_row is not None and max_abs_change > self.activation_threshold:
                last_row = best_row
                horizon_found = int(last_row.get("horizon", 0))
                target_time = last_row.get("timestamp", last_row.get("Date", f"+{horizon_found}h"))
                actual_chg = float(last_row.get("change_pct", 0))
                self.logger.info(f"Strategia: Il picco direzionale previsto è alle ore {target_time} (Horizon: +{horizon_found}h) con variazione del {actual_chg*100:+.3f}%")
            else:
                # Fallback standard su horizon=1
                if "horizon" in df.columns:
                    df_horizon = df[df["horizon"] == 1]
                    if not df_horizon.empty:
                        last_row = df_horizon.iloc[-1]
                    else:
                        last_row = df.iloc[-1]
                else:
                    last_row = df.iloc[-1]
            
            # Catturiamo il timestamp del momento base (riga 0) per tracciare il "ciclo",
            # altrimenti il bot eseguirebbe trade continui per un semplice scostamento del best horizon.
            if "timestamp" in df.columns:
                current_tms = df.iloc[0]["timestamp"] if not df.empty else last_row["timestamp"]
            elif "Date" in df.columns:
                current_tms = df.iloc[0]["Date"] if not df.empty else last_row["Date"]
            else:
                current_tms = str(datetime.now(timezone.utc))

            if current_tms == self.last_processed_tms:
                # Silenzioso se il ciclo temporale "base" non evolve
                return
            
            self.last_processed_tms = current_tms
            
            # Parametri dalla predizione
            try:
                predicted_val = float(last_row.get("predicted_value", 0))
                change_pct = float(last_row.get("change_pct", 0))
                direction = int(last_row.get("direction", 0)) # 1 (BUY), -1 (SELL), 0 (HOLD)
            except ValueError:
                self.logger.error("Errore conversione campi predizione")
                return

            self.logger.info(f"Nuovo Ciclo Valutazione {current_tms} | Orizzonte Target: {last_row.get('horizon', 'N/A')} | Prezzo Previsto: {predicted_val:.2f} | Variazione Stimata: {change_pct*100:.5f}% | Direzione: {direction}")

            # Logic: usa la predizione di change_pct combinata con la direzione del modello
            
            # --- Inibizione Ordini Duplicati ---
            # Controlliamo la direzione netta voluta
            target_direction_str = None
            if direction == 1 and change_pct > self.activation_threshold:
                target_direction_str = "BUY"
            elif direction == -1 and abs(change_pct) > self.activation_threshold:
                target_direction_str = "SELL"
                
            if target_direction_str:
                # Controlla cosa bolle in pentola su Capital.com
                open_pos = self.broker.get_open_positions()
                current_market_dir = None
                
                # Cerca l'epic corrente
                for p in open_pos:
                    if p.get("market", {}).get("epic") == self.epic:
                        current_market_dir = p.get("position", {}).get("direction")
                        break
                        
                if current_market_dir == target_direction_str:
                    target_time = last_row.get("timestamp", last_row.get("Date", "Sconosciuta"))
                    self.logger.info(f"Conferma Strategia: Manteniamo aperta la posizione {current_market_dir} su {self.epic}. Le previsioni confermano il target per le ore {target_time}.")
                    return
                elif current_market_dir is not None and current_market_dir != target_direction_str:
                    # Direzione cambiata rispetto a quella aperta: liquida tutto
                    self.logger.info(f"Inversione di trand da {current_market_dir} a {target_direction_str}. Chiusura posizioni in corso!")
                    self.broker.close_all_positions(self.epic)
                else:
                    # Nessuna posizione, ma abbiamo un target. Liquida sicurezze (es. monete pendenti) se ci sono
                    pass
            # ------------------------------------

            # Buy se la direzione è UP (1) e il cambiamento stimato supera la soglia di attivazione
            if target_direction_str == "BUY":
                 self.logger.info("SEGNALE LONG SCATTATO: Esecuzione ordine di BUY a Mercato")
                 self.broker.place_market_order(self.epic, "BUY", self.trade_size, self.sl_pts, self.tp_pts)
            
            # Sell se la direzione è DOWN (-1) e la magnitudo del crollo stimato (-change_pct) supera la soglia
            elif target_direction_str == "SELL":
                 self.logger.info("SEGNALE SHORT SCATTATO: Esecuzione ordine di SELL (Short) a Mercato")
                 self.broker.place_market_order(self.epic, "SELL", self.trade_size, self.sl_pts, self.tp_pts)
            else:
                 self.logger.info(f"Il Modello Consiglia HOLD: direzione {direction} o delta perc {change_pct*100:.5f}% sotto soglia.")

        except FileNotFoundError:
            self.logger.error(f"File previsioni non trovato (forse in fase di rendering). Attendere la prima esecuzione di 'Run_profeta_real_time.py' su: {self.predictions_path}")
        except Exception as e:
            self.logger.error(f"Errore ciclo trading: {e}")


def main():
    # File conf generato pre-backtesting
    config_file = "./BKTEST/config-lstm-backtest.ini"
    bot = ProfetaTradingBot(config_file)
    
    bot.logger.info("Profeta Live Bot Inizializzato (Modalità Daemone). Ascolto predizioni...")
    print("---------------------------------------------------------------")
    
    while True:
        bot.run_cycle()
        time.sleep(30) # Poll ogni 30 secondi in cron


if __name__ == "__main__":
    main()
