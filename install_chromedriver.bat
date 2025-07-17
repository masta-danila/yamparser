@echo off
echo.
echo ========================================
echo  Автоматическая установка ChromeDriver
echo ========================================
echo.

REM Проверяем права администратора
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Права администратора подтверждены
) else (
    echo ❌ Требуются права администратора!
    echo Запустите этот файл как администратор
    echo (Правый клик → "Запуск от имени администратора")
    pause
    exit /b 1
)

echo.
echo 🚀 Запуск PowerShell скрипта...
echo.

REM Запускаем PowerShell скрипт
powershell -ExecutionPolicy Bypass -File "%~dp0install_chromedriver.ps1"

echo.
echo 🏁 Скрипт завершен
pause 