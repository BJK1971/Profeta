import configparser
import json
import logging
from profeta_trading_bot import CapitalDemoBroker

def run_test():
    print("---------------------------------------------------------")
    print("      TEST AUTENTICAZIONE CAPITAL.COM DEMO API           ")
    print("---------------------------------------------------------")
    
    # Inizializzazione configurazione
    config = configparser.ConfigParser()
    try:
        config.read("./BKTEST/config-lstm-backtest.ini")
        k_key = config["CAPITAL_DEMO"]["api_key"]
        k_sec = config["CAPITAL_DEMO"]["api_secret"]
        k_pas = config["CAPITAL_DEMO"]["api_pass"]
    except KeyError:
        print("Errore: Credenziali CAPITAL_DEMO non trovate! Assicurati di aver compilato il blocco nel file .ini.")
        return

    # Inizializziamo il Broker
    broker = CapitalDemoBroker(api_key=k_key, api_secret=k_sec, api_pass=k_pas)
    
    # Disabilitare i fiumi di log per rendere l'output pulito
    broker.logger.setLevel(logging.ERROR)

    print(f"[*] Autenticazione con Identifier: {k_sec} ...")
    if broker.authenticate():
        print("[+] Autenticazione Riuscita! Token ricevuti correttamente.\n")
        
        # 1. Recupero Conti (Fondi e Margine)
        print("[*] Richiesta Saldi / Accounts...")
        accounts = broker.get_accounts()
        if accounts:
             print("[+] Dettagli Conti Ricevuti:")
             print(json.dumps(accounts, indent=4))
        else:
             print("[-] Recupero conti fallito o vuoti.")
             
        print("\n---------------------------------------------------------")
             
        # 2. Recupero Posizioni Aperte
        print("[*] Ricerca posizioni attualmente aperte a mercato...")
        positions = broker.get_open_positions()
        print(f"[+] Posizioni aperte sul conto: {len(positions)}")
        if positions:
             print(json.dumps(positions, indent=4))
             
        print("\n[✓] Test di connessione completato con successo. Nessun ordine eseguito.")
    else:
        print("[-] Autenticazione Scartata dal server Capital! Controlla password o la API KEY nel file .ini e riprova.")

if __name__ == "__main__":
    run_test()
