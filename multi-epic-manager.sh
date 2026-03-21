#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    PROFETA MULTI-EPIC MANAGER
# ═══════════════════════════════════════════════════════════════════════════════════════════
#
# Gestione coordinata di multiple epic (EURUSD, BTCUSD) con training sincronizzati
#
# Usage: ./multi-epic-manager.sh [start|stop|status]
#
# ═══════════════════════════════════════════════════════════════════════════════════════════

set -e

# Configurazione
PROJECT_DIR="$HOME/Profeta"
LOGS_DIR="$PROJECT_DIR/logs"
CONFIG_DIR="$PROJECT_DIR/BKTEST"
PYTHON="$HOME/miniconda3/envs/profeta/bin/python"

# Epic da gestire
EPICS=("EURUSD" "BTCUSD")

# Timing (in minuti)
# I training partono sfalsati: EURUSD al minuto 0, BTCUSD al minuto 30
TRAINING_OFFSET_MINUTES=30

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════

log() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# Verifica se un processo è in esecuzione
is_running() {
    local pattern="$1"
    pgrep -f "$pattern" > /dev/null 2>&1
}

# Kill di un processo
kill_process() {
    local pattern="$1"
    pkill -9 -f "$pattern" 2>/dev/null || true
}

# Avvia orchestratore per una epic
start_orchestrator() {
    local epic="$1"
    local config="$CONFIG_DIR/config-lstm-${epic}.ini"
    
    # Verifica config
    if [ ! -f "$config" ]; then
        log "⚠️  Config non trovato per $epic, uso backtest config"
        config="$CONFIG_DIR/config-lstm-backtest.ini"
    fi
    
    log "🚀 Avvio orchestratore per $epic (config: $config)"
    
    # Avvia in background
    cd "$PROJECT_DIR"
    $PYTHON Run_profeta_real_time.py --config "$config" --epic "$epic" > "$LOGS_DIR/orchestrator-${epic}.log" 2>&1 &
    local pid=$!
    echo $pid > "/tmp/orchestrator-${epic}.pid"
    
    success "Orchestrator $epic avviato (PID: $pid)"
}

# Avvia trading bot per una epic
start_trading_bot() {
    local epic="$1"
    
    log "🤖 Avvio trading bot per $epic"
    
    cd "$PROJECT_DIR"
    $PYTHON profeta_trading_bot.py --epic "$epic" > "$LOGS_DIR/trading-bot-${epic}.log" 2>&1 &
    local pid=$!
    echo $pid > "/tmp/trading-bot-${epic}.pid"
    
    success "Trading bot $epic avviato (PID: $pid)"
}

# Ferma tutti i processi per una epic
stop_epic() {
    local epic="$1"
    
    log "⏹️  Arresto servizi per $epic..."
    
    kill_process "Run_profeta_real_time.py.*--epic $epic"
    kill_process "profeta_trading_bot.py.*--epic $epic"
    
    # Rimuovi PID file
    rm -f "/tmp/orchestrator-${epic}.pid" "/tmp/trading-bot-${epic}.pid"
    
    success "Servizi $epic arrestati"
}

