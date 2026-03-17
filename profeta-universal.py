#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║     ██████╗ ██████╗  ██████╗ ███████╗███████╗████████╗ █████╗     ██╗   ██╗███████╗     ║
║     ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗    ██║   ██║██╔════╝     ║
║     ██████╔╝██████╔╝██║   ██║█████╗  █████╗     ██║   ███████║    ██║   ██║███████╗     ║
║     ██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══██║    ╚██╗ ██╔╝╚════██║     ║
║     ██║     ██║  ██║╚██████╔╝██║     ███████╗   ██║   ██║  ██║     ╚████╔╝ ███████║     ║
║     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝      ╚═══╝  ╚══════╝     ║
║                                                                                          ║
║                    UNIVERSAL MULTI-DOMAIN PREDICTION SYSTEM                              ║
║                              Version 5.0 Enterprise                                      ║
║══════════════════════════════════════════════════════════════════════════════════════════║
║  HYBRID ARCHITECTURE: Multi-Head Neural Network (Regression + Classification)           ║
║  DOMAINS: Financial, Energy, Environmental, Generic                                      ║
║  Author: Eng. Emilio Billi | Company: BilliDynamics™ | Copyright © 2025                 ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import os, sys, gc, time, pickle, signal, socket, logging, hashlib, platform, io
import datetime, threading, functools, traceback, configparser, json, warnings, uuid
from enum import Enum, auto, unique
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import (Tuple, List, Dict, Optional, Union, Any, Set, Callable, 
                   TypeVar, Final, ClassVar, Sequence)
from contextlib import contextmanager
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    OpenMP THREAD SAFETY FIX
# ═══════════════════════════════════════════════════════════════════════════════════════════
# Fix per libgomp: assicura che OMP_NUM_THREADS sia valido prima del caricamento di numpy/tf
_omp_threads = os.environ.get('OMP_NUM_THREADS', '').strip()
if not _omp_threads or not _omp_threads.isdigit():
    _default_threads = str(min(os.cpu_count() or 4, 8))
    os.environ['OMP_NUM_THREADS'] = _default_threads
    os.environ['MKL_NUM_THREADS'] = _default_threads
    os.environ['OPENBLAS_NUM_THREADS'] = _default_threads
del _omp_threads

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score,
                            accuracy_score, precision_score, recall_score, f1_score, confusion_matrix)
from sklearn.utils.class_weight import compute_class_weight

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from tqdm import tqdm

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    GPU/CPU DEVICE SELECTION
# ═══════════════════════════════════════════════════════════════════════════════════════════
# Forza CPU se: PROFETA_FORCE_CPU=1 oppure GPU con compute capability non supportata
_force_cpu = os.environ.get('PROFETA_FORCE_CPU', '').strip() == '1'
_auto_disabled_gpu = False

if _force_cpu:
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    print("[PROFETA] Forcing CPU mode (PROFETA_FORCE_CPU=1)")

import tensorflow as tf

if _auto_disabled_gpu:
    pass  # già gestito
elif not _force_cpu and os.environ.get('PROFETA_FORCE_GPU', '') != '1':
    # Verifica post-import se la GPU è problematica
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                details = tf.config.experimental.get_device_details(gpu)
                cc = details.get('compute_capability', (0, 0))
                if cc[0] >= 12:
                    print(f"[PROFETA] WARNING: GPU {gpu.name} (compute capability {cc[0]}.{cc[1]}) may not be fully supported")
                    print(f"[PROFETA] If you see CUDA errors, run with: PROFETA_FORCE_CPU=1 python profeta-universal.py")
    except Exception:
        pass

del _force_cpu, _auto_disabled_gpu

from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (LSTM, GRU, Dense, Dropout, Bidirectional, Input,
                                    BatchNormalization, MultiHeadAttention, GlobalAveragePooling1D)
from tensorflow.keras.callbacks import EarlyStopping, Callback, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2
from tensorflow.keras import backend as K
from tensorflow.keras.utils import to_categorical

tf.get_logger().setLevel('ERROR')

__version__: Final[str] = "5.7.1"  # Enterprise - Fix trend calculation on predicted delta
__author__: Final[str] = "Eng. Emilio Billi"
__company__: Final[str] = "BilliDynamics™"

# Constants
MAX_SEQUENCE_LENGTH, MIN_SEQUENCE_LENGTH = 2000, 5
DEFAULT_RANDOM_SEED, EPSILON = 42, 1e-10
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"

# Technical Indicators Constants
RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL = 14, 12, 26, 9
BOLLINGER_PERIOD, BOLLINGER_STD, ATR_PERIOD = 20, 2.0, 14


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    EXCEPTION HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════════════════════

class PROFETAError(Exception):
    _error_registry: ClassVar[Dict[str, int]] = defaultdict(int)
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict] = None, recoverable: bool = False):
        self.message, self.details = message, details or {}
        self.error_code = error_code or f"PRF-{hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:6]}"
        self.recoverable, self.timestamp = recoverable, datetime.datetime.now()
        PROFETAError._error_registry[self.__class__.__name__] += 1
        super().__init__(f"[{self.error_code}] {message}")

class ConfigurationError(PROFETAError): pass
class ValidationError(PROFETAError): pass
class DataError(PROFETAError): pass
class DomainError(PROFETAError): pass
class FeatureEngineeringError(PROFETAError): pass
class GranularityError(PROFETAError): pass
class ModelError(PROFETAError): pass
class TrainingError(PROFETAError): pass
class PredictionError(PROFETAError): pass
class FusionError(PROFETAError): pass
class GPUError(PROFETAError): pass
class StateError(PROFETAError): pass

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════

@unique
class DomainType(Enum):
    FINANCIAL = "financial"
    ENERGY = "energy"
    ENVIRONMENTAL = "environmental"
    GENERIC = "generic"
    
    @classmethod
    def from_string(cls, v: str) -> 'DomainType':
        m = {'financial': cls.FINANCIAL, 'finance': cls.FINANCIAL, 'crypto': cls.FINANCIAL,
             'forex': cls.FINANCIAL, 'energy': cls.ENERGY, 'electricity': cls.ENERGY,
             'environmental': cls.ENVIRONMENTAL, 'climate': cls.ENVIRONMENTAL}
        return m.get(v.lower().strip(), cls.GENERIC)

@unique
class Granularity(Enum):
    SECOND = ("second", "s", 1, "Second")
    MINUTE = ("minute", "min", 60, "Minute")
    MINUTE_5 = ("minute_5", "5min", 300, "5 Minutes")
    MINUTE_15 = ("minute_15", "15min", 900, "15 Minutes")
    HOUR = ("hour", "h", 3600, "Hour")
    HOUR_4 = ("hour_4", "4h", 14400, "4 Hours")
    DAY = ("day", "D", 86400, "Day")
    WEEK = ("week", "W", 604800, "Week")
    MONTH = ("month", "ME", 2592000, "Month")
    
    def __init__(self, value: str, pandas_code: str, seconds: int, display_name: str):
        self._value_, self.pandas_code = value, pandas_code
        self.seconds, self.display_name = seconds, display_name
    
    @classmethod
    def from_string(cls, v: str) -> 'Granularity':
        m = {'second': cls.SECOND, 's': cls.SECOND, 'minute': cls.MINUTE, 'min': cls.MINUTE,
             'm': cls.MINUTE, '1m': cls.MINUTE, '5min': cls.MINUTE_5, '15min': cls.MINUTE_15,
             'hour': cls.HOUR, 'h': cls.HOUR, '1h': cls.HOUR, '4h': cls.HOUR_4,
             'day': cls.DAY, 'd': cls.DAY, 'week': cls.WEEK, 'w': cls.WEEK, 'month': cls.MONTH}
        return m.get(v.lower().strip(), cls.MINUTE)
    
    @classmethod
    def from_seconds(cls, s: float) -> 'Granularity':
        for g in sorted(cls, key=lambda x: x.seconds, reverse=True):
            if s >= g.seconds * 0.8: return g
        return cls.SECOND
    
    def __lt__(self, o): return self.seconds < o.seconds
    def __gt__(self, o): return self.seconds > o.seconds

@unique
class VolatilityRegime(Enum):
    """Regime di volatilità per adaptive prediction."""
    LOW = "low"           # Volatilità < 1 std sotto media
    NORMAL = "normal"     # Volatilità nella norma
    HIGH = "high"         # Volatilità > 1 std sopra media
    EXTREME = "extreme"   # Volatilità > 2 std (liquidazioni, crash)

@unique
class ResampleMethod(Enum):
    MEAN = "mean"; LAST = "last"; FIRST = "first"; SUM = "sum"
    OHLC = "ohlc"; MEDIAN = "median"; MIN = "min"; MAX = "max"
    @classmethod
    def from_string(cls, v: str) -> 'ResampleMethod':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.MEAN)

@unique
class GapFillMethod(Enum):
    FFILL = "ffill"; BFILL = "bfill"; INTERPOLATE = "interpolate"
    DROP = "drop"; ZERO = "zero"; MEAN = "mean"
    @classmethod
    def from_string(cls, v: str) -> 'GapFillMethod':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.FFILL)

@unique
class PredictionMode(Enum):
    REGRESSION = "regression"; CLASSIFICATION = "classification"; HYBRID = "hybrid"
    @classmethod
    def from_string(cls, v: str) -> 'PredictionMode':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.HYBRID)

@unique
class TrendClass(Enum):
    DOWN = (0, "DOWN", -1, "↓")
    FLAT = (1, "FLAT", 0, "→")
    UP = (2, "UP", 1, "↑")
    
    def __init__(self, index: int, label: str, direction: int, symbol: str):
        self._value_, self.label = index, label
        self.direction, self.symbol = direction, symbol
    
    @classmethod
    def from_index(cls, i: int) -> 'TrendClass':
        for t in cls:
            if t.value == i: return t
        return cls.FLAT

@unique
class ThresholdMode(Enum):
    FIXED = "fixed"; PERCENTILE = "percentile"; VOLATILITY = "volatility"
    ATR = "atr"; ADAPTIVE = "adaptive"
    @classmethod
    def from_string(cls, v: str) -> 'ThresholdMode':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.FIXED)

@unique
class FusionStrategy(Enum):
    """
    PROFETA v5.0 PRODUCTION usa esclusivamente REGRESSION_DERIVED.
    Le altre strategie sono mantenute per retrocompatibilità.
    """
    REGRESSION_DERIVED = "regression_derived"  # ⭐ DEFAULT - Classificazione dal delta
    WEIGHTED_AVERAGE = "weighted_average"      # Legacy
    @classmethod
    def from_string(cls, v: str) -> 'FusionStrategy':
        m = {s.value: s for s in cls}
        # Tutti gli alias puntano a REGRESSION_DERIVED
        m['derived'] = cls.REGRESSION_DERIVED
        m['production'] = cls.REGRESSION_DERIVED
        m['default'] = cls.REGRESSION_DERIVED
        m['dual_confirmation'] = cls.REGRESSION_DERIVED  # Deprecato
        m['dual'] = cls.REGRESSION_DERIVED
        return m.get(v.lower().strip(), cls.REGRESSION_DERIVED)

@unique
class SignalType(Enum):
    """
    DEPRECATED in v5.2.0 - Mantenuto solo per backward compatibility.
    PROFETA è ora un Pure Forecast tool - non genera segnali di trading.
    """
    STRONG_SELL = (-2, "STRONG_SELL", "🔴🔴")
    SELL = (-1, "SELL", "🔴")
    HOLD = (0, "HOLD", "⚪")
    BUY = (1, "BUY", "🟢")
    STRONG_BUY = (2, "STRONG_BUY", "🟢🟢")
    def __init__(self, value: int, label: str, emoji: str):
        self._value_, self.label, self.emoji = value, label, emoji

@unique
class ExecutionMode(Enum):
    ONCE = "once"; DAEMON = "daemon"
    @classmethod
    def from_string(cls, v: str) -> 'ExecutionMode':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.ONCE)

@unique
class ModelArchitecture(Enum):
    LSTM = "lstm"; BILSTM = "bilstm"; GRU = "gru"; BIGRU = "bigru"
    @classmethod
    def from_string(cls, v: str) -> 'ModelArchitecture':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.LSTM)

@unique
class ScalerType(Enum):
    MINMAX = "minmax"; STANDARD = "standard"; ROBUST = "robust"
    @classmethod
    def from_string(cls, v: str) -> 'ScalerType':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.MINMAX)

@unique
class GPUStrategy(Enum):
    OFF = "off"; SINGLE = "single"; MIRROR = "mirror"; AUTO = "auto"
    @classmethod
    def from_string(cls, v: str) -> 'GPUStrategy':
        return {m.value: m for m in cls}.get(v.lower().strip(), cls.AUTO)

@unique
class LogLevel(Enum):
    DEBUG = logging.DEBUG; INFO = logging.INFO
    WARNING = logging.WARNING; ERROR = logging.ERROR
    @classmethod
    def from_string(cls, v: str) -> 'LogLevel':
        return {m.name.lower(): m for m in cls}.get(v.lower().strip(), cls.INFO)


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    VOLATILITY ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class VolatilityState:
    """Stato corrente della volatilità per adaptive prediction."""
    regime: VolatilityRegime
    realized_vol: float           # Volatilità realizzata (annualizzata)
    vol_zscore: float             # Z-score rispetto alla media storica
    vol_multiplier: float         # Moltiplicatore per le predizioni
    recommended_decay: float      # Decay raccomandato per questo regime
    recommended_threshold: float  # Soglia delta raccomandata

class VolatilityAnalyzer:
    """
    Analizza la volatilità corrente e determina il regime di mercato.
    Usato per adattare dinamicamente decay e soglie delle predizioni.
    """
    DECAY_MAP = {
        VolatilityRegime.LOW: 0.999,
        VolatilityRegime.NORMAL: 0.998,
        VolatilityRegime.HIGH: 0.995,
        VolatilityRegime.EXTREME: 0.990
    }
    THRESHOLD_MAP = {
        VolatilityRegime.LOW: 0.0003,
        VolatilityRegime.NORMAL: 0.0005,
        VolatilityRegime.HIGH: 0.0010,
        VolatilityRegime.EXTREME: 0.0020
    }
    
    def __init__(self, lookback: int = 20, hist_window: int = 50, 
                 min_mult: float = 0.5, max_mult: float = 3.0):
        self.lookback = lookback
        self.hist_window = hist_window
        self.min_mult = min_mult
        self.max_mult = max_mult
        self._vol_history: List[float] = []
    
    def analyze(self, prices: pd.Series) -> VolatilityState:
        """Analizza la serie di prezzi e ritorna lo stato di volatilità."""
        returns = prices.pct_change().dropna()
        
        if len(returns) < self.lookback:
            # Dati insufficienti, usa valori default
            return VolatilityState(
                regime=VolatilityRegime.NORMAL,
                realized_vol=0.02, vol_zscore=0.0, vol_multiplier=1.0,
                recommended_decay=0.998, recommended_threshold=0.0005
            )
        
        # Volatilità realizzata (annualizzata per dati orari)
        realized_vol = float(returns.tail(self.lookback).std() * np.sqrt(24 * 365))
        
        # Aggiorna history
        self._vol_history.append(realized_vol)
        if len(self._vol_history) > self.hist_window * 2:
            self._vol_history = self._vol_history[-self.hist_window * 2:]
        
        # Calcola media e std storica
        if len(self._vol_history) >= self.hist_window:
            hist_data = self._vol_history[-self.hist_window:]
            hist_mean = np.mean(hist_data)
            hist_std = np.std(hist_data)
        else:
            hist_mean = realized_vol
            hist_std = realized_vol * 0.3
        
        # Z-score
        vol_zscore = (realized_vol - hist_mean) / (hist_std + EPSILON)
        
        # Determina regime
        if vol_zscore > 2.0:
            regime = VolatilityRegime.EXTREME
        elif vol_zscore > 1.0:
            regime = VolatilityRegime.HIGH
        elif vol_zscore < -1.0:
            regime = VolatilityRegime.LOW
        else:
            regime = VolatilityRegime.NORMAL
        
        # Multiplier con cap
        raw_mult = realized_vol / (hist_mean + EPSILON)
        vol_multiplier = float(np.clip(raw_mult, self.min_mult, self.max_mult))
        
        return VolatilityState(
            regime=regime,
            realized_vol=realized_vol,
            vol_zscore=float(vol_zscore),
            vol_multiplier=vol_multiplier,
            recommended_decay=self.DECAY_MAP[regime],
            recommended_threshold=self.THRESHOLD_MAP[regime]
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    GPU MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GPUInfo:
    index: int; name: str; memory_total_mb: int; memory_free_mb: int
    compute_capability: Tuple[int, int]; is_available: bool = True
    @property
    def supports_mixed_precision(self) -> bool: return self.compute_capability >= (7, 0)

@dataclass
class GPUConfig:
    enabled: bool = True; strategy: GPUStrategy = GPUStrategy.AUTO
    memory_growth: bool = True; memory_limit_mb: int = 0; mixed_precision: bool = True
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'GPUConfig':
        if not config.has_section('SYSTEM'): return cls()
        s = config['SYSTEM']
        return cls(enabled=s.getboolean('use_gpu', True),
                   strategy=GPUStrategy.from_string(s.get('multi_gpu', 'auto')),
                   memory_growth=s.getboolean('gpu_memory_growth', True),
                   memory_limit_mb=s.getint('gpu_memory_limit', 0),
                   mixed_precision=s.getboolean('mixed_precision', True))

class GPUManager:
    _instance: ClassVar[Optional['GPUManager']] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __new__(cls) -> 'GPUManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self.logger = logging.getLogger(self.__class__.__name__)
        self._config, self._strategy = None, None
        self._using_gpu = self._mixed_precision_enabled = False
        self._initialized = True
    
    def initialize(self, config: GPUConfig) -> bool:
        self._config = config
        if not config.enabled or config.strategy == GPUStrategy.OFF:
            self._strategy = tf.distribute.get_strategy()
            return False
        try:
            gpus = tf.config.list_physical_devices('GPU')
            if not gpus:
                self._strategy = tf.distribute.get_strategy()
                return False
            for gpu in gpus:
                if config.memory_growth:
                    tf.config.experimental.set_memory_growth(gpu, True)
            if config.mixed_precision:
                tf.keras.mixed_precision.set_global_policy('mixed_float16')
                self._mixed_precision_enabled = True
            if len(gpus) == 1 or config.strategy == GPUStrategy.SINGLE:
                self._strategy = tf.distribute.OneDeviceStrategy("/gpu:0")
            elif config.strategy == GPUStrategy.MIRROR or len(gpus) > 1:
                self._strategy = tf.distribute.MirroredStrategy()
            else:
                self._strategy = tf.distribute.get_strategy()
            self._using_gpu = True
            self.logger.info(f"GPU initialized: {len(gpus)} device(s)")
            return True
        except Exception as e:
            self.logger.error(f"GPU init failed: {e}")
            self._strategy = tf.distribute.get_strategy()
            return False
    
    @contextmanager
    def strategy_scope(self):
        if self._strategy:
            with self._strategy.scope(): yield
        else: yield
    
    @property
    def is_gpu_available(self) -> bool: return self._using_gpu
    @property
    def is_mixed_precision(self) -> bool: return self._mixed_precision_enabled
    def clear_memory(self): K.clear_session(); gc.collect()

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    DOMAIN PROFILES
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DomainProfile:
    domain_type: DomainType; subtype: str = "generic"
    auto_detect_ohlcv: bool = True; use_returns: bool = True
    use_volatility: bool = True; use_volume_features: bool = True
    use_order_flow: bool = False; use_temporal_features: bool = True
    use_technical_indicators: bool = False; use_seasonal_decomposition: bool = False
    detrend: bool = False; deseasonalize: bool = False
    seasonal_periods: List[int] = field(default_factory=list)
    default_threshold: float = 0.001
    threshold_mode: ThresholdMode = ThresholdMode.FIXED
    num_classes: int = 3
    typical_granularity: Granularity = Granularity.MINUTE
    typical_sequence_length: int = 60
    
    @classmethod
    def for_financial(cls, subtype: str = "generic") -> 'DomainProfile':
        return cls(DomainType.FINANCIAL, subtype, True, True, True, True,
                   subtype == "crypto", True, True, False, False, False, [],
                   0.001, ThresholdMode.VOLATILITY, 3, Granularity.MINUTE, 60)
    
    @classmethod
    def for_energy(cls) -> 'DomainProfile':
        return cls(DomainType.ENERGY, "electricity", False, True, True, False,
                   False, True, False, True, False, True, [24, 168],
                   0.05, ThresholdMode.PERCENTILE, 3, Granularity.HOUR, 168)
    
    @classmethod
    def for_environmental(cls) -> 'DomainProfile':
        return cls(DomainType.ENVIRONMENTAL, "climate", False, False, False, False,
                   False, True, False, True, True, True, [365],
                   0.1, ThresholdMode.PERCENTILE, 3, Granularity.DAY, 365)
    
    @classmethod
    def for_generic(cls) -> 'DomainProfile':
        return cls(DomainType.GENERIC, "generic", True, True, True, True,
                   False, True, False, False, False, False, [],
                   0.01, ThresholdMode.ADAPTIVE, 3, Granularity.MINUTE, 60)
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'DomainProfile':
        if not config.has_section('DOMAIN'): return cls.for_generic()
        s = config['DOMAIN']
        dt = DomainType.from_string(s.get('type', 'generic'))
        sub = s.get('subtype', 'generic')
        if dt == DomainType.FINANCIAL: p = cls.for_financial(sub)
        elif dt == DomainType.ENERGY: p = cls.for_energy()
        elif dt == DomainType.ENVIRONMENTAL: p = cls.for_environmental()
        else: p = cls.for_generic()
        p.use_returns = s.getboolean('use_returns', p.use_returns)
        p.use_volatility = s.getboolean('use_volatility', p.use_volatility)
        p.use_volume_features = s.getboolean('use_volume_features', p.use_volume_features)
        p.use_order_flow = s.getboolean('use_order_flow', p.use_order_flow)
        p.use_temporal_features = s.getboolean('use_temporal_features', p.use_temporal_features)
        p.use_technical_indicators = s.getboolean('use_technical_indicators', p.use_technical_indicators)
        p.use_seasonal_decomposition = s.getboolean('use_seasonal_decomposition', p.use_seasonal_decomposition)
        p.detrend = s.getboolean('detrend', p.detrend)
        p.deseasonalize = s.getboolean('deseasonalize', p.deseasonalize)
        return p


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    TECHNICAL INDICATORS
# ═══════════════════════════════════════════════════════════════════════════════════════════

class TechnicalIndicators:
    @staticmethod
    def returns(s: pd.Series, p: int = 1) -> pd.Series: return s.pct_change(periods=p)
    
    @staticmethod
    def log_returns(s: pd.Series, p: int = 1) -> pd.Series: return np.log(s / s.shift(p))
    
    @staticmethod
    def volatility(s: pd.Series, w: int = 20) -> pd.Series: return s.pct_change().rolling(w).std()
    
    @staticmethod
    def rsi(s: pd.Series, p: int = RSI_PERIOD) -> pd.Series:
        delta = s.diff()
        gain = delta.where(delta > 0, 0).rolling(p).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(p).mean()
        rs = gain / (loss + EPSILON)
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(s: pd.Series, fast: int = MACD_FAST, slow: int = MACD_SLOW, 
             sig: int = MACD_SIGNAL) -> Tuple[pd.Series, pd.Series, pd.Series]:
        exp_fast, exp_slow = s.ewm(span=fast).mean(), s.ewm(span=slow).mean()
        macd_line = exp_fast - exp_slow
        signal_line = macd_line.ewm(span=sig).mean()
        return macd_line, signal_line, macd_line - signal_line
    
    @staticmethod
    def bollinger(s: pd.Series, p: int = BOLLINGER_PERIOD, 
                  std: float = BOLLINGER_STD) -> Tuple[pd.Series, pd.Series, pd.Series]:
        mid = s.rolling(p).mean()
        std_val = s.rolling(p).std()
        return mid + std_val * std, mid, mid - std_val * std
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, p: int = ATR_PERIOD) -> pd.Series:
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(p).mean()
    
    @staticmethod
    def ema(s: pd.Series, p: int) -> pd.Series: return s.ewm(span=p).mean()
    
    @staticmethod
    def sma(s: pd.Series, p: int) -> pd.Series: return s.rolling(p).mean()

