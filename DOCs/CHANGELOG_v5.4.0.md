# PROFETA Universal v5.4.0 - Enterprise Forecasting Engine

## 🎯 Da "Buon Forecaster" a "Production-Grade System"

PROFETA v5.4.0 introduce tre upgrade fondamentali che trasformano il sistema in un **enterprise-grade forecasting engine**:

| Feature | Descrizione | Impatto Business |
|---------|-------------|------------------|
| **Conformal Prediction** | Intervalli calibrati con coverage garantita | "Il prezzo sarà $86,500 [$85,200 - $87,800] @ 90%" |
| **Walk-Forward Validation** | Valutazione realistica su time series | R² affidabile, non ottimistico |
| **Drift Monitoring** | Alerting quando il modello degrada | Zero sorprese in produzione |

---

## 1. Conformal Prediction Intervals

### Il Problema
```
v5.3.0: "Il prezzo sarà $86,500"
Cliente: "Con quanta certezza?"
v5.3.0: "Confidence: 0.92"
Cliente: "Cosa significa 0.92? Qual è il range possibile?"
```

### La Soluzione
```
v5.4.0: "Il prezzo sarà $86,500 [$85,200 - $87,800] @ 90%"
        "Con 90% di probabilità, il prezzo sarà in questo range"
```

### Come Funziona

**Split Conformal Prediction** (Vovk et al., 2005):

```python
# 1. Durante il training, su calibration set:
residuals = |y_true - y_pred|
quantile_90 = np.quantile(residuals, 0.90)  # es. $650

# 2. Per ogni nuova previsione:
point_prediction = $86,500
interval_90 = [$86,500 - $650, $86,500 + $650]
            = [$85,850, $87,150]
```

**Garanzia teorica**: Con n sufficientemente grande, la coverage empirica converge alla coverage nominale.

### Output v5.4.0
```json
{
  "timestamp": "2026-01-26T12:00:00",
  "predicted_value": 86500.00,
  "trend": "DOWN",
  "confidence": 0.92,
  "interval_90": [85200.00, 87800.00],
  "interval_50": [86100.00, 86900.00]
}
```

### CSV Output
```csv
timestamp,predicted_value,trend,confidence,interval_90_lower,interval_90_upper
2026-01-26T12:00,86500.00,DOWN,0.92,85200.00,87800.00
```

---

## 2. Walk-Forward Cross-Validation

### Il Problema

```
Standard CV (sbagliato per time series):
┌─────────────────────────────────────┐
│  SHUFFLE tutto insieme              │
│  Train su 80% random                │
│  Test su 20% random                 │
└─────────────────────────────────────┘
→ Data leakage! Futuro usato per predire passato!
→ R² ottimisticamente gonfiato
```

### La Soluzione

```
Walk-Forward (corretto):
Fold 1: [========TRAIN========][TEST]
Fold 2: [==========TRAIN==========][TEST]
Fold 3: [============TRAIN============][TEST]
Fold 4: [==============TRAIN==============][TEST]
Fold 5: [================TRAIN================][TEST]

→ Simula deployment reale
→ R² realistico
→ Misura stabilità nel tempo
```

### Utilizzo

```python
# Durante training
engine.train(data_path, run_walk_forward=True)

# Risultati
{
  "n_folds": 5,
  "mean_r2": 0.89,
  "std_r2": 0.03,
  "stability_score": 0.97,  # Molto stabile
  "degradation_detected": False
}
```

### Metriche Chiave

| Metrica | Significato | Target |
|---------|-------------|--------|
| `mean_r2` | Performance media | > 0.85 |
| `std_r2` | Variabilità | < 0.05 |
| `stability_score` | 1 - CV(R²) | > 0.90 |
| `r2_trend` | Slope R² nel tempo | > -0.01 |
| `degradation_detected` | Alert automatico | False |

---

## 3. Drift Monitoring

### Il Problema

