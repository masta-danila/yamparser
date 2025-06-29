from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# Импорт seleniumwire для рабочих прокси
try:
    from seleniumwire import webdriver as wiredriver
    SELENIUMWIRE_AVAILABLE = True
except ImportError:
    SELENIUMWIRE_AVAILABLE = False
    wiredriver = None
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import stat
import time
import sys
import re
from datetime import datetime
import random

# Импорт модуля работы с базой данных
try:
    from reviews_database import ReviewsDatabase
    DATABASE_AVAILABLE = True
    print("✅ Модуль базы данных подключен")
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ Модуль reviews_database.py не найден - отзывы не будут сохраняться в БД")

# Импорт функций решения CAPTCHA
try:
    from selenium_captcha_solver import detect_captcha as captcha_detect, solve_captcha as captcha_solve
    CAPTCHA_SOLVER_AVAILABLE = True
    print("✅ Модуль решения CAPTCHA подключен")
except ImportError:
    CAPTCHA_SOLVER_AVAILABLE = False
    print("⚠️ Модуль selenium_captcha_solver.py не найден - CAPTCHA будет обрабатываться базовым способом")

# Импорт менеджера прокси (РАБОЧИЙ МЕТОД SELENIUMWIRE)
try:
    from proxy_manager_seleniumwire import ProxyManagerSeleniumWire
    PROXY_AVAILABLE = True
    print("✅ Модуль рабочих прокси (seleniumwire) подключен")
except ImportError:
    PROXY_AVAILABLE = False
    print("⚠️ Модуль proxy_manager_seleniumwire.py не найден - прокси будут недоступны")

# Импорт упрощенного обработчика всплывающих окон приложения
try:
    from simple_popup_handler import handle_popup_simple
    POPUP_HANDLER_AVAILABLE = True
    print("✅ Модуль простой обработки всплывающих окон подключен")
except ImportError:
    POPUP_HANDLER_AVAILABLE = False
    print("⚠️ Модуль simple_popup_handler.py не найден - всплывающие окна не будут обрабатываться автоматически")

