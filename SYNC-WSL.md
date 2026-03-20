# PROFETA - WSL Synchronization Guide

## 📌 Sincronizzare da Windows a WSL

### Metodo Rapido (PowerShell)

```powershell
# Sincronizzazione completa
.\sync-to-wsl.ps1

# Dry run (vedi cosa verrebbe copiato senza copiare)
.\sync-to-wsl.ps1 --dry-run

# Verbose (mostra tutti i file)
.\sync-to-wsl.ps1 --verbose
```

### Comandi Disponibili

| Comando | Descrizione |
|---------|-------------|
| `.\sync-to-wsl.ps1` | Sincronizza tutti i file |
| `.\sync-to-wsl.ps1 -d` | Dry run (anteprima) |
| `.\sync-to-wsl.ps1 -v` | Verbose output |
| `.\sync-to-wsl.ps1 -h` | Mostra aiuto |

---

## 🔄 Cosa viene sincronizzato

### ✅ File inclusi
- Tutti i file `.py` (script Python)
- File di configurazione `.ini`
- Documentazione (`.md`, `.txt`)
- Directory di supporto (`cfx_markets/`, `UI/`, `DOCs/`, ecc.)

### ❌ File esclusi (automaticamente)
- `*.pyc` e `__pycache__/`
- File di log (`.log`, `logs/*`)
- Modelli salvati (`models/*`)
- Output previsioni (`output/*`, `reports/*`)
- Ambiente conda/venv (`conda/`, `venv/`)
- `.git/`

---

## 🚀 Workflow Consigliato

### 1. Modifica su Windows
```
# Lavora sui file in:
C:\work\gitrepo\Profeta\
```

### 2. Sincronizza in WSL
```powershell
.\sync-to-wsl.ps1
```

### 3. Esegui test in WSL
```bash
# Accedi a WSL
wsl -d Ubuntu-24.04

# Attiva ambiente conda
conda activate profeta

# Vai alla directory del progetto
cd ~/Profeta

# Esegui i test
python profeta-universal.py config-lstm.ini
```

---

## 🛠️ Risoluzione Problemi

### WSL non trovato
```
❌ WSL destination not found: \\wsl.localhost\Ubuntu-24.04\home\ubuntu\Profeta
```

**Soluzione:**
1. Avvia WSL: `wsl -d Ubuntu-24.04`
2. Lascia WSL aperto in background
3. Ripeti la sincronizzazione

### Permessi negati
```
❌ Access denied
```

**Soluzione:**
```bash
# In WSL, resetta i permessi
chmod -R 755 ~/Profeta
chown -R ubuntu:ubuntu ~/Profeta
```

---

## 📋 Sync Manuale (Alternativa)

Se lo script PowerShell non funziona, puoi usare comandi manuali:

### Da PowerShell:
```powershell
# Copia ricorsiva con robocopy
robocopy "C:\work\gitrepo\Profeta" "\\wsl.localhost\Ubuntu-24.04\home\ubuntu\Profeta" /E /XD __pycache__ logs models output reports conda /XF *.pyc *.log
```

### Da WSL:
```bash
# Copia da WSL (pull da Windows)
rsync -av --exclude '__pycache__' --exclude '*.pyc' --exclude 'logs' --exclude 'models' --exclude 'output' --exclude 'reports' /mnt/c/work/gitrepo/Profeta/ ~/Profeta/
```

---

## 🔗 Integration con Git

Se usi anche git per il versioning:

```powershell
# 1. Commit su Windows
git add .
git commit -m "Descrizione modifiche"

# 2. Sync in WSL
.\sync-to-wsl.ps1

# 3. In WSL, verifica
wsl -d Ubuntu-24.04
cd ~/Profeta
git status
```

---

## 📝 Note Importanti

1. **Ambiente Conda**: L'ambiente `profeta` esiste solo in WSL, non viene sincronizzato
2. **Modelli salvati**: La cartella `models/` è esclusa per evitare conflitti
3. **Output**: I file di output generati in WSL rimangono in WSL
4. **Credenziali**: I file con credenziali (es. `BKTEST/config-lstm-backtest.ini`) vengono sincronizzati - assicurati di avere backup sicuri

---

*Ultimo aggiornamento: Marzo 2026*