class TemporalFeatures:
    @staticmethod
    def extract(ts: pd.DatetimeIndex) -> pd.DataFrame:
        f = pd.DataFrame(index=ts)
        f['hour'], f['day_of_week'] = ts.hour, ts.dayofweek
        f['day_of_month'], f['month'] = ts.day, ts.month
        f['is_weekend'] = (ts.dayofweek >= 5).astype(int)
        f['hour_sin'] = np.sin(2 * np.pi * ts.hour / 24)
        f['hour_cos'] = np.cos(2 * np.pi * ts.hour / 24)
        f['day_sin'] = np.sin(2 * np.pi * ts.dayofweek / 7)
        f['day_cos'] = np.cos(2 * np.pi * ts.dayofweek / 7)
        return f

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════════════════

class FeatureEngineer:
    def __init__(self, profile: DomainProfile, logger: Optional[logging.Logger] = None):
        self.profile, self.logger = profile, logger or logging.getLogger(self.__class__.__name__)
        self.feature_names: List[str] = []
        self._fitted = False
    
    def fit_transform(self, df: pd.DataFrame, ts_col: str, target_col: str) -> pd.DataFrame:
        self.logger.info(f"Feature Engineering - Domain: {self.profile.domain_type.value}")
        result = df.copy()
        if ts_col in result.columns:
            result[ts_col] = pd.to_datetime(result[ts_col])
            result = result.set_index(ts_col)
        
        ohlcv = self._detect_ohlcv(result)
        features = pd.DataFrame(index=result.index)
        features[target_col] = result[target_col]
        
        # Returns
        if self.profile.use_returns:
            features[f'{target_col}_ret1'] = TechnicalIndicators.returns(result[target_col], 1)
            features[f'{target_col}_ret5'] = TechnicalIndicators.returns(result[target_col], 5)
            features[f'{target_col}_logret'] = TechnicalIndicators.log_returns(result[target_col])
        
        # Volatility
        if self.profile.use_volatility:
            features[f'{target_col}_vol5'] = TechnicalIndicators.volatility(result[target_col], 5)
            features[f'{target_col}_vol20'] = TechnicalIndicators.volatility(result[target_col], 20)
        
        # Technical Indicators
        if self.profile.use_technical_indicators and ohlcv:
            close = result.get(ohlcv.get('close', target_col), result[target_col])
            features['rsi'] = TechnicalIndicators.rsi(close)
            macd, sig, hist = TechnicalIndicators.macd(close)
            features['macd'], features['macd_sig'], features['macd_hist'] = macd, sig, hist
            bb_up, bb_mid, bb_low = TechnicalIndicators.bollinger(close)
            features['bb_width'] = (bb_up - bb_low) / (bb_mid + EPSILON)
            features['bb_pos'] = (close - bb_low) / (bb_up - bb_low + EPSILON)
            features['ema5'], features['ema20'] = TechnicalIndicators.ema(close, 5), TechnicalIndicators.ema(close, 20)
            if all(k in ohlcv for k in ['high', 'low', 'close']):
                features['atr'] = TechnicalIndicators.atr(result[ohlcv['high']], result[ohlcv['low']], close)
        
        # Volume
        if self.profile.use_volume_features and 'volume' in ohlcv:
            vol = result[ohlcv['volume']]
            features['volume'] = vol
            features['vol_ma20'] = vol.rolling(20).mean()
            features['vol_ratio'] = vol / (vol.rolling(20).mean() + EPSILON)
        
        # Order Flow
        if self.profile.use_order_flow:
            of_cols = self._detect_order_flow(result)
            if of_cols.get('taker_buy') and 'volume' in ohlcv:
                tbv, vol = result[of_cols['taker_buy']], result[ohlcv['volume']]
                features['taker_buy_ratio'] = tbv / (vol + EPSILON)
                features['order_imbalance'] = features['taker_buy_ratio'] - 0.5
        
        # Temporal
        if self.profile.use_temporal_features:
            temp = TemporalFeatures.extract(features.index)
            for c in temp.columns: features[f't_{c}'] = temp[c]
        
        # Lags & Rolling
        for lag in [1, 2, 3, 5, 10]:
            features[f'{target_col}_lag{lag}'] = result[target_col].shift(lag)
        for w in [5, 10, 20]:
            features[f'{target_col}_ma{w}'] = result[target_col].rolling(w).mean()
            features[f'{target_col}_std{w}'] = result[target_col].rolling(w).std()
        
        init_len = len(features)
        features = features.dropna()
        self.feature_names = [c for c in features.columns if c != target_col]
        self._fitted = True
        self.logger.info(f"Features: {len(self.feature_names)}, Rows: {init_len} -> {len(features)}")
        return features
    
    def _detect_ohlcv(self, df: pd.DataFrame) -> Dict[str, str]:
        m, cl = {}, {c.lower(): c for c in df.columns}
        for f, ps in [('open', ['open', 'o']), ('high', ['high', 'h']), ('low', ['low', 'l']),
                      ('close', ['close', 'c', 'price']), ('volume', ['volume', 'vol', 'v'])]:
            for p in ps:
                if p in cl: m[f] = cl[p]; break
        return m
    
    def _detect_order_flow(self, df: pd.DataFrame) -> Dict[str, str]:
        m, cl = {}, {c.lower(): c for c in df.columns}
        for p in ['takerbuybavolume', 'taker_buy_volume', 'takerbuyvolume']:
            if p in cl: m['taker_buy'] = cl[p]; break
        return m


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    TREND LABELING
# ═══════════════════════════════════════════════════════════════════════════════════════════