def setup_driver(device_type="desktop", proxy_manager=None):
    """Настройка драйвера для получения отзывов с поддержкой рабочих прокси (seleniumwire)"""
    print(f"🚀 Настройка Selenium драйвера ({device_type})...")
    
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
        current_proxy = proxy_manager.get_next_proxy()
        if current_proxy:
            # Используем рабочий метод seleniumwire
            chrome_options, proxy_options = proxy_manager.configure_seleniumwire_proxy(current_proxy)
            options = chrome_options  # Заменяем на настроенные опции
            use_seleniumwire = True
            print(f"🌐 Используется рабочий прокси (seleniumwire): {current_proxy['ip']}:{current_proxy['port']}")
        else:
            print("⚠️ Нет доступных прокси, используется прямое соединение")
    elif proxy_manager and PROXY_AVAILABLE and not SELENIUMWIRE_AVAILABLE:
        print("⚠️ Прокси менеджер доступен, но seleniumwire не установлен")
        print("💡 Установите: pip install selenium-wire")
    
    # Создаем папку для профиля с уникальным timestamp
    import time
    timestamp = int(time.time() * 1000)  # Миллисекунды для уникальности
    user_data_dir = os.path.join(os.getcwd(), f"reviews_profile_{timestamp}")
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Если нужна мобильная версия
    if device_type == "mobile":
        mobile_emulation = {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        print("📱 Используем мобильную эмуляцию")
    
    print(f"📁 Профиль: {user_data_dir}")
    
    # Создаем драйвер (с поддержкой seleniumwire для прокси)
    if use_seleniumwire and proxy_options and SELENIUMWIRE_AVAILABLE:
        print("🔧 Создаем драйвер с seleniumwire и прокси...")
        try:
            driver = wiredriver.Chrome(
                options=options,
                seleniumwire_options=proxy_options
            )
            # Убираем признаки автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Драйвер с рабочими прокси создан успешно!")
            return driver
        except Exception as e:
            print(f"❌ Ошибка создания драйвера с прокси: {e}")
            print("🔄 Переключаемся на обычный драйвер...")
    
    # Обычный драйвер (без прокси или если seleniumwire недоступен)
    print("🔧 Создаем обычный драйвер...")
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
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    else:
        raise Exception("ChromeDriver не найден!")

def extract_card_id_from_url(url: str) -> str:
    """Извлечь ID карточки из URL Яндекс Карт"""
    # Паттерн для поиска ID карточки в URL
    # Ищем числовой ID после /org/название/
    pattern = r'/org/[^/]+/(\d+)/?'
    match = re.search(pattern, url)
    
    if match:
        card_id = match.group(1)
        print(f"🆔 Извлечен ID карточки: {card_id}")
        return card_id
    else:
        print(f"❌ Не удалось извлечь ID карточки из URL: {url}")
        return None

def get_page_info(driver):
    """Получение информации о странице"""
    info = {
        "url": driver.current_url,
        "title": driver.title,
        "timestamp": time.time()
    }
    
    print(f"🌐 URL: {info['url']}")
    print(f"📄 Заголовок: {info['title']}")
    
    return info

def check_for_captcha(driver):
    """Улучшенная проверка на наличие CAPTCHA"""
    # Проверяем URL - самый надежный способ
    if "showcaptcha" in driver.current_url.lower():
        print("🤖 CAPTCHA обнаружена в URL (showcaptcha)")
        return True
    
    # Проверяем заголовок страницы
    title = driver.title.lower()
    if any(phrase in title for phrase in ["are you not a robot", "не робот", "captcha"]):
        print(f"🤖 CAPTCHA обнаружена в заголовке: '{driver.title}'")
        return True
    
    # Проверяем специфичные элементы CAPTCHA
    captcha_selectors = [
        "iframe[src*='captcha']",
        ".smart-captcha",
        ".captcha-checkbox",
        "input[type='checkbox'][aria-label*='робот']",
        "[data-testid*='captcha']"
    ]
    
    for selector in captcha_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and any(elem.is_displayed() for elem in elements):
                print(f"🤖 CAPTCHA обнаружена по селектору: {selector}")
                return True
        except:
            continue
    
    # Проверяем специфичные тексты только если они видимы на странице
    captcha_texts = [
        "Подтвердите, что запросы отправляли вы",
        "Я не робот",
        "I am not a robot"
    ]
    
    for text in captcha_texts:
        try:
            xpath = f"//*[contains(text(), '{text}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            if elements and any(elem.is_displayed() for elem in elements):
                print(f"🤖 CAPTCHA обнаружена по тексту: '{text}'")
                return True
        except:
            continue
    
    return False

def handle_captcha_automatically(driver):
    """Автоматическое решение CAPTCHA с использованием функций из selenium_captcha_solver.py"""
    print("🤖 Запускаем автоматическое решение CAPTCHA...")
    
    if not CAPTCHA_SOLVER_AVAILABLE:
        print("❌ Модуль решения CAPTCHA недоступен")
        return False
    
    try:
        # Используем продвинутую детекцию CAPTCHA
        captcha_found, captcha_element = captcha_detect(driver)
        
        if not captcha_found:
            print("✅ CAPTCHA не обнаружена продвинутым детектором")
            return True
        
        print("🎯 CAPTCHA подтверждена, пытаемся решить...")
        
        # Пытаемся решить CAPTCHA
        solved = captcha_solve(driver, captcha_element)
        
        if solved:
            print("🎉 CAPTCHA успешно решена автоматически!")
            # Ждем перезагрузки страницы
            time.sleep(3)
            
            # Проверяем, что мы вернулись на нужную страницу
            final_captcha_check, _ = captcha_detect(driver)
            if not final_captcha_check:
                print("✅ Подтверждено: CAPTCHA больше нет")
                return True
            else:
                print("⚠️ CAPTCHA все еще присутствует")
                return False
        else:
            print("❌ Не удалось решить CAPTCHA автоматически")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при автоматическом решении CAPTCHA: {e}")
        return False

def click_sort_by_date(driver):
    """Клик по сортировке отзывов по дате/новизне"""
    print("📅 Ищем кнопку сортировки...")
    
    # Селекторы для кнопки "By default" / "По умолчанию" на основе диагностики
    default_button_selectors = [
        # Найденный в диагностике - приоритет
        "div.rating-ranking-view[role='button']",
        ".rating-ranking-view",
        
        # Текстовые селекторы
        "//div[@role='button' and contains(text(), 'By default')]",
        "//div[contains(@class, 'rating-ranking-view')]",
        "//span[contains(text(), 'By default')]",
        "//div[contains(text(), 'By default')]",
        "//button[contains(text(), 'By default')]",
        "//button[contains(text(), 'По умолчанию')]",
        "//span[contains(text(), 'По умолчанию')]",
        "//div[contains(text(), 'По умолчанию')]",
        "//a[contains(text(), 'By default')]",
        "//a[contains(text(), 'По умолчанию')]",
        
        # Общие селекторы для кнопок сортировки
        "[role='button']",
        "button[data-testid*='sort']",
        "button[class*='sort']",
        "button[class*='filter']",
        ".sort-button",
        ".filter-button",
        ".reviews-sort button"
    ]
    
    # Селекторы для опций "New first" (найдено в диагностике)
    date_option_selectors = [
        # Найденные в диагностике - приоритет
        "//div[@class='rating-ranking-view__popup-line' and contains(text(), 'New first')]",
        ".rating-ranking-view__popup-line",
        
        # Текстовые селекторы для "New first"
        "//div[contains(text(), 'New first')]",
        "//span[contains(text(), 'New first')]",
        "//button[contains(text(), 'New first')]",
        
        # Альтернативные варианты
        "//div[contains(text(), 'By date')]",
        "//div[contains(text(), 'По новизне')]",
        "//div[contains(text(), 'По дате')]",
        "//option[contains(text(), 'By date')]",
        "//option[contains(text(), 'По новизне')]",
        "//li[contains(text(), 'By date')]",
        "//li[contains(text(), 'По новизне')]"
    ]
    
    clicked_default = False
    
    # Шаг 1: Ищем и кликаем кнопку "By default" / "По умолчанию"
    print("🔍 Ищем кнопку 'By default' или 'По умолчанию'...")
    
    for selector in default_button_selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    element_text = element.text.strip()
                    print(f"✅ Найден элемент: {selector}")
                    print(f"   📱 Текст: '{element_text}'")
                    
                    # Проверяем, содержит ли текст нужные слова
                    if any(word in element_text.lower() for word in ['default', 'умолчанию', 'sort', 'сортир']):
                        print("🎯 Подходящий элемент найден!")
                        
                        # Прокручиваем к элементу
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                        time.sleep(1)
                        
                        # Кликаем
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            print("🖱️ JavaScript клик по кнопке сортировки выполнен!")
                        except:
                            element.click()
                            print("🖱️ Обычный клик по кнопке сортировки выполнен!")
                        
                        clicked_default = True
                        time.sleep(2)  # Ждем появления меню
                        break
                    
            if clicked_default:
                break
                
        except Exception as e:
            print(f"❌ Ошибка с селектором {selector}: {e}")
            continue
    
    if not clicked_default:
        print("❓ Кнопка 'By default' или 'По умолчанию' не найдена")
        return False
    
    # Шаг 2: Ищем и кликаем опцию "New first"
    print("📋 Ищем опцию 'New first' в выпадающем меню...")
    
    for selector in date_option_selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    element_text = element.text.strip()
                    print(f"✅ Найдена опция: {selector}")
                    print(f"   📱 Текст опции: '{element_text}'")
                    
                    # Проверяем, содержит ли текст "New first" или другие варианты сортировки по времени
                    if any(word in element_text.lower() for word in ['new first', 'date', 'новизне', 'дате', 'newest']):
                        print("🎯 Подходящая опция найдена!")
                        
                        # Прокручиваем и кликаем
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                        time.sleep(1)
                        
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            print("🖱️ JavaScript клик по опции выполнен!")
                        except:
                            element.click()
                            print("🖱️ Обычный клик по опции выполнен!")
                        
                        time.sleep(2)
                        print("📅 Сортировка 'New first' применена!")
                        return True
                        
        except Exception as e:
            print(f"❌ Ошибка с селектором опции {selector}: {e}")
            continue
    
    print("❓ Опция 'New first' не найдена в меню")
    return False

def extract_reviews(driver, max_reviews=10):
    """Извлечение текстов отзывов со страницы"""
    print(f"\n📝 Извлекаем последние {max_reviews} отзывов...")
    
    # Селекторы для поиска отзывов
    review_selectors = [
        # Основные селекторы для текста отзывов
        ".business-review-view__body-text",
        ".business-review-view__text",
        ".review-text",
        ".spoiler-view__text-container",
        "[class*='review'][class*='text']",
        "[class*='business-review'][class*='text']"
    ]
    
    reviews = []
    
    for selector in review_selectors:
        try:
            print(f"🔍 Ищем отзывы по селектору: {selector}")
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if element.is_displayed() and element.text.strip():
                    review_text = element.text.strip()
                    
                    # Фильтруем слишком короткие тексты (вероятно не отзывы)
                    if len(review_text) > 20 and review_text not in reviews:
                        reviews.append(review_text)
                        print(f"✅ Найден отзыв #{len(reviews)}: {review_text[:50]}...")
                        
                        # Останавливаемся, если достигли нужного количества
                        if len(reviews) >= max_reviews:
                            break
            
            # Если нашли достаточно отзывов, прерываем поиск
            if len(reviews) >= max_reviews:
                break
                
        except Exception as e:
            print(f"❌ Ошибка с селектором {selector}: {e}")
            continue
    
    print(f"📊 Всего найдено отзывов: {len(reviews)}")
    return reviews[:max_reviews]

def expand_review_text(driver, container):
    """Раскрытие полного текста отзыва если он свернут"""
    # Селекторы для кнопок раскрытия текста
    expand_button_selectors = [
        # НАЙДЕННЫЙ РАБОЧИЙ СЕЛЕКТОР!
        ".business-review-view__expand",
        "span.business-review-view__expand",
        
        # Дополнительные селекторы
        ".business-review-view__show-more",
        ".spoiler-view__button",
        ".show-more-button",
        ".expand-button",
        ".read-more",
        "[class*='show-more']",
        "[class*='expand']",
        "[class*='spoiler'][class*='button']",
        "button[class*='more']",
        "span[class*='more']",
        
        # Текстовые селекторы
        "//span[contains(text(), 'more')]",
        "//span[contains(text(), 'Show more')]",
        "//span[contains(text(), 'Read more')]", 
        "//span[contains(text(), 'Показать полностью')]",
        "//span[contains(text(), 'Читать далее')]",
        "//button[contains(text(), 'Show more')]",
        "//button[contains(text(), 'Показать полностью')]"
    ]
    
    # Получаем изначальный текст контейнера
    initial_text = container.text
    initial_length = len(initial_text)
    
    for selector in expand_button_selectors:
        try:
            if selector.startswith("//"):
                expand_buttons = container.find_elements(By.XPATH, selector)
            else:
                expand_buttons = container.find_elements(By.CSS_SELECTOR, selector)
            
            for button in expand_buttons:
                if button.is_displayed() and button.is_enabled():
                    try:
                        # Проверяем, не относится ли кнопка к официальному ответу
                        try:
                            # Ищем ближайший родительский элемент кнопки
                            button_parent = button.find_element(By.XPATH, "./ancestor::*[1]")
                            parent_text = button_parent.text.lower()
                            button_text = button.text.lower()
                            
                            # Пропускаем только если кнопка непосредственно относится к официальному ответу
                            if any(phrase in parent_text for phrase in [
                                'show business', 'business response', 'official response'
                            ]) or any(phrase in button_text for phrase in [
                                'show business', 'business response'
                            ]):
                                continue  # Тихо пропускаем кнопки официальных ответов
                        except:
                            pass  # Если не можем определить контекст, продолжаем
                        
                        # Прокручиваем к кнопке
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                        time.sleep(0.5)
                        
                        # Кликаем по кнопке раскрытия
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)  # Ждем загрузки полного текста
                        
                        # Проверяем, изменился ли текст
                        new_text = container.text
                        new_length = len(new_text)
                        
                        if new_length > initial_length:
                            increase = new_length - initial_length
                            print(f"📖 Отзыв действительно раскрыт! Текст увеличился на {increase} символов")
                            return True
                        else:
                            # Если текст не изменился, продолжаем поиск других кнопок
                            continue
                            
                    except Exception as e:
                        continue
        except:
            continue
    
    return False

