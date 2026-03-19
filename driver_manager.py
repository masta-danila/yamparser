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
import shutil
from thread_logger import thread_print

# Импорт настроек из config
try:
    from config import HEADLESS_MODE
except ImportError:
    HEADLESS_MODE = False  # По умолчанию показываем браузеры

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

# Глобальная блокировка только для установки драйвера
_driver_install_lock = threading.Lock()
# Кэш для пути к драйверу
_driver_path_cache = None

def cleanup_profiles_folder():
    """
    Очищает папку chrome_profiles от всех старых профилей
    """
    profiles_dir = os.path.join(os.getcwd(), "chrome_profiles")
    
    if not os.path.exists(profiles_dir):
        thread_print("📂 Папка chrome_profiles не существует")
        return
    
    try:
        profiles = [p for p in os.listdir(profiles_dir) if p.startswith("chrome_profile_")]
        
        if not profiles:
            thread_print("✅ Папка chrome_profiles пуста")
            return
        
        thread_print(f"🧹 Найдено {len(profiles)} старых профилей для удаления...")
        
        deleted_count = 0
        for profile in profiles:
            profile_path = os.path.join(profiles_dir, profile)
            try:
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path, ignore_errors=True)
                    if not os.path.exists(profile_path):
                        deleted_count += 1
                        thread_print(f"🗑️ Удален профиль: {profile}")
                    else:
                        thread_print(f"⚠️ Не удалось удалить: {profile}")
            except Exception as e:
                thread_print(f"❌ Ошибка удаления {profile}: {e}")
        
        thread_print(f"✅ Очистка завершена: удалено {deleted_count} из {len(profiles)} профилей")
        
        # Удаляем папку если она пустая
        try:
            remaining_items = os.listdir(profiles_dir)
            if not remaining_items:
                os.rmdir(profiles_dir)
                thread_print("📂 Пустая папка chrome_profiles удалена")
        except:
            pass
            
    except Exception as e:
        thread_print(f"❌ Ошибка очистки папки профилей: {e}")

def cleanup_all_profiles():
    """
    Полная очистка всех профилей (для завершения программы)
    """
    thread_print("🧹 Финальная очистка всех профилей...")
    cleanup_profiles_folder()

def initialize_profiles_cleanup():
    """
    Инициализация с очисткой старых профилей
    """
    thread_print("🚀 Инициализация системы профилей...")
    cleanup_profiles_folder()

