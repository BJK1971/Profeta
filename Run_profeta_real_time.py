"""
Spiegazione dello script
Lista dei programmi Python:

Lo script contiene un elenco (scripts) dei file Python da eseguire in ordine.
Gestione degli intervalli:

Usa time.sleep(interval) per attendere 15 minuti (900 secondi)
prima di iniziare un nuovo ciclo.
Esecuzione dei programmi:

Ogni programma viene eseguito utilizzando subprocess.run, che esegue i file Python in un sottoprocesso.
Gestione degli errori:

Se un file non viene trovato o un programma restituisce un errore, il programma registra
il problema e passa al successivo.
Compatibilità:

Assicurati che lo script sia eseguito nella stessa directory in cui si trovano gli altri script,
o aggiorna i percorsi degli script con i relativi path completi."""

import argparse
import configparser
import datetime
import logging
import os
import subprocess
import sys
import time
from math import ceil

# Import per market check ibrido
from check_market_hybrid import check_market_status

parser = argparse.ArgumentParser(description="Profeta Real-Time Orchestrator")
parser.add_argument('--config', help='Path del file di configurazione (.ini)')
parser.add_argument('--epic', help='Override dell\'asset Epic (es. BTCUSD)')
args = parser.parse_args()

# Determina il file di configurazione
if args.config:
    config_path = args.config
else:
    # Default: scorri i classici nomi file
    config_path = "./config-lstm.ini" if os.path.exists("./config-lstm.ini") else "./BKTEST/config-lstm-backtest.ini"

config = configparser.ConfigParser()
config.read(config_path)

# Carica scheduling config (opzionale)
schedule_config = configparser.ConfigParser()
schedule_config.read('orchestrator-schedule.ini')

# Determina l'epic
epic_override = args.epic
if epic_override:
    epic = epic_override
else:
    epic = config["CAPITAL_DEMO"].get("epic", "BTCUSD")

# Determina minuto di scheduling per questo epic
# Se non configurato, usa 0 (default)
if schedule_config.has_section('SCHEDULING'):
    SCHEDULE_MINUTE = schedule_config.getint('SCHEDULING', epic, fallback=0)
else:
    SCHEDULE_MINUTE = 0

interval = config["PREDICTION"].get("freq", fallback="H")


def calculate_waiting_time(
    interval: str,
    schedule_minute: int = 0,
) -> tuple[datetime.timedelta, datetime.datetime]:
    """
    Calcola tempo di attesa per sincronizzare orchestrator.
    
    Args:
        interval: 'H' (hourly), 'M' (10 min), etc.
        schedule_minute: Minuto dell'ora in cui partire (0-59)
        
    Returns:
        (waiting_time, current_time)
    """
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    match interval:
        case "H":
            # Sincronizza sul minuto configurato
            # Es: schedule_minute=10 → parte alle :10 di ogni ora
            waiting_time = datetime.timedelta(hours=1)
            
            # Se siamo PRIMA del minuto configurato, aspetta fino a quello
            # Se siamo DOPO, aspetta il minuto configurato dell'ora prossima
            if current_time.minute < schedule_minute:
                # Stessa ora, minuto configurato
                delta_minutes = schedule_minute - current_time.minute
            else:
                # Ora prossima, minuto configurato
                delta_minutes = (60 - current_time.minute) + schedule_minute
            
            waiting_time = datetime.timedelta(minutes=delta_minutes)
            current_time = current_time.replace(minute=schedule_minute, second=0, microsecond=0)
            
        case "M":
            # 10 minuti (non usato per scheduling)
            waiting_time = datetime.timedelta(minutes=10)
            current_time = current_time.replace(second=0, microsecond=0)
            
        case _:
            print("Intervallo non valido, impostato a 3 ore.")
            waiting_time = datetime.timedelta(hours=3)

    return waiting_time, current_time


def check_market_open(config_path: str, epic: str, logger) -> bool:
    """
    Verifica se il mercato è aperto prima di eseguire il training.
    Usa il sistema ibrido (TradingHours + fallback locale).
    
    Args:
        config_path: Percorso file configurazione
        epic: Epic da verificare
        logger: Logger instance
        
    Returns:
        bool: True se mercato aperto
    """
    try:
        # Usa check_market_hybrid
        result = check_market_status(epic, config_path)
        
        if result['is_open']:
            logger.info(f"✅ {result['message']} (Provider: {result.get('provider', 'unknown')})")
            return True
        else:
            reason = result.get('reason', 'Motivo sconosciuto')
            logger.info(f"❌ {result['message']}")
            logger.info(f"   Reason: {reason}")
            logger.info("Skip training/prediction - mercato chiuso")
            return False
            
    except Exception as e:
        logger.warning(f"Errore market check: {e} - procedo comunque")
        return True  # Fallback: procedi se errore


