# PROFETA Universal Ensemble 33 - v3.0 Enterprise

## Changelog da v2.0 a v3.0

### 🏗️ Architettura

| Aspetto | v2.0 | v3.0 |
|---------|------|------|
| Struttura | Procedurale monolitica | OOP modulare con 15+ classi |
| Type hints | Parziali | Completi con `typing` |
| Configurazione | Parsing inline | `ConfigurationLoader` dedicato |
| Modelli | Funzioni sparse | `PROFETAModel` wrapper |
| Ensemble | Logica embedded | `PROFETAEnsemble` orchestrator |

### 🐛 Bug Fix Critici

#### 1. Data Leakage (RISOLTO)
```python
# v2.0 - BUG: Scaler fittato su TUTTI i dati
scaled_data = scaler.fit_transform(target_data)  # ❌ Leak!

# v3.0 - FIX: Scaler fittato SOLO su training
split_idx = int(len(target_data) * train_test_split)
training_data = target_data[:split_idx]
preprocessor.fit(training_data)  # ✅ Corretto
```

#### 2. Fine-tuning Scaler Override (RISOLTO)
```python
# v2.0 - BUG: Scaler caricato ma poi sovrascritto con fit_transform
model = load_model(...)
scaler = pickle.load(...)
scaled_data = scaler.fit_transform(target_data)  # ❌ Sovrascrive!

# v3.0 - FIX: In fine-tuning usa solo transform
preprocessor = model.preprocessor  # Scaler esistente
scaled_data = preprocessor.transform(target_data)  # ✅ Preservato
```

#### 3. Modelli Ricaricati da Disco (RISOLTO)
```python
# v2.0 - Modelli ricaricati 2 volte per ogni iterazione
for idx, model_sec in enumerate(model_sections):
    model = load_model(...)  # Prima volta
# ... poi ancora ...
for idx, model_sec in enumerate(model_sections):
    model = load_model(...)  # Seconda volta ❌

# v3.0 - Caching in memoria
self.models: Dict[int, PROFETAModel] = {}
self.models[config.model_id] = model  # ✅ Cache
```

### 🕐 Allineamento Temporale (NUOVA FEATURE)

La feature più importante richiesta: **previsioni allineate ai boundary temporali**.

#### Comportamento v2.0
```
Ultimo dato: 2025-03-21 10:45:00
Previsioni:  11:45, 12:45, 13:45, 14:45, ...  ❌
```

#### Comportamento v3.0
```
Ultimo dato: 2025-03-21 10:45:00
Previsioni:  11:00, 12:00, 13:00, 14:00, ...  ✅
```

#### Implementazione
```python
class TemporalAligner:
    ALIGNMENT_RULES = {
        TimeFrequency.SECOND: lambda ts: ts.ceil('S'),
        TimeFrequency.MINUTE: lambda ts: ts.ceil('T'),
        TimeFrequency.HOUR: lambda ts: ts.ceil('H'),
        TimeFrequency.DAY: lambda ts: (ts + pd.Timedelta(days=1)).normalize(),
    }
    
    def align_to_next_boundary(self, timestamp):
        return self._alignment_func(timestamp)
    
    def generate_aligned_dates(self, start_timestamp, num_periods):
        aligned_start = self.align_to_next_boundary(start_timestamp)
        return pd.date_range(start=aligned_start, periods=num_periods, freq=...)
```

### 📊 Metriche Avanzate

v3.0 introduce un sistema completo di metriche:

```python
@dataclass
class PredictionMetrics:
    rmse: float      # Root Mean Square Error
    mae: float       # Mean Absolute Error  
    mape: float      # Mean Absolute Percentage Error
    r2: float        # Coefficiente di determinazione
    mean_delta: float
    std_delta: float
```

Output esempio:
```
┌─────────────────────────────────────┐
│       METRICHE DI VALUTAZIONE       │
├─────────────────────────────────────┤
│  RMSE:             0.012345         │
│  MAE:              0.009876         │
│  MAPE:             1.2345%          │
│  R²:               0.987654         │
│  Mean Δ:          -0.001234         │
│  Std Δ:            0.005678         │
└─────────────────────────────────────┘
```

### 🔍 Rilevamento Duplicati

v3.0 segnala automaticamente configurazioni duplicate:

```python
def _check_duplicates(self) -> None:
    seen = {}
    for config in self.model_configs:
        config_hash = hash(config)
        if config_hash in seen:
            self.logger.warning(
                f"⚠️  MODEL_{config.model_id} è duplicato di MODEL_{seen[config_hash]}"
            )
```

Nel tuo `config-lstm.ini`, MODEL_3 e MODEL_7 sono identici - ora riceverai un warning.

### 🛡️ Gestione Eccezioni

```python
# v2.0 - Nessuna gestione
with open(scaler_filename, 'rb') as f:
    scaler = pickle.load(f)  # Crash se file corrotto

# v3.0 - Gestione robusta
try:
    with open(path, 'rb') as f:
        preprocessor.scaler = pickle.load(f)
except Exception as e:
    raise RuntimeError(f"Errore caricamento scaler da {path}: {e}")
```

### 📁 Struttura Classi

```
PROFETAOrchestrator          # Entry point principale
├── SystemConfig             # Configurazione GPU, logging, seed
├── ConfigurationLoader      # Parser file INI
├── PROFETAEnsemble          # Orchestrazione N modelli
│   ├── PROFETAModel         # Wrapper singolo modello
│   │   ├── LSTMModelBuilder # Factory pattern
│   │   └── TimeSeriesPreprocessor  # Scaling e sequenze
│   ├── TemporalAligner      # Allineamento date
│   └── MetricsCalculator    # Calcolo metriche
└── EnsembleResults          # Container risultati
```

### 🚀 Miglioramenti Performance

1. **Caching modelli**: Evita ricaricamento da disco
2. **Lazy evaluation**: Preprocessing on-demand
3. **Memory growth**: GPU memory allocation dinamica
4. **Batch predict**: `verbose=0` elimina overhead console

### 📋 Requisiti

```
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=0.24.0
tensorflow>=2.8.0
matplotlib>=3.4.0
tqdm>=4.60.0
```

### 🔧 Utilizzo

```bash
# Default config
python profeta-universal-v3.py

# Config personalizzata
python profeta-universal-v3.py /path/to/custom-config.ini
```

### 📝 Note di Compatibilità

- Il file `config-lstm.ini` esistente è **100% compatibile**
- Il `report_generator.py` esistente è supportato (import opzionale)
- Output CSV/Excel mantiene lo stesso formato
- Nessuna modifica richiesta ai dati di input

---

**Autore**: Eng. Emilio Billi  
**Azienda**: BilliDynamics™  
**Versione**: 3.0 Enterprise  
**Data**: 2025