def expand_all_reviews_with_date_check(driver, max_days_back=None, checkpoint_info=None):
    """🌊 ПЛАВНОЕ раскрытие отзывов с проверкой дат и checkpoint - останавливается при достижении старой даты или checkpoint"""
    from datetime import datetime, timedelta
    
    print("🌊 Плавное раскрытие отзывов с проверкой дат и checkpoint...")
    start_time = time.time()
    
    # Вычисляем дату отсечения, если указана
    cutoff_date = None
    if max_days_back:
        cutoff_date = datetime.now() - timedelta(days=max_days_back)
        print(f"📅 Остановка при достижении даты старше: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Информация о checkpoint
    checkpoint_author = None
    checkpoint_date = None
    if checkpoint_info and checkpoint_info.get('has_checkpoint'):
        checkpoint_author = checkpoint_info.get('last_author')
        checkpoint_date = checkpoint_info.get('last_date')
        if checkpoint_author and checkpoint_date:
            print(f"🎯 Checkpoint: {checkpoint_author} ({checkpoint_date})")
    
    stats = {
        'total_reviews': 0,
        'reviews_expanded': 0,
        'reviews_processed': 0,
        'date_limit_reached': False,
        'checkpoint_reached': False
    }
    
    try:
        # Получаем все отзывы без предварительного скроллинга
        reviews = driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
        stats['total_reviews'] = len(reviews)
        
        if stats['total_reviews'] == 0:
            print("⚠️ Отзывы не найдены")
            return 0
        
        print(f"📝 Найдено отзывов: {stats['total_reviews']}")
        
        # Плавная обработка всех отзывов с естественным скроллингом и проверкой дат
        for i, review in enumerate(reviews):
            try:
                # 🎯 ПРОВЕРКА ДАТЫ ОТЗЫВА И CHECKPOINT ПЕРЕД ОБРАБОТКОЙ
                review_date_str = get_review_date_quickly(review)
                
                # Проверяем checkpoint
                if checkpoint_date and review_date_str:
                    try:
                        # Парсим дату отзыва в стандартный формат (если ещё не распарсена)
                        import re
                        if re.match(r'^\d{4}-\d{2}-\d{2}$', review_date_str):
                            # Дата уже в формате YYYY-MM-DD
                            parsed_review_date = review_date_str
                        else:
                            # Парсим дату
                            parsed_review_date = parse_review_date(review_date_str)
                        
                        # Преобразуем checkpoint_date в строку если это объект date
                        checkpoint_date_str = str(checkpoint_date) if checkpoint_date else None
                        
                        # ОТЛАДКА: выводим информацию о проверке
                        print(f"🔍 Отзыв #{i+1}: дата '{parsed_review_date}' vs checkpoint '{checkpoint_date_str}'")
                        
                        # Сравниваем с checkpoint датой
                        if parsed_review_date == checkpoint_date_str:
                            print(f"🎯 Достигнут checkpoint по дате! Дата отзыва: {parsed_review_date}")
                            print(f"🛑 Остановка раскрытия отзывов на позиции #{i+1}")
                            stats['checkpoint_reached'] = True
                            break
                        
                        # Если дата отзыва старше checkpoint даты - тоже останавливаемся
                        if parsed_review_date and checkpoint_date_str and parsed_review_date < checkpoint_date_str:
                            print(f"🎯 Достигнута дата старше checkpoint! Дата отзыва: {parsed_review_date} старше checkpoint: {checkpoint_date_str}")
                            print(f"🛑 Остановка раскрытия отзывов на позиции #{i+1}")
                            stats['checkpoint_reached'] = True
                            break
                            
                    except Exception as e:
                        print(f"❌ Ошибка проверки checkpoint для отзыва #{i+1}: {e}")
                        pass  # Если не удалось распарсить дату, продолжаем
                
                # Проверяем дату отсечения (только если нет checkpoint или он не найден)
                if cutoff_date and review_date_str:
                    try:
                        review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
                        
                        # Если отзыв старше целевой даты - останавливаем обработку
                        if review_date < cutoff_date:
                            print(f"🎯 Достигнута дата отсечения! Отзыв от {review_date_str} старше чем {cutoff_date.strftime('%Y-%m-%d')}")
                            print(f"🛑 Остановка обработки отзывов на позиции #{i+1}")
                            stats['date_limit_reached'] = True
                            break
                            
                    except ValueError:
                        pass  # Если не удалось распарсить дату, продолжаем
                
                # 🌊 ПЛАВНАЯ прокрутка к отзыву с имитацией человеческого поведения
                
                # Сначала плавно прокручиваем к отзыву
                driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                """, review)
                
                # Естественная пауза для наблюдения за прокруткой
                import random
                scroll_pause = random.uniform(0.8, 1.5)  # Случайная пауза 0.8-1.5 сек
                time.sleep(scroll_pause)
                
                # Небольшая дополнительная прокрутка для имитации точной настройки позиции
                try:
                    driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-20, 20))
                    time.sleep(random.uniform(0.2, 0.4))
                except:
                    pass
                
                # Ищем кнопку раскрытия
                try:
                    button = review.find_element(By.CSS_SELECTOR, ".business-review-view__expand")
                    if button.is_displayed():
                        # ФИЛЬТРАЦИЯ: Проверяем, что это НЕ официальный ответ
                        review_text = review.text.lower()
                        if any(phrase in review_text for phrase in [
                            'business response', 'official response', 'response from business',
                            'ответ от организации', 'официальный ответ', 'ответ компании'
                        ]):
                            continue  # Пропускаем официальные ответы
                        
                        # Запоминаем длину текста до клика
                        text_length_before = len(review.text)
                        
                        # Естественная пауза перед кликом (имитация чтения)
                        reading_pause = random.uniform(0.3, 0.7)
                        time.sleep(reading_pause)
                        
                        # Плавный клик с небольшой задержкой
                        driver.execute_script("arguments[0].click();", button)
                        
                        # Пауза на обработку раскрытия
                        expand_pause = random.uniform(0.5, 1.0)
                        time.sleep(expand_pause)
                        
                        # Проверяем результат
                        text_length_after = len(review.text)
                        if text_length_after > text_length_before:
                            stats['reviews_expanded'] += 1
                        
                except:
                    pass  # Кнопка не найдена или не кликается
                
                stats['reviews_processed'] += 1
                
                # Естественная пауза между отзывами (имитация перехода к следующему)
                if i < len(reviews) - 1:
                    between_reviews_pause = random.uniform(0.4, 0.8)
                    time.sleep(between_reviews_pause)
                
            except Exception as e:
                continue
        
        # Статистика
        total_time = time.time() - start_time
        success_rate = (stats['reviews_expanded'] / stats['reviews_processed'] * 100) if stats['reviews_processed'] > 0 else 0
        
        print(f"✅ Раскрытие завершено за {total_time:.1f}с")
        print(f"📊 Обработано отзывов: {stats['reviews_processed']}/{stats['total_reviews']}")
        print(f"📊 Успешно раскрыто: {stats['reviews_expanded']}/{stats['reviews_processed']} ({success_rate:.1f}%)")
        
        if stats['checkpoint_reached']:
            print(f"🎯 Остановлено по достижении checkpoint")
        elif stats['date_limit_reached']:
            print(f"🎯 Остановлено по достижении даты отсечения")
        
        return stats['reviews_expanded']
        
    except Exception as e:
        print(f"❌ Ошибка плавного раскрытия с проверкой дат: {e}")
        return 0

def expand_all_reviews(driver):
    """🌊 ПЛАВНОЕ раскрытие всех свернутых отзывов с имитацией человеческого поведения"""
    print("🌊 Плавное раскрытие всех отзывов...")
    start_time = time.time()
    
    stats = {
        'total_reviews': 0,
        'reviews_expanded': 0,
        'reviews_processed': 0
    }
    
    try:
        # Получаем все отзывы без предварительного скроллинга
        reviews = driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
        stats['total_reviews'] = len(reviews)
        
        if stats['total_reviews'] == 0:
            print("⚠️ Отзывы не найдены")
            return 0
        
        print(f"📝 Найдено отзывов: {stats['total_reviews']}")
        
        # Плавная обработка всех отзывов с естественным скроллингом
        for i, review in enumerate(reviews):
            try:
                # 🌊 ПЛАВНАЯ прокрутка к отзыву с имитацией человеческого поведения
                
                # Сначала плавно прокручиваем к отзыву
                driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                """, review)
                
                # Естественная пауза для наблюдения за прокруткой
                import random
                scroll_pause = random.uniform(0.8, 1.5)  # Случайная пауза 0.8-1.5 сек
                time.sleep(scroll_pause)
                
                # Небольшая дополнительная прокрутка для имитации точной настройки позиции
                try:
                    driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-20, 20))
                    time.sleep(random.uniform(0.2, 0.4))
                except:
                    pass
                
                # Ищем кнопку раскрытия
                try:
                    button = review.find_element(By.CSS_SELECTOR, ".business-review-view__expand")
                    if button.is_displayed():
                        # ФИЛЬТРАЦИЯ: Проверяем, что это НЕ официальный ответ
                        review_text = review.text.lower()
                        if any(phrase in review_text for phrase in [
                            'business response', 'official response', 'response from business',
                            'ответ от организации', 'официальный ответ', 'ответ компании'
                        ]):
                            continue  # Пропускаем официальные ответы
                        
                        # Запоминаем длину текста до клика
                        text_length_before = len(review.text)
                        
                        # Естественная пауза перед кликом (имитация чтения)
                        reading_pause = random.uniform(0.3, 0.7)
                        time.sleep(reading_pause)
                        
                        # Плавный клик с небольшой задержкой
                        driver.execute_script("arguments[0].click();", button)
                        
                        # Пауза на обработку раскрытия
                        expand_pause = random.uniform(0.5, 1.0)
                        time.sleep(expand_pause)
                        
                        # Проверяем результат
                        text_length_after = len(review.text)
                        if text_length_after > text_length_before:
                            stats['reviews_expanded'] += 1
                        
                except:
                    pass  # Кнопка не найдена или не кликается
                
                stats['reviews_processed'] += 1
                
                # Естественная пауза между отзывами (имитация перехода к следующему)
                if i < len(reviews) - 1:
                    between_reviews_pause = random.uniform(0.4, 0.8)
                    time.sleep(between_reviews_pause)
                
            except Exception as e:
                continue
        
        # Статистика
        total_time = time.time() - start_time
        success_rate = (stats['reviews_expanded'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0
        
        print(f"✅ Раскрытие завершено за {total_time:.1f}с")
        print(f"📊 Успешно раскрыто: {stats['reviews_expanded']}/{stats['total_reviews']} ({success_rate:.1f}%)")
        
        return stats['reviews_expanded']
        
    except Exception as e:
        print(f"❌ Ошибка плавного раскрытия: {e}")
        return 0

def extract_review_details(driver, max_reviews=10):
    """Извлечение детальной информации об отзывах"""
    print(f"\n📝 Извлекаем детальную информацию о последних {max_reviews} отзывах...")
    
    # Селекторы для контейнеров отзывов
    review_container_selectors = [
        ".business-review-view",
        ".review-item",
        "[class*='business-review-view']",
        "[class*='review-view']"
    ]
    
    reviews_data = []
    
    for selector in review_container_selectors:
        try:
            print(f"🔍 Ищем контейнеры отзывов: {selector}")
            containers = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for container in containers:
                if container.is_displayed():
                    try:
                        # ОПТИМИЗАЦИЯ: Убираем повторное раскрытие - уже сделано быстрой функцией
                        # expand_review_text(driver, container)  # Закомментировано для ускорения
                        
                        # Извлекаем различные части отзыва
                        review_data = {}
                        
                        # Текст отзыва - ищем максимально полный текст
                        text_selectors = [
                            # Основные селекторы
                            ".business-review-view__body-text",
                            ".spoiler-view__text-container", 
                            ".business-review-view__body",
                            ".review-text",
                            
                            # Дополнительные селекторы для полного текста
                            "*[class*='text']:not([class*='_collapsed'])",
                            "[class*='spoiler'][class*='text']:not([class*='_collapsed'])",
                            "[class*='review'][class*='text']",
                            "[class*='body'][class*='text']"
                        ]
                        
                        longest_text = ""
                        for text_sel in text_selectors:
                            try:
                                text_elems = container.find_elements(By.CSS_SELECTOR, text_sel)
                                for text_elem in text_elems:
                                    if text_elem and text_elem.text.strip():
                                        current_text = text_elem.text.strip()
                                        # Берем самый длинный текст
                                        if len(current_text) > len(longest_text):
                                            longest_text = current_text
                            except:
                                continue
                        
                        # Если ничего не найдено, берем весь текст контейнера
                        if not longest_text:
                            try:
                                full_text = container.text.strip()
                                # Извлекаем только основной текст отзыва, убирая метаданные
                                lines = full_text.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    # Ищем строки с реальным текстом отзыва (длинные, не метаданные)
                                    if len(line) > 50 and not any(word in line.lower() for word in 
                                        ['level', 'expert', 'subscribe', 'show', 'response', 'january', 'february', 'march', 'april', 'may', 'june']):
                                        if len(line) > len(longest_text):
                                            longest_text = line
                            except:
                                pass
                        
                        if longest_text:
                            review_data['text'] = longest_text
                        
                        # Имя автора - ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ
                        author_selectors = [
                            # Самый надежный селектор (найден в отладке)
                            ".business-review-view__author-name",
                            # Дополнительные селекторы
                            ".business-review-view__link",
                            ".review-author",
                            "[class*='author-name']",
                            "[class*='user'][class*='link']",
                            "a[class*='link']"
                        ]
                        
                        for author_sel in author_selectors:
                            try:
                                author_elem = container.find_element(By.CSS_SELECTOR, author_sel)
                                if author_elem and author_elem.text.strip():
                                    author_text = author_elem.text.strip()
                                    # Фильтруем лишние тексты
                                    if (len(author_text) > 2 and len(author_text) < 50 and
                                        not any(word in author_text.lower() for word in 
                                               ['level', 'expert', 'subscribe', 'local', 'response', 'show'])):
                                        review_data['author'] = author_text
                                        break
                            except:
                                continue
                        
                        # Рейтинг (звезды) - ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ
                        rating_selectors = [
                            # Самый надежный селектор (найден в отладке)
                            ".business-rating-badge-view__stars",
                            # Дополнительные селекторы
                            ".business-rating-badge-view__rating", 
                            ".rating",
                            "[class*='rating'][class*='badge']",
                            "[class*='stars']",
                            "[aria-label*='Rating']"
                        ]
                        
                        for rating_sel in rating_selectors:
                            try:
                                rating_elem = container.find_element(By.CSS_SELECTOR, rating_sel)
                                
                                # Проверяем aria-label для рейтинга
                                aria_label = rating_elem.get_attribute('aria-label') or ''
                                if 'rating' in aria_label.lower() and 'out of' in aria_label.lower():
                                    # Извлекаем число из "Rating 5 Out of 5"
                                    import re
                                    match = re.search(r'rating\s+(\d+(?:\.\d+)?)\s+out\s+of', aria_label, re.IGNORECASE)
                                    if match:
                                        review_data['rating'] = match.group(1)
                                        break
                                
                                # Проверяем текст элемента
                                if rating_elem.text.strip():
                                    rating_text = rating_elem.text.strip()
                                    # Фильтруем только числовые рейтинги
                                    if re.match(r'^[1-5](\.[0-9])?$', rating_text):
                                        review_data['rating'] = rating_text
                                        break
                            except:
                                continue
                        
                        # Дата отзыва
                        date_selectors = [
                            ".business-review-view__date",
                            ".review-date",
                            "[class*='date']",
                            "time"
                        ]
                        
                        for date_sel in date_selectors:
                            try:
                                date_elem = container.find_element(By.CSS_SELECTOR, date_sel)
                                if date_elem and date_elem.text.strip():
                                    review_data['date'] = date_elem.text.strip()
                                    break
                            except:
                                continue
                        
                        # Добавляем отзыв, если есть текст
                        if 'text' in review_data and len(review_data['text']) > 20:
                            reviews_data.append(review_data)
                            print(f"✅ Найден отзыв #{len(reviews_data)}: {review_data.get('author', 'Неизвестно')} - {review_data['text'][:50]}...")
                            
                            # Останавливаемся, если достигли нужного количества
                            if len(reviews_data) >= max_reviews:
                                break
                                
                    except Exception as e:
                        continue
            
            # Если нашли достаточно отзывов, прерываем поиск
            if len(reviews_data) >= max_reviews:
                break
                
        except Exception as e:
            print(f"❌ Ошибка с селектором контейнера {selector}: {e}")
            continue
    
    print(f"📊 Всего найдено детальных отзывов: {len(reviews_data)}")
    return reviews_data[:max_reviews]

def extract_reviews_until_checkpoint(driver, checkpoint_info: dict, card_id: str, max_reviews_limit: int = 100):
    """Извлечение отзывов до checkpoint (инкрементальный парсинг) - БЕЗ ДОПОЛНИТЕЛЬНЫХ ПРОКРУТОК"""
    
    print(f"🔄 Инкрементальный парсинг до checkpoint...")
    print(f"🎯 Checkpoint: {checkpoint_info.get('author', 'N/A')} - {checkpoint_info.get('text_preview', 'N/A')}")
    
    reviews_data = []
    processed_review_ids = set()
    checkpoint_reached = False
    
    print(f"🔄 Обрабатываем все найденные отзывы до checkpoint...")
    
    # Получаем все контейнеры отзывов (только пользовательские отзывы, НЕ официальные ответы)
    all_containers = driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
    containers = []
    for container in all_containers:
        try:
            container_text = container.text.lower()
            # Фильтруем официальные ответы
            if not any(phrase in container_text for phrase in [
                'business response', 'official response', 'response from business',
                'ответ от организации', 'официальный ответ', 'ответ компании'
            ]):
                containers.append(container)
        except:
            containers.append(container)  # В случае ошибки добавляем контейнер
    
    if not containers:
        print(f"⚠️ Отзывы не найдены на странице")
        return reviews_data
    
    duplicate_count = 0
    
    # Обрабатываем ВСЕ контейнеры за один проход до достижения checkpoint
    for i, container in enumerate(containers):
        if len(reviews_data) >= max_reviews_limit or checkpoint_reached:
            break
            
        if not container.is_displayed():
            continue
            
        try:
            # Создаем уникальный ID для отзыва
            try:
                author_elem = container.find_element(By.CSS_SELECTOR, ".business-review-view__author")
                author = author_elem.text.strip() if author_elem else "unknown"
                
                date_elem = container.find_element(By.CSS_SELECTOR, ".business-review-view__date")
                date = date_elem.text.strip() if date_elem else "unknown"
                
                text_preview = container.text[:50].replace('\n', ' ').strip()
                review_id = f"{author}_{date}_{hash(text_preview)}"
            except:
                container_text = container.text[:100]
                review_id = f"pos_{i}_{hash(container_text)}"
            
            # Проверяем дубликаты
            if review_id in processed_review_ids:
                duplicate_count += 1
                continue
            
            # Полностью обрабатываем отзыв
            review_data = extract_single_review_data(driver, container)
            
            if review_data and 'text' in review_data and review_data['text'].strip():
                processed_review_ids.add(review_id)
                
                # Проверяем checkpoint ПЕРЕД добавлением отзыва
                if should_stop_parsing(checkpoint_info, review_data, card_id):
                    print(f"🎯 Достигнут checkpoint на отзыве #{i+1}")
                    print(f"📊 Найдено новых отзывов: {len(reviews_data)}")
                    checkpoint_reached = True
                    break
                
                # Добавляем новый отзыв
                reviews_data.append(review_data)
                print(f"✅ Новый отзыв #{len(reviews_data)}: {review_data.get('author', 'Неизвестно')} - {review_data['text'][:50]}...")
            else:
                processed_review_ids.add(review_id)
                
        except Exception as e:
            continue
    
    # Выводим статистику
    if duplicate_count > 0:
        print(f"🔄 Пропущено дубликатов: {duplicate_count}")
    
    print(f"📊 Инкрементальный парсинг завершен:")
    print(f"   ✅ Собрано отзывов: {len(reviews_data)}")
    print(f"   🎯 Обработано контейнеров: {len(containers)}")
    print(f"   📝 Уникальных элементов: {len(processed_review_ids)}")
    print(f"   🏁 Checkpoint достигнут: {'Да' if checkpoint_reached else 'Нет'}")
    
    return reviews_data

def extract_reviews_with_time_limit(driver, max_days_back: int, max_reviews_limit: int = 100):
    """Извлечение отзывов с ограничением по времени (первичный парсинг) - БЕЗ ДОПОЛНИТЕЛЬНЫХ ПРОКРУТОК"""
    from datetime import datetime, timedelta
    
    print(f"🆕 Первичный парсинг за последние {max_days_back} дней...")
    
    # Вычисляем дату отсечения
    cutoff_date = datetime.now() - timedelta(days=max_days_back)
    print(f"📅 Парсим отзывы новее: {cutoff_date.strftime('%Y-%m-%d')}")
    
    reviews_data = []
    processed_review_ids = set()
    
    print(f"🔄 Обрабатываем все найденные отзывы...")
    
    # Получаем все контейнеры отзывов (только пользовательские отзывы, НЕ официальные ответы)
    all_containers = driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
    containers = []
    for container in all_containers:
        try:
            container_text = container.text.lower()
            # Фильтруем официальные ответы
            if not any(phrase in container_text for phrase in [
                'business response', 'official response', 'response from business',
                'ответ от организации', 'официальный ответ', 'ответ компании'
            ]):
                containers.append(container)
        except:
            containers.append(container)  # В случае ошибки добавляем контейнер
    
    if not containers:
        print(f"⚠️ Отзывы не найдены на странице")
        return reviews_data
    
    old_reviews_count = 0
    duplicate_count = 0
    
    # Обрабатываем ВСЕ контейнеры за один проход
    for i, container in enumerate(containers):
        if len(reviews_data) >= max_reviews_limit:
            break
            
        if not container.is_displayed():
            continue
            
        try:
            # Создаем уникальный ID для отзыва
            try:
                author_elem = container.find_element(By.CSS_SELECTOR, ".business-review-view__author")
                author = author_elem.text.strip() if author_elem else "unknown"
                
                date_elem = container.find_element(By.CSS_SELECTOR, ".business-review-view__date")
                date = date_elem.text.strip() if date_elem else "unknown"
                
                text_preview = container.text[:50].replace('\n', ' ').strip()
                review_id = f"{author}_{date}_{hash(text_preview)}"
            except:
                container_text = container.text[:100]
                review_id = f"pos_{i}_{hash(container_text)}"
            
            # Проверяем дубликаты
            if review_id in processed_review_ids:
                duplicate_count += 1
                continue
            
            # Быстро проверяем дату
            quick_date = get_review_date_quickly(container)
            if quick_date:
                try:
                    review_date = datetime.strptime(quick_date, '%Y-%m-%d')
                    
                    # Если отзыв старый - пропускаем
                    if review_date < cutoff_date:
                        old_reviews_count += 1
                        processed_review_ids.add(review_id)
                        continue
                        
                except ValueError:
                    continue
            
            # Полностью обрабатываем подходящий отзыв
            review_data = extract_single_review_data(driver, container)
            
            if review_data and 'text' in review_data and review_data['text'].strip():
                reviews_data.append(review_data)
                processed_review_ids.add(review_id)
                print(f"✅ Отзыв #{len(reviews_data)}: {review_data.get('author', 'Неизвестно')} ({review_data.get('date', 'Без даты')}) - {review_data['text'][:50]}...")
            else:
                processed_review_ids.add(review_id)
                
        except Exception as e:
            continue
    
    # Выводим статистику
    if duplicate_count > 0:
        print(f"🔄 Пропущено дубликатов: {duplicate_count}")
    if old_reviews_count > 0:
        print(f"⏰ Пропущено старых отзывов: {old_reviews_count}")
    
    print(f"📊 Первичный парсинг завершен:")
    print(f"   ✅ Собрано отзывов: {len(reviews_data)}")
    print(f"   🎯 Обработано контейнеров: {len(containers)}")
    print(f"   📝 Уникальных элементов: {len(processed_review_ids)}")
    
    return reviews_data

def scroll_page(driver):
    """Плавная видимая прокрутка страницы для загрузки новых отзывов"""
    try:
        print("🔽 Начинаем плавную прокрутку...")
        
        # Ищем скроллируемый контейнер (найден в диагностике)
        scroll_container = None
        container_selectors = [
            ".scroll__container",
            ".business-reviews-view",
            ".business-reviews-card-view"
        ]
        
        for selector in container_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    container = elements[0]
                    # Проверяем, что контейнер действительно скроллируемый
                    scroll_height = driver.execute_script("return arguments[0].scrollHeight", container)
                    client_height = driver.execute_script("return arguments[0].clientHeight", container)
                    
                    if scroll_height > client_height:
                        scroll_container = container
                        print(f"✅ Найден скроллируемый контейнер: {selector}")
                        print(f"   scrollHeight: {scroll_height}px, clientHeight: {client_height}px")
                        break
            except Exception as e:
                continue
        
        if scroll_container:
            # Скроллим внутренний контейнер
            current_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_container)
            max_scroll = driver.execute_script("return arguments[0].scrollHeight - arguments[0].clientHeight", scroll_container)
            
            print(f"📏 Текущий скролл контейнера: {current_scroll}, максимальный: {max_scroll}")
            
            # Плавная прокрутка по частям
            scroll_step = 300  # Прокручиваем по 300px за раз
            target_scroll = min(current_scroll + 1500, max_scroll)  # Прокручиваем на ~1500px или до конца
            
            while current_scroll < target_scroll:
                next_scroll = min(current_scroll + scroll_step, target_scroll)
                
                # Плавно прокручиваем контейнер
                driver.execute_script(f"arguments[0].scrollTop = {next_scroll}", scroll_container)
                
                print(f"📜 Прокрутка контейнера до позиции: {next_scroll}")
                time.sleep(0.8)  # Пауза для наблюдения и подгрузки контента
                
                current_scroll = next_scroll
            
            # Финальная прокрутка до самого низа для подгрузки всего контента
            print("⬇️ Финальная прокрутка контейнера до конца...")
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(2)
            
            # Небольшая прокрутка вверх для активации lazy loading
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 200", scroll_container)
            time.sleep(1)
            
            final_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_container)
            print(f"✅ Прокрутка контейнера завершена. Финальная позиция: {final_scroll}")
            
        else:
            # Fallback: обычный скролл окна (если контейнер не найден)
            print("⚠️ Скроллируемый контейнер не найден, используем обычный скролл")
            current_position = driver.execute_script("return window.pageYOffset;")
            page_height = driver.execute_script("return document.body.scrollHeight;")
            window_height = driver.execute_script("return window.innerHeight;")
            
            print(f"📏 Текущая позиция: {current_position}, высота страницы: {page_height}")
            
            # Плавная прокрутка по частям
            scroll_step = 300  # Прокручиваем по 300px за раз
            target_position = min(current_position + 1500, page_height - window_height)
            
            while current_position < target_position:
                next_position = min(current_position + scroll_step, target_position)
                
                driver.execute_script(f"window.scrollTo({{top: {next_position}, behavior: 'smooth'}});")
                
                print(f"📜 Прокрутка до позиции: {next_position}")
                time.sleep(0.8)
                
                current_position = next_position
            
            # Финальная прокрутка до самого низа
            print("⬇️ Финальная прокрутка до конца страницы...")
            driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
            time.sleep(2)
            
            # Небольшая прокрутка вверх для активации lazy loading
            driver.execute_script("window.scrollBy({top: -200, behavior: 'smooth'});")
            time.sleep(1)
            
            final_position = driver.execute_script("return window.pageYOffset;")
            print(f"✅ Прокрутка завершена. Финальная позиция: {final_position}")
        
    except Exception as e:
        print(f"⚠️ Ошибка прокрутки: {e}")

