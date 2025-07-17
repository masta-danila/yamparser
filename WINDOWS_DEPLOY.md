# 🪟 Развертывание YamParser на Windows Server

Инструкция по развертыванию парсера отзывов Яндекс Карт на Windows Server через RDP.

## 📋 Требования к серверу

### Минимальные требования:
- **ОС**: Windows Server 2016+, Windows 10/11
- **RAM**: минимум 4 ГБ, рекомендуется 8 ГБ+
- **Диск**: минимум 20 ГБ свободного места
- **RDP**: доступ по Remote Desktop

## 🚀 Пошаговая установка

### 1. Подключение к серверу
- Откройте **Remote Desktop Connection**
- Подключитесь к серверу по IP и учетным данным

### 2. Установка Python 3.12
1. Откройте браузер на сервере
2. Идите на https://www.python.org/downloads/
3. Скачайте **Python 3.12.x** для Windows
4. Запустите установщик:
   - ✅ Поставьте галочку **"Add Python to PATH"**
   - ✅ Выберите **"Install for all users"**
   - Нажмите **Install Now**

### 3. Установка Git
1. Идите на https://git-scm.com/download/win
2. Скачайте **Git for Windows**
3. Установите с настройками по умолчанию

### 4. Установка Google Chrome
1. Скачайте Chrome с https://www.google.com/chrome/
2. Установите браузер

### 5. Установка ChromeDriver
1. Узнайте версию Chrome: `chrome://version/`
2. Идите на https://chromedriver.chromium.org/
3. Скачайте ChromeDriver для вашей версии Chrome
4. Распакуйте `chromedriver.exe` в папку `C:\Windows\System32\`

## 📦 Развертывание проекта

### 1. Клонирование репозитория
Откройте **Command Prompt** (cmd) как **Администратор**:

```cmd
cd C:\
git clone https://github.com/masta-danila/yamparser.git
cd yamparser
```

### 2. Создание виртуального окружения
```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
```

### 3. Установка зависимостей
```cmd
pip install -r requirements.txt
```

### 4. Настройка credentials.json
1. Замените файл `credentials.json` на реальный файл Google Sheets API
2. Или скопируйте с локальной машины через RDP

### 5. Настройка прокси (опционально)
Отредактируйте файл `proxy.txt`:
```
# Формат: IP:PORT:USERNAME:PASSWORD
82.97.251.114:16172:username:password
203.0.113.10:3128:user1:pass1
```

### 6. Настройка конфигурации
Отредактируйте `config.py` под ваши нужды

## 🎮 Запуск парсера

### Разовый запуск
```cmd
cd C:\yamparser
venv\Scripts\activate
python integrated_parser.py
```

### Тестовый запуск отдельного URL
```cmd
venv\Scripts\activate
python reviews_parser.py "https://yandex.ru/maps/org/organization_name/123456789/reviews/"
```

## 🤖 Автоматизация (Windows Service)

### Создание bat файла для запуска
Создайте файл `run_parser.bat`:

```bat
@echo off
cd /d C:\yamparser
call venv\Scripts\activate
python integrated_parser.py
pause
```

### Настройка Task Scheduler (Планировщик заданий)

1. Откройте **Task Scheduler** (Планировщик заданий)
2. **Create Basic Task** → Далее
3. **Name**: `YamParser`
4. **Trigger**: Выберите частоту (Daily/Weekly/etc.)
5. **Action**: Start a program
6. **Program**: `C:\yamparser\run_parser.bat`
7. **Start in**: `C:\yamparser`
8. Готово!

### Альтернатива: Windows Service

Создайте файл `yamparser_service.py`:

```python
import win32serviceutil
import win32service
import win32event
import subprocess
import time
import os

class YamParserService(win32serviceutil.ServiceFramework):
    _svc_name_ = "YamParser"
    _svc_display_name_ = "YamParser Service"
    _svc_description_ = "Парсер отзывов Яндекс Карт"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

    def SvcDoRun(self):
        while self.is_running:
            try:
                # Запуск парсера
                os.chdir(r'C:\yamparser')
                subprocess.run([r'venv\Scripts\python.exe', 'integrated_parser.py'])
                
                # Пауза 1 час (3600 секунд)
                time.sleep(3600)
                
            except Exception as e:
                # Логирование ошибок
                with open(r'C:\yamparser\service_error.log', 'a') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error: {e}\n")
                time.sleep(300)  # При ошибке ждем 5 минут

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(YamParserService)
```

Установка сервиса:
```cmd
pip install pywin32
python yamparser_service.py install
python yamparser_service.py start
```

## 📊 Мониторинг

### Просмотр логов
- Логи приложения: `C:\yamparser\logs\`
- Логи сервиса: Event Viewer → Windows Logs → Application

### Проверка работы
```cmd
# Проверить процессы Python
tasklist | findstr python

# Проверить Chrome процессы  
tasklist | findstr chrome
```

### Управление сервисом
```cmd
# Статус сервиса
sc query YamParser

# Остановка сервиса
sc stop YamParser

# Запуск сервиса
sc start YamParser

# Удаление сервиса
python yamparser_service.py remove
```

## 🚨 Решение проблем

### Python не найден
```cmd
# Проверить установку Python
python --version
where python

# Если не работает, добавить в PATH:
# Панель управления → Система → Дополнительные параметры → Переменные среды
# Добавить C:\Python312\ и C:\Python312\Scripts\
```

### ChromeDriver не найден
```cmd
# Проверить ChromeDriver
chromedriver --version

# Если не работает:
# 1. Скачать правильную версию с chromedriver.chromium.org
# 2. Поместить chromedriver.exe в C:\Windows\System32\
# 3. Или добавить папку с chromedriver в PATH
```

### Ошибки прав доступа
- Запускать Command Prompt **как Администратор**
- Проверить права на папку `C:\yamparser`

### Проблемы с виртуальным окружением
```cmd
# Пересоздать venv
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 🔄 Обновление

### Обновление кода
```cmd
cd C:\yamparser
git pull
venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

### Перезапуск сервиса после обновления
```cmd
sc stop YamParser
sc start YamParser
```

## 📁 Структура файлов на Windows

```
C:\yamparser\
├── venv\                    # Виртуальное окружение
├── data\                    # Результаты парсинга
├── logs\                    # Логи приложения
├── chrome_profiles\         # Профили Chrome
├── credentials.json         # Google Sheets API
├── proxy.txt               # Прокси серверы
├── config.py               # Настройки
├── run_parser.bat          # Bat файл для запуска
├── yamparser_service.py    # Windows Service
├── integrated_parser.py    # Основной парсер
├── reviews_parser.py       # Парсер отзывов
└── requirements.txt        # Python зависимости
```

## 🛡️ Безопасность

### Файрвол Windows
- Разрешить Python в Windows Defender Firewall
- Разрешить Chrome/ChromeDriver

### Антивирус
- Добавить папку `C:\yamparser` в исключения антивируса
- Разрешить `python.exe` и `chromedriver.exe`

### Удаленный доступ
- Настроить RDP только для нужных пользователей
- Использовать сложные пароли
- Рассмотреть VPN для доступа к серверу

## 🎯 Результат

После успешной установки:
- ✅ Парсер работает на Windows Server
- ✅ Автоматический запуск через Task Scheduler или Windows Service
- ✅ Логирование в стандартные папки Windows
- ✅ Удаленное управление через RDP

**Время установки:** ~15-30 минут в зависимости от скорости интернета

---

**💡 Совет:** Для production рекомендуется использовать Windows Service для надежности и автоматического перезапуска при сбоях. 