class TrendLabeler:
    """
    Calcola le etichette di trend per la classificazione.
    
    IMPORTANTE: Ora usa i DELTA ASSOLUTI invece dei returns percentuali,
    per allinearsi con il sistema di predizione delta-based.
    
    - DOWN: delta < -threshold
    - FLAT: -threshold <= delta <= threshold  
    - UP: delta > threshold
    """
    def __init__(self, threshold_mode: ThresholdMode = ThresholdMode.FIXED,
                 threshold: float = 0.001, horizon: int = 1, num_classes: int = 3,
                 vol_window: int = 20, logger: Optional[logging.Logger] = None):
        self.threshold_mode, self.fixed_threshold = threshold_mode, threshold
        self.horizon, self.num_classes, self.vol_window = horizon, num_classes, vol_window
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._threshold: Optional[float] = None
        self._use_absolute_delta: bool = True  # Nuovo: usa delta assoluti
    
    def compute_labels(self, series: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Calcola le label di trend basate sui delta assoluti.
        
        delta[t] = price[t + horizon] - price[t]
        
        Questo allinea le label con il target del modello (delta-based).
        """
        # Calcola delta assoluti (non percentuali)
        future_delta = series.diff(self.horizon).shift(-self.horizon)
        
        # Calcola anche i returns per retrocompatibilità nel logging
        future_ret = series.pct_change(self.horizon).shift(-self.horizon)
        
        # Calcola threshold sui delta assoluti
        self._compute_threshold_absolute(future_delta)
        
        labels = pd.Series(index=series.index, dtype='int32')
        labels[future_delta < -self._threshold] = TrendClass.DOWN.value
        labels[future_delta > self._threshold] = TrendClass.UP.value
        labels[(future_delta >= -self._threshold) & (future_delta <= self._threshold)] = TrendClass.FLAT.value
        
        # Log distribuzione
        dist = labels.value_counts().to_dict()
        dist_pct = {k: f"{v/len(labels)*100:.1f}%" for k, v in dist.items()}
        self.logger.info(f"Labels (delta-based): threshold={self._threshold:.2f}$, dist={dist_pct}")
        
        return labels, future_ret
    
    def _compute_threshold_absolute(self, delta: pd.Series) -> None:
        """
        Calcola la soglia per i delta assoluti.
        
        Per crypto/forex con prezzi alti (es. BTC ~100k), usiamo:
        - FIXED: threshold è già in valore assoluto (es. 50 = 50$)
        - PERCENTILE: mediana dei delta assoluti
        - VOLATILITY: std dei delta * fattore
        - ADAPTIVE: media tra volatility e percentile
        """
        valid = delta.dropna()
        
        if self.threshold_mode == ThresholdMode.FIXED:
            # Per delta assoluti, convertiamo la percentuale in valore assoluto
            # Se threshold=0.001 (0.1%) e prezzo medio=100k, allora ~100$
            mean_price = valid.mean() if len(valid) > 0 else 1
            # Se threshold è già grande (>1), usalo direttamente, altrimenti converti
            if self.fixed_threshold < 1:
                # Assume che sia una percentuale, converti usando il delta medio
                self._threshold = abs(valid).median() if len(valid) > 0 else self.fixed_threshold
            else:
                self._threshold = self.fixed_threshold
                
        elif self.threshold_mode == ThresholdMode.PERCENTILE:
            # Usa il 60° percentile dei delta assoluti per bilanciare le classi
            self._threshold = np.percentile(abs(valid), 60)
            
        elif self.threshold_mode == ThresholdMode.VOLATILITY:
            # Usa la deviazione standard dei delta
            rolling_std = valid.rolling(self.vol_window, min_periods=5).std()
            self._threshold = rolling_std.mean() * 0.8  # 0.8 sigma
            
        elif self.threshold_mode == ThresholdMode.ADAPTIVE:
            # Combina volatility e percentile per robustezza
            vol_t = valid.rolling(self.vol_window, min_periods=5).std().mean() * 0.8
            pct_t = np.percentile(abs(valid), 55)
            self._threshold = (vol_t + pct_t) / 2
        else:
            self._threshold = abs(valid).median() if len(valid) > 0 else self.fixed_threshold
        
        # Assicura threshold minimo
        self._threshold = max(self._threshold, EPSILON)
        
        # Log per debug
        self.logger.debug(f"Threshold computed: mode={self.threshold_mode.value}, value={self._threshold:.2f}")
    
    def _compute_threshold(self, ret: pd.Series) -> None:
        """Legacy method per retrocompatibilità - ora chiama _compute_threshold_absolute"""
        # Converti returns in delta approssimati per il calcolo
        valid = ret.dropna()
        if self.threshold_mode == ThresholdMode.FIXED:
            self._threshold = self.fixed_threshold
        elif self.threshold_mode == ThresholdMode.PERCENTILE:
            self._threshold = np.percentile(valid.abs(), 50)
        elif self.threshold_mode == ThresholdMode.VOLATILITY:
            self._threshold = valid.rolling(self.vol_window).std().mean() * 0.5
        elif self.threshold_mode == ThresholdMode.ADAPTIVE:
            vol_t = valid.rolling(self.vol_window).std().mean() * 0.5
            pct_t = np.percentile(valid.abs(), 50)
            self._threshold = (vol_t + pct_t) / 2
        else:
            self._threshold = self.fixed_threshold
        self._threshold = max(self._threshold, EPSILON)
    
    @property
    def threshold(self) -> float: return self._threshold or self.fixed_threshold

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    DATA PREPROCESSING
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class GranularityConfig:
    input_granularity: Optional[Granularity] = None
    model_granularity: Granularity = Granularity.MINUTE
    output_granularity: Granularity = Granularity.HOUR
    resample_method: ResampleMethod = ResampleMethod.OHLC
    detect_gaps: bool = True
    fill_gaps_method: GapFillMethod = GapFillMethod.FFILL
    min_data_points: int = 1000
    max_gap_tolerance: int = 10
    auto_sort: bool = True
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'GranularityConfig':
        if not config.has_section('GRANULARITY'):
            return cls()
        s = config['GRANULARITY']
        inp = s.get('input_granularity', 'auto').lower()
        return cls(
            input_granularity=None if inp == 'auto' else Granularity.from_string(inp),
            model_granularity=Granularity.from_string(s.get('model_granularity', 'minute')),
            output_granularity=Granularity.from_string(s.get('output_granularity', 'hour')),
            resample_method=ResampleMethod.from_string(s.get('resample_method', 'ohlc')),
            detect_gaps=s.getboolean('detect_gaps', True),
            fill_gaps_method=GapFillMethod.from_string(s.get('fill_gaps_method', 'ffill')),
            min_data_points=s.getint('min_data_points', 1000),
            max_gap_tolerance=s.getint('max_gap_tolerance', 10),
            auto_sort=s.getboolean('auto_sort', True))

class GranularityDetector:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def detect(self, ts: pd.Series) -> Tuple[Granularity, Dict]:
        ts_dt = pd.to_datetime(ts)
        diffs = ts_dt.diff().dropna().dt.total_seconds()
        if len(diffs) == 0: raise GranularityError("No timestamps")
        median = diffs.median()
        detected = Granularity.from_seconds(median)
        conf = max(0, 1 - abs(median - detected.seconds) / detected.seconds)
        self.logger.info(f"Detected: {detected.display_name} (conf: {conf:.0%})")
        return detected, {'mean': diffs.mean(), 'median': median, 'confidence': conf}

class DataResampler:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def resample(self, df: pd.DataFrame, ts_col: str, from_g: Granularity,
                 to_g: Granularity, method: ResampleMethod, target: str) -> pd.DataFrame:
        result = df.copy()
        if ts_col in result.columns:
            result[ts_col] = pd.to_datetime(result[ts_col])
            result = result.set_index(ts_col)
        if from_g < to_g:
            result = self._downsample(result, to_g, method)
        elif from_g > to_g:
            result = result.resample(to_g.pandas_code).interpolate('linear').dropna()
        result = result.reset_index().rename(columns={'index': ts_col})
        return result
    
    def _downsample(self, df: pd.DataFrame, to_g: Granularity, method: ResampleMethod) -> pd.DataFrame:
        r = df.resample(to_g.pandas_code)
        ohlc_cols = self._detect_ohlcv(df)
        if method == ResampleMethod.OHLC and ohlc_cols:
            agg = {}
            if 'open' in ohlc_cols: agg[ohlc_cols['open']] = 'first'
            if 'high' in ohlc_cols: agg[ohlc_cols['high']] = 'max'
            if 'low' in ohlc_cols: agg[ohlc_cols['low']] = 'min'
            if 'close' in ohlc_cols: agg[ohlc_cols['close']] = 'last'
            if 'volume' in ohlc_cols: agg[ohlc_cols['volume']] = 'sum'
            for c in df.columns:
                if c not in agg: agg[c] = 'last'
            return r.agg(agg).dropna()
        return getattr(r, method.value)().dropna()
    
    def _detect_ohlcv(self, df: pd.DataFrame) -> Dict[str, str]:
        m, cl = {}, {c.lower(): c for c in df.columns}
        for f, ps in [('open', ['open']), ('high', ['high']), ('low', ['low']),
                      ('close', ['close']), ('volume', ['volume', 'vol'])]:
            for p in ps:
                if p in cl: m[f] = cl[p]; break
        return m

class GapHandler:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def fill_gaps(self, df: pd.DataFrame, ts_col: str, method: GapFillMethod, 
                  gran: Granularity) -> pd.DataFrame:
        result = df.copy()
        if ts_col in result.columns:
            result[ts_col] = pd.to_datetime(result[ts_col])
            result = result.set_index(ts_col)
        full_idx = pd.date_range(result.index.min(), result.index.max(), freq=gran.pandas_code)
        result = result.reindex(full_idx)
        gaps = result.isna().any(axis=1).sum()
        if method == GapFillMethod.FFILL: result = result.ffill()
        elif method == GapFillMethod.BFILL: result = result.bfill()
        elif method == GapFillMethod.INTERPOLATE: result = result.interpolate('linear')
        elif method == GapFillMethod.DROP: result = result.dropna()
        elif method == GapFillMethod.ZERO: result = result.fillna(0)
        elif method == GapFillMethod.MEAN: result = result.fillna(result.mean())
        result = result.reset_index().rename(columns={'index': ts_col})
        if gaps > 0: self.logger.info(f"Filled {gaps} gaps with {method.value}")
        return result

class DataPreprocessor:
    def __init__(self, gran_config: GranularityConfig, domain_profile: DomainProfile,
                 logger: Optional[logging.Logger] = None):
        self.gran_config, self.domain_profile = gran_config, domain_profile
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.detector = GranularityDetector(logger)
        self.resampler = DataResampler(logger)
        self.gap_handler = GapHandler(logger)
        self.feature_engineer = FeatureEngineer(domain_profile, logger)
        self._detected_gran: Optional[Granularity] = None
    
    def process(self, df: pd.DataFrame, ts_col: str, target_col: str) -> pd.DataFrame:
        self.logger.info("=" * 70)
        self.logger.info("DATA PREPROCESSOR")
        result = df.copy()
        # Auto-sort
        if self.gran_config.auto_sort:
            result = self._auto_sort(result, ts_col)
        # Detect granularity
        if self.gran_config.input_granularity is None:
            self._detected_gran, _ = self.detector.detect(result[ts_col])
        else:
            self._detected_gran = self.gran_config.input_granularity
        # Fill gaps
        if self.gran_config.detect_gaps:
            result = self.gap_handler.fill_gaps(result, ts_col, self.gran_config.fill_gaps_method, self._detected_gran)
        # Resample
        if self._detected_gran != self.gran_config.model_granularity:
            result = self.resampler.resample(result, ts_col, self._detected_gran,
                                             self.gran_config.model_granularity,
                                             self.gran_config.resample_method, target_col)
        # Feature engineering
        result = self.feature_engineer.fit_transform(result, ts_col, target_col)
        if len(result) < self.gran_config.min_data_points:
            raise DataError(f"Insufficient data: {len(result)} < {self.gran_config.min_data_points}")
        self.logger.info(f"Preprocessing complete: {len(df)} -> {len(result)} records")
        return result
    
    def _auto_sort(self, df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
        ts = pd.to_datetime(df[ts_col], errors='coerce')
        diffs = ts.diff().dropna()
        desc_ratio = (diffs < pd.Timedelta(0)).mean()
        if desc_ratio > 0.9:
            self.logger.warning("Data in REVERSE order - sorting chronologically")
            df = df.sort_values(ts_col, ascending=True).reset_index(drop=True)
        elif desc_ratio > 0.1:
            self.logger.warning("Data has MIXED order - sorting")
            df = df.sort_values(ts_col, ascending=True).reset_index(drop=True)
        return df
    
    @property
    def feature_names(self) -> List[str]: return self.feature_engineer.feature_names


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    SEQUENCE PREPARATION
# ═══════════════════════════════════════════════════════════════════════════════════════════

class SequencePreparator:
    """
    PROFETA v5.5.0 - Sequence Preparator con Scaling Canonico
    
    Metodi canonici per scaling/unscaling:
    - scale_delta(delta) → delta_scaled
    - unscale_delta(delta_scaled) → delta
    - scale_price(price) → price_scaled
    - get_scale_factor() → float
    - get_center() → float
    
    Supporta: MinMaxScaler, StandardScaler, RobustScaler
    """
    
    def __init__(self, seq_len: int, feature_cols: List[str], target_col: str,
                 label_col: Optional[str] = None, scaler_type: ScalerType = ScalerType.MINMAX,
                 logger: Optional[logging.Logger] = None):
        self.seq_len, self.feature_cols, self.target_col = seq_len, feature_cols, target_col
        self.label_col, self.scaler_type = label_col, scaler_type
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.feature_scaler: Optional[Any] = None
        self.target_scaler: Optional[Any] = None
        self._fitted = False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CANONICAL SCALING METHODS (v5.5.0)
    # Single source of truth per lo scaling del target
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_scale_factor(self) -> float:
        """
        Restituisce il fattore di scala del target scaler.
        
        Tutti gli scaler sklearn hanno `scale_` dopo fit:
        - MinMaxScaler: scale_ = data_max - data_min (per feature_range (0,1))
        - StandardScaler: scale_ = std
        - RobustScaler: scale_ = IQR
        
        Returns:
            Fattore di scala (sempre > 0)
        
        Raises:
            StateError: Se lo scaler non è stato fittato
        """
        if not self._fitted or self.target_scaler is None:
            raise StateError("SequencePreparator not fitted")
        
        if hasattr(self.target_scaler, 'scale_') and self.target_scaler.scale_ is not None:
            return float(self.target_scaler.scale_[0])
        
        # Fallback per scaler custom (non dovrebbe mai accadere con sklearn)
        raise StateError(f"Unknown scaler type: {type(self.target_scaler)}")
    
    def get_center(self) -> float:
        """
        Restituisce il centro (offset) del target scaler.
        
        - MinMaxScaler: data_min_
        - StandardScaler: mean_
        - RobustScaler: center_
        
        Returns:
            Centro dello scaler
        """
        if not self._fitted or self.target_scaler is None:
            raise StateError("SequencePreparator not fitted")
        
        # StandardScaler
        if hasattr(self.target_scaler, 'mean_') and self.target_scaler.mean_ is not None:
            return float(self.target_scaler.mean_[0])
        
        # RobustScaler
        if hasattr(self.target_scaler, 'center_') and self.target_scaler.center_ is not None:
            return float(self.target_scaler.center_[0])
        
        # MinMaxScaler
        if hasattr(self.target_scaler, 'data_min_') and self.target_scaler.data_min_ is not None:
            return float(self.target_scaler.data_min_[0])
        
        raise StateError(f"Cannot determine center for scaler: {type(self.target_scaler)}")
    
    def scale_delta(self, delta: float) -> float:
        """
        Scala un delta (differenza di prezzo) usando il fattore di scala.
        
        delta_scaled = delta / scale_factor
        
        Args:
            delta: Differenza di prezzo in unità originali
            
        Returns:
            Delta scalato
        """
        return delta / self.get_scale_factor()
    
    def unscale_delta(self, delta_scaled: float) -> float:
        """
        Converte un delta scalato in unità originali.
        
        delta = delta_scaled * scale_factor
        
        Args:
            delta_scaled: Delta in unità scalate
            
        Returns:
            Delta in unità originali
        """
        return delta_scaled * self.get_scale_factor()
    
    def scale_price(self, price: float) -> float:
        """
        Scala un prezzo assoluto usando lo scaler.
        
        price_scaled = (price - center) / scale_factor
        
        Args:
            price: Prezzo in unità originali
            
        Returns:
            Prezzo scalato
        """
        return (price - self.get_center()) / self.get_scale_factor()
    
    def unscale_price(self, price_scaled: float) -> float:
        """
        Converte un prezzo scalato in unità originali.
        
        price = price_scaled * scale_factor + center
        
        Args:
            price_scaled: Prezzo in unità scalate
            
        Returns:
            Prezzo in unità originali
        """
        return price_scaled * self.get_scale_factor() + self.get_center()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STANDARD METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def fit(self, df: pd.DataFrame) -> 'SequencePreparator':
        if self.scaler_type == ScalerType.STANDARD:
            self.feature_scaler, self.target_scaler = StandardScaler(), StandardScaler()
        elif self.scaler_type == ScalerType.ROBUST:
            self.feature_scaler, self.target_scaler = RobustScaler(), RobustScaler()
        else:
            self.feature_scaler = MinMaxScaler((0, 1))
            self.target_scaler = MinMaxScaler((0, 1))
        self.feature_scaler.fit(df[self.feature_cols].values)
        self.target_scaler.fit(df[self.target_col].values.reshape(-1, 1))
        self._fitted = True
        return self
    
    def transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """
        Trasforma i dati in sequenze per LSTM.
        
        IMPORTANTE: Il target è ora il DELTA (cambiamento) invece del prezzo assoluto.
        Questo permette al modello di imparare i pattern di cambiamento invece di predire
        semplicemente la media del prezzo.
        
        target_delta[t] = price[t+seq_len] - price[t+seq_len-1]
        
        Durante l'inferenza: predicted_price = last_known_price + predicted_delta
        """
        if not self._fitted: raise StateError("Not fitted")
        features = self.feature_scaler.transform(df[self.feature_cols].values)
        
        # Prezzo originale (non scalato) per calcolare i delta
        prices = df[self.target_col].values
        
        X, y_reg = [], []
        
        # Salva gli ultimi prezzi di ogni sequenza per ricostruire il prezzo in inferenza
        self._last_prices = []
        
        for i in range(len(features) - self.seq_len):
            X.append(features[i:i + self.seq_len])
            
            # Target è il DELTA scalato
            last_price = prices[i + self.seq_len - 1]
            next_price = prices[i + self.seq_len]
            delta = next_price - last_price
            
            # Scala il delta usando il metodo canonico
            delta_scaled = self.scale_delta(delta)
            
            y_reg.append(delta_scaled)
            self._last_prices.append(last_price)
        
        return np.array(X), np.array(y_reg)
    
    def inverse_transform_target(self, delta_scaled: np.ndarray, last_prices: np.ndarray = None) -> np.ndarray:
        """
        Converte i delta scalati in prezzi assoluti.
        
        predicted_price = last_price + unscale_delta(delta_scaled)
        
        Args:
            delta_scaled: Array di delta predetti (scalati)
            last_prices: Array degli ultimi prezzi noti (opzionale, usa quelli salvati)
        """
        # Unscale i delta usando il metodo canonico
        delta_scaled = np.asarray(delta_scaled).flatten()
        delta_unscaled = np.array([self.unscale_delta(d) for d in delta_scaled])
        
        # Se non vengono passati last_prices, usa quelli salvati durante transform
        if last_prices is None:
            if hasattr(self, '_last_prices') and len(self._last_prices) == len(delta_scaled):
                last_prices = np.array(self._last_prices)
            else:
                # Fallback: usa il centro dello scaler (non 0!)
                self.logger.warning("No last_prices available, using scaler center as base")
                last_prices = np.full(len(delta_scaled), self.get_center())
        
        return last_prices + delta_unscaled
    
    def inverse_transform_target_legacy(self, vals: np.ndarray) -> np.ndarray:
        """Vecchio metodo per compatibilità - converte valori scalati in originali"""
        return self.target_scaler.inverse_transform(vals.reshape(-1, 1)).flatten()
    
    def save(self, path): 
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({'seq_len': self.seq_len, 'feature_cols': self.feature_cols,
                        'target_col': self.target_col, 'label_col': self.label_col,
                        'scaler_type': self.scaler_type.value, 'feature_scaler': self.feature_scaler,
                        'target_scaler': self.target_scaler, 'fitted': self._fitted}, f)
    
    @classmethod
    def load(cls, path, logger=None) -> 'SequencePreparator':
        with open(path, 'rb') as f: d = pickle.load(f)
        p = cls(d['seq_len'], d['feature_cols'], d['target_col'], d.get('label_col'),
                ScalerType.from_string(d.get('scaler_type', 'minmax')), logger)
        p.feature_scaler, p.target_scaler = d['feature_scaler'], d['target_scaler']
        p._fitted = d.get('fitted', True)
        return p

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MULTI-HEAD MODEL
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelConfig:
    model_id: int; sequence_length: int; num_features: int
    lstm_units: int = 64; dropout_rate: float = 0.2
    use_bidirectional: bool = True; num_lstm_layers: int = 3
    architecture: ModelArchitecture = ModelArchitecture.LSTM
    l2_reg: float = 0.0001; use_attention: bool = False
    # num_classes: REMOVED in v5.3.0 - classification head rimossa
    
    @classmethod
    def from_config_section(cls, section, model_id: int, num_features: int, num_classes: int = 3):
        """num_classes è ignorato in v5.3.0 - mantenuto per retrocompatibilità signature"""
        arch = 'bilstm' if section.getboolean('use_bidirectional', True) else 'lstm'
        return cls(model_id, section.getint('sequence_length', 60), num_features,
                   section.getint('lstm_units', 64), section.getfloat('dropout_rate', 0.2),
                   section.getboolean('use_bidirectional', True), section.getint('num_lstm_layers', 3),
                   ModelArchitecture.from_string(arch), section.getfloat('l2_regularization', 0.0001),
                   section.getboolean('use_attention', False))

class RegressionModelBuilder:
    """
    PROFETA v5.3.0 - Pure Regression Model Builder
    
    Costruisce un modello LSTM/BiLSTM con solo output di regressione.
    La classification head è stata rimossa - il trend è derivato dal delta.
    """
    def __init__(self, config: ModelConfig, logger: Optional[logging.Logger] = None):
        self.config, self.logger = config, logger or logging.getLogger(self.__class__.__name__)
    
    def build(self) -> Model:
        self.logger.info(f"Building regression model {self.config.model_id}: {self.config.architecture.value}")
        inputs = Input(shape=(self.config.sequence_length, self.config.num_features), name='input')
        x = self._build_backbone(inputs)
        reg_out = self._build_regression_head(x)
        return Model(inputs=inputs, outputs=reg_out, name=f'profeta_reg_{self.config.model_id}')
    
    def _build_backbone(self, inputs):
        x, reg = inputs, l2(self.config.l2_reg) if self.config.l2_reg > 0 else None
        for i in range(self.config.num_lstm_layers):
            ret_seq = (i < self.config.num_lstm_layers - 1) or self.config.use_attention
            layer = LSTM(self.config.lstm_units, return_sequences=ret_seq,
                        dropout=self.config.dropout_rate if i > 0 else 0,
                        kernel_regularizer=reg, name=f'lstm_{i}')
            x = Bidirectional(layer, name=f'bi_{i}')(x) if self.config.use_bidirectional else layer(x)
            if i < self.config.num_lstm_layers - 1:
                x = BatchNormalization(name=f'bn_{i}')(x)
        if self.config.use_attention:
            att = MultiHeadAttention(num_heads=4, key_dim=self.config.lstm_units // 4, name='attention')
            x = att(x, x)
            x = GlobalAveragePooling1D(name='pool')(x)
        return x
    
    def _build_regression_head(self, x):
        x = Dense(64, activation='relu', name='reg_d1')(x)
        x = Dropout(self.config.dropout_rate, name='reg_drop')(x)
        return Dense(1, activation='linear', dtype='float32', name='regression_output')(x)

# Alias per retrocompatibilità
MultiHeadModelBuilder = RegressionModelBuilder

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    TRAINING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TrainingConfig:
    """
    PROFETA v5.6.0 - Training Configuration
    
    Supporta due modalità di split:
    
    1. LEGACY (use_nested_split=False):
       |---- TRAIN ----|---- VAL ----|
       train_test_split   validation_split
       
    2. NESTED CONFORMAL (use_nested_split=True):
       |---- TRAIN ----|---- CALIB ----|---- TEST ----|
       train_ratio        calib_ratio      test_ratio
       
       - Scaler fittato SOLO su TRAIN (no data leakage)
       - Model trainato SOLO su TRAIN  
       - Conformal calibrato SOLO su CALIB (out-of-sample)
       - Metriche calcolate SOLO su TEST (truly held-out)
       
       Garanzia: "Coverage verificata out-of-sample su dati mai visti"
    """
    num_epochs: int = 100; batch_size: int = 32; validation_split: float = 0.2
    early_stopping_patience: int = 15; learning_rate: float = 0.001
    reduce_lr_patience: int = 7; reduce_lr_factor: float = 0.5
    train_test_split: float = 0.8; fine_tuning: bool = False
    
    # v5.6.0 - Nested Conformal Prediction Split
    use_nested_split: bool = True   # True = tripla partizione (raccomandato)
    train_ratio: float = 0.60       # 60% per training scaler + model
    calib_ratio: float = 0.20       # 20% per conformal calibration
    test_ratio: float = 0.20        # 20% per metrics + coverage verification
    
    # DEPRECATED in v5.3.0 - mantenuti per retrocompatibilità config file
    use_class_weights: bool = False  # Ignorato
    reg_loss_weight: float = 1.0     # Ignorato (solo regressione)
    cls_loss_weight: float = 0.0     # Ignorato
    
    def __post_init__(self):
        """Valida i ratio di split"""
        if self.use_nested_split:
            total = self.train_ratio + self.calib_ratio + self.test_ratio
            if not (0.99 <= total <= 1.01):
                raise ValidationError(f"Split ratios must sum to 1.0, got {total:.2f}")
            if self.train_ratio < 0.4:
                raise ValidationError(f"train_ratio must be >= 0.4, got {self.train_ratio}")
            if self.calib_ratio < 0.1:
                raise ValidationError(f"calib_ratio must be >= 0.1, got {self.calib_ratio}")
            if self.test_ratio < 0.1:
                raise ValidationError(f"test_ratio must be >= 0.1, got {self.test_ratio}")
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'TrainingConfig':
        if not config.has_section('TRAINING'): return cls()
        s = config['TRAINING']
        return cls(
            num_epochs=s.getint('num_epochs', 100),
            batch_size=s.getint('batch_size', 32),
            validation_split=s.getfloat('validation_split', 0.2),
            early_stopping_patience=s.getint('early_stopping_patience', 15),
            learning_rate=s.getfloat('learning_rate', 0.001),
            reduce_lr_patience=s.getint('reduce_lr_patience', 7),
            reduce_lr_factor=s.getfloat('reduce_lr_factor', 0.5),
            train_test_split=s.getfloat('train_test_split', 0.8),
            fine_tuning=s.getboolean('fine_tuning', False),
            # v5.6.0 - Nested split parameters
            use_nested_split=s.getboolean('use_nested_split', True),
            train_ratio=s.getfloat('train_ratio', 0.60),
            calib_ratio=s.getfloat('calib_ratio', 0.20),
            test_ratio=s.getfloat('test_ratio', 0.20),
            # Legacy - ignorati
            use_class_weights=False,
            reg_loss_weight=1.0,
            cls_loss_weight=0.0
        )

@dataclass
class ClassificationConfig:
    """
    DEPRECATED in v5.3.0 - Mantenuto solo per retrocompatibilità file config.
    La classification head è stata rimossa. Il trend è derivato dalla regressione.
    """
    enabled: bool = False  # Sempre False in v5.3+
    num_classes: int = 3   # Ignorato
    threshold_mode: ThresholdMode = ThresholdMode.VOLATILITY
    threshold: float = 0.001
    prediction_horizon: int = 1
    vol_window: int = 20
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'ClassificationConfig':
        # Parsa per retrocompatibilità ma enabled è sempre False
        if not config.has_section('CLASSIFICATION'): return cls()
        s = config['CLASSIFICATION']
        return cls(enabled=False,  # Sempre False in v5.3+
                   num_classes=s.getint('num_classes', 3),
                   threshold_mode=ThresholdMode.from_string(s.get('threshold_mode', 'volatility')),
                   threshold=s.getfloat('threshold', 0.001),
                   prediction_horizon=s.getint('prediction_horizon', 1),
                   vol_window=s.getint('vol_window', 20))

@dataclass
class FusionConfig:
    """
    PROFETA v5.2.0 - Pure Forecast Configuration
    
    Configurazione per il motore di fusione.
    Non genera più segnali di trading (solo forecast).
    """
    strategy: FusionStrategy = FusionStrategy.REGRESSION_DERIVED
    delta_threshold_pct: float = 0.0005  # Soglia UP/DOWN come % del prezzo (0.05%)
    min_confidence: float = 0.35         # Confidence minima per trend non-FLAT
    # Legacy - mantenuti per retrocompatibilità file config
    signal_threshold: float = 0.55       # DEPRECATED - non usato
    generate_signals: bool = False       # DEPRECATED - sempre False in v5.2+
    reg_weight: float = 1.0              # DEPRECATED - non usato
    cls_weight: float = 0.0              # DEPRECATED - non usato
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'FusionConfig':
        if not config.has_section('FUSION'): return cls()
        s = config['FUSION']
        return cls(
            strategy=FusionStrategy.from_string(s.get('strategy', 'regression_derived')),
            delta_threshold_pct=s.getfloat('delta_threshold_pct', 0.0005),
            min_confidence=s.getfloat('min_confidence', 0.35),
            # Legacy params - ignorati ma parsati per retrocompatibilità
            signal_threshold=s.getfloat('signal_threshold', 0.55),
            generate_signals=False,  # Sempre False in v5.2+
            reg_weight=s.getfloat('regression_weight', 1.0),
            cls_weight=s.getfloat('classification_weight', 0.0)
        )

@dataclass
class PredictionConfig:
    num_future_steps: int = 24; test_data_pct: float = 0.1
    timestamp_column: str = "timestamp"; target_column: str = "close"
    generate_graph: bool = True; output_dir: str = "./output"
    output_predictions_path: Optional[str] = None  # Path specifico per CSV output
    future_decay: float = 0.998  # Decay per step futuro (0.998^72 ≈ 0.87, mantiene 87% della predizione)
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'PredictionConfig':
        if not config.has_section('PREDICTION'): return cls()
        s = config['PREDICTION']
        return cls(s.getint('num_future_steps', 24), s.getfloat('test_data_percentage', 0.1),
                   s.get('timestamp_column', 'timestamp'), s.get('target_column', 'close'),
                   s.getboolean('graph', True), s.get('output_dir', './output'),
                   s.get('output_predictions_path', None),
                   s.getfloat('future_decay', 0.998))


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    CALLBACKS & METRICS
# ═══════════════════════════════════════════════════════════════════════════════════════════

class TQDMProgressCallback(Callback):
    def __init__(self, total_epochs: int, desc: str = "Training", model_id: int = 0):
        super().__init__()
        self.total_epochs, self.desc, self.model_id = total_epochs, desc, model_id
        self.pbar = None
    
    def on_train_begin(self, logs=None):
        self.pbar = tqdm(total=self.total_epochs, desc=f"{self.desc} [{self.model_id}]", leave=False, ncols=100)
    
    def on_epoch_end(self, epoch, logs=None):
        if self.pbar:
            self.pbar.update(1)
            if logs:
                pf = {}
                if 'loss' in logs: pf['loss'] = f"{logs['loss']:.4f}"
                if 'val_loss' in logs: pf['v_loss'] = f"{logs['val_loss']:.4f}"
                if 'classification_output_accuracy' in logs: pf['acc'] = f"{logs['classification_output_accuracy']:.1%}"
                self.pbar.set_postfix(pf)
    
    def on_train_end(self, logs=None):
        if self.pbar: self.pbar.close()

@dataclass
class RegressionMetrics:
    rmse: float; mae: float; mape: float; r2: float; mean_delta: float; std_delta: float
    def to_dict(self) -> Dict: return asdict(self)

@dataclass
class DirectionMetrics:
    """Metriche basate sulla direzione del movimento invece dell'accuracy classica."""
    direction_accuracy: float    # % volte che sign(delta_pred) == sign(delta_real)
    up_precision: float          # Quando predice UP, quante volte è UP?
    down_precision: float        # Quando predice DOWN, quante volte è DOWN?
    profitable_signals: float    # % segnali non-FLAT che sono corretti
    confusion: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict:
        return {'direction_accuracy': self.direction_accuracy, 
                'up_precision': self.up_precision,
                'down_precision': self.down_precision,
                'profitable_signals': self.profitable_signals}

# Alias per retrocompatibilità
ClassificationMetrics = DirectionMetrics

@dataclass
class HybridMetrics:
    regression: RegressionMetrics; classification: ClassificationMetrics
    def to_dict(self) -> Dict:
        return {'regression': self.regression.to_dict(), 'classification': self.classification.to_dict()}

class MetricsCalculator:
    @staticmethod
    def calc_regression(y_true: np.ndarray, y_pred: np.ndarray) -> RegressionMetrics:
        y_t, y_p = np.asarray(y_true).flatten(), np.asarray(y_pred).flatten()
        n = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:n], y_p[:n]
        mask = np.isfinite(y_t) & np.isfinite(y_p)
        y_t, y_p = y_t[mask], y_p[mask]
        delta = y_t - y_p
        return RegressionMetrics(
            float(np.sqrt(mean_squared_error(y_t, y_p))),
            float(mean_absolute_error(y_t, y_p)),
            float(np.mean(np.abs(delta) / np.maximum(np.abs(y_t), EPSILON))),
            float(r2_score(y_t, y_p)), float(np.mean(delta)), float(np.std(delta)))
    
    @staticmethod
    def calc_direction_from_regression(y_dir_true: np.ndarray, y_dir_pred: np.ndarray) -> DirectionMetrics:
        """
        PROFETA v5.3.0 - Calcola direction metrics da previsioni di regressione.
        
        Usa np.sign() sui delta per determinare la direzione:
        - -1 = DOWN
        -  0 = FLAT
        - +1 = UP
        
        Mappatura interna per confusion matrix: DOWN=0, FLAT=1, UP=2
        """
        y_t = np.asarray(y_dir_true).flatten()
        y_p = np.asarray(y_dir_pred).flatten()
        n = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:n], y_p[:n]
        
        # Mappa da sign (-1, 0, 1) a classe (0, 1, 2)
        y_t_cls = (y_t + 1).astype(int)  # -1→0, 0→1, 1→2
        y_p_cls = (y_p + 1).astype(int)
        
        # Direction Accuracy (su movimenti reali, escluso FLAT)
        non_flat_mask = y_t_cls != 1
        if non_flat_mask.sum() > 0:
            direction_accuracy = float((y_t_cls[non_flat_mask] == y_p_cls[non_flat_mask]).mean())
        else:
            direction_accuracy = 0.0
        
        # UP Precision
        up_pred_mask = y_p_cls == 2
        up_precision = float((y_t_cls[up_pred_mask] == 2).mean()) if up_pred_mask.sum() > 0 else 0.0
        
        # DOWN Precision
        down_pred_mask = y_p_cls == 0
        down_precision = float((y_t_cls[down_pred_mask] == 0).mean()) if down_pred_mask.sum() > 0 else 0.0
        
        # Profitable Signals
        actionable_mask = y_p_cls != 1
        profitable_signals = float((y_t_cls[actionable_mask] == y_p_cls[actionable_mask]).mean()) if actionable_mask.sum() > 0 else 0.0
        
        return DirectionMetrics(
            direction_accuracy=direction_accuracy,
            up_precision=up_precision,
            down_precision=down_precision,
            profitable_signals=profitable_signals,
            confusion=confusion_matrix(y_t_cls, y_p_cls, labels=[0, 1, 2])
        )
    
    @staticmethod
    def calc_classification(y_true: np.ndarray, y_pred: np.ndarray, n_cls: int = 3) -> DirectionMetrics:
        """
        DEPRECATED in v5.3.0 - Usa calc_direction_from_regression invece.
        Mantenuto per retrocompatibilità.
        """
        y_t, y_p = np.asarray(y_true).flatten(), np.asarray(y_pred).flatten()
        if y_p.ndim > 1: y_p = y_p.argmax(axis=-1)
        n = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:n], y_p[:n]
        
        non_flat_mask = y_t != 1
        direction_accuracy = float((y_t[non_flat_mask] == y_p[non_flat_mask]).mean()) if non_flat_mask.sum() > 0 else 0.0
        
        up_pred_mask = y_p == 2
        up_precision = float((y_t[up_pred_mask] == 2).mean()) if up_pred_mask.sum() > 0 else 0.0
        
        down_pred_mask = y_p == 0
        down_precision = float((y_t[down_pred_mask] == 0).mean()) if down_pred_mask.sum() > 0 else 0.0
        
        actionable_mask = y_p != 1
        profitable_signals = float((y_t[actionable_mask] == y_p[actionable_mask]).mean()) if actionable_mask.sum() > 0 else 0.0
        
        return DirectionMetrics(
            direction_accuracy=direction_accuracy,
            up_precision=up_precision,
            down_precision=down_precision,
            profitable_signals=profitable_signals,
            confusion=confusion_matrix(y_t, y_p, labels=list(range(n_cls)))
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                           ENTERPRISE FEATURES (v5.5.0)
#                    Horizon-Aware Conformal Prediction + Walk-Forward + Drift Detection
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PredictionInterval:
    """
    Intervallo di previsione calibrato per un orizzonte specifico.
    
    v5.5.0: Include horizon e calibration_n per tracciabilità completa.
    v5.7.0: Supporta intervalli asimmetrici (asymmetric=True).
    """
    point: float           # Previsione puntuale
    lower: float           # Limite inferiore
    upper: float           # Limite superiore
    coverage: float        # Livello di copertura nominale (es. 0.90)
    horizon: int = 1       # Orizzonte di previsione (h1, h2, ..., hn)
    calibration_n: int = 0 # Numero di campioni usati per calibrazione
    asymmetric: bool = False  # v5.7.0: True se calibrato asimmetricamente
    
    @property
    def width(self) -> float:
        """Larghezza dell'intervallo"""
        return self.upper - self.lower
    
    @property
    def half_width(self) -> float:
        """Semi-larghezza media"""
        return self.width / 2
    
    @property
    def lower_width(self) -> float:
        """Distanza dal punto al limite inferiore"""
        return self.point - self.lower
    
    @property
    def upper_width(self) -> float:
        """Distanza dal punto al limite superiore"""
        return self.upper - self.point
    
    @property
    def asymmetry_ratio(self) -> float:
        """Rapporto di asimmetria: >1 = skew positivo, <1 = skew negativo"""
        if self.lower_width == 0:
            return float('inf')
        return self.upper_width / self.lower_width
    
    def to_dict(self) -> Dict:
        result = {
            'point': round(self.point, 2),
            'lower': round(self.lower, 2),
            'upper': round(self.upper, 2),
            'coverage': self.coverage,
            'width': round(self.width, 2),
            'horizon': self.horizon,
            'calibration_n': self.calibration_n
        }
        if self.asymmetric:
            result['asymmetric'] = True
            result['lower_width'] = round(self.lower_width, 2)
            result['upper_width'] = round(self.upper_width, 2)
            result['asymmetry_ratio'] = round(self.asymmetry_ratio, 3)
        return result
    
    def contains(self, actual: float) -> bool:
        """Verifica se il valore reale cade nell'intervallo"""
        return self.lower <= actual <= self.upper


@dataclass
class HorizonCalibrationStats:
    """
    Statistiche di calibrazione per un singolo orizzonte.
    
    v5.5.0: Statistiche base
    v5.7.0: Aggiunge metriche asimmetria (skewness, bias)
    """
    horizon: int
    n_samples: int
    score_mean: float       # Media dei residui assoluti |y - ŷ|
    score_std: float
    score_median: float
    score_min: float
    score_max: float
    score_q25: float
    score_q75: float
    quantiles: Dict[float, float]  # Simmetrici: {0.50: X, 0.90: Y, 0.95: Z}
    empirical_coverage: Optional[Dict[float, float]] = None
    
    # v5.7.0 - Statistiche asimmetriche
    error_mean: float = 0.0         # Media di (y - ŷ), bias
    error_skewness: float = 0.0     # Skewness degli errori
    quantiles_lower: Optional[Dict[float, float]] = None  # Quantili per lower bound
    quantiles_upper: Optional[Dict[float, float]] = None  # Quantili per upper bound
    
    def to_dict(self) -> Dict:
        result = {
            'horizon': self.horizon,
            'n_samples': self.n_samples,
            'score_stats': {
                'mean': round(self.score_mean, 4),
                'std': round(self.score_std, 4),
                'median': round(self.score_median, 4),
                'iqr': round(self.score_q75 - self.score_q25, 4)
            },
            'quantiles_symmetric': {f'{k:.0%}': round(v, 2) for k, v in self.quantiles.items()},
            'bias': round(self.error_mean, 4),
            'skewness': round(self.error_skewness, 4)
        }
        if self.quantiles_lower and self.quantiles_upper:
            result['quantiles_asymmetric'] = {
                f'{k:.0%}': {
                    'lower': round(self.quantiles_lower.get(k, 0), 2),
                    'upper': round(self.quantiles_upper.get(k, 0), 2)
                } for k in self.quantiles.keys()
            }
        if self.empirical_coverage:
            result['empirical_coverage'] = {f'{k:.0%}': f'{v:.1%}' for k, v in self.empirical_coverage.items()}
        return result


class HorizonAwareConformalPredictor:
    """
    ╔══════════════════════════════════════════════════════════════════════════════════════╗
    ║     PROFETA v5.7.0 - HORIZON-AWARE CONFORMAL PREDICTION                             ║
    ╠══════════════════════════════════════════════════════════════════════════════════════╣
    ║  Implementa Split Conformal Prediction con calibrazione per orizzonte.              ║
    ║                                                                                      ║
    ║  TEORIA (Symmetric - default):                                                       ║
    ║  Per ogni orizzonte h: q_h(α) = Quantile(|y_h - ŷ_h|, ⌈(n+1)(1-α)⌉/n)              ║
    ║  Intervallo: Ĉ_h(x) = [ŷ_h - q_h(α), ŷ_h + q_h(α)]                                 ║
    ║                                                                                      ║
    ║  TEORIA (Asymmetric - v5.7.0):                                                       ║
    ║  Per ogni orizzonte h:                                                               ║
    ║    q_l = Quantile(y_h - ŷ_h, (1-α)/2)     # Lower quantile (tipicamente negativo)   ║
    ║    q_u = Quantile(y_h - ŷ_h, (1+α)/2)     # Upper quantile (tipicamente positivo)   ║
    ║  Intervallo: Ĉ_h(x) = [ŷ_h + q_l, ŷ_h + q_u]                                        ║
    ║                                                                                      ║
    ║  GARANZIA: P(Y_h ∈ Ĉ_h) ≥ 1 - α per ogni h, sotto exchangeability                  ║
    ║                                                                                      ║
    ║  Ref: Romano et al. "Conformalized Quantile Regression" (2019)                       ║
    ║       Stankeviciute et al. "Conformal Time Series Forecasting" (2021)               ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, max_horizon: int = 72, coverages: List[float] = [0.50, 0.90, 0.95],
                 min_samples_per_horizon: int = 30, use_asymmetric: bool = True,
                 logger: Optional[logging.Logger] = None):
        self.max_horizon = max_horizon
        self.coverages = sorted(coverages)
        self.min_samples_per_horizon = min_samples_per_horizon
        self.use_asymmetric = use_asymmetric  # v5.7.0
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Symmetric quantiles (|y - ŷ|)
        self._calibration_scores: Dict[int, np.ndarray] = {}
        self._quantiles: Dict[int, Dict[float, float]] = {}
        
        # Asymmetric quantiles (y - ŷ) - v5.7.0
        self._signed_errors: Dict[int, np.ndarray] = {}
        self._quantiles_lower: Dict[int, Dict[float, float]] = {}
        self._quantiles_upper: Dict[int, Dict[float, float]] = {}
        
        self._horizon_stats: Dict[int, HorizonCalibrationStats] = {}
        self._calibrated = False
        self._global_quantiles: Dict[float, float] = {}
        self._global_quantiles_lower: Dict[float, float] = {}
        self._global_quantiles_upper: Dict[float, float] = {}
        self._fallback_growth_rate: float = 0.02
        
        # Diagnostics v5.7.0
        self._asymmetry_detected: bool = False
        self._mean_skewness: float = 0.0
        self._mean_bias: float = 0.0
    
    def calibrate(self, y_true_by_horizon: Dict[int, np.ndarray],
                  y_pred_by_horizon: Dict[int, np.ndarray]) -> 'HorizonAwareConformalPredictor':
        """Calibra il predictor usando dati organizzati per orizzonte."""
        mode = "ASYMMETRIC" if self.use_asymmetric else "SYMMETRIC"
        self.logger.info("=" * 70)
        self.logger.info(f"HORIZON-AWARE CONFORMAL CALIBRATION v5.7.0 ({mode})")
        self.logger.info("=" * 70)
        
        horizons = sorted(set(y_true_by_horizon.keys()) & set(y_pred_by_horizon.keys()))
        if not horizons:
            raise ValidationError("No matching horizons between y_true and y_pred")
        
        self.logger.info(f"Calibrating {len(horizons)} horizons: h{min(horizons)} to h{max(horizons)}")
        
        total_samples = 0
        calibrated_horizons = []
        all_skewness = []
        all_bias = []
        
        for h in horizons:
            y_t = np.asarray(y_true_by_horizon[h]).flatten()
            y_p = np.asarray(y_pred_by_horizon[h]).flatten()
            n = min(len(y_t), len(y_p))
            y_t, y_p = y_t[:n], y_p[:n]
            
            mask = np.isfinite(y_t) & np.isfinite(y_p)
            y_t, y_p = y_t[mask], y_p[mask]
            
            if len(y_t) < self.min_samples_per_horizon:
                continue
            
            # Residui assoluti (simmetrici)
            scores = np.abs(y_t - y_p)
            self._calibration_scores[h] = scores
            
            # Residui con segno (asimmetrici) - v5.7.0
            signed_errors = y_t - y_p  # Positivo = sottostima, Negativo = sovrastima
            self._signed_errors[h] = signed_errors
            
            total_samples += len(scores)
            n_scores = len(scores)
            
            # Calcolo quantili simmetrici
            self._quantiles[h] = {}
            for cov in self.coverages:
                q_level = np.ceil((n_scores + 1) * cov) / n_scores
                self._quantiles[h][cov] = float(np.quantile(scores, min(q_level, 1.0)))
            
            # Calcolo quantili asimmetrici - v5.7.0
            self._quantiles_lower[h] = {}
            self._quantiles_upper[h] = {}
            for cov in self.coverages:
                alpha = 1 - cov
                # Lower: quantile a α/2 dei signed errors (tipicamente negativo)
                q_l_level = np.ceil((n_scores + 1) * (alpha / 2)) / n_scores
                # Upper: quantile a 1 - α/2 dei signed errors (tipicamente positivo)
                q_u_level = np.ceil((n_scores + 1) * (1 - alpha / 2)) / n_scores
                
                self._quantiles_lower[h][cov] = float(np.quantile(signed_errors, min(q_l_level, 1.0)))
                self._quantiles_upper[h][cov] = float(np.quantile(signed_errors, min(q_u_level, 1.0)))
            
            # Statistiche asimmetria - v5.7.0
            error_mean = float(np.mean(signed_errors))
            error_std = float(np.std(signed_errors))
            
            # Skewness (Fisher)
            if error_std > 0:
                skewness = float(np.mean(((signed_errors - error_mean) / error_std) ** 3))
            else:
                skewness = 0.0
            
            all_skewness.append(skewness)
            all_bias.append(error_mean)
            
            self._horizon_stats[h] = HorizonCalibrationStats(
                horizon=h, n_samples=len(scores),
                score_mean=float(np.mean(scores)), score_std=float(np.std(scores)),
                score_median=float(np.median(scores)), score_min=float(np.min(scores)),
                score_max=float(np.max(scores)), score_q25=float(np.percentile(scores, 25)),
                score_q75=float(np.percentile(scores, 75)), quantiles=self._quantiles[h].copy(),
                error_mean=error_mean, error_skewness=skewness,
                quantiles_lower=self._quantiles_lower[h].copy(),
                quantiles_upper=self._quantiles_upper[h].copy()
            )
            calibrated_horizons.append(h)
        
        if not calibrated_horizons:
            raise ValidationError(f"No horizons with sufficient samples (need {self.min_samples_per_horizon})")
        
        # Global quantiles (fallback)
        all_scores = np.concatenate([self._calibration_scores[h] for h in calibrated_horizons])
        all_signed = np.concatenate([self._signed_errors[h] for h in calibrated_horizons])
        
        for cov in self.coverages:
            n_all = len(all_scores)
            q_level = np.ceil((n_all + 1) * cov) / n_all
            self._global_quantiles[cov] = float(np.quantile(all_scores, min(q_level, 1.0)))
            
            alpha = 1 - cov
            q_l_level = np.ceil((n_all + 1) * (alpha / 2)) / n_all
            q_u_level = np.ceil((n_all + 1) * (1 - alpha / 2)) / n_all
            self._global_quantiles_lower[cov] = float(np.quantile(all_signed, min(q_l_level, 1.0)))
            self._global_quantiles_upper[cov] = float(np.quantile(all_signed, min(q_u_level, 1.0)))
        
        # Diagnostics v5.7.0
        self._mean_skewness = float(np.mean(all_skewness)) if all_skewness else 0.0
        self._mean_bias = float(np.mean(all_bias)) if all_bias else 0.0
        self._asymmetry_detected = abs(self._mean_skewness) > 0.5 or abs(self._mean_bias) > 10
        
        # Interpola orizzonti mancanti
        self._interpolate_missing_horizons(calibrated_horizons)
        
        self._calibrated = True
        self.logger.info(f"Calibration complete: {len(calibrated_horizons)} horizons, {total_samples} samples")
        
        # Report diagnostics
        if self.use_asymmetric:
            self.logger.info(f"  Asymmetric mode: bias={self._mean_bias:+.2f}, skewness={self._mean_skewness:+.3f}")
            if self._asymmetry_detected:
                self.logger.info("  ⚠ Significant asymmetry detected - asymmetric intervals recommended")
        
        # Report intervalli per orizzonti chiave
        for h in [1, 6, 12, 24, 48, 72]:
            if h in self._quantiles:
                if self.use_asymmetric and h in self._quantiles_lower:
                    q_l = self._quantiles_lower[h].get(0.90, 0)
                    q_u = self._quantiles_upper[h].get(0.90, 0)
                    self.logger.info(f"  h{h:>2}: 90% interval = [{q_l:+.2f}, {q_u:+.2f}] (width=${q_u-q_l:.2f})")
                else:
                    q90 = self._quantiles[h].get(0.90, 0)
                    self.logger.info(f"  h{h:>2}: 90% interval = ±${q90:.2f}")
        
        return self
    
    def _interpolate_missing_horizons(self, calibrated_horizons: List[int]) -> None:
        """Interpola quantili per orizzonti non calibrati."""
        if len(calibrated_horizons) < 2:
            return
        calibrated_horizons = sorted(calibrated_horizons)
        
        for h in range(1, self.max_horizon + 1):
            if h in self._quantiles:
                continue
            
            lower = [ch for ch in calibrated_horizons if ch < h]
            upper = [ch for ch in calibrated_horizons if ch > h]
            
            if not lower and upper:
                # Extrapolate down
                self._quantiles[h] = self._quantiles[upper[0]].copy()
                if self.use_asymmetric:
                    self._quantiles_lower[h] = self._quantiles_lower[upper[0]].copy()
                    self._quantiles_upper[h] = self._quantiles_upper[upper[0]].copy()
            elif lower and not upper:
                # Extrapolate up
                h_ref = lower[-1]
                growth = self._fallback_growth_rate * (h - h_ref)
                self._quantiles[h] = {cov: q * (1 + growth) for cov, q in self._quantiles[h_ref].items()}
                if self.use_asymmetric:
                    self._quantiles_lower[h] = {cov: q * (1 + growth) for cov, q in self._quantiles_lower[h_ref].items()}
                    self._quantiles_upper[h] = {cov: q * (1 + growth) for cov, q in self._quantiles_upper[h_ref].items()}
            elif lower and upper:
                # Interpolate
                h_low, h_high = lower[-1], upper[0]
                alpha = (h - h_low) / (h_high - h_low)
                self._quantiles[h] = {
                    cov: self._quantiles[h_low][cov] * (1 - alpha) + self._quantiles[h_high][cov] * alpha
                    for cov in self.coverages
                }
                if self.use_asymmetric:
                    self._quantiles_lower[h] = {
                        cov: self._quantiles_lower[h_low][cov] * (1 - alpha) + self._quantiles_lower[h_high][cov] * alpha
                        for cov in self.coverages
                    }
                    self._quantiles_upper[h] = {
                        cov: self._quantiles_upper[h_low][cov] * (1 - alpha) + self._quantiles_upper[h_high][cov] * alpha
                        for cov in self.coverages
                    }
    
    def predict_interval(self, point_pred: float, horizon: int = 1, coverage: float = 0.90) -> PredictionInterval:
        """Genera intervallo calibrato per un orizzonte specifico."""
        if not self._calibrated:
            raise StateError("HorizonAwareConformalPredictor not calibrated")
        
        n_samples = self._horizon_stats[horizon].n_samples if horizon in self._horizon_stats else 0
        
        if self.use_asymmetric:
            # ASYMMETRIC MODE - v5.7.0
            if horizon in self._quantiles_lower and coverage in self._quantiles_lower[horizon]:
                q_lower = self._quantiles_lower[horizon][coverage]
                q_upper = self._quantiles_upper[horizon][coverage]
            else:
                q_lower = self._get_interpolated_quantile_asymmetric(horizon, coverage, 'lower')
                q_upper = self._get_interpolated_quantile_asymmetric(horizon, coverage, 'upper')
            
            return PredictionInterval(
                point=point_pred, 
                lower=point_pred + q_lower,  # q_lower è tipicamente negativo
                upper=point_pred + q_upper,  # q_upper è tipicamente positivo
                coverage=coverage, horizon=horizon, calibration_n=n_samples,
                asymmetric=True
            )
        else:
            # SYMMETRIC MODE
            if horizon in self._quantiles and coverage in self._quantiles[horizon]:
                quantile = self._quantiles[horizon][coverage]
            else:
                quantile = self._get_interpolated_quantile(horizon, coverage)
            
            return PredictionInterval(
                point=point_pred, lower=point_pred - quantile, upper=point_pred + quantile,
                coverage=coverage, horizon=horizon, calibration_n=n_samples,
                asymmetric=False
            )
    
    def _get_interpolated_quantile(self, horizon: int, coverage: float) -> float:
        """Ottieni quantile simmetrico per orizzonte non calibrato."""
        calibrated = sorted(self._quantiles.keys())
        if not calibrated:
            return self._global_quantiles.get(coverage, 100) * (1 + self._fallback_growth_rate * horizon)
        
        if horizon <= calibrated[0]:
            return self._quantiles[calibrated[0]].get(coverage, 0) * (horizon / calibrated[0])
        if horizon >= calibrated[-1]:
            base = self._quantiles[calibrated[-1]].get(coverage, 0)
            return base * (1 + self._fallback_growth_rate * (horizon - calibrated[-1]))
        
        for i, h in enumerate(calibrated[:-1]):
            if h <= horizon < calibrated[i+1]:
                h_low, h_high = h, calibrated[i+1]
                alpha = (horizon - h_low) / (h_high - h_low)
                return self._quantiles[h_low].get(coverage, 0) * (1 - alpha) + \
                       self._quantiles[h_high].get(coverage, 0) * alpha
        
        return self._global_quantiles.get(coverage, 100)
    
    def _get_interpolated_quantile_asymmetric(self, horizon: int, coverage: float, side: str) -> float:
        """Ottieni quantile asimmetrico per orizzonte non calibrato."""
        if side == 'lower':
            quantiles_dict = self._quantiles_lower
            global_dict = self._global_quantiles_lower
        else:
            quantiles_dict = self._quantiles_upper
            global_dict = self._global_quantiles_upper
        
        calibrated = sorted(quantiles_dict.keys())
        if not calibrated:
            return global_dict.get(coverage, 0)
        
        if horizon <= calibrated[0]:
            base = quantiles_dict[calibrated[0]].get(coverage, 0)
            return base * (horizon / calibrated[0])
        if horizon >= calibrated[-1]:
            base = quantiles_dict[calibrated[-1]].get(coverage, 0)
            return base * (1 + self._fallback_growth_rate * (horizon - calibrated[-1]))
        
        for i, h in enumerate(calibrated[:-1]):
            if h <= horizon < calibrated[i+1]:
                h_low, h_high = h, calibrated[i+1]
                alpha = (horizon - h_low) / (h_high - h_low)
                return quantiles_dict[h_low].get(coverage, 0) * (1 - alpha) + \
                       quantiles_dict[h_high].get(coverage, 0) * alpha
        
        return global_dict.get(coverage, 0)
    
    def predict_all_intervals(self, point_pred: float, horizon: int = 1) -> Dict[float, PredictionInterval]:
        """Genera intervalli per tutti i livelli di coverage per un orizzonte."""
        return {cov: self.predict_interval(point_pred, horizon, cov) for cov in self.coverages}
    
    def evaluate_coverage(self, y_true_by_horizon: Dict[int, np.ndarray],
                          y_pred_by_horizon: Dict[int, np.ndarray]) -> Dict[int, Dict[float, float]]:
        """Valuta coverage empirica per ogni orizzonte su un test set."""
        results = {}
        for h in sorted(set(y_true_by_horizon.keys()) & set(y_pred_by_horizon.keys())):
            y_t = np.asarray(y_true_by_horizon[h]).flatten()
            y_p = np.asarray(y_pred_by_horizon[h]).flatten()
            n = min(len(y_t), len(y_p))
            y_t, y_p = y_t[:n], y_p[:n]
            
            results[h] = {}
            for cov in self.coverages:
                hits = sum(1 for yt, yp in zip(y_t, y_p) if self.predict_interval(yp, h, cov).contains(yt))
                results[h][cov] = hits / len(y_t) if len(y_t) > 0 else 0.0
            
            if h in self._horizon_stats:
                self._horizon_stats[h].empirical_coverage = results[h]
        return results
    
    def get_stats(self) -> Dict:
        if not self._calibrated:
            return {}
        return {
            'type': 'horizon_aware_asymmetric' if self.use_asymmetric else 'horizon_aware_symmetric',
            'version': '5.7.0',
            'max_horizon': max(self._quantiles.keys()) if self._quantiles else 0,
            'n_calibrated_horizons': len(self._quantiles),
            'coverages': self.coverages,
            'asymmetric_mode': self.use_asymmetric,
            'diagnostics': {
                'mean_bias': round(self._mean_bias, 4),
                'mean_skewness': round(self._mean_skewness, 4),
                'asymmetry_detected': self._asymmetry_detected
            },
            'global_quantiles': {f'{c:.0%}': q for c, q in self._global_quantiles.items()},
            'sample_horizons': {f'h{h}': self._horizon_stats[h].to_dict()
                               for h in [1, 6, 12, 24, 48, 72] if h in self._horizon_stats}
        }


class MultiHorizonCalibrator:
    """
    Genera dati di calibrazione multi-orizzonte durante il training.
    
    Prende il validation set e genera previsioni rolling per ogni orizzonte,
    alimentando HorizonAwareConformalPredictor.calibrate().
    """
    
    def __init__(self, max_horizon: int = 72, stride: int = 1,
                 logger: Optional[logging.Logger] = None):
        self.max_horizon = max_horizon
        self.stride = stride
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def generate_calibration_data(self, X_val: np.ndarray, y_val_prices: np.ndarray,
                                   ensemble_predict_fn: Callable, seq_prep: Any,
                                   decay: float = 0.998, progress: bool = True
                                   ) -> Tuple[Dict[int, np.ndarray], Dict[int, np.ndarray]]:
        """Genera dati di calibrazione multi-orizzonte tramite rolling predictions."""
        n_samples = len(X_val)
        usable_samples = n_samples - self.max_horizon
        
        if usable_samples <= 0:
            raise ValidationError(f"Not enough samples: have {n_samples}, need {self.max_horizon + 1}")
        
        self.logger.info(f"Generating multi-horizon calibration data: {usable_samples} origins, h=1..{self.max_horizon}")
        
        y_true_by_h: Dict[int, List[float]] = {h: [] for h in range(1, self.max_horizon + 1)}
        y_pred_by_h: Dict[int, List[float]] = {h: [] for h in range(1, self.max_horizon + 1)}
        
        origins = range(0, usable_samples, self.stride)
        iterator = tqdm(origins, desc="Calibration", disable=not progress, ncols=100)
        
        for i in iterator:
            X_start = X_val[i:i+1]
            curr_price = y_val_prices[i]
            
            reg_pred, _ = ensemble_predict_fn(X_start)
            
            pred_price = curr_price
            for h in range(1, min(self.max_horizon + 1, n_samples - i)):
                if h == 1:
                    delta_scaled = reg_pred[0]
                    pred_price = seq_prep.inverse_transform_target(np.array([delta_scaled]), np.array([curr_price]))[0]
                else:
                    pred_price = curr_price + (pred_price - curr_price) * decay
                
                true_price = y_val_prices[i + h]
                y_true_by_h[h].append(true_price)
                y_pred_by_h[h].append(pred_price)
        
        y_true_dict = {h: np.array(v) for h, v in y_true_by_h.items() if len(v) > 0}
        y_pred_dict = {h: np.array(v) for h, v in y_pred_by_h.items() if len(v) > 0}
        
        self.logger.info(f"Calibration data generated: {len(y_true_dict)} horizons")
        return y_true_dict, y_pred_dict


class ConformalPredictor:
    """
    PROFETA v5.7.0 - Conformal Predictor con supporto Horizon-Aware e Asimmetrico
    
    Wrapper backward-compatible che usa HorizonAwareConformalPredictor internamente.
    
    USO:
    - calibrate(): Calibrazione legacy (singolo orizzonte, simmetrica)
    - calibrate_horizon_aware(): Calibrazione per orizzonte (v5.7.0, asimmetrica)
    """
    
    def __init__(self, coverages: List[float] = [0.50, 0.90, 0.95],
                 max_horizon: int = 72, use_asymmetric: bool = True,
                 logger: Optional[logging.Logger] = None):
        self.coverages = sorted(coverages)
        self.max_horizon = max_horizon
        self.use_asymmetric = use_asymmetric  # v5.7.0
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        self.calibration_scores: Optional[np.ndarray] = None
        self.quantiles: Dict[float, float] = {}
        self._calibrated = False
        self._n_calibration = 0
        
        self._horizon_aware: Optional[HorizonAwareConformalPredictor] = None
        self._use_horizon_aware = False
    
    def calibrate(self, y_true: np.ndarray, y_pred: np.ndarray) -> 'ConformalPredictor':
        """Calibrazione legacy (singolo orizzonte) per backward compatibility."""
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()
        
        self.calibration_scores = np.abs(y_true - y_pred)
        self._n_calibration = len(self.calibration_scores)
        
        for coverage in self.coverages:
            n = self._n_calibration
            q_level = np.ceil((n + 1) * coverage) / n
            self.quantiles[coverage] = float(np.quantile(self.calibration_scores, min(q_level, 1.0)))
        
        self._calibrated = True
        self._use_horizon_aware = False
        
        self.logger.info(f"Conformal calibration (legacy): n={self._n_calibration}, "
                        f"quantiles={{{', '.join(f'{c:.0%}: ±${q:.2f}' for c, q in self.quantiles.items())}}}")
        return self
    
    def calibrate_horizon_aware(self, y_true_by_horizon: Dict[int, np.ndarray],
                                 y_pred_by_horizon: Dict[int, np.ndarray]) -> 'ConformalPredictor':
        """Calibrazione horizon-aware (v5.7.0) con supporto asimmetrico."""
        self._horizon_aware = HorizonAwareConformalPredictor(
            max_horizon=self.max_horizon, coverages=self.coverages, 
            use_asymmetric=self.use_asymmetric, logger=self.logger
        )
        self._horizon_aware.calibrate(y_true_by_horizon, y_pred_by_horizon)
        
        self.quantiles = self._horizon_aware._global_quantiles.copy()
        self._calibrated = True
        self._use_horizon_aware = True
        self._n_calibration = sum(len(s) for s in self._horizon_aware._calibration_scores.values())
        
        return self
    
    def predict_interval(self, point_pred: float, coverage: float = 0.90, horizon: int = 1) -> PredictionInterval:
        """Genera intervallo, usando horizon se disponibile."""
        if not self._calibrated:
            raise StateError("ConformalPredictor not calibrated")
        
        if self._use_horizon_aware and self._horizon_aware:
            return self._horizon_aware.predict_interval(point_pred, horizon, coverage)
        
        if coverage in self.quantiles:
            quantile = self.quantiles[coverage]
        else:
            q_level = np.ceil((self._n_calibration + 1) * coverage) / self._n_calibration
            quantile = float(np.quantile(self.calibration_scores, min(q_level, 1.0)))
        
        return PredictionInterval(
            point=point_pred, lower=point_pred - quantile, upper=point_pred + quantile,
            coverage=coverage, horizon=horizon, calibration_n=self._n_calibration
        )
    
    def predict_all_intervals(self, point_pred: float, horizon: int = 1) -> Dict[float, PredictionInterval]:
        """Genera intervalli per tutte le coverage"""
        return {cov: self.predict_interval(point_pred, cov, horizon) for cov in self.coverages}
    
    def evaluate_coverage(self, y_true: np.ndarray, y_pred: np.ndarray, horizon: int = 1) -> Dict[float, float]:
        """Valuta coverage empirica"""
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()
        
        empirical = {}
        for cov in self.coverages:
            hits = sum(1 for yt, yp in zip(y_true, y_pred) 
                      if self.predict_interval(yp, cov, horizon).contains(yt))
            empirical[cov] = hits / len(y_true)
        return empirical
    
    def get_horizon_aware_predictor(self) -> Optional[HorizonAwareConformalPredictor]:
        """Restituisce il predictor horizon-aware se disponibile"""
        return self._horizon_aware if self._use_horizon_aware else None
    
    def get_stats(self) -> Dict:
        if not self._calibrated:
            return {}
        if self._use_horizon_aware and self._horizon_aware:
            return self._horizon_aware.get_stats()
        return {
            'type': 'legacy',
            'n_calibration': self._n_calibration,
            'score_mean': float(np.mean(self.calibration_scores)),
            'score_std': float(np.std(self.calibration_scores)),
            'quantiles': {f'{c:.0%}': q for c, q in self.quantiles.items()}
        }
    
    def get_horizon_aware_predictor(self) -> Optional[HorizonAwareConformalPredictor]:
        """Accesso diretto al predictor horizon-aware se disponibile"""
        return self._horizon_aware if self._use_horizon_aware else None


@dataclass
class WalkForwardFold:
    """Risultato di un singolo fold"""
    fold_id: int
    train_size: int
    test_size: int
    metrics: RegressionMetrics
    direction_metrics: DirectionMetrics
    
    def to_dict(self) -> Dict:
        return {
            'fold_id': self.fold_id,
            'train_size': self.train_size,
            'test_size': self.test_size,
            'r2': self.metrics.r2,
            'rmse': self.metrics.rmse,
            'mae': self.metrics.mae,
            'direction_accuracy': self.direction_metrics.direction_accuracy
        }


@dataclass 
class WalkForwardResult:
    """Risultato completo walk-forward validation"""
    folds: List[WalkForwardFold]
    mean_r2: float
    std_r2: float
    mean_rmse: float
    std_rmse: float
    mean_direction_accuracy: float
    stability_score: float      # 1 - CV(R²)
    r2_trend: float             # Slope R² nel tempo
    degradation_detected: bool
    
    def to_dict(self) -> Dict:
        return {
            'n_folds': len(self.folds),
            'metrics': {
                'r2': {'mean': self.mean_r2, 'std': self.std_r2},
                'rmse': {'mean': self.mean_rmse, 'std': self.std_rmse},
                'direction_accuracy': self.mean_direction_accuracy
            },
            'stability': {
                'score': self.stability_score,
                'r2_trend': self.r2_trend,
                'degradation_detected': self.degradation_detected
            },
            'folds': [f.to_dict() for f in self.folds]
        }
    
    def summary(self) -> str:
        status = "⚠️ DEGRADATION" if self.degradation_detected else "✅ STABLE"
        return (f"Walk-Forward ({len(self.folds)} folds): "
                f"R²={self.mean_r2:.4f}±{self.std_r2:.4f}, "
                f"Stability={self.stability_score:.1%} {status}")


class WalkForwardValidator:
    """
    PROFETA v5.4.0 - Walk-Forward Cross-Validation
    
    Fold 1: [========TRAIN========][TEST]
    Fold 2: [==========TRAIN==========][TEST]
    Fold 3: [============TRAIN============][TEST]
    """
    
    def __init__(self, n_splits: int = 5, min_train_pct: float = 0.5,
                 test_pct: float = 0.1, logger: Optional[logging.Logger] = None):
        self.n_splits = n_splits
        self.min_train_pct = min_train_pct
        self.test_pct = test_pct
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def split(self, n_samples: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Genera indici per ogni fold"""
        min_train = int(n_samples * self.min_train_pct)
        test_size = int(n_samples * self.test_pct)
        remaining = n_samples - min_train
        step = remaining // self.n_splits
        
        splits = []
        for i in range(self.n_splits):
            train_end = min_train + i * step
            test_start = train_end
            test_end = min(test_start + test_size, n_samples)
            if test_end > test_start:
                splits.append(((0, train_end), (test_start, test_end)))
        return splits
    
    def validate(self, X: np.ndarray, y: np.ndarray, 
                 model_builder: Callable) -> WalkForwardResult:
        """
        Esegue walk-forward validation.
        
        Args:
            X: Features (n_samples, seq_len, n_features)
            y: Target (n_samples,)
            model_builder: Callable(X_train, y_train) -> model con .predict()
        """
        splits = self.split(len(X))
        folds = []
        
        self.logger.info(f"Walk-Forward Validation: {len(splits)} folds")
        
        for fold_id, ((train_start, train_end), (test_start, test_end)) in enumerate(splits):
            X_train, y_train = X[train_start:train_end], y[train_start:train_end]
            X_test, y_test = X[test_start:test_end], y[test_start:test_end]
            
            self.logger.info(f"Fold {fold_id+1}: Train={train_end}, Test={test_end-test_start}")
            
            model = model_builder(X_train, y_train)
            y_pred = model.predict(X_test)
            if hasattr(y_pred, 'flatten'): y_pred = y_pred.flatten()
            
            reg_m = MetricsCalculator.calc_regression(y_test, y_pred)
            dir_m = MetricsCalculator.calc_direction_from_regression(np.sign(y_test), np.sign(y_pred))
            
            folds.append(WalkForwardFold(
                fold_id=fold_id + 1,
                train_size=train_end - train_start,
                test_size=test_end - test_start,
                metrics=reg_m,
                direction_metrics=dir_m
            ))
            self.logger.info(f"  → R²={reg_m.r2:.4f}, Dir={dir_m.direction_accuracy:.1%}")
        
        # Aggregazione
        r2_vals = [f.metrics.r2 for f in folds]
        mean_r2, std_r2 = np.mean(r2_vals), np.std(r2_vals)
        
        stability = max(0, 1 - std_r2 / (abs(mean_r2) + 1e-10))
        
        if len(r2_vals) >= 3:
            slope, _ = np.polyfit(range(len(r2_vals)), r2_vals, 1)
            degradation = slope < -0.01
        else:
            slope, degradation = 0.0, False
        
        return WalkForwardResult(
            folds=folds,
            mean_r2=float(mean_r2),
            std_r2=float(std_r2),
            mean_rmse=float(np.mean([f.metrics.rmse for f in folds])),
            std_rmse=float(np.std([f.metrics.rmse for f in folds])),
            mean_direction_accuracy=float(np.mean([f.direction_metrics.direction_accuracy for f in folds])),
            stability_score=float(stability),
            r2_trend=float(slope),
            degradation_detected=degradation
        )


@dataclass
class DriftAlert:
    """Alert per drift detection"""
    detected: bool
    drift_type: str          # "error", "prediction", "performance"
    severity: str            # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    z_score: float
    metric_name: str
    baseline_value: float
    current_value: float
    message: str
    
    def to_dict(self) -> Dict:
        return {
            'detected': self.detected,
            'type': self.drift_type,
            'severity': self.severity,
            'z_score': round(self.z_score, 2),
            'metric': self.metric_name,
            'baseline': round(self.baseline_value, 4),
            'current': round(self.current_value, 4),
            'message': self.message
        }


class DriftMonitor:
    """
    PROFETA v5.4.0 - Drift Detection & Monitoring
    
    Monitora:
    1. Error Drift: cambio distribuzione errori
    2. Prediction Drift: cambio distribuzione previsioni
    3. Performance Drift: degradazione R², MAE
    """
    
    def __init__(self, z_threshold: float = 2.0, logger: Optional[logging.Logger] = None):
        self.z_threshold = z_threshold
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._baseline: Dict[str, float] = {}
        self._fitted = False
    
    def fit_baseline(self, y_true: np.ndarray, y_pred: np.ndarray) -> 'DriftMonitor':
        """Stabilisce baseline statistics"""
        y_true, y_pred = np.asarray(y_true).flatten(), np.asarray(y_pred).flatten()
        errors = y_true - y_pred
        metrics = MetricsCalculator.calc_regression(y_true, y_pred)
        
        self._baseline = {
            'error_mean': float(np.mean(errors)),
            'error_std': float(np.std(errors)),
            'pred_mean': float(np.mean(y_pred)),
            'pred_std': float(np.std(y_pred)),
            'r2': metrics.r2,
            'mae': metrics.mae
        }
        self._fitted = True
        self.logger.info(f"Drift baseline: error_mean={self._baseline['error_mean']:.4f}, R²={self._baseline['r2']:.4f}")
        return self
    
    def _severity(self, z: float) -> str:
        z = abs(z)
        if z >= 4: return "CRITICAL"
        if z >= 3: return "HIGH"
        if z >= 2: return "MEDIUM"
        return "LOW"
    
    def check_error_drift(self, errors: np.ndarray) -> DriftAlert:
        if not self._fitted: raise StateError("DriftMonitor not fitted")
        current = float(np.mean(errors))
        z = (current - self._baseline['error_mean']) / (self._baseline['error_std'] + 1e-10)
        detected = abs(z) > self.z_threshold
        return DriftAlert(detected, "error", self._severity(z), z, "mean_error",
                         self._baseline['error_mean'], current,
                         f"Error drift {'DETECTED' if detected else 'OK'}: z={z:.2f}")
    
    def check_prediction_drift(self, predictions: np.ndarray) -> DriftAlert:
        if not self._fitted: raise StateError("DriftMonitor not fitted")
        current = float(np.mean(predictions))
        z = (current - self._baseline['pred_mean']) / (self._baseline['pred_std'] + 1e-10)
        detected = abs(z) > self.z_threshold
        return DriftAlert(detected, "prediction", self._severity(z), z, "mean_prediction",
                         self._baseline['pred_mean'], current,
                         f"Prediction drift {'DETECTED' if detected else 'OK'}: z={z:.2f}")
    
    def check_performance_drift(self, y_true: np.ndarray, y_pred: np.ndarray) -> DriftAlert:
        if not self._fitted: raise StateError("DriftMonitor not fitted")
        metrics = MetricsCalculator.calc_regression(y_true, y_pred)
        r2_drop = self._baseline['r2'] - metrics.r2
        z = r2_drop / (self._baseline['r2'] + 1e-10) * 10
        detected = r2_drop > self._baseline['r2'] * 0.1  # >10% drop
        return DriftAlert(detected, "performance", self._severity(z), z, "r2",
                         self._baseline['r2'], metrics.r2,
                         f"R² {'DEGRADED' if detected else 'OK'}: {self._baseline['r2']:.4f} → {metrics.r2:.4f}")
    
    def check_all(self, y_true: np.ndarray, y_pred: np.ndarray) -> List[DriftAlert]:
        errors = np.asarray(y_true).flatten() - np.asarray(y_pred).flatten()
        return [
            self.check_error_drift(errors),
            self.check_prediction_drift(y_pred),
            self.check_performance_drift(y_true, y_pred)
        ]
    
    def get_baseline(self) -> Dict: return self._baseline if self._fitted else {}


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    PROFETA MODEL WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════════════════

class PROFETAModel:
    """
    PROFETA v5.3.0 - Pure Regression Model
    
    Single-task model che predice solo il delta di prezzo.
    La classification head è stata rimossa.
    """
    def __init__(self, config: ModelConfig, train_config: TrainingConfig,
                 logger: Optional[logging.Logger] = None):
        self.config, self.train_config = config, train_config
        self.logger = logger or logging.getLogger(f"{self.__class__.__name__}_{config.model_id}")
        self.model: Optional[Model] = None
        self.model_uid = uuid.uuid4().hex[:12]
        self._lock, self._trained = threading.RLock(), False
    
    def build(self) -> 'PROFETAModel':
        with self._lock:
            gpu = GPUManager()
            with gpu.strategy_scope():
                self.model = RegressionModelBuilder(self.config, self.logger).build()
                self._compile()
        return self
    
    def _compile(self):
        """Compila il modello con solo loss di regressione (MSE)"""
        self.model.compile(
            optimizer=Adam(learning_rate=self.train_config.learning_rate),
            loss='mse',
            metrics=['mae'])
    
    def train(self, X_train, y_reg_train, X_val=None, y_reg_val=None) -> Dict:
        """
        Training single-task (solo regressione).
        
        Args:
            X_train: Features di training
            y_reg_train: Target di regressione (delta scalati)
            X_val: Features di validazione (opzionale)
            y_reg_val: Target di validazione (opzionale)
        """
        with self._lock:
            if self.model is None: self.build()
            
            # Tronca sequenze alla lunghezza specifica di questo modello
            seq_len = self.config.sequence_length
            if X_train.shape[1] > seq_len:
                X_train = X_train[:, -seq_len:, :]
            if X_val is not None and X_val.shape[1] > seq_len:
                X_val = X_val[:, -seq_len:, :]
            
            val_data = (X_val, y_reg_val) if X_val is not None else None
            
            callbacks = [
                EarlyStopping('val_loss', patience=self.train_config.early_stopping_patience, restore_best_weights=True),
                ReduceLROnPlateau('val_loss', factor=self.train_config.reduce_lr_factor,
                                 patience=self.train_config.reduce_lr_patience, min_lr=1e-7),
                TQDMProgressCallback(self.train_config.num_epochs, "Training", self.config.model_id)]
            
            history = self.model.fit(X_train, y_reg_train,
                                     epochs=self.train_config.num_epochs, batch_size=self.train_config.batch_size,
                                     validation_data=val_data, callbacks=callbacks, verbose=0)
            self._trained = True
            return history.history
    
    def predict(self, X) -> np.ndarray:
        """Predice delta scalati (solo regressione)"""
        with self._lock:
            if self.model is None: raise StateError("Model not built")
            seq_len = self.config.sequence_length
            if X.shape[1] > seq_len:
                X = X[:, -seq_len:, :]
            return self.model.predict(X, verbose=0).flatten()
    
    def save(self, base_path):
        with self._lock:
            p = Path(base_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(p.with_suffix('.keras'))
            with open(p.with_suffix('.meta.json'), 'w') as f:
                json.dump({'model_uid': self.model_uid, 'config': asdict(self.config),
                          'trained': self._trained, 'version': __version__}, f, indent=2)
    
    @classmethod
    def load(cls, base_path, train_config=None, logger=None) -> 'PROFETAModel':
        p = Path(base_path)
        with open(p.with_suffix('.meta.json')) as f: meta = json.load(f)
        config = ModelConfig(**meta['config'])
        inst = cls(config, train_config or TrainingConfig(), logger)
        gpu = GPUManager()
        with gpu.strategy_scope():
            inst.model = load_model(p.with_suffix('.keras'))
        inst.model_uid, inst._trained = meta.get('model_uid', uuid.uuid4().hex[:12]), meta.get('trained', True)
        return inst
    
    @property
    def is_trained(self) -> bool: return self._trained


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    ENSEMBLE & FUSION
# ═══════════════════════════════════════════════════════════════════════════════════════════

class EnsembleManager:
    """
    PROFETA v5.3.0 - Pure Regression Ensemble
    
    Gestisce un ensemble di modelli di regressione.
    """
    def __init__(self, model_configs: List[ModelConfig], train_config: TrainingConfig,
                 logger: Optional[logging.Logger] = None):
        self.model_configs, self.train_config = model_configs, train_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.models: List[PROFETAModel] = []
        self._ensemble_delta = 0.0
        self._model_deltas: Dict[int, float] = {}
    
    def build_all(self) -> 'EnsembleManager':
        self.logger.info(f"Building ensemble of {len(self.model_configs)} models")
        self.models = [PROFETAModel(c, self.train_config, self.logger).build() for c in self.model_configs]
        return self
    
    def train_all(self, X_train, y_reg_train, X_val, y_reg_val) -> Dict:
        """Training single-task per tutti i modelli dell'ensemble"""
        self.logger.info("=" * 70)
        self.logger.info(f"ENSEMBLE TRAINING - {len(self.models)} models (Pure Regression)")
        histories = {}
        for i, m in enumerate(self.models):
            self.logger.info(f"Training model {i+1}/{len(self.models)}")
            histories[f'model_{i+1}'] = m.train(X_train, y_reg_train, X_val, y_reg_val)
        self._calc_ensemble_delta(X_val, y_reg_val)
        return histories
    
    def _calc_ensemble_delta(self, X, y_true):
        preds = []
        for m in self.models:
            reg = m.predict(X)
            preds.append(reg)
            self._model_deltas[m.config.model_id] = float(np.mean(y_true - reg))
        ens_pred = np.mean(preds, axis=0)
        self._ensemble_delta = float(np.mean(y_true - ens_pred))
        self.logger.info(f"Ensemble delta: {self._ensemble_delta:.6f}")
    
    def predict_ensemble(self, X, apply_delta: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predice con l'ensemble.
        
        Returns:
            (reg_mean, reg_std) - Media e std delle previsioni (per confidence)
        """
        reg_preds = []
        for m in self.models:
            reg = m.predict(X)
            reg_preds.append(reg)
        ens_reg = np.mean(reg_preds, axis=0)
        ens_reg_std = np.std(reg_preds, axis=0) if len(reg_preds) > 1 else np.zeros_like(ens_reg)
        if apply_delta: ens_reg += self._ensemble_delta
        return ens_reg, ens_reg_std
    
    def save_all(self, out_dir):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for m in self.models:
            m.save(out_dir / f"profeta_model_{m.config.model_id}")
        with open(out_dir / "ensemble_meta.json", 'w') as f:
            json.dump({'num_models': len(self.models), 'ensemble_delta': self._ensemble_delta,
                      'model_deltas': self._model_deltas, 'version': __version__}, f, indent=2)
    
    def load_all(self, out_dir) -> 'EnsembleManager':
        out_dir = Path(out_dir)
        with open(out_dir / "ensemble_meta.json") as f: meta = json.load(f)
        self._ensemble_delta = meta.get('ensemble_delta', 0.0)
        self._model_deltas = {int(k): v for k, v in meta.get('model_deltas', {}).items()}
        self.models = []
        for i in range(meta['num_models']):
            p = out_dir / f"profeta_model_{i+1}"
            if p.with_suffix('.keras').exists():
                self.models.append(PROFETAModel.load(p, self.train_config, self.logger))
        return self
    
    @property
    def ensemble_delta(self) -> float: return self._ensemble_delta
    @property
    def num_models(self) -> int: return len(self.models)

@dataclass
class FusionResult:
    """
    PROFETA v5.5.0 - Enterprise Forecast Result with Horizon-Aware Intervals
    
    Include:
    - Previsione puntuale
    - Intervalli di previsione calibrati per orizzonte (conformal)
    - Trend derivato
    - Confidence e volatility regime
    - Orizzonte di previsione (v5.5.0)
    """
    timestamp: pd.Timestamp
    predicted_value: float
    predicted_change_pct: float
    direction: int                    # -1=DOWN, 0=FLAT, +1=UP
    trend: str                        # "DOWN", "FLAT", "UP"
    confidence: float                 # Convergenza ensemble (0-1)
    volatility_regime: str            # "LOW", "NORMAL", "HIGH", "EXTREME"
    
    # Horizon info (v5.5.0)
    horizon: int = 0                  # 0 = historical, 1+ = future
    
    # Conformal Intervals - ora horizon-aware (v5.5.0)
    interval_50: Optional[Tuple[float, float]] = None   # 50% coverage
    interval_90: Optional[Tuple[float, float]] = None   # 90% coverage
    interval_95: Optional[Tuple[float, float]] = None   # 95% coverage
    
    # Calibration metadata (v5.5.0)
    interval_calibration_n: int = 0   # Campioni usati per calibrare questo orizzonte
    
    def to_dict(self) -> Dict:
        result = {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'predicted_value': round(self.predicted_value, 2),
            'change_pct': round(self.predicted_change_pct, 6),
            'direction': self.direction,
            'trend': self.trend,
            'confidence': round(self.confidence, 4),
            'volatility_regime': self.volatility_regime,
            'horizon': self.horizon
        }
        # Aggiungi intervalli se presenti
        if self.interval_90:
            result['interval_90'] = {
                'lower': round(self.interval_90[0], 2),
                'upper': round(self.interval_90[1], 2),
                'width': round(self.interval_90[1] - self.interval_90[0], 2)
            }
        if self.interval_50:
            result['interval_50'] = {
                'lower': round(self.interval_50[0], 2),
                'upper': round(self.interval_50[1], 2),
                'width': round(self.interval_50[1] - self.interval_50[0], 2)
            }
        if self.interval_95:
            result['interval_95'] = {
                'lower': round(self.interval_95[0], 2),
                'upper': round(self.interval_95[1], 2),
                'width': round(self.interval_95[1] - self.interval_95[0], 2)
            }
        if self.interval_calibration_n > 0:
            result['calibration_samples'] = self.interval_calibration_n
        return result
    
    def to_csv_row(self) -> Dict:
        """Versione flat per CSV export con intervalli horizon-aware (v5.5.0)"""
        row = {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'horizon': self.horizon,
            'predicted_value': round(self.predicted_value, 2),
            'change_pct': round(self.predicted_change_pct, 6),
            'direction': self.direction,
            'trend': self.trend,
            'confidence': round(self.confidence, 4),
            'volatility_regime': self.volatility_regime,
            'interval_90_lower': round(self.interval_90[0], 2) if self.interval_90 else None,
            'interval_90_upper': round(self.interval_90[1], 2) if self.interval_90 else None,
            'interval_90_width': round(self.interval_90[1] - self.interval_90[0], 2) if self.interval_90 else None,
        }
        return row

class FusionEngine:
    """
    PROFETA v5.3.0 - Pure Regression Fusion
    
    Trasforma le predizioni di regressione in FusionResult.
    Non usa più cls_probs (rimosso in v5.3.0).
    """
    def __init__(self, config: FusionConfig, logger: Optional[logging.Logger] = None):
        self.config, self.logger = config, logger or logging.getLogger(self.__class__.__name__)
    
    def fuse(self, timestamps, current_values, reg_preds, 
             ensemble_std: Optional[np.ndarray] = None,
             volatility_regime: str = "NORMAL") -> List[FusionResult]:
        """
        Fonde le predizioni di regressione in FusionResult.
        
        Args:
            timestamps: Array di timestamp
            current_values: Array di prezzi correnti
            reg_preds: Array di prezzi predetti
            ensemble_std: Array di std dell'ensemble (per confidence)
            volatility_regime: Regime di volatilità corrente
        """
        return [self._fuse_single(
            timestamps[i], 
            current_values[i] if i < len(current_values) else current_values[-1],
            reg_preds[i], 
            ensemble_std[i] if ensemble_std is not None else None,
            volatility_regime
        ) for i in range(len(timestamps))]
    
    def _fuse_single(self, ts, curr_val, reg_pred,
                     ensemble_std: Optional[float] = None,
                     volatility_regime: str = "NORMAL") -> FusionResult:
        """
        PROFETA v5.3.0 - Pure Regression Fusion
        
        Genera FusionResult da una singola predizione di regressione.
        Il trend è derivato matematicamente dal delta.
        """
        # ═══════════════════════════════════════════════════════════════════════════
        # CALCOLO DELTA E TREND
        # ═══════════════════════════════════════════════════════════════════════════
        delta_abs = reg_pred - curr_val
        change_pct = delta_abs / (curr_val + EPSILON)
        
        # Soglia dinamica per determinare UP/DOWN/FLAT
        delta_threshold = max(abs(curr_val) * self.config.delta_threshold_pct, 10)
        flat_threshold = delta_threshold * 0.5
        
        # Trend derivato matematicamente
        if delta_abs > flat_threshold:
            direction = 1
            trend = "UP"
        elif delta_abs < -flat_threshold:
            direction = -1
            trend = "DOWN"
        else:
            direction = 0
            trend = "FLAT"
        
        # ═══════════════════════════════════════════════════════════════════════════
        # CONFIDENCE (convergenza ensemble)
        # ═══════════════════════════════════════════════════════════════════════════
        if ensemble_std is not None and ensemble_std > 0:
            std_normalized = ensemble_std / (curr_val + EPSILON)
            threshold_normalized = delta_threshold / (curr_val + EPSILON)
            confidence = np.exp(-3 * std_normalized / (threshold_normalized + EPSILON))
            confidence = float(np.clip(confidence, 0.1, 0.99))
        else:
            movement_strength = abs(delta_abs) / delta_threshold
            confidence = min(movement_strength * 0.5, 1.0)
        
        return FusionResult(
            timestamp=ts,
            predicted_value=reg_pred,
            predicted_change_pct=change_pct,
            direction=direction,
            trend=trend,
            confidence=confidence,
            volatility_regime=volatility_regime
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    OUTPUT & TEMPORAL ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════

class OutputGenerator:
    def __init__(self, out_dir, logger=None):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def generate_csv(self, results: List[FusionResult], fn="predictions.csv", 
                     custom_path: Optional[str] = None) -> Path:
        df = pd.DataFrame([r.to_dict() for r in results])
        if custom_path:
            p = Path(custom_path)
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            p = self.out_dir / fn
        df.to_csv(p, index=False)
        self.logger.info(f"CSV saved: {p}")
        return p
    
    def generate_json(self, results, metrics, metadata, fn="predictions.json") -> Path:
        out = {'metadata': {**metadata, 'generated': datetime.datetime.now().isoformat(), 'version': __version__},
               'metrics': metrics.to_dict(), 'predictions': [r.to_dict() for r in results]}
        p = self.out_dir / fn
        with open(p, 'w') as f: json.dump(out, f, indent=2, default=str)
        self.logger.info(f"JSON saved: {p}")
        return p
    
    def generate_graph(self, hist_vals, hist_ts, results, metrics, fn="analysis.png") -> Path:
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig, height_ratios=[2, 1])
        
        # Normalizza timestamp (rimuove timezone per matplotlib)
        def normalize_ts(ts_array):
            normalized = []
            for ts in ts_array:
                if isinstance(ts, pd.Timestamp):
                    if ts.tzinfo is not None:
                        ts = ts.tz_convert(None)  # rimuove tz da timestamp tz-aware
                elif hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                normalized.append(ts)
            return normalized
        
        hist_ts_norm = normalize_ts(hist_ts[-100:])
        
        # Main chart
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(hist_ts_norm, hist_vals[-100:], 'b-', linewidth=1.5, label='Actual', alpha=0.8)
        if results:
            pred_ts = normalize_ts([r.timestamp for r in results])
            pred_vals = [r.predicted_value for r in results]
            ax1.plot(pred_ts, pred_vals, 'r--', linewidth=2, label='Predicted', marker='o', markersize=4)
        ax1.set_title('PROFETA Universal v5.2 - Pure Forecast', fontsize=14, fontweight='bold')
        ax1.legend(); ax1.grid(True, alpha=0.3)
        
        # Trend Direction & Confidence (v5.2.0 Pure Forecast)
        ax2 = fig.add_subplot(gs[1, 0])
        if results:
            x = range(len(results))
            directions = [r.direction for r in results]
            confidences = [r.confidence for r in results]
            colors = ['#27ae60' if d > 0 else '#c0392b' if d < 0 else '#95a5a6' for d in directions]
            ax2.bar(x, confidences, color=colors, alpha=0.7)
            ax2.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='50% confidence')
        ax2.set_title('Trend Direction & Confidence'); ax2.set_ylim(0, 1)
        ax2.set_ylabel('Confidence'); ax2.legend()
        
        # Metrics
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.axis('off')
        txt = (f"REGRESSION\n{'─'*20}\nRMSE: {metrics.regression.rmse:.6f}\n"
               f"MAE: {metrics.regression.mae:.6f}\nR²: {metrics.regression.r2:.4f}\n\n"
               f"DIRECTION\n{'─'*20}\nDir Accuracy: {metrics.classification.direction_accuracy:.1%}\n"
               f"UP Precision: {metrics.classification.up_precision:.1%}\n"
               f"DOWN Precision: {metrics.classification.down_precision:.1%}")
        ax3.text(0.1, 0.9, txt, transform=ax3.transAxes, fontsize=10, va='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        p = self.out_dir / fn
        plt.savefig(p, dpi=150, bbox_inches='tight')
        plt.close()
        self.logger.info(f"Graph saved: {p}")
        return p
    
    def generate_validation_graph(self, y_actual: np.ndarray, y_predicted: np.ndarray, 
                                   metrics, val_timestamps=None, fn="validation_comparison.png") -> Path:
        """
        Genera grafico professionale di confronto Predictions vs Actual sul validation set.
        
        Args:
            y_actual: Valori reali del validation set
            y_predicted: Valori predetti dal modello
            metrics: HybridMetrics con le metriche di valutazione
            val_timestamps: Timestamps opzionali per l'asse X
            fn: Nome file output
        """
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle('PROFETA v5.0 - Validation Set Analysis\nPredictions vs Actual Comparison', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        gs = GridSpec(3, 3, figure=fig, height_ratios=[2, 1.2, 1], hspace=0.3, wspace=0.3)
        
        # Calcola errori
        errors = y_predicted - y_actual
        abs_errors = np.abs(errors)
        pct_errors = (errors / (y_actual + 1e-10)) * 100
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 1: Serie temporale - Actual vs Predicted (spanning top)
        # ═══════════════════════════════════════════════════════════════════════════════
        ax1 = fig.add_subplot(gs[0, :])
        x_axis = val_timestamps if val_timestamps is not None else np.arange(len(y_actual))
        
        ax1.plot(x_axis, y_actual, 'b-', linewidth=1.5, label='Actual', alpha=0.8)
        ax1.plot(x_axis, y_predicted, 'r--', linewidth=1.5, label='Predicted', alpha=0.8)
        ax1.fill_between(x_axis, y_actual, y_predicted, alpha=0.2, color='gray', label='Error Zone')
        
        ax1.set_title(f'Time Series Comparison (Validation Set: {len(y_actual)} samples)', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Sample Index' if val_timestamps is None else 'Timestamp')
        ax1.set_ylabel('Value')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # Annotazione metriche sul grafico
        metrics_text = f"R² = {metrics.regression.r2:.4f}  |  RMSE = {metrics.regression.rmse:.6f}  |  MAE = {metrics.regression.mae:.6f}"
        ax1.text(0.5, 1.02, metrics_text, transform=ax1.transAxes, ha='center', fontsize=10, 
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 2: Scatter Plot con regressione
        # ═══════════════════════════════════════════════════════════════════════════════
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.scatter(y_actual, y_predicted, alpha=0.5, s=20, c='steelblue', edgecolors='none')
        
        # Linea di perfetta previsione (45°)
        min_val, max_val = min(y_actual.min(), y_predicted.min()), max(y_actual.max(), y_predicted.max())
        margin = (max_val - min_val) * 0.05
        ax2.plot([min_val - margin, max_val + margin], [min_val - margin, max_val + margin], 
                 'g--', linewidth=2, label='Perfect Prediction')
        
        # Linea di regressione
        z = np.polyfit(y_actual, y_predicted, 1)
        p_line = np.poly1d(z)
        ax2.plot([min_val, max_val], [p_line(min_val), p_line(max_val)], 
                 'r-', linewidth=1.5, label=f'Regression (slope={z[0]:.3f})')
        
        ax2.set_title('Scatter: Actual vs Predicted', fontsize=11, fontweight='bold')
        ax2.set_xlabel('Actual Values')
        ax2.set_ylabel('Predicted Values')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(min_val - margin, max_val + margin)
        ax2.set_ylim(min_val - margin, max_val + margin)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 3: Distribuzione errori (istogramma)
        # ═══════════════════════════════════════════════════════════════════════════════
        ax3 = fig.add_subplot(gs[1, 1])
        n, bins, patches = ax3.hist(errors, bins=50, color='steelblue', alpha=0.7, edgecolor='white')
        
        # Colora le barre in base al segno
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor('#c0392b')  # rosso per sottostima
            else:
                patch.set_facecolor('#27ae60')  # verde per sovrastima
        
        ax3.axvline(x=0, color='black', linestyle='-', linewidth=2)
        ax3.axvline(x=errors.mean(), color='red', linestyle='--', linewidth=1.5, label=f'Mean: {errors.mean():.6f}')
        ax3.axvline(x=np.median(errors), color='orange', linestyle=':', linewidth=1.5, label=f'Median: {np.median(errors):.6f}')
        
        ax3.set_title('Error Distribution', fontsize=11, fontweight='bold')
        ax3.set_xlabel('Prediction Error (Predicted - Actual)')
        ax3.set_ylabel('Frequency')
        ax3.legend(loc='upper right', fontsize=8)
        ax3.grid(True, alpha=0.3)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 4: Box plot errori e percentili
        # ═══════════════════════════════════════════════════════════════════════════════
        ax4 = fig.add_subplot(gs[1, 2])
        bp = ax4.boxplot([errors, pct_errors], labels=['Absolute Error', 'Percentage Error (%)'], 
                         patch_artist=True, notch=True)
        bp['boxes'][0].set_facecolor('#3498db')
        bp['boxes'][1].set_facecolor('#e74c3c')
        
        ax4.set_title('Error Statistics', fontsize=11, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # Aggiungi statistiche
        stats_text = f"Error Stats:\n" \
                     f"Std: {errors.std():.6f}\n" \
                     f"P10: {np.percentile(errors, 10):.6f}\n" \
                     f"P90: {np.percentile(errors, 90):.6f}"
        ax4.text(1.02, 0.98, stats_text, transform=ax4.transAxes, fontsize=8, va='top',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 5: Errore nel tempo
        # ═══════════════════════════════════════════════════════════════════════════════
        ax5 = fig.add_subplot(gs[2, 0:2])
        ax5.fill_between(range(len(errors)), errors, 0, where=(errors >= 0), 
                         color='#27ae60', alpha=0.6, label='Overestimate')
        ax5.fill_between(range(len(errors)), errors, 0, where=(errors < 0), 
                         color='#c0392b', alpha=0.6, label='Underestimate')
        ax5.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        # Rolling mean
        window = min(20, len(errors) // 5)
        if window > 1:
            rolling_mean = pd.Series(errors).rolling(window=window, center=True).mean()
            ax5.plot(rolling_mean, 'b-', linewidth=2, label=f'Rolling Mean (w={window})')
        
        ax5.set_title('Error Evolution Over Validation Set', fontsize=11, fontweight='bold')
        ax5.set_xlabel('Sample Index')
        ax5.set_ylabel('Prediction Error')
        ax5.legend(loc='upper right', fontsize=8)
        ax5.grid(True, alpha=0.3)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # PANNELLO 6: Riepilogo metriche
        # ═══════════════════════════════════════════════════════════════════════════════
        ax6 = fig.add_subplot(gs[2, 2])
        ax6.axis('off')
        
        # Prepara testo metriche
        reg = metrics.regression
        cls = metrics.classification
        
        summary_text = (
            f"{'═'*35}\n"
            f"   REGRESSION METRICS\n"
            f"{'─'*35}\n"
            f"   RMSE:        {reg.rmse:>12.6f}\n"
            f"   MAE:         {reg.mae:>12.6f}\n"
            f"   MAPE:        {reg.mape:>12.2f}%\n"
            f"   R²:          {reg.r2:>12.4f}\n"
            f"   Mean Δ:      {reg.mean_delta:>12.6f}\n"
            f"   Std Δ:       {reg.std_delta:>12.6f}\n"
            f"{'═'*35}\n"
            f"   DIRECTION METRICS\n"
            f"{'─'*35}\n"
            f"   Dir Accuracy:{cls.direction_accuracy:>12.1%}\n"
            f"   UP Precision:{cls.up_precision:>12.1%}\n"
            f"   DOWN Prec:   {cls.down_precision:>12.1%}\n"
            f"   Profitable:  {cls.profitable_signals:>12.1%}\n"
            f"{'═'*35}\n"
            f"   Validation Samples: {len(y_actual):>7}\n"
            f"{'═'*35}"
        )
        
        ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes, fontsize=9, va='top',
                 family='monospace', bbox=dict(boxstyle='round', facecolor='#f8f9fa', 
                                               edgecolor='#dee2e6', alpha=0.95))
        
        # Footer
        fig.text(0.99, 0.01, f'Generated by PROFETA Universal v{__version__} | BilliDynamics™', 
                 ha='right', va='bottom', fontsize=8, style='italic', alpha=0.7)
        fig.text(0.01, 0.01, f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                 ha='left', va='bottom', fontsize=8, alpha=0.7)
        
        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        p = self.out_dir / fn
        plt.savefig(p, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        self.logger.info(f"Validation comparison graph saved: {p}")
        return p

class TemporalAligner:
    def __init__(self, gran: Granularity, logger=None):
        self.gran, self.logger = gran, logger or logging.getLogger(self.__class__.__name__)
    
    def align_to_next(self, ts: pd.Timestamp) -> pd.Timestamp:
        if not isinstance(ts, pd.Timestamp): ts = pd.Timestamp(ts)
        if ts.tzinfo: ts = ts.tz_convert(None)  # rimuove tz da timestamp tz-aware
        aligned = ts.ceil(self.gran.pandas_code)
        return aligned + pd.Timedelta(seconds=self.gran.seconds) if aligned == ts else aligned
    
    def generate_aligned(self, start, num_periods) -> pd.DatetimeIndex:
        return pd.date_range(self.align_to_next(start), periods=num_periods, freq=self.gran.pandas_code)


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════════

class PROFETAEngine:
    """
    ╔══════════════════════════════════════════════════════════════════════════════════════╗
    ║     PROFETA v5.7.0 - ENTERPRISE FORECASTING ENGINE                                  ║
    ╠══════════════════════════════════════════════════════════════════════════════════════╣
    ║  Features:                                                                           ║
    ║  • Pure regression forecasting with LSTM ensemble                                    ║
    ║  • Nested conformal prediction (TRAIN/CALIB/TEST split)                              ║
    ║  • ASYMMETRIC horizon-aware calibrated intervals (v5.7.0)                            ║
    ║  • Per-horizon coverage diagnostics                                                  ║
    ║  • Walk-forward validation                                                           ║
    ║  • Drift monitoring                                                                  ║
    ║                                                                                      ║
    ║  v5.7.0 ASYMMETRIC INTERVALS:                                                        ║
    ║  Instead of symmetric |y - ŷ| → ±q, we use signed errors (y - ŷ):                    ║
    ║    • q_lower = Quantile(y - ŷ, α/2)    → typically negative (underestimate)         ║
    ║    • q_upper = Quantile(y - ŷ, 1-α/2)  → typically positive (overestimate)          ║
    ║    • Interval: [ŷ + q_lower, ŷ + q_upper]                                           ║
    ║                                                                                      ║
    ║  This captures distribution asymmetry and bias, improving coverage for all levels.   ║
    ║                                                                                      ║
    ║  GARANZIA: Coverage verificata out-of-sample su dati mai visti.                      ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝
    """
    def __init__(self, domain_profile: DomainProfile, gran_config: GranularityConfig,
                 train_config: TrainingConfig, cls_config: ClassificationConfig,
                 fusion_config: FusionConfig, pred_config: PredictionConfig,
                 model_configs: List[ModelConfig], logger: Optional[logging.Logger] = None,
                 report_config: Optional[ReportConfig] = None):
        self.domain_profile, self.gran_config = domain_profile, gran_config
        self.train_config, self.cls_config = train_config, cls_config
        self.fusion_config, self.pred_config = fusion_config, pred_config
        self.model_configs = model_configs
        self.report_config = report_config or ReportConfig()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        self.preprocessor: Optional[DataPreprocessor] = None
        self.seq_prep: Optional[SequencePreparator] = None
        self.labeler: Optional[TrendLabeler] = None
        self.ensemble: Optional[EnsembleManager] = None
        self.fusion: Optional[FusionEngine] = None
        self.output_gen: Optional[OutputGenerator] = None
        self.aligner: Optional[TemporalAligner] = None
        self._processed_data: Optional[pd.DataFrame] = None
        self._metrics: Optional[HybridMetrics] = None
        self._validation_data: Optional[Dict] = None
        self._model_stats: List[Dict] = []
        self._execution_times: Dict[str, float] = {}
        
        # Enterprise Features (v5.6.0)
        self.conformal: Optional[ConformalPredictor] = None
        self.drift_monitor: Optional[DriftMonitor] = None
        self._walk_forward_result: Optional[WalkForwardResult] = None
        
        # v5.6.0 - Nested split metadata
        self._split_info: Optional[Dict] = None
        self._coverage_verification: Optional[Dict] = None
    
    def train(self, data_path, load_frac=1.0, run_walk_forward: bool = False) -> HybridMetrics:
        """
        PROFETA v5.6.0 - Enterprise Training with Nested Conformal Prediction
        
        Se use_nested_split=True (default):
            |---- TRAIN ----|---- CALIB ----|---- TEST ----|
                  60%             20%            20%
            
            - Scaler fittato SOLO su TRAIN (no data leakage)
            - Model trainato SOLO su TRAIN
            - Conformal calibrato SOLO su CALIB (out-of-sample calibration)
            - Metriche calcolate SOLO su TEST (truly held-out evaluation)
            - Coverage verificata SOLO su TEST (out-of-sample guarantee)
        """
        self.logger.info("=" * 70)
        self.logger.info("PROFETA UNIVERSAL v5.6.0 - ENTERPRISE TRAINING")
        self.logger.info("=" * 70)
        
        # Load
        df = pd.read_csv(data_path)
        if load_frac < 1.0: df = df.iloc[:int(len(df) * load_frac)]
        self.logger.info(f"Loaded {len(df)} records from {data_path}")
        
        # Preprocess (features, no scaling yet)
        self.preprocessor = DataPreprocessor(self.gran_config, self.domain_profile, self.logger)
        proc_df = self.preprocessor.process(df, self.pred_config.timestamp_column, self.pred_config.target_column)
        self._processed_data = proc_df
        
        # Labels - Solo se classificazione abilitata (deprecated in v5.3+)
        if self.cls_config.enabled:
            self.labeler = TrendLabeler(self.cls_config.threshold_mode, self.cls_config.threshold,
                                        self.cls_config.prediction_horizon, self.cls_config.num_classes,
                                        self.cls_config.vol_window, logger=self.logger)
            labels, _ = self.labeler.compute_labels(proc_df[self.pred_config.target_column])
            proc_df['trend_label'] = labels
            proc_df = proc_df.dropna()
        else:
            proc_df['trend_label'] = 1
            self.labeler = None
        
        feat_names = self.preprocessor.feature_names
        max_seq_len = max(c.sequence_length for c in self.model_configs)
        self.logger.info(f"Ensemble sequence lengths: {sorted(set(c.sequence_length for c in self.model_configs))}, using max={max_seq_len}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # NESTED CONFORMAL PREDICTION SPLIT (v5.6.0)
        # ═══════════════════════════════════════════════════════════════════════════
        
        if self.train_config.use_nested_split:
            return self._train_nested_split(proc_df, feat_names, max_seq_len, run_walk_forward)
        else:
            return self._train_legacy_split(proc_df, feat_names, max_seq_len, run_walk_forward)
    
    def _train_nested_split(self, proc_df: pd.DataFrame, feat_names: List[str], 
                            max_seq_len: int, run_walk_forward: bool) -> HybridMetrics:
        """
        NESTED CONFORMAL PREDICTION (v5.6.0)
        
        Split temporale rigoroso:
        |---- TRAIN ----|---- CALIB ----|---- TEST ----|
        
        GARANZIA: Coverage verificata out-of-sample su dati mai visti.
        """
        self.logger.info("=" * 70)
        self.logger.info("NESTED CONFORMAL PREDICTION SPLIT (v5.6.0)")
        self.logger.info("=" * 70)
        
        n = len(proc_df)
        train_ratio = self.train_config.train_ratio
        calib_ratio = self.train_config.calib_ratio
        test_ratio = self.train_config.test_ratio
        
        # Split indices
        train_end = int(n * train_ratio)
        calib_end = int(n * (train_ratio + calib_ratio))
        
        # Split dataframes
        df_train = proc_df.iloc[:train_end].copy()
        df_calib = proc_df.iloc[train_end:calib_end].copy()
        df_test = proc_df.iloc[calib_end:].copy()
        
        self.logger.info(f"TRAIN: {len(df_train)} samples ({train_ratio:.0%}) - indices [0:{train_end}]")
        self.logger.info(f"CALIB: {len(df_calib)} samples ({calib_ratio:.0%}) - indices [{train_end}:{calib_end}]")
        self.logger.info(f"TEST:  {len(df_test)} samples ({test_ratio:.0%}) - indices [{calib_end}:{n}]")
        
        # Salva metadata split
        self._split_info = {
            'method': 'nested_conformal',
            'train_samples': len(df_train),
            'calib_samples': len(df_calib),
            'test_samples': len(df_test),
            'train_ratio': train_ratio,
            'calib_ratio': calib_ratio,
            'test_ratio': test_ratio,
            'train_end_idx': train_end,
            'calib_end_idx': calib_end
        }
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 1: FIT SCALER SOLO SU TRAIN (NO DATA LEAKAGE!)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 1: Fitting scaler on TRAIN only (no data leakage)")
        
        self.seq_prep = SequencePreparator(max_seq_len, feat_names,
                                           self.pred_config.target_column, None, logger=self.logger)
        self.seq_prep.fit(df_train)  # FIT SOLO SU TRAIN!
        
        self.logger.info(f"  Scaler fitted on {len(df_train)} TRAIN samples")
        self.logger.info(f"  Scale factor: {self.seq_prep.get_scale_factor():.4f}")
        self.logger.info(f"  Center: {self.seq_prep.get_center():.2f}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 2: TRANSFORM ALL SETS (using scaler fitted on TRAIN)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 2: Transforming all sets with TRAIN-fitted scaler")
        
        X_train_full, y_train_full = self.seq_prep.transform(df_train)
        last_prices_train = np.array(self.seq_prep._last_prices.copy())
        
        X_calib, y_calib = self.seq_prep.transform(df_calib)
        last_prices_calib = np.array(self.seq_prep._last_prices.copy())
        
        X_test, y_test = self.seq_prep.transform(df_test)
        last_prices_test = np.array(self.seq_prep._last_prices.copy())
        
        self.logger.info(f"  X_train: {X_train_full.shape}, X_calib: {X_calib.shape}, X_test: {X_test.shape}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 3: TRAIN MODEL SOLO SU TRAIN (with internal validation for early stopping)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 3: Training model on TRAIN only")
        
        # Usa una porzione di TRAIN per validation interna (early stopping)
        internal_val_ratio = 0.15  # 15% di TRAIN per early stopping
        internal_split = int(len(X_train_full) * (1 - internal_val_ratio))
        
        X_train = X_train_full[:internal_split]
        y_train = y_train_full[:internal_split]
        X_train_val = X_train_full[internal_split:]
        y_train_val = y_train_full[internal_split:]
        
        self.logger.info(f"  Training split: {len(X_train)} train + {len(X_train_val)} internal validation")
        
        # Update model configs
        for c in self.model_configs:
            c.num_features = len(feat_names)
        
        # Train ensemble
        self.ensemble = EnsembleManager(self.model_configs, self.train_config, self.logger)
        self.ensemble.build_all()
        histories = self.ensemble.train_all(X_train, y_train, X_train_val, y_train_val)
        
        # Raccogli statistiche dei modelli
        self._model_stats = []
        for i, m in enumerate(self.ensemble.models):
            hist = histories.get(f'model_{i+1}', {})
            epochs_trained = len(hist.get('loss', [])) if hist else 0
            final_loss = hist.get('val_loss', hist.get('loss', [0]))[-1] if hist else 0
            model_delta = self.ensemble._model_deltas.get(m.config.model_id, 0)
            
            self._model_stats.append({
                'model_id': m.config.model_id,
                'architecture': m.config.architecture.value,
                'sequence_length': m.config.sequence_length,
                'lstm_units': m.config.lstm_units,
                'dropout_rate': m.config.dropout_rate,
                'bidirectional': m.config.use_bidirectional,
                'use_attention': m.config.use_attention,
                'num_lstm_layers': m.config.num_lstm_layers,
                'epochs': epochs_trained,
                'final_loss': float(final_loss),
                'delta_mean': float(model_delta),
                'delta_std': 0.0
            })
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 4: CALIBRATE CONFORMAL SOLO SU CALIB (OUT-OF-SAMPLE, ASYMMETRIC)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 4: Calibrating conformal on CALIB only (out-of-sample, asymmetric)")
        
        max_horizon = self.pred_config.num_future_steps
        usable_calib = len(X_calib) - max_horizon
        
        # Predict su CALIB
        calib_pred, calib_std = self.ensemble.predict_ensemble(X_calib)
        y_calib_orig = self.seq_prep.inverse_transform_target(y_calib, last_prices_calib)
        calib_pred_orig = self.seq_prep.inverse_transform_target(calib_pred, last_prices_calib)
        
        # Variabili per coverage per-horizon
        y_true_by_h_calib = None
        y_pred_by_h_calib = None
        
        if usable_calib >= 50:
            self.logger.info(f"  Generating multi-horizon calibration data (h=1..{max_horizon})...")
            
            calibrator = MultiHorizonCalibrator(
                max_horizon=max_horizon,
                stride=max(1, usable_calib // 300),
                logger=self.logger
            )
            
            try:
                y_true_by_h_calib, y_pred_by_h_calib = calibrator.generate_calibration_data(
                    X_val=X_calib,
                    y_val_prices=y_calib_orig,
                    ensemble_predict_fn=self.ensemble.predict_ensemble,
                    seq_prep=self.seq_prep,
                    decay=self.pred_config.future_decay,
                    progress=True
                )
                
                # v5.7.0 - Asymmetric conformal prediction
                self.conformal = ConformalPredictor(
                    coverages=[0.50, 0.90, 0.95],
                    max_horizon=max_horizon,
                    use_asymmetric=True,  # v5.7.0 - Intervalli asimmetrici
                    logger=self.logger
                )
                self.conformal.calibrate_horizon_aware(y_true_by_h_calib, y_pred_by_h_calib)
                
            except Exception as e:
                self.logger.warning(f"  Horizon-aware calibration failed: {e}, using legacy")
                self.conformal = ConformalPredictor(coverages=[0.50, 0.90, 0.95], max_horizon=max_horizon, 
                                                   use_asymmetric=False, logger=self.logger)
                self.conformal.calibrate(y_calib_orig, calib_pred_orig)
        else:
            self.logger.info(f"  Not enough CALIB data ({usable_calib} < 50), using legacy calibration")
            self.conformal = ConformalPredictor(coverages=[0.50, 0.90, 0.95], max_horizon=max_horizon, 
                                               use_asymmetric=False, logger=self.logger)
            self.conformal.calibrate(y_calib_orig, calib_pred_orig)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 5: EVALUATE METRICS SOLO SU TEST (TRULY HELD-OUT!)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 5: Evaluating metrics on TEST only (truly held-out)")
        
        # Predict su TEST
        test_pred, test_std = self.ensemble.predict_ensemble(X_test)
        y_test_orig = self.seq_prep.inverse_transform_target(y_test, last_prices_test)
        test_pred_orig = self.seq_prep.inverse_transform_target(test_pred, last_prices_test)
        
        # Metriche su TEST
        reg_m = MetricsCalculator.calc_regression(y_test_orig, test_pred_orig)
        y_direction_actual = np.sign(y_test)
        y_direction_pred = np.sign(test_pred)
        dir_m = MetricsCalculator.calc_direction_from_regression(y_direction_actual, y_direction_pred)
        
        self._metrics = HybridMetrics(reg_m, dir_m)
        
        self.logger.info(f"  TEST R²: {reg_m.r2:.4f}")
        self.logger.info(f"  TEST RMSE: ${reg_m.rmse:.2f}")
        self.logger.info(f"  TEST Direction Accuracy: {dir_m.direction_accuracy:.1%}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 6: VERIFY COVERAGE SU TEST (OUT-OF-SAMPLE GUARANTEE!)
        # ═══════════════════════════════════════════════════════════════════════════
        self.logger.info("-" * 70)
        self.logger.info("STEP 6: Verifying coverage on TEST (out-of-sample guarantee)")
        self.logger.info("=" * 70)
        
        # Coverage verification globale su TEST (dati MAI visti durante calibrazione!)
        test_coverage = self.conformal.evaluate_coverage(y_test_orig, test_pred_orig)
        
        # v5.7.0 - Coverage verification PER-HORIZON
        horizon_predictor = self.conformal.get_horizon_aware_predictor()
        per_horizon_coverage = {}
        
        if horizon_predictor and y_true_by_h_calib:
            # Genera dati multi-horizon per TEST
            usable_test = len(X_test) - max_horizon
            if usable_test >= 30:
                test_calibrator = MultiHorizonCalibrator(
                    max_horizon=max_horizon,
                    stride=max(1, usable_test // 200),
                    logger=self.logger
                )
                try:
                    y_true_by_h_test, y_pred_by_h_test = test_calibrator.generate_calibration_data(
                        X_val=X_test,
                        y_val_prices=y_test_orig,
                        ensemble_predict_fn=self.ensemble.predict_ensemble,
                        seq_prep=self.seq_prep,
                        decay=self.pred_config.future_decay,
                        progress=False
                    )
                    per_horizon_coverage = horizon_predictor.evaluate_coverage(y_true_by_h_test, y_pred_by_h_test)
                except Exception as e:
                    self.logger.warning(f"  Per-horizon coverage failed: {e}")
        
        self._coverage_verification = {
            'method': 'out_of_sample_asymmetric' if self.conformal.use_asymmetric else 'out_of_sample_symmetric',
            'test_samples': len(y_test_orig),
            'coverages': {f'{k:.0%}': v for k, v in test_coverage.items()},
            'nominal_vs_empirical': {f'{k:.0%}': {'nominal': k, 'empirical': v, 'gap': abs(v - k)} 
                                      for k, v in test_coverage.items()},
            'per_horizon': {f'h{h}': {f'{c:.0%}': v for c, v in covs.items()} 
                           for h, covs in per_horizon_coverage.items()} if per_horizon_coverage else {}
        }
        
        # Report globale
        mode_str = "ASYMMETRIC" if self.conformal.use_asymmetric else "SYMMETRIC"
        self.logger.info("╔══════════════════════════════════════════════════════════════════════╗")
        self.logger.info(f"║     OUT-OF-SAMPLE COVERAGE VERIFICATION (v5.7.0 {mode_str})        ║")
        self.logger.info("╠══════════════════════════════════════════════════════════════════════╣")
        for cov, emp in test_coverage.items():
            gap = abs(emp - cov)
            status = "✓" if gap <= 0.05 else "⚠" if gap <= 0.10 else "✗"
            self.logger.info(f"║  {status} {cov:>3.0%} nominal → {emp:>5.1%} empirical (gap: {gap:>4.1%})             ║")
        self.logger.info("╠══════════════════════════════════════════════════════════════════════╣")
        self.logger.info("║  Coverage verified on data NEVER seen during calibration!           ║")
        self.logger.info("╚══════════════════════════════════════════════════════════════════════╝")
        
        # v5.7.0 - Report per-horizon coverage
        if per_horizon_coverage:
            self.logger.info("")
            self.logger.info("┌────────────────────────────────────────────────────────────────────────┐")
            self.logger.info("│              PER-HORIZON COVERAGE (v5.7.0 DIAGNOSTICS)                │")
            self.logger.info("├────────────────────────────────────────────────────────────────────────┤")
            self.logger.info("│  Horizon    50% nom→emp    90% nom→emp    95% nom→emp                 │")
            self.logger.info("├────────────────────────────────────────────────────────────────────────┤")
            for h in [1, 6, 12, 24, 48, 72]:
                if h in per_horizon_coverage:
                    c50 = per_horizon_coverage[h].get(0.50, 0)
                    c90 = per_horizon_coverage[h].get(0.90, 0)
                    c95 = per_horizon_coverage[h].get(0.95, 0)
                    s50 = "✓" if abs(c50 - 0.50) <= 0.08 else "✗"
                    s90 = "✓" if abs(c90 - 0.90) <= 0.05 else "⚠" if abs(c90 - 0.90) <= 0.10 else "✗"
                    s95 = "✓" if abs(c95 - 0.95) <= 0.05 else "⚠" if abs(c95 - 0.95) <= 0.10 else "✗"
                    self.logger.info(f"│  h{h:>2}:       {s50} {c50:>5.1%}         {s90} {c90:>5.1%}         {s95} {c95:>5.1%}                │")
            self.logger.info("└────────────────────────────────────────────────────────────────────────┘")
        
        # Drift Monitor (fit su CALIB, per monitorare TEST)
        self.drift_monitor = DriftMonitor(z_threshold=2.0, logger=self.logger)
        self.drift_monitor.fit_baseline(y_calib_orig, calib_pred_orig)
        
        # Walk-Forward (opzionale)
        if run_walk_forward:
            self.logger.info("Running Walk-Forward Validation...")
            wf_validator = WalkForwardValidator(n_splits=5, min_train_pct=0.5, test_pct=0.1, logger=self.logger)
            def _build_wf_model(X_tr, y_tr):
                from sklearn.linear_model import Ridge
                model = Ridge(alpha=1.0)
                model.fit(X_tr.reshape(X_tr.shape[0], -1), y_tr)
                class _Wrapper:
                    def __init__(self, m): self.m = m
                    def predict(self, X): return self.m.predict(X.reshape(X.shape[0], -1))
                return _Wrapper(model)
            self._walk_forward_result = wf_validator.validate(X_train_full, y_train_full, _build_wf_model)
            self.logger.info(self._walk_forward_result.summary())
        
        # Salva dati per grafici (usa TEST)
        self._validation_data = {
            'y_actual': y_test_orig,
            'y_predicted': test_pred_orig,
            'timestamps': df_test.index[max_seq_len:] if len(df_test.index) > max_seq_len else None,
            'conformal_stats': self.conformal.get_stats(),
            'drift_baseline': self.drift_monitor.get_baseline(),
            'split_info': self._split_info,
            'coverage_verification': self._coverage_verification
        }
        
        # Genera grafico
        if self.pred_config.generate_graph:
            try:
                self.output_gen = OutputGenerator(self.pred_config.output_dir, self.logger)
                val_graph_path = self.output_gen.generate_validation_graph(
                    y_test_orig, test_pred_orig, self._metrics,
                    val_timestamps=None,
                    fn="test_validation_comparison.png"
                )
                self.logger.info(f"Test validation graph generated: {val_graph_path}")
            except Exception as e:
                self.logger.warning(f"Failed to generate validation graph: {e}")
        
        # Report finale con info asimmetria v5.7.0
        horizon_pred = self.conformal.get_horizon_aware_predictor()
        if horizon_pred and horizon_pred.use_asymmetric:
            bias = horizon_pred._mean_bias
            skew = horizon_pred._mean_skewness
            asym_info = f" (bias={bias:+.1f}, skew={skew:+.2f})"
        else:
            asym_info = ""
        
        self.logger.info("=" * 70)
        self.logger.info(f"TRAINING COMPLETE (ASYMMETRIC CONFORMAL v5.7.0)")
        self.logger.info(f"  TEST R²: {reg_m.r2:.4f}, TEST Dir Accuracy: {dir_m.direction_accuracy:.1%}")
        self.logger.info(f"  90% Coverage (out-of-sample): {test_coverage.get(0.90, 0):.1%}{asym_info}")
        return self._metrics
    
    def _train_legacy_split(self, proc_df: pd.DataFrame, feat_names: List[str],
                            max_seq_len: int, run_walk_forward: bool) -> HybridMetrics:
        """
        LEGACY SPLIT (v5.4.0 compatible)
        
        |---- TRAIN ----|---- VAL ----|
        
        Mantenuto per backward compatibility.
        """
        self.logger.info("Using LEGACY split (v5.4.0 compatible)")
        self.logger.info("NOTE: For out-of-sample guarantees, set use_nested_split=True")
        
        self._split_info = {'method': 'legacy', 'train_test_split': self.train_config.train_test_split}
        
        # Sequences
        self.seq_prep = SequencePreparator(max_seq_len, feat_names,
                                           self.pred_config.target_column, None, logger=self.logger)
        self.seq_prep.fit(proc_df)  # Fit su tutto (legacy behavior)
        X, y_reg = self.seq_prep.transform(proc_df)
        
        # Split
        split = int(len(X) * self.train_config.train_test_split)
        X_train, X_val = X[:split], X[split:]
        y_reg_train, y_reg_val = y_reg[:split], y_reg[split:]
        self.logger.info(f"Split: Train={len(X_train)}, Val={len(X_val)}")
        
        # Update configs
        for c in self.model_configs:
            c.num_features = len(feat_names)
        
        # Train ensemble
        self.ensemble = EnsembleManager(self.model_configs, self.train_config, self.logger)
        self.ensemble.build_all()
        histories = self.ensemble.train_all(X_train, y_reg_train, X_val, y_reg_val)
        
        # Model stats
        self._model_stats = []
        for i, m in enumerate(self.ensemble.models):
            hist = histories.get(f'model_{i+1}', {})
            epochs_trained = len(hist.get('loss', [])) if hist else 0
            final_loss = hist.get('val_loss', hist.get('loss', [0]))[-1] if hist else 0
            model_delta = self.ensemble._model_deltas.get(m.config.model_id, 0)
            self._model_stats.append({
                'model_id': m.config.model_id,
                'architecture': m.config.architecture.value,
                'sequence_length': m.config.sequence_length,
                'lstm_units': m.config.lstm_units,
                'dropout_rate': m.config.dropout_rate,
                'bidirectional': m.config.use_bidirectional,
                'use_attention': m.config.use_attention,
                'num_lstm_layers': m.config.num_lstm_layers,
                'epochs': epochs_trained,
                'final_loss': float(final_loss),
                'delta_mean': float(model_delta),
                'delta_std': 0.0
            })
        
        # Evaluate
        reg_pred, reg_std = self.ensemble.predict_ensemble(X_val)
        last_prices_val = np.array(self.seq_prep._last_prices[split:])
        reg_pred_orig = self.seq_prep.inverse_transform_target(reg_pred, last_prices_val)
        y_reg_val_orig = self.seq_prep.inverse_transform_target(y_reg_val, last_prices_val)
        
        reg_m = MetricsCalculator.calc_regression(y_reg_val_orig, reg_pred_orig)
        y_direction_actual = np.sign(y_reg_val)
        y_direction_pred = np.sign(reg_pred)
        dir_m = MetricsCalculator.calc_direction_from_regression(y_direction_actual, y_direction_pred)
        
        self._metrics = HybridMetrics(reg_m, dir_m)
        
        # Conformal (legacy - calibrate and evaluate on same data)
        max_horizon = self.pred_config.num_future_steps
        self.conformal = ConformalPredictor(coverages=[0.50, 0.90, 0.95], max_horizon=max_horizon, logger=self.logger)
        self.conformal.calibrate(y_reg_val_orig, reg_pred_orig)
        empirical_coverage = self.conformal.evaluate_coverage(y_reg_val_orig, reg_pred_orig)
        self.logger.info(f"Empirical coverage (in-sample): {', '.join(f'{k:.0%}→{v:.1%}' for k,v in empirical_coverage.items())}")
        
        # Drift Monitor
        self.drift_monitor = DriftMonitor(z_threshold=2.0, logger=self.logger)
        self.drift_monitor.fit_baseline(y_reg_val_orig, reg_pred_orig)
        
        # Walk-Forward (opzionale)
        if run_walk_forward:
            self.logger.info("Running Walk-Forward Validation...")
            wf_validator = WalkForwardValidator(n_splits=5, min_train_pct=0.5, test_pct=0.1, logger=self.logger)
            def _build_wf_model(X_tr, y_tr):
                from sklearn.linear_model import Ridge
                model = Ridge(alpha=1.0)
                model.fit(X_tr.reshape(X_tr.shape[0], -1), y_tr)
                class _Wrapper:
                    def __init__(self, m): self.m = m
                    def predict(self, X): return self.m.predict(X.reshape(X.shape[0], -1))
                return _Wrapper(model)
            self._walk_forward_result = wf_validator.validate(X, y_reg, _build_wf_model)
            self.logger.info(self._walk_forward_result.summary())
        
        # Salva dati validation
        self._validation_data = {
            'y_actual': y_reg_val_orig,
            'y_predicted': reg_pred_orig,
            'timestamps': proc_df.index[split + max_seq_len:] if len(proc_df.index) > split + max_seq_len else None,
            'conformal_stats': self.conformal.get_stats(),
            'drift_baseline': self.drift_monitor.get_baseline()
        }
        
        # Genera grafico
        if self.pred_config.generate_graph:
            try:
                self.output_gen = OutputGenerator(self.pred_config.output_dir, self.logger)
                val_graph_path = self.output_gen.generate_validation_graph(
                    y_reg_val_orig, reg_pred_orig, self._metrics,
                    val_timestamps=None,
                    fn="validation_comparison.png"
                )
                self.logger.info(f"Validation graph generated: {val_graph_path}")
            except Exception as e:
                self.logger.warning(f"Failed to generate validation graph: {e}")
        
        self.logger.info("=" * 70)
        self.logger.info(f"TRAINING COMPLETE (LEGACY) - R²: {reg_m.r2:.4f}, Dir Accuracy: {dir_m.direction_accuracy:.1%}")
        self.logger.info(f"Conformal Intervals: 90% width = ±${self.conformal.quantiles.get(0.90, 0):.2f}")
        return self._metrics
    
    def predict(self, data_path=None, df=None) -> List[FusionResult]:
        """
        PROFETA v5.4.0 - Enterprise Prediction with Conformal Intervals
        """
        self.logger.info("=" * 70)
        self.logger.info("PROFETA UNIVERSAL v5.4 - ENTERPRISE PREDICTION")
        
        if self.ensemble is None: raise StateError("Not trained")
        if df is None:
            if data_path is None: raise ValidationError("Need data")
            df = pd.read_csv(data_path)
        
        proc_df = self.preprocessor.process(df, self.pred_config.timestamp_column, self.pred_config.target_column)
        
        X, y_reg = self.seq_prep.transform(proc_df)
        reg_pred, reg_std = self.ensemble.predict_ensemble(X)
        
        last_prices = np.array(self.seq_prep._last_prices)
        reg_pred_orig = self.seq_prep.inverse_transform_target(reg_pred, last_prices)
        # Converti std in scala originale usando metodo canonico
        reg_std_orig = reg_std * self.seq_prep.get_scale_factor()
        
        ts = proc_df.index[self.seq_prep.seq_len:]
        # FIX v5.7.1: usa last_prices come riferimento per il trend
        # Prima usava prices[seq_len:] che è il prezzo REALE successivo,
        # causando il calcolo del trend sull'ERRORE invece che sul DELTA PREDETTO
        curr_vals = last_prices
        
        self.fusion = FusionEngine(self.fusion_config, self.logger)
        results = self.fusion.fuse(pd.DatetimeIndex(ts), curr_vals, reg_pred_orig, 
                                   ensemble_std=reg_std_orig)
        
        # Applica intervalli conformal se calibrato
        if self.conformal and self.conformal._calibrated:
            for i, r in enumerate(results):
                intervals = self.conformal.predict_all_intervals(r.predicted_value)
                if 0.50 in intervals:
                    r.interval_50 = (intervals[0.50].lower, intervals[0.50].upper)
                if 0.90 in intervals:
                    r.interval_90 = (intervals[0.90].lower, intervals[0.90].upper)
                if 0.95 in intervals:
                    r.interval_95 = (intervals[0.95].lower, intervals[0.95].upper)
        
        # Future predictions
        future = self._predict_future(proc_df, reg_pred_orig[-1])
        results.extend(future)
        return results
    
    def _predict_future(self, proc_df, last_reg) -> List[FusionResult]:
        self.aligner = TemporalAligner(self.gran_config.output_granularity, self.logger)
        last_ts = proc_df.index[-1]
        future_ts = self.aligner.generate_aligned(last_ts, self.pred_config.num_future_steps)
        self.logger.info(f"Generating {len(future_ts)} future predictions")
        
        feat_cols = self.preprocessor.feature_names
        seq_len = self.seq_prep.seq_len
        last_feats = proc_df[feat_cols].values[-seq_len:]
        last_feats_scaled = self.seq_prep.feature_scaler.transform(last_feats)
        curr_seq = last_feats_scaled.copy()
        curr_val = proc_df[self.pred_config.target_column].values[-1]
        
        # ═══════════════════════════════════════════════════════════════════════════
        # IMPORTANTE: Salva il prezzo iniziale per la classificazione CUMULATIVA
        # Questo assicura che la classe (UP/DOWN/FLAT) rifletta il movimento
        # rispetto all'inizio del forecast, non rispetto allo step precedente
        # ═══════════════════════════════════════════════════════════════════════════
        initial_val = curr_val
        
        # ═══════════════════════════════════════════════════════════════════════════
        # VOLATILITY-ADAPTIVE PREDICTION (v5.1.0)
        # ═══════════════════════════════════════════════════════════════════════════
        prices = proc_df[self.pred_config.target_column]
        vol_analyzer = VolatilityAnalyzer(
            lookback=min(20, len(prices) // 2),
            hist_window=min(50, len(prices)),
            min_mult=0.5,
            max_mult=3.0
        )
        vol_state = vol_analyzer.analyze(prices)
        
        self.logger.info(f"Volatility Regime: {vol_state.regime.value} | "
                        f"Z-score: {vol_state.vol_zscore:.2f} | "
                        f"Multiplier: {vol_state.vol_multiplier:.2f} | "
                        f"Adaptive Decay: {vol_state.recommended_decay}")
        
        # Usa decay dinamico basato sul regime di volatilità
        base_decay = vol_state.recommended_decay
        vol_multiplier = vol_state.vol_multiplier
        
        # Aggiorna soglia dinamicamente
        original_threshold = self.fusion_config.delta_threshold_pct
        adaptive_threshold = vol_state.recommended_threshold
        
        results = []
        for i, ts in enumerate(future_ts):
            X = curr_seq.reshape(1, seq_len, -1)
            reg, reg_std = self.ensemble.predict_ensemble(X)
            
            # reg è un delta scalato - converti in prezzo assoluto
            reg_orig = self.seq_prep.inverse_transform_target(reg, np.array([curr_val]))[0]
            
            # Converti std in scala originale usando metodo canonico
            std_orig = self.seq_prep.unscale_delta(float(reg_std[0]))
            
            # ═══════════════════════════════════════════════════════════════════════════
            # ADAPTIVE DECAY: usa il decay raccomandato dal regime di volatilità
            # In regime EXTREME il decay è più basso → predizioni più "aggressive"
            # ═══════════════════════════════════════════════════════════════════════════
            decay = base_decay ** (i + 1)
            
            # Calcola delta e applica volatility multiplier
            delta = reg_orig - curr_val
            delta_adjusted = delta * vol_multiplier
            reg_corr = curr_val + delta_adjusted * decay
            
            # La std aumenta più velocemente in regime volatile
            vol_factor = 1.0 + 0.1 * i * vol_multiplier
            std_corr = std_orig * vol_factor
            
            # Usa soglia adattiva per la fusione
            self.fusion.config.delta_threshold_pct = adaptive_threshold
            
            # ═══════════════════════════════════════════════════════════════════════════
            # TREND CUMULATIVO: usa initial_val per determinare UP/DOWN/FLAT
            # Questo fa sì che un trend costante DOWN venga classificato correttamente
            # anche se ogni singolo step è piccolo
            # ═══════════════════════════════════════════════════════════════════════════
            result = self.fusion._fuse_single(
                ts, initial_val, reg_corr,
                ensemble_std=std_corr,
                volatility_regime=vol_state.regime.value
            )
            
            # ═══════════════════════════════════════════════════════════════════════════
            # APPLICA INTERVALLI CONFORMAL (v5.5.0 - HORIZON-AWARE)
            # Gli intervalli sono ora calibrati SPECIFICAMENTE per ogni orizzonte
            # Non serve più scalare manualmente - la calibrazione è empirica!
            # ═══════════════════════════════════════════════════════════════════════════
            if self.conformal and self.conformal._calibrated:
                horizon = i + 1  # Orizzonte 1-indexed
                
                # Ottieni intervalli calibrati per QUESTO orizzonte specifico
                intervals = self.conformal.predict_all_intervals(reg_corr, horizon=horizon)
                
                for cov, intv in intervals.items():
                    # Gli intervalli sono già calibrati - usa direttamente!
                    if cov == 0.50:
                        result.interval_50 = (intv.lower, intv.upper)
                    elif cov == 0.90:
                        result.interval_90 = (intv.lower, intv.upper)
                    elif cov == 0.95:
                        result.interval_95 = (intv.lower, intv.upper)
                
                # Metadata aggiuntivi (v5.5.0)
                result.horizon = horizon
                result.interval_calibration_n = intv.calibration_n if intervals else 0
            
            results.append(result)
            
            # Aggiorna curr_val per la prossima iterazione (per il calcolo del prezzo)
            curr_val = reg_corr
            
            # Roll della sequenza e aggiorna l'ultima feature
            curr_seq = np.roll(curr_seq, -1, axis=0)
            # Scala il nuovo prezzo usando metodo canonico (niente più branch!)
            new_scaled = self.seq_prep.scale_price(reg_corr)
            curr_seq[-1, 0] = new_scaled
        
        # Ripristina soglia originale
        self.fusion.config.delta_threshold_pct = original_threshold
        
        return results
    
    def check_drift(self, y_true: np.ndarray, y_pred: np.ndarray) -> List[DriftAlert]:
        """
        PROFETA v5.4.0 - Check for drift in production predictions.
        
        Usa questo metodo per monitorare se le performance del modello
        stanno degradando rispetto al baseline stabilito durante il training.
        
        Returns:
            Lista di DriftAlert con eventuali warning/alert
        """
        if self.drift_monitor is None:
            raise StateError("Drift monitor not fitted. Train the model first.")
        
        alerts = self.drift_monitor.check_all(y_true, y_pred)
        
        for alert in alerts:
            if alert.detected:
                self.logger.warning(f"DRIFT ALERT: {alert.message}")
            else:
                self.logger.info(f"Drift check OK: {alert.drift_type}")
        
        return alerts
    
    def get_enterprise_stats(self) -> Dict:
        """Restituisce statistiche Enterprise (conformal, drift, walk-forward)"""
        stats = {}
        
        if self.conformal and self.conformal._calibrated:
            stats['conformal'] = self.conformal.get_stats()
        
        if self.drift_monitor and self.drift_monitor._fitted:
            stats['drift_baseline'] = self.drift_monitor.get_baseline()
        
        if self._walk_forward_result:
            stats['walk_forward'] = self._walk_forward_result.to_dict()
        
        return stats
    
    def generate_output(self, results, hist_df=None, trigger: str = "prediction") -> Dict[str, Path]:
        """
        Genera output (CSV, JSON, grafico, report PDF).
        
        Args:
            results: Lista di FusionResult (include storici + futuri)
            hist_df: DataFrame storico per grafici
            trigger: 'training' o 'prediction' per determinare quando generare il report
        """
        self.output_gen = OutputGenerator(self.pred_config.output_dir, self.logger)
        
        # ══════════════════════════════════════════════════════════════════════════
        # FIX v5.0.1: Estrai SOLO le previsioni future (ultime num_future_steps righe)
        # Il CSV deve contenere solo le previsioni future allineate a output_granularity
        # ══════════════════════════════════════════════════════════════════════════
        num_future = self.pred_config.num_future_steps
        future_results = results[-num_future:] if len(results) > num_future else results
        
        self.logger.info(f"Saving {len(future_results)} future predictions to CSV (out of {len(results)} total)")
        
        outs = {'csv': self.output_gen.generate_csv(
            future_results,  # Solo previsioni future
            custom_path=self.pred_config.output_predictions_path
        )}
        meta = {'domain': self.domain_profile.domain_type.value, 'subtype': self.domain_profile.subtype,
                'num_models': self.ensemble.num_models, 'ensemble_delta': self.ensemble.ensemble_delta,
                'classification_enabled': self.cls_config.enabled}  # Indica se classificazione attiva
        outs['json'] = self.output_gen.generate_json(results, self._metrics, meta)
        if self.pred_config.generate_graph and hist_df is not None:
            outs['graph'] = self.output_gen.generate_graph(
                hist_df[self.pred_config.target_column].values, hist_df.index, results, self._metrics)
        
        # Generazione Report PDF
        if self._should_generate_report(trigger):
            outs['report'] = self._generate_pdf_report(results, outs)
        
        return outs
    
    def _should_generate_report(self, trigger: str) -> bool:
        """Determina se generare il report PDF in base al trigger e alla configurazione"""
        if not self.report_config.enabled:
            return False
        if trigger == "training" and self.report_config.generate_on_training:
            return True
        if trigger == "prediction" and self.report_config.generate_on_prediction:
            return True
        return False
    
    def _generate_pdf_report(self, results, output_paths: Dict) -> Optional[Path]:
        """Genera il report PDF usando profeta_report_generator"""
        try:
            # Import dinamico per evitare dipendenza obbligatoria
            try:
                from profeta_report_generator import (
                    PROFETAReportGenerator, ReportConfig as PDFReportConfig, ReportData,
                    RegressionMetrics as PDFRegMetrics, ClassificationMetrics as PDFClsMetrics,
                    ModelStatistics, PredictionSummary
                )
            except ImportError:
                self.logger.warning("profeta_report_generator.py not found - PDF report skipped")
                return None
            
            self.logger.info("Generating PDF report...")
            
            # Costruisci i dati per il report
            reg_metrics = PDFRegMetrics(
                rmse=self._metrics.regression.rmse if self._metrics else 0,
                mae=self._metrics.regression.mae if self._metrics else 0,
                mape=self._metrics.regression.mape if self._metrics else 0,
                r2=self._metrics.regression.r2 if self._metrics else 0,
                mean_delta=self._metrics.regression.mean_delta if self._metrics else 0,
                std_delta=self._metrics.regression.std_delta if self._metrics else 0
            )
            
            cls_metrics = PDFClsMetrics(
                accuracy=self._metrics.classification.direction_accuracy if self._metrics else 0,
                precision_macro=self._metrics.classification.up_precision if self._metrics else 0,
                recall_macro=self._metrics.classification.down_precision if self._metrics else 0,
                f1_macro=self._metrics.classification.profitable_signals if self._metrics else 0
            )
            
            # Model stats - usa i dati raccolti durante il training
            model_stats = []
            for i, cfg in enumerate(self.model_configs):
                stats = self._model_stats[i] if i < len(self._model_stats) else {}
                model_stats.append(ModelStatistics(
                    model_id=cfg.model_id,
                    sequence_length=cfg.sequence_length,
                    lstm_units=cfg.lstm_units,
                    dropout_rate=cfg.dropout_rate,
                    bidirectional=cfg.use_bidirectional,
                    attention=cfg.use_attention,
                    train_loss=stats.get('final_loss', 0.0),
                    val_loss=stats.get('final_loss', 0.0),
                    delta_mean=stats.get('delta_mean', 0.0),
                    delta_std=stats.get('delta_std', 0.0),
                    epochs_trained=stats.get('epochs', 0),
                    training_time_sec=0.0
                ))
            
            # Prediction summary (v5.2.0 Pure Forecast)
            pred_summary = None
            if results:
                # Trend distribution invece di signal distribution
                trend_dist = {'UP': 0, 'DOWN': 0, 'FLAT': 0}
                for r in results:
                    trend = r.trend if hasattr(r, 'trend') else 'FLAT'
                    if trend in trend_dist:
                        trend_dist[trend] += 1
                
                # Dominant trend
                dominant = max(trend_dist, key=trend_dist.get)
                
                # Average confidence
                avg_conf = sum(r.confidence for r in results) / len(results) if results else 0
                
                pred_summary = PredictionSummary(
                    total_predictions=len(results),
                    time_horizon_hours=len(results),
                    first_timestamp=str(results[0].timestamp) if results else "",
                    last_timestamp=str(results[-1].timestamp) if results else "",
                    price_start=results[0].predicted_value if results else 0,
                    price_end_predicted=results[-1].predicted_value if results else 0,
                    price_change_pct=((results[-1].predicted_value - results[0].predicted_value) / 
                                     results[0].predicted_value) if results and results[0].predicted_value else 0,
                    dominant_trend=dominant,
                    avg_confidence=avg_conf,
                    signal_distribution=trend_dist,  # Renamed from signals to trends
                    agreement_rate=1.0  # Always 1.0 in Pure Forecast (no disagreement possible)
                )
            
            # Build ReportData
            report_data = ReportData(
                regression_metrics=reg_metrics,
                classification_metrics=cls_metrics,
                model_stats=model_stats,
                num_models=len(self.model_configs),
                ensemble_delta=self.ensemble.ensemble_delta if self.ensemble else 0,
                prediction_summary=pred_summary,
                config_file="",
                domain_type=self.domain_profile.domain_type.value,
                domain_subtype=self.domain_profile.subtype,
                granularity_input=self.gran_config.input_granularity.value if self.gran_config.input_granularity else "auto",
                granularity_output=self.gran_config.output_granularity.value,
                classification_enabled=self.cls_config.enabled,
                graph_path=str(output_paths.get('graph', '')) if output_paths.get('graph') else "",
                csv_path=str(output_paths.get('csv', '')) if output_paths.get('csv') else "",
                json_path=str(output_paths.get('json', '')) if output_paths.get('json') else "",
                execution_time_sec=self._execution_times.get('total', 0),
                training_time_sec=self._execution_times.get('training', 0),
                prediction_time_sec=self._execution_times.get('prediction', 0)
            )
            
            # Configure report generator - usa TUTTI i parametri da ReportConfig
            # Converti page_size da stringa a tuple
            from reportlab.lib.pagesizes import A4, letter
            page_size_map = {'A4': A4, 'a4': A4, 'letter': letter, 'LETTER': letter}
            page_size_tuple = page_size_map.get(self.report_config.page_size, A4)
            
            pdf_config = PDFReportConfig(
                title=self.report_config.title,
                subtitle=self.report_config.subtitle,
                company=self.report_config.company,
                author=self.report_config.author,
                confidential=self.report_config.confidential,
                include_disclaimer=self.report_config.include_disclaimer,
                include_watermark=self.report_config.include_watermark,
                language=self.report_config.language,
                page_size=page_size_tuple,
                include_model_details=self.report_config.include_model_details,
                include_charts=self.report_config.include_charts,
                include_prediction_graph=self.report_config.include_prediction_graph,
                top_models_count=self.report_config.top_models_count
            )
            
            # Generate report
            generator = PROFETAReportGenerator(
                output_dir=self.report_config.output_dir,
                config=pdf_config
            )
            
            # Build filename
            filename = self.report_config.filename_prefix
            if self.report_config.include_timestamp:
                filename += f"_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            pdf_path = generator.generate(report_data, filename=filename)
            self.logger.info(f"PDF Report generated: {pdf_path}")
            return Path(pdf_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF report: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def save(self, out_dir):
        out_dir = Path(out_dir)
        self.ensemble.save_all(out_dir / "models")
        self.seq_prep.save(out_dir / "prep" / "seq_prep.pkl")
        with open(out_dir / "config.json", 'w') as f:
            json.dump({'version': __version__, 'domain': self.domain_profile.domain_type.value}, f)


# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    SYSTEM & DAEMON
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class SystemConfig:
    log_level: LogLevel = LogLevel.INFO; log_file: Optional[str] = None
    random_seed: int = DEFAULT_RANDOM_SEED; gpu_config: GPUConfig = field(default_factory=GPUConfig)
    output_dir: str = "./output"
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'SystemConfig':
        if not config.has_section('SYSTEM'): return cls()
        s = config['SYSTEM']
        return cls(LogLevel.from_string(s.get('log_level', 'info')), s.get('log_file'),
                   s.getint('random_seed', DEFAULT_RANDOM_SEED), GPUConfig.from_config(config),
                   s.get('output_dir', './output'))
    
    def initialize(self):
        # StreamHandler con encoding robusto per Windows
        stream_handler = logging.StreamHandler()
        if platform.system() == 'Windows':
            # Su Windows, usa errors='replace' per evitare crash su caratteri Unicode
            stream_handler.stream = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace'
            )
        handlers = [stream_handler]
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.log_file, encoding='utf-8'))
        logging.basicConfig(level=self.log_level.value, format=LOG_FORMAT, handlers=handlers)
        os.environ['PYTHONHASHSEED'] = str(self.random_seed)
        np.random.seed(self.random_seed); tf.random.set_seed(self.random_seed)
        GPUManager().initialize(self.gpu_config)

@dataclass
class SchedulerConfig:
    mode: ExecutionMode = ExecutionMode.ONCE
    training_interval_min: int = 60; prediction_interval_min: int = 1440
    train_on_startup: bool = True; predict_on_startup: bool = True
    health_check_sec: int = 60
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'SchedulerConfig':
        if not config.has_section('SCHEDULER'): return cls()
        s = config['SCHEDULER']
        return cls(ExecutionMode.from_string(s.get('mode', 'once')),
                   s.getint('training_interval_minutes', 60), s.getint('prediction_interval_minutes', 1440),
                   s.getboolean('train_on_startup', True), s.getboolean('predict_on_startup', True),
                   s.getint('health_check_interval', 60))


@dataclass
class ReportConfig:
    """Configurazione completa per la generazione dei report PDF enterprise"""
    # === ATTIVAZIONE ===
    enabled: bool = False                          # Abilita/disabilita report PDF
    generate_on_training: bool = True              # Genera report dopo training
    generate_on_prediction: bool = False           # Genera report dopo prediction (attenzione in daemon!)
    
    # === OUTPUT ===
    output_dir: str = "./reports"                  # Directory output report
    filename_prefix: str = "PROFETA_Report"        # Prefisso nome file
    include_timestamp: bool = True                 # Include timestamp nel nome file
    
    # === CONTENUTO TESTUALE ===
    title: str = "PROFETA Analysis Report"         # Titolo report
    subtitle: str = "Universal Multi-Domain Hybrid Prediction System"  # Sottotitolo
    company: str = "BilliDynamics™"                # Nome azienda
    author: str = "PROFETA v5.0"                   # Autore (metadati PDF)
    language: str = "en"                           # Lingua report ('en' o 'it')
    
    # === FORMATTAZIONE ===
    confidential: bool = True                      # Marca come confidenziale
    include_disclaimer: bool = True                # Include disclaimer legale
    include_watermark: bool = False                # Include watermark "DRAFT"
    page_size: str = "A4"                          # Formato pagina: 'A4' o 'letter'
    
    # === CONTENUTO OPZIONALE ===
    include_model_details: bool = True             # Includi analisi dettagliata modelli
    include_charts: bool = True                    # Includi grafici e visualizzazioni
    include_prediction_graph: bool = True          # Embed grafico PNG predizioni
    top_models_count: int = 10                     # Numero modelli da mostrare in classifica
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'ReportConfig':
        if not config.has_section('REPORT'): return cls()
        s = config['REPORT']
        return cls(
            # Attivazione
            enabled=s.getboolean('enabled', False),
            generate_on_training=s.getboolean('generate_on_training', True),
            generate_on_prediction=s.getboolean('generate_on_prediction', False),
            # Output
            output_dir=s.get('output_dir', './reports'),
            filename_prefix=s.get('filename_prefix', 'PROFETA_Report'),
            include_timestamp=s.getboolean('include_timestamp', True),
            # Contenuto testuale
            title=s.get('title', 'PROFETA Analysis Report'),
            subtitle=s.get('subtitle', 'Universal Multi-Domain Hybrid Prediction System'),
            company=s.get('company', 'BilliDynamics™'),
            author=s.get('author', 'PROFETA v5.0'),
            language=s.get('language', 'en'),
            # Formattazione
            confidential=s.getboolean('confidential', True),
            include_disclaimer=s.getboolean('include_disclaimer', True),
            include_watermark=s.getboolean('include_watermark', False),
            page_size=s.get('page_size', 'A4'),
            # Contenuto opzionale
            include_model_details=s.getboolean('include_model_details', True),
            include_charts=s.getboolean('include_charts', True),
            include_prediction_graph=s.getboolean('include_prediction_graph', True),
            top_models_count=s.getint('top_models_count', 10)
        )


class ConfigLoader:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists(): raise ConfigurationError(f"Not found: {path}")
        self.config = configparser.ConfigParser()
        # Prova vari encoding per compatibilità cross-platform
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        for enc in encodings:
            try:
                self.config.read(self.path, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ConfigurationError(f"Cannot decode config file: {path}")
    
    def get_system(self) -> SystemConfig: return SystemConfig.from_config(self.config)
    def get_domain(self) -> DomainProfile: return DomainProfile.from_config(self.config)
    def get_granularity(self) -> GranularityConfig: return GranularityConfig.from_config(self.config)
    def get_training(self) -> TrainingConfig: return TrainingConfig.from_config(self.config)
    def get_classification(self) -> ClassificationConfig: return ClassificationConfig.from_config(self.config)
    def get_fusion(self) -> FusionConfig: return FusionConfig.from_config(self.config)
    def get_prediction(self) -> PredictionConfig: return PredictionConfig.from_config(self.config)
    def get_scheduler(self) -> SchedulerConfig: return SchedulerConfig.from_config(self.config)
    def get_report(self) -> ReportConfig: return ReportConfig.from_config(self.config)
    
    def get_model_configs(self, num_features: int = 50) -> List[ModelConfig]:
        num_models = self.config.getint('ENSEMBLE', 'num_models', fallback=3)
        num_classes = self.config.getint('CLASSIFICATION', 'num_classes', fallback=3)
        configs = []
        for i in range(1, num_models + 1):
            sec = f'MODEL_{i}'
            if self.config.has_section(sec):
                configs.append(ModelConfig.from_config_section(self.config[sec], i, num_features, num_classes))
            else:
                configs.append(ModelConfig(i, 60, num_features, 64, 0.2, True, 3, ModelArchitecture.LSTM, 0.0001, False, num_classes))
        return configs
    
    def get_data_paths(self) -> Tuple[str, str]:
        train = self.config.get('DATA', 'data_path', fallback='data/train.csv')
        pred = self.config.get('INPUT', 'input_data_path', fallback=train)
        return train, pred

class PROFETADaemon:
    def __init__(self, config_path, logger=None):
        self.config_path = Path(config_path)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._shutdown = threading.Event()
        self._engine: Optional[PROFETAEngine] = None
    
    def run(self):
        self._print_banner()
        self._setup_signals()
        loader = ConfigLoader(self.config_path)
        loader.get_system().initialize()
        
        sched = loader.get_scheduler()
        train_path, pred_path = loader.get_data_paths()
        
        self._engine = PROFETAEngine(
            loader.get_domain(), loader.get_granularity(), loader.get_training(),
            loader.get_classification(), loader.get_fusion(), loader.get_prediction(),
            loader.get_model_configs(), self.logger, loader.get_report())
        
        if sched.mode == ExecutionMode.ONCE:
            self._run_once(train_path, pred_path)
        else:
            self._run_daemon(train_path, pred_path, sched)
    
    def _run_once(self, train_path, pred_path):
        self.logger.info("Running ONCE mode")
        self._engine.train(train_path)
        results = self._engine.predict(pred_path)
        # In ONCE mode, trigger=training per generare report dopo il ciclo completo
        self._engine.generate_output(results, self._engine._processed_data, trigger="training")
        self.logger.info("Complete")
    
    def _run_daemon(self, train_path, pred_path, sched):
        self.logger.info("Running DAEMON mode")
        last_train = last_pred = None
        if sched.train_on_startup:
            self._engine.train(train_path)
            last_train = datetime.datetime.now()
            # Report dopo training iniziale se configurato
            if self._engine.report_config.generate_on_training:
                results = self._engine.predict(pred_path)
                self._engine.generate_output(results, self._engine._processed_data, trigger="training")
        if sched.predict_on_startup and not (sched.train_on_startup and self._engine.report_config.generate_on_training):
            results = self._engine.predict(pred_path)
            self._engine.generate_output(results, self._engine._processed_data, trigger="prediction")
            last_pred = datetime.datetime.now()
        while not self._shutdown.is_set():
            now = datetime.datetime.now()
            if sched.training_interval_min > 0 and (last_train is None or (now - last_train).total_seconds() / 60 >= sched.training_interval_min):
                try:
                    self._engine.train(train_path)
                    last_train = now
                    # Report dopo re-training
                    if self._engine.report_config.generate_on_training:
                        results = self._engine.predict(pred_path)
                        self._engine.generate_output(results, self._engine._processed_data, trigger="training")
                except Exception as e: self.logger.error(f"Training failed: {e}")
            if sched.prediction_interval_min > 0 and (last_pred is None or (now - last_pred).total_seconds() / 60 >= sched.prediction_interval_min):
                try:
                    results = self._engine.predict(pred_path)
                    self._engine.generate_output(results, self._engine._processed_data, trigger="prediction")
                    last_pred = now
                except Exception as e: self.logger.error(f"Prediction failed: {e}")
            self._shutdown.wait(sched.health_check_sec)
        self.logger.info("Daemon shutdown")
    
    def _setup_signals(self):
        def handler(sig, frame):
            self.logger.info(f"Signal {sig} received, shutting down...")
            self._shutdown.set()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    def _print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════════════════════════════╗
║     PROFETA UNIVERSAL v5.0 - Multi-Domain Hybrid Prediction System              ║
║     BilliDynamics™ - Eng. Emilio Billi - 2025                                    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
        """)
        self.logger.info(f"PROFETA Universal v{__version__}")

def create_sample_config(path="config-profeta-v5.ini"):
    content = """; PROFETA Universal v5.0 Configuration
[SYSTEM]
log_level = INFO
use_gpu = true
multi_gpu = auto
mixed_precision = true

[DOMAIN]
type = financial
subtype = crypto
use_returns = true
use_volatility = true
use_order_flow = true
use_technical_indicators = true

[GRANULARITY]
input_granularity = auto
model_granularity = minute
output_granularity = hour
resample_method = ohlc
auto_sort = true

[DATA]
data_path = ./data/training.csv
target_column = close

[INPUT]
input_data_path = ./data/live.csv

[TRAINING]
num_epochs = 100
batch_size = 32
learning_rate = 0.001
early_stopping_patience = 15

[CLASSIFICATION]
enabled = true
num_classes = 3
threshold_mode = volatility
prediction_horizon = 1

[FUSION]
# v5.2.0 Pure Forecast - segnali di trading rimossi
strategy = regression_derived
delta_threshold_pct = 0.0005
# generate_signals = DEPRECATED - sempre disabilitato in v5.2+

[PREDICTION]
num_future_steps = 24
timestamp_column = timestamp_column
target_column = close
graph = true

[SCHEDULER]
mode = once

[ENSEMBLE]
num_models = 3

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
sequence_length = 90
lstm_units = 64
dropout_rate = 0.2
use_bidirectional = false
"""
    with open(path, 'w') as f: f.write(content)
    print(f"Config created: {path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PROFETA Universal v5.0")
    parser.add_argument('config_file', nargs='?', help='Config file')
    parser.add_argument('--create-config', action='store_true', help='Create sample config')
    parser.add_argument('--version', action='store_true', help='Show version')
    args = parser.parse_args()
    
    if args.version:
        print(f"PROFETA Universal v{__version__}\n{__author__}\n{__company__}")
        return
    if args.create_config:
        create_sample_config()
        return
    
    # Auto-discovery config file
    if not args.config_file:
        config_candidates = list(Path('.').glob('*.ini')) + list(Path('.').glob('config*.ini'))
        config_candidates = sorted(set(config_candidates))  # rimuovi duplicati
        
        if len(config_candidates) == 1:
            args.config_file = str(config_candidates[0])
            print(f"[Auto-detected config: {args.config_file}]")
        elif len(config_candidates) > 1:
            print("Multiple config files found:")
            for i, cfg in enumerate(config_candidates, 1):
                print(f"  {i}. {cfg}")
            print("\nSpecify which one: python profeta-universal.py <config_file>")
            return
        else:
            parser.print_help()
            return
    
    try:
        PROFETADaemon(args.config_file).run()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except PROFETAError as e:
        logging.error(f"PROFETA Error: {e}")
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