def run_scripts(current_time: datetime.datetime, config_path: str, epic: str):
    # Get absolute path to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    train_csv = os.path.join(script_dir, f"Trading_live_data/dati-training_{epic}.csv")
    trade_csv = os.path.join(script_dir, f"Trading_live_data/dati-trading_{epic}.csv")

    scripts = [
        [
            os.path.join(script_dir, "capital_data_download.py"),
            train_csv,
            "8000",
            current_time.isoformat(),
            "--config", config_path,
            "--epic", epic,
        ],
        [
            os.path.join(script_dir, "capital_data_download.py"),
            trade_csv,
            "1500",
            current_time.isoformat(),
            "--config", config_path,
            "--epic", epic,
        ],
        [os.path.join(script_dir, "profeta-universal.py"), "--config", config_path, "--epic", epic],
    ]
    for script in scripts:
        try:
            print(f"Esecuzione di {script}...")
            # Use sys.executable to get the correct Python interpreter
            import sys
            subprocess.run([sys.executable] + script, check=True, cwd=script_dir)
            print(f"Completato: {script[0]}\n")
        except subprocess.CalledProcessError as e:
            print(f"Errore durante l'esecuzione di {script}: {e}\n")
        except FileNotFoundError as e:
            print(
                f"Script non trovato: {script}. Assicurati che sia nella stessa directory o fornisci il percorso completo.\n"
            )


if __name__ == "__main__":
    # Setup logging - Centralizzato in ~/Profeta/logs/
    log_dir = os.path.expanduser("~/Profeta/logs")
    os.makedirs(log_dir, exist_ok=True)
    # NOTA: Non creiamo più log file qui, usa solo StreamHandler
    # nohup redirect gestisce il logging su file

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.StreamHandler()  # Solo console, nohup scrive su file
        ],
        force=True  # Forza reset configurazione precedente
    )
    logger = logging.getLogger("ProfetaOrchestrator")
    
    logger.info("=" * 70)
    logger.info(f"PROFETA ORCHESTRATOR - EPIC: {epic}")
    logger.info(f"Config: {config_path}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Scheduling: minuto :{SCHEDULE_MINUTE} di ogni ora")
    logger.info("=" * 70)
    
    while True:
        # Calcola tempo di attesa PRIMA di eseguire (con scheduling)
        waiting_time, current_time = calculate_waiting_time(interval, SCHEDULE_MINUTE)
        
        # Calcola quando dovrebbe iniziare il prossimo ciclo
        next_time = current_time + waiting_time
        waiting_time_seconds = (
            ceil(
                (
                    next_time - datetime.datetime.now(datetime.timezone.utc)
                ).total_seconds()
            )
            if next_time > datetime.datetime.now(datetime.timezone.utc)
            else 1
        )
        
        hours, remainder = divmod(waiting_time_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info("")
        logger.info(f"--- Inizio ciclo di esecuzione (attesa: {hours}h {minutes}m {seconds}s) ---")
        logger.info("")
        
        # Check mercato prima di eseguire
        logger.info("Verifica stato mercato...")
        if not check_market_open(config_path, epic, logger):
            logger.info("")
            logger.info("⚠️  Mercato CHIUSO - Skip ciclo corrente")
            logger.info(f"⏱️  Prossimo tentativo tra {waiting_time}")
            logger.info("")
        else:
            logger.info("")
            logger.info("✅ Mercato APERTO - Esecuzione training/prediction")
            logger.info("")
            run_scripts(current_time, config_path, epic)
        
        # Ora attendi fino al prossimo ciclo
        logger.info("")
        logger.info(f"--- Fine ciclo. Attesa per {hours}h {minutes}m {seconds}s ---")
        logger.info("")
        for remaining in range(waiting_time_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"Tempo rimanente: {mins:02d}:{secs:02d}", end="\r")
            time.sleep(1)

