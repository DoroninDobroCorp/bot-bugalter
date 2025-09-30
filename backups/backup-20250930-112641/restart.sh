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

# Очищаем webhook для id_matches бота (чтобы избежать конфликтов)
echo "Clearing webhook for id_matches bot..."
curl -s "https://api.telegram.org/bot7109114044:AAGiEKyiqIrCEzmJQxxQhYOmTUWNtIfgJbc/deleteWebhook?drop_pending_updates=true" > /dev/null 2>&1 || true

echo "Waiting for Telegram API and processes to clear..."
sleep 10

echo "🚀 Starting services..."
screen -S flask_app -d -m bash -c 'cd /root/bot-bugalter/flask_app && venv/bin/python app.py >> flask.log 2>&1'
screen -S manager_bot -d -m bash -c 'cd /root/bot-bugalter/manager-bot && /root/bot-bugalter/venv-mb/bin/python main.py >> run.log 2>&1'
screen -S auto_reports -d -m bash -c 'cd /root/bot-bugalter/auto-reports-bot && ../venv-ar/bin/python bot.py >> ar.log 2>&1'

echo "Waiting 30 seconds for Telegram API to release id_matches bot token..."
sleep 30

echo "Starting id_matches bot..."
screen -S id_matches -d -m bash -c 'cd /root/bot-bugalter/id-matches-bot && ../venv311/bin/python main.py >> id_matches.log 2>&1'

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
echo "=== Manager bot log (last 5 lines) ==="
tail -n 5 manager-bot/run.log

echo ""
echo "✅ All services restarted!"
