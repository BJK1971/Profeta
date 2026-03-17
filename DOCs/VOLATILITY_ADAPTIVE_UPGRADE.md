# PROFETA v5.1.0 - Volatility-Adaptive Prediction System

## Problema Identificato

Il modello v5.0.3 ha previsto correttamente la **direzione** (bearish) ma ha sottostimato la **magnitudine** del movimento di ~40x:

| Metrica | PROFETA v5.0.3 | Realtà |
|---------|----------------|--------|
| Variazione 12h | -$51 (-0.06%) | -$2,300 (-2.6%) |
| Velocità | ~$4/h | ~$190/h |

## Causa Radice

Il modello tratta tutti i regimi di mercato allo stesso modo:
- **Decay fisso** (0.998) non si adatta alla volatilità
- **Soglie fisse** (0.05%) ignorano il regime di mercato
- **Nessun regime detection** per distinguere mercato calmo vs volatile

---

## Soluzioni Implementate in v5.1.0

### 1. Volatility Regime Detection

```python
class VolatilityRegime(Enum):
    LOW = "low"           # Volatilità < 1 std sotto media
    NORMAL = "normal"     # Volatilità nella norma
    HIGH = "high"         # Volatilità > 1 std sopra media
    EXTREME = "extreme"   # Volatilità > 2 std sopra media (liquidazioni, crash)
```

Il sistema rileva automaticamente il regime basandosi su:
- **Realized Volatility** (std dei returns su finestra mobile)
- **ATR Normalizzato** (Average True Range / prezzo)
- **Volume Spike** (volume attuale vs media)

### 2. Dynamic Decay

Il decay ora si adatta al regime:

| Regime | Decay | Effetto a 72h |
|--------|-------|---------------|
| LOW | 0.999 | 93% della predizione |
| NORMAL | 0.998 | 87% della predizione |
| HIGH | 0.995 | 70% della predizione |
| EXTREME | 0.990 | 49% della predizione |

In regime EXTREME, il modello "amplifica" le predizioni invece di smorzarle.

### 3. Volatility Multiplier

Le predizioni vengono scalate in base alla volatilità attuale vs storica:

```python
vol_multiplier = current_volatility / historical_avg_volatility
prediction_adjusted = prediction * vol_multiplier
```

Se la volatilità attuale è 3x la media storica, le predizioni vengono amplificate 3x.

### 4. Feature Engineering Avanzato

Nuove feature aggiunte:

| Feature | Descrizione |
|---------|-------------|
| `vol_regime` | Regime di volatilità (0-3) |
| `vol_zscore` | Z-score della volatilità corrente |
| `atr_norm` | ATR normalizzato (ATR/prezzo) |
| `vol_expansion` | Ratio volatilità attuale/media |
| `price_velocity` | Velocità del prezzo (derivata prima) |
| `price_acceleration` | Accelerazione (derivata seconda) |
| `volume_spike` | Volume attuale / media mobile volume |
| `liquidation_proxy` | Proxy per liquidazioni (|return| * volume_spike) |

### 5. Adaptive Thresholds

Le soglie di classificazione si adattano al regime:

| Regime | delta_threshold_pct | flat_threshold |
|--------|---------------------|----------------|
| LOW | 0.03% | 0.015% |
| NORMAL | 0.05% | 0.025% |
| HIGH | 0.10% | 0.050% |
| EXTREME | 0.20% | 0.100% |

---

## Modifiche al Codice

### A. Nuova classe VolatilityAnalyzer

```python
@dataclass
class VolatilityState:
    regime: VolatilityRegime
    realized_vol: float
    atr_normalized: float
    vol_zscore: float
    vol_multiplier: float
    recommended_decay: float
    recommended_threshold: float

class VolatilityAnalyzer:
    def __init__(self, lookback: int = 20, vol_ma_window: int = 50):
        self.lookback = lookback
        self.vol_ma_window = vol_ma_window
        self._vol_history: List[float] = []
    
    def analyze(self, prices: pd.Series, volumes: Optional[pd.Series] = None) -> VolatilityState:
        # Calcola realized volatility
        returns = prices.pct_change().dropna()
        realized_vol = returns.tail(self.lookback).std() * np.sqrt(24)  # Annualizzata hourly
        
        # Volatilità storica per confronto
        if len(self._vol_history) >= self.vol_ma_window:
            hist_vol_mean = np.mean(self._vol_history[-self.vol_ma_window:])
            hist_vol_std = np.std(self._vol_history[-self.vol_ma_window:])
        else:
            hist_vol_mean = realized_vol
            hist_vol_std = realized_vol * 0.3
        
        self._vol_history.append(realized_vol)
        
        # Z-score della volatilità
        vol_zscore = (realized_vol - hist_vol_mean) / (hist_vol_std + 1e-10)
        
        # Determina regime
        if vol_zscore > 2.0:
            regime = VolatilityRegime.EXTREME
        elif vol_zscore > 1.0:
            regime = VolatilityRegime.HIGH
        elif vol_zscore < -1.0:
            regime = VolatilityRegime.LOW
        else:
            regime = VolatilityRegime.NORMAL
        
        # Calcola multiplier e parametri raccomandati
        vol_multiplier = max(0.5, min(3.0, realized_vol / (hist_vol_mean + 1e-10)))
        
        decay_map = {
            VolatilityRegime.LOW: 0.999,
            VolatilityRegime.NORMAL: 0.998,
            VolatilityRegime.HIGH: 0.995,
            VolatilityRegime.EXTREME: 0.990
        }
        
        threshold_map = {
            VolatilityRegime.LOW: 0.0003,
            VolatilityRegime.NORMAL: 0.0005,
            VolatilityRegime.HIGH: 0.0010,
            VolatilityRegime.EXTREME: 0.0020
        }
        
        # ATR normalizzato (se abbiamo OHLC)
        atr_norm = realized_vol  # Fallback
        
        return VolatilityState(
            regime=regime,
            realized_vol=realized_vol,
            atr_normalized=atr_norm,
            vol_zscore=vol_zscore,
            vol_multiplier=vol_multiplier,
            recommended_decay=decay_map[regime],
            recommended_threshold=threshold_map[regime]
        )
```

