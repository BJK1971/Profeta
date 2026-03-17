# PROFETA Universal Ensemble 33 - v3.1 Enterprise Daemon

## Architettura Adaptive Learning

### Concetto Fondamentale

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    PROFETA ADAPTIVE LEARNING ARCHITECTURE                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║                         MARKET DATA FLOW                                      ║
║                              │                                                ║
║                              ▼                                                ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                                                                     │    ║
║   │    TRAINING LOOP                    PREDICTION LOOP                 │    ║
║   │    ══════════════                   ════════════════                │    ║
║   │                                                                     │    ║
║   │    Intervallo: 20 min               Intervallo: 24 ore              │    ║
║   │    ┌──────────────┐                 ┌──────────────┐                │    ║
║   │    │              │                 │              │                │    ║
║   │    │  Fine-tuning │ ──────────────► │  Previsioni  │                │    ║
║   │    │   Modelli    │   Modelli       │   Future     │                │    ║
║   │    │              │   Aggiornati    │              │                │    ║
║   │    └──────────────┘                 └──────────────┘                │    ║
║   │           │                                │                        │    ║
║   │           │                                │                        │    ║
║   │           ▼                                ▼                        │    ║
║   │    ┌──────────────┐                 ┌──────────────┐                │    ║
║   │    │   Ensemble   │                 │    Output    │                │    ║
║   │    │    Delta     │                 │  Allineato   │                │    ║
║   │    │  Aggiornato  │                 │  (ore piene) │                │    ║
║   │    └──────────────┘                 └──────────────┘                │    ║
║   │                                                                     │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   VANTAGGI:                                                                   ║
║   ─────────                                                                   ║
║   ✓ Modelli sempre sincronizzati con il mercato                              ║
║   ✓ Previsioni stabili, non affette da rumore                                ║
║   ✓ Ensemble delta si adatta in tempo reale                                  ║
║   ✓ Zero downtime: training non blocca le previsioni                         ║
║   ✓ Thread-safe con locking ottimizzato                                      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Perché Questa Architettura?

| Aspetto | Training Frequente | Previsioni Stabili |
|---------|-------------------|-------------------|
| **Frequenza** | Ogni 20 minuti | Ogni 24 ore |
| **Obiettivo** | Catturare micro-trend | Decisioni strategiche |
| **Dati** | Ultimi dati mercato | Modelli consolidati |
| **Beneficio** | Modelli sempre attuali | Forecast non rumorosi |

---

## Componenti Sistema

### Diagramma Architetturale

```
PROFETADaemon
│
├── SystemConfig              # GPU, logging, seed
│
├── ConfigurationLoader       # Parser INI
│   ├── SchedulerConfig       # [SCHEDULER]
│   ├── TrainingConfig        # [TRAINING]
│   ├── PredictionConfig      # [PREDICTION]
│   └── ModelConfig[]         # [MODEL_1..33]
│
├── TaskScheduler             # Scheduling task
│   ├── ScheduledTask[TRAINING]
│   ├── ScheduledTask[PREDICTION]
│   └── ScheduledTask[HEALTH_CHECK]
│
├── ModelRegistry             # Storage modelli (thread-safe)
│   ├── _models: Dict[id, PROFETAModel]
│   ├── _ensemble_delta: float
│   ├── _lock: RLock
│   └── _version: int
│
├── StateManager              # Persistenza stato
│   └── SystemState
│       ├── last_training_time
│       ├── last_prediction_time
│       ├── training_count
│       └── errors[]
│
├── TrainingEngine            # Esecuzione training
│   └── execute(data) → (ensemble_delta, model_deltas)
│
└── PredictionEngine          # Esecuzione previsioni
    ├── TemporalAligner       # Allineamento date
    └── execute(data) → EnsembleResults
```

### Thread Safety

