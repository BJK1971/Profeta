# PROFETA Universal Ensemble 33 - v3.2 Ultimate

## Multi-Granularity Architecture

### Il Capolavoro Ingegneristico

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MULTI-GRANULARITY ARCHITECTURE v3.2                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐             ║
║   │     INPUT      │    │     MODEL      │    │     OUTPUT     │             ║
║   │  GRANULARITY   │───►│  GRANULARITY   │───►│  GRANULARITY   │             ║
║   │                │    │                │    │                │             ║
║   │  ┌──────────┐  │    │  ┌──────────┐  │    │  ┌──────────┐  │             ║
║   │  │ SECONDI  │  │    │  │  MINUTI  │  │    │  │   ORE    │  │             ║
║   │  │ 86400/d  │  │    │  │ 1440/d   │  │    │  │  24/d    │  │             ║
║   │  └──────────┘  │    │  └──────────┘  │    │  └──────────┘  │             ║
║   │                │    │                │    │                │             ║
║   │  • Auto-detect │    │  • Resampling  │    │  • Allineate   │             ║
║   │  • Validazione │    │  • OHLC        │    │  • 11:00       │             ║
║   │  • Gap filling │    │  • Aggregation │    │  • 12:00       │             ║
║   │                │    │                │    │  • 13:00...    │             ║
║   └────────────────┘    └────────────────┘    └────────────────┘             ║
║                                                                               ║
║   COMPLETAMENTE CONFIGURABILE VIA .INI                                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Sezione [GRANULARITY]

### Configurazione Completa

```ini
[GRANULARITY]
; ═══════════════════════════════════════════════════════
; INPUT - Granularità dati in ingresso
; ═══════════════════════════════════════════════════════
input_granularity = auto    ; auto | second | minute | hour | day

; ═══════════════════════════════════════════════════════
; MODEL - Granularità di lavoro per training
; ═══════════════════════════════════════════════════════
model_granularity = minute  ; second | minute | hour | day

; ═══════════════════════════════════════════════════════
; OUTPUT - Granularità previsioni (allineate ai boundary)
; ═══════════════════════════════════════════════════════
output_granularity = hour   ; second | minute | hour | day | week | month

; ═══════════════════════════════════════════════════════
; RESAMPLING - Metodo aggregazione
; ═══════════════════════════════════════════════════════
resample_method = ohlc      ; ohlc | mean | last | first | sum | median

; ═══════════════════════════════════════════════════════
; GAP HANDLING - Gestione buchi nei dati
; ═══════════════════════════════════════════════════════
detect_gaps = true
fill_gaps_method = ffill    ; ffill | bfill | interpolate | drop | zero | mean

; ═══════════════════════════════════════════════════════
; VALIDAZIONE
; ═══════════════════════════════════════════════════════
min_data_points = 1000
max_gap_tolerance = 10
```

---

## Scenari di Utilizzo

### Scenario 1: Trading Crypto ad Alta Frequenza
```ini
[GRANULARITY]
input_granularity = second      ; Dati tick-by-tick
model_granularity = minute      ; Training su candele 1 min
output_granularity = hour       ; Previsioni orarie strategiche
resample_method = ohlc          ; Preserva OHLC
```

**Flusso dati:**
```
86400 tick/giorno → 1440 candele/giorno → 24 previsioni/giorno
     (raw)              (training)            (output)
```

### Scenario 2: Trading Azioni Giornaliero
```ini
[GRANULARITY]
input_granularity = minute      ; Dati intraday
model_granularity = hour        ; Training su candele orarie
output_granularity = day        ; Previsioni giornaliere
resample_method = ohlc
```

### Scenario 3: Analisi Settimanale
```ini
[GRANULARITY]
input_granularity = hour        ; Dati orari
model_granularity = day         ; Training giornaliero
output_granularity = week       ; Previsioni settimanali
resample_method = last
```

### Scenario 4: Compatibilità v3.1 (No Resampling)
```ini
[GRANULARITY]
input_granularity = minute
model_granularity = minute      ; Stesso di input = no resampling
output_granularity = hour
```

