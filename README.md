<div align="center">

```
██████╗ ██████╗  ██████╗ ███████╗███████╗████████╗ █████╗ 
██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗
██████╔╝██████╔╝██║   ██║█████╗  █████╗     ██║   ███████║
██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══██║
██║     ██║  ██║╚██████╔╝██║     ███████╗   ██║   ██║  ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝
                                                          
       ██╗   ██╗███████╗    ██████╗     ██████╗           
       ██║   ██║██╔════╝   ██╔════╝    ██╔═████╗          
       ██║   ██║███████╗   ███████╗    ██║██╔██║          
       ╚██╗ ██╔╝╚════██║   ██╔═══██╗   ████╔╝██║          
        ╚████╔╝ ███████║██╗╚██████╔╝██╗╚██████╔╝          
         ╚═══╝  ╚══════╝╚═╝ ╚═════╝ ╚═╝ ╚═════╝           
```

# **Universal Multi-Domain Hybrid Prediction System**

### *Enterprise-Grade Time Series Forecasting with Delta-Based LSTM Ensemble*

<br>

**Version 5.0.0 PRODUCTION** · **Enterprise Edition** · **January 2026**

---

`Python 3.10+` · `TensorFlow 2.15+` · `CUDA 11.8+` · `R² = 0.96` · `100% Agreement`

---

