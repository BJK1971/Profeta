"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗  █████╗  ██████╗██╗  ██╗████████╗███████╗███████╗████████╗         ║
║   ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝         ║
║   ██████╔╝███████║██║     █████╔╝    ██║   █████╗  ███████╗   ██║            ║
║   ██╔══██╗██╔══██║██║     ██╔═██╗    ██║   ██╔══╝  ╚════██║   ██║            ║
║   ██████╔╝██║  ██║╚██████╗██║  ██╗   ██║   ███████╗███████║   ██║            ║
║   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝   ╚═╝            ║
║                                                                              ║
║   PROFETA Backtesting Framework                                              ║
║   Version 1.0 - Enterprise Edition                                           ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   Titolo:    PROFETA Backtesting Framework                                   ║
║   Autore:    Eng. Emilio Billi                                               ║
║   Azienda:   BilliDynamics™                                                  ║
║   Data:      2025                                                            ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   FUNZIONALITÀ:                                                              ║
║   ═════════════                                                              ║
║   • Walk-Forward Validation con rolling window                               ║
║   • Simulazione trading con strategie configurabili                          ║
║   • Metriche finanziarie complete (Sharpe, Sortino, Max DD)                 ║
║   • Equity curve e visualizzazioni                                           ║
║   • Report PDF/Excel automatici                                              ║
║   • Analisi per fold e aggregata                                             ║
║   • Integrazione completa con PROFETA v3.2                                   ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   CONFIGURAZIONE VIA .INI:                                                   ║
║   ─────────────────────────                                                  ║
║   [BACKTEST]                                                                 ║
║   mode = walk_forward                                                        ║
║   num_folds = 12                                                             ║
║   train_window_days = 90                                                     ║
║   test_window_days = 30                                                      ║
║   step_days = 30                                                             ║
║   initial_capital = 100000                                                   ║
║   transaction_cost_pct = 0.1                                                 ║
║   strategy = threshold                                                       ║
║   threshold_pct = 0.5                                                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import sys
import json
import logging
import datetime
import warnings
import configparser
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import (
    Tuple, List, Dict, Optional, Union, Any,
    Callable, Iterator, Literal
)
from abc import ABC, abstractmethod
import pickle

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from tqdm import tqdm

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, Callback
from tensorflow.keras.optimizers import Adam

# Suppress warnings
warnings.filterwarnings('ignore')
tf.get_logger().setLevel('ERROR')


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              ENUMS E COSTANTI                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BacktestMode(Enum):
    """Modalità di backtesting."""
    WALK_FORWARD = "walk_forward"       # Rolling window
    EXPANDING = "expanding"             # Expanding window
    SIMPLE_SPLIT = "simple_split"       # Semplice train/test split


class TradingStrategy(Enum):
    """Strategie di trading simulabili."""
    DIRECTION = "direction"             # Buy se prediction > current
    THRESHOLD = "threshold"             # Con soglia minima
    CONFIDENCE = "confidence"           # Basato su accordo ensemble
    MEAN_REVERSION = "mean_reversion"   # Contrarian


class TradeAction(Enum):
    """Azioni di trading."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionType(Enum):
    """Tipo di posizione."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                         CONFIGURAZIONE BACKTEST                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@dataclass
class BacktestConfig:
    """Configurazione completa per il backtesting."""
    
    # Modalità
    mode: BacktestMode = BacktestMode.WALK_FORWARD
    
    # Finestre temporali (in giorni)
    num_folds: int = 12
    train_window_days: int = 90
    test_window_days: int = 30
    step_days: int = 30  # Quanto avanzare tra un fold e l'altro
    
    # Capitale e costi
    initial_capital: float = 100000.0
    transaction_cost_pct: float = 0.1  # 0.1% per trade
    slippage_pct: float = 0.05         # 0.05% slippage
    risk_free_rate: float = 0.02       # 2% annuo
    
    # Strategia
    strategy: TradingStrategy = TradingStrategy.THRESHOLD
    threshold_pct: float = 0.5         # Soglia per strategia threshold
    confidence_threshold: float = 0.7  # Soglia per strategia confidence
    
    # Position sizing
    position_size_pct: float = 100.0   # % capitale per trade
    max_positions: int = 1             # Max posizioni simultanee
    allow_short: bool = True           # Permetti short selling
    
    # Risk management
    stop_loss_pct: Optional[float] = None    # Stop loss (None = disabilitato)
    take_profit_pct: Optional[float] = None  # Take profit
    max_drawdown_pct: float = 30.0           # Max drawdown per stop trading
    
    # Output
    output_dir: Path = Path("./backtest_results")
    generate_plots: bool = True
    generate_report: bool = True
    save_trades: bool = True
    
    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> 'BacktestConfig':
        """Crea BacktestConfig dal file INI."""
        if not config.has_section('BACKTEST'):
            return cls()
        
        section = config['BACKTEST']
        
        # Mode
        mode_str = section.get('mode', 'walk_forward').lower()
        mode_map = {
            'walk_forward': BacktestMode.WALK_FORWARD,
            'expanding': BacktestMode.EXPANDING,
            'simple_split': BacktestMode.SIMPLE_SPLIT
        }
        mode = mode_map.get(mode_str, BacktestMode.WALK_FORWARD)
        
        # Strategy
        strategy_str = section.get('strategy', 'threshold').lower()
        strategy_map = {
            'direction': TradingStrategy.DIRECTION,
            'threshold': TradingStrategy.THRESHOLD,
            'confidence': TradingStrategy.CONFIDENCE,
            'mean_reversion': TradingStrategy.MEAN_REVERSION
        }
        strategy = strategy_map.get(strategy_str, TradingStrategy.THRESHOLD)
        
        return cls(
            mode=mode,
            num_folds=int(section.get('num_folds', 12)),
            train_window_days=int(section.get('train_window_days', 90)),
            test_window_days=int(section.get('test_window_days', 30)),
            step_days=int(section.get('step_days', 30)),
            initial_capital=float(section.get('initial_capital', 100000)),
            transaction_cost_pct=float(section.get('transaction_cost_pct', 0.1)),
            slippage_pct=float(section.get('slippage_pct', 0.05)),
            risk_free_rate=float(section.get('risk_free_rate', 0.02)),
            strategy=strategy,
            threshold_pct=float(section.get('threshold_pct', 0.5)),
            confidence_threshold=float(section.get('confidence_threshold', 0.7)),
            position_size_pct=float(section.get('position_size_pct', 100)),
            max_positions=int(section.get('max_positions', 1)),
            allow_short=section.getboolean('allow_short', True),
            stop_loss_pct=float(section.get('stop_loss_pct')) if section.get('stop_loss_pct') else None,
            take_profit_pct=float(section.get('take_profit_pct')) if section.get('take_profit_pct') else None,
            max_drawdown_pct=float(section.get('max_drawdown_pct', 30)),
            output_dir=Path(section.get('output_dir', './backtest_results')),
            generate_plots=section.getboolean('generate_plots', True),
            generate_report=section.getboolean('generate_report', True),
            save_trades=section.getboolean('save_trades', True)
        )


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              DATA STRUCTURES                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@dataclass
class Trade:
    """Rappresenta un singolo trade."""
    trade_id: int
    timestamp: datetime.datetime
    action: TradeAction
    price: float
    quantity: float
    position_type: PositionType
    prediction: float
    actual_next: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    cumulative_pnl: float = 0.0
    transaction_cost: float = 0.0
    fold_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trade_id': self.trade_id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'price': self.price,
            'quantity': self.quantity,
            'position_type': self.position_type.value,
            'prediction': self.prediction,
            'actual_next': self.actual_next,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'cumulative_pnl': self.cumulative_pnl,
            'transaction_cost': self.transaction_cost,
            'fold_id': self.fold_id
        }