---

## Componenti del Sistema di Granularità

### 1. GranularityDetector

```python
class GranularityDetector:
    """
    Rileva automaticamente la granularità dai timestamp.
    
    Algoritmo:
    1. Calcola differenze tra timestamp consecutivi
    2. Usa la MEDIANA (robusta agli outlier)
    3. Mappa a granularità più vicina
    4. Calcola confidence score
    """
    
    def detect(self, timestamps) -> Tuple[Granularity, Dict]:
        # Esempio output:
        # (Granularity.MINUTE, {
        #     'mean_interval': 60.2,
        #     'median_interval': 60.0,
        #     'confidence': 0.98,
        #     'detected_granularity': 'Minuti'
        # })
```

### 2. DataResampler

```python
class DataResampler:
    """
    Resampla dati tra granularità diverse.
    
    Supporta:
    - Downsampling: second → minute → hour → day
    - Upsampling: day → hour → minute (con interpolazione)
    - Metodo OHLC per dati finanziari
    """
    
    def resample(self, data, source, target, method):
        if method == ResampleMethod.OHLC:
            # Open: primo valore
            # High: massimo
            # Low: minimo
            # Close: ultimo valore
            # Volume: somma
```

### 3. GapHandler

```python
class GapHandler:
    """
    Gestisce gaps nei dati temporali.
    
    Metodi:
    - ffill: Forward fill (usa ultimo valore)
    - bfill: Backward fill
    - interpolate: Interpolazione lineare
    - drop: Rimuovi gaps
    """
```

### 4. GranularityManager

```python
class GranularityManager:
    """
    Orchestratore principale.
    
    Pipeline:
    1. Auto-detect input granularity (se auto)
    2. Valida configurazione
    3. Rileva e gestisce gaps
    4. Resampla a model_granularity
    """
    
    def process_data(self, data, timestamp_col, target_col):
        # Step 1: Detect
        if self.config.input_granularity is None:
            detected, stats = self.detector.detect(data[timestamp_col])
        
        # Step 2: Validate
        warnings = self.config.validate()
        
        # Step 3: Handle gaps
        if self.config.detect_gaps:
            gaps = self.detector.detect_gaps(...)
            data = self.gap_handler.fill_gaps(...)
        
        # Step 4: Resample
        if detected != self.config.model_granularity:
            data = self.resampler.resample(...)
        
        return data
```

---

## Metodi di Resampling

| Metodo | Descrizione | Uso Consigliato |
|--------|-------------|-----------------|
| `ohlc` | Open-High-Low-Close | **Dati finanziari** (preserva struttura candele) |
| `mean` | Media | Sensori, metriche continue |
| `last` | Ultimo valore | Stati, configurazioni |
| `first` | Primo valore | Eventi, log |
| `sum` | Somma | Volumi, conteggi |
| `median` | Mediana | Dati con outlier |
| `min` | Minimo | Valori critici bassi |
| `max` | Massimo | Valori critici alti |

### Logica OHLC per Dati Finanziari

```
Input (secondi):
  10:00:00  open=100, high=102, low=99,  close=101
  10:00:01  open=101, high=103, low=100, close=102
  ...
  10:00:59  open=105, high=107, low=104, close=106

Output (minuto):
  10:00:00  open=100  (primo open)
            high=107  (max di tutti i high)
            low=99    (min di tutti i low)
            close=106 (ultimo close)
            volume=Σ  (somma volumi)
```

---

## Allineamento Temporale Output

### Come Funziona

```
ULTIMO DATO:     2025-03-21 10:45:23
                         │
                         ▼
ALLINEAMENTO:    ceil() al prossimo boundary
                         │
                         ▼
PREVISIONI:      11:00:00, 12:00:00, 13:00:00, ...
                 ▲
                 └── Allineate alle ore INTERE
```

### Esempi per Ogni Granularità

