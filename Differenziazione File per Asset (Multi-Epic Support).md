# Differenziazione File per Asset (Multi-Epic Support)

L'obiettivo è permettere a Profeta di gestire più asset contemporaneamente (es. BTCUSD e EURUSD) senza che i file di dati e previsioni si sovrappongano. Il sistema diventerà "Epic-aware", aggiungendo automaticamente il nome dell'asset ai file generati.

## Proposed Changes

### 1. [Run_profeta_real_time.py](file:///c:/work/gitrepo/Profeta/Run_profeta_real_time.py)
Modificheremo l'orchestratore per:
- Leggere l'asset `epic` dal file di configurazione.
- Generare nomi file dinamici per i dati di training e trading (es. `dati-training_EURUSD.csv`).
- Passare questi percorsi corretti agli script di download.

### 2. [profeta_trading_bot.py](file:///c:/work/gitrepo/Profeta/profeta_trading_bot.py)
Modificheremo l'inizializzazione del bot per:
- Rilevare l'asset `epic`.
- Cercare il file delle previsioni aggiungendo il suffisso dell'epic (es. `real_time_ens_hours_EURUSD.csv`) se quello di base non esiste o per coerenza.

### 3. [profeta-universal.py](file:///c:/work/gitrepo/Profeta/profeta-universal.py)
Aggiorneremo il caricamento della configurazione per:
- Appendere il suffisso `_{epic}` ai percorsi di output delle previsioni e ai percorsi dei dati di input, garantendo l'isolamento dei modelli e dei risultati.

---

## Verification Plan

### Test Manuali
1. Impostare `epic = EURUSD` in [config-lstm-backtest.ini](file:///c:/work/gitrepo/Profeta/BKTEST/config-lstm-backtest.ini).
2. Avviare [Run_profeta_real_time.py](file:///c:/work/gitrepo/Profeta/Run_profeta_real_time.py).
3. Verificare che nella cartella `Trading_live_data` appaiano i file col suffisso `_EURUSD`.
4. Verificare che nella cartella `PREVISIONI` appaia il file `real_time_ens_hours_EURUSD.csv`.
5. Verificare che il bot legga correttamente il file specifico.
