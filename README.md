# Руководство по перезапуску сервисов

## Метод 1: Ручной запуск через Python (рекомендуется для разработки)

```bash
# Активировать виртуальное окружение (если используется)
cd /root/bot-bugalter
source .venv/bin/activate  # или source venv/bin/activate

# Запустить сервисы в отдельных терминалах:

# Flask (веб-интерфейс)
cd flask_app
python app.py

# Менеджер-бот (основной функционал)
cd ../manager-bot
python main.py

# Авто-отчеты
cd ../auto-reports-bot
python main.py

# ID-матчи
cd ../id-matches-bot
python main.py
```

## Метод 2: Запуск в фоне через screen
```bash
# Установить screen если нужно
sudo apt install screen

# Создать сессии для каждого сервиса
screen -S flask_app -d -m bash -c "cd /root/bot-bugalter/flask_app && python app.py"
screen -S manager_bot -d -m bash -c "cd /root/bot-bugalter/manager-bot && python main.py"
screen -S auto_reports -d -m bash -c "cd /root/bot-bugalter/auto-reports-bot && python main.py"
screen -S id_matches -d -m bash -c "cd /root/bot-bugalter/id-matches-bot && python main.py"

# Просмотр работающих сессий
screen -ls

# Подключиться к сессии:
screen -x flask_app
```

## Метод 3: Systemd (для production)

1. Создать файлы сервисов в `/etc/systemd/system/`:

Файл: `ibet-flask.service`
```ini
[Unit]
Description=iBet Flask Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/bot-bugalter/flask_app
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Повторить для других сервисов, изменив `WorkingDirectory` и имя сервиса.

2. Команды управления:
```bash
# Перезагрузка демона systemd
sudo systemctl daemon-reload

# Запуск сервиса
sudo systemctl start ibet-flask.service

# Автозагрузка
sudo systemctl enable ibet-flask.service

# Просмотр статуса
sudo systemctl status ibet-flask.service -l
```

## Перезапуск после изменений кода
```bash
# Для ручного запуска - просто остановите и перезапустите процессы
# Для systemd:
sudo systemctl restart ibet-flask.service ibet-manager-bot.service ibet-auto-reports.service ibet-id-matches.service

# Проверить логи:
journalctl -u ibet-flask.service -f
```
