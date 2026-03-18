# Modifica Logica Entry Bot per Previsioni Orarie

Attualmente il bot è "cieco" perché lavora solo sulla primissima candela futura (`horizon=1`), la quale ha in genere una variazione piccolissima (spesso classificata come `FLAT` o `0`). Inoltre, la soglia di attivazione predefinita (`0.001` = `0.1%`) è troppo alta persino per le ampiezze che si sviluppano dopo 72 ore.

## Proposed Changes

### 1. `profeta_trading_bot.py`
Aggiorneremo la funzione `run_cycle` per rendere il bot molto più intelligente:
- Invece di limitarsi a `horizon = 1`, il bot esaminerà **tutti gli orizzonti temporali predetti** nel CSV (da 1 a 72 ore).
- Cercherà la previsione ("row") che presenta la **massima variazione percentuale in valore assoluto**, purché la direzionalità sia nettamente `1` (UP) o `-1` (DOWN).
- Il bot utilizzerà questa previsione (il "segnale più forte") per decidere se aprire una posizione `BUY` o `SELL`.

#### [MODIFY] profeta_trading_bot.py
Verrà modificato il blocco di codice che estrae `last_row` all'interno della funzione `run_cycle()`.

### 2. `config-lstm.ini`
Aggiungeremo una sezione `[CAPITAL_DEMO]` (se non presente) per configurare esplicitamente un **`activation_threshold`** più basso.
- Dato che la massima variazione predetta su 72 ore è di circa `0.0007` (0.07%), una soglia target sensata per attivare il bot su un trend prolungato è `0.0001` (0.01%) oppure `0.0002` (0.02%).

#### [MODIFY] config-lstm.ini
Aggiungeremo alla fine del file:
```ini
[CAPITAL_DEMO]
epic = BTCUSD
trade_size = 0.01
sl_pts = 100
tp_pts = 300
activation_threshold = 0.0002
```

## Verification Plan

### Test Automatici / Verifica a vista
- Dopo aver applicato le modifiche, basterà lanciare `python profeta_trading_bot.py` dal terminale (nella dir `C:\work\gitrepo\Profeta\`).
- Il bot leggerà l'attuale file `real_time_ens_hours.csv` da WSL (o Windows, dipende dal mount). 
- Vedremo stampato a schermo il "SEGNALE SHORT SCATTATO" invece del silenzio completo, perché la variazione a h=72 supera il nuovo `0.0002` ed è `DOWN` (-1).