| Output Gran | Ultimo Dato | Prima Previsione |
|-------------|-------------|------------------|
| second | 10:45:23.456 | 10:45:24.000 |
| minute | 10:45:23 | 10:46:00 |
| hour | 10:45:23 | 11:00:00 |
| day | 2025-03-21 14:30 | 2025-03-22 00:00 |
| week | 2025-03-21 | 2025-03-24 (lunedì) |
| month | 2025-03-21 | 2025-04-01 |

---

## Output del Sistema

### File Generati

```
output_dir/
├── real_time_ens_hours.csv           # Previsioni CSV
├── real_time_ens_20250321_143000.xlsx # Previsioni Excel
├── real_time_ens_hours.png           # Grafico
├── ensemble_delta.txt                # Log delta
├── model_average_deltas.txt          # Log delta modelli
├── system_state.json                 # Stato sistema
└── granularity_info.json             # Info granularità
```

### granularity_info.json

```json
{
  "input": "Secondi",
  "model": "Minuti", 
  "output": "Ore"
}
```

### system_state.json

```json
{
  "last_training_time": "2025-03-21T10:20:00",
  "training_count": 42,
  "prediction_count": 7,
  "last_ensemble_delta": -0.001234,
  "input_granularity": "Secondi",
  "model_granularity": "Minuti",
  "output_granularity": "Ore"
}
```

---

## Log di Esempio

```
2025-03-21 10:00:00 | INFO     | GRANULARITY MANAGER - Processing Pipeline
============================================================
2025-03-21 10:00:01 | INFO     | Granularità rilevata: Secondi (intervallo mediano: 1.00s, confidence: 99.80%)
2025-03-21 10:00:02 | WARNING  | Rilevati 3 gaps nei dati (totale 180 punti mancanti)
2025-03-21 10:00:03 | INFO     | Gap filling completato: 86400 → 86580 record
2025-03-21 10:00:04 | INFO     | Resampling: Secondi → Minuti (metodo: ohlc)
2025-03-21 10:00:05 | INFO     | Resampling completato: 86580 → 1440 record
------------------------------------------------------------
RIEPILOGO PROCESSING:
  Input granularità:  Secondi
  Model granularità:  Minuti
  Output granularità: Ore
  Record originali:   86400
  Record processati:  1440
  Resample method:    ohlc
------------------------------------------------------------
```

---

## Changelog v3.1 → v3.2

### Nuove Funzionalità

| Feature | Descrizione |
|---------|-------------|
| **[GRANULARITY] section** | Configurazione completa granularità |
| **Auto-detection** | Rileva automaticamente granularità input |
| **DataResampler** | Resampling multi-metodo (OHLC, mean, last...) |
| **GapHandler** | Gestione gaps con fill methods |
| **GranularityManager** | Orchestrazione pipeline completo |
| **Validation** | Warning per configurazioni subottimali |

### Nuove Classi

```python
class Granularity(Enum)           # second, minute, hour, day...
class ResampleMethod(Enum)        # ohlc, mean, last, first...
class GapFillMethod(Enum)         # ffill, bfill, interpolate...
class GranularityConfig           # Configurazione completa
class GranularityDetector         # Auto-detection
class DataResampler               # Resampling
class GapHandler                  # Gap filling
class GranularityManager          # Orchestrazione
```

### Retrocompatibilità

- **100% compatibile** con config v3.1
- Se manca [GRANULARITY], usa `freq` da [PREDICTION]
- `granularity` in [DATA] ora deprecato ma ignorato

---

## Best Practices

### Per Massima Accuratezza

```ini
[GRANULARITY]
input_granularity = auto          ; Lascia rilevare
model_granularity = minute        ; Granularità fine per training
output_granularity = hour         ; Previsioni stabili
resample_method = ohlc            ; Preserva struttura mercato
detect_gaps = true                ; Rileva problemi dati
fill_gaps_method = ffill          ; Fill conservativo
```

### Per Performance

```ini
[GRANULARITY]
input_granularity = hour          ; Meno dati
model_granularity = hour          ; No resampling
output_granularity = day          ; Meno previsioni
```

---

**Autore**: Eng. Emilio Billi  
**Azienda**: BilliDynamics™  
**Versione**: 3.2 Ultimate  
**Data**: 2025
