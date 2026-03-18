# Analisi Approfondita del Progetto PROFETA

## 1. Panoramica del Sistema
**PROFETA Universal v5.0 PRODUCTION** è un avanzato sistema di previsione di serie temporali (*time series forecasting*), progettato specificamente per scenari enterprise multi-dominio (finanza/crypto, energia ed ecologia). È sviluppato interamente in Python (3.10+) e fa un uso estensivo di TensorFlow (2.15+) per l'addestramento e l'inferenza di reti neurali.

La caratteristica più innovativa della versione 5.x è l'approccio **Delta-Based**: il sistema non prevede il prezzo o il valore assoluto futuro, ma la **variazione** (delta) tra il valore attuale e quello futuro. Questo elimina in partenza il *mean-reversion bias* (previsioni piatte che inseguono la media), consentendo di raggiungere tassi di accuratezza elevatissimi (R² = 0.96 dichiarato per il mercato crypto) e garantendo che le classificazioni del trend (UP/DOWN/FLAT) siano dedotte in maniera sicura (100% agreement) dal regresso del delta.

## 2. Architettura del Software

Il codice, concentrato nel corposo file [profeta-universal.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py), è scritto sfruttando pattern object-oriented molto strutturati, tipici di soluzioni di livello enterprise: type hinting avanzato (`typing`), uso di classi virtuali e `dataclasses` per la definizioni dei profili e della configurazione, gestione delle eccezioni gerarchica ([PROFETAError](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#142-151)), e multi-threading.

I moduli principali implementati nell'architettura includono:

### 2.1 Gestione dell'Ambiente e GPU ([GPUManager](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#463-522))
Viene implementato un pattern singleton per gestire il multithreading e la concorrenza via OpenMP, oltre ad un set up automatico della GPU tramite TensorFlow per il calcolo con *mixed-precision* (FP16/FP32). Supporta strategie a singola GPU, Multi-GPU (`MirroredStrategy`), o fallback su CPU nel caso in cui CUDA o le GPU non siano compatibili (es. architettura Blackwell).

### 2.2 Profili di Dominio ([DomainProfile](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#527-586))
Il software pre-imposta insiemi di feature in base al dominio su cui deve operare:
- **Financial/Crypto**: Abilita feature di volume, indicazioni tecniche estese, volatilità, calcolo dei *rendimenti* (*returns*), ed eventalmente l'*order flow*.
- **Energy/Electricity**: Orientato su serie orarie e stagionalità multiple (24h/168h).
- **Environmental/Climate**: Focalizzato sui trend stagionali (365giorni).
- **Generic**: Un profilo base riadattabile per esperimenti su altri segnali.

### 2.3 Motore dei Dati e Pre-processing ([DataPreprocessor](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#973-1025))
È presente un robusto sistema per la validazione temporale e l'estrazione delle feature.
- Riconosce la **granularità** della serie (secondi, minuti, ore).
- Gestisce i "buchi" di dati ([GapHandler](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#950-972)) interpolando o propagando l'ultimo valore valido.
- Il [FeatureEngineer](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#653-741) estrae *Technical Indicators* in modo automatico: calcola Bande di Bollinger, MACD, RSI, Average True Range (ATR), oltre a trasformate cicliche (seno/coseno) per mappare ore e giorni della settimana in uno spazio coerente per le reti neurali. 
- Dispone di un **Volatility Analyzer** dinamico: a seconda della deviazione standard del mercato calcola il "regime" (LOW, NORMAL, HIGH, EXTREME), parametro fondamentale per adattare le soglie dei segnali (adaptive decay/thresholding).

### 2.4 Preparazione delle Sequenze ([SequencePreparator](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#1031-1269))
Usa vari scaler (`MinMaxScaler`, `StandardScaler`, `RobustScaler`) preparandole per l'algoritmo ricorrente (LSTM/GRU). La vera forza risiede nello *Scaling Canonico* del Target: il file modella e memorizza parametri interni del prezzo (come l'offset e lo scale factor) per riconvertire con precisione assoluta i *delta predetti* in prezzi di inferenza originali calcolando `prezzo_previsto = prezzo_ultimo_noto + predetto_delta_riconvertito`.

### 2.5 Multi-Head Neural Network Ensemble ([RegressionModelBuilder](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#1293-1330))
Il core AI è basato su reti **LSTM (Long-Short Term Memory)**, bidirezionali (`BiLSTM`) o `GRU`.
- Una tipica configurazione d'ensemble usa fino a 20 di queste reti neurali impilate. L'output passa attraverso strati di BatchNormalization e Multiple Head Attention prima di condensarsi tramite un `GlobalAveragePooling1D`.
- **Pure Regression:** Non esiste più una rete dedicata alla classificazione (rimossa dalla versione 5.3): il modello genera esclusivamente previsioni scalate dei Delta continui con output di attivazione *lineare*. 

### 2.6 Signal Generation e Classificazione derivata ([TrendLabeler](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#747-862) & [FusionStrategy](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta-universal.py#271-289))
Superando la classificazione da rete neurale delle versioni precedenti, il nuovo modulo **Fusion** ricava la direzione strettamente dalla magnitudine del Delta previsto:
- Se $Delta > 0.05\%$ del prezzo attuale: segnale UP (`BUY`).
- Se $Delta < -0.05\%$: segnale DOWN (`SELL`).
- Altrimenti segnale `FLAT` (`HOLD`).
Inoltre, produce un intervallo di "confidence" calcolando il rapporto tra il Delta predetto e il threshold, permettendo al sistema di filtrare segnali deboli ed isolare posizioni `STRONG_BUY` o `STRONG_SELL`.

## 3. Configuration & Bootstrapping
Il sistema viene istruito tramite un file [config-lstm.ini](file:///c:/work/PROFETA-UNIVERSAL-V5.0/config-lstm.ini). Un parser dedicato estrae dozzine di parametri, incapsulandoli in data class specializzate: 
- Parametri per il training (pazienza per l'early stopping, suddivisioni annidate "nested conformal" per training/calib/test che prevengono la contaminazione dei dati o *data leakage*).
- Parametri per ogni singolo modello dell'ensemble (numero di unit LSTM, dropout, sequence length), favorendo così la diversità nell'apprendimento.

### Strumenti a corredo
- **[profeta_report_generator.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/profeta_report_generator.py)**: Interfaccia per la generazione automatica di solidi report in PDF per consultare i risultati.
- **[Run_profeta_real_time.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/Run_profeta_real_time.py)** e **[real_time_data_download.py](file:///c:/work/PROFETA-UNIVERSAL-V5.0/real_time_data_download.py)**: Componenti adatti al deploy del sistema per connettersi a flussi dati remoti (es. exchange di trading in modalità *daemon*) per produrre report previsori in background.

## 4. Conclusioni
"Profeta" non è un semplice script di addestramento, è un ambiente produttivo completo. Il salto architetturale verso la predizione del *Delta* e la rimozione del dualismo tra rete di regressione e rete di classificazione risolvono abilmente i fastidiosi problemi di segnali contraddittori tipici dei bot di trading automatizzati. 
Il codice è manutenibile e denota uno standard enterprise molto alto, ideale per scenari di predizione ad altissima frequenza grazie al massiccio tuning apportato sul multithreading ed al supporto avanzato GPU.
