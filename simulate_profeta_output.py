import csv
import os
import time
from datetime import datetime

# Path su cui si incrocia il Bot
CSV_PATH = "/home/ubuntu/PROFETA-UNIVERSAL-V5.0/PREVISIONI/real_time_ens_hours.csv"
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

# Oscillazione del prezzo previsto per ingannare il bot: 
# Prezzo Attuale (close): fisso a 1000$ per semplicità
# La prediction balzerà tra 1010$ (+1%, BUY) e 990$ (-1%, SELL)
predictions = [1010.0, 1010.0, 990.0, 990.0]

def main():
    print(f"[{datetime.now()}] Inizio simulazione Profeta Ensemble.")
    print(f"Scrittura file in: {CSV_PATH}")
    print("---------------------------------------------------------")
    
    # Scrivi Heders
    try:
        with open(CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_column", "close", "prediction"])
    except Exception as e:
        print(f"Errore scrittura CSV: {e}")
        return

    i = 0
    while True:
        tms_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        curr_prediction = predictions[i % len(predictions)]
        
        # Scrivi a file l'ultima candela simulata
        # Nota: usiamo 'a' (append) ma il csv logger del bot legge solo l'ultima riga
        with open(CSV_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([tms_now, 1000.0, curr_prediction])
            
        print(f"[{tms_now}] Emessa candela | Attuale: 1000.0 | Previsto: {curr_prediction}")
        
        i += 1
        time.sleep(10) # Pausa di 10 secondi per permettere al bot (in polling a 30s) di accorgersene

if __name__ == "__main__":
    main()
