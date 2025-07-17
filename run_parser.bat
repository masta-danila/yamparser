@echo off
echo.
echo ========================================
echo  YamParser - Парсер отзывов Яндекс Карт
echo ========================================
echo.

cd /d "%~dp0"

REM Проверяем существование виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Виртуальное окружение не найдено!
    echo Сначала создайте venv:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo 🚀 Активация виртуального окружения...
call venv\Scripts\activate.bat

echo 📋 Проверка зависимостей...
python -c "import selenium, psycopg2, pandas" 2>nul
if errorlevel 1 (
    echo ❌ Некоторые зависимости не установлены!
    echo Установите зависимости: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Все зависимости найдены

echo.
echo 🗺️ Запуск интегрированного парсера...
echo.

python integrated_parser.py

echo.
echo 🏁 Парсинг завершен
echo.
pause 