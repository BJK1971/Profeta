#!/bin/bash
# Stop PROFETA services

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          PROFETA SERVICES STOP                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Kill all PROFETA processes
echo "🛑 Arresto processi..."
pkill -9 -f "Run_profeta_real_time.py" 2>/dev/null && echo "  ✅ Orchestrators stopped"
pkill -9 -f "profeta_trading_bot.py" 2>/dev/null && echo "  ✅ Trading bots stopped"
pkill -9 -f "profeta-universal.py" 2>/dev/null && echo "  ✅ Training stopped"

# Remove PID files
rm -f /tmp/orchestrator-*.pid /tmp/trading-bot-*.pid 2>/dev/null

echo ""
echo "✅ Tutti i servizi sono stati arrestati"
echo ""
echo "=== Per riavviare ==="
echo "  ./start-epic-services.sh"
echo ""
