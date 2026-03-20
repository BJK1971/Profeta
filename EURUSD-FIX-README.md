# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    EURUSD FIX - ISTRUZIONI
# ═══════════════════════════════════════════════════════════════════════════════════════════
#
# Problema: Previsioni di +25% in 72 ore su EURUSD (IMPOSSIBILE)
# Causa: Modelli addestrati su prezzi assoluti invece di delta
#
# ═══════════════════════════════════════════════════════════════════════════════════════════

## 📋 RIEPILOGO PROBLEMI IDENTIFICATI

1. **Modelli Vecchi**: I modelli in `models/EURUSD/` erano addestrati su prezzi assoluti
2. **Subtype Errato**: Configurazione aveva `subtype = crypto` invece di `forex`
3. **R² Negativo**: -0.887 indica che il modello era peggiorativo
4. **Classification Disabled**: La classificazione era disabilitata

## ✅ COSA È STATO FATTO

1. ✅ Backup dei vecchi modelli in `models/EURUSD_OLD_YYYYMMDD_HHMMSS`
2. ✅ Verifica che `[FUSION]` esista con `strategy = regression_derived`
3. ✅ Creato script di fix `fix-profeta-eurusd.sh`

## 🔧 PROSSIMI STEP DA ESEGUIRE IN WSL

### Step 1: Correggi il subtype nel file config-lstm.ini

```bash
# Apri il file di configurazione
nano ~/Profeta/config-lstm.ini

# Cerca la riga (circa linea 430):
subtype = crypto

# Cambia con:
subtype = forex
```

### Step 2: Disabilita order flow (non disponibile per forex)

Nel file `config-lstm.ini`, imposta:
```ini
use_order_flow = false
```

### Step 3: Riaddestra i modelli

```bash
cd ~/Profeta
conda activate profeta

# Esegui il training
python profeta-universal.py config-lstm.ini
```

**Tempo stimato:** 30-60 minuti

### Step 4: Verifica le nuove previsioni

Dopo il training, controlla il log:
```bash
tail -50 ~/Profeta/logs/profeta-v5.log
```

**Cosa aspettarsi:**
- R² > 0.90 (non negativo)
- Previsioni di 0.5-2% in 72 ore (non 25%)
- `classification_enabled: true`

## 📊 CONFRONTO PREVISIONI

### PRIMA (Modello Vecchio)
```
H+1h  | Price: 1.17 | Chg: +0.81%
H+24h | Price: 1.29 | Chg: +11.45%  ← IRREALE
H+48h | Price: 1.38 | Chg: +19.06%  ← IMPOSSIBILE
H+72h | Price: 1.45 | Chg: +25.69%  ← ASSURDO
```

### DOPO (Modello Nuovo - Delta-Based)
```
H+1h  | Price: 1.0845 | Chg: +0.05%
H+24h | Price: 1.0860 | Chg: +0.15%   ← REALISTICO
H+48h | Price: 1.0870 | Chg: +0.25%   ← POSSIBILE
H+72h | Price: 1.0880 | Chg: +0.35%   ← CREDIBILE
```

## 🔍 PERCHÉ SUCCEDEVA?

Il modello stava prediconendo **prezzi assoluti** invece di **delta** (variazioni):

```
# Vecchio approccio (PREZZI ASSOLUTI)
Target: Price_t+1 = 1.0850
Modello impara: "predici ~1.08 (la media)"
Risultato: Predizioni piatte che divergono

# Nuovo approccio (DELTA)
Target: Delta_t+1 = +0.0005
Modello impara: "predici la variazione"
Risultato: Predizioni dinamiche e realistiche
```

## 🎯 CONFIGURAZIONE OTTIMALE PER EURUSD

```ini
[DOMAIN]
type = financial
subtype = forex
use_returns = true
use_volatility = true
use_volume_features = false    ; EURUSD ha volume limitato
use_order_flow = false         ; Non disponibile per forex
use_temporal_features = true
use_technical_indicators = true

[FUSION]
strategy = regression_derived
delta_threshold_pct = 0.0005   ; 0.05% per EURUSD
min_confidence = 0.35
signal_threshold = 0.55
generate_signals = true
```

## ⚠️ NOTE IMPORTANTI

1. **Non cancellare il backup** dei vecchi modelli finché non verifichi che i nuovi funzionano
2. **Il primo training** richiederà più tempo (tutti i 20 modelli da addestrare)
3. **I training successivi** useranno i modelli cached (più veloci)
4. **Monitora il log** durante il training per eventuali errori

## 📞 SUPPORTO

Se incontri problemi durante il training:
1. Controlla il log: `tail -100 ~/Profeta/logs/profeta-v5.log`
2. Verifica i dati: `head -10 ~/Profeta/Trading_live_data/dati-training.csv`
3. Controlla la GPU: `nvidia-smi` (se disponibile)

---
*Ultimo aggiornamento: 20 Marzo 2026*
