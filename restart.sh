#!/bin/bash
cd /root/bot-bugalter

echo "🛑 Stopping all services..."

# Останавливаем screen сессии
screen -S manager_bot -X quit 2>/dev/null || true
screen -S flask_app -X quit 2>/dev/null || true
screen -S auto_reports -X quit 2>/dev/null || true
screen -S id_matches -X quit 2>/dev/null || true
screen -wipe 2>/dev/null || true

# Убиваем процессы из текущей директории
echo "Killing processes from /root/bot-bugalter..."
pkill -9 -f "/root/bot-bugalter.*python" 2>/dev/null || true

# ВАЖНО: Убиваем старые процессы из /root/old/ которые могут конфликтовать с токенами
echo "Killing old processes from /root/old/bot-bugalter..."
pkill -9 -f "/root/old/bot-bugalter.*python" 2>/dev/null || true

# Убиваем процессы по токенам ботов (на случай если где-то еще запущены)
echo "Killing processes by bot tokens..."
pkill -9 -f "7109114044" 2>/dev/null || true  # id_matches token
pkill -9 -f "6842489166" 2>/dev/null || true  # auto_reports token

# Убиваем все процессы python main.py из id-matches-bot (включая запущенные в терминалах)
echo "Killing all id-matches-bot python processes..."
pgrep -f "id-matches-bot.*python.*main.py" | xargs -r kill -9 2>/dev/null || true
pgrep -f "venv311/bin/python main.py" | xargs -r kill -9 2>/dev/null || true

# Убиваем все процессы python bot.py из auto-reports-bot
echo "Killing all auto-reports-bot python processes..."
pgrep -f "auto-reports-bot.*python.*bot.py" | xargs -r kill -9 2>/dev/null || true
pgrep -f "venv-ar/bin/python bot.py" | xargs -r kill -9 2>/dev/null || true

# Убиваем все процессы manager-bot
echo "Killing all manager-bot python processes..."
pgrep -f "manager-bot.*python.*main.py" | xargs -r kill -9 2>/dev/null || true
pgrep -f "venv-mb/bin/python main.py" | xargs -r kill -9 2>/dev/null || true

# Ждем завершения всех процессов
echo "Waiting for processes to fully terminate..."
sleep 3

# Проверяем что процессы действительно завершились
remaining=$(pgrep -f "bot-bugalter.*(bot\.py|main\.py)" 2>/dev/null | wc -l)
if [ "$remaining" -gt 0 ]; then
    echo "Warning: $remaining processes still running, force killing..."
    pgrep -f "bot-bugalter.*(bot\.py|main\.py)" | xargs -r kill -9 2>/dev/null || true
    sleep 2
fi

# Очищаем webhook для всех ботов (чтобы избежать конфликтов)
echo "Clearing webhooks for all bots..."
curl -s "https://api.telegram.org/bot7109114044:AAGiEKyiqIrCEzmJQxxQhYOmTUWNtIfgJbc/deleteWebhook?drop_pending_updates=true" > /dev/null 2>&1 || true
curl -s "https://api.telegram.org/bot6842489166:AAFFLbZeyCTDlBOOC_mhx0Y0vnUSHMazIFY/deleteWebhook?drop_pending_updates=true" > /dev/null 2>&1 || true

echo "Waiting for Telegram API to release bot sessions (30 seconds)..."
sleep 30

# Очищаем логи перед запуском
echo "Clearing old logs..."
> flask_app/flask.log
> manager-bot/run.log
> auto-reports-bot/ar.log
> id-matches-bot/id_matches.log

echo "🚀 Starting services at $(date)..."
screen -S flask_app -d -m bash -c 'cd /root/bot-bugalter/flask_app && venv/bin/python -u app.py >> flask.log 2>&1'
echo "✅ Flask app started"

screen -S manager_bot -d -m bash -c 'cd /root/bot-bugalter/manager-bot && /root/bot-bugalter/venv-mb/bin/python -u main.py >> run.log 2>&1'
echo "✅ Manager bot started"

screen -S auto_reports -d -m bash -c 'cd /root/bot-bugalter/auto-reports-bot && ../venv-ar/bin/python -u bot.py >> ar.log 2>&1'
echo "✅ Auto reports bot started"

screen -S id_matches -d -m bash -c 'cd /root/bot-bugalter/id-matches-bot && ../venv311/bin/python -u main.py >> id_matches.log 2>&1'
echo "✅ ID matches bot started"

echo "Waiting for all services to stabilize..."
sleep 10

echo ""
echo "=== Screen sessions ==="
screen -ls

echo ""
echo "=== Flask status ==="
lsof -i :8180 | grep LISTEN && echo "✅ Flask running on 8180" || echo "❌ Flask NOT running"

echo ""
echo "=== Python processes ==="
ps aux | grep "bot-bugalter.*python" | grep -v grep | awk '{print $11, $12, $13}'

echo ""
echo "=== Manager bot log ==="
tail -n 5 manager-bot/run.log

echo ""
echo "=== Auto reports bot log ==="
tail -n 5 auto-reports-bot/ar.log

echo ""
echo "=== ID matches bot log ==="
tail -n 5 id-matches-bot/id_matches.log

echo ""
echo "=== Check for Telegram conflicts ==="
if grep -q "Conflict" auto-reports-bot/ar.log id-matches-bot/id_matches.log manager-bot/run.log 2>/dev/null; then
    echo "⚠️  WARNING: Telegram conflict detected in logs!"
    grep "Conflict" auto-reports-bot/ar.log id-matches-bot/id_matches.log manager-bot/run.log 2>/dev/null | head -3
else
    echo "✅ No Telegram conflicts detected"
fi

echo ""
echo "=== Active Python processes ==="
ps aux | grep -E "venv.*/python.*(bot\.py|main\.py|app\.py)" | grep -v grep | awk '{printf "%-10s %-30s %s\n", $2, $11, $12}'

echo ""
echo "✅ All services restarted at $(date)!"
