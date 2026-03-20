# PROFETA - Guida Multi-Epic

## 📌 Panoramica

PROFETA supporta nativamente il trading su **multipli asset** (epic) contemporaneamente:
- **Crypto**: BTCUSD, ETHUSD, XRPUSD, etc.
- **Forex**: EURUSD, GBPUSD, USDJPY, etc.
- **Stocks**: AAPL, TSLA, NVDA, etc.
- **Commodities**: GOLD, SILVER, OIL, etc.

---

## 🎯 Utilizzo del Parametro `--epic`

### Comando Base

```bash
# Sintassi
python profeta-universal.py <CONFIG> --epic <EPIC_NAME>

# Esempi
python profeta-universal.py config-lstm.ini --epic EURUSD
python profeta-universal.py config-lstm.ini --epic BTCUSD
python profeta-universal.py config-lstm.ini --epic ETHUSD
```

### Orchestratore Real-Time

```bash
# Singolo epic
python Run_profeta_real_time.py --epic EURUSD

# Con config specifico
python Run_profeta_real_time.py --config BKTEST/config-lstm-EURUSD.ini --epic EURUSD
```

---

## 📁 Struttura File Multi-Epic

### Dati di Training

Ogni epic ha i suoi file CSV dedicati:

```
Trading_live_data/
├── dati-training_EURUSD.csv
├── dati-trading_EURUSD.csv
├── dati-training_BTCUSD.csv
├── dati-trading_BTCUSD.csv
├── dati-training_ETHUSD.csv
└── dati-trading_ETHUSD.csv
```

### Modelli Salvati

I modelli sono organizzati per epic:

```
models/
├── EURUSD/
│   ├── profeta_model_1.keras
│   ├── profeta_model_2.keras
│   └── ...
├── BTCUSD/
│   ├── profeta_model_1.keras
│   ├── profeta_model_2.keras
│   └── ...
└── ETHUSD/
    └── ...
```

### Output

```
output/
├── predictions_EURUSD.csv
├── predictions_EURUSD.json
├── predictions_BTCUSD.csv
└── predictions_BTCUSD.json
```

---

## 🔧 Script di Gestione Multi-Epic

### `run-epic.sh` - Epic Manager

Script bash per gestire automaticamente i diversi epic:

```bash
# Usage
./run-epic.sh <EPIC> [MODE]

# Modi disponibili
./run-epic.sh EURUSD          # Full cycle (train + predict)
./run-epic.sh BTCUSD train    # Solo training
./run-epic.sh ETHUSD predict  # Solo predizione
./run-epic.sh EURUSD realtime # Modalità real-time
```

### Vantaggi di `run-epic.sh`

1. ✅ **Configurazione automatica** - Crea config specifici se non esistono
2. ✅ **Attivazione conda** - Attiva automaticamente l'ambiente
3. ✅ **Logging separato** - Log dedicati per ogni epic
4. ✅ **Cache organizzata** - Modelli salvati in directory separate

---

## ⚙️ Configurazione per Epic

### Creare Config Specifico

```bash
# Copia il config base
cp BKTEST/config-lstm-backtest.ini BKTEST/config-lstm-EURUSD.ini

# Modifica l'epic
sed -i 's/^epic = .*/epic = EURUSD/' BKTEST/config-lstm-EURUSD.ini

# Esegui
python profeta-universal.py BKTEST/config-lstm-EURUSD.ini --epic EURUSD
```

### Parametri per Tipo di Asset

#### **Forex (EURUSD, GBPUSD)**
```ini
[DOMAIN]
type = financial
subtype = forex
use_returns = true
use_volatility = true
use_volume_features = false    ; Volume limitato nel forex
use_order_flow = false         ; Non disponibile
use_technical_indicators = true

[FUSION]
delta_threshold_pct = 0.0005   ; 0.05% tipico per forex
min_confidence = 0.35
signal_threshold = 0.55
```

#### **Crypto (BTCUSD, ETHUSD)**
```ini
[DOMAIN]
type = financial
subtype = crypto
use_returns = true
use_volatility = true
use_volume_features = true
use_order_flow = true          ; Disponibile per crypto
use_technical_indicators = true

[FUSION]
delta_threshold_pct = 0.001    ; 0.1% per crypto (più volatile)
min_confidence = 0.35
signal_threshold = 0.55
```

#### **Stocks (AAPL, TSLA)**
```ini
[DOMAIN]
type = financial
subtype = stocks
use_returns = true
use_volatility = true
use_volume_features = true
use_order_flow = false
use_technical_indicators = true

[FUSION]
delta_threshold_pct = 0.002    ; 0.2% per stocks
min_confidence = 0.35
signal_threshold = 0.55
```

---

## 🚀 Esempi di Esecuzione

### 1. Training Iniziale per EURUSD

```bash
# Primo training (30-60 minuti)
cd ~/Profeta
conda activate profeta
./run-epic.sh EURUSD train
```

### 2. Predizione Singola

```bash
# Usa modelli esistenti
./run-epic.sh EURUSD predict
```