```python
class ModelRegistry:
    """
    Registro thread-safe per modelli.
    
    Garantisce:
    - Lettura concorrente sicura
    - Scrittura atomica
    - Versioning per cache invalidation
    """
    
    @contextmanager
    def read_lock(self):
        """Accesso in lettura (prediction)."""
        with self._lock:
            yield self._models
    
    @contextmanager  
    def write_lock(self):
        """Accesso in scrittura (training)."""
        with self._lock:
            yield self._models
            self._version += 1
```

---

## Configurazione

### Sezione [SCHEDULER]

```ini
[SCHEDULER]
; Modalità operativa
;   once:   Training + prediction, poi termina
;   daemon: Servizio continuo con scheduling
mode = daemon

; Intervallo training in MINUTI
; 0 = solo all'avvio
; 20 = ogni 20 minuti (consigliato per mercati volatili)
training_interval_minutes = 20

; Intervallo previsioni in MINUTI  
; 0 = solo dopo training
; 1440 = ogni 24 ore (consigliato per stabilità)
prediction_interval_minutes = 1440

; Task all'avvio
train_on_startup = true
predict_on_startup = true

; Resilienza
max_training_retries = 3
health_check_interval = 60
graceful_shutdown_timeout = 30
```

### Scenari di Configurazione

#### 1. Trading ad Alta Frequenza
```ini
mode = daemon
training_interval_minutes = 10      ; Aggiornamento rapido
prediction_interval_minutes = 60    ; Previsioni ogni ora
```

#### 2. Trading Giornaliero (Consigliato)
```ini
mode = daemon
training_interval_minutes = 20      ; Bilanciato
prediction_interval_minutes = 1440  ; Una volta al giorno
```

#### 3. Analisi Settimanale
```ini
mode = daemon
training_interval_minutes = 60      ; Ogni ora
prediction_interval_minutes = 10080 ; Una volta a settimana
```

#### 4. Singola Esecuzione (Compatibilità v3.0)
```ini
mode = once
train_on_startup = true
predict_on_startup = true
```

---

## Allineamento Temporale

### Comportamento

```
ULTIMO DATO:     2025-03-21 10:45:00
                         │
                         ▼
ALLINEAMENTO:    ceil() al prossimo boundary
                         │
                         ▼
PREVISIONI:      11:00, 12:00, 13:00, 14:00, ...
                 ▲
                 │
                 └── Allineate alle ore INTERE
```

### Supporto Frequenze

| Frequenza | Codice | Esempio |
|-----------|--------|---------|
| Secondi | S | 10:45:30 → 10:45:31, 10:45:32... |
| Minuti | T, min | 10:45:30 → 10:46, 10:47... |
| Ore | H | 10:45 → 11:00, 12:00... |
| Giorni | D | 2025-03-21 14:30 → 2025-03-22... |
| Settimane | W | → Prossimo lunedì |
| Mesi | M | → Primo del mese successivo |

---

## Flusso Operativo

### Modalità Daemon

```
┌──────────────────────────────────────────────────────────────┐
│                      DAEMON LIFECYCLE                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. STARTUP                                                  │
│     └── Carica configurazione                                │
│     └── Inizializza componenti                               │
│     └── Setup signal handlers (SIGINT, SIGTERM)              │
│                                                              │
│  2. STARTUP TASKS (se configurati)                           │
│     └── train_on_startup → TrainingEngine.execute()          │
│     └── predict_on_startup → PredictionEngine.execute()      │
│                                                              │
│  3. MAIN LOOP                                                │
│     ┌─────────────────────────────────────────────────┐      │
│     │  while not shutdown_requested:                  │      │
│     │      task = scheduler.get_next_task()          │      │
│     │                                                 │      │
│     │      if task.type == TRAINING:                 │      │
│     │          TrainingEngine.execute()              │      │
│     │                                                 │      │
│     │      elif task.type == PREDICTION:             │      │
│     │          PredictionEngine.execute()            │      │
│     │                                                 │      │
│     │      elif task.type == HEALTH_CHECK:           │      │
│     │          log_system_status()                   │      │
│     │                                                 │      │
│     │      sleep(until_next_task)                    │      │
│     └─────────────────────────────────────────────────┘      │
│                                                              │
│  4. SHUTDOWN                                                 │
│     └── Signal ricevuto (Ctrl+C / SIGTERM)                   │
│     └── Completa task corrente                               │
│     └── Salva stato                                          │
│     └── Cleanup risorse                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Priorità Task

```
TRAINING > PREDICTION > HEALTH_CHECK

