# 🚀 Развертывание YamParser на сервере

Инструкция по развертыванию парсера отзывов Яндекс Карт на Linux сервере без Docker.

## 📋 Требования к серверу

### Минимальные требования:
- **ОС**: Ubuntu 20.04+, CentOS 7+, RHEL 8+
- **RAM**: минимум 2 ГБ, рекомендуется 4 ГБ+
- **Диск**: минимум 10 ГБ свободного места
- **CPU**: минимум 2 ядра
- **Права**: sudo доступ

### Поддерживаемые ОС:
- ✅ Ubuntu 20.04, 22.04, 24.04
- ✅ Debian 10, 11, 12
- ✅ CentOS 7, 8
- ✅ RHEL 8, 9
- ✅ Amazon Linux 2
- ✅ macOS (для тестирования)

## 🛠️ Автоматическая установка

### 1. Загрузка проекта на сервер

```bash
# Через git (рекомендуется)
git clone <repository-url> yamparser
cd yamparser

# Или загрузите архив и распакуйте
wget <archive-url>
unzip yamparser.zip
cd yamparser
```

### 2. Запуск автоустановки

```bash
# Сделать скрипт исполняемым
chmod +x deploy_server.sh

# Запустить полную установку
./deploy_server.sh install
```

Скрипт автоматически установит:
- ✅ Python 3.11+ и pip
- ✅ PostgreSQL базу данных
- ✅ Chromium браузер
- ✅ ChromeDriver
- ✅ Xvfb (виртуальный дисплей)
- ✅ Все Python зависимости
- ✅ Systemd сервис
- ✅ Скрипт управления

### 3. Настройка после установки

#### Замените файл credentials.json
```bash
# Замените созданную заглушку на реальный файл Google Sheets API
nano credentials.json
```

#### Добавьте прокси (опционально)
```bash
# Отредактируйте файл с прокси серверами
nano proxy.txt

# Формат: IP:PORT:USERNAME:PASSWORD
# Пример:
82.97.251.114:16172:username:password
203.0.113.10:3128:user1:pass1
```

#### Настройте конфигурацию
```bash
# Отредактируйте настройки парсера
nano config.py
```

## 🎮 Управление сервисом

После установки используйте скрипт `run_parser.sh`:

```bash
# Запуск парсера как сервиса
./run_parser.sh start

# Остановка сервиса
./run_parser.sh stop

# Перезапуск
./run_parser.sh restart

# Статус сервиса
./run_parser.sh status

# Просмотр логов
./run_parser.sh logs          # Системные логи
./run_parser.sh logs-app      # Логи приложения
./run_parser.sh logs-error    # Логи ошибок
```

### Однократный запуск (без сервиса)

```bash
# Запустить парсер один раз
./run_parser.sh run-once

# Запустить парсер конкретного URL
./run_parser.sh run-reviews "https://yandex.ru/maps/org/organization_name/123456789/reviews/"

# Войти в виртуальное окружение
./run_parser.sh shell
```

## 📊 Мониторинг

### Просмотр логов в реальном времени
```bash
# Логи сервиса
sudo journalctl -u yamparser -f

# Логи приложения
tail -f logs/yamparser.log

# Логи ошибок
tail -f logs/yamparser_error.log
```

### Проверка статуса
```bash
# Статус systemd сервиса
sudo systemctl status yamparser

# Статус PostgreSQL
sudo systemctl status postgresql

# Проверка процессов
ps aux | grep -E "(python|yamparser|Xvfb)"
```

### Мониторинг ресурсов
```bash
# Использование памяти и CPU
top -p $(pgrep -f yamparser)

# Место на диске
df -h
du -sh data/ logs/ chrome_profiles/
```

## 🔧 Ручная установка (если автоскрипт не работает)

### 1. Установка системных зависимостей

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    wget curl unzip \
    xvfb chromium-browser \
    postgresql postgresql-contrib \
    build-essential python3-dev libpq-dev
```

#### CentOS/RHEL:
```bash
sudo yum update -y
sudo yum install -y \
    python3 python3-pip \
    wget curl unzip \
    xorg-x11-server-Xvfb chromium \
    postgresql postgresql-server postgresql-contrib \
    gcc python3-devel postgresql-devel
```

### 2. Установка ChromeDriver
```bash
# Скачать последнюю версию
LATEST_VERSION=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -O /tmp/chromedriver_linux64.zip \
    "https://chromedriver.storage.googleapis.com/$LATEST_VERSION/chromedriver_linux64.zip"