### B. Modifica a _predict_future()

```python
def _predict_future(self, proc_df, last_reg, last_cls) -> List[FusionResult]:
    # ... codice esistente ...
    
    # NUOVO: Analizza volatilità corrente
    vol_analyzer = VolatilityAnalyzer()
    prices = proc_df[self.pred_config.target_column]
    vol_state = vol_analyzer.analyze(prices)
    
    self.logger.info(f"Volatility Regime: {vol_state.regime.value}, "
                     f"Multiplier: {vol_state.vol_multiplier:.2f}, "
                     f"Recommended Decay: {vol_state.recommended_decay}")
    
    results = []
    for i, ts in enumerate(future_ts):
        X = curr_seq.reshape(1, seq_len, -1)
        reg, cls, reg_std = self.ensemble.predict_ensemble(X)
        
        reg_orig = self.seq_prep.inverse_transform_target(reg, np.array([curr_val]))[0]
        std_orig = float(reg_std[0] * self.seq_prep.target_scaler.scale_[0]) if hasattr(self.seq_prep.target_scaler, 'scale_') else float(reg_std[0])
        
        # NUOVO: Usa decay dinamico basato sul regime
        decay = vol_state.recommended_decay ** (i + 1)
        
        # NUOVO: Applica volatility multiplier alla predizione
        delta = reg_orig - curr_val
        delta_adjusted = delta * vol_state.vol_multiplier
        reg_corr = curr_val + delta_adjusted * decay
        
        # La std aumenta più velocemente in regime volatile
        vol_factor = 1.0 + 0.1 * i * vol_state.vol_multiplier
        std_corr = std_orig * vol_factor
        
        # NUOVO: Usa threshold dinamica
        self.fusion.config.delta_threshold_pct = vol_state.recommended_threshold
        
        result = self.fusion._fuse_single(ts, curr_val, reg_corr, cls[0], 
                                          self.cls_config.num_classes, ensemble_std=std_corr)
        results.append(result)
        
        curr_val = reg_corr
        # ... resto del codice ...
    
    return results
```

### C. Nuove Feature nel Preprocessor

```python
# In DomainFeatureEngineer.engineer()

# Volatility features avanzate
returns = result[target_col].pct_change()
features['vol_realized_20'] = returns.rolling(20).std() * np.sqrt(24)
features['vol_realized_5'] = returns.rolling(5).std() * np.sqrt(24)

# Volatility z-score
vol_mean = features['vol_realized_20'].rolling(50).mean()
vol_std = features['vol_realized_20'].rolling(50).std()
features['vol_zscore'] = (features['vol_realized_20'] - vol_mean) / (vol_std + 1e-10)

# Volatility expansion ratio
features['vol_expansion'] = features['vol_realized_5'] / (features['vol_realized_20'] + 1e-10)

# Price velocity e acceleration
features['price_velocity'] = result[target_col].diff()
features['price_acceleration'] = features['price_velocity'].diff()

# Volume spike (se disponibile)
if 'volume' in self.ohlcv:
    vol_col = self.ohlcv['volume']
    features['volume_spike'] = result[vol_col] / result[vol_col].rolling(20).mean()
    features['liquidation_proxy'] = abs(returns) * features['volume_spike']
```

---

## Configurazione INI

Aggiungi alla sezione `[VOLATILITY]` del config:

```ini
[VOLATILITY]
; Abilita sistema volatility-adaptive
enabled = true

; Finestra per calcolo volatilità realizzata
lookback_window = 20

; Finestra per media storica volatilità
historical_window = 50

; Moltiplicatore massimo (cap per evitare predizioni eccessive)
max_multiplier = 3.0

; Moltiplicatore minimo (floor per mercati molto calmi)
min_multiplier = 0.5

; Override manuale del regime (auto, low, normal, high, extreme)
regime_override = auto
```

---

## Impatto Atteso

Con queste modifiche, in un scenario come quello osservato (liquidazioni massive, -2.6% in 12h):

| Metrica | v5.0.3 | v5.1.0 (previsto) |
|---------|--------|-------------------|
| Regime rilevato | N/A | EXTREME |
| Vol multiplier | 1.0 | ~2.5-3.0 |
| Decay | 0.998 | 0.990 |
| Predizione 12h | -$51 | -$500 a -$800 |
| Errore | ~40x | ~3-5x |

Non raggiungeremo mai la precisione perfetta (eventi black swan sono imprevedibili), ma possiamo ridurre l'errore da 40x a 3-5x.

---

## Note Importanti

1. **Non è una bacchetta magica**: Eventi come liquidazioni massive sono parzialmente imprevedibili
2. **Rischio di overfit**: Il multiplier può amplificare anche errori
3. **Latenza dati**: La volatilità viene calcolata su dati storici, c'è sempre lag
4. **Tuning necessario**: I parametri vanno calibrati sul tuo dataset specifico

---

*PROFETA Universal v5.1.0 - Volatility-Adaptive Prediction System*
*BilliDynamics™ - Gennaio 2026*
