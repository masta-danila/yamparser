"""
Модуль управления веб-драйверами для парсинга отзывов Яндекс.Карт
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import stat
import time
import threading
import tempfile

# Импорт seleniumwire для рабочих прокси
try:
    from seleniumwire import webdriver as wiredriver
    SELENIUMWIRE_AVAILABLE = True
except ImportError:
    SELENIUMWIRE_AVAILABLE = False
    wiredriver = None

# Импорт менеджера прокси
try:
    from proxy_manager import ProxyManagerSeleniumWire
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# Глобальная блокировка для создания драйверов
_driver_creation_lock = threading.Lock()

def setup_driver(device_type="desktop", proxy_manager=None, profile_path=None):
    """Настройка драйвера для получения отзывов с поддержкой рабочих прокси (seleniumwire)"""
    thread_id = threading.current_thread().ident
    print(f"🚀 Настройка Selenium драйвера ({device_type}) в потоке {thread_id}...")
    
    # Настройки браузера
    options = Options()
    # options.add_argument("--headless")  # Оставляем видимым
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Настройка прокси если доступен менеджер (РАБОЧИЙ МЕТОД SELENIUMWIRE)
    current_proxy = None
    proxy_options = None
    use_seleniumwire = False
    
    if proxy_manager and PROXY_AVAILABLE and SELENIUMWIRE_AVAILABLE:
        current_proxy = proxy_manager.get_random_proxy()  # Случайный прокси вместо последовательного
        if current_proxy:
            # Используем рабочий метод seleniumwire
            chrome_options, proxy_options = proxy_manager.configure_seleniumwire_proxy(current_proxy)
            options = chrome_options  # Заменяем на настроенные опции
            use_seleniumwire = True
            print(f"🌐 Используется случайный прокси (seleniumwire): {current_proxy['ip']}:{current_proxy['port']}")
        else:
            print("⚠️ Нет доступных прокси, используется прямое соединение")
    elif proxy_manager and PROXY_AVAILABLE and not SELENIUMWIRE_AVAILABLE:
        print("⚠️ Прокси менеджер доступен, но seleniumwire не установлен")
        print("💡 Установите: pip install selenium-wire")
    
    # Управление профилями
    user_data_dir = None
    
    # Если передан готовый профиль, используем его
    if profile_path:
        user_data_dir = profile_path
        print(f"📁 Используется переданный профиль: {os.path.basename(profile_path)}")
    elif device_type == "mobile":
        # Создание временного профиля если не передан готовый
        user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_temp_")
        print(f"📁 Создан временный профиль: {os.path.basename(user_data_dir)}")
    else:
        # Desktop режим - без профилей
        user_data_dir = None
        print(f"🖥️ Desktop режим: профили не используются")
    
    # Добавляем профиль только если он есть (mobile)
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Если нужна мобильная версия
    mobile_device_size = None
    if device_type == "mobile":
        # Определяем размеры устройства (можно расширить для разных устройств)
        device_width, device_height = 390, 844  # iPhone 13 по умолчанию
        
        mobile_emulation = {
            "deviceMetrics": {"width": device_width, "height": device_height, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        mobile_device_size = (device_width, device_height)  # Сохраняем размер для настройки окна
        
        # Устанавливаем размер окна сразу при создании браузера
        window_width = device_width + 50
        window_height = device_height + 150
        options.add_argument(f"--window-size={window_width},{window_height}")
        print(f"📱 Используем мобильную эмуляцию: {device_width}x{device_height}")
        print(f"📏 Размер окна будет установлен при создании: {window_width}x{window_height}")
    
    print(f"📁 Профиль: {user_data_dir}")
    
    # Создаем драйвер (с поддержкой seleniumwire для прокси)
    if use_seleniumwire and proxy_options and SELENIUMWIRE_AVAILABLE:
        print("🔧 Создаем драйвер с seleniumwire и прокси...")
        driver = None
        try:
            with _driver_creation_lock:
                driver = wiredriver.Chrome(
                    options=options,
                    seleniumwire_options=proxy_options
                )
                # Убираем признаки автоматизации
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                print(f"✅ Драйвер с рабочими прокси создан успешно в потоке {thread_id}!")
                return driver
        except Exception as e:
            print(f"❌ Ошибка создания драйвера с прокси: {e}")
            # Закрываем неудачно созданный драйвер, если он существует
            if driver:
                try:
                    driver.quit()
                    print("🔒 Неудачный драйвер закрыт")
                except:
                    pass
            print("🔄 Переключаемся на обычный драйвер...")
    
    # Обычный драйвер (без прокси или если seleniumwire недоступен)
    print("🔧 Создаем обычный драйвер...")
    
    # Используем блокировку для предотвращения конфликтов при создании драйвера
    with _driver_creation_lock:
        driver_path = ChromeDriverManager().install()
        driver_dir = os.path.dirname(driver_path)
        actual_driver = os.path.join(driver_dir, "chromedriver")
        
        if os.path.exists(actual_driver):
            # Исправляем права доступа
            current_permissions = os.stat(actual_driver).st_mode
            if not (current_permissions & stat.S_IXUSR):
                print("🔧 Исправляем права доступа...")
                os.chmod(actual_driver, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            
            service = Service(actual_driver)
            print(f"🔧 Создаем обычный драйвер в потоке {thread_id}...")
            driver = webdriver.Chrome(service=service, options=options)
            
            return driver
        else:
            raise Exception("ChromeDriver не найден!")

def get_driver_creation_lock():
    """Возвращает глобальную блокировку для создания драйверов"""
    return _driver_creation_lock 