# Установить
unzip -o /tmp/chromedriver_linux64.zip -d /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

### 3. Настройка PostgreSQL
```bash
# Запуск и включение автозапуска
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создание пользователя и базы данных
sudo -u postgres psql -c "CREATE USER daniladzhiev WITH PASSWORD 'parser123';"
sudo -u postgres psql -c "ALTER USER daniladzhiev CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE reviews OWNER daniladzhiev;"
```

### 4. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Настройка базы данных приложения
```bash
source venv/bin/activate
python setup_database.py
```

## 🚨 Решение проблем

### Ошибки установки

#### ChromeDriver не найден
```bash
# Проверить установку
which chromedriver
chromedriver --version

# Переустановить
sudo rm -f /usr/local/bin/chromedriver
# Повторить установку ChromeDriver
```

#### Проблемы с PostgreSQL
```bash
# Проверить статус
sudo systemctl status postgresql

# Перезапустить
sudo systemctl restart postgresql

# Проверить подключение
sudo -u postgres psql -l
```

#### Ошибки Python зависимостей
```bash
# Очистить кэш pip
pip cache purge

# Переустановить проблемные пакеты
pip install --upgrade --force-reinstall selenium psycopg2-binary
```

### Ошибки выполнения

#### Браузер не запускается
```bash
# Проверить Xvfb
ps aux | grep Xvfb

# Запустить Xvfb вручную
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99
```

#### Проблемы с прокси
```bash
# Проверить файл прокси
cat proxy.txt

# Тестировать без прокси
./run_parser.sh run-reviews --no-proxy "URL"
```

#### Проблемы с Google Sheets
```bash
# Проверить файл credentials.json
python -c "import json; print(json.load(open('credentials.json'))['project_id'])"

# Тестировать подключение
python -c "from google_sheets_reader import GoogleSheetsReader; reader = GoogleSheetsReader('credentials.json')"
```

### Логи и диагностика

```bash
# Полная диагностика
echo "=== Статус сервисов ==="
sudo systemctl status yamparser postgresql

echo "=== Логи приложения ==="
tail -20 logs/yamparser.log

echo "=== Логи ошибок ==="
tail -20 logs/yamparser_error.log

echo "=== Использование ресурсов ==="
free -h
df -h

echo "=== Процессы ==="
ps aux | grep -E "(python|yamparser|Xvfb|chrome)"
```

## 🔄 Обновление

### Обновление кода
```bash
# Остановить сервис
./run_parser.sh stop

# Обновить код
git pull

# Обновить зависимости
./deploy_server.sh update

# Запустить сервис
./run_parser.sh start
```

### Обновление системных компонентов
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get upgrade

# CentOS/RHEL
sudo yum update

# Перезапустить сервер при необходимости
sudo reboot
```

## 📁 Структура файлов

После установки структура проекта:

```
yamparser/
├── venv/                    # Виртуальное окружение
├── data/                    # Результаты парсинга
├── logs/                    # Логи приложения
├── chrome_profiles/         # Профили Chrome
├── credentials.json         # Google Sheets API
├── proxy.txt               # Прокси серверы
├── config.py               # Настройки
├── deploy_server.sh        # Скрипт развертывания
├── run_parser.sh           # Скрипт управления
├── integrated_parser.py    # Основной парсер
├── reviews_parser.py       # Парсер отзывов
├── setup_database.py       # Настройка БД
└── requirements.txt        # Python зависимости
```

## 🛡️ Безопасность

### Файл credentials.json
```bash
# Ограничить доступ
chmod 600 credentials.json
```

### Файл proxy.txt
```bash
# Ограничить доступ к паролям прокси
chmod 600 proxy.txt
```

### База данных
```bash
# Изменить пароль PostgreSQL
sudo -u postgres psql -c "ALTER USER daniladzhiev PASSWORD 'новый_пароль';"

# Обновить пароль в config.py
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `./run_parser.sh logs`
2. **Запустите диагностику**: команды из раздела "Решение проблем"
3. **Проверьте статус сервисов**: `sudo systemctl status yamparser postgresql`
4. **Тестируйте компоненты по отдельности**: `./run_parser.sh run-once`

---

**🎯 После успешной установки парсер будет автоматически запускаться при старте сервера и обрабатывать все URL из настроенных Google Sheets таблиц.** 