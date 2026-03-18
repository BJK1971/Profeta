# Piano di Valutazione e Integrazione Trading con Profeta

Per valutare l'efficacia di PROFETA nel trading reale, procederemo in due fasi distinte: una rigorosa **Simulazione Storica (Backtesting)** e una successiva **Esecuzione Live su Conto Demo (es. Capital.com)**.

## Fase 1: Simulazione e Backtesting (Walk-Forward Validation)
L'obiettivo di questa fase è accertare se le previsioni delta-based di Profeta sono capaci di generare un reale vantaggio statistico (ed economico) al netto di costi di transazione e slippage.

✅ **Cosa abbiamo già:** 
- Una suite di backtest dedicata nella cartella `BKTEST/`.
- Un motore di *Walk-Forward Validation* per evitare l'overfitting.
- Metriche pronte all'uso (Sharpe, Drawdown, Win Rate, ecc.).

📌 **Azioni da compiere:**
1. Raccogliere e formattare un dataset storico ampio (almeno 1-2 anni di storico OHLCV) tramite gli script di download presenti nel progetto.
2. Configurare in maniera realistica [BKTEST/config-lstm-backtest.ini](file:///c:/work/PROFETA-UNIVERSAL-V5.0/BKTEST/config-lstm-backtest.ini) inserendo commissioni (es. `transaction_cost_pct`), capitale iniziale e parametri di validazione.
3. Eseguire l'analisi lanciando [profeta-backtest.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/BKTEST/profeta-backtest.py).
4. Analizzare il report generato (equity curve, profitti, loss) ed individuare la soglia operativa ottimale ([threshold](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#860-862)) per i trade.

## Fase 2: Integrazione Live su Conto Demo (Capital.com)
Se la fase 1 produce metriche come uno Sharpe Ratio > 1.5 e un Maximum Drawdown tollerabile, passeremo ad attaccare il sistema ad un reale conto demo.
Il framework integra già una cartella `cfx_markets/` contenente un client per le API. Attualmente lo script [Run_profeta_real_time.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/Run_profeta_real_time.py) scarica i dati ed esegue il modello regolarmente come "cronjob", ma non invia ordini di mercato.

📌 **Azioni da compiere:**
1. **Configurazione API:** Creare e validare le chiavi API del conto demo di Capital.com nel file [cfx_markets/config.json](file:///c:/work/PROFETA-UNIVERSAL-V5.0/cfx_markets/config.json).
2. **Sviluppo del Trading Bot:** 
   Sviluppare uno script (es. `profeta_trading_bot.py`) che:
   - Richiama [profeta-universal.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py) o ne legge gli output previsionali (es. file CSV/JSON nella cartella [output/](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#3989-4026)).
   - Usa la logica direzionale di Profeta v5.x (se delta predetto > threshold → segnale `BUY`).
   - Interagisce col modulo `cfx_markets/api_client` per inviare ordini `LONG` o `SHORT` a mercato.
3. **Gestione del Rischio Esecutiva:** Implementare parametri rigidi (Stop Loss percentuale, Take Profit o trailing stop, Size della posizione calcolata in base al margine di rischio) per evitare l'esposizione eccessiva del capitale.
4. **Testing in Simulativo Live:** Avviare lo script su server per un mese e validare che le posizioni vengano aperte nei mercati e chiuse in modo concorde a quanto loggato dal sistema.

## Prossimi Passi
Per procedere, possiamo iniziare a mettere a punto il backtesting oppure possiamo analizzare ed estendere subito il codice del Bot collegandolo alle API del broker. Da dove preferisci iniziare?
