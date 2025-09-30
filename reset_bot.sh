#!/bin/bash
cd /root/bot-bugalter/manager-bot
TOKEN=$(grep 'TOKEN.*=' data/config.py | cut -d'"' -f2 | head -1)
curl -s "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true" > /dev/null
curl -s "https://api.telegram.org/bot${TOKEN}/logOut" > /dev/null
sleep 2
echo "Bot token reset complete"
