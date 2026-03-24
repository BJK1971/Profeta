#!/bin/bash
# Start PROFETA services for EURUSD e BTCUSD
# Tutti i log vengono salvati in ~/Profeta/logs/

cd ~/Profeta

# Crea directory log se non esiste
mkdir -p ~/Profeta/logs

# Kill any existing processes
pkill -9 -f "Run_profeta_real_time.py" 2>/dev/null
pkill -9 -f "profeta_trading_bot.py" 2>/dev/null
pkill -9 -f "profeta-universal.py" 2>/dev/null
sleep 2

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          PROFETA SERVICES STARTER                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Funzione per avviare servizi per una epic
start_epic_services() {
    local epic=$1
    local config="BKTEST/config-lstm-${epic}.ini"
    
    # Verifica config
    if [ ! -f "$config" ]; then
        echo "⚠️  Config non trovato per $epic, uso backtest config"
        config="BKTEST/config-lstm-backtest.ini"
    fi
    
    echo "🚀 Avvio servizi per $epic..."
    
    # Start orchestrator (hourly predictions) con nohup
    nohup ~/miniconda3/envs/profeta/bin/python Run_profeta_real_time.py --config "$config" --epic "$epic" > ~/Profeta/logs/orchestrator-${epic}-live.log 2>&1 &
    ORCH_PID=$!
    echo "  ✅ Orchestrator $epic: PID $ORCH_PID"
    
    # Start trading bot (poll every 30s) con nohup
    nohup ~/miniconda3/envs/profeta/bin/python profeta_trading_bot.py --config "$config" --epic "$epic" > ~/Profeta/logs/trading-bot-${epic}-live.log 2>&1 &
    BOT_PID=$!
    echo "  ✅ Trading Bot $epic: PID $BOT_PID"
    
    # Save PIDs
    echo $ORCH_PID > /tmp/orchestrator-${epic}.pid
    echo $BOT_PID > /tmp/trading-bot-${epic}.pid
    
    echo ""
}

# Avvia servizi per EURUSD, BTCUSD, GOLD e US500
# IMPORTANTE: Delay di 15 secondi tra ogni epic per evitare rate limit Capital.com (429)
start_epic_services "EURUSD"
sleep 15
start_epic_services "BTCUSD"
sleep 15
start_epic_services "GOLD"
sleep 15
start_epic_services "US500"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  TUTTI I SERVIZI SONO STATI AVVIATI                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "=== Log Files (all in ~/Profeta/logs/) ==="
echo "  📄 orchestrator-EURUSD-live.log"
echo "  📄 orchestrator-BTCUSD-live.log"
echo "  📄 orchestrator-GOLD-live.log"
echo "  📄 trading-bot-EURUSD-live.log"
echo "  📄 trading-bot-BTCUSD-live.log"
echo "  📄 trading-bot-GOLD-live.log"
echo "  📄 profeta-v5.log"
echo ""
echo "=== Monitoraggio ==="
echo "  tail -f ~/Profeta/logs/orchestrator-EURUSD-live.log"
echo "  tail -f ~/Profeta/logs/trading-bot-EURUSD-live.log"
echo ""
echo "  Oppure: ./logs-monitor.sh EURUSD (o BTCUSD)"
echo ""
echo "=== Stop Services ==="
echo "  ./stop-epic-services.sh  (o pkill -f profeta)"
echo ""
