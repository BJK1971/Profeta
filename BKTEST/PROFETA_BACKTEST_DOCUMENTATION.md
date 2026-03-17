# PROFETA Backtesting Framework

## Documentazione Completa

---

## Cos'è e Perché Serve

Il backtesting è il processo di **validare un sistema di previsione su dati storici**, simulando come avrebbe performato nel passato. È **CRITICO** prima di usare PROFETA con capitale reale.

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        DOMANDA FONDAMENTALE                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   "Le previsioni di PROFETA avrebbero generato PROFITTO REALE                 ║
║    se fossero state usate nel passato?"                                       ║
║                                                                               ║
║   Il backtest risponde a questa domanda con NUMERI CONCRETI:                  ║
║                                                                               ║
║   • Sharpe Ratio: 1.85 → Sistema statisticamente valido                       ║
║   • Max Drawdown: 15% → Rischio accettabile                                   ║
║   • Win Rate: 58% → Più trade vincenti che perdenti                          ║
║   • Direction Accuracy: 62% → Previsioni direzionalmente accurate            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Walk-Forward Validation

### Perché NON Usare Simple Split

```
❌ SBAGLIATO: Simple Train/Test Split
════════════════════════════════════

┌────────────────────────────────────┐┌──────────┐
│          TRAIN (80%)               ││TEST (20%)│
│       Gennaio - Ottobre            ││Nov - Dic │
└────────────────────────────────────┘└──────────┘

PROBLEMI:
1. Testi solo su Nov-Dic → E se quei mesi fossero anomali?
2. Non simula l'uso reale → In produzione ri-traini periodicamente
3. Rischio overfitting → Potresti aver "fittato" proprio quei mesi
```

### Walk-Forward: La Soluzione

```
✅ CORRETTO: Walk-Forward Validation
═══════════════════════════════════

Il modello viene RI-TRAINATO periodicamente, esattamente come
farebbe in produzione. OGNI fold è un test out-of-sample.

Fold 1: ┌────────────────────┐┌──────────┐
        │   TRAIN (90 days)  ││TEST (30d)│
        │   Gen - Mar        ││   Apr    │
        └────────────────────┘└──────────┘
                                   ↓
                            Simula trading
                            Calcola P&L

Fold 2: ┌────────────────────┐┌──────────┐
        │   TRAIN (90 days)  ││TEST (30d)│
        │   Feb - Apr        ││   Mag    │
        └────────────────────┘└──────────┘
                                   ↓
                            Simula trading

Fold 3: ┌────────────────────┐┌──────────┐
        │   TRAIN (90 days)  ││TEST (30d)│
        │   Mar - Mag        ││   Giu    │
        └────────────────────┘└──────────┘

... e così via per 12 fold ...

RISULTATO FINALE: Performance testata su TUTTO l'anno,
non solo su un periodo arbitrario.
```

---

## Configurazione [BACKTEST]

### Parametri Completi

```ini
[BACKTEST]
; ═══════════════════════════════════════════════════════════
; MODALITÀ
; ═══════════════════════════════════════════════════════════
mode = walk_forward    ; walk_forward | expanding | simple_split

; ═══════════════════════════════════════════════════════════
; FINESTRE TEMPORALI
; ═══════════════════════════════════════════════════════════
num_folds = 12              ; Numero di fold
train_window_days = 90      ; Giorni training per fold
test_window_days = 30       ; Giorni test per fold
step_days = 30              ; Avanzamento tra fold

; ═══════════════════════════════════════════════════════════
; CAPITALE E COSTI
; ═══════════════════════════════════════════════════════════
initial_capital = 100000    ; Capitale iniziale ($)
transaction_cost_pct = 0.1  ; Commissioni (%)
slippage_pct = 0.05         ; Slippage stimato (%)
risk_free_rate = 0.02       ; Risk-free rate annuo

; ═══════════════════════════════════════════════════════════
; STRATEGIA
; ═══════════════════════════════════════════════════════════
strategy = threshold        ; direction | threshold | confidence | mean_reversion
threshold_pct = 0.5         ; Soglia minima per trade (%)
confidence_threshold = 0.7  ; Per strategy=confidence

; ═══════════════════════════════════════════════════════════
; POSITION SIZING
; ═══════════════════════════════════════════════════════════
position_size_pct = 100     ; % capitale per trade
max_positions = 1           ; Max posizioni simultanee
allow_short = true          ; Permetti short selling

; ═══════════════════════════════════════════════════════════
; RISK MANAGEMENT
; ═══════════════════════════════════════════════════════════
; stop_loss_pct = 5.0       ; Stop loss (opzionale)
; take_profit_pct = 10.0    ; Take profit (opzionale)
max_drawdown_pct = 30.0     ; Max drawdown tollerato

; ═══════════════════════════════════════════════════════════
; OUTPUT
; ═══════════════════════════════════════════════════════════
output_dir = ./backtest_results
generate_plots = true
generate_report = true
save_trades = true
```