def setup_driver(device_type="desktop", proxy_manager=None, profile_path=None):
    """Настройка драйвера для получения отзывов с поддержкой рабочих прокси (seleniumwire)"""
    global _driver_path_cache
    
    thread_id = threading.current_thread().ident
    thread_print(f"🚀 Настройка Selenium драйвера ({device_type}) в потоке {thread_id}...")
    
    # Настройки браузера
    options = Options()
    
    # Проверяем настройку показа браузеров
    if HEADLESS_MODE:
        options.add_argument("--headless")
        thread_print("🔇 Браузер запущен в скрытом режиме (headless)")
    else:
        thread_print("👁️ Браузер будет видимым")
        
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Параметры для стабильного открытия без дергания
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Устанавливаем позицию окна для предсказуемого поведения
    options.add_argument("--window-position=100,100")
    
    # КРИТИЧЕСКИ ВАЖНО: Прокси обязательны для безопасности
    if not proxy_manager or not PROXY_AVAILABLE or not SELENIUMWIRE_AVAILABLE:
        error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Прокси недоступны!"
        thread_print(error_msg)
        if not proxy_manager:
            thread_print("   • Прокси менеджер не передан")
        if not PROXY_AVAILABLE:
            thread_print("   • Модуль proxy_manager недоступен")
        if not SELENIUMWIRE_AVAILABLE:
            thread_print("   • Модуль seleniumwire недоступен")
        thread_print("🚫 РАБОТА БЕЗ ПРОКСИ ЗАПРЕЩЕНА - риск бана IP!")
        thread_print("💡 Убедитесь что:")
        thread_print("   1. Файл proxy.txt существует и содержит рабочие прокси")
        thread_print("   2. Установлен seleniumwire: pip install selenium-wire")
        thread_print("   3. Прокси менеджер передан в функцию")
        raise Exception("Прокси недоступны - работа без прокси запрещена!")
    
    # Проверяем наличие прокси в менеджере
    stats = proxy_manager.get_stats()
    if stats['total_proxies'] == 0:
        error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Нет загруженных прокси!"
        thread_print(error_msg)
        thread_print("🚫 РАБОТА БЕЗ ПРОКСИ ЗАПРЕЩЕНА - риск бана IP!")
        thread_print("💡 Проверьте файл proxy.txt и формат прокси: IP:PORT:USERNAME:PASSWORD")
        raise Exception("Нет доступных прокси - работа без прокси запрещена!")
    
    thread_print(f"✅ Доступно прокси: {stats['total_proxies']}")
    
    # Управление профилями
    user_data_dir = None
    
    # Если передан готовый профиль, используем его
    if profile_path:
        user_data_dir = profile_path
        thread_print(f"📁 Используется переданный профиль: {os.path.basename(profile_path)}")
    elif device_type == "mobile":
        # Создание временного профиля в текущей папке проекта
        profiles_dir = os.path.join(os.getcwd(), "chrome_profiles")
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
            thread_print(f"📂 Создана папка для профилей: chrome_profiles/")
        
        # Генерируем уникальное имя профиля
        import uuid
        profile_name = f"chrome_profile_{uuid.uuid4().hex[:8]}"
        user_data_dir = os.path.join(profiles_dir, profile_name)
        
        thread_print(f"📁 Создан профиль: chrome_profiles/{profile_name}")
    else:
        # Desktop режим - без профилей
        user_data_dir = None
        thread_print(f"🖥️ Desktop режим: профили не используются")
    
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
        
        # Устанавливаем размер окна через Chrome options
        window_width = 500  # Минимальная ширина Chrome
        window_height = 994  # 844 + 150
        options.add_argument(f"--window-size={window_width},{window_height}")
        
        thread_print(f"📱 Используем мобильную эмуляцию: {device_width}x{device_height}")
        thread_print(f"📏 Размер окна: {window_width}x{window_height}")
        thread_print(f"💡 Внутренняя область (viewport): {device_width}x{device_height}")
    
    thread_print(f"📁 Профиль: {user_data_dir}")
    
    # Получаем путь к драйверу (с блокировкой только для установки)
    if _driver_path_cache is None:
        with _driver_install_lock:
            if _driver_path_cache is None:  # Двойная проверка
                _driver_path_cache = ChromeDriverManager().install()
    
    # Пробуем прокси до тех пор, пока не найдем рабочий
    max_proxy_attempts = min(5, stats['total_proxies'])  # Максимум 5 попыток или все доступные прокси
    thread_print(f"🔄 Будем пробовать до {max_proxy_attempts} прокси...")
    
    for attempt in range(max_proxy_attempts):
        current_proxy = proxy_manager.get_random_proxy()
        if not current_proxy:
            thread_print(f"❌ Попытка {attempt + 1}: Не удалось получить прокси")
            continue
            
        thread_print(f"🧪 Попытка {attempt + 1}/{max_proxy_attempts}: Тестируем прокси {current_proxy['ip']}:{current_proxy['port']}")
        
        driver = None
        try:
            # Настраиваем прокси для seleniumwire
            chrome_options, proxy_options = proxy_manager.configure_seleniumwire_proxy(current_proxy)
            
            # Добавляем наши настройки к chrome_options от прокси-менеджера
            for arg in options.arguments:
                if not any(arg.startswith(existing_arg.split('=')[0]) for existing_arg in chrome_options.arguments):
                    chrome_options.add_argument(arg)
            
            # Добавляем экспериментальные опции
            for option_name, option_value in options.experimental_options.items():
                chrome_options.add_experimental_option(option_name, option_value)
            
            # Создаем драйвер с текущим прокси
            driver = wiredriver.Chrome(
                options=chrome_options,
                seleniumwire_options=proxy_options
            )
            
            # Убираем признаки автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # КРИТИЧЕСКИ ВАЖНО: Тестируем прокси соединение
            thread_print(f"🧪 Тестируем соединение через прокси {current_proxy['ip']}:{current_proxy['port']}...")
            try:
                # Быстрая проверка соединения
                driver.set_page_load_timeout(30)  # Таймаут 30 секунд
                
                driver.get("http://icanhazip.com")
                
                # Проверяем, что страница загрузилась и получили валидный IP
                page_source = driver.page_source.strip()
                
                # Проверяем, что получили IP (простая валидация)
                if page_source and len(page_source) > 5 and ('.' in page_source or ':' in page_source):
                    thread_print(f"✅ Прокси {current_proxy['ip']}:{current_proxy['port']} работает корректно!")
                    thread_print(f"   IP через прокси: {page_source}")
                    thread_print(f"✅ Драйвер с рабочим прокси создан успешно в потоке {thread_id}!")
                    return driver
                else:
                    thread_print(f"❌ Прокси {current_proxy['ip']}:{current_proxy['port']} не работает (некорректный ответ)")
                    thread_print(f"   Получен ответ: {page_source[:100]}")
                    raise Exception("Прокси не работает - некорректный ответ")
                    
            except Exception as proxy_test_error:
                thread_print(f"❌ Ошибка тестирования прокси {current_proxy['ip']}:{current_proxy['port']}: {proxy_test_error}")
                # Закрываем драйвер с неработающим прокси
                if driver:
                    try:
                        driver.quit()
                        thread_print(f"🔒 Драйвер с неработающим прокси {current_proxy['ip']} закрыт")
                    except:
                        pass
                    driver = None
                # Продолжаем пробовать следующий прокси
                continue
                
        except Exception as e:
            thread_print(f"❌ Ошибка создания драйвера с прокси {current_proxy['ip']}:{current_proxy['port']}: {e}")
            # Закрываем неудачно созданный драйвер, если он существует
            if driver:
                try:
                    driver.quit()
                    thread_print(f"🔒 Неудачный драйвер с прокси {current_proxy['ip']} закрыт")
                except:
                    pass
            # Продолжаем пробовать следующий прокси
            continue
    
    # Если дошли до сюда, значит ни один прокси не сработал
    error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА: Ни один из {max_proxy_attempts} прокси не работает!"
    thread_print(error_msg)
    thread_print("🚫 РАБОТА БЕЗ ПРОКСИ ЗАПРЕЩЕНА - риск бана IP!")
    thread_print("💡 Возможные решения:")
    thread_print("   1. Проверьте качество прокси в proxy.txt")
    thread_print("   2. Обратитесь к провайдеру прокси")
    thread_print("   3. Обновите список прокси")
    thread_print("   4. Проверьте интернет соединение")
    raise Exception("Все прокси недоступны - работа без прокси запрещена!")