def get_review_date_quickly(container):
    """Быстро получить дату отзыва без полной обработки"""
    try:
        # Селекторы только для даты
        date_selectors = [
            ".business-review-view__date",
            ".review-date", 
            "[class*='date']",
            "time"
        ]
        
        for date_sel in date_selectors:
            try:
                date_elem = container.find_element(By.CSS_SELECTOR, date_sel)
                if date_elem and date_elem.text.strip():
                    date_text = date_elem.text.strip()
                    # Быстро парсим дату
                    parsed_date = parse_review_date(date_text)
                    if parsed_date:
                        return parsed_date
            except:
                continue
                
        return None
        
    except Exception as e:
        return None

def expand_review_text(driver, container):
    """Раскрытие текста отзыва в конкретном контейнере"""
    try:
        # Ищем кнопку "more" в данном контейнере
        expand_selectors = [
            ".business-review-view__expand",
            ".spoiler-view__expand",
            "[class*='expand']",
            "span:contains('more')",
            "button:contains('more')"
        ]
        
        for selector in expand_selectors:
            try:
                expand_button = container.find_element(By.CSS_SELECTOR, selector)
                if expand_button and expand_button.is_displayed():
                    # Получаем текст до клика
                    text_before = container.text
                    
                    # Кликаем
                    driver.execute_script("arguments[0].click();", expand_button)
                    time.sleep(0.5)  # Короткая пауза
                    
                    # Проверяем, изменился ли текст
                    text_after = container.text
                    if len(text_after) > len(text_before):
                        return True
                        
            except:
                continue
                
        return False
        
    except Exception as e:
        return False