### 3. Ciclo Completo

```bash
# Training + Predizione
./run-epic.sh EURUSD full
```

### 4. Modalità Real-Time

```bash
# Orchestratore con polling orario
./run-epic.sh EURUSD realtime
```

### 5. Multi-Epic Simultaneo

```bash
# Terminale 1 - EURUSD
./run-epic.sh EURUSD realtime &

# Terminale 2 - BTCUSD
./run-epic.sh BTCUSD realtime &

# Terminale 3 - ETHUSD
./run-epic.sh ETHUSD realtime &
```

---

## 📊 Verifica Risultati

### Controlla Log

```bash
# Log specifico per epic
tail -100 ~/Profeta/logs/profeta-EURUSD.log

# Log generico
tail -100 ~/Profeta/logs/profeta-v5.log
```

### Verifica Output

```bash
# CSV previsioni
cat ~/Profeta/output/predictions_EURUSD.csv | head -20

# JSON con metriche
cat ~/Profeta/output/predictions_EURUSD.json | python3 -m json.tool | head -50
```

### Controlla Modelli

```bash
# Lista modelli per epic
ls -lh ~/Profeta/models/EURUSD/

# Verifica metadata
cat ~/Profeta/models/EURUSD/ensemble_meta.json | python3 -m json.tool
```

---

## ⚠️ Problemi Comuni e Soluzioni

### 1. Previsioni Esagerate (+25% in 72h)

**Sintomo:** Previsioni irrealistiche (>5% per forex, >20% per crypto)

**Causa:** Modello addestrato su epic sbagliato (es: BTCUSD su dati EURUSD)

**Soluzione:**
```bash
# Cancella modelli errati
rm -rf ~/Profeta/models/EURUSD/

# Rilancia con epic corretto
./run-epic.sh EURUSD train
```

### 2. File CSV Non Trovato

**Sintomo:** `FileNotFoundError: dati-training_EURUSD.csv`

**Soluzione:**
```bash
# Verifica file esistenti
ls ~/Profeta/Trading_live_data/dati-*.csv

# Scarica dati per l'epic specifico
python capital_data_download.py ./Trading_live_data/dati-training_EURUSD.csv 8000
python capital_data_download.py ./Trading_live_data/dati-trading_EURUSD.csv 1500
```

### 3. Modelli Non Compatibili

**Sintomo:** Errore nel caricamento modelli dopo cambio versione

**Soluzione:**
```bash
# Backup e ricrea
mv ~/Profeta/models/EURUSD ~/Profeta/models/EURUSD_OLD
./run-epic.sh EURUSD train
```

---

## 🎯 Best Practices

### 1. Organizzazione Config

Crea un config dedicato per ogni epic:
```bash
BKTEST/
├── config-lstm-EURUSD.ini
├── config-lstm-BTCUSD.ini
├── config-lstm-ETHUSD.ini
└── config-lstm-backtest.ini  # Template
```

### 2. Separazione Log

Usa log separati per epic:
```ini
[SYSTEM]
log_file = ./logs/profeta-EURUSD.log
```

### 3. Soglie Specifiche

Adatta le soglie alla volatilità dell'asset:

| Asset | delta_threshold_pct | Note |
|-------|---------------------|------|
| EURUSD | 0.0005 | 0.05% - basso |
| GBPUSD | 0.0007 | 0.07% - medio |
| BTCUSD | 0.001-0.002 | 0.1-0.2% - alto |
| ETHUSD | 0.0015-0.003 | 0.15-0.3% - molto alto |

### 4. Monitoring

Monitora separatamente ogni epic:
```bash
# Script di monitoring
watch -n 60 'tail -20 ~/Profeta/logs/profeta-*.log | grep "PRED_NUM"'
```

---

## 📈 Workflow Consigliato

### Per Nuovo Epic

1. **Crea config specifico**
   ```bash
   cp BKTEST/config-lstm-backtest.ini BKTEST/config-lstm-NEWEPIC.ini
   sed -i 's/^epic = .*/epic = NEWEPIC/' BKTEST/config-lstm-NEWEPIC.ini
   ```

2. **Scarica dati**
   ```bash
   python capital_data_download.py ./Trading_live_data/dati-training_NEWEPIC.csv 8000
   python capital_data_download.py ./Trading_live_data/dati-trading_NEWEPIC.csv 1500
   ```

3. **Training iniziale**
   ```bash
   ./run-epic.sh NEWEPIC train
   ```

4. **Verifica previsioni**
   ```bash
   cat ~/Profeta/output/predictions_NEWEPIC.csv | head -20
   ```

5. **Avvia real-time**
   ```bash
   ./run-epic.sh NEWEPIC realtime
   ```

---

## 🔗 Riferimenti

- `run-epic.sh` - Script di gestione epic
- `EURUSD-FIX-README.md` - Fix per previsioni esagerate
- `SYNC-WSL.md` - Guida sincronizzazione
- `QWEN.md` - Analisi completa del progetto

---

*Ultimo aggiornamento: 20 Marzo 2026*