def get_driver_creation_lock():
    """Возвращает блокировку для установки драйвера (для совместимости)"""
    return _driver_install_lock 

def ensure_correct_window_size(driver, device_type="mobile"):
    """
    Принудительно устанавливает правильный размер окна браузера
    
    Args:
        driver: WebDriver instance
        device_type: "mobile" или "desktop"
    """
    try:
        if device_type == "mobile":
            # Размеры для мобильной эмуляции (iPhone 13)
            window_width = 500   # Минимальная ширина Chrome
            window_height = 994  # 844 + 150 (рамки)
            
            # Получаем текущий размер
            current_size = driver.get_window_size()
            current_width = current_size['width']
            current_height = current_size['height']
            
            # Проверяем, нужно ли изменить размер
            if current_width != window_width or current_height != window_height:
                thread_print(f"📏 Текущий размер окна: {current_width}x{current_height}")
                thread_print(f"📏 Устанавливаем правильный размер: {window_width}x{window_height}")
                
                # Устанавливаем правильный размер
                driver.set_window_size(window_width, window_height)
                
                # Проверяем результат
                new_size = driver.get_window_size()
                thread_print(f"✅ Размер окна установлен: {new_size['width']}x{new_size['height']}")
                
                return True
            else:
                thread_print(f"✅ Размер окна уже правильный: {current_width}x{current_height}")
                return False
        else:
            thread_print("🖥️ Desktop режим: размер окна не изменяется")
            return False
            
    except Exception as e:
        thread_print(f"❌ Ошибка установки размера окна: {e}")
        return False

def get_expected_window_size(device_type="mobile"):
    """
    Возвращает ожидаемый размер окна для указанного типа устройства
    
    Args:
        device_type: "mobile" или "desktop"
        
    Returns:
        tuple: (width, height) или None для desktop
    """
    if device_type == "mobile":
        return (500, 994)  # iPhone 13 с минимальной шириной Chrome
    else:
        return None 

