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
import fcntl
import logging
import os
import subprocess
import sys
import time
from math import ceil

# ─── GPU Lock ───────────────────────────────────────────────────────────────
# File lock condiviso tra tutti gli orchestratori per serializzare i training.
# Solo profeta-universal.py (GPU-intensive) viene protetto dal lock.
GPU_LOCK_PATH = "/tmp/profeta_gpu.lock"

def acquire_gpu_lock(epic: str, logger, timeout: int = 1800):
    """Attende finché la GPU è libera, poi acquisisce il lock."""
    lock_file = open(GPU_LOCK_PATH, "a+")
    start = time.time()
    while True:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.write(f"{epic}:{os.getpid()}")
            lock_file.flush()
            logger.info(f"GPU lock acquisito per {epic}")
            return lock_file
        except BlockingIOError:
            elapsed = int(time.time() - start)
            if elapsed > timeout:
                logger.warning(f"Timeout GPU lock ({timeout}s). Procedo comunque.")
                return lock_file
            if elapsed % 30 == 0:
                lock_file.seek(0)
                owner = lock_file.read().strip() or "sconosciuto"
                logger.info(f"GPU occupata ({owner}), attesa... [{elapsed}s]")
            time.sleep(10)

def release_gpu_lock(lock_file, epic: str, logger):
    """Rilascia il lock GPU."""
    try:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        logger.info(f"GPU lock rilasciato da {epic}")
    except Exception:
        pass
# ─────────────────────────────────────────────────────────────────────────────

# Import per market check ibrido
from check_market_hybrid import check_market_status

parser = argparse.ArgumentParser(description="Profeta Real-Time Orchestrator")
parser.add_argument('--config', help='Path del file di configurazione (.ini)')
parser.add_argument('--epic', help='Override dell\'asset Epic (es. BTCUSD)')
parser.add_argument('--force-now', action='store_true', help='Esegui subito il primo ciclo senza aspettare lo slot schedulato')
args = parser.parse_args()

# Determina il file di configurazione
if args.config:
    config_path = args.config
else:
    # Default: scorri i classici nomi file
    config_path = "./config-lstm.ini" if os.path.exists("./config-lstm.ini") else "./BKTEST/config-lstm-backtest.ini"

config = configparser.ConfigParser()
config.read(config_path)

# Carica scheduling config (opzionale) - Usa percorso assoluto
script_dir = os.path.dirname(os.path.abspath(__file__))
schedule_config_path = os.path.join(script_dir, 'orchestrator-schedule.ini')
schedule_config = configparser.ConfigParser()
schedule_config.read(schedule_config_path)

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
    logger = logging.getLogger("ProfetaOrchestrator")

    train_csv = os.path.join(script_dir, f"Trading_live_data/dati-training_{epic}.csv")
    trade_csv = os.path.join(script_dir, f"Trading_live_data/dati-trading_{epic}.csv")

    # Download dati (non GPU-intensive, eseguiti senza lock)
    train_candles = str(config["DATA"].getint("train_candles", fallback=8000))
    download_scripts = [
        [
            os.path.join(script_dir, "capital_data_download.py"),
            train_csv, train_candles, current_time.isoformat(),
            "--config", config_path, "--epic", epic,
        ],
        [
            os.path.join(script_dir, "capital_data_download.py"),
            trade_csv, "1500", current_time.isoformat(),
            "--config", config_path, "--epic", epic,
        ],
    ]
    for script in download_scripts:
        try:
            print(f"Esecuzione di {script[0]}...")
            subprocess.run([sys.executable] + script, check=True, cwd=script_dir)
            print(f"Completato: {script[0]}\n")
        except subprocess.CalledProcessError as e:
            print(f"Errore durante l'esecuzione di {script}: {e}\n")
        except FileNotFoundError:
            print(f"Script non trovato: {script[0]}\n")

    # Training LSTM (GPU-intensive): serializzato tramite GPU lock
    training_script = [os.path.join(script_dir, "profeta-universal.py"), "--config", config_path, "--epic", epic]
    lock_file = acquire_gpu_lock(epic, logger)
    try:
        print(f"Esecuzione di {training_script[0]}...")
        subprocess.run([sys.executable] + training_script, check=True, cwd=script_dir)
        print(f"Completato: {training_script[0]}\n")
    except subprocess.CalledProcessError as e:
        print(f"Errore durante l'esecuzione di profeta-universal.py: {e}\n")
    except FileNotFoundError:
        print(f"Script non trovato: {training_script[0]}\n")
    finally:
        release_gpu_lock(lock_file, epic, logger)


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
    logger.info(f"Scheduling: minuto :{SCHEDULE_MINUTE} di ogni ora")
    logger.info("=" * 70)
    
    # Esegui SUBITO il primo ciclo (senza attesa)
    # Lo scheduling si applica solo dai cicli successivi
    first_cycle = True

    while True:
        # Salva il tempo attuale PRIMA di calcolare l'attesa
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Calcola tempo di attesa per il PROSSIMO ciclo (con scheduling)
        waiting_time, current_time = calculate_waiting_time(interval, SCHEDULE_MINUTE)

        # Calcola quando dovrebbe iniziare il prossimo ciclo
        next_time = now + waiting_time
        waiting_time_seconds = int(ceil(waiting_time.total_seconds()))

        hours, remainder = divmod(waiting_time_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        logger.info("")
        logger.info(f"--- Inizio ciclo di esecuzione ---")
        logger.info("")

        # SE È IL PRIMO CICLO: esegui SUBITO, poi aspetta per i cicli successivi
        if first_cycle:
            logger.info("PRIMO CICLO: Esecuzione immediata (scheduling si applica dai cicli successivi)")
            logger.info("")
            first_cycle = False
        else:
            # Cicli successivi: aspetta il tempo schedulato
            logger.info(f"⏱️  Attesa di {hours}h {minutes}m {seconds}s per allineamento scheduling...")
            logger.info("")
            for remaining in range(waiting_time_seconds, 0, -1):
                mins, secs = divmod(remaining, 60)
                print(f"Tempo rimanente: {mins:02d}:{secs:02d}", end="\r")
                time.sleep(1)
            print()  # Newline after countdown

        # Check mercato prima di eseguire
        logger.info("Verifica stato mercato...")
        if not check_market_open(config_path, epic, logger):
            logger.info("")
            logger.info("⚠️  Mercato CHIUSO - Skip ciclo corrente")
            logger.info(f"⏱️  Prossimo tentativo tra {hours}h {minutes}m {seconds}s")
            logger.info("")
        else:
            logger.info("")
            logger.info("✅ Mercato APERTO - Esecuzione training/prediction")
            logger.info("")
            run_scripts(current_time, config_path, epic)

        # Attendi fino al prossimo ciclo
        logger.info("")
        logger.info(f"--- Fine ciclo. Prossima esecuzione tra {hours}h {minutes}m {seconds}s ---")
        logger.info("")
        for remaining in range(waiting_time_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"Prossimo ciclo: {mins:02d}:{secs:02d}", end="\r")
            time.sleep(1)

