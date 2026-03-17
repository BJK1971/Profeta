# PROFETA Universal v5.0 - Enterprise Dashboard

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                           ║
║     ██████╗ ██████╗  ██████╗ ███████╗███████╗████████╗ █████╗     ██╗   ██╗██╗            ║
║     ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗    ██║   ██║██║            ║
║     ██████╔╝██████╔╝██║   ██║█████╗  █████╗     ██║   ███████║    ██║   ██║██║            ║
║     ██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══██║    ██║   ██║██║            ║
║     ██║     ██║  ██║╚██████╔╝██║     ███████╗   ██║   ██║  ██║    ╚██████╔╝██║            ║
║     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝     ╚═════╝ ╚═╝            ║
║                                                                                           ║
║                         ENTERPRISE MONITORING DASHBOARD                                   ║
║                                   Version 1.0.0                                           ║
║                                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

## 📋 Descrizione

Dashboard web autocontenuta per il monitoraggio in tempo reale di **PROFETA Universal v5.0**, il sistema di previsione multi-dominio basato su ensemble di reti LSTM.

### Caratteristiche Principali

- 🖥️ **Interfaccia Hi-Tech** - Design dark mode con estetica da terminale di trading istituzionale
- 📊 **Metriche Real-Time** - KPI di performance (R², RMSE, MAE, Accuracy, F1)
- 📈 **Visualizzazione Previsioni** - Tabella interattiva con segnali colorati e confidence
- ⚙️ **Configuration Viewer** - Visualizzazione completa del file INI (sola lettura)
- 🔄 **Auto-Refresh** - Aggiornamento automatico ogni 30 secondi
- 📱 **Responsive** - Ottimizzato per desktop e tablet

---

## 🚀 Installazione Rapida

### Prerequisiti

- Python 3.10+ (compatibile con l'ambiente Conda di PROFETA)
- pip (gestore pacchetti Python)

### 1. Installazione Dipendenze

```bash
# Attiva il tuo ambiente conda (se usi conda)
conda activate profeta

# Installa le dipendenze
pip install flask flask-cors
```

### 2. Avvio Dashboard

```bash
# Naviga nella cartella UI
cd /path/to/PROFETA/UI

# Avvia con path al config
python server.py --config ../config-lstm.ini

# Oppure specifica host e porta
python server.py --config ../config-lstm.ini --host 0.0.0.0 --port 8080
```

### 3. Accesso

Apri il browser e vai a: **http://127.0.0.1:5000**

---

## 📁 Struttura Directory

```
PROFETA-v5/
├── profeta-universal.py          # Script principale PROFETA
├── config-lstm.ini               # File configurazione
├── data/
│   └── ...                       # Dati di training/trading
├── output/
│   ├── predictions.json          # Output JSON con metriche
│   └── real_time_*.csv           # Output CSV previsioni
├── models/
│   └── ...                       # Modelli salvati
├── logs/
│   └── ...                       # File di log
│
└── UI/                           # ← DASHBOARD (questa cartella)
    ├── server.py                 # Backend Flask
    ├── requirements.txt          # Dipendenze Python
    ├── README.md                 # Questa documentazione
    ├── static/
    │   ├── css/
    │   │   └── dashboard.css     # Stili principali
    │   └── js/
    │       └── dashboard.js      # Logica frontend
    └── templates/
        └── index.html            # Template pagina
```

---

## ⚙️ Configurazione

### Opzioni Linea di Comando

| Opzione | Default | Descrizione |
|---------|---------|-------------|
| `--config, -c` | Auto-detect | Path al file `config-lstm.ini` |
| `--port, -p` | 5000 | Porta HTTP |
| `--host, -H` | 127.0.0.1 | Host binding (usa `0.0.0.0` per accesso LAN) |
| `--debug, -d` | False | Abilita modalità debug Flask |

### Esempi

```bash
# Uso base con auto-detect
python server.py

# Config specifico
python server.py --config /home/user/profeta/config-lstm.ini

# Accesso da rete locale
python server.py --host 0.0.0.0 --port 8080

# Modalità sviluppo
python server.py --debug
```

---

## 🔌 API Endpoints

La dashboard espone le seguenti API REST (utili per integrazioni):

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/` | GET | Pagina dashboard |
| `/api/status` | GET | Stato sistema (uptime, path file, etc.) |
| `/api/config` | GET | Configurazione INI parsata |
| `/api/predictions/csv` | GET | Previsioni dal file CSV |
| `/api/predictions/json` | GET | Previsioni e metriche dal JSON |
| `/api/metrics` | GET | Solo metriche (endpoint veloce) |

### Parametri Query

- `limit`: Numero max di record (es: `?limit=100`)
- `offset`: Offset per paginazione (es: `?offset=50`)

---

## 🎨 Personalizzazione

### Tema Colori

I colori sono definiti come variabili CSS in `static/css/dashboard.css`:

```css
:root {
    --bg-primary: #06080c;        /* Background principale */
    --accent-primary: #00d4ff;    /* Colore accent (ciano) */
    --signal-buy: #00ff88;        /* Verde per segnali BUY */
    --signal-sell: #ff3366;       /* Rosso per segnali SELL */
    --signal-hold: #ffc107;       /* Giallo per HOLD */
}
```

### Intervallo Refresh

Modifica in `static/js/dashboard.js`:

```javascript
const CONFIG = {
    REFRESH_INTERVAL: 30000,  // Millisecondi (default: 30s)
    PREDICTIONS_LIMIT: 100,   // Righe per pagina
};
```

---

## 🐛 Troubleshooting

### "File di configurazione non trovato"

Verifica che il path sia corretto:
```bash
python server.py --config /path/assoluto/al/config-lstm.ini
```

### "CSV previsioni non trovato"

La dashboard cerca automaticamente i file in:
1. `../output/real_time_*.csv`
2. `../real_time_*.csv`
3. `../data/real_time_*.csv`

Assicurati che PROFETA abbia generato almeno un'esecuzione.

### Porta già in uso

Specifica una porta diversa:
```bash
python server.py --port 8888
```

### Accesso da altri dispositivi in LAN

Usa `--host 0.0.0.0` e assicurati che il firewall permetta la porta.

---

## 📄 Licenza

**Proprietaria** - © 2026 BilliDynamics™

Questo software è parte integrante di PROFETA Universal v5.0 Enterprise.
Tutti i diritti riservati. Utilizzo consentito esclusivamente ai licenziatari autorizzati.

---

## 📞 Supporto

- **Email**: support@billidynamics.com
- **Documentazione**: https://docs.billidynamics.com
- **Licenze**: licensing@billidynamics.com

---

<p align="center">
  <strong>BilliDynamics™</strong> — Engineering Excellence<br>
  <em>www.billidynamics.com</em>
</p>
