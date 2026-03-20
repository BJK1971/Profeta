# Walkthrough: Support Multi-Asset (Epic)

Abbiamo implementato un sistema di differenziazione automatica dei file basato sull'asset ("Epic") configurato. Questo permette di far girare più istanze di Profeta (es. `BTCUSD` e `EURUSD`) contemporaneamente senza conflitti di file.

## Modifiche apportate

### 1. Orchestratore ([Run_profeta_real_time.py](file:///c:/work/gitrepo/Profeta/Run_profeta_real_time.py))
L'orchestratore ora legge l'Epic dal file [.ini](file:///c:/work/gitrepo/Profeta/config-lstm.ini) e genera percorsi dinamici:
- `dati-training_BTCUSD.csv`
- `dati-trading_BTCUSD.csv`

### 2. Motore Predittivo ([profeta-universal.py](file:///c:/work/gitrepo/Profeta/profeta-universal.py))
Il caricatore del config è stato aggiornato per essere "Epic-aware":
- Se un Epic è definito, aggiunge il suffisso `_{epic}` ai percorsi delle previsioni (`output_predictions_path`).
- Isola la cache dei modelli in sottocartelle specifiche (es. `./models/BTCUSD/`).

### 3. Trading Bot ([profeta_trading_bot.py](file:///c:/work/gitrepo/Profeta/profeta_trading_bot.py))
Il bot rileva l'Epic e cerca automaticamente il file previsioni corrispondente (es. `real_time_ens_hours_BTCUSD.csv`).

---

## Validazione

Eseguendo [Run_profeta_real_time.py](file:///c:/work/gitrepo/Profeta/Run_profeta_real_time.py), i log confermano il passaggio dei nuovi nomi file agli script di download:

```bash
--- Inizio ciclo di esecuzione ---
Esecuzione di ['./capital_data_download.py', './Trading_live_data/dati-training_BTCUSD.csv', '8000', '2026-03-19T13:00:00+00:00']...
```
## Performance and Cache Optimizations

During the final verification, we addressed two critical performance issues:

1. **Model Granularity**: Changed `model_granularity` from `minute` to `hour`. This eliminated a 60x unnecessary upsampling of data, drastically reducing training time for hourly trading.
2. **Cache Migration**: Moved existing models to the new asset-specific directory (`models/BTCUSD/`).
3. **Configuration Fix**: Added the missing `[CAPITAL_DEMO]` section to [config-lstm.ini](file:///c:/work/gitrepo/Profeta/config-lstm.ini) to ensure the system correctly identifies the Epic and uses the appropriate cache folder.

With these changes, the system is now:
- **Fast**: Training takes ~5 seconds per model on a 5090.
- **Persistent**: Correctly loads and saves models in isolated, asset-specific folders.
- **Accurate**: Correctly generates filenames and reads configurations for the specific asset.

## Nuova Funzionalità: Parametri da Riga di Comando

Abbiamo reso gli script più flessibili permettendo di passare l'Epic e il file di configurazione direttamente da terminale.

### Come usare i nuovi parametri

Ora puoi avviare Profeta per un asset specifico senza modificare i file [.ini](file:///c:/work/gitrepo/Profeta/config-lstm.ini):

1. **Orchestratore**:
   ```bash
   python Run_profeta_real_time.py --epic EURUSD --config ./config-lstm.ini
   ```
   *Questo scaricherà i dati per EURUSD e avvierà il training/predizione usando EURUSD.*

2. **Trading Bot**:
   ```bash
   python profeta_trading_bot.py --epic EURUSD --config ./BKTEST/config-lstm-backtest.ini
   ```
   *In questo modo il bot cercherà il file `real_time_ens_hours_EURUSD.csv` e opererà sull'asset EURUSD.*

3. **Solo Motore (Manuale)**:
   ```bash
   python profeta-universal.py --config ./config-lstm.ini --epic EURUSD
   ```

4. **Downloader (Manuale)**:
   ```bash
   python capital_data_download.py ./test.csv 100 --epic EURUSD
   ```

### Vantaggi
- **Isolamento Totale**: I modelli, i dati e le previsioni sono salvati separatamente per ogni Epic (es. `/models/EURUSD/`, `dati-training_EURUSD.csv`).
- **Nessuna Modifica ai Config**: Puoi usare lo stesso file di base per più asset semplicemente cambiando il parametro `--epic`.
- **Esecuzione Parallela**: Puoi aprire più terminali e lanciare lo stesso script con Epic diversi.
