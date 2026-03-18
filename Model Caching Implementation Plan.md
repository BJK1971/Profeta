# Model Caching Implementation Plan

## Goal Description
The problem is that `profeta-universal.py` currently trains the ensemble of LSTM models from scratch every time it is invoked. Since `Run_profeta_real_time.py` runs the scripts in a loop every few hours, this causes excessive compute usage and delays. The goal is to implement a caching mechanism so that the script can save the trained model and data scaler (`SequencePreparator`), and reload them in subsequent runs instead of retraining.

## Proposed Changes

### Configuration
#### [MODIFY] `profeta-universal.py`
In `TrainingConfig`:
- Add `load_existing_model: bool = True`
- Add `model_cache_dir: str = "./models"`
- Read these values in `TrainingConfig.from_config()` pulling from `[TRAINING]`.

### Model Save/Load Logic
#### [MODIFY] `profeta-universal.py`
In `PROFETAEngine._train_nested_split()` and `PROFETAEngine._train_legacy_split()`:
We will wrap the training process in a cache check:
```python
models_dir = Path(self.train_config.model_cache_dir)
seq_prep_path = models_dir / "seq_prep.pkl"
ensemble_meta_path = models_dir / "ensemble_meta.json"

if self.train_config.load_existing_model and ensemble_meta_path.exists() and seq_prep_path.exists():
    self.logger.info(f"Loading existing models from {models_dir}")
    self.seq_prep = SequencePreparator.load(seq_prep_path, self.logger)
    # Recreate the ensemble manager and load weights
    self.ensemble = EnsembleManager(self.model_configs, self.train_config, self.logger)
    self.ensemble.load_all(models_dir)
    # Generate mock HybridMetrics or return empty as training was skipped
    return HybridMetrics()
else:
    # ... proceed with normal training ...
    
    # After training, save to cache
    self.logger.info(f"Saving models and scaler to {models_dir}")
    self.seq_prep.save(seq_prep_path)
    self.ensemble.save_all(models_dir)
```

**Note on fine_tuning**: `TrainingConfig` already has a `fine_tuning` flag. In the future, if you want it to load the model BUT train for a few epochs incrementally instead of skipping entirely, we can just trigger `train_all()` after `load_all()`. For now, `load_existing_model` will skip training.

## Verification Plan

### Automated Tests
- Run `python profeta-universal.py` manually. The first time, it should execute the long training process and save to `./models`.
- Run `python profeta-universal.py` a second time. It should instantly log `Loading existing models from models` and skip the training phase, finishing execution in seconds.
- Verify `PROFETA_Report...pdf` is still generated correctly without crashes using the loaded predictions.
