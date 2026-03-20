#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    PROFETA EPIC MANAGER
# ═══════════════════════════════════════════════════════════════════════════════════════════
#
# Gestione multi-epic per PROFETA (crypto, forex, stocks)
#
# Usage: ./run-epic.sh <EPIC> [MODE]
#   EPIC: BTCUSD, EURUSD, ETHUSD, etc.
#   MODE: train, predict, full (default: full)
#
# ═══════════════════════════════════════════════════════════════════════════════════════════

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configurazione
PROJECT_DIR="$HOME/Profeta"
CONFIG_FILE="$PROJECT_DIR/config-lstm.ini"
BACKTEST_CONFIG="$PROJECT_DIR/BKTEST/config-lstm-backtest.ini"
LOG_FILE="$PROJECT_DIR/logs/profeta-${EPIC}.log"

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    USAGE
# ═══════════════════════════════════════════════════════════════════════════════════════════

usage() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    PROFETA - EPIC MANAGER                                                ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Usage: ${YELLOW}$0 <EPIC> [MODE]${NC}"
    echo ""
    echo -e "  ${GREEN}EPIC${NC}  Asset da trading (es: BTCUSD, EURUSD, ETHUSD)"
    echo -e "  ${GREEN}MODE${NC}  Modalità di esecuzione:"
    echo -e "         ${CYAN}train${NC}   - Solo training dei modelli"
    echo -e "         ${CYAN}predict${NC} - Solo predizione (usa modelli esistenti)"
    echo -e "         ${CYAN}full${NC}    - Training + Prediction (default)"
    echo -e "         ${CYAN}realtime${NC}- Modalità real-time (orchestratore)"
    echo ""
    echo -e "Esempi:"
    echo -e "  ${YELLOW}$0 EURUSD${NC}         # Esegue full cycle per EURUSD"
    echo -e "  ${YELLOW}$0 BTCUSD train${NC}   # Solo training per BTCUSD"
    echo -e "  ${YELLOW}$0 ETHUSD realtime${NC} # Modalità real-time per ETHUSD"
    echo ""
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

# Check argomenti
if [ $# -lt 1 ]; then
    usage
fi

EPIC="$1"
MODE="${2:-full}"

cd "$PROJECT_DIR"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    PROFETA - EPIC: ${YELLOW}$EPIC${NC}"
echo -e "${CYAN}║                    Mode: ${YELLOW}$MODE${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Attiva ambiente conda
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate profeta
    echo -e "${GREEN}✓${NC} Ambiente conda 'profeta' attivato"
else
    echo -e "${YELLOW}⚠${NC} Conda non trovato. Assicurati di avere l'ambiente attivo."
fi
echo ""

# Verifica file di configurazione
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗${NC} File di configurazione non trovato: $CONFIG_FILE"
    exit 1
fi

# Verifica o crea file di config per l'epic specifico
EPIC_CONFIG="$PROJECT_DIR/BKTEST/config-lstm-${EPIC}.ini"
if [ ! -f "$EPIC_CONFIG" ]; then
    echo -e "${YELLOW}⚠${NC} Config specifico per $EPIC non trovato. Creo da template..."
    cp "$BACKTEST_CONFIG" "$EPIC_CONFIG"
    
    # Aggiorna epic nel file
    sed -i "s/^epic = .*/epic = $EPIC/" "$EPIC_CONFIG"
    echo -e "${GREEN}✓${NC} Creato: $EPIC_CONFIG"
fi

# Esecuzione in base alla modalità
case $MODE in
    train)
        echo -e "${CYAN}[TRAIN]${NC} Avvio training per $EPIC..."
        echo -e "${YELLOW}Nota:${NC} I modelli saranno salvati in ./models/$EPIC/"
        echo ""
        python profeta-universal.py "$EPIC_CONFIG" --epic "$EPIC"
        ;;
    
    predict)
        echo -e "${CYAN}[PREDICT]${NC} Avvio predizione per $EPIC..."
        echo -e "${YELLOW}Nota:${NC} Userà i modelli esistenti in ./models/$EPIC/"
        echo ""
        python profeta-universal.py "$EPIC_CONFIG" --epic "$EPIC"
        ;;
    
    full)
        echo -e "${CYAN}[FULL]${NC} Training + Prediction per $EPIC..."
        echo ""
        python profeta-universal.py "$EPIC_CONFIG" --epic "$EPIC"
        ;;
    
    realtime)
        echo -e "${CYAN}[REALTIME]${NC} Avvio orchestratore real-time per $EPIC..."
        echo ""
        python Run_profeta_real_time.py --config "$EPIC_CONFIG" --epic "$EPIC"
        ;;
    
    *)
        echo -e "${RED}✗${NC} Modalità '$MODE' non riconosciuta"
        usage
        ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ESECUZIONE COMPLETATA                                                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📊 Output per ${YELLOW}$EPIC${NC}:"
echo -e "   - Log:     ${CYAN}$LOG_FILE${NC}"
echo -e "   - Modelli: ${CYAN}./models/$EPIC/${NC}"
echo -e "   - Output:  ${CYAN}./output/predictions_${EPIC}.csv${NC}"
echo ""