def extract_single_review_data(driver, container):
    """Извлечение данных одного отзыва из контейнера"""
    try:
        # ОПТИМИЗАЦИЯ: Убираем повторное раскрытие - уже сделано быстрой функцией
        # expand_review_text(driver, container)  # Закомментировано для ускорения
        
        # Извлекаем различные части отзыва
        review_data = {}
        
        # Текст отзыва - ищем максимально полный текст
        text_selectors = [
            # Основные селекторы
            ".business-review-view__body-text",
            ".spoiler-view__text-container", 
            ".business-review-view__body",
            ".review-text",
            
            # Дополнительные селекторы для полного текста
            "*[class*='text']:not([class*='_collapsed'])",
            "[class*='spoiler'][class*='text']:not([class*='_collapsed'])",
            "[class*='review'][class*='text']",
            "[class*='body'][class*='text']"
        ]
        
        longest_text = ""
        for text_sel in text_selectors:
            try:
                text_elems = container.find_elements(By.CSS_SELECTOR, text_sel)
                for text_elem in text_elems:
                    if text_elem and text_elem.text.strip():
                        current_text = text_elem.text.strip()
                        # Берем самый длинный текст
                        if len(current_text) > len(longest_text):
                            longest_text = current_text
            except:
                continue
        
        # Если ничего не найдено, берем весь текст контейнера
        if not longest_text:
            try:
                full_text = container.text.strip()
                # Извлекаем только основной текст отзыва, убирая метаданные
                lines = full_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Ищем строки с реальным текстом отзыва (длинные, не метаданные)
                    if len(line) > 50 and not any(word in line.lower() for word in 
                        ['level', 'expert', 'subscribe', 'show', 'response', 'january', 'february', 'march', 'april', 'may', 'june']):
                        if len(line) > len(longest_text):
                            longest_text = line
            except:
                pass
        
        if longest_text:
            review_data['text'] = longest_text
        
        # Имя автора - ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ
        author_selectors = [
            # Самый надежный селектор (найден в отладке)
            ".business-review-view__author-name",
            # Дополнительные селекторы
            ".business-review-view__link",
            ".review-author",
            "[class*='author-name']",
            "[class*='user'][class*='link']",
            "a[class*='link']"
        ]
        
        for author_sel in author_selectors:
            try:
                author_elem = container.find_element(By.CSS_SELECTOR, author_sel)
                if author_elem and author_elem.text.strip():
                    author_text = author_elem.text.strip()
                    # Фильтруем лишние тексты
                    if (len(author_text) > 2 and len(author_text) < 50 and
                        not any(word in author_text.lower() for word in 
                               ['level', 'expert', 'subscribe', 'local', 'response', 'show'])):
                        review_data['author'] = author_text
                        break
            except:
                continue
        
        # Рейтинг (звезды) - ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ
        rating_selectors = [
            # Самый надежный селектор (найден в отладке)
            ".business-rating-badge-view__stars",
            # Дополнительные селекторы
            ".business-rating-badge-view__rating", 
            ".rating",
            "[class*='rating'][class*='badge']",
            "[class*='stars']",
            "[aria-label*='Rating']"
        ]
        
        for rating_sel in rating_selectors:
            try:
                rating_elem = container.find_element(By.CSS_SELECTOR, rating_sel)
                
                # Проверяем aria-label для рейтинга
                aria_label = rating_elem.get_attribute('aria-label') or ''
                if 'rating' in aria_label.lower() and 'out of' in aria_label.lower():
                    # Извлекаем число из "Rating 5 Out of 5"
                    import re
                    match = re.search(r'rating\s+(\d+(?:\.\d+)?)\s+out\s+of', aria_label, re.IGNORECASE)
                    if match:
                        review_data['rating'] = match.group(1)
                        break
                
                # Проверяем текст элемента
                if rating_elem.text.strip():
                    rating_text = rating_elem.text.strip()
                    # Фильтруем только числовые рейтинги
                    if re.match(r'^[1-5](\.[0-9])?$', rating_text):
                        review_data['rating'] = rating_text
                        break
            except:
                continue
        
        # Дата отзыва
        date_selectors = [
            ".business-review-view__date",
            ".review-date",
            "[class*='date']",
            "time"
        ]
        
        for date_sel in date_selectors:
            try:
                date_elem = container.find_element(By.CSS_SELECTOR, date_sel)
                if date_elem and date_elem.text.strip():
                    review_data['date'] = date_elem.text.strip()
                    break
            except:
                continue
        
        return review_data if 'text' in review_data else None
        
    except Exception as e:
        return None