def handle_captcha_with_proxy_switching(driver, proxy_manager, device_type="desktop", profile_path=None, max_proxy_attempts=3):
    """
    Обработка капчи с автоматическим переключением прокси и созданием нового профиля
    
    Args:
        driver: текущий драйвер с капчей
        proxy_manager: менеджер прокси
        device_type: тип устройства
        profile_path: путь к профилю (будет игнорирован, создается новый)
        max_proxy_attempts: максимальное количество попыток с разными прокси
    
    Returns:
        Новый драйвер с другим прокси и новым профилем или None если все прокси не работают
    """
    thread_id = threading.current_thread().ident
    thread_print(f"🤖 Обнаружена капча! Создаем новый профиль и переключаем прокси в потоке {thread_id}...")
    
    # Сохраняем URL текущей страницы
    try:
        current_url = driver.current_url
        thread_print(f"📍 Текущий URL: {current_url}")
    except:
        current_url = None
        thread_print("❌ Не удалось получить текущий URL")
    
    # Закрываем текущий драйвер
    try:
        driver.quit()
        thread_print("🔒 Старый драйвер закрыт")
    except:
        thread_print("⚠️ Ошибка при закрытии старого драйвера")
    
    # Удаляем старый профиль если он был временным
    if profile_path and ("chrome_profile_temp_" in profile_path or "chrome_profile_" in profile_path):
        try:
            import shutil
            shutil.rmtree(profile_path, ignore_errors=True)
            thread_print(f"🗑️ Старый профиль удален: {os.path.basename(profile_path)}")
        except:
            thread_print("⚠️ Не удалось удалить старый профиль")
    
    # Пробуем создать новый драйвер с другим прокси и новым профилем
    for attempt in range(max_proxy_attempts):
        thread_print(f"🔄 Попытка {attempt + 1}/{max_proxy_attempts}: Создаем новый драйвер с новым прокси и профилем...")
        
        try:
            # ВАЖНО: Передаем None как profile_path, чтобы создался новый временный профиль
            new_driver = setup_driver(device_type, proxy_manager, None)
            
            if new_driver:
                thread_print(f"✅ Новый драйвер создан с новым профилем и прокси!")
                
                # Если есть URL, пробуем загрузить страницу
                if current_url:
                    try:
                        thread_print(f"🔗 Загружаем страницу с новым прокси и профилем...")
                        new_driver.get(current_url)
                        
                        # Ждем загрузки
                        time.sleep(3)
                        
                        # Проверяем, есть ли капча на новой странице
                        from page_handler import check_for_captcha
                        if check_for_captcha(new_driver):
                            thread_print(f"❌ Капча все еще присутствует с прокси #{attempt + 1}")
                            new_driver.quit()
                            continue
                        else:
                            thread_print(f"🎉 Капча исчезла! Новый прокси и профиль работают!")
                            return new_driver
                            
                    except Exception as e:
                        thread_print(f"❌ Ошибка загрузки страницы с новым прокси: {e}")
                        new_driver.quit()
                        continue
                else:
                    # Если нет URL, просто возвращаем новый драйвер
                    thread_print(f"✅ Новый драйвер готов с новым профилем (URL не сохранен)")
                    return new_driver
                    
        except Exception as e:
            thread_print(f"❌ Ошибка создания нового драйвера (попытка {attempt + 1}): {e}")
            continue
    
    # Если все попытки неудачны
    thread_print(f"❌ Не удалось создать рабочий драйвер после {max_proxy_attempts} попыток")
    return None

def restart_driver_with_new_proxy(driver, proxy_manager, device_type="desktop", profile_path=None):
    """
    Перезапуск драйвера с новым прокси и новым профилем (упрощенная версия)
    
    Args:
        driver: текущий драйвер
        proxy_manager: менеджер прокси
        device_type: тип устройства
        profile_path: путь к профилю (будет игнорирован, создается новый)
    
    Returns:
        Новый драйвер или None
    """
    thread_id = threading.current_thread().ident
    thread_print(f"🔄 Перезапускаем драйвер с новым прокси и профилем в потоке {thread_id}...")
    
    # Сохраняем URL
    current_url = None
    try:
        current_url = driver.current_url
    except:
        pass
    
    # Закрываем старый драйвер
    try:
        driver.quit()
        thread_print("🔒 Старый драйвер закрыт")
    except:
        pass
    
    # Удаляем старый профиль если он был временным
    if profile_path and ("chrome_profile_temp_" in profile_path or "chrome_profile_" in profile_path):
        try:
            import shutil
            shutil.rmtree(profile_path, ignore_errors=True)
            thread_print(f"🗑️ Старый профиль удален: {os.path.basename(profile_path)}")
        except:
            thread_print("⚠️ Не удалось удалить старый профиль")
    
    # Создаем новый драйвер с новым профилем
    try:
        # ВАЖНО: Передаем None как profile_path, чтобы создался новый временный профиль
        new_driver = setup_driver(device_type, proxy_manager, None)
        if new_driver and current_url:
            thread_print("🔗 Загружаем страницу с новым прокси и профилем...")
            new_driver.get(current_url)
            time.sleep(2)
        return new_driver
    except Exception as e:
        thread_print(f"❌ Ошибка перезапуска драйвера: {e}")
        return None 

def get_driver_profile_path(driver):
    """
    Получает путь к профилю драйвера
    
    Args:
        driver: WebDriver instance
        
    Returns:
        str: путь к профилю или None
    """
    try:
        # Получаем опции драйвера
        if hasattr(driver, 'capabilities'):
            chrome_options = driver.capabilities.get('chrome', {}).get('chromedriverVersion', '')
            
            # Пытаемся получить путь к профилю из опций
            if hasattr(driver, 'service') and hasattr(driver.service, 'command_line_args'):
                for arg in driver.service.command_line_args():
                    if '--user-data-dir=' in arg:
                        return arg.split('--user-data-dir=')[1]
            
            # Альтернативный способ через опции
            if hasattr(driver, 'options'):
                for arg in driver.options.arguments:
                    if '--user-data-dir=' in arg:
                        return arg.split('--user-data-dir=')[1]
        
        # Если не удалось получить путь
        return None
        
    except Exception as e:
        thread_print(f"⚠️ Не удалось получить путь к профилю: {e}")
        return None 