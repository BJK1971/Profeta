# PROFETA - Log Files Guide

## 📁 Directory Log

Tutti i file di log sono centralizzati in:
```
~/Profeta/logs/
```

---

## 📄 File Log Principali

| File | Descrizione | Quando usarlo |
|------|-------------|---------------|
| **profeta-v5.log** | Log principale del motore di previsione | Monitoraggio generale |
| **trading-bot-{EPIC}.log** | Log del trading bot (es: `trading-bot-EURUSD.log`) | Debug trading |
| **orchestrator-{EPIC}.log** | Log dell'orchestratore (es: `orchestrator-EURUSD.log`) | Verifica ciclo orario |

---

## 🎯 Monitoraggio Rapido

### **Comando Singolo per Tutti i Log**
```bash
cd ~/Profeta
./logs-monitor.sh EURUSD
```

### **Log Separati**

```bash
# Previsioni (aggiornamento orario)
tail -f ~/Profeta/logs/profeta-v5.log | grep "PRED_NUM"

# Trading (P/L e segnali)
tail -f ~/Profeta/logs/profeta-v5.log | grep "STATUS TRADES"

# Trading Bot (dettagliato)
tail -f ~/Profeta/logs/trading-bot-EURUSD.log

# Orchestratore (ciclo orario)
tail -f ~/Profeta/logs/orchestrator-EURUSD.log
```

---

## 📊 Cosa Cercare nei Log

### **profeta-v5.log**

| Pattern | Significato |
|---------|-------------|
| `PRED_NUM \| H+1h` | Previsione a 1 ora |
| `PRED_NUM \| H+24h` | Previsione a 24 ore |
| `PRED_NUM \| H+72h` | Previsione a 72 ore |
| `Chg: +X.XX%` | Variazione percentuale prevista |
| `STATUS TRADES` | Stato posizioni aperte con P/L |
| `Strategia: Il picco direzionale` | Segnale individuato |
| `SEGNALE LONG/SHORT SCATTATO` | Ordine eseguito |
| `Conferma Strategia` | Posizione confermata |
| `Inversione di trend` | Chiusura posizione |

**Esempio:**
```
2026-03-20 17:46:49,337 | INFO | PRED_NUM | H+71h | Price: 1.1600 | Chg: +0.378% | Dir: UP
2026-03-20 17:46:49,337 | INFO | STATUS TRADES: [BUY 100.0 EURUSD -> P/L: -0.09 $ (-0.08%)] | TOTALE P/L: 23.03 $
```

---

### **trading-bot-{EPIC}.log**

| Pattern | Significato |
|---------|-------------|
| `Autenticazione ... completata` | Login a Capital.com riuscito |
| `STATUS TRADES` | Riepilogo posizioni |
| `Strategia: Il picco direzionale` | Analisi previsioni |
| `Conferma Strategia` | Mantiene posizione |
| `Inversione di trend` | Chiude e inverte |
| `Esecuzione ordine` | Trade eseguito |

**Esempio:**
```
2026-03-20 17:46:49,337 | INFO | STATUS TRADES: [BUY 100.0 EURUSD -> P/L: -0.09 $ (-0.08%)]
2026-03-20 17:46:49,337 | INFO | Strategia: Il picco direzionale previsto è alle ore 2026-03-23T14:00:00
2026-03-20 17:46:49,579 | INFO | Conferma Strategia: Manteniamo aperta la posizione BUY su EURUSD
```

---

### **orchestrator-{EPIC}.log**

| Pattern | Significato |
|---------|-------------|
| `Inizio ciclo di esecuzione` | Nuovo ciclo orario avviato |
| `Scaricamento blocco` | Download dati da Capital.com |
| `Sincronizzazione ... completata` | Dati scaricati |
| `Fine ciclo. Attesa per` | Inizio attesa prossimo ciclo |

**Esempio:**
```
2026-03-20 17:00:00,000 | INFO | --- Inizio ciclo di esecuzione ---
2026-03-20 17:00:01,234 | INFO | Scaricamento blocco: 2026-03-04T00:00:00 -> 2026-03-20T16:00:00
2026-03-20 17:00:30,567 | INFO | Sincronizzazione di 8000 candele completata
2026-03-20 17:05:00,890 | INFO | --- Fine ciclo. Attesa per 0h 54m 59s ---
```

---

## 🔍 Comandi Utili

### **Verifica Frequenza Previsioni**
```bash
# Conta esecuzioni oggi
grep "ONCE mode" ~/Profeta/logs/profeta-v5.log | grep "$(date +%Y-%m-%d)" | wc -l

# Dovresti vedere 1 esecuzione per ora
# Se vedi più esecuzioni/ora, c'è un problema
```

### **Monitora P/L**
```bash
# Aggiornamento ogni 30 secondi
watch -n 30 "grep 'STATUS TRADES' ~/Profeta/logs/profeta-v5.log | tail -1"
```

### **Cerca Errori**
```bash
grep -i "error\|exception\|failed" ~/Profeta/logs/*.log | tail -20
```

### **Verifica Previsioni Generate Oggi**
```bash
grep "PRED_NUM" ~/Profeta/logs/profeta-v5.log | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## ⚠️ Problemi Comuni

### **1. Troppe Esecuzioni all'Ora**
```bash
# Verifica
grep "Complete" ~/Profeta/logs/profeta-v5.log | grep "$(date +%Y-%m-%d %H)" | wc -l

# Se > 1, c'è un problema con l'orchestratore
# Soluzione: Riavvia l'orchestratore
```

### **2. Nessuna Previsione da >1 Ora**
```bash
# Verifica ultima esecuzione
tail -20 ~/Profeta/logs/orchestrator-{EPIC}.log

# Se l'orchestratore è fermo, riavvialo
```

### **3. Trading Bot Non Legge Previsioni**
```bash
# Verifica che il bot stia leggendo
tail -20 ~/Profeta/logs/trading-bot-{EPIC}.log | grep "Strategia"

# Se non ci sono aggiornamenti, riavvia il bot
```

---

## 📋 Script di Monitoraggio

### **logs-monitor.sh**

Script interattivo per monitorare tutti i log:

```bash
cd ~/Profeta
./logs-monitor.sh EURUSD
```

**Menu disponibile:**
1. Tutti i log (multi-panel)
2. Solo previsioni (PRED_NUM)
3. Solo trading (trading-bot)
4. Solo orchestratore
5. P/L in tempo reale
6. Errori e warning
7. Ultime 50 righe
0. Esci

---

## 🎯 Best Practices

1. **Monitora regolarmente** il P/L con `watch -n 30`
2. **Verifica una volta al giorno** che le previsioni vengano generate ogni ora
3. **Controlla gli errori** settimanalmente
4. **Ruota i log** mensilmente (i file possono diventare grandi)

---

*Ultimo aggiornamento: Marzo 2026*
