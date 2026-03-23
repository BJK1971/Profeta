import configparser
import logging
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

# Import per market check ibrido
from check_market_hybrid import check_market_status

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

    def check_market_status(self, epic: str) -> dict:
        """
        Verifica lo stato del mercato per un dato epic usando Capital.com API.
        Strategia: Controlla se ci sono prezzi recenti.
        
        Args:
            epic: Strumento da verificare (es: EURUSD, BTCUSD)
            
        Returns:
            dict: {
                'is_open': bool,
                'status': str,
                'epic': str,
                'message': str
            }
        """
        from datetime import datetime, timedelta
        
        # Usa endpoint prices - Capital.com richiede parametri specifici
        url = f"{self.base_url}prices/{epic}"
        
        # Capital.com ha un limite di 400 ore per richiesta
        # Per market check, prendiamo solo ultime 6 ore
        now = datetime.now(timezone.utc)
        from_time = now - timedelta(hours=6)
        
        # Parametri per Capital.com API
        params = {
            'resolution': 'MINUTE',
            'from': from_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': now.strftime('%Y-%m-%dT%H:%M:%S'),
            'max': '5'  # Solo ultimi 5 prezzi
        }
        
        try:
            # Usa params invece di URL-encoded manuale
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 404:
                self.logger.warning(f"Epic {epic} non trovato su Capital.com")
                return {
                    'is_open': False,
                    'status': 'NOT_FOUND',
                    'epic': epic,
                    'message': f'Epic {epic} non trovato',
                    'bid': None,
                    'offer': None
                }
            
            response.raise_for_status()
            data = response.json()
            prices = data.get('prices', [])
            
            if not prices or len(prices) == 0:
                result = {
                    'is_open': False,
                    'status': 'NO_DATA',
                    'epic': epic,
                    'message': f'Mercato {epic}: CHIUSO (nessun prezzo disponibile)',
                    'bid': None,
                    'offer': None
                }
                self.logger.info(result['message'])
                return result
            
            # Prendi l'ultimo prezzo
            last_price = prices[-1]
            bid = last_price.get('closePrice', {}).get('bid')
            ask = last_price.get('closePrice', {}).get('ask')
            snapshot_time = last_price.get('snapshotTimeUTC', '')
            
            # Verifica se il prezzo è recente (ultimi 30 minuti)
            try:
                price_time = datetime.fromisoformat(snapshot_time.replace('Z', '+00:00'))
                time_diff = now - price_time
                is_recent = time_diff.total_seconds() < 1800  # 30 minuti
            except:
                is_recent = False
            
            # Determina se mercato aperto
            is_open = False
            if bid and ask and bid > 0 and ask > 0 and is_recent:
                is_open = True
                status_msg = f"Mercato {epic}: APERTO (Bid: {bid}, Ask: {ask})"
            else:
                if not is_recent:
                    status_msg = f"Mercato {epic}: CHIUSO (prezzi vecchi di {time_diff.total_seconds()/60:.0f} min)"
                else:
                    status_msg = f"Mercato {epic}: CHIUSO (dati non disponibili)"
            
            result = {
                'is_open': is_open,
                'status': 'OPEN' if is_open else 'CLOSED',
                'epic': epic,
                'message': status_msg,
                'bid': bid,
                'offer': ask,
                'last_update': snapshot_time
            }
            
            self.logger.info(status_msg)
            return result
            
        except requests.exceptions.HTTPError as he:
            self.logger.error(f"Errore HTTP check mercato {epic}: {he}")
            return {
                'is_open': True,  # Fallback: procedi se errore HTTP
                'status': 'ERROR',
                'epic': epic,
                'message': f'Errore HTTP: {he}',
                'bid': None,
                'offer': None
            }
        except Exception as e:
            self.logger.error(f"Errore check mercato {epic}: {e}")
            return {
                'is_open': True,  # Fallback: procedi se errore generico
                'status': 'ERROR',
                'epic': epic,
                'message': f'Check fallito, procedo con cautela: {e}',
                'bid': None,
                'offer': None
            }

    def confirm_order(self, deal_reference: str) -> dict:
        """
        Verifica l'esito definitivo di un ordine tramite l'endpoint /confirms.
        Capital.com è asincrono: dealReference != conferma esecuzione.
        """
        url = f"{self.base_url}confirms/{deal_reference}"
        time.sleep(2)  # Attende elaborazione asincrona Capital.com
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            status = data.get("dealStatus", "UNKNOWN")
            reason = data.get("reason", "")
            deal_id = data.get("dealId", "")
            if status == "ACCEPTED":
                self.logger.info(f"Ordine CONFERMATO: dealId={deal_id} status={status}")
            else:
                self.logger.error(f"Ordine RIGETTATO: status={status} reason={reason} | dettagli: {data}")
            return data
        except Exception as e:
            self.logger.error(f"Errore conferma ordine {deal_reference}: {e}")
            return {}

    def place_market_order(self, epic: str, direction: str, size: float, sl_points: float = None, tp_points: float = None):
        """
        Piazza un ordine a mercato sul conto usando le REST API reali.
        stopDistance e profitDistance sono in pips/punti (unità nativa Capital.com).
        - EURUSD: 1 pip = 0.0001, sl_pts=60 → stopDistance=60 pips → ΔP=0.006 → P/L=size×0.006
        - BTCUSD/NVDA: sl_pts in USD direttamente → stopDistance=sl_pts USD
        """
        url = f"{self.base_url}positions"

        payload = {
            "epic": epic,
            "direction": direction,
            "size": size,
            "guaranteedStop": False
        }

        # stopDistance/profitDistance: Capital.com usa distanza PREZZO per forex, punti USD per crypto.
        # EURUSD/forex: sl_pts=60 pips → 60×0.0001=0.006 prezzo distance
        # BTCUSD/NVDA/azioni: sl_pts già in USD → nessuna conversione
        sl_distance = sl_points
        tp_distance = tp_points
        if epic in ('EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY', 'AUDUSD', 'USDCAD', 'USDCHF'):
            if sl_points is not None:
                sl_distance = round(sl_points * 0.0001, 6)
            if tp_points is not None:
                tp_distance = round(tp_points * 0.0001, 6)

        if sl_distance is not None and sl_distance > 0:
            payload["stopDistance"] = sl_distance
        if tp_distance is not None and tp_distance > 0:
            payload["profitDistance"] = tp_distance

        try:
            self.logger.info(f"Invio ordine {direction} su {epic} (Size: {size}, SL: {sl_points} pts, TP: {tp_points} pts)")
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            deal_ref = data.get("dealReference", "")
            self.logger.info(f"Ordine inviato: dealReference={deal_ref}")
            # Verifica conferma asincrona Capital.com
            if deal_ref:
                self.confirm_order(deal_ref)
            return data
        except requests.exceptions.HTTPError as he:
            if he.response.status_code == 401:
                self.logger.warning("Token scaduto (401) in place_order. Rialineamento e retry...")
                if self.authenticate():
                    return self.place_market_order(epic, direction, size, sl_points, tp_points)
            self.logger.error(f"Errore HTTP piazzamento ordine: {he} - Dettagli: {he.response.text}")
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
            if he.response.status_code in (400, 401):
                self.logger.warning(f"Sessione scaduta ({he.response.status_code}) in get_positions. Ri-autenticazione...")
                if self.authenticate():
                    return self.get_open_positions()
            self.logger.error(f"Errore HTTP recupero posizioni: {he}")
            return []
        except Exception as e:
            self.logger.error(f"Errore recupero posizioni: {e}")
            return []

    def get_accounts(self):
        """Recupera le informazioni sui conti (saldi, fondi disponibili, margini, ecc)."""
        url = f"{self.base_url}accounts"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            accounts = data.get("accounts", [])
            for acc in accounts:
                balance = acc.get("balance", {}).get("balance", 0)
                deposit = acc.get("balance", {}).get("deposit", 0)
                self.logger.info(f"ACCOUNT INFO | Propr.: {acc.get('accountName')} | Balance: {balance} {acc.get('currency')} | Equity: {deposit}")
            return data
        except requests.exceptions.HTTPError as he:
            if he.response.status_code in (400, 401):
                self.logger.warning(f"Sessione scaduta ({he.response.status_code}) in get_accounts. Ri-autenticazione...")
                if self.authenticate():
                    return self.get_accounts()
            self.logger.error(f"Errore recupero conti: {he}")
            return None
        except Exception as e:
            self.logger.error(f"Errore recupero conti: {e}")
            return None

    def get_market_info(self, epic: str):
        """Recupera le info di mercato per un epic specifico (es. minDealSize)."""
        url = f"{self.base_url}markets/{epic}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as he:
            if he.response.status_code == 401:
                if self.authenticate():
                    return self.get_market_info(epic)
            self.logger.error(f"Errore HTTP recupero info mercato per {epic}: {he}")
            return None
        except Exception as e:
            self.logger.error(f"Errore recupero info mercato per {epic}: {e}")
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

    def __init__(self, config_path: str, epic_override=None):
        self.config_path = config_path  # Salva per market check
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        # Override Epic if provided
        self.epic = epic_override
        if not self.epic:
            self.epic = self.config["CAPITAL_DEMO"].get("epic", "BTCUSD")

        # Inizializza logger - Solo StreamHandler (nohup gestisce il file)
        # force=True assicura di sovrascrivere eventuali handler precedenti
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            handlers=[
                logging.StreamHandler()  # Solo console, nohup scrive su file
            ],
            force=True  # Forza reset configurazione precedente
        )
        self.logger = logging.getLogger("ProfetaTradingBot")
        
        # Percorso previsioni (renderlo epic-aware)
        base_path = self.config["PREDICTION"].get("output_predictions_path", "./PREVISIONI/real_time_ens_hours.csv")
        if self.epic and self.epic not in base_path:
            self.predictions_path = base_path.replace(".csv", f"_{self.epic}.csv")
        else:
            self.predictions_path = base_path

        # Estrai chiavi se configurate, altrimenti mock fallback
        try:
            k_key = self.config["CAPITAL_DEMO"]["api_key"]
            k_sec = self.config["CAPITAL_DEMO"]["api_secret"]
            k_pas = self.config["CAPITAL_DEMO"]["api_pass"]
        except KeyError:
            k_key, k_sec, k_pas = "DEMO_KEY", "DEMO_SECRET", "DEMO_PASS"

        # Inizializza Broker e tenta Auth
        self.broker = CapitalDemoBroker(api_key=k_key, api_secret=k_sec, api_pass=k_pas)
        self.broker.authenticate()

        self.last_processed_tms = None
        self.last_position_open = False  # Traccia se la posizione era aperta al ciclo precedente
        self.last_auth_time = time.time()  # Per re-auth preventivo ogni 8 minuti

        # Lettura Base Parametri Operativi e Rischio
        size_key = f"trade_size_{self.epic}"
        self.trade_size = self.config["CAPITAL_DEMO"].getfloat(size_key, fallback=self.config["CAPITAL_DEMO"].getfloat("trade_size", 0.01))

        sl_key = f"sl_pts_{self.epic}"
        self.sl_pts = self.config["CAPITAL_DEMO"].getfloat(sl_key, fallback=self.config["CAPITAL_DEMO"].getfloat("sl_pts", 2000))
        
        tp_key = f"tp_pts_{self.epic}"
        self.tp_pts = self.config["CAPITAL_DEMO"].getfloat(tp_key, fallback=self.config["CAPITAL_DEMO"].getfloat("tp_pts", 4000))

        self.activation_threshold = self.config["CAPITAL_DEMO"].getfloat("activation_threshold", 0.0002)

        # -------------------------------------------------------------
        # ALLINEAMENTO DINAMICO REQ MINIMI DELL'API (SIZE, SL, TP)
        # -------------------------------------------------------------
        try:
            market_info = self.broker.get_market_info(self.epic)
            if market_info and "dealingRules" in market_info:
                rules = market_info["dealingRules"]
                
                # Size Adeguamento
                min_deal_size = rules.get("minDealSize", {}).get("value")
                if min_deal_size is not None:
                    min_deal_size = float(min_deal_size)
                    self.logger.info(f"API Capital.com riporta minDealSize = {min_deal_size} per {self.epic}")
                    if self.trade_size < min_deal_size:
                        self.logger.warning(f"La size configurata ({self.trade_size}) è minore del minimo. Adeguamento a {min_deal_size}")
                        self.trade_size = min_deal_size
                
                # SL / TP: usa i valori dalla config senza override automatici.
                # I valori sono già calibrati per ottenere ~50€ SL e ~100€ TP per asset.
                        
        except Exception as e:
            self.logger.error(f"Errore nel recupero dinamico info mercato: {e}")
        # -------------------------------------------------------------
        

    def run_cycle(self):
        """Legge periodicamente l'ultimo file CSV dell'ensemble."""
        
        # --- MARKET CHECK: Verifica se mercato è aperto ---
        try:
            config_path = self.config_path if hasattr(self, 'config_path') else 'BKTEST/config-lstm-backtest.ini'
            market_result = check_market_status(self.epic, config_path)
            
            if not market_result['is_open']:
                reason = market_result.get('reason', 'Motivo sconosciuto')
                self.logger.info(f"❌ Mercato {self.epic}: CHIUSO ({reason}) - Skip trading cycle")
                return  # Skip questo ciclo
            else:
                self.logger.debug(f"✅ Mercato {self.epic}: APERTO")
        except Exception as e:
            self.logger.warning(f"Errore market check: {e} - procedo comunque")
        
        # --- Re-auth preventivo ogni 8 minuti (token Capital.com scadono ~10 min) ---
        if time.time() - self.last_auth_time > 480:
            self.logger.debug("Re-autenticazione preventiva token Capital.com...")
            if self.broker.authenticate():
                self.last_auth_time = time.time()

        # --- Monitoraggio Conti ---
        try:
            self.broker.get_accounts()
        except Exception:
            pass
            
        # --- Monitoraggio P/L Posizioni Aperte ---
        epic_position_open = self.last_position_open  # Default: assume invariato se errore di rete
        try:
            open_pos = self.broker.get_open_positions()
            epic_position_open = any(p.get("market", {}).get("epic") == self.epic for p in open_pos)
            # Filtra solo le posizioni dell'epic di questo bot
            my_positions = [p for p in open_pos if p.get("market", {}).get("epic") == self.epic]
            if my_positions:
                total_upl = 0.0
                log_entries = []
                for p in my_positions:
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

                    log_entries.append(f"[{direction} {size} {self.epic} -> P/L: {upl:.2f} $ ({upl_pct:+.2f}%)]")

                self.logger.info(f"STATUS TRADES: {', '.join(log_entries)} | P/L: {total_upl:.2f} $")
            else:
                self.logger.debug(f"Nessuna posizione aperta su {self.epic}.")
        except Exception:
             pass # Silenzioso su errori di rete isolati

        # Rilevamento chiusura inattesa della posizione (SL/TP/chiusura manuale)
        # Se al ciclo precedente la posizione era aperta e ora non c'è più,
        # resettiamo last_processed_tms per forzare una nuova valutazione del segnale
        # anche se il timestamp del CSV non è ancora cambiato.
        if self.last_position_open and not epic_position_open:
            self.logger.info(f"Posizione {self.epic} chiusa (SL/TP/manuale). Forzo ri-valutazione segnale.")
            self.last_processed_tms = None
        self.last_position_open = epic_position_open
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
                
                # Check soglia
                diff_from_limit = abs(change_pct) - self.activation_threshold
                check_status = "OK" if abs(change_pct) > self.activation_threshold else "SOTTO SOGLIA"
            except (ValueError, TypeError):
                self.logger.error("Errore conversione campi predizione")
                return

            self.logger.info(f"VALUTAZIONE CICLO {current_tms} | Asset: {self.epic}")
            self.logger.info(f"  > Orizzonte: +{last_row.get('horizon', 'N/A')}h | Prezzo Previsto: {predicted_val:.4f}")
            self.logger.info(f"  > Variazione: {change_pct*100:+.5f}% vs Soglia: {self.activation_threshold*100:.5f}% [{check_status}]")
            self.logger.info(f"  > Direzione Modello: {'LONG' if direction==1 else 'SHORT' if direction==-1 else 'HOLD'}")

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
                    return  # Già aperto, non fare nulla
                elif current_market_dir is not None and current_market_dir != target_direction_str:
                    # Direzione cambiata rispetto a quella aperta: liquida tutto
                    self.logger.info(f"Inversione di trend da {current_market_dir} a {target_direction_str}. Chiusura posizioni in corso!")
                    self.broker.close_all_positions(self.epic)
                    # Dopo aver chiuso, procedi con apertura nuova posizione
                    self.logger.info(f"Posizione chiusa, apro nuova posizione {target_direction_str}...")
                # else: Nessuna posizione aperta, procedi con apertura
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
    import argparse
    parser = argparse.ArgumentParser(description="Profeta Trading Bot")
    parser.add_argument('--config', default="./BKTEST/config-lstm-backtest.ini", help='Config file path')
    parser.add_argument('--epic', help='Override asset Epic (e.g. BTCUSD)')
    args = parser.parse_args()
    
    bot = ProfetaTradingBot(args.config, epic_override=args.epic)
    
    bot.logger.info(f"Profeta Live Bot Inizializzato per {bot.epic} (Modalità Daemone). Ascolto predizioni...")
    print("---------------------------------------------------------------")
    
    while True:
        bot.run_cycle()
        time.sleep(30) # Poll ogni 30 secondi in cron


if __name__ == "__main__":
    main()