@dataclass
class FoldResult:
    """Risultati di un singolo fold."""
    fold_id: int
    train_start: datetime.datetime
    train_end: datetime.datetime
    test_start: datetime.datetime
    test_end: datetime.datetime
    
    # Metriche previsione
    rmse: float = 0.0
    mae: float = 0.0
    mape: float = 0.0
    r2: float = 0.0
    direction_accuracy: float = 0.0
    
    # Metriche trading
    num_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Trades dettagliati
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    
    @property
    def win_rate(self) -> float:
        if self.num_trades == 0:
            return 0.0
        return self.winning_trades / self.num_trades
    
    @property
    def profit_factor(self) -> float:
        gains = sum(t.pnl for t in self.trades if t.pnl > 0)
        losses = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if losses == 0:
            return float('inf') if gains > 0 else 0.0
        return gains / losses


@dataclass
class BacktestResult:
    """Risultati aggregati del backtest."""
    config: BacktestConfig
    start_time: datetime.datetime
    end_time: datetime.datetime
    
    # Fold results
    fold_results: List[FoldResult] = field(default_factory=list)
    
    # Metriche aggregate
    total_trades: int = 0
    total_winning_trades: int = 0
    total_losing_trades: int = 0
    
    # Performance
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    volatility: float = 0.0
    
    # Win/Loss
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Prediction accuracy
    avg_rmse: float = 0.0
    avg_mae: float = 0.0
    avg_direction_accuracy: float = 0.0
    
    # Full equity curve
    equity_curve: List[Tuple[datetime.datetime, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_days': (self.end_time - self.start_time).days,
                'num_folds': len(self.fold_results),
                'total_trades': self.total_trades
            },
            'performance': {
                'initial_capital': self.initial_capital,
                'final_capital': self.final_capital,
                'total_return': self.total_return,
                'total_return_pct': self.total_return_pct,
                'annualized_return': self.annualized_return
            },
            'risk_metrics': {
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'calmar_ratio': self.calmar_ratio,
                'max_drawdown': self.max_drawdown,
                'max_drawdown_duration_days': self.max_drawdown_duration_days,
                'volatility': self.volatility
            },
            'trading_metrics': {
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
                'largest_win': self.largest_win,
                'largest_loss': self.largest_loss
            },
            'prediction_metrics': {
                'avg_rmse': self.avg_rmse,
                'avg_mae': self.avg_mae,
                'avg_direction_accuracy': self.avg_direction_accuracy
            }
        }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           METRICS CALCULATOR                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class FinancialMetricsCalculator:
    """Calcola metriche finanziarie avanzate."""
    
    @staticmethod
    def calculate_returns(equity_curve: List[float]) -> np.ndarray:
        """Calcola i rendimenti percentuali."""
        equity = np.array(equity_curve)
        returns = np.diff(equity) / equity[:-1]
        return returns
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray, 
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ) -> float:
        """
        Calcola lo Sharpe Ratio.
        
        Sharpe = (E[R] - Rf) / σ(R)
        """
        if len(returns) < 2 or np.std(returns) == 0:
            return 0.0
        
        # Converti risk-free rate in rate per periodo
        rf_per_period = risk_free_rate / periods_per_year
        
        excess_returns = returns - rf_per_period
        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        
        # Annualizza
        sharpe_annualized = sharpe * np.sqrt(periods_per_year)
        
        return sharpe_annualized
    
    @staticmethod
    def calculate_sortino_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ) -> float:
        """
        Calcola il Sortino Ratio.
        
        Sortino = (E[R] - Rf) / σ(R_negative)
        
        Penalizza solo la volatilità negativa.
        """
        if len(returns) < 2:
            return 0.0
        
        rf_per_period = risk_free_rate / periods_per_year
        excess_returns = returns - rf_per_period
        
        # Solo rendimenti negativi
        negative_returns = returns[returns < 0]
        
        if len(negative_returns) == 0 or np.std(negative_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_std = np.std(negative_returns)
        sortino = np.mean(excess_returns) / downside_std
        
        # Annualizza
        sortino_annualized = sortino * np.sqrt(periods_per_year)
        
        return sortino_annualized
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int, int]:
        """
        Calcola il Maximum Drawdown.
        
        Returns:
            Tuple (max_dd_pct, peak_idx, trough_idx, duration_periods)
        """
        equity = np.array(equity_curve)
        
        if len(equity) < 2:
            return 0.0, 0, 0, 0
        
        # Calcola running maximum
        running_max = np.maximum.accumulate(equity)
        
        # Drawdown in ogni punto
        drawdowns = (running_max - equity) / running_max
        
        # Maximum drawdown
        max_dd_idx = np.argmax(drawdowns)
        max_dd = drawdowns[max_dd_idx]
        
        # Trova il picco prima del max drawdown
        peak_idx = np.argmax(equity[:max_dd_idx + 1])
        
        # Durata: dal picco al recupero (o fine serie)
        recovery_idx = len(equity) - 1
        for i in range(max_dd_idx, len(equity)):
            if equity[i] >= equity[peak_idx]:
                recovery_idx = i
                break
        
        duration = recovery_idx - peak_idx
        
        return max_dd * 100, peak_idx, max_dd_idx, duration
    
    @staticmethod
    def calculate_calmar_ratio(
        annualized_return: float,
        max_drawdown_pct: float
    ) -> float:
        """
        Calcola il Calmar Ratio.
        
        Calmar = Annualized Return / Max Drawdown
        """
        if max_drawdown_pct == 0:
            return float('inf') if annualized_return > 0 else 0.0
        
        return annualized_return / max_drawdown_pct
    
    @staticmethod
    def calculate_volatility(
        returns: np.ndarray,
        periods_per_year: int = 252
    ) -> float:
        """Calcola la volatilità annualizzata."""
        if len(returns) < 2:
            return 0.0
        
        return np.std(returns) * np.sqrt(periods_per_year) * 100
    
    @staticmethod
    def calculate_direction_accuracy(
        predictions: np.ndarray,
        actuals: np.ndarray,
        current_prices: np.ndarray
    ) -> float:
        """
        Calcola l'accuratezza direzionale.
        
        Percentuale di volte in cui la previsione ha indovinato
        la direzione del movimento.
        """
        if len(predictions) < 2:
            return 0.0
        
        # Direzione prevista: prediction vs current
        pred_direction = np.sign(predictions - current_prices)
        
        # Direzione reale: actual vs current
        actual_direction = np.sign(actuals - current_prices)
        
        # Accuratezza
        correct = np.sum(pred_direction == actual_direction)
        accuracy = correct / len(predictions)
        
        return accuracy * 100


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           TRADING STRATEGIES                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class TradingStrategyBase(ABC):
    """Classe base per le strategie di trading."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
    
    @abstractmethod
    def generate_signal(
        self,
        current_price: float,
        prediction: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None
    ) -> TradeAction:
        """Genera un segnale di trading."""
        pass


class DirectionStrategy(TradingStrategyBase):
    """Strategia basata sulla direzione della previsione."""
    
    def generate_signal(
        self,
        current_price: float,
        prediction: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None
    ) -> TradeAction:
        if prediction > current_price:
            return TradeAction.BUY
        elif prediction < current_price and self.config.allow_short:
            return TradeAction.SELL
        else:
            return TradeAction.HOLD


class ThresholdStrategy(TradingStrategyBase):
    """Strategia con soglia minima."""
    
    def generate_signal(
        self,
        current_price: float,
        prediction: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None
    ) -> TradeAction:
        threshold = self.config.threshold_pct / 100
        
        change_pct = (prediction - current_price) / current_price
        
        if change_pct > threshold:
            return TradeAction.BUY
        elif change_pct < -threshold and self.config.allow_short:
            return TradeAction.SELL
        else:
            return TradeAction.HOLD


class ConfidenceStrategy(TradingStrategyBase):
    """Strategia basata sull'accordo tra modelli dell'ensemble."""
    
    def generate_signal(
        self,
        current_price: float,
        prediction: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None
    ) -> TradeAction:
        if model_predictions is None or len(model_predictions) < 2:
            # Fallback a direction
            return DirectionStrategy(self.config).generate_signal(
                current_price, prediction)
        
        # Calcola accordo tra modelli
        predictions = np.array(model_predictions)
        
        # Quanti modelli prevedono aumento?
        bullish_count = np.sum(predictions > current_price)
        bearish_count = np.sum(predictions < current_price)
        total = len(predictions)
        
        bullish_ratio = bullish_count / total
        bearish_ratio = bearish_count / total
        
        threshold = self.config.confidence_threshold
        
        if bullish_ratio >= threshold:
            return TradeAction.BUY
        elif bearish_ratio >= threshold and self.config.allow_short:
            return TradeAction.SELL
        else:
            return TradeAction.HOLD


class MeanReversionStrategy(TradingStrategyBase):
    """Strategia contrarian di mean reversion."""
    
    def generate_signal(
        self,
        current_price: float,
        prediction: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None
    ) -> TradeAction:
        if historical_prices is None or len(historical_prices) < 20:
            return TradeAction.HOLD
        
        # Calcola media mobile
        ma = np.mean(historical_prices[-20:])
        std = np.std(historical_prices[-20:])
        
        # Z-score
        z_score = (current_price - ma) / std if std > 0 else 0
        
        threshold = self.config.threshold_pct / 100 * 2  # Usa threshold come z-score
        
        # Mean reversion: compra se troppo basso, vendi se troppo alto
        if z_score < -threshold:
            return TradeAction.BUY
        elif z_score > threshold and self.config.allow_short:
            return TradeAction.SELL
        else:
            return TradeAction.HOLD


class StrategyFactory:
    """Factory per le strategie di trading."""
    
    @staticmethod
    def create(config: BacktestConfig) -> TradingStrategyBase:
        strategies = {
            TradingStrategy.DIRECTION: DirectionStrategy,
            TradingStrategy.THRESHOLD: ThresholdStrategy,
            TradingStrategy.CONFIDENCE: ConfidenceStrategy,
            TradingStrategy.MEAN_REVERSION: MeanReversionStrategy
        }
        
        strategy_class = strategies.get(config.strategy, ThresholdStrategy)
        return strategy_class(config)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           TRADING SIMULATOR                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class TradingSimulator:
    """
    Simula il trading basato sulle previsioni.
    
    Gestisce:
    - Apertura/chiusura posizioni
    - Calcolo P&L
    - Transaction costs e slippage
    - Stop loss e take profit
    """
    
    def __init__(self, config: BacktestConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        self.strategy = StrategyFactory.create(config)
        
        # Stato
        self.capital = config.initial_capital
        self.position: PositionType = PositionType.FLAT
        self.position_price: float = 0.0
        self.position_size: float = 0.0
        self.trade_count: int = 0
        
        # Tracking
        self.equity_history: List[float] = [config.initial_capital]
        self.trades: List[Trade] = []
    
    def reset(self) -> None:
        """Reset dello stato del simulatore."""
        self.capital = self.config.initial_capital
        self.position = PositionType.FLAT
        self.position_price = 0.0
        self.position_size = 0.0
        self.trade_count = 0
        self.equity_history = [self.config.initial_capital]
        self.trades = []
    
    def get_equity(self, current_price: float) -> float:
        """Calcola l'equity corrente (capitale + valore posizioni aperte)."""
        if self.position == PositionType.FLAT:
            return self.capital
        
        if self.position == PositionType.LONG:
            unrealized_pnl = (current_price - self.position_price) * self.position_size
        else:  # SHORT
            unrealized_pnl = (self.position_price - current_price) * self.position_size
        
        return self.capital + unrealized_pnl
    
    def _calculate_transaction_cost(self, price: float, quantity: float) -> float:
        """Calcola i costi di transazione."""
        value = price * quantity
        cost = value * (self.config.transaction_cost_pct / 100)
        slippage = value * (self.config.slippage_pct / 100)
        return cost + slippage
    
    def _check_stop_loss_take_profit(
        self, 
        current_price: float
    ) -> Optional[TradeAction]:
        """Verifica se triggerare stop loss o take profit."""
        if self.position == PositionType.FLAT:
            return None
        
        if self.position == PositionType.LONG:
            pnl_pct = (current_price - self.position_price) / self.position_price * 100
        else:
            pnl_pct = (self.position_price - current_price) / self.position_price * 100
        
        # Stop loss
        if self.config.stop_loss_pct and pnl_pct <= -self.config.stop_loss_pct:
            self.logger.debug(f"Stop loss triggered at {pnl_pct:.2f}%")
            return TradeAction.SELL if self.position == PositionType.LONG else TradeAction.BUY
        
        # Take profit
        if self.config.take_profit_pct and pnl_pct >= self.config.take_profit_pct:
            self.logger.debug(f"Take profit triggered at {pnl_pct:.2f}%")
            return TradeAction.SELL if self.position == PositionType.LONG else TradeAction.BUY
        
        return None
    
    def process_bar(
        self,
        timestamp: datetime.datetime,
        current_price: float,
        prediction: float,
        actual_next: float,
        model_predictions: Optional[List[float]] = None,
        historical_prices: Optional[np.ndarray] = None,
        fold_id: int = 0
    ) -> Optional[Trade]:
        """
        Processa una barra di prezzo e potenzialmente esegue un trade.
        
        Args:
            timestamp: Timestamp della barra
            current_price: Prezzo corrente
            prediction: Previsione ensemble
            actual_next: Prezzo reale successivo (per calcolo P&L)
            model_predictions: Previsioni individuali dei modelli
            historical_prices: Prezzi storici per strategie avanzate
            fold_id: ID del fold corrente
            
        Returns:
            Trade se eseguito, None altrimenti
        """
        trade = None
        
        # Check stop loss / take profit
        sl_tp_action = self._check_stop_loss_take_profit(current_price)
        if sl_tp_action:
            trade = self._close_position(timestamp, current_price, prediction, 
                                        actual_next, fold_id, reason="SL/TP")
        
        # Genera segnale dalla strategia
        if trade is None:
            signal = self.strategy.generate_signal(
                current_price, prediction, model_predictions, historical_prices
            )
            
            trade = self._execute_signal(
                signal, timestamp, current_price, prediction, actual_next, fold_id
            )
        
        # Aggiorna equity history
        self.equity_history.append(self.get_equity(current_price))
        
        return trade
    
    def _execute_signal(
        self,
        signal: TradeAction,
        timestamp: datetime.datetime,
        price: float,
        prediction: float,
        actual_next: float,
        fold_id: int
    ) -> Optional[Trade]:
        """Esegue un segnale di trading."""
        
        if signal == TradeAction.HOLD:
            return None
        
        if signal == TradeAction.BUY:
            if self.position == PositionType.SHORT:
                # Chiudi short prima
                trade = self._close_position(timestamp, price, prediction, 
                                            actual_next, fold_id)
                return trade
            elif self.position == PositionType.FLAT:
                # Apri long
                return self._open_position(timestamp, price, prediction, 
                                          actual_next, PositionType.LONG, fold_id)
        
        elif signal == TradeAction.SELL:
            if self.position == PositionType.LONG:
                # Chiudi long
                trade = self._close_position(timestamp, price, prediction,
                                            actual_next, fold_id)
                return trade
            elif self.position == PositionType.FLAT and self.config.allow_short:
                # Apri short
                return self._open_position(timestamp, price, prediction,
                                          actual_next, PositionType.SHORT, fold_id)
        
        return None
    
    def _open_position(
        self,
        timestamp: datetime.datetime,
        price: float,
        prediction: float,
        actual_next: float,
        position_type: PositionType,
        fold_id: int
    ) -> Trade:
        """Apre una nuova posizione."""
        # Calcola size
        position_value = self.capital * (self.config.position_size_pct / 100)
        quantity = position_value / price
        
        # Transaction cost
        cost = self._calculate_transaction_cost(price, quantity)
        self.capital -= cost
        
        # Aggiorna stato
        self.position = position_type
        self.position_price = price
        self.position_size = quantity
        self.trade_count += 1
        
        action = TradeAction.BUY if position_type == PositionType.LONG else TradeAction.SELL
        
        trade = Trade(
            trade_id=self.trade_count,
            timestamp=timestamp,
            action=action,
            price=price,
            quantity=quantity,
            position_type=position_type,
            prediction=prediction,
            actual_next=actual_next,
            transaction_cost=cost,
            fold_id=fold_id
        )
        
        self.trades.append(trade)
        self.logger.debug(f"Opened {position_type.value} at {price:.4f}")
        
        return trade
    
    def _close_position(
        self,
        timestamp: datetime.datetime,
        price: float,
        prediction: float,
        actual_next: float,
        fold_id: int,
        reason: str = ""
    ) -> Trade:
        """Chiude la posizione corrente."""
        if self.position == PositionType.FLAT:
            return None
        
        # Calcola P&L
        if self.position == PositionType.LONG:
            pnl = (price - self.position_price) * self.position_size
            action = TradeAction.SELL
        else:
            pnl = (self.position_price - price) * self.position_size
            action = TradeAction.BUY
        
        # Transaction cost
        cost = self._calculate_transaction_cost(price, self.position_size)
        pnl -= cost
        
        pnl_pct = pnl / (self.position_price * self.position_size) * 100
        
        # Aggiorna capitale con P&L netto (i margini non erano stati sottratti all'apertura)
        self.capital += pnl
        
        self.trade_count += 1
        
        trade = Trade(
            trade_id=self.trade_count,
            timestamp=timestamp,
            action=action,
            price=price,
            quantity=self.position_size,
            position_type=self.position,
            prediction=prediction,
            actual_next=actual_next,
            pnl=pnl,
            pnl_pct=pnl_pct,
            cumulative_pnl=self.capital - self.config.initial_capital,
            transaction_cost=cost,
            fold_id=fold_id
        )
        
        self.trades.append(trade)
        
        self.logger.debug(f"Closed {self.position.value} at {price:.4f}, PnL: {pnl:.2f} ({pnl_pct:.2f}%)")
        
        # Reset posizione
        self.position = PositionType.FLAT
        self.position_price = 0.0
        self.position_size = 0.0
        
        return trade
    
    def close_all_positions(
        self,
        timestamp: datetime.datetime,
        price: float,
        fold_id: int
    ) -> Optional[Trade]:
        """Chiude tutte le posizioni aperte (fine fold)."""
        if self.position != PositionType.FLAT:
            return self._close_position(timestamp, price, price, price, fold_id, "End of fold")
        return None


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              FOLD GENERATOR                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@dataclass
class FoldWindow:
    """Rappresenta una finestra temporale per un fold."""
    fold_id: int
    train_start: datetime.datetime
    train_end: datetime.datetime
    test_start: datetime.datetime
    test_end: datetime.datetime