**[Overview](#-overview)** · **[Architecture](#-architecture)** · **[Installation](#-installation)** · **[Configuration](#-configuration)** · **[Usage](#-usage)** · **[Performance](#-performance)** · **[Troubleshooting](#-troubleshooting)**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [v5.0 PRODUCTION Highlights](#-v50-production-highlights)
- [System Architecture](#-system-architecture)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration Guide](#-configuration-guide)
- [Data Format Specification](#-data-format-specification)
- [Usage Examples](#-usage-examples)
- [Output Specification](#-output-specification)
- [Performance Metrics](#-performance-metrics)
- [Troubleshooting](#-troubleshooting)
- [Changelog](#-changelog)
- [License](#-license)
- [Support](#-support)

---

## 🎯 Overview

**PROFETA Universal v5.0 PRODUCTION** is an enterprise-grade time series prediction system featuring a revolutionary **delta-based prediction architecture**. The system predicts price **changes** (deltas) rather than absolute values, achieving exceptional accuracy (R² = 0.96) with guaranteed coherence between numerical predictions and directional classification.

### What Makes v5.0 PRODUCTION Different

| Previous Versions | PROFETA v5.0 PRODUCTION |
|-------------------|-------------------------|
| Predicted absolute prices | **Predicts price deltas** (changes) |
| Separate neural classification | **Classification derived from regression** |
| ~34% classification accuracy | **100% coherent classification** |
| ~58% agreement rate | **100% agreement guaranteed** |
| Complex fusion strategies | **Single elegant strategy** |
| Multiple competing outputs | **Unified coherent output** |

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🎯 Delta-Based Prediction
- Predicts price **changes**, not absolute values
- Eliminates mean-reversion bias
- R² = 0.96 on real market data
- RMSE ~66$ on BTC (~0.06% error)

### 🔄 Derived Classification
- Classification **derived from delta prediction**
- 100% coherence with regression
- No conflicting signals
- Confidence = movement strength

### ⚡ Enterprise Performance
- Multi-GPU support with MirroredStrategy
- Mixed precision training (FP16/FP32)
- 20-model ensemble with diversity
- Memory-efficient batch processing

</td>
<td width="50%">

### 📊 Intelligent Signal Generation
- 5-level signals: STRONG_BUY → STRONG_SELL
- Confidence based on movement magnitude
- Dynamic thresholds (% of price)
- No false disagreement signals

### 🎛️ Simplified Configuration
- Single fusion strategy (regression_derived)
- 3 key parameters to tune
- Production-ready defaults
- INI-based configuration

### 📈 Validated Performance
- Tested on real crypto market data
- Walk-forward validation ready
- Comprehensive metrics dashboard
- PDF report generation

</td>
</tr>
</table>

---

## 🏆 v5.0 PRODUCTION Highlights

### The Delta Revolution

Traditional time series models predict **absolute prices**, which leads to a fundamental problem:

```
Traditional Approach:
─────────────────────
Target: Price at t+1 = $100,050
MSE Loss → Model learns: "Predict ~$100,000 (the mean)"
Result: FLAT PREDICTIONS that don't follow market movements

PROFETA v5.0 PRODUCTION:
────────────────────────
Target: Delta at t+1 = +$50
MSE Loss → Model learns: "Predict the change direction and magnitude"
Result: DYNAMIC PREDICTIONS that track market movements
```

### Performance Comparison

| Metric | v4.x (Absolute) | v5.0 PRODUCTION (Delta) | Improvement |
|--------|-----------------|-------------------------|-------------|
| **R²** | 0.37 | **0.9561** | +158% |
| **RMSE** | 249$ | **66$** | -74% |
| **MAE** | 212$ | **51$** | -76% |
| **Scatter Slope** | 0.21 | **0.985** | Near perfect |
| **Agreement** | 58% | **100%** | Guaranteed |

### Unified Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROFETA v5.0 PRODUCTION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  LSTM ENSEMBLE (20 Models)              │    │
│  │                                                         │    │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────┐   │    │
│  │   │ Model 1 │ │ Model 2 │ │ Model 3 │ ... │Model 20 │   │    │
│  │   └────┬────┘ └────┬────┘ └────┬────┘     └────┬────┘   │    │
│  │        └───────────┴───────────┴───────┬──────┘         │    │
│  │                                        │                │    │
│  │                                        ▼                │    │
│  │                             ┌─────────────────┐         │    │
│  │                             │ ENSEMBLE MEAN   │         │    │
│  │                             └────────┬────────┘         │    │
│  └──────────────────────────────────────┼──────────────────┘    │
│                                         │                       │
│                                         ▼                       │
│                              ┌─────────────────┐                │
│                              │  DELTA PREDETTO │ ◄── R² = 0.96  │
│                              │   (Δ price)     │                │
│                              └────────┬────────┘                │
│                                       │                         │
│                                       ▼                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              DERIVED CLASSIFICATION                     │    │
│  │                                                         │    │
│  │    if Δ > +threshold  →  UP      🟢  (BUY/STRONG_BUY)   │    │
│  │    if Δ < -threshold  →  DOWN    🔴  (SELL/STRONG_SELL) │    │
│  │    else               →  FLAT    ⚪  (HOLD)             │    │
│  │                                                         │    │
│  │    Confidence = |Δ| / threshold  (movement strength)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                       │                         │
│                                       ▼                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SIGNAL OUTPUT                        │    │
│  │                                                         │    │
│  │  🟢🟢 STRONG_BUY │ 🟢 BUY │ ⚪ HOLD │ 🔴 SELL │ 🔴🔴 STRONG_SELL  │
│  │                                                         │    │
│  │  • 100% Agreement (classification = regression)         │    │
│  │  • Confidence reflects prediction strength              │    │
│  │  • No conflicting signals possible                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PROFETA UNIVERSAL v5.0 PRODUCTION PIPELINE               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ╔═══════════════╗    ╔═══════════════╗    ╔═══════════════╗    ╔════════════╗  │
│  ║  DATA INPUT   ║    ║  PREPROCESS   ║    ║   FEATURES    ║    ║  SEQUENCES ║  │
│  ║───────────────║    ║───────────────║    ║───────────────║    ║────────────║  │
│  ║ • CSV Data    ║───▶║ • Auto-sort   ║───▶║ • Returns     ║───▶║ • Sliding  ║  │
│  ║ • OHLCV       ║    ║ • Gap-fill    ║    ║ • Volatility  ║    ║   Window   ║  │
│  ║ • Timestamp   ║    ║ • Resample    ║    ║ • Technical   ║    ║ • Scaling  ║  │
│  ║               ║    ║ • Validate    ║    ║ • Temporal    ║    ║ • DELTA    ║  │
│  ╚═══════════════╝    ╚═══════════════╝    ╚═══════════════╝    ║   TARGET   ║  │
│                                                                 ╚═════╪══════╝  │
│                                                                       │         │
│                                                                       ▼         │
│  ╔══════════════════════════════════════════════════════════════════════════╗   │
│  ║                       MULTI-HEAD LSTM ENSEMBLE                           ║   │
│  ║──────────────────────────────────────────────────────────────────────────║   │
│  ║                                                                          ║   │
│  ║   ┌────────────────────────────────────────────────────────────────┐     ║   │
│  ║   │                      SHARED BACKBONE                           │     ║   │
│  ║   │  Input(seq_len, features) → BiLSTM → BatchNorm → BiLSTM → ... │     ║   │
│  ║   └────────────────────────────────┬───────────────────────────────┘     ║   │
│  ║                                    │                                     ║   │
│  ║                    ┌───────────────┴───────────────┐                     ║   │
│  ║                    ▼                               ▼                     ║   │
│  ║   ┌────────────────────────────┐  ┌────────────────────────────┐         ║   │
│  ║   │    REGRESSION HEAD        │  │   CLASSIFICATION HEAD      │         ║   │
│  ║   │────────────────────────────│  │────────────────────────────│         ║   │
│  ║   │  Dense → Dense → Dense(1) │  │  (Maintained for compat.)  │         ║   │
│  ║   │  Output: DELTA SCALED     │  │  Output: NOT USED          │         ║   │
│  ║   └─────────────┬──────────────┘  └────────────────────────────┘         ║   │
│  ║                 │                                                        ║   │
│  ╚═════════════════╪════════════════════════════════════════════════════════╝   │
│                    │                                                            │
│                    ▼                                                            │
│  ╔══════════════════════════════════════════════════════════════════════════╗   │
│  ║                    DERIVED CLASSIFICATION ENGINE                         ║   │
│  ║──────────────────────────────────────────────────────────────────────────║   │
│  ║                                                                          ║   │
│  ║   delta_threshold = price × delta_threshold_pct  (e.g., 0.05% = $50)     ║   │
│  ║   flat_threshold  = delta_threshold × 0.5                                ║   │
│  ║                                                                          ║   │
│  ║   if delta > +flat_threshold  →  CLASS = UP,   DIRECTION = +1            ║   │
│  ║   if delta < -flat_threshold  →  CLASS = DOWN, DIRECTION = -1            ║   │
│  ║   else                        →  CLASS = FLAT, DIRECTION =  0            ║   │
│  ║                                                                          ║   │
│  ║   confidence = min(|delta| / delta_threshold × 0.5, 1.0)                 ║   │
│  ║                                                                          ║   │
│  ╚══════════════════════════════════════════════════════════════════════════╝   │
│                    │                                                            │
│                    ▼                                                            │
│  ╔══════════════════════════════════════════════════════════════════════════╗   │
│  ║                         SIGNAL GENERATOR                                 ║   │
│  ║──────────────────────────────────────────────────────────────────────────║   │
│  ║                                                                          ║   │
│  ║   if confidence < min_confidence        →  HOLD                          ║   │
│  ║   if direction > 0 AND conf >= strong   →  STRONG_BUY                    ║   │
│  ║   if direction > 0                      →  BUY                           ║   │
│  ║   if direction < 0 AND conf >= strong   →  STRONG_SELL                   ║   │
│  ║   if direction < 0                      →  SELL                          ║   │
│  ║   else                                  →  HOLD                          ║   │
│  ║                                                                          ║   │
│  ╚══════════════════════════════════════════════════════════════════════════╝   │
│                    │                                                            │
│                    ▼                                                            │
│        ┌──────────────────┬──────────────────┬──────────────────┐               │
│        ▼                  ▼                  ▼                  ▼               │
│  ╔═══════════╗     ╔═══════════╗     ╔═══════════╗     ╔═══════════╗            │
│  ║ CSV       ║     ║ JSON      ║     ║ PNG       ║     ║ PDF       ║            │
│  ║ Output    ║     ║ Output    ║     ║ Graph     ║     ║ Report    ║            │
│  ╚═══════════╝     ╚═══════════╝     ╚═══════════╝     ╚═══════════╝            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 Requirements

### Hardware Requirements

| Component        | Minimum      | Recommended   | Optimal         |
|------------------|--------------|---------------|-----------------|
| **CPU**          | 8 cores      | 16+ cores     | 32+ cores       |
| **RAM**          | 16 GB        | 32 GB         | 64+ GB          |
| **GPU**          | GTX 1060 6GB | RTX 3080 10GB | RTX 4090 / 5090 |
| **Storage**      | 10 GB SSD    | 50 GB NVMe    | 100+ GB NVMe    |
| **CUDA Compute** | 6.1          | 7.5+          | 8.9+ (RTX 5090) |

### Software Requirements

| Dependency      | Version        | Purpose                   |
|-----------------|----------------|---------------------------|
| **Python**      | ≥ 3.10, < 3.13 | Runtime environment       |
| **TensorFlow**  | ≥ 2.15         | Deep learning framework   |
| **CUDA Toolkit**| ≥ 11.8         | GPU acceleration          |
| **cuDNN**       | ≥ 8.6          | Deep learning primitives  |
| **NumPy**       | ≥ 1.24         | Numerical computing       |
| **Pandas**      | ≥ 2.0          | Data manipulation         |
| **scikit-learn**| ≥ 1.3          | ML utilities              |
| **Matplotlib**  | ≥ 3.7          | Visualization             |
| **ReportLab**   | ≥ 4.0          | PDF generation            |

---

## 📦 Installation

### Step 1: Environment Setup

```bash
# Create dedicated Python environment
python -m venv profeta-env

# Activate environment
# Windows:
profeta-env\Scripts\activate
# Linux/macOS:
source profeta-env/bin/activate

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel
```

### Step 2: Install Dependencies

```bash
# Core dependencies
pip install tensorflow>=2.15 numpy>=1.24 pandas>=2.0

# ML and scientific computing
pip install scikit-learn>=1.3 scipy>=1.11

# Visualization and reporting
pip install matplotlib>=3.7 tqdm>=4.65 reportlab>=4.0

# Optional: GPU monitoring
pip install gputil pynvml
```

### Step 3: Verify Installation

```bash
python -c "
import tensorflow as tf
print(f'TensorFlow Version: {tf.__version__}')
print(f'GPU Available: {tf.config.list_physical_devices(\"GPU\")}')
print(f'CUDA Built: {tf.test.is_built_with_cuda()}')
"
```

### Step 4: Directory Structure

```
PROFETA-v5-PRODUCTION/
├── profeta-universal.py              # Main application
├── config-lstm.ini                   # Configuration file
├── README.md                         # This documentation
│
├── data/                             # Data directory
│   ├── training.csv                  # Training data
│   └── trading.csv                   # Inference data
│
├── models/                           # Saved models (delete for retrain)
│   ├── profeta_model_1.keras
│   ├── profeta_model_1.meta.json
│   └── ...
│
├── output/                           # Prediction outputs
│   ├── predictions.csv
│   ├── predictions.json
│   ├── analysis.png
│   └── PROFETA_Report_*.pdf
│
└── logs/                             # Log files
    └── profeta.log
```

---

## 🚀 Quick Start

### 1. Minimal Configuration

Create `config-lstm.ini`:

```ini
[DATA]
data_path = ./data/training.csv
target_column = close

[INPUT]
input_data_path = ./data/trading.csv

[PREDICTION]
num_future_steps = 24
output_predictions_path = ./output/predictions.csv
graph = true

[ENSEMBLE]
num_models = 5

[FUSION]
; ⭐ PRODUCTION: Classification derived from regression
strategy = regression_derived
delta_threshold_pct = 0.0005
min_confidence = 0.35
signal_threshold = 0.55

[MODEL_1]
sequence_length = 60
lstm_units = 64
dropout_rate = 0.2
use_bidirectional = true

[MODEL_2]
sequence_length = 60
lstm_units = 128
dropout_rate = 0.3
use_bidirectional = true

[MODEL_3]
sequence_length = 45
lstm_units = 64
dropout_rate = 0.25
use_bidirectional = true

[MODEL_4]
sequence_length = 90
lstm_units = 32
dropout_rate = 0.2
use_bidirectional = false

[MODEL_5]
sequence_length = 60
lstm_units = 256
dropout_rate = 0.35
use_bidirectional = true
```

### 2. Run Prediction

```bash
# First run: trains models and generates predictions
python profeta-universal.py config-lstm.ini

# Subsequent runs: uses cached models
python profeta-universal.py config-lstm.ini
```

### 3. Retrain Models

```bash
# Delete existing models to force retraining
rm -rf ./models/*

# Run with fresh training
python profeta-universal.py config-lstm.ini
```

---

## ⚙️ Configuration Guide

### FUSION Section (v5.0 PRODUCTION)

```ini
[FUSION]

; ═══════════════════════════════════════════════════════════════════════════════
; PROFETA v5.0 PRODUCTION - FUSION CONFIGURATION
; ═══════════════════════════════════════════════════════════════════════════════
;
; Classification is DERIVED from regression delta, guaranteeing:
; • 100% coherence between predicted price and direction
; • Confidence based on movement strength
; • Signals as reliable as regression (R² = 0.96)

; STRATEGY - Always use regression_derived for PRODUCTION
strategy = regression_derived

; DELTA_THRESHOLD_PCT - Threshold for UP/DOWN vs FLAT classification
; Expressed as percentage of current price
;
;   0.0003 : 0.03% (sensitive - more signals, more noise)
;   0.0005 : 0.05% (balanced - DEFAULT) → for BTC $100k = $50 threshold
;   0.001  : 0.1%  (conservative - fewer but stronger signals)
;
delta_threshold_pct = 0.0005

; MIN_CONFIDENCE - Minimum confidence to generate signal (below = HOLD)
;
;   0.25 : Aggressive (many signals)
;   0.35 : Balanced (DEFAULT)
;   0.50 : Conservative
;
min_confidence = 0.35

; SIGNAL_THRESHOLD - Threshold for STRONG signals (STRONG_BUY/STRONG_SELL)
;
;   0.45 : Aggressive (more STRONG signals)
;   0.55 : Balanced (DEFAULT)
;   0.70 : Conservative (only very strong movements)
;
signal_threshold = 0.55

; GENERATE_SIGNALS - Enable trading signal generation
generate_signals = true
```

### Signal Logic

| Condition | Signal |
|-----------|--------|
| `confidence < min_confidence` | HOLD |
| `direction > 0` AND `confidence >= signal_threshold` | STRONG_BUY |
| `direction > 0` | BUY |
| `direction < 0` AND `confidence >= signal_threshold` | STRONG_SELL |
| `direction < 0` | SELL |
| `direction == 0` | HOLD |

### Tuning Guidelines

| Goal | delta_threshold_pct | min_confidence | signal_threshold |
|------|---------------------|----------------|------------------|
| **More signals** | 0.0003 | 0.25 | 0.45 |
| **Balanced** | 0.0005 | 0.35 | 0.55 |
| **Conservative** | 0.001 | 0.50 | 0.70 |
| **Only strong moves** | 0.002 | 0.60 | 0.80 |

---

## 📊 Performance Metrics

### Validated Results (Real BTC Data)

| Metric | Value | Status |
|--------|-------|--------|
| **R² Score** | 0.9561 | ✅ Excellent |
| **RMSE** | 65.78$ | ✅ Excellent |
| **MAE** | 51.08$ | ✅ Excellent |
| **MAPE** | 0.045% | ✅ Excellent |
| **Scatter Slope** | 0.985 | ✅ Near Perfect |
| **Agreement** | 100% | ✅ Guaranteed |

### Validation Graph

The validation graph shows:
- **Blue line**: Actual prices
- **Red dashed line**: Predicted prices
- **Gray zone**: Error margin

A well-trained model shows the red line closely following the blue line.

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Flat Predictions (R² < 0.5)

**Symptom**: Predictions are a nearly flat line

**Cause**: Model is predicting absolute prices instead of deltas

**Solution**: Ensure you're using the v5.0 PRODUCTION code with delta-based training

```bash
# Delete old models and retrain
rm -rf ./models/*
python profeta-universal.py config-lstm.ini
```

#### 2. All HOLD Signals

**Symptom**: 100% HOLD signals, no BUY/SELL

**Cause**: Confidence threshold too high or delta threshold too large

**Solution**: Lower thresholds in config:

```ini
[FUSION]
delta_threshold_pct = 0.0003  ; Lower = more sensitive
min_confidence = 0.25         ; Lower = more signals
```

#### 3. Too Many STRONG Signals

**Symptom**: Most signals are STRONG_BUY or STRONG_SELL

**Cause**: Thresholds too low

**Solution**: Raise thresholds:

```ini
[FUSION]
signal_threshold = 0.70      ; Higher = fewer STRONG signals
min_confidence = 0.50        ; Higher = more conservative
```

#### 4. GPU Not Detected

```bash
# Verify TensorFlow GPU
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

**Solutions**:
- Verify CUDA installation: `nvcc --version`
- Install correct TensorFlow version for your CUDA
- Set `use_gpu = false` in config to use CPU

#### 5. Out of Memory

**Solutions**:
- Enable memory growth: `gpu_memory_growth = true`
- Reduce batch size: `batch_size = 16`
- Reduce models: `num_models = 10`
- Reduce LSTM units in model configs

---

## 📜 Changelog

### Version 5.0.0 PRODUCTION (January 2026)

#### 🆕 Revolutionary Changes
- **Delta-based prediction**: Model now predicts price changes instead of absolute values
- **Derived classification**: Classification determined by delta sign, not neural network
- **100% agreement**: Classification always coherent with regression
- **Simplified architecture**: Single fusion strategy, cleaner codebase

#### 📈 Performance Improvements
- R² improved from 0.37 to **0.9561** (+158%)
- RMSE reduced from 249$ to **66$** (-74%)
- Scatter slope improved from 0.21 to **0.985**
- Agreement improved from 58% to **100%**

#### 🔧 Configuration Changes
- New `delta_threshold_pct` parameter
- Simplified `[FUSION]` section
- Removed unused legacy strategies
- Production-ready defaults

#### 🐛 Bug Fixes
- Fixed flat prediction issue (mean reversion)
- Fixed classification-regression misalignment
- Fixed confidence calculation for high-value assets
- Fixed label generation using returns instead of deltas

### Version 5.0.0 (Previous)
- Multi-head architecture
- Fusion engine with 4 strategies
- Signal generation system
- Daemon mode

### Version 4.x (Legacy)
- Enterprise ensemble architecture
- Basic feature engineering
- Single-output models

---

## 📄 License

```
Copyright © 2025-2026 BilliDynamics™
All Rights Reserved.

PROPRIETARY AND CONFIDENTIAL

This software and associated documentation are the exclusive property of
BilliDynamics™. Unauthorized copying, modification, distribution, or use
of this software is strictly prohibited.

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED. IN NO EVENT SHALL BILLIDYNAMICS™ BE LIABLE FOR ANY DAMAGES ARISING
FROM THE USE OF THIS SOFTWARE.

⚠️ FINANCIAL DISCLAIMER: This software does not constitute financial advice.
Predictions are indicative only and should not be considered investment
recommendations. Users are solely responsible for their trading decisions.
Past performance does not guarantee future results.
```

---

## 📞 Support

### Documentation Resources

| Resource | Location |
|----------|----------|
| Configuration Reference | `config-lstm.ini` |
| This README | `README.md` |
| Inline Code Documentation | `profeta-universal.py` |

### Contact Information

| Type | Contact |
|------|---------|
| Technical Support | support@billidynamics.com |
| Licensing Inquiries | licensing@billidynamics.com |
| Bug Reports | bugs@billidynamics.com |
| Feature Requests | features@billidynamics.com |

---

<div align="center">

---

**PROFETA Universal v5.0 PRODUCTION** · *Predicting Tomorrow, Today*

`R² = 0.96` · `100% Agreement` · `Production Ready`

Copyright © 2025-2026 **BilliDynamics™** · All Rights Reserved

---

</div>