```
Giorno 1: Modello deployato, R² = 0.92 ✅
Giorno 30: R² = 0.87, nessuno se ne accorge
Giorno 60: R² = 0.65, cliente arrabbiato 😠
Giorno 90: "Perché le previsioni sono sbagliate da mesi?"
```

### La Soluzione

```python
# Monitoring automatico
alerts = engine.check_drift(y_true_recent, y_pred_recent)

for alert in alerts:
    if alert.detected:
        send_slack_notification(f"⚠️ {alert.message}")
```

### Tipi di Drift Monitorati

| Tipo | Cosa Monitora | Alert Quando |
|------|---------------|--------------|
| **Error Drift** | Distribuzione errori | Media errori shift > 2σ |
| **Prediction Drift** | Distribuzione previsioni | Media pred shift > 2σ |
| **Performance Drift** | R², MAE | R² drop > 10% |

### Severity Levels

| Z-Score | Severity | Azione |
|---------|----------|--------|
| < 2.0 | LOW | Log |
| 2.0 - 3.0 | MEDIUM | Warning |
| 3.0 - 4.0 | HIGH | Alert team |
| > 4.0 | CRITICAL | Retrain immediato |

---

## 🔧 API Changes

### Training
```python
# v5.3.0
metrics = engine.train(data_path)

# v5.4.0 - Con walk-forward opzionale
metrics = engine.train(data_path, run_walk_forward=True)
```

### Prediction Output
```python
# v5.3.0
result.predicted_value  # $86,500

# v5.4.0 - Con intervalli
result.predicted_value  # $86,500
result.interval_90      # ($85,200, $87,800)
result.interval_50      # ($86,100, $86,900)
```

### Drift Monitoring
```python
# v5.4.0 - Nuovo metodo
alerts = engine.check_drift(y_true, y_pred)
stats = engine.get_enterprise_stats()
```

---

## 📊 Confronto Versioni

| Feature | v5.3.0 | v5.4.0 |
|---------|--------|--------|
| Point forecast | ✅ | ✅ |
| Trend detection | ✅ | ✅ |
| Volatility adaptive | ✅ | ✅ |
| **Prediction intervals** | ❌ | ✅ |
| **Walk-forward eval** | ❌ | ✅ |
| **Drift monitoring** | ❌ | ✅ |
| Enterprise-ready | ⚠️ | ✅ |

---

## 🏢 Enterprise Use Cases

### 1. Risk Management
```python
# Scenario planning con intervalli
forecast = engine.predict(data)
worst_case = forecast[-1].interval_90[0]  # Lower bound 90%
best_case = forecast[-1].interval_90[1]   # Upper bound 90%
```

### 2. Production Monitoring
```python
# Cron job giornaliero
alerts = engine.check_drift(y_actual, y_predicted)
if any(a.detected for a in alerts):
    trigger_model_review()
```

### 3. Model Governance
```python
# Audit trail
stats = engine.get_enterprise_stats()
save_to_mlflow({
    'conformal_calibration': stats['conformal'],
    'walk_forward_r2': stats['walk_forward']['mean_r2'],
    'drift_baseline': stats['drift_baseline']
})
```

---

## 📈 Roadmap Futura

| Versione | Focus | Feature |
|----------|-------|---------|
| v5.4.0 | Enterprise | ✅ Conformal + Walk-Forward + Drift |
| v5.5.0 | Explainability | SHAP values, feature importance |
| v5.6.0 | AutoML | Hyperparameter optimization |
| v6.0.0 | Multi-asset | Portfolio forecasting |

---

## 📋 Migration Guide

### Da v5.3.0 a v5.4.0

1. **Nessuna breaking change** - codice esistente funziona
2. Intervalli sono `None` se non calibrati (backward compat)
3. Nuovi metodi sono opzionali

```python
# Codice v5.3.0 funziona identico
result = engine.predict(data)
print(result[-1].predicted_value)  # Funziona

# Nuove features v5.4.0
if result[-1].interval_90:
    print(f"Range: {result[-1].interval_90}")
```

---

*PROFETA Universal v5.4.0 - "Enterprise-grade forecasting, production-ready"*
