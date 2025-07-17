#!/bin/bash

# =============================================================================
# СКРИПТ РАЗВЕРТЫВАНИЯ YAMPARSER НА СЕРВЕРЕ
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка ОС
check_os() {
    print_info "Проверка операционной системы..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
        else
            print_error "Неподдерживаемый пакетный менеджер"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PKG_MANAGER="brew"
    else
        print_error "Неподдерживаемая ОС: $OSTYPE"
        exit 1
    fi
    
    print_success "ОС: $OS, Пакетный менеджер: $PKG_MANAGER"
}

# Установка системных зависимостей
install_system_deps() {
    print_info "Установка системных зависимостей..."
    
    case $PKG_MANAGER in
        "apt")
            sudo apt-get update
            sudo apt-get install -y \
                python3 \
                python3-pip \
                python3-venv \
                wget \
                curl \
                unzip \
                xvfb \
                chromium-browser \
                postgresql \
                postgresql-contrib \
                build-essential \
                python3-dev \
                libpq-dev
            ;;
        "yum"|"dnf")
            sudo $PKG_MANAGER update -y
            sudo $PKG_MANAGER install -y \
                python3 \
                python3-pip \
                wget \
                curl \
                unzip \
                xorg-x11-server-Xvfb \
                chromium \
                postgresql \
                postgresql-server \
                postgresql-contrib \
                gcc \
                python3-devel \
                postgresql-devel
            ;;
        "brew")
            brew update
            brew install \
                python3 \
                wget \
                curl \
                unzip \
                postgresql \
                chromium
            ;;
    esac
    
    print_success "Системные зависимости установлены"
}

# Установка ChromeDriver
install_chromedriver() {
    print_info "Установка ChromeDriver..."
    
    # Определяем архитектуру
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        CHROME_ARCH="linux64"
    elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        CHROME_ARCH="linux64"  # ChromeDriver теперь поддерживает ARM64
    else
        print_warning "Неизвестная архитектура: $ARCH, пробуем linux64"
        CHROME_ARCH="linux64"
    fi
    
    # Скачиваем последнюю версию ChromeDriver
    LATEST_VERSION=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE)
    print_info "Последняя версия ChromeDriver: $LATEST_VERSION"
    
    wget -O /tmp/chromedriver_$CHROME_ARCH.zip \
        "https://chromedriver.storage.googleapis.com/$LATEST_VERSION/chromedriver_$CHROME_ARCH.zip"
    
    unzip -o /tmp/chromedriver_$CHROME_ARCH.zip -d /tmp/
    sudo mv /tmp/chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    
    print_success "ChromeDriver установлен: $(chromedriver --version)"
}

# Настройка PostgreSQL
setup_postgresql() {
    print_info "Настройка PostgreSQL..."
    
    case $PKG_MANAGER in
        "apt")
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "yum"|"dnf")
            sudo postgresql-setup initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "brew")
            brew services start postgresql
            ;;
    esac
    
    # Создание пользователя и базы данных
    print_info "Создание пользователя и базы данных..."
    
    # Создаем пользователя daniladzhiev если не существует
    sudo -u postgres psql -c "CREATE USER daniladzhiev WITH PASSWORD 'parser123';" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER daniladzhiev CREATEDB;" 2>/dev/null || true
    
    # Создаем базу данных reviews если не существует
    sudo -u postgres psql -c "CREATE DATABASE reviews OWNER daniladzhiev;" 2>/dev/null || true
    
    print_success "PostgreSQL настроен"
}

# Создание виртуального окружения
create_venv() {
    print_info "Создание виртуального окружения..."
    
    if [ -d "venv" ]; then
        print_warning "Виртуальное окружение уже существует, пересоздаю..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Обновляем pip
    pip install --upgrade pip
    
    print_success "Виртуальное окружение создано"
}

# Установка Python зависимостей
install_python_deps() {
    print_info "Установка Python зависимостей..."
    
    source venv/bin/activate
    
    # Устанавливаем зависимости из requirements.txt
    pip install -r requirements.txt
    
    print_success "Python зависимости установлены"
}

# Настройка базы данных
setup_database() {
    print_info "Настройка базы данных приложения..."
    
    source venv/bin/activate
    
    # Запускаем скрипт настройки базы данных
    python setup_database.py
    
    print_success "База данных настроена"
}

# Создание папок для данных
create_data_dirs() {
    print_info "Создание папок для данных..."
    
    mkdir -p data logs chrome_profiles
    chmod 755 data logs chrome_profiles
    
    print_success "Папки для данных созданы"
}

# Создание systemd сервиса
create_service() {
    print_info "Создание systemd сервиса..."
    
    # Получаем полный путь к проекту
    PROJECT_PATH=$(pwd)
    USER=$(whoami)
    
    # Создаем файл сервиса
    sudo tee /etc/systemd/system/yamparser.service > /dev/null <<EOF
[Unit]
Description=YamParser - Парсер отзывов Яндекс Карт
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_PATH
Environment=PATH=$PROJECT_PATH/venv/bin
Environment=DISPLAY=:99
Environment=PYTHONPATH=$PROJECT_PATH
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset -nolisten tcp &
ExecStart=$PROJECT_PATH/venv/bin/python integrated_parser.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_PATH/logs/yamparser.log
StandardError=append:$PROJECT_PATH/logs/yamparser_error.log

[Install]
WantedBy=multi-user.target
EOF

    # Перезагружаем systemd и включаем сервис
    sudo systemctl daemon-reload
    sudo systemctl enable yamparser.service
    
    print_success "Systemd сервис создан"
}

