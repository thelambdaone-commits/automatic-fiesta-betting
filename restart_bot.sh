#!/bin/bash
# Kill all python bots (with more aggressive cleanup)
pkill -9 -f "main_telegram.py" 2>/dev/null
pkill -9 -f "main_copy_trade.py" 2>/dev/null
pkill -9 -f "src/main_telegram.py" 2>/dev/null
pkill -9 -f "src/main_copy_trade.py" 2>/dev/null

# Wait for processes to die
sleep 3

# Verify all processes are killed
remaining=$(ps aux | grep -E "main_telegram|main_copy" | grep -v grep | wc -l)
if [ $remaining -gt 0 ]; then
    echo "Warning: $remaining processes still running, killing again..."
    pkill -9 -f "main_telegram" 2>/dev/null
    pkill -9 -f "main_copy" 2>/dev/null
    sleep 2
fi

# Clear any pending updates (reset Telegram offset)
curl -s "https://api.telegram.org/bot8439202456:AAGY8DY6VQp67qcAjrRVls8YeAAAwasGdi0/getUpdates?offset=-1&timeout=0" > /dev/null

# Wait for API to release
sleep 2

# Start bots from the correct directory with absolute paths
cd /home/ey9dyk3j8bg3/polymarket-copy-trade
nohup python3 /home/ey9dyk3j8bg3/polymarket-copy-trade/src/main_copy_trade.py > /tmp/copy_trade.log 2>&1 &
sleep 2
nohup python3 /home/ey9dyk3j8bg3/polymarket-copy-trade/src/main_telegram.py > /tmp/telegram_bot.log 2>&1 &

echo "Bots restarted"
sleep 3
ps aux | grep -E "main_telegram|main_copy" | grep -v grep
