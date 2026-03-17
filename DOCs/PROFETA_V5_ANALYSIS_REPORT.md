# PROFETA v5.0 - REPORT ANALISI COMPATIBILITÀ

## ✅ RIEPILOGO

| Punto | Requisito | Status | Note |
|-------|-----------|--------|------|
| 1 | Disabilitare classificazione | ⚠️ PARZIALE | Campo `enabled` esiste ma NON implementato |
| 2 | Granularità configurabile | ✅ OK | Completamente implementato |
| 3 | Output previsioni nel .ini | ⚠️ PARZIALE | `output_predictions_path` non letto |
| 4 | Due file CSV separati | ✅ OK | `[DATA]` + `[INPUT]` |
| 5 | Frequenze separate | ⚠️ BUG | Calcolo tempo con `.seconds` errato |

---

## 📋 DETTAGLIO ANALISI

### 1️⃣ DISABILITARE CLASSIFICAZIONE

**STATO: ⚠️ CAMPO PRESENTE MA NON IMPLEMENTATO**

```python
# ClassificationConfig ha il campo:
@dataclass
class ClassificationConfig:
    enabled: bool = True  # ← ESISTE
    ...
```

**PROBLEMA:** Il campo `enabled` non viene MAI controllato nel codice. La classificazione viene sempre eseguita.

**SOLUZIONE:** Aggiungere controllo nel PROFETAEngine.train() e predict()

---

### 2️⃣ GRANULARITÀ TEMPORALI

**STATO: ✅ COMPLETAMENTE IMPLEMENTATO**

```ini
[GRANULARITY]
input_granularity = auto          ; ✅ Letto da from_config()
model_granularity = minute        ; ✅ Letto da from_config()
output_granularity = hour         ; ✅ Letto da from_config()
resample_method = ohlc            ; ✅ Letto da from_config()
```

**Flusso implementato:**
1. `input_granularity = auto` → GranularityDetector rileva automaticamente
2. Dati resamplati a `model_granularity` per training
3. Previsioni allineate a `output_granularity`

---

### 3️⃣ OUTPUT PREVISIONI

**STATO: ⚠️ PARZIALMENTE IMPLEMENTATO**

```python
# PredictionConfig legge:
class PredictionConfig:
    output_dir: str = "./output"  # ✅ Letto
    
# MA NON LEGGE:
# output_predictions_path = ...   # ❌ IGNORATO
```

**PROBLEMA:** Il path specifico per le previsioni CSV non viene letto.

**Nel config .ini c'è:**
```ini
[PREDICTION]
output_predictions_path = C:/Users/.../real_time_ens_hours.csv  ; ❌ IGNORATO
output_dir = ./output  ; ✅ USATO
```

---

### 4️⃣ DUE FILE CSV SEPARATI

**STATO: ✅ COMPLETAMENTE IMPLEMENTATO**

```python
def get_data_paths(self) -> Tuple[str, str]:
    train = self.config.get('DATA', 'data_path', fallback='data/train.csv')      # ✅
    pred = self.config.get('INPUT', 'input_data_path', fallback=train)           # ✅
    return train, pred
```

**Config .ini:**
```ini
[DATA]
data_path = ./dati-training.csv        ; ✅ Per training/fine-tuning

[INPUT]  
input_data_path = ./dati-trading.csv   ; ✅ Per inferenza
```

---

### 5️⃣ FREQUENZE SEPARATE TRAINING/INFERENZA

**STATO: ⚠️ IMPLEMENTATO CON BUG**

```python
# SchedulerConfig legge correttamente:
training_interval_min: int = 60         # ✅ Ogni 60 minuti
prediction_interval_min: int = 1440     # ✅ Ogni 1440 minuti (24h)
```

**BUG nel daemon:**
```python
# CODICE ATTUALE (ERRATO):
if (now - last_train).seconds / 60 >= sched.training_interval_min:
#                    ^^^^^^^^ SBAGLIATO! .seconds restituisce solo i secondi
#                             della parte time, non il totale

# CORRETTO:
if (now - last_train).total_seconds() / 60 >= sched.training_interval_min:
#                     ^^^^^^^^^^^^^^^^ USA total_seconds()
```

**Config .ini:**
```ini
[SCHEDULER]
training_interval_minutes = 15      ; Re-train ogni 15 minuti
prediction_interval_minutes = 180   ; Previsioni ogni 3 ore (180 min)
```

---

## 🔧 CORREZIONI NECESSARIE

Vedere file: `profeta-universal-v5-fixed.py`
