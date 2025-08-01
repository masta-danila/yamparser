@echo off
REM Batch-скрипт для запуска парсера с логированием
REM Переходим в папку проекта (замените на ваш путь!)
cd /d "C:\Path\To\Your\Project\yamparser"

REM Создаем папку для логов если её нет
if not exist "logs" mkdir logs

REM Активируем виртуальное окружение
call venv\Scripts\activate.bat

REM Запускаем парсер (логи будут писаться автоматически)
python integrated_parser.py

REM Показываем где сохранены логи
echo.
echo 📁 Логи сохранены в папке logs\
echo Имя файла: %date:~-4%-%date:~-10,2%-%date:~-7,2%.txt
echo.
pause