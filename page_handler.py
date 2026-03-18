"""
Модуль для работы со страницей Яндекс.Карт
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import os
from thread_logger import thread_print

# Импорт функций решения CAPTCHA
try:
    from captcha_solver import detect_captcha as captcha_detect, solve_captcha as captcha_solve
    CAPTCHA_SOLVER_AVAILABLE = True
except ImportError:
    CAPTCHA_SOLVER_AVAILABLE = False

# Импорт упрощенного обработчика всплывающих окон приложения
try:
    from popup_handler import handle_popup_simple
    POPUP_HANDLER_AVAILABLE = True
except ImportError:
    POPUP_HANDLER_AVAILABLE = False
    handle_popup_simple = None

def prepare_reviews_url(url: str) -> str:
    """
    Подготавливает URL для парсинга отзывов
    Если в URL нет /reviews/, то:
    1. Находит ID организации
    2. Обрезает всё что после ID (включая GET параметры и другие пути)
    3. Добавляет /reviews/ в конец
    
    Args:
        url: Исходный URL
        
    Returns:
        Нормализованный URL с /reviews/
    """
    if not url:
        return url
    
    url = url.strip()
    
    # Проверяем, есть ли уже /reviews/ в URL
    if '/reviews/' in url or '/reviews' in url:
        thread_print(f"✅ URL уже содержит /reviews/: {url}")
        return url
    
    # Проверяем, что это URL Яндекс.Карт с ID организации
    # Паттерн ищет /org/название/ID и всё что после ID (включая GET параметры)
    org_pattern = r'(https?://[^/]+/[^/]+/org/[^/]+/\d+)'
    match = re.search(org_pattern, url)
    
    if match:
        # Получаем базовую часть URL до ID включительно
        base_url = match.group(1)
        
        # Добавляем /reviews/
        normalized_url = base_url + '/reviews/'
        
        thread_print(f"🔧 URL нормализован: {url} → {normalized_url}")
        return normalized_url

    # Яндекс.Профиль: yandex.ru/profile/ID → конвертируем в maps/org/ID/reviews/
    profile_pattern = r'https?://(?:yandex\.ru|yandex\.com)/profile/(\d+)'
    profile_match = re.search(profile_pattern, url, re.IGNORECASE)
    if profile_match:
        org_id = profile_match.group(1)
        normalized_url = f"https://yandex.ru/maps/org/{org_id}/reviews/"
        thread_print(f"🔧 URL профиля конвертирован в Карты: {url} → {normalized_url}")
        return normalized_url
    
    thread_print(f"⚠️ URL не соответствует формату Яндекс.Карт: {url}")
    return url

def extract_card_id_from_url(url: str) -> str:
    """Извлечь ID карточки из URL Яндекс Карт"""
    # Паттерн для поиска ID карточки в URL
    # Ищем числовой ID после /org/название/
    pattern = r'/org/[^/]+/(\d+)/?'
    match = re.search(pattern, url)
    
    if match:
        card_id = match.group(1)
        thread_print(f"🆔 Извлечен ID карточки: {card_id}")
        return card_id
    else:
        thread_print(f"❌ Не удалось извлечь ID карточки из URL: {url}")
        return None

def get_page_info(driver):
    """Получение информации о странице"""
    info = {
        "url": driver.current_url,
        "title": driver.title,
        "timestamp": time.time()
    }
    
    thread_print(f"🌐 URL: {info['url']}")
    thread_print(f"📄 Заголовок: {info['title']}")
    
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

def handle_captcha_with_proxy_restart(driver, proxy_manager, device_type="desktop", profile_path=None):
    """
    Обработка капчи с переключением прокси и созданием нового профиля
    
    Args:
        driver: текущий драйвер с капчей
        proxy_manager: менеджер прокси
        device_type: тип устройства
        profile_path: путь к профилю (для удаления старого)
    
    Returns:
        Новый драйвер с другим прокси и профилем или None
    """
    print("🤖 Обнаружена капча! Переключаем на новый прокси и профиль...")
    
    try:
        # Импортируем функцию переключения прокси из driver_manager
        from driver_manager import handle_captcha_with_proxy_switching
        
        # Вызываем функцию переключения прокси
        new_driver = handle_captcha_with_proxy_switching(
            driver, 
            proxy_manager, 
            device_type, 
            profile_path, 
            max_proxy_attempts=3
        )
        
        if new_driver:
            print("✅ Успешно переключились на новый прокси и профиль!")
            return new_driver
        else:
            print("❌ Не удалось переключиться на новый прокси")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка переключения прокси: {e}")
        return None

def handle_captcha_automatically(driver, proxy_manager=None, device_type="desktop", profile_path=None):
    """Автоматическое решение CAPTCHA с возможностью переключения прокси"""
    print("🤖 Запускаем автоматическое решение CAPTCHA...")
    
    # Сначала пробуем решить капчу автоматически
    if CAPTCHA_SOLVER_AVAILABLE:
        try:
            # Используем продвинутую детекцию CAPTCHA
            captcha_found, captcha_element = captcha_detect(driver)
        
            if not captcha_found:
                print("✅ CAPTCHA не обнаружена продвинутым детектором")
                return driver, True
        
            print("🎯 CAPTCHA подтверждена, пытаемся решить...")
        
            # Пытаемся решить CAPTCHA
            success = captcha_solve(driver, captcha_element)
        
            if success:
                print("✅ CAPTCHA успешно решена!")
                return driver, True
            else:
                print("❌ Не удалось решить CAPTCHA автоматически")
            
        except Exception as e:
            print(f"❌ Ошибка при автоматическом решении CAPTCHA: {e}")
        else:
            print("❌ Модуль решения CAPTCHA недоступен")
    
    # Если автоматическое решение не сработало, переключаем прокси
    if proxy_manager:
        print("🔄 Пробуем переключить прокси...")
        
        # Получаем путь к профилю из драйвера если не передан
        if not profile_path:
            try:
                from driver_manager import get_driver_profile_path
                profile_path = get_driver_profile_path(driver)
                if profile_path:
                    print(f"📁 Получен путь к профилю драйвера: {os.path.basename(profile_path)}")
            except Exception as e:
                print(f"⚠️ Не удалось получить путь к профилю: {e}")
        
        new_driver = handle_captcha_with_proxy_restart(
            driver, proxy_manager, device_type, profile_path
        )
        
        if new_driver:
            return new_driver, True
        else:
            print("❌ Переключение прокси не помогло")
            return driver, False
    else:
        print("⚠️ Прокси менеджер не предоставлен - переключение невозможно")
        return driver, False

def click_sort_by_date(driver):
    """Переключение сортировки отзывов на 'Сначала новые' (по дате)"""
    print("📅 Ищем кнопку сортировки...")
    
    try:
        # Ищем кнопку сортировки "По умолчанию"
        print("🔍 Ищем кнопку 'By default' или 'По умолчанию'...")
        
        # Основной селектор для кнопки сортировки
        sort_button_selector = "div.rating-ranking-view[role='button']"
        
        try:
            sort_button = driver.find_element(By.CSS_SELECTOR, sort_button_selector)
            if sort_button.is_displayed():
                button_text = sort_button.text.strip()
                print(f"✅ Найден элемент: {sort_button_selector}")
                print(f"   📱 Текст: '{button_text}'")
                
                # Проверяем, что это действительно кнопка сортировки
                if any(keyword in button_text.lower() for keyword in ['по умолчанию', 'by default', 'умолчанию']):
                    print("🎯 Подходящий элемент найден!")
                else:
                    print(f"⚠️ Элемент найден, но текст не соответствует ожидаемому: '{button_text}'")
                    return False
            else:
                print(f"❌ Элемент найден, но не видим")
                return False
        except Exception as e:
            print(f"❌ Кнопка сортировки не найдена: {e}")
            return False
        
        # Кликаем по кнопке сортировки
        try:
            driver.execute_script("arguments[0].click();", sort_button)
            print("🖱️ JavaScript клик по кнопке сортировки выполнен!")
            time.sleep(1)  # Ждем появления выпадающего меню
        except Exception as e:
            print(f"❌ Ошибка клика по кнопке сортировки: {e}")
            return False
        
        # Ищем опцию "По новизне" в выпадающем меню
        print("📋 Ищем опцию 'New first' в выпадающем меню...")
        
        # Селектор для опций в выпадающем меню
        option_selector = ".rating-ranking-view__popup-line"
        
        try:
            options = driver.find_elements(By.CSS_SELECTOR, option_selector)
            target_option = None
            
            for option in options:
                if option.is_displayed():
                    option_text = option.text.strip()
                    print(f"✅ Найдена опция: {option_selector}")
                    print(f"   📱 Текст опции: '{option_text}'")
                    
                    # Ищем опцию "По новизне" или "New first"
                    if any(keyword in option_text.lower() for keyword in ['по новизне', 'new first', 'newest', 'новизне']):
                        target_option = option
                        print("🎯 Подходящая опция найдена!")
                        break
            
            if target_option:
                # Кликаем по опции "По новизне"
                try:
                    driver.execute_script("arguments[0].click();", target_option)
                    print("🖱️ JavaScript клик по опции выполнен!")
                    time.sleep(1)  # Ждем применения сортировки
                except Exception as e:
                    print(f"❌ Ошибка клика по опции: {e}")
                    return False
            else:
                print("❌ Опция 'По новизне' не найдена в выпадающем меню")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка поиска опций в выпадающем меню: {e}")
            return False
        
        print("📅 Сортировка 'New first' применена!")
        
        # Небольшая пауза для применения сортировки
        import random
        pause_time = random.uniform(1.0, 2.0)
        print(f"⏳ Пауза после сортировки: {pause_time:.1f} сек...")
        time.sleep(pause_time)
        
        return True
        
    except Exception as e:
        print(f"❌ Общая ошибка в функции сортировки: {e}")
        return False

def handle_popup_if_available(driver):
    """Обработка всплывающих окон если доступен модуль"""
    if POPUP_HANDLER_AVAILABLE and handle_popup_simple:
        try:
            handle_popup_simple(driver, verbose=True)
        except Exception as e:
            print(f"⚠️ Ошибка обработки всплывающего окна: {e}")
    else:
        print("⚠️ Модуль обработки всплывающих окон недоступен")

def scroll_page(driver):
    """Прокрутка страницы вниз для загрузки дополнительных отзывов"""
    try:
        # Получаем высоту страницы до прокрутки
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        # Прокручиваем страницу вниз
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Ждем загрузки новых элементов
        time.sleep(2)
        
        # Получаем новую высоту страницы
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Возвращаем True, если страница увеличилась (загрузились новые элементы)
        return new_height > last_height
        
    except Exception as e:
        print(f"❌ Ошибка прокрутки страницы: {e}")
        return False 