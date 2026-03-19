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

import configparser
import datetime
import subprocess
import time
from math import ceil

config = configparser.ConfigParser()
config.read("./config-lstm.ini")

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


def run_scripts(current_time: datetime.datetime):
    scripts = [
        [
            "./capital_data_download.py",
            "./Trading_live_data/dati-training.csv",
            "8000",
            current_time.isoformat(),
        ],
        [
            "./capital_data_download.py",
            "./Trading_live_data/dati-trading.csv",
            "1500",
            current_time.isoformat(),
        ],
        ["./profeta-universal.py"],
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
        run_scripts(current_time)
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

