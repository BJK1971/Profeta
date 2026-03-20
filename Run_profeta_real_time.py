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
import subprocess
import time
import os
from math import ceil

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

# Determina l'epic
epic_override = args.epic
if epic_override:
    epic = epic_override
else:
    epic = config["CAPITAL_DEMO"].get("epic", "BTCUSD")

interval = config["PREDICTION"].get("freq", fallback="H")


def calculate_waiting_time(
    interval: str,
) -> tuple[datetime.timedelta, datetime.datetime]:
    current_time = datetime.datetime.now(datetime.timezone.utc)
    match interval:
        case "H":
            # Sincronizza esattamente sulla prossima ora solare (+ 1 min di ritardo tecnico API broker)
            waiting_time = datetime.timedelta(hours=1, minutes=1)
            current_time = current_time.replace(minute=0, second=0, microsecond=0)
        case "M":
            waiting_time = datetime.timedelta(minutes=10)
            current_time = current_time.replace(second=0, microsecond=0)
        case _:
            print("Intervallo non valido, impostato a 3 ore.")
            waiting_time = datetime.timedelta(hours=3)

    return waiting_time, current_time


def run_scripts(current_time: datetime.datetime, config_path: str, epic: str):

    train_csv = f"./Trading_live_data/dati-training_{epic}.csv"
    trade_csv = f"./Trading_live_data/dati-trading_{epic}.csv"

    scripts = [
        [
            "./capital_data_download.py",
            train_csv,
            "8000",
            current_time.isoformat(),
            "--config", config_path,
            "--epic", epic,
        ],
        [
            "./capital_data_download.py",
            trade_csv,
            "1500",
            current_time.isoformat(),
            "--config", config_path,
            "--epic", epic,
        ],
        ["./profeta-universal.py", "--config", config_path, "--epic", epic],
    ]
    for script in scripts:
        try:
            print(f"Esecuzione di {script}...")
            # Esegue lo script Python
            subprocess.run(["python"] + script, check=True)
            print(f"Completato: {script[0]}\n")
        except subprocess.CalledProcessError as e:
            print(f"Errore durante l'esecuzione di {script}: {e}\n")
        except FileNotFoundError:
            print(
                f"Script non trovato: {script}. Assicurati che sia nella stessa directory o fornisci il percorso completo.\n"
            )


if __name__ == "__main__":
    while True:
        waiting_time, current_time = calculate_waiting_time(interval)
        print("\n--- Inizio ciclo di esecuzione ---\n")
        run_scripts(current_time, config_path, epic)
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
        print(f"\n--- Fine ciclo. Attesa per {hours}h {minutes}m {seconds}s ---\n")
        for remaining in range(waiting_time_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"Tempo rimanente: {mins:02d}:{secs:02d}", end="\r")
            time.sleep(1)