def parse_review_date(date_str: str) -> str:
    """Преобразовать дату отзыва в формат YYYY-MM-DD (поддержка русского и английского)"""
    if not date_str:
        return None
    
    try:
        import re
        
        # Словарь месяцев на английском и русском
        months = {
            # Английские месяцы
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12',
            # Сокращенные английские
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'Jun': '06', 'Jul': '07', 'Aug': '08', 'Sep': '09', 
            'Oct': '10', 'Nov': '11', 'Dec': '12',
            # Русские месяцы
            'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
            'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
            'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12',
            # Русские в именительном падеже
            'январь': '01', 'февраль': '02', 'март': '03', 'апрель': '04',
            'май': '05', 'июнь': '06', 'июль': '07', 'август': '08',
            'сентябрь': '09', 'октябрь': '10', 'ноябрь': '11', 'декабрь': '12'
        }
        
        # Нормализуем входную строку
        date_str_clean = date_str.strip()
        
        # ========== ФОРМАТ С ГОДОМ ==========
        # "November 5, 2024", "April 19, 2023", "May 17, 2022"
        pattern_with_year = r'([A-Za-zа-я]+)\s+(\d{1,2}),?\s+(\d{4})'
        match = re.search(pattern_with_year, date_str_clean)
        if match:
            month_name, day, year = match.groups()
            if month_name in months:
                month = months[month_name]
                day = day.zfill(2)
                return f"{year}-{month}-{day}"
        
        # ========== ФОРМАТ БЕЗ ГОДА ==========
        # "February 4", "January 4" - определяем год логично
        if ' ' in date_str_clean:
            parts = date_str_clean.split()
            if len(parts) == 2:
                first_part, second_part = parts
                
                # Вариант 1: "May 28" (месяц день)
                if first_part in months and second_part.isdigit():
                    current_date = datetime.now()
                    month_num = int(months[first_part])
                    day_num = int(second_part)
                    
                    # Если месяц больше текущего, то это прошлый год
                    if month_num > current_date.month:
                        year = current_date.year - 1
                    # Если месяц равен текущему, но день больше текущего, то это прошлый год
                    elif month_num == current_date.month and day_num > current_date.day:
                        year = current_date.year - 1
                    else:
                        year = current_date.year
                    
                    month = months[first_part]
                    day = second_part.zfill(2)
                    return f"{year}-{month}-{day}"
                
                # Вариант 2: "28 мая" (день месяц)
                elif first_part.isdigit() and second_part in months:
                    current_date = datetime.now()
                    month_num = int(months[second_part])
                    day_num = int(first_part)
                    
                    # Если месяц больше текущего, то это прошлый год
                    if month_num > current_date.month:
                        year = current_date.year - 1
                    # Если месяц равен текущему, но день больше текущего, то это прошлый год
                    elif month_num == current_date.month and day_num > current_date.day:
                        year = current_date.year - 1
                    else:
                        year = current_date.year
                    
                    month = months[second_part]
                    day = first_part.zfill(2)
                    return f"{year}-{month}-{day}"
        
        # ========== ДОПОЛНИТЕЛЬНЫЙ ПОИСК ==========
        # Ищем любой месяц в строке
        for month_name, month_num in months.items():
            if month_name.lower() in date_str_clean.lower():
                # Ищем все числа в строке
                numbers = re.findall(r'\d+', date_str_clean)
                if numbers:
                    current_date = datetime.now()
                    year = current_date.year
                    day = numbers[0]
                    
                    # Если есть 4-значное число, это год
                    for num in numbers:
                        if len(num) == 4 and num.isdigit():
                            year = int(num)
                            break
                    else:
                        # Если года нет, определяем логично
                        month_num_int = int(month_num)
                        day_num = int(day) if day.isdigit() else 1
                        
                        # Если месяц больше текущего, то это прошлый год
                        if month_num_int > current_date.month:
                            year = current_date.year - 1
                        # Если месяц равен текущему, но день больше текущего, то это прошлый год
                        elif month_num_int == current_date.month and day_num > current_date.day:
                            year = current_date.year - 1
                    
                    # Берем первое 1-2 значное число как день
                    for num in numbers:
                        if len(num) <= 2 and 1 <= int(num) <= 31:
                            day = num
                            break
                    
                    day = day.zfill(2)
                    return f"{year}-{month_num}-{day}"
        
        print(f"⚠️ Не удалось распарсить дату: '{date_str}'")
        return date_str  # Возвращаем как есть, если не удалось распарсить
        
    except Exception as e:
        print(f"⚠️ Ошибка парсинга даты '{date_str}': {e}")
        return date_str