# Mostra stato
show_status() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          PROFETA MULTI-EPIC STATUS                             ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    for epic in "${EPICS[@]}"; do
        echo -e "${YELLOW}=== $epic ===${NC}"
        
        # Orchestrator
        if is_running "Run_profeta_real_time.py.*--epic $epic"; then
            local pid=$(pgrep -f "Run_profeta_real_time.py.*--epic $epic" | head -1)
            echo -e "  ${GREEN}✓${NC} Orchestrator: RUNNING (PID: $pid)"
        else
            echo -e "  ${RED}✗${NC} Orchestrator: STOPPED"
        fi
        
        # Trading Bot
        if is_running "profeta_trading_bot.py.*--epic $epic"; then
            local pid=$(pgrep -f "profeta_trading_bot.py.*--epic $epic" | head -1)
            echo -e "  ${GREEN}✓${NC} Trading Bot: RUNNING (PID: $pid)"
        else
            echo -e "  ${RED}✗${NC} Trading Bot: STOPPED"
        fi
        
        # Training in corso
        if is_running "profeta-universal.py.*--epic $epic"; then
            local pid=$(pgrep -f "profeta-universal.py.*--epic $epic" | head -1)
            echo -e "  ${YELLOW}⚙${NC} Training: IN CORSO (PID: $pid)"
        else
            echo -e "  ${GREEN}✓${NC} Training: IDLE"
        fi
        
        echo ""
    done
    
    # Log files
    echo -e "${YELLOW}=== Log Files ===${NC}"
    ls -lh "$LOGS_DIR"/*.log 2>/dev/null | grep -E "(orchestrator|trading-bot)" | awk '{print "  📄 " $9 " (" $5 ")"}'
    echo ""
}

# Avvia tutti i servizi coordinati
start_all() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          PROFETA MULTI-EPIC START                              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Crea directory log
    mkdir -p "$LOGS_DIR"
    
    # Ferma eventuali processi esistenti
    log "🧹 Pulizia processi esistenti..."
    for epic in "${EPICS[@]}"; do
        stop_epic "$epic"
    done
    sleep 2
    
    # Avvia EURUSD per primo (minuto 0)
    log "📈 Avvio ciclo EURUSD (offset: 0 min)"
    start_orchestrator "EURUSD"
    sleep 5
    start_trading_bot "EURUSD"
    
    # Attendi offset per BTCUSD (minuto 30)
    log "⏱️  Attesa offset di ${TRAINING_OFFSET_MINUTES} minuti per BTCUSD..."
    log "   (Questo evita sovrapposizioni dei training)"
    
    # In produzione, l'attesa sarebbe reale. Per il test, avviamo subito.
    # Scommenta la linea sotto per l'attesa reale:
    # sleep $((TRAINING_OFFSET_MINUTES * 60))
    
    # Per avvio immediato (test):
    sleep 10
    
    # Avvia BTCUSD (minuto 30)
    log "₿ Avvio ciclo BTCUSD (offset: ${TRAINING_OFFSET_MINUTES} min)"
    start_orchestrator "BTCUSD"
    sleep 5
    start_trading_bot "BTCUSD"
    
    echo ""
    success "╔════════════════════════════════════════════════════════════════╗"
    success "║  TUTTI I SERVIZI SONO STATI AVVIATI                            ║"
    success "║                                                                ║"
    success "║  EURUSD: Orchestrator + Trading Bot                            ║"
    success "║  BTCUSD: Orchestrator + Trading Bot (offset ${TRAINING_OFFSET_MINUTES} min)           ║"
    success "║                                                                ║"
    success "║  Usa: ./multi-epic-manager.sh status per monitorare            ║"
    success "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Mostra come monitorare
    echo -e "${YELLOW}=== Monitoraggio ===${NC}"
    echo "  tail -f $LOGS_DIR/profeta-v5.log | grep -E 'PRED_NUM|STATUS TRADES'"
    echo "  tail -f $LOGS_DIR/orchestrator-EURUSD.log"
    echo "  tail -f $LOGS_DIR/orchestrator-BTCUSD.log"
    echo "  tail -f $LOGS_DIR/trading-bot-EURUSD.log"
    echo "  tail -f $LOGS_DIR/trading-bot-BTCUSD.log"
    echo ""
    echo "  Oppure: ./logs-monitor.sh EURUSD (o BTCUSD)"
    echo ""
}

# Ferma tutti i servizi
stop_all() {
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          PROFETA MULTI-EPIC STOP                               ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    for epic in "${EPICS[@]}"; do
        stop_epic "$epic"
    done
    
    success "Tutti i servizi sono stati arrestati"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
#                                    MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    *)
        echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║          PROFETA MULTI-EPIC MANAGER                            ║${NC}"
        echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "Usage: ${YELLOW}$0 {start|stop|status|restart}${NC}"
        echo ""
        echo -e "Commands:"
        echo -e "  ${GREEN}start${NC}    - Avvia tutti i servizi (EURUSD + BTCUSD coordinati)"
        echo -e "  ${GREEN}stop${NC}     - Ferma tutti i servizi"
        echo -e "  ${GREEN}status${NC}   - Mostra stato dei servizi"
        echo -e "  ${GREEN}restart${NC}  - Riavvia tutti i servizi"
        echo ""
        echo -e "Epic gestite: ${YELLOW}${EPICS[*]}${NC}"
        echo -e "Training offset: ${YELLOW}${TRAINING_OFFSET_MINUTES} minuti${NC} (evita sovrapposizioni)"
        echo ""
        exit 1
        ;;
esac