---

## Strategie di Trading

### 1. Direction (Semplice)
```python
if prediction > current_price:
    BUY
elif prediction < current_price:
    SELL (short)
```

### 2. Threshold (Consigliata)
```python
change_pct = (prediction - current_price) / current_price

if change_pct > +0.5%:    # threshold_pct
    BUY
elif change_pct < -0.5%:
    SELL
else:
    HOLD  # Evita overtrading
```

### 3. Confidence (Ensemble-Based)
```python
bullish_models = count(model_pred > current_price)
total_models = 20

if bullish_models / total_models >= 70%:  # confidence_threshold
    BUY (alta confidenza)
elif bullish_models / total_models <= 30%:
    SELL (alta confidenza short)
else:
    HOLD (modelli discordi)
```

### 4. Mean Reversion (Contrarian)
```python
z_score = (current_price - MA_20) / STD_20

if z_score < -2.0:   # Prezzo troppo basso
    BUY (mean reversion up)
elif z_score > +2.0: # Prezzo troppo alto
    SELL (mean reversion down)
```

---

## Metriche Finanziarie

### Sharpe Ratio

```
            E[R] - Rf
Sharpe = ─────────────
             σ(R)

Interpretazione:
━━━━━━━━━━━━━━━━
< 0    → PERDITA (non usare!)
0 - 1  → Scarso
1 - 2  → Buono ✓
2 - 3  → Molto buono ✓✓
> 3    → Eccellente (ma sospetta overfitting!) ⚠️
```

### Sortino Ratio

```
            E[R] - Rf
Sortino = ─────────────
           σ(R_negative)

Come Sharpe, ma penalizza SOLO volatilità negativa.
Più rilevante per trading: non ci interessa la
volatilità positiva (guadagni), solo quella negativa.
```

### Maximum Drawdown

```
Il massimo calo percentuale dal picco al minimo.

Equity: $100k → $120k → $90k → $130k
                  │       │
                  │       └── Drawdown = ($120k-$90k)/$120k = 25%
                  │
                  └── Picco

Interpretazione:
━━━━━━━━━━━━━━━━
< 10%   → Eccellente
10-20%  → Buono ✓
20-30%  → Accettabile
> 30%   → Rischioso ⚠️
> 50%   → Inaccettabile ❌
```

### Win Rate & Profit Factor

```
              Trades Vincenti
Win Rate = ────────────────────
              Totale Trades

              Σ Profitti
Profit Factor = ────────────
              Σ |Perdite|

Target:
━━━━━━━
Win Rate > 50%
Profit Factor > 1.5
```

---

## Output del Backtest

### File Generati

```
backtest_results/
├── backtest_results.json      # Tutte le metriche in JSON
├── backtest_report.xlsx       # Report Excel completo
├── trades.csv                 # Dettaglio ogni trade
├── equity_curve.png           # Grafico equity
├── drawdown.png               # Grafico drawdown
├── returns_distribution.png   # Distribuzione P&L
├── fold_performance.png       # Performance per fold
└── summary_dashboard.png      # Dashboard riassuntivo
```