Se training e prediction sono entrambi "due",
il training viene eseguito PRIMA per garantire
che le previsioni usino modelli aggiornati.
```

---

## Persistenza Stato

### File system_state.json

```json
{
  "last_training_time": "2025-03-21T10:20:00",
  "last_prediction_time": "2025-03-21T10:00:00",
  "training_count": 42,
  "prediction_count": 7,
  "last_ensemble_delta": -0.001234,
  "last_metrics": {
    "RMSE": 0.012345,
    "MAE": 0.009876,
    "R²": 0.987654
  },
  "is_models_loaded": true,
  "errors": []
}
```

### Benefici

1. **Ripristino dopo crash**: Lo stato permette di sapere quando è stato l'ultimo training
2. **Monitoring**: Dashboard possono leggere questo file per status
3. **Debug**: Storico errori per troubleshooting

---

## Utilizzo

### Avvio Daemon

```bash
# Con config default
python profeta-universal-v3.1.py

# Con config personalizzata  
python profeta-universal-v3.1.py /path/to/config-lstm.ini

# In background (Linux)
nohup python profeta-universal-v3.1.py > profeta.log 2>&1 &

# Come servizio systemd (Linux)
systemctl start profeta
```

### Shutdown Graceful

```bash
# Ctrl+C nel terminale
^C

# O inviando SIGTERM
kill -TERM <pid>
```

Il sistema:
1. Completa il task corrente
2. Salva lo stato
3. Chiude le connessioni
4. Termina pulitamente

---

## Changelog v3.0 → v3.1

### Nuove Funzionalità

| Feature | Descrizione |
|---------|-------------|
| **Modalità Daemon** | Servizio continuo con scheduling |
| **Task Scheduler** | Scheduling indipendente training/prediction |
| **Model Registry** | Storage thread-safe con versioning |
| **State Manager** | Persistenza stato su disco |
| **Health Monitor** | Heartbeat e metriche sistema |
| **Signal Handlers** | Graceful shutdown (SIGINT/SIGTERM) |

### Nuove Classi

```python
class ExecutionMode(Enum)      # once / daemon
class TaskType(Enum)           # training / prediction / health_check  
class TaskStatus(Enum)         # pending / running / completed / failed
class SchedulerConfig          # Configurazione scheduler
class ScheduledTask            # Rappresentazione task
class TaskScheduler            # Orchestrazione scheduling
class SystemState              # Stato persistente
class StateManager             # Gestione persistenza
class ModelRegistry            # Registry thread-safe
class TrainingEngine           # Motore training
class PredictionEngine         # Motore previsioni
class PROFETADaemon            # Demone principale
```

### Compatibilità

- **100% retrocompatibile** con config v3.0
- Se manca sezione [SCHEDULER], usa `mode = once`
- Tutti i parametri hanno valori default sensati

---

## Best Practices

### Per Trading Crypto/Forex

```ini
[SCHEDULER]
mode = daemon
training_interval_minutes = 15    ; Mercati 24/7 volatili
prediction_interval_minutes = 240 ; Ogni 4 ore
fine_tuning = 1                   ; Sempre fine-tuning
```

### Per Azioni/ETF

```ini
[SCHEDULER]  
mode = daemon
training_interval_minutes = 30    ; Meno volatile
prediction_interval_minutes = 1440 ; Una volta al giorno
fine_tuning = 1
```

### Per Backtesting

```ini
[SCHEDULER]
mode = once                       ; Singola esecuzione
train_on_startup = true
predict_on_startup = true
```

---

**Autore**: Eng. Emilio Billi  
**Azienda**: BilliDynamics™  
**Versione**: 3.1 Enterprise Daemon  
**Data**: 2025