# Создание скрипта запуска
create_run_script() {
    print_info "Создание скрипта управления..."
    
    cat > run_parser.sh << 'EOF'
#!/bin/bash

# Скрипт управления YamParser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

case "$1" in
    "start")
        print_status "Запуск YamParser..."
        sudo systemctl start yamparser
        ;;
    "stop")
        print_status "Остановка YamParser..."
        sudo systemctl stop yamparser
        ;;
    "restart")
        print_status "Перезапуск YamParser..."
        sudo systemctl restart yamparser
        ;;
    "status")
        sudo systemctl status yamparser
        ;;
    "logs")
        sudo journalctl -u yamparser -f
        ;;
    "logs-app")
        tail -f logs/yamparser.log
        ;;
    "logs-error")
        tail -f logs/yamparser_error.log
        ;;
    "run-once")
        print_status "Запуск парсера один раз..."
        source venv/bin/activate
        export DISPLAY=:99
        Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
        XVFB_PID=$!
        sleep 2
        python integrated_parser.py
        kill $XVFB_PID 2>/dev/null || true
        ;;
    "run-reviews")
        print_status "Запуск парсера отзывов..."
        source venv/bin/activate
        export DISPLAY=:99
        Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
        XVFB_PID=$!
        sleep 2
        shift
        python reviews_parser.py "$@"
        kill $XVFB_PID 2>/dev/null || true
        ;;
    "db-setup")
        print_status "Настройка базы данных..."
        source venv/bin/activate
        python setup_database.py
        ;;
    "shell")
        source venv/bin/activate
        bash
        ;;
    *)
        echo "🗺️ Управление YamParser"
        echo ""
        echo "Использование: $0 {команда}"
        echo ""
        echo "Команды:"
        echo "  start        - Запустить сервис"
        echo "  stop         - Остановить сервис"  
        echo "  restart      - Перезапустить сервис"
        echo "  status       - Статус сервиса"
        echo "  logs         - Логи systemd"
        echo "  logs-app     - Логи приложения"
        echo "  logs-error   - Логи ошибок"
        echo "  run-once     - Запустить парсер один раз"
        echo "  run-reviews  - Запустить парсер отзывов с URL"
        echo "  db-setup     - Настроить базу данных"
        echo "  shell        - Войти в виртуальное окружение"
        echo ""
        echo "Примеры:"
        echo "  $0 start                              # Запуск сервиса"
        echo "  $0 run-once                           # Однократный запуск"
        echo "  $0 run-reviews 'https://yandex.ru...' # Парсинг конкретного URL"
        echo "  $0 logs                               # Просмотр логов"
        ;;
esac
EOF

    chmod +x run_parser.sh
    print_success "Скрипт управления создан: ./run_parser.sh"
}

# Проверка файлов конфигурации
check_config_files() {
    print_info "Проверка файлов конфигурации..."
    
    # Проверяем обязательные файлы
    if [ ! -f "credentials.json" ]; then
        print_warning "Файл credentials.json не найден!"
        print_info "Создаю файл-заглушку. Замените его на реальный файл Google Sheets API."
        cat > credentials.json << 'EOF'
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project-id.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"
}
EOF
    fi
    
    if [ ! -f "proxy.txt" ]; then
        print_warning "Файл proxy.txt не найден!"
        print_info "Создаю пустой файл proxy.txt"
        touch proxy.txt
        echo "# Формат: IP:PORT:USERNAME:PASSWORD" > proxy.txt
        echo "# Пример: 82.97.251.114:16172:username:password" >> proxy.txt
    fi
    
    print_success "Файлы конфигурации проверены"
}

# Основная функция
main() {
    echo "🚀 Развертывание YamParser на сервере"
    echo "="*50
    
    case "$1" in
        "install")
            check_os
            install_system_deps
            install_chromedriver
            setup_postgresql
            create_venv
            install_python_deps
            create_data_dirs
            setup_database
            check_config_files
            create_service
            create_run_script
            
            print_success "Установка завершена!"
            echo ""
            echo "📝 Следующие шаги:"
            echo "1. Замените credentials.json на реальный файл Google Sheets API"
            echo "2. Добавьте прокси в proxy.txt (опционально)"
            echo "3. Запустите парсер: ./run_parser.sh start"
            echo "4. Просмотр логов: ./run_parser.sh logs"
            ;;
        "update")
            print_info "Обновление зависимостей..."
            source venv/bin/activate
            pip install --upgrade -r requirements.txt
            print_success "Зависимости обновлены"
            ;;
        "uninstall")
            print_warning "Удаление YamParser..."
            sudo systemctl stop yamparser 2>/dev/null || true
            sudo systemctl disable yamparser 2>/dev/null || true
            sudo rm -f /etc/systemd/system/yamparser.service
            sudo systemctl daemon-reload
            print_success "Сервис удален"
            ;;
        *)
            echo "🗺️ Скрипт развертывания YamParser"
            echo ""
            echo "Использование: $0 {команда}"
            echo ""
            echo "Команды:"
            echo "  install     - Полная установка на сервер"
            echo "  update      - Обновление зависимостей"
            echo "  uninstall   - Удаление сервиса"
            echo ""
            echo "Примеры:"
            echo "  $0 install    # Полная установка"
            echo "  $0 update     # Обновление"
            ;;
    esac
}

# Запуск главной функции
main "$@" 