class FoldGenerator:
    """Genera le finestre temporali per il walk-forward validation."""
    
    def __init__(self, config: BacktestConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def generate(
        self,
        data_start: datetime.datetime,
        data_end: datetime.datetime
    ) -> List[FoldWindow]:
        """
        Genera i fold per il backtesting.
        
        Returns:
            Lista di FoldWindow
        """
        folds = []
        
        train_days = self.config.train_window_days
        test_days = self.config.test_window_days
        step_days = self.config.step_days
        
        if self.config.mode == BacktestMode.SIMPLE_SPLIT:
            # Semplice split basato sui secondi totali per supportare dataset < 1 giorno
            total_secs = (data_end - data_start).total_seconds()
            train_end_sec = int(total_secs * 0.8)
            
            train_end = data_start + datetime.timedelta(seconds=train_end_sec)
            
            folds.append(FoldWindow(
                fold_id=1,
                train_start=data_start,
                train_end=train_end,
                test_start=train_end,
                test_end=data_end
            ))
        
        elif self.config.mode == BacktestMode.WALK_FORWARD:
            # Walk-forward con rolling window
            current_start = data_start
            fold_id = 1
            
            while fold_id <= self.config.num_folds:
                train_start = current_start
                train_end = train_start + datetime.timedelta(days=train_days)
                test_start = train_end
                test_end = test_start + datetime.timedelta(days=test_days)
                
                if test_end > data_end:
                    break
                
                folds.append(FoldWindow(
                    fold_id=fold_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end
                ))
                
                current_start += datetime.timedelta(days=step_days)
                fold_id += 1
        
        elif self.config.mode == BacktestMode.EXPANDING:
            # Expanding window (train cresce)
            fold_id = 1
            train_start = data_start
            
            for i in range(self.config.num_folds):
                train_end = train_start + datetime.timedelta(
                    days=train_days + i * step_days
                )
                test_start = train_end
                test_end = test_start + datetime.timedelta(days=test_days)
                
                if test_end > data_end:
                    break
                
                folds.append(FoldWindow(
                    fold_id=fold_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end
                ))
                
                fold_id += 1
        
        self.logger.info(f"Generati {len(folds)} fold per backtesting")
        
        return folds


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           LIGHTWEIGHT TRAINER                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class LightweightTrainer:
    """
    Trainer leggero per backtesting.
    
    Trainato su ogni fold senza salvare modelli su disco.
    """
    
    def __init__(
        self,
        model_configs: List[Dict],
        training_config: Dict,
        logger: Optional[logging.Logger] = None
    ):
        self.model_configs = model_configs
        self.training_config = training_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        self.models: List[Sequential] = []
        self.scalers: List[MinMaxScaler] = []
        self.ensemble_delta: float = 0.0
    
    def _build_model(self, config: Dict) -> Sequential:
        """Costruisce un modello LSTM."""
        model = Sequential()
        
        seq_len = config.get('sequence_length', 60)
        lstm_units = config.get('lstm_units', 64)
        dropout = config.get('dropout_rate', 0.2)
        bidirectional = config.get('use_bidirectional', False)
        num_layers = config.get('num_lstm_layers', 4)
        
        for i in range(num_layers):
            return_seq = (i < num_layers - 1)
            
            if i == 0:
                if bidirectional:
                    model.add(Bidirectional(
                        LSTM(lstm_units, return_sequences=return_seq),
                        input_shape=(seq_len, 1)
                    ))
                else:
                    model.add(LSTM(lstm_units, input_shape=(seq_len, 1),
                                  return_sequences=return_seq))
            else:
                if bidirectional:
                    model.add(Bidirectional(LSTM(lstm_units, return_sequences=return_seq)))
                else:
                    model.add(LSTM(lstm_units, return_sequences=return_seq))
            
            model.add(Dropout(dropout))
        
        model.add(Dense(1))
        model.compile(optimizer=Adam(learning_rate=self.training_config.get('learning_rate', 0.001)),
                     loss='mse')
        
        return model
    
    def train(self, data: np.ndarray) -> None:
        """Trainare tutti i modelli dell'ensemble."""
        self.models = []
        self.scalers = []
        
        # Split per calcolo delta
        split_idx = int(len(data) * self.training_config.get('train_test_split', 0.8))
        train_data = data[:split_idx]
        test_data = data[split_idx:]
        
        all_test_predictions = []
        
        for config in self.model_configs:
            # Scaler
            scaler = MinMaxScaler()
            scaler.fit(train_data.reshape(-1, 1))
            self.scalers.append(scaler)
            
            scaled_data = scaler.transform(data.reshape(-1, 1))
            
            # Sequenze
            seq_len = config.get('sequence_length', 60)
            X, y = self._create_sequences(scaled_data, seq_len)
            
            # Split
            split = int(len(X) * self.training_config.get('train_test_split', 0.8))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # Build e train
            model = self._build_model(config)
            
            model.fit(
                X_train, y_train,
                epochs=self.training_config.get('num_epochs', 10),
                batch_size=self.training_config.get('batch_size', 32),
                validation_split=0.2,
                verbose=0,
                callbacks=[EarlyStopping(patience=3, restore_best_weights=True)]
            )
            
            self.models.append(model)
            
            # Previsioni test per delta
            if len(X_test) > 0:
                preds = model.predict(X_test, verbose=0)
                preds_inv = scaler.inverse_transform(preds)
                all_test_predictions.append(preds_inv.flatten())
        
        # Calcola ensemble delta
        if all_test_predictions:
            # Trova la lunghezza minima tra tutte le previsioni
            min_len_preds = min(len(p) for p in all_test_predictions)
            
            # Ground truth parte dopo la sequence length massima per allinearsi
            # Prendi la sequence length massima configurata nell'ensemble
            max_seq_len = max(config.get('sequence_length', 60) for config in self.model_configs)
            y_true_full = data[split_idx + max_seq_len:]
            
            # La lunghezza finale da confrontare è il minimo tra predizioni e ground truth rimanente
            final_min_len = min(min_len_preds, len(y_true_full))
            
            # Taglia a destra (se ci sono discordanze) tutte le previsioni individuali
            aligned_preds = [p[-final_min_len:] for p in all_test_predictions]
            
            # Media delle predizioni allineate
            ensemble_avg = np.mean(aligned_preds, axis=0)
            
            # Allinea ground truth
            y_true_aligned = y_true_full[-final_min_len:]
            
            self.ensemble_delta = np.mean(y_true_aligned - ensemble_avg)
    
    def predict(
        self, 
        data: np.ndarray, 
        num_steps: int = 1
    ) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        Genera previsioni.
        
        Returns:
            Tuple (ensemble_prediction, individual_predictions)
        """
        all_predictions = []
        
        for model, scaler, config in zip(self.models, self.scalers, self.model_configs):
            seq_len = config.get('sequence_length', 60)
            
            scaled_data = scaler.transform(data.reshape(-1, 1))
            
            # Usa ultima sequenza
            if len(scaled_data) >= seq_len:
                last_seq = scaled_data[-seq_len:]
                
                pred_scaled = model.predict(last_seq.reshape(1, -1, 1), verbose=0)
                pred = scaler.inverse_transform(pred_scaled)[0, 0]
                
                all_predictions.append(pred)
        
        if not all_predictions:
            return np.array([data[-1]]), [np.array([data[-1]])]
        
        ensemble_pred = np.mean(all_predictions) + self.ensemble_delta
        
        return np.array([ensemble_pred]), [np.array([p]) for p in all_predictions]
    
    @staticmethod
    def _create_sequences(data: np.ndarray, seq_len: int) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for i in range(len(data) - seq_len):
            X.append(data[i:i+seq_len])
            y.append(data[i+seq_len])
        return np.array(X), np.array(y)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           REPORT GENERATOR                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BacktestReportGenerator:
    """Genera report e visualizzazioni per il backtest."""
    
    def __init__(self, config: BacktestConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def generate_plots(self, result: BacktestResult) -> List[Path]:
        """Genera tutti i grafici."""
        plots = []
        
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Equity Curve
        plots.append(self._plot_equity_curve(result))
        
        # 2. Drawdown
        plots.append(self._plot_drawdown(result))
        
        # 3. Returns Distribution
        plots.append(self._plot_returns_distribution(result))
        
        # 4. Performance per Fold
        plots.append(self._plot_fold_performance(result))
        
        # 5. Summary Dashboard
        plots.append(self._plot_summary_dashboard(result))
        
        return plots
    
    def _plot_equity_curve(self, result: BacktestResult) -> Path:
        """Grafico equity curve."""
        fig, ax = plt.subplots(figsize=(14, 7))
        
        dates = [ec[0] for ec in result.equity_curve]
        values = [ec[1] for ec in result.equity_curve]
        
        ax.plot(dates, values, linewidth=2, color='#2196F3', label='Equity')
        ax.axhline(y=result.initial_capital, color='gray', linestyle='--', 
                   label=f'Capitale Iniziale: ${result.initial_capital:,.0f}')
        
        # Evidenzia i fold
        colors = plt.cm.Pastel1(np.linspace(0, 1, len(result.fold_results)))
        for i, fold in enumerate(result.fold_results):
            ax.axvspan(fold.test_start, fold.test_end, alpha=0.3, color=colors[i])
        
        ax.set_xlabel('Data', fontsize=12)
        ax.set_ylabel('Equity ($)', fontsize=12)
        ax.set_title('PROFETA Backtest - Equity Curve', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Formato data
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        path = self.config.output_dir / 'equity_curve.png'
        plt.savefig(path, dpi=150)
        plt.close()
        
        return path
    
    def _plot_drawdown(self, result: BacktestResult) -> Path:
        """Grafico drawdown."""
        fig, ax = plt.subplots(figsize=(14, 5))
        
        dates = [ec[0] for ec in result.equity_curve]
        values = np.array([ec[1] for ec in result.equity_curve])
        
        # Calcola drawdown
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max * 100
        
        ax.fill_between(dates, drawdown, 0, color='#F44336', alpha=0.5)
        ax.plot(dates, drawdown, color='#D32F2F', linewidth=1)
        
        ax.axhline(y=-result.max_drawdown, color='red', linestyle='--',
                   label=f'Max Drawdown: {result.max_drawdown:.2f}%')
        
        ax.set_xlabel('Data', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.set_title('PROFETA Backtest - Drawdown', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        path = self.config.output_dir / 'drawdown.png'
        plt.savefig(path, dpi=150)
        plt.close()
        
        return path
    
    def _plot_returns_distribution(self, result: BacktestResult) -> Path:
        """Grafico distribuzione rendimenti."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Raccogli tutti i trade P&L
        all_pnl = [t.pnl for fold in result.fold_results for t in fold.trades if t.pnl != 0]
        
        if all_pnl:
            # Histogram
            axes[0].hist(all_pnl, bins=30, color='#2196F3', alpha=0.7, edgecolor='white')
            axes[0].axvline(x=0, color='red', linestyle='--')
            axes[0].axvline(x=np.mean(all_pnl), color='green', linestyle='--',
                           label=f'Media: ${np.mean(all_pnl):.2f}')
            axes[0].set_xlabel('P&L ($)')
            axes[0].set_ylabel('Frequenza')
            axes[0].set_title('Distribuzione P&L per Trade')
            axes[0].legend()
            
            # Box plot per fold
            pnl_by_fold = [[t.pnl for t in fold.trades if t.pnl != 0] 
                          for fold in result.fold_results]
            pnl_by_fold = [p for p in pnl_by_fold if p]  # Rimuovi vuoti
            
            if pnl_by_fold:
                axes[1].boxplot(pnl_by_fold)
                axes[1].axhline(y=0, color='red', linestyle='--')
                axes[1].set_xlabel('Fold')
                axes[1].set_ylabel('P&L ($)')
                axes[1].set_title('P&L per Fold')
        
        plt.tight_layout()
        
        path = self.config.output_dir / 'returns_distribution.png'
        plt.savefig(path, dpi=150)
        plt.close()
        
        return path
    
    def _plot_fold_performance(self, result: BacktestResult) -> Path:
        """Grafico performance per fold."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        folds = result.fold_results
        fold_ids = [f.fold_id for f in folds]
        
        # 1. P&L per fold
        pnl = [f.total_pnl for f in folds]
        colors = ['#4CAF50' if p > 0 else '#F44336' for p in pnl]
        axes[0, 0].bar(fold_ids, pnl, color=colors)
        axes[0, 0].axhline(y=0, color='black', linestyle='-')
        axes[0, 0].set_xlabel('Fold')
        axes[0, 0].set_ylabel('P&L ($)')
        axes[0, 0].set_title('P&L per Fold')
        
        # 2. Win rate per fold
        win_rates = [f.win_rate * 100 for f in folds]
        axes[0, 1].bar(fold_ids, win_rates, color='#2196F3')
        axes[0, 1].axhline(y=50, color='red', linestyle='--', label='50%')
        axes[0, 1].set_xlabel('Fold')
        axes[0, 1].set_ylabel('Win Rate (%)')
        axes[0, 1].set_title('Win Rate per Fold')
        axes[0, 1].legend()
        
        # 3. Direction accuracy per fold
        dir_acc = [f.direction_accuracy for f in folds]
        axes[1, 0].bar(fold_ids, dir_acc, color='#9C27B0')
        axes[1, 0].axhline(y=50, color='red', linestyle='--', label='Random (50%)')
        axes[1, 0].set_xlabel('Fold')
        axes[1, 0].set_ylabel('Accuracy (%)')
        axes[1, 0].set_title('Direction Accuracy per Fold')
        axes[1, 0].legend()
        
        # 4. Numero trades per fold
        num_trades = [f.num_trades for f in folds]
        axes[1, 1].bar(fold_ids, num_trades, color='#FF9800')
        axes[1, 1].set_xlabel('Fold')
        axes[1, 1].set_ylabel('# Trades')
        axes[1, 1].set_title('Numero Trades per Fold')
        
        plt.tight_layout()
        
        path = self.config.output_dir / 'fold_performance.png'
        plt.savefig(path, dpi=150)
        plt.close()
        
        return path
    
    def _plot_summary_dashboard(self, result: BacktestResult) -> Path:
        """Dashboard riassuntivo."""
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 3, figure=fig)
        
        # Metriche principali come testo
        ax_metrics = fig.add_subplot(gs[0, :])
        ax_metrics.axis('off')
        
        metrics_text = f"""
        ╔══════════════════════════════════════════════════════════════════════════════════════════╗
        ║                              PROFETA BACKTEST SUMMARY                                     ║
        ╠══════════════════════════════════════════════════════════════════════════════════════════╣
        ║                                                                                          ║
        ║   PERFORMANCE                              RISK METRICS                                  ║
        ║   ───────────                              ────────────                                  ║
        ║   Initial Capital:  ${result.initial_capital:>12,.0f}       Sharpe Ratio:    {result.sharpe_ratio:>10.2f}       ║
        ║   Final Capital:    ${result.final_capital:>12,.0f}       Sortino Ratio:   {result.sortino_ratio:>10.2f}       ║
        ║   Total Return:     ${result.total_return:>12,.0f}       Max Drawdown:    {result.max_drawdown:>9.2f}%       ║
        ║   Total Return %:   {result.total_return_pct:>12.2f}%       Volatility:      {result.volatility:>9.2f}%       ║
        ║   Annualized:       {result.annualized_return:>12.2f}%       Calmar Ratio:    {result.calmar_ratio:>10.2f}       ║
        ║                                                                                          ║
        ║   TRADING STATS                            PREDICTION ACCURACY                           ║
        ║   ─────────────                            ───────────────────                           ║
        ║   Total Trades:     {result.total_trades:>12}       Avg RMSE:        {result.avg_rmse:>10.4f}       ║
        ║   Win Rate:         {result.win_rate*100:>11.2f}%       Avg MAE:         {result.avg_mae:>10.4f}       ║
        ║   Profit Factor:    {result.profit_factor:>12.2f}       Direction Acc:   {result.avg_direction_accuracy:>9.2f}%       ║
        ║   Avg Win:          ${result.avg_win:>11,.0f}                                                 ║
        ║   Avg Loss:         ${result.avg_loss:>11,.0f}                                                 ║
        ║                                                                                          ║
        ╚══════════════════════════════════════════════════════════════════════════════════════════╝
        """
        
        ax_metrics.text(0.5, 0.5, metrics_text, transform=ax_metrics.transAxes,
                       fontsize=10, verticalalignment='center', horizontalalignment='center',
                       fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Mini equity curve
        ax_equity = fig.add_subplot(gs[1, :2])
        dates = [ec[0] for ec in result.equity_curve]
        values = [ec[1] for ec in result.equity_curve]
        ax_equity.plot(dates, values, color='#2196F3', linewidth=2)
        ax_equity.fill_between(dates, result.initial_capital, values, alpha=0.3,
                              where=[v >= result.initial_capital for v in values], color='green')
        ax_equity.fill_between(dates, result.initial_capital, values, alpha=0.3,
                              where=[v < result.initial_capital for v in values], color='red')
        ax_equity.axhline(y=result.initial_capital, color='gray', linestyle='--')
        ax_equity.set_title('Equity Curve')
        ax_equity.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # Pie chart win/loss
        ax_pie = fig.add_subplot(gs[1, 2])
        if result.total_winning_trades > 0 or result.total_losing_trades > 0:
            ax_pie.pie([result.total_winning_trades, result.total_losing_trades],
                      labels=['Wins', 'Losses'],
                      colors=['#4CAF50', '#F44336'],
                      autopct='%1.1f%%',
                      startangle=90)
            ax_pie.set_title('Win/Loss Ratio')
        
        # Cumulative return per fold
        ax_fold = fig.add_subplot(gs[2, :])
        cumulative_returns = []
        current = 0
        for fold in result.fold_results:
            current += fold.total_pnl_pct
            cumulative_returns.append(current)
        
        ax_fold.bar(range(1, len(cumulative_returns)+1), cumulative_returns,
                   color=['#4CAF50' if r >= 0 else '#F44336' for r in cumulative_returns])
        ax_fold.axhline(y=0, color='black')
        ax_fold.set_xlabel('Fold')
        ax_fold.set_ylabel('Cumulative Return (%)')
        ax_fold.set_title('Cumulative Return per Fold')
        
        plt.tight_layout()
        
        path = self.config.output_dir / 'summary_dashboard.png'
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return path
    
    def save_results(self, result: BacktestResult) -> Dict[str, Path]:
        """Salva tutti i risultati."""
        paths = {}
        
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON summary
        json_path = self.config.output_dir / 'backtest_results.json'
        with open(json_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        paths['json'] = json_path
        
        # CSV trades
        if self.config.save_trades:
            all_trades = []
            for fold in result.fold_results:
                all_trades.extend([t.to_dict() for t in fold.trades])
            
            if all_trades:
                trades_df = pd.DataFrame(all_trades)
                csv_path = self.config.output_dir / 'trades.csv'
                trades_df.to_csv(csv_path, index=False)
                paths['trades_csv'] = csv_path
        
        # Excel report
        excel_path = self.config.output_dir / 'backtest_report.xlsx'
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Summary
            summary_df = pd.DataFrame([result.to_dict()['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Performance
            perf_df = pd.DataFrame([result.to_dict()['performance']])
            perf_df.to_excel(writer, sheet_name='Performance', index=False)
            
            # Risk
            risk_df = pd.DataFrame([result.to_dict()['risk_metrics']])
            risk_df.to_excel(writer, sheet_name='Risk Metrics', index=False)
            
            # Fold details
            fold_data = []
            for fold in result.fold_results:
                fold_data.append({
                    'fold_id': fold.fold_id,
                    'train_start': fold.train_start,
                    'train_end': fold.train_end,
                    'test_start': fold.test_start,
                    'test_end': fold.test_end,
                    'num_trades': fold.num_trades,
                    'win_rate': fold.win_rate,
                    'total_pnl': fold.total_pnl,
                    'sharpe_ratio': fold.sharpe_ratio,
                    'direction_accuracy': fold.direction_accuracy
                })
            fold_df = pd.DataFrame(fold_data)
            
            # Excel non supporta datetime con timezone, rimuoviamolo:
            for col in ['train_start', 'train_end', 'test_start', 'test_end']:
                if col in fold_df.columns:
                    fold_df[col] = pd.to_datetime(fold_df[col]).dt.tz_localize(None)
            
            fold_df.to_excel(writer, sheet_name='Fold Details', index=False)
            
            # Equity curve
            equity_df = pd.DataFrame(result.equity_curve, columns=['Date', 'Equity'])
            
            if 'Date' in equity_df.columns:
                equity_df['Date'] = pd.to_datetime(equity_df['Date']).dt.tz_localize(None)
                
            equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)
        
        paths['excel'] = excel_path
        
        self.logger.info(f"Risultati salvati in: {self.config.output_dir}")
        
        return paths


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           BACKTEST ENGINE                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BacktestEngine:
    """
    Motore principale del backtesting.
    
    Esegue:
    1. Generazione fold
    2. Training su ogni fold
    3. Simulazione trading
    4. Calcolo metriche
    5. Report
    """
    
    def __init__(
        self,
        backtest_config: BacktestConfig,
        model_configs: List[Dict],
        training_config: Dict,
        logger: Optional[logging.Logger] = None
    ):
        self.config = backtest_config
        self.model_configs = model_configs
        self.training_config = training_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        self.fold_generator = FoldGenerator(backtest_config, logger)
        self.report_generator = BacktestReportGenerator(backtest_config, logger)
        self.metrics_calculator = FinancialMetricsCalculator()
    
    def run(
        self,
        data: pd.DataFrame,
        timestamp_column: str,
        target_column: str
    ) -> BacktestResult:
        """
        Esegue il backtest completo.
        
        Args:
            data: DataFrame con i dati storici
            timestamp_column: Nome colonna timestamp
            target_column: Nome colonna target
            
        Returns:
            BacktestResult con tutti i risultati
        """
        self._print_banner()
        
        start_time = datetime.datetime.now()
        
        # Prepara dati
        data = data.copy()
        data[timestamp_column] = pd.to_datetime(data[timestamp_column])
        data = data.sort_values(timestamp_column).reset_index(drop=True)
        
        data_start = data[timestamp_column].min()
        data_end = data[timestamp_column].max()
        
        self.logger.info(f"Periodo dati: {data_start} → {data_end}")
        self.logger.info(f"Record totali: {len(data)}")
        
        # Genera fold
        folds = self.fold_generator.generate(data_start, data_end)
        
        if not folds:
            raise ValueError("Nessun fold generato. Verificare configurazione e dati.")
        
        # Esegui backtest per ogni fold
        fold_results = []
        all_equity_points = []
        
        simulator = TradingSimulator(self.config, self.logger)
        
        for fold in tqdm(folds, desc="Backtesting folds", colour="blue"):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"FOLD {fold.fold_id}")
            self.logger.info(f"Train: {fold.train_start} → {fold.train_end}")
            self.logger.info(f"Test:  {fold.test_start} → {fold.test_end}")
            
            # Filtra dati per fold
            train_mask = (data[timestamp_column] >= fold.train_start) & \
                        (data[timestamp_column] < fold.train_end)
            test_mask = (data[timestamp_column] >= fold.test_start) & \
                       (data[timestamp_column] < fold.test_end)
            
            train_data = data[train_mask]
            test_data = data[test_mask]
            
            if len(train_data) < 100 or len(test_data) < 10:
                self.logger.warning(f"Dati insufficienti per fold {fold.fold_id}, skip")
                continue
            
            # Train
            self.logger.info(f"Training su {len(train_data)} record...")
            trainer = LightweightTrainer(self.model_configs, self.training_config, self.logger)
            trainer.train(train_data[target_column].values)
            
            # Test
            self.logger.info(f"Testing su {len(test_data)} record...")
            
            fold_result = self._test_fold(
                fold, test_data, timestamp_column, target_column,
                trainer, simulator
            )
            
            fold_results.append(fold_result)
            
            # Aggiungi punti equity
            for i, eq in enumerate(fold_result.equity_curve):
                ts = test_data[timestamp_column].iloc[i] if i < len(test_data) else fold.test_end
                all_equity_points.append((ts, eq))
        
        # Chiudi posizioni rimanenti
        if len(test_data) > 0:
            last_price = test_data[target_column].iloc[-1]
            last_ts = test_data[timestamp_column].iloc[-1]
            simulator.close_all_positions(last_ts, last_price, fold.fold_id)
        
        end_time = datetime.datetime.now()
        
        # Calcola risultati aggregati
        result = self._aggregate_results(
            fold_results, all_equity_points, start_time, end_time, simulator
        )
        
        # Genera report
        if self.config.generate_plots:
            self.logger.info("\nGenerazione grafici...")
            self.report_generator.generate_plots(result)
        
        if self.config.generate_report:
            self.logger.info("Salvataggio report...")
            self.report_generator.save_results(result)
        
        self._print_summary(result)
        
        return result
    
    def _test_fold(
        self,
        fold: FoldWindow,
        test_data: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
        trainer: LightweightTrainer,
        simulator: TradingSimulator
    ) -> FoldResult:
        """Esegue il test su un singolo fold."""
        
        predictions = []
        actuals = []
        current_prices = []
        
        fold_trades = []
        fold_equity = [simulator.capital]
        
        target_values = test_data[target_column].values
        timestamps = test_data[timestamp_column].values
        
        # Lookback per previsioni
        lookback = max(cfg.get('sequence_length', 60) for cfg in self.model_configs)
        
        for i in range(lookback, len(target_values) - 1):
            current_price = target_values[i]
            actual_next = target_values[i + 1]
            timestamp = pd.Timestamp(timestamps[i])
            
            # Genera previsione
            history = target_values[:i+1]
            pred, model_preds = trainer.predict(history)
            prediction = pred[0]
            
            predictions.append(prediction)
            actuals.append(actual_next)
            current_prices.append(current_price)
            
            # Simula trading
            trade = simulator.process_bar(
                timestamp=timestamp,
                current_price=current_price,
                prediction=prediction,
                actual_next=actual_next,
                model_predictions=[p[0] for p in model_preds],
                historical_prices=history,
                fold_id=fold.fold_id
            )
            
            if trade:
                fold_trades.append(trade)
            
            fold_equity.append(simulator.get_equity(current_price))
        
        # Calcola metriche fold
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        current_prices = np.array(current_prices)
        
        # Metriche previsione
        rmse = np.sqrt(mean_squared_error(actuals, predictions)) if len(actuals) > 0 else 0
        mae = mean_absolute_error(actuals, predictions) if len(actuals) > 0 else 0
        mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100 if len(actuals) > 0 else 0
        r2 = r2_score(actuals, predictions) if len(actuals) > 1 else 0
        
        direction_accuracy = self.metrics_calculator.calculate_direction_accuracy(
            predictions, actuals, current_prices
        )
        
        # Metriche trading
        winning = [t for t in fold_trades if t.pnl > 0]
        losing = [t for t in fold_trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in fold_trades)
        
        returns = self.metrics_calculator.calculate_returns(fold_equity)
        sharpe = self.metrics_calculator.calculate_sharpe_ratio(
            returns, self.config.risk_free_rate
        ) if len(returns) > 1 else 0
        
        max_dd, _, _, _ = self.metrics_calculator.calculate_max_drawdown(fold_equity)
        
        return FoldResult(
            fold_id=fold.fold_id,
            train_start=fold.train_start,
            train_end=fold.train_end,
            test_start=fold.test_start,
            test_end=fold.test_end,
            rmse=rmse,
            mae=mae,
            mape=mape,
            r2=r2,
            direction_accuracy=direction_accuracy,
            num_trades=len(fold_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            total_pnl_pct=(total_pnl / self.config.initial_capital) * 100,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            trades=fold_trades,
            equity_curve=fold_equity
        )
    
    def _aggregate_results(
        self,
        fold_results: List[FoldResult],
        equity_points: List[Tuple[datetime.datetime, float]],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        simulator: TradingSimulator
    ) -> BacktestResult:
        """Aggrega i risultati di tutti i fold."""
        
        # Metriche aggregate
        total_trades = sum(f.num_trades for f in fold_results)
        total_winning = sum(f.winning_trades for f in fold_results)
        total_losing = sum(f.losing_trades for f in fold_results)
        
        final_capital = simulator.capital
        total_return = final_capital - self.config.initial_capital
        total_return_pct = (total_return / self.config.initial_capital) * 100
        
        # Annualized return
        days = (end_time - start_time).days
        if days > 0:
            annualized = ((final_capital / self.config.initial_capital) ** (365 / days) - 1) * 100
        else:
            annualized = 0
        
        # Full equity curve
        equity_values = [eq[1] for eq in equity_points]
        
        # Risk metrics
        returns = self.metrics_calculator.calculate_returns(equity_values) if len(equity_values) > 1 else np.array([0])
        
        sharpe = self.metrics_calculator.calculate_sharpe_ratio(returns, self.config.risk_free_rate)
        sortino = self.metrics_calculator.calculate_sortino_ratio(returns, self.config.risk_free_rate)
        max_dd, _, _, dd_duration = self.metrics_calculator.calculate_max_drawdown(equity_values)
        volatility = self.metrics_calculator.calculate_volatility(returns)
        calmar = self.metrics_calculator.calculate_calmar_ratio(annualized, max_dd)
        
        # Win/Loss stats
        all_trades = [t for f in fold_results for t in f.trades]
        wins = [t.pnl for t in all_trades if t.pnl > 0]
        losses = [t.pnl for t in all_trades if t.pnl < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        profit_factor = sum(wins) / abs(sum(losses)) if losses else float('inf')
        
        # Prediction metrics
        avg_rmse = np.mean([f.rmse for f in fold_results])
        avg_mae = np.mean([f.mae for f in fold_results])
        avg_dir_acc = np.mean([f.direction_accuracy for f in fold_results])
        
        return BacktestResult(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            fold_results=fold_results,
            total_trades=total_trades,
            total_winning_trades=total_winning,
            total_losing_trades=total_losing,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration_days=dd_duration,
            volatility=volatility,
            win_rate=total_winning / total_trades if total_trades > 0 else 0,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_rmse=avg_rmse,
            avg_mae=avg_mae,
            avg_direction_accuracy=avg_dir_acc,
            equity_curve=equity_points
        )
    
    def _print_banner(self) -> None:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗  █████╗  ██████╗██╗  ██╗████████╗███████╗███████╗████████╗         ║
║   ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝         ║
║   ██████╔╝███████║██║     █████╔╝    ██║   █████╗  ███████╗   ██║            ║
║   ██╔══██╗██╔══██║██║     ██╔═██╗    ██║   ██╔══╝  ╚════██║   ██║            ║
║   ██████╔╝██║  ██║╚██████╗██║  ██╗   ██║   ███████╗███████║   ██║            ║
║   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝   ╚═╝            ║
║                                                                              ║
║   PROFETA Backtesting Framework v1.0                                         ║
║   BilliDynamics™ - Eng. Emilio Billi                                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def _print_summary(self, result: BacktestResult) -> None:
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           BACKTEST COMPLETATO                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   PERFORMANCE                              RISK                              ║
║   ───────────                              ────                              ║
║   Capitale Iniziale: ${result.initial_capital:>10,.0f}       Sharpe Ratio:   {result.sharpe_ratio:>8.2f}        ║
║   Capitale Finale:   ${result.final_capital:>10,.0f}       Sortino Ratio:  {result.sortino_ratio:>8.2f}        ║
║   Rendimento:        {result.total_return_pct:>10.2f}%       Max Drawdown:   {result.max_drawdown:>7.2f}%        ║
║   Annualizzato:      {result.annualized_return:>10.2f}%       Volatilità:     {result.volatility:>7.2f}%        ║
║                                                                              ║
║   TRADING                                  PREVISIONI                        ║
║   ───────                                  ──────────                        ║
║   Trades Totali:     {result.total_trades:>10}       RMSE:           {result.avg_rmse:>8.4f}        ║
║   Win Rate:          {result.win_rate*100:>9.2f}%       MAE:            {result.avg_mae:>8.4f}        ║
║   Profit Factor:     {result.profit_factor:>10.2f}       Direction Acc:  {result.avg_direction_accuracy:>7.2f}%        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              CONFIGURATION LOADER                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BacktestConfigLoader:
    """Carica configurazione da file INI."""
    
    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"File non trovato: {config_path}")
        
        self.config.read(self.config_path)
    
    def get_backtest_config(self) -> BacktestConfig:
        return BacktestConfig.from_config(self.config)
    
    def get_model_configs(self) -> List[Dict]:
        configs = []
        model_sections = sorted(
            [s for s in self.config.sections() if s.startswith("MODEL_")],
            key=lambda x: int(x.split('_')[1])
        )
        
        num_models = int(self.config['ENSEMBLE'].get('num_models', len(model_sections))) \
            if self.config.has_section('ENSEMBLE') else len(model_sections)
        
        for section in model_sections[:num_models]:
            configs.append({
                'sequence_length': int(self.config[section].get('sequence_length', 60)),
                'lstm_units': int(self.config[section].get('lstm_units', 64)),
                'dropout_rate': float(self.config[section].get('dropout_rate', 0.2)),
                'use_bidirectional': self.config[section].getboolean('use_bidirectional', False),
                'num_lstm_layers': int(self.config[section].get('num_lstm_layers', 4))
            })
        
        return configs
    
    def get_training_config(self) -> Dict:
        return {
            'num_epochs': int(self.config['TRAINING'].get('num_epochs', 10)),
            'batch_size': int(self.config['TRAINING'].get('batch_size', 32)),
            'learning_rate': float(self.config['TRAINING'].get('learning_rate', 0.001)),
            'train_test_split': float(self.config['DATA'].get('train_test_split', 0.8))
        }
    
    def get_data_config(self) -> Dict:
        return {
            'data_path': self.config['DATA']['data_path'],
            'target_column': self.config['DATA']['target_column'],
            'timestamp_column': self.config['PREDICTION']['timestamp_column']
        }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                   MAIN                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def main(config_path: str = 'config-lstm.ini') -> BacktestResult:
    """Entry point."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    logger = logging.getLogger("BACKTEST")
    
    try:
        # Carica configurazione
        loader = BacktestConfigLoader(config_path)
        
        backtest_config = loader.get_backtest_config()
        model_configs = loader.get_model_configs()
        training_config = loader.get_training_config()
        data_config = loader.get_data_config()
        
        # Carica dati
        logger.info(f"Caricamento dati da: {data_config['data_path']}")
        data = pd.read_csv(data_config['data_path'])
        
        # Crea engine
        engine = BacktestEngine(
            backtest_config=backtest_config,
            model_configs=model_configs,
            training_config=training_config,
            logger=logger
        )
        
        # Esegui backtest
        result = engine.run(
            data=data,
            timestamp_column=data_config['timestamp_column'],
            target_column=data_config['target_column']
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Errore: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config-lstm.ini'
    main(config_file)