def parse_rating(rating_str: str) -> float:
    """Преобразовать рейтинг в число"""
    if not rating_str:
        return None
    
    try:
        # Извлекаем первое число из строки
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', rating_str)
        if match:
            return float(match.group(1))
        return None
    except:
        return None

def save_reviews_to_database(reviews_data: list, card_id: str) -> dict:
    """Сохранить отзывы в базу данных с проверкой уникальности"""
    if not DATABASE_AVAILABLE:
        print("⚠️ База данных недоступна - пропускаем сохранение")
        return {"saved": 0, "duplicates": 0, "errors": 0}
    
    if not reviews_data or not card_id:
        print("⚠️ Нет данных для сохранения")
        return {"saved": 0, "duplicates": 0, "errors": 0}
    
    print(f"\n💾 Сохраняем {len(reviews_data)} отзывов в базу данных...")
    
    results = {"saved": 0, "duplicates": 0, "errors": 0}
    
    try:
        with ReviewsDatabase() as db:
            for i, review in enumerate(reviews_data, 1):
                try:
                    # Подготавливаем данные для БД
                    author_name = review.get('author', 'Неизвестный автор')
                    review_text = review.get('text', '')
                    review_date = parse_review_date(review.get('date', ''))
                    rating = parse_rating(review.get('rating', ''))
                    
                    # Проверяем уникальность по алгоритму: card_id + date + author + rating
                    duplicate = db.check_duplicate_review(
                        card_id=card_id,
                        author_name=author_name,
                        review_date=review_date,
                        review_text=review_text,  # Используем текст для дополнительной проверки
                        rating=rating  # Основной критерий уникальности
                    )
                    
                    if duplicate:
                        print(f"⚠️ Отзыв #{i} уже существует (автор: {author_name}, дата: {review_date})")
                        results["duplicates"] += 1
                        continue
                    
                    # Добавляем новый отзыв
                    review_id = db.add_review(
                        card_id=card_id,
                        author_name=author_name,
                        review_text=review_text,
                        review_date=review_date,
                        rating=rating,
                        status='found'
                    )
                    
                    if review_id:
                        print(f"✅ Отзыв #{i} сохранен (ID: {review_id}, автор: {author_name})")
                        results["saved"] += 1
                    else:
                        results["errors"] += 1
                        
                except Exception as e:
                    print(f"❌ Ошибка сохранения отзыва #{i}: {e}")
                    results["errors"] += 1
                    continue
            
            print(f"\n📊 Результаты сохранения:")
            print(f"   ✅ Сохранено новых: {results['saved']}")
            print(f"   ⚠️ Дубликатов пропущено: {results['duplicates']}")
            print(f"   ❌ Ошибок: {results['errors']}")
            
            return results
            
    except Exception as e:
        print(f"❌ Критическая ошибка при работе с БД: {e}")
        results["errors"] = len(reviews_data)
        return results

def print_reviews(reviews_data):
    """Вывод отзывов в консоль"""
    if not reviews_data:
        print("❌ Отзывы не найдены")
        return
    
    print(f"\n📋 ПОСЛЕДНИЕ {len(reviews_data)} ОТЗЫВОВ:")
    print("=" * 80)
    
    for i, review in enumerate(reviews_data, 1):
        print(f"\n📝 ОТЗЫВ #{i}")
        print("-" * 40)
        
        if 'author' in review:
            print(f"👤 Автор: {review['author']}")
        
        if 'rating' in review:
            print(f"⭐ Рейтинг: {review['rating']}")
        
        if 'date' in review:
            print(f"📅 Дата: {review['date']}")
        
        print(f"💬 Текст:")
        print(f"   {review['text']}")
        
        if i < len(reviews_data):
            print()

def get_checkpoint_info(card_id: str) -> dict:
    """Получить информацию о checkpoint для карточки"""
    if not DATABASE_AVAILABLE:
        return {"has_checkpoint": False, "last_date": None, "total_reviews": 0}
    
    try:
        with ReviewsDatabase() as db:
            # Получаем последний отзыв
            latest_review = db.get_latest_review_by_card(card_id)
            
            if latest_review:
                # Получаем общее количество отзывов
                stats = db.get_statistics(card_id)
                total_reviews = stats.get('total_reviews', 0)
                
                print(f"📍 CHECKPOINT найден:")
                print(f"   📅 Последний отзыв: {latest_review['review_date']}")
                print(f"   👤 Автор: {latest_review['author_name']}")
                print(f"   📊 Всего отзывов в БД: {total_reviews}")
                
                return {
                    "has_checkpoint": True,
                    "last_date": latest_review['review_date'],
                    "last_author": latest_review['author_name'],
                    "last_rating": latest_review.get('rating'),
                    "total_reviews": total_reviews
                }
            else:
                print(f"📍 CHECKPOINT не найден - первичный парсинг")
                return {"has_checkpoint": False, "last_date": None, "total_reviews": 0}
                
    except Exception as e:
        print(f"❌ Ошибка получения checkpoint: {e}")
        return {"has_checkpoint": False, "last_date": None, "total_reviews": 0}

def should_stop_parsing(checkpoint_info: dict, review_data: dict, card_id: str) -> bool:
    """Определить, нужно ли остановить парсинг (дошли до checkpoint)"""
    if not checkpoint_info.get("has_checkpoint"):
        return False  # Нет checkpoint - продолжаем
    
    if not DATABASE_AVAILABLE:
        return False
    
    try:
        # Проверяем точное совпадение с последним известным отзывом
        author = review_data.get('author', 'Неизвестный автор')
        date = parse_review_date(review_data.get('date', ''))
        rating = parse_rating(review_data.get('rating', ''))
        
        # Сравниваем с checkpoint
        if (date == str(checkpoint_info.get("last_date")) and
            author == checkpoint_info.get("last_author") and
            rating == checkpoint_info.get("last_rating")):
            
            print(f"🎯 CHECKPOINT достигнут! Найден отзыв:")
            print(f"   👤 Автор: {author}")
            print(f"   📅 Дата: {date}")
            print(f"   ⭐ Рейтинг: {rating}")
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ Ошибка проверки checkpoint: {e}")
        return False

