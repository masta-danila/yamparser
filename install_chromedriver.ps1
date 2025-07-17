# ========================================================================
# Автоматическая установка ChromeDriver для Windows
# ========================================================================

Write-Host "🔍 Автоматическая установка ChromeDriver..." -ForegroundColor Green

# Функция для получения версии Chrome
function Get-ChromeVersion {
    try {
        # Проверяем Chrome в разных местах
        $chromePaths = @(
            "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
        )
        
        foreach ($path in $chromePaths) {
            if (Test-Path $path) {
                Write-Host "✅ Chrome найден: $path" -ForegroundColor Green
                $version = (Get-ItemProperty $path).VersionInfo.ProductVersion
                Write-Host "📋 Версия Chrome: $version" -ForegroundColor Cyan
                return $version
            }
        }
        
        Write-Host "❌ Chrome не найден в стандартных папках" -ForegroundColor Red
        return $null
    }
    catch {
        Write-Host "❌ Ошибка получения версии Chrome: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Функция для получения основной версии (например, 120.0.6099.109 -> 120)
function Get-MajorVersion {
    param($version)
    if ($version) {
        return $version.Split('.')[0]
    }
    return $null
}

# Функция для скачивания ChromeDriver
function Download-ChromeDriver {
    param($version)
    
    try {
        Write-Host "🌐 Получение URL для ChromeDriver версии $version..." -ForegroundColor Yellow
        
        # Получаем точную версию ChromeDriver
        $chromeDriverVersion = Invoke-RestMethod -Uri "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$version"
        Write-Host "📋 Версия ChromeDriver: $chromeDriverVersion" -ForegroundColor Cyan
        
        # URL для скачивания
        $downloadUrl = "https://chromedriver.storage.googleapis.com/$chromeDriverVersion/chromedriver_win32.zip"
        Write-Host "🔗 URL: $downloadUrl" -ForegroundColor Gray
        
        # Создаем временную папку
        $tempDir = "$env:TEMP\chromedriver_install"
        if (Test-Path $tempDir) {
            Remove-Item $tempDir -Recurse -Force
        }
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Скачиваем архив
        $zipPath = "$tempDir\chromedriver.zip"
        Write-Host "⬇️ Скачивание ChromeDriver..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
        
        # Распаковываем
        Write-Host "📦 Распаковка архива..." -ForegroundColor Yellow
        Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
        
        # Проверяем что файл существует
        $chromeDriverExe = "$tempDir\chromedriver.exe"
        if (-not (Test-Path $chromeDriverExe)) {
            throw "ChromeDriver.exe не найден после распаковки"
        }
        
        # Копируем в System32
        $systemPath = "$env:SystemRoot\System32\chromedriver.exe"
        Write-Host "📁 Копирование в System32..." -ForegroundColor Yellow
        Copy-Item $chromeDriverExe $systemPath -Force
        
        # Проверяем установку
        Write-Host "✅ Проверка установки..." -ForegroundColor Green
        $installedVersion = & chromedriver --version 2>$null
        if ($installedVersion) {
            Write-Host "🎉 ChromeDriver успешно установлен!" -ForegroundColor Green
            Write-Host "📋 Установленная версия: $installedVersion" -ForegroundColor Cyan
        } else {
            throw "ChromeDriver не запускается после установки"
        }
        
        # Очищаем временные файлы
        Remove-Item $tempDir -Recurse -Force
        
        return $true
    }
    catch {
        Write-Host "❌ Ошибка установки ChromeDriver: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Основная логика
Write-Host ""
Write-Host "🚀 Начинаем автоматическую установку ChromeDriver" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Gray

# Проверяем права администратора
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ Требуются права администратора!" -ForegroundColor Red
    Write-Host "Запустите PowerShell как администратор и повторите" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Получаем версию Chrome
$chromeVersion = Get-ChromeVersion
if (-not $chromeVersion) {
    Write-Host "❌ Установите Google Chrome перед установкой ChromeDriver" -ForegroundColor Red
    Write-Host "Скачайте Chrome с https://www.google.com/chrome/" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Получаем основную версию
$majorVersion = Get-MajorVersion $chromeVersion
if (-not $majorVersion) {
    Write-Host "❌ Не удалось определить основную версию Chrome" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "🎯 Основная версия Chrome: $majorVersion" -ForegroundColor Cyan

# Проверяем, установлен ли уже ChromeDriver
try {
    $existingVersion = & chromedriver --version 2>$null
    if ($existingVersion) {
        Write-Host "📋 Найден установленный ChromeDriver: $existingVersion" -ForegroundColor Yellow
        $response = Read-Host "Переустановить? (y/N)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "✅ Установка отменена" -ForegroundColor Green
            exit 0
        }
    }
}
catch {
    Write-Host "📋 ChromeDriver не установлен" -ForegroundColor Yellow
}

# Скачиваем и устанавливаем ChromeDriver
$success = Download-ChromeDriver $majorVersion

if ($success) {
    Write-Host ""
    Write-Host "🎉 Установка завершена успешно!" -ForegroundColor Green
    Write-Host "✅ ChromeDriver готов к использованию" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Установка не удалась" -ForegroundColor Red
    Write-Host "🔧 Попробуйте установить вручную:" -ForegroundColor Yellow
    Write-Host "   1. Откройте chrome://version/" -ForegroundColor Gray
    Write-Host "   2. Идите на https://chromedriver.chromium.org/" -ForegroundColor Gray
    Write-Host "   3. Скачайте версию для Chrome $majorVersion" -ForegroundColor Gray
    Write-Host "   4. Поместите chromedriver.exe в C:\Windows\System32\" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Нажмите Enter для выхода" 