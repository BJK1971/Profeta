#!/bin/bash
# PROFETA - Log Monitor Script
# Visualizza tutti i log centralizzati in ~/Profeta/logs/

LOGS_DIR="$HOME/Profeta/logs"
EPIC="${1:-EURUSD}"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              PROFETA LOG MONITOR - EPIC: $EPIC                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Log Directory: $LOGS_DIR"
echo ""

# Verifica che i file esistano
if [ ! -d "$LOGS_DIR" ]; then
    echo "❌ Directory log non trovata: $LOGS_DIR"
    exit 1
fi

echo "=== File log disponibili ==="
ls -lh "$LOGS_DIR"/*${EPIC}*.log 2>/dev/null || echo "Nessun log trovato per $EPIC"
ls -lh "$LOGS_DIR"/profeta-v5.log 2>/dev/null || echo "profeta-v5.log non trovato"
echo ""

# Funzione per mostrare menu
show_menu() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  Scegli cosa monitorare:                                       ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║  1) Tutti i log (multi-panel)                                  ║"
    echo "║  2) Solo previsioni (profeta-v5.log - PRED_NUM)                ║"
    echo "║  3) Solo trading (trading-bot-${EPIC}.log)                     ║"
    echo "║  4) Solo orchestratore (orchestrator-${EPIC}.log)              ║"
    echo "║  5) P/L in tempo reale                                         ║"
    echo "║  6) Errori e warning                                           ║"
    echo "║  7) Ultime 50 righe da tutti i log                             ║"
    echo "║  0) Esci                                                       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

# Loop menu
while true; do
    show_menu
    read -p "Scelta: " choice
    
    case $choice in
        1)
            clear
            echo "Premi Ctrl+C per uscire"
            sleep 2
            # Usa tmux se disponibile, altrimenti mostra log sequenziali
            if command -v tmux &> /dev/null; then
                tmux new-session "tail -f $LOGS_DIR/profeta-v5.log | grep --line-buffered 'PRED_NUM\|STATUS TRADES\|Strategia\|SEGNALE'" \; \
                split-window -v "tail -f $LOGS_DIR/trading-bot-${EPIC}.log" \; \
                split-window -h "tail -f $LOGS_DIR/orchestrator-${EPIC}.log"
            else
                echo "=== PROFETA-V5.LOG (Previsioni + Trading) ==="
                tail -f $LOGS_DIR/profeta-v5.log | grep --line-buffered 'PRED_NUM\|STATUS TRADES\|Strategia\|SEGNALE' &
                PID1=$!
                
                echo "=== TRADING-BOT-${EPIC}.LOG ==="
                tail -f $LOGS_DIR/trading-bot-${EPIC}.log &
                PID2=$!
                
                echo "=== ORCHESTRATOR-${EPIC}.LOG ==="
                tail -f $LOGS_DIR/orchestrator-${EPIC}.log &
                PID3=$!
                
                wait
            fi
            ;;
        2)
            echo "=== PREVISIONI (PRED_NUM) ==="
            tail -f $LOGS_DIR/profeta-v5.log | grep --line-buffered 'PRED_NUM'
            ;;
        3)
            echo "=== TRADING BOT ==="
            tail -f $LOGS_DIR/trading-bot-${EPIC}.log
            ;;
        4)
            echo "=== ORCHESTRATORE ==="
            tail -f $LOGS_DIR/orchestrator-${EPIC}.log
            ;;
        5)
            echo "=== P/L IN TEMPO REALE ==="
            watch -n 30 "grep 'STATUS TRADES' $LOGS_DIR/profeta-v5.log | tail -1"
            ;;
        6)
            echo "=== ERRORI E WARNING ==="
            tail -f $LOGS_DIR/*.log | grep --line-buffered -i 'error\|warning\|exception\|failed'
            ;;
        7)
            echo "=== ULTIME 50 RIGHE DA TUTTI I LOG ==="
            echo ""
            echo "--- profeta-v5.log ---"
            tail -50 $LOGS_DIR/profeta-v5.log | tail -20
            echo ""
            echo "--- trading-bot-${EPIC}.log ---"
            tail -50 $LOGS_DIR/trading-bot-${EPIC}.log 2>/dev/null | tail -20 || echo "Non disponibile"
            echo ""
            echo "--- orchestrator-${EPIC}.log ---"
            tail -50 $LOGS_DIR/orchestrator-${EPIC}.log 2>/dev/null | tail -20 || echo "Non disponibile"
            ;;
        0)
            echo "Exit"
            exit 0
            ;;
        *)
            echo "Scelta non valida"
            ;;
    esac
done
