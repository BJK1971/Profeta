# Differenziazione File per Asset (Multi-Epic Support)

L'obiettivo è permettere a Profeta di gestire più asset contemporaneamente (es. BTCUSD e EURUSD) senza che i file di dati e previsioni si sovrappongano. Il sistema diventerà "Epic-aware", aggiungendo automaticamente il nome dell'asset ai file generati.

## Proposed Changes

### 1. `Run_profeta_real_time.py`
Modificheremo l'orchestratore per:
- Leggere l'asset `epic` dal file di configurazione.
- Generare nomi file dinamici per i dati di training e trading (es. `dati-training_EURUSD.csv`).
- Passare questi percorsi corretti agli script di download.

### 2. `profeta_trading_bot.py`
Modificheremo l'inizializzazione del bot per:
- Rilevare l'asset `epic`.
- Cercare il file delle previsioni aggiungendo il suffisso dell'epic (es. `real_time_ens_hours_EURUSD.csv`) se quello di base non esiste o per coerenza.

### 3. `profeta-universal.py`
Aggiorneremo il caricamento della configurazione per:
- Appendere il suffisso `_{epic}` ai percorsi di output delle previsioni e ai percorsi dei dati di input, garantendo l'isolamento dei modelli e dei risultati.

## Parametri da Riga di Comando (Command-Line Overrides)

Abbiamo aggiunto il supporto per i seguenti parametri in tutti gli script principali:
- `--config <path>`: Permette di specificare un file .ini diverso da quello di default.
- `--epic <value>`: Permette di sovrascrivere l'asset `epic` definito nel file .ini.

### Dettagli Tecnici
- **`profeta-universal.py`**: Accetta `--config` e `--epic`. L'epic sovrascrive quello in `[CAPITAL_DEMO]`.
- **`profeta_trading_bot.py`**: Accetta `--config` e `--epic`. Inizializza il bot con l'asset specificato.
- **`Run_profeta_real_time.py`**: Accetta `--config` e `--epic` e li propaga agli script figli.

---

## Verification Plan

### Test Automatici/Manuali
1. Eseguire `python Run_profeta_real_time.py --epic BTCUSD`.
2. Verificare che i dati vengano scaricati in `dati-training_BTCUSD.csv`.
3. Verificare che il training salvi i modelli in `./models/BTCUSD/`.
4. Eseguire `python profeta_trading_bot.py --epic BTCUSD`.
5. Verificare che il bot cerchi `real_time_ens_hours_BTCUSD.csv`.