def get_reviews_page(url, device_type="desktop", wait_time=5, max_days_back=30, max_reviews_limit=100, use_proxy=True):
    """
    Основная функция для получения отзывов с Яндекс Карт
    
    Args:
        url: URL страницы отзывов
        device_type: "mobile" или "desktop"  
        wait_time: время ожидания в секундах
        max_days_back: максимальное количество дней назад для первичного парсинга
        max_reviews_limit: максимальное количество отзывов для парсинга
        use_proxy: использовать ли прокси (по умолчанию True)
    
    Returns:
        dict: результаты парсинга
    """
    
    # Извлекаем ID карточки из URL
    card_id = extract_card_id_from_url(url)
    if not card_id:
        print("❌ Не удалось извлечь ID карточки из URL")
        return None
    
    # Определяем стратегию парсинга на основе checkpoint
    checkpoint_info = get_checkpoint_info(card_id)
    
    if checkpoint_info['has_checkpoint']:
        print("🔄 ИНКРЕМЕНТАЛЬНЫЙ парсинг до checkpoint")
        parsing_strategy = "incremental"
    else:
        print("🆕 ПЕРВИЧНЫЙ парсинг за последние {} дней".format(max_days_back))
        parsing_strategy = "initial"
    
    # Инициализация менеджера прокси (РАБОЧИЙ МЕТОД SELENIUMWIRE)
    proxy_manager = None
    if use_proxy and PROXY_AVAILABLE:
        try:
            proxy_manager = ProxyManagerSeleniumWire()
            stats = proxy_manager.get_stats()
            working_proxies = stats['total_proxies']
            print(f"✅ Загружено {working_proxies} рабочих прокси")
        except Exception as e:
            print(f"❌ Ошибка инициализации прокси: {e}")
            print("🔄 Продолжаем без прокси...")
            proxy_manager = None
    elif use_proxy and not PROXY_AVAILABLE:
        print("⚠️ Прокси запрошены, но модуль недоступен")
    
    # Настройка и запуск браузера с поддержкой прокси
    print(f"🚀 Настройка Selenium драйвера ({device_type})...")
    driver = setup_driver(device_type, proxy_manager)
    
    if not driver:
        print("❌ Не удалось запустить браузер")
        return None
    
    print("✅ Драйвер запущен!")
    
    try:
        # Загружаем страницу
        print("🔗 Загружаем страницу...")
        driver.get(url)
        
        # БЕЗОПАСНОСТЬ: Случайная пауза для имитации человеческого поведения
        import random
        human_pause = wait_time + random.uniform(0.5, 2.0)
        print(f"⏳ Ожидание {human_pause:.1f} секунд (имитация человека)...")
        time.sleep(human_pause)
        
        # Получаем информацию о странице
        page_info = get_page_info(driver)
        
        # 🔧 ОБРАБОТКА ВСПЛЫВАЮЩИХ ОКОН ПРИЛОЖЕНИЯ (простой метод)
        if POPUP_HANDLER_AVAILABLE:
            try:
                handle_popup_simple(driver, verbose=False)
            except Exception as e:
                print(f"⚠️ Ошибка обработки всплывающих окон: {e}")
        
        # Проверяем на CAPTCHA
        if check_for_captcha(driver):
            print("🤖 Обнаружена CAPTCHA! Пытаемся решить...")
            
            # Делаем скриншот CAPTCHA
            driver.save_screenshot("captcha_detected.png")
            print("📸 Скриншот CAPTCHA сохранен: captcha_detected.png")
            
            # Пытаемся решить CAPTCHA автоматически
            captcha_solved = handle_captcha_automatically(driver)
            
            if not captcha_solved:
                print("❌ Не удалось решить CAPTCHA автоматически")
                print("🔧 Решите CAPTCHA вручную в браузере и нажмите Enter...")
                input("Нажмите Enter после решения CAPTCHA...")
                
                # Проверяем еще раз
                if check_for_captcha(driver):
                    print("❌ CAPTCHA все еще присутствует. Завершение работы.")
                    return {
                        "success": False,
                        "error": "CAPTCHA не решена",
                        "url": driver.current_url,
                        "screenshot": "captcha_detected.png"
                    }
            
            print("✅ CAPTCHA решена! Продолжаем...")
        else:
            print("✅ CAPTCHA не обнаружена! Страница загружена успешно.")
        
        # Применяем сортировку
        sort_applied = click_sort_by_date(driver)
        
        # БЕЗОПАСНОСТЬ: Пауза после сортировки
        if sort_applied:
            human_pause = random.uniform(1.0, 2.0)
            print(f"⏳ Пауза после сортировки: {human_pause:.1f} сек...")
            time.sleep(human_pause)
        
        # 🌊 ПЛАВНОЕ раскрытие отзывов с проверкой дат ПЕРЕД парсингом
        print(f"\n🌊 Плавное раскрытие отзывов...")
        
        if parsing_strategy == "incremental":
            # Инкрементальный парсинг - раскрываем до checkpoint
            expanded_count = expand_all_reviews_with_date_check(driver, max_days_back=None, checkpoint_info=checkpoint_info)
        else:
            # Первичный парсинг - раскрываем только до целевой даты
            expanded_count = expand_all_reviews_with_date_check(driver, max_days_back)
        
        print(f"✅ Раскрыто отзывов: {expanded_count}")
        
        # Извлекаем отзывы в зависимости от стратегии
        print(f"\n📝 Извлекаем отзывы (стратегия: {parsing_strategy})...")
        
        if parsing_strategy == "incremental":
            # Инкрементальный парсинг до checkpoint
            reviews_data = extract_reviews_until_checkpoint(driver, checkpoint_info, card_id, max_reviews_limit)
        else:
            # Первичный парсинг за определенный период
            reviews_data = extract_reviews_with_time_limit(driver, max_days_back, max_reviews_limit)
        
        # Сохраняем отзывы в базу данных
        save_result = save_reviews_to_database(reviews_data, card_id)
        
        # Выводим отзывы в консоль
        print_reviews(reviews_data)
        
        # Делаем финальный скриншот
        driver.save_screenshot("reviews_page_sorted_new_first.png")
        print("📸 Скриншот сохранен: reviews_page_sorted_new_first.png")
        
        # Финальная информация
        final_info = {
            "success": True,
            "url": driver.current_url,
            "title": driver.title,
            "captcha_detected": False,  # Если дошли до сюда, то CAPTCHA решена
            "sort_applied": sort_applied,
            "screenshot": "reviews_page_sorted_new_first.png",
            "parsing_strategy": parsing_strategy,
            "reviews_found": len(reviews_data),
            "database_result": save_result
        }
        
        print(f"\n📊 Результат:")
        print(f"   🌐 Финальный URL: {final_info['url']}")
        print(f"   📄 Заголовок: {final_info['title']}")
        print(f"   🤖 CAPTCHA: {'Нет' if not final_info['captcha_detected'] else 'Да'}")
        print(f"   📅 Сортировка 'New first': {'Применена' if final_info['sort_applied'] else 'Не применена'}")
        print(f"   📸 Скриншот: {final_info['screenshot']}")
        
        print("\n✅ Задача выполнена. Браузер будет закрыт автоматически.")
        
        return final_info
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
        # Делаем скриншот ошибки
        try:
            driver.save_screenshot("error_screenshot.png")
            print("📸 Скриншот ошибки сохранен: error_screenshot.png")
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "url": driver.current_url if driver else url,
            "screenshot": "error_screenshot.png"
        }
        
    finally:
        # Закрываем браузер
        if driver:
            print("🔒 Браузер закрыт.")
            driver.quit()

def main():
    """Основная функция"""
    # URL по умолчанию - страница Адверт Про
    default_url = "https://yandex.ru/maps/org/kombinat_sotsialnogo_pitaniya/1111195101/reviews/?ll=37.597909%2C54.210244&z=17.63"
    default_url = "https://yandex.ru/maps/org/tulskiy_gosudarstvenny_tsirk/1100333178/reviews/?ll=37.626170%2C54.189593&z=17.63"

    
    # ============= НАСТРОЙКИ ПАРСИНГА =============
    MAX_DAYS_BACK = 10        # Количество дней назад для первичного парсинга (3 года)
    MAX_REVIEWS_LIMIT = 2000    # Максимальное количество отзывов для парсинга
    DEVICE_TYPE = "mobile"    # Тип устройства: "mobile" или "desktop" 
    WAIT_TIME = 3             # Время ожидания загрузки страницы (секунды)
    USE_PROXY = True          # Использовать прокси по умолчанию
    # =============================================
    
    # Проверяем аргументы командной строки
    url = default_url
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--no-proxy":
            USE_PROXY = False
            print("🚫 Прокси отключены через --no-proxy")
        elif not arg.startswith("--"):
            url = arg
            print(f"📝 URL из аргументов: {url}")
    
    if url == default_url:
        print(f"📝 URL по умолчанию: {url}")
    
    print("🗺️ Получение отзывов с Яндекс Карт")
    print("=" * 50)
    print(f"⚙️ НАСТРОЙКИ ПАРСИНГА:")
    print(f"   📅 Первичный парсинг: за последние {MAX_DAYS_BACK} дней")
    print(f"   📊 Максимум отзывов: {MAX_REVIEWS_LIMIT}")
    print(f"   📱 Устройство: {DEVICE_TYPE}")
    print(f"   ⏱️ Время ожидания: {WAIT_TIME} сек")
    print(f"   🌐 Использовать прокси: {'Да' if USE_PROXY else 'Нет'}")
    print("=" * 50)
    
    print(f"\n📱 Используем: {DEVICE_TYPE} устройство (iPhone 13) с раскрытием отзывов")
    
    # Запускаем получение страницы
    result = get_reviews_page(
        url=url, 
        device_type=DEVICE_TYPE, 
        wait_time=WAIT_TIME,
        max_days_back=MAX_DAYS_BACK,
        max_reviews_limit=MAX_REVIEWS_LIMIT,
        use_proxy=USE_PROXY
    )
    
    if result["success"]:
        print(f"\n🎉 Задача выполнена успешно!")
        
        # Отображаем результаты сохранения в БД
        if result.get("database_result"):
            db_results = result["database_result"]
            if db_results["saved"] > 0 or db_results["duplicates"] > 0:
                print(f"\n💾 Результаты сохранения в БД:")
                print(f"   🆔 ID карточки: {result.get('card_id', 'N/A')}")
                print(f"   ✅ Новых отзывов сохранено: {db_results['saved']}")
                print(f"   ⚠️ Дубликатов пропущено: {db_results['duplicates']}")
                if db_results['errors'] > 0:
                    print(f"   ❌ Ошибок при сохранении: {db_results['errors']}")
        
        if result.get("captcha_detected", False):
            print("💡 Для решения CAPTCHA используйте selenium_captcha_solver.py")
    else:
        print(f"\n❌ Ошибка выполнения: {result.get('error', 'Неизвестная ошибка')}")

if __name__ == "__main__":
    main() 