### Dashboard Output

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           BACKTEST COMPLETATO                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   PERFORMANCE                              RISK                              ║
║   ───────────                              ────                              ║
║   Capitale Iniziale: $   100,000       Sharpe Ratio:       1.85             ║
║   Capitale Finale:   $   142,500       Sortino Ratio:      2.31             ║
║   Rendimento:            42.50%       Max Drawdown:      15.20%             ║
║   Annualizzato:          38.20%       Volatilità:        18.50%             ║
║                                                                              ║
║   TRADING                                  PREVISIONI                        ║
║   ───────                                  ──────────                        ║
║   Trades Totali:             156       RMSE:            0.0124              ║
║   Win Rate:               58.30%       MAE:             0.0098              ║
║   Profit Factor:           1.72       Direction Acc:     62.10%             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Come Usare Correttamente

### Workflow Completo

```
1. PREPARAZIONE
   ├── Assicurati di avere almeno 1 anno di dati storici
   ├── Configura [BACKTEST] nel file .ini
   └── Scegli strategia appropriata

2. ESECUZIONE
   python profeta-backtest.py config-lstm-backtest.ini

3. ANALISI RISULTATI
   ├── Sharpe > 1.0? → ✓ Statisticamente significativo
   ├── Max DD < 20%? → ✓ Rischio accettabile
   ├── Win Rate > 50%? → ✓ Più trade vincenti
   ├── Direction Acc > 55%? → ✓ Previsioni utili
   └── Profit Factor > 1.5? → ✓ Guadagni > Perdite

4. DECISIONE
   ┌─────────────────────────────────────────────────────────┐
   │ SE tutte le metriche sono buone:                        │
   │   → Procedi con PAPER TRADING (1-3 mesi)                │
   │   → Confronta performance live vs backtest              │
   │   → SE conferma → LIVE TRADING con capitale ridotto     │
   │                                                         │
   │ SE metriche scarse:                                     │
   │   → Rivedi configurazione modelli                       │
   │   → Prova strategia diversa                             │
   │   → Verifica qualità dati                               │
   │                                                         │
   │ SE metriche TROPPO buone (Sharpe > 3):                  │
   │   → SOSPETTA OVERFITTING!                               │
   │   → Aumenta num_folds                                   │
   │   → Usa dati più recenti                                │
   └─────────────────────────────────────────────────────────┘
```

---

## Interpretazione Risultati

### Segnali Positivi ✓

| Metrica | Valore | Significato |
|---------|--------|-------------|
| Sharpe | 1.5 - 2.5 | Rendimento risk-adjusted eccellente |
| Max DD | < 20% | Perdite contenute |
| Win Rate | 55-65% | Maggioranza trade vincenti |
| Profit Factor | 1.5 - 2.5 | Profitti > Perdite |
| Direction Acc | > 55% | Previsioni migliori del random |

### Segnali di Allarme ⚠️

| Metrica | Valore | Problema |
|---------|--------|----------|
| Sharpe | > 3.0 | Probabile overfitting |
| Sharpe | < 0.5 | Sistema non profittevole |
| Max DD | > 30% | Rischio troppo alto |
| Win Rate | < 45% | Più perdite che vincite |
| Fold Variance | Alta | Sistema instabile |

---

## Best Practices

### 1. Dati Sufficienti
```
MINIMO: 1 anno di dati
IDEALE: 2-3 anni di dati
INCLUDE: Diversi regimi di mercato (bull, bear, sideways)
```

### 2. Costi Realistici
```ini
transaction_cost_pct = 0.1   ; Commissioni reali del tuo broker
slippage_pct = 0.05          ; Stima conservativa
```

### 3. Out-of-Sample Testing
```
NON usare gli stessi dati per:
1. Sviluppo modello
2. Tuning iperparametri
3. Backtest finale

Idealmente: Train su 2022, Backtest su 2023, Live su 2024
```

### 4. Robustezza
```
Testa con diversi:
- num_folds (8, 12, 16)
- train_window_days (60, 90, 120)
- strategy (threshold, confidence)

Se i risultati sono CONSISTENTI → Sistema robusto ✓
Se variano MOLTO → Sistema fragile ⚠️
```

---

## Comandi

### Esecuzione Base
```bash
python profeta-backtest.py config-lstm-backtest.ini
```

### Con Config Personalizzata
```bash
python profeta-backtest.py /path/to/my-config.ini
```

---

**Autore**: Eng. Emilio Billi  
**Azienda**: BilliDynamics™  
**Versione**: 1.0  
**Data**: 2025
