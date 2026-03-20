#!/bin/bash
# Start PROFETA services for EURUSD
# Tutti i log vengono salvati in ~/Profeta/logs/

cd ~/Profeta

# Crea directory log se non esiste
mkdir -p ~/Profeta/logs

# Kill any existing processes
pkill -9 -f "Run_profeta_real_time.py" 2>/dev/null
pkill -9 -f "profeta_trading_bot.py" 2>/dev/null
sleep 2

# Start orchestrator (hourly predictions)
~/miniconda3/envs/profeta/bin/python Run_profeta_real_time.py --config BKTEST/config-lstm-EURUSD.ini --epic EURUSD &
ORCH_PID=$!
echo "Orchestrator started: PID $ORCH_PID"

# Start trading bot (poll every 30s)
~/miniconda3/envs/profeta/bin/python profeta_trading_bot.py --epic EURUSD &
BOT_PID=$!
echo "Trading bot started: PID $BOT_PID"

# Save PIDs
echo $ORCH_PID > /tmp/orchestrator.pid
echo $BOT_PID > /tmp/trading-bot.pid

echo ""
echo "=== PROFETA Services Started ==="
echo "Orchestrator PID: $ORCH_PID (hourly predictions)"
echo "Trading Bot PID: $BOT_PID (poll every 30s)"
echo ""
echo "=== Log Files (all in ~/Profeta/logs/) ==="
echo "  📄 orchestrator-EURUSD.log  - Orchestrator cycle logs"
echo "  📄 trading-bot-EURUSD.log   - Trading bot logs"
echo "  📄 profeta-v5.log           - Main prediction engine logs"
echo ""
echo "To monitor:"
echo "  tail -f ~/Profeta/logs/profeta-v5.log"
echo "  tail -f ~/Profeta/logs/trading-bot-EURUSD.log"
echo "  tail -f ~/Profeta/logs/orchestrator-EURUSD.log"
