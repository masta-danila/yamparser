# Установка systemd-службы Yamparser

## На сервере

```bash
# Скопировать службу
sudo cp deploy/yamparser.service /etc/systemd/system/

# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск при старте системы
sudo systemctl enable yamparser

# Запустить
sudo systemctl start yamparser

# Проверить статус
sudo systemctl status yamparser

# Смотреть логи
journalctl -u yamparser -f
```

## Команды управления

| Действие | Команда |
|----------|---------|
| Статус | `sudo systemctl status yamparser` |
| Логи (live) | `journalctl -u yamparser -f` |
| Остановить | `sudo systemctl stop yamparser` |
| Запустить | `sudo systemctl start yamparser` |
| Перезапустить | `sudo systemctl restart yamparser` |

## Важно

- Путь в службе: `/home/danil/yamparser` — измените в `.service` если пользователь или путь другие.
- Требуется `xvfb`: `sudo apt install xvfb -y` (для headless-режима Chrome).
- Логи парсера пишутся в `logs/YYYY-MM-DD.txt` внутри рабочей директории.
- Убедитесь, что в `config.py` установлено `HEADLESS_MODE = True` для сервера.
