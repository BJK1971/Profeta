# PROFETA - Multi-Epic Management Guide

## 📋 Panoramica

Il **Multi-Epic Manager** gestisce contemporaneamente multiple asset (EURUSD, BTCUSD) coordinando i training per evitare sovrapposizioni.

---

## 🚀 Avvio Rapido

### **Avvia Tutti i Servizi**
```bash
cd ~/Profeta
./multi-epic-manager.sh start
```

### **Verifica Stato**
```bash
./multi-epic-manager.sh status
```

### **Ferma Tutti i Servizi**
```bash
./multi-epic-manager.sh stop
```

---

## ⏰ Coordinamento Training

### **Problema**
Se EURUSD e BTCUSD eseguono il training contemporaneamente:
- Consumo eccessivo di CPU/GPU
- Conflitti sui file di output
- Possibili crash

### **Soluzione**
I training vengono sfalsati di **30 minuti**:

| Epic | Minuto di avvio training | Descrizione |
|------|--------------------------|-------------|
| **EURUSD** | :00 | Training all'inizio dell'ora |
| **BTCUSD** | :30 | Training a metà ora |

```
14:00 → EURUSD training start
14:30 → BTCUSD training start
15:00 → EURUSD training start
15:30 → BTCUSD training start
```

---

## 📁 File di Configurazione

Ogni epic ha il suo config file:

```
BKTEST/
├── config-lstm-EURUSD.ini    # Configurazione EURUSD
├── config-lstm-BTCUSD.ini    # Configurazione BTCUSD
└── config-lstm-backtest.ini  # Template
```

### **Creare Config per Nuova Epic**
```bash
cd ~/Profeta
cp BKTEST/config-lstm-backtest.ini BKTEST/config-lstm-ETHUSD.ini
sed -i 's/^epic = .*/epic = ETHUSD/' BKTEST/config-lstm-ETHUSD.ini
```

---

## 📊 Log Files

Tutti i log sono centralizzati in `~/Profeta/logs/`:

| File | Descrizione |
|------|-------------|
| `orchestrator-EURUSD.log` | Ciclo orario EURUSD |
| `orchestrator-BTCUSD.log` | Ciclo orario BTCUSD |
| `trading-bot-EURUSD.log` | Trading bot EURUSD |
| `trading-bot-BTCUSD.log` | Trading bot BTCUSD |
| `profeta-v5.log` | Motore previsioni (comune) |

---

## 🎯 Monitoraggio

### **Comando Singolo per Tutto**
```bash
./logs-monitor.sh MULTI
```

### **Log Separati**
```bash
# EURUSD
tail -f ~/Profeta/logs/orchestrator-EURUSD.log
tail -f ~/Profeta/logs/trading-bot-EURUSD.log

# BTCUSD
tail -f ~/Profeta/logs/orchestrator-BTCUSD.log
tail -f ~/Profeta/logs/trading-bot-BTCUSD.log

# Previsioni combinate
tail -f ~/Profeta/logs/profeta-v5.log | grep -E 'PRED_NUM|STATUS TRADES'
```

### **Stato P/L**
```bash
# P/L EURUSD
grep 'STATUS TRADES.*EURUSD' ~/Profeta/logs/profeta-v5.log | tail -1

# P/L BTCUSD
grep 'STATUS TRADES.*BTCUSD' ~/Profeta/logs/profeta-v5.log | tail -1

# P/L Totale
grep 'STATUS TRADES' ~/Profeta/logs/profeta-v5.log | tail -1
```

---

## ⚙️ Comandi Disponibili

| Comando | Descrizione |
|---------|-------------|
| `./multi-epic-manager.sh start` | Avvia tutti i servizi |
| `./multi-epic-manager.sh stop` | Ferma tutti i servizi |
| `./multi-epic-manager.sh status` | Mostra stato |
| `./multi-epic-manager.sh restart` | Riavvia tutto |

---

## 🔧 Aggiungere Nuova Epic

### **1. Crea Configurazione**
```bash
cp BKTEST/config-lstm-backtest.ini BKTEST/config-lstm-ETHUSD.ini
sed -i 's/^epic = .*/epic = ETHUSD/' BKTEST/config-lstm-ETHUSD.ini
```

### **2. Modifica Multi-Epic Manager**
Apri `multi-epic-manager.sh` e aggiungi l'epic:

```bash
EPICS=("EURUSD" "BTCUSD" "ETHUSD")
```

### **3. Avvia**
```bash
./multi-epic-manager.sh start
```

---

## ⚠️ Risoluzione Problemi

### **Training Si Sovrappongono**

**Sintomo:** Entrambi i training partono allo stesso tempo

**Soluzione:** Verifica l'offset nel config:
```bash
grep 'TRAINING_OFFSET_MINUTES' multi-epic-manager.sh
# Dovrebbe essere 30
```

### **Processi Non Rimangono Attivi**

**Sintomo:** I processi muoiono subito dopo l'avvio

**Soluzione:** In WSL, usa terminali separati:

**Terminale 1 - EURUSD:**
```bash
wsl -d Ubuntu-24.04
cd ~/Profeta
~/miniconda3/envs/profeta/bin/python Run_profeta_real_time.py \
  --config BKTEST/config-lstm-EURUSD.ini --epic EURUSD
```

**Terminale 2 - BTCUSD:**
```bash
wsl -d Ubuntu-24.04
cd ~/Profeta
~/miniconda3/envs/profeta/bin/python Run_profeta_real_time.py \
  --config BKTEST/config-lstm-BTCUSD.ini --epic BTCUSD
```

**Terminale 3 - Trading Bot EURUSD:**
```bash
wsl -d Ubuntu-24.04
cd ~/Profeta
~/miniconda3/envs/profeta/bin/python profeta_trading_bot.py --epic EURUSD
```

**Terminale 4 - Trading Bot BTCUSD:**
```bash
wsl -d Ubuntu-24.04
cd ~/Profeta
~/miniconda3/envs/profeta/bin/python profeta_trading_bot.py --epic BTCUSD
```

### **Log Non Vengono Scritti**

**Soluzione:** Verifica permessi:
```bash
chmod 755 ~/Profeta/logs
```

---

## 📈 Best Practices

1. **Monitora regolarmente** lo stato con `./multi-epic-manager.sh status`
2. **Verifica i log** ogni ora per assicurarti che i training non si sovrappongano
3. **Controlla il P/L** combinato di tutte le epic
4. **Riavvia i servizi** se noti comportamenti anomali

---

## 🎯 Esempio Sessione Tipica

```bash
# 1. Avvia tutti i servizi
./multi-epic-manager.sh start

# 2. Verifica stato
./multi-epic-manager.sh status

# 3. Monitora previsioni
tail -f ~/Profeta/logs/profeta-v5.log | grep PRED_NUM

# 4. Controlla P/L
watch -n 60 "grep 'STATUS TRADES' ~/Profeta/logs/profeta-v5.log"

# 5. A fine giornata, ferma tutto
./multi-epic-manager.sh stop
```

---

*Ultimo aggiornamento: Marzo 2026*
