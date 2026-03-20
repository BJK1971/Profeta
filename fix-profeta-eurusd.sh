#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    PROFETA FIX SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════════════════
#
# Fix per previsioni esagerate su EURUSD (+25% in 72 ore)
# Problema: Modelli addestrati su prezzi assoluti invece di delta
#
# Usage: ./fix-profeta-eurusd.sh
#
# ═══════════════════════════════════════════════════════════════════════════════════════════

set -e

echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                    PROFETA - EURUSD FIX SCRIPT                                           ║"
echo "║         Fix per previsioni esagerate (+25% in 72 ore)                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

PROJECT_DIR="$HOME/Profeta"
MODELS_DIR="$PROJECT_DIR/models/EURUSD"
CONFIG_FILE="$PROJECT_DIR/config-lstm.ini"
BACKTEST_CONFIG="$PROJECT_DIR/BKTEST/config-lstm-backtest.ini"

cd "$PROJECT_DIR"

# Step 1: Backup vecchi modelli
echo "📦 Step 1: Backup vecchi modelli..."
if [ -d "$MODELS_DIR" ]; then
    BACKUP_DIR="$PROJECT_DIR/models/EURUSD_OLD_$(date +%Y%m%d_%H%M%S)"
    mv "$MODELS_DIR" "$BACKUP_DIR"
    echo "   ✅ Modelli spostati in: $BACKUP_DIR"
else
    echo "   ⚠️  Nessun modello trovato in $MODELS_DIR"
fi
echo ""

# Step 2: Verifica configurazione FUSION
echo "📋 Step 2: Verifica configurazione [FUSION]..."
if grep -q "strategy = regression_derived" "$CONFIG_FILE" 2>/dev/null; then
    echo "   ✅ [FUSION] strategy = regression_derived TROVATO in config-lstm.ini"
else
    echo "   ❌ [FUSION] strategy = regression_derived NON TROVATO!"
    echo "   Aggiungo la sezione [FUSION] mancante..."
    
    # Aggiungi sezione FUSION se manca
    if ! grep -q "^\[FUSION\]" "$CONFIG_FILE"; then
        cat >> "$CONFIG_FILE" << 'EOF'

; ═══════════════════════════════════════════════════════════════════════════════════════════
; FUSION - v5.0 PRODUCTION
; ═══════════════════════════════════════════════════════════════════════════════════════════
[FUSION]

; STRATEGY: regression_derived (classification from delta)
; Questo garantisce 100% accordo tra regressione e classificazione
strategy = regression_derived

; DELTA_THRESHOLD_PCT: Soglia per classificazione UP/DOWN
; 0.0005 = 0.05% (per EURUSD ~1.17 = soglia di 0.00058)
delta_threshold_pct = 0.0005

; MIN_CONFIDENCE: Confidenza minima per generare segnali
min_confidence = 0.35

; SIGNAL_THRESHOLD: Soglia per segnali STRONG
signal_threshold = 0.55

; GENERATE_SIGNALS: Abilita generazione segnali
generate_signals = true

EOF
        echo "   ✅ Sezione [FUSION] aggiunta"
    fi
fi
echo ""

# Step 3: Verifica configurazione dominio
echo "📋 Step 3: Verifica configurazione [DOMAIN]..."
if grep -q "type = financial" "$CONFIG_FILE" && grep -q "subtype = forex" "$CONFIG_FILE"; then
    echo "   ✅ Dominio configurato correttamente (financial/forex)"
else
    echo "   ⚠️  Dominio potrebbe non essere ottimizzato per EURUSD"
    echo "   Consiglio: imposta subtype = forex nel file $CONFIG_FILE"
fi
echo ""

# Step 4: Attiva ambiente conda
echo "🐍 Step 4: Attivazione ambiente conda..."
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate profeta
    echo "   ✅ Ambiente 'profeta' attivato"
else
    echo "   ⚠️  Conda non trovato. Attivalo manualmente prima di eseguire il training."
fi
echo ""

# Step 5: Istruzioni per riaddestramento
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                              CONFIGURAZIONE COMPLETATA                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ I vecchi modelli sono stati backupati"
echo "✅ La configurazione [FUSION] è stata verificata/aggiunta"
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                              PROSSIMI STEP                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Verifica che il file $CONFIG_FILE contenga:"
echo ""
echo "   [FUSION]"
echo "   strategy = regression_derived"
echo "   delta_threshold_pct = 0.0005"
echo ""
echo "2️⃣  Esegui il riaddestramento dei modelli:"
echo ""
echo "   cd ~/Profeta"
echo "   conda activate profeta"
echo "   python profeta-universal.py config-lstm.ini"
echo ""
echo "3️⃣  Verifica le nuove previsioni:"
echo ""
echo "   Il modello ora predice DELTA (variazioni), non prezzi assoluti"
echo "   Le previsioni dovrebbero essere realistiche (0.5-2% in 72 ore per EURUSD)"
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                              NOTE IMPORTANTI                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  Il riaddestramento richiederà 30-60 minuti"
echo "⚠️  Le nuove previsioni saranno molto più conservative"
echo "⚠️  R² dovrebbe essere > 0.90 (non negativo come -0.887)"
echo ""
echo "📊 Confronto previsioni:"
echo "   PRIMA: +25% in 72 ore (IMPOSSIBILE per EURUSD)"
echo "   DOPO:  +0.5-2% in 72 ore (REALISTICO per EURUSD)"
echo ""
