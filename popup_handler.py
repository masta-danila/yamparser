#!/usr/bin/env python3
"""
Упрощенный обработчик всплывающих окон приложения
Только поиск и клик по кнопке "Не сейчас"
"""

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def find_not_now_button(driver):
    """
    Поиск кнопки "Не сейчас" или аналогичной
    
    Алгоритм поиска:
    1. Ищет по тексту кнопки (XPath)
    2. Ищет по CSS селекторам кнопок
    3. Проверяет aria-label и title атрибуты
    """
    
    # Возможные тексты кнопок "Не сейчас" и принятия куков
    button_texts = [
        # Кнопки закрытия приложения
        "Не сейчас",
        "Not now", 
        "Not Now",
        "Later",
        "Maybe later",
        "Позже",
        "Отмена",
        "Cancel",
        "Закрыть",
        "Close",
        "Dismiss",
        "Пропустить",
        "Skip",
        "No thanks",
        "No, thanks",
        # Кнопки принятия куков
        "Accept",
        "Accept all",
        "Accept cookies",
        "Accept all cookies",
        "I agree",
        "Agree",
        "OK",
        "Got it",
        "Understood",
        "Принять",
        "Принять все",
        "Принять куки",
        "Согласен",
        "Я согласен",
        "Понятно"
    ]
    
    found_buttons = []
    
    # 1. ПРИОРИТЕТНЫЙ ПОИСК ПО ID (самый надежный)
    print("🔍 Приоритетный поиск по ID...")
    try:
        # Известные ID кнопок закрытия для разных типов попапов
        known_ids = [
            "close-button",
            "dismiss-button", 
            "cancel-button",
            "not-now-button",
            "app-banner-close",
            "modal-close",
            "popup-close",
            "banner-close",
            "install-banner-close"
        ]
        
        for button_id in known_ids:
            try:
                element = driver.find_element(By.ID, button_id)
                if element.is_displayed() and element.is_enabled():
                    found_buttons.append({
                        "element": element,
                        "method": f"ID: #{button_id}",
                        "text": element.text or f"[id='{button_id}']",
                        "tag": element.tag_name,
                        "classes": element.get_attribute("class") or ""
                    })
                    print(f"   ✅ Найдена кнопка по ID: #{button_id} ({element.tag_name})")
            except:
                continue
    except Exception as e:
        pass
    
    # 2. ПОИСК ПО ТЕКСТУ КНОПКИ
    print("🔍 Ищем кнопки по тексту...")
    for text in button_texts:
        try:
            # XPath поиск по точному тексту (включая div для Яндекс.Карт)
            xpath_exact = f"//button[text()='{text}'] | //a[text()='{text}'] | //div[text()='{text}']"
            buttons = driver.find_elements(By.XPATH, xpath_exact)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    found_buttons.append({
                        "element": button,
                        "method": f"Точный текст: '{text}'",
                        "text": button.text,
                        "tag": button.tag_name,
                        "classes": button.get_attribute("class") or ""
                    })
                    print(f"   ✅ Найдена кнопка: '{text}' ({button.tag_name})")
            
            # XPath поиск по содержанию текста (включая div)
            xpath_contains = f"//button[contains(text(), '{text}')] | //a[contains(text(), '{text}')] | //div[contains(text(), '{text}')]"
            buttons = driver.find_elements(By.XPATH, xpath_contains)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    # Проверяем, что еще не добавили эту кнопку
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Содержит текст: '{text}'",
                            "text": button.text,
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка: '{button.text}' ({button.tag_name})")
        except Exception as e:
            continue
    
    # 2.1. СПЕЦИАЛЬНЫЙ ПОИСК ДЛЯ ЯНДЕКС.КАРТ (после основного поиска по тексту)
    print("🔍 Дополнительный поиск для Яндекс.Карт...")
    try:
        # Поиск ссылок с динамическими классами Яндекса, содержащих "Не сейчас"
        yandex_patterns = [
            "//a[text()='Не сейчас' and contains(@class, 'cea')]",  # Конкретный паттерн из отладки
            "//a[text()='Не сейчас' and string-length(@class) > 5]",  # Ссылки с длинными хэшированными классами
            "//a[text()='Не сейчас' and @class]",  # Любые ссылки с классами
            "//div[text()='Не сейчас' and contains(@class, 'na')]",  # Родительские div с классами
            # НОВЫЕ ПАТТЕРНЫ ДЛЯ БАННЕРА ПРИЛОЖЕНИЯ:
            "//a[text()='Не сейчас' and contains(@class, 'p1dba9a6a')]",  # Специфичный класс баннера
            "//a[text()='Не сейчас' and ancestor::*[starts-with(@id, 'Y-A-')]]",  # Внутри баннера с ID Y-A-*
        ]
        
        for pattern in yandex_patterns:
            buttons = driver.find_elements(By.XPATH, pattern)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        classes = button.get_attribute("class") or ""
                        found_buttons.append({
                            "element": button,
                            "method": f"Яндекс.Карты паттерн: {pattern}",
                            "text": button.text,
                            "tag": button.tag_name,
                            "classes": classes
                        })
                        print(f"   ✅ Найдена кнопка Яндекс.Карт: 'Не сейчас' ({button.tag_name}) classes='{classes[:20]}...'")
    except Exception as e:
        print(f"   ⚠️ Ошибка поиска Яндекс.Карт: {e}")
    
    # 2.2. ПОИСК КНОПКИ ЗАКРЫТИЯ ПО ARIA-LABEL="Закрыть"
    print("🔍 Поиск кнопки закрытия по aria-label...")
    try:
        close_buttons = driver.find_elements(By.XPATH, "//*[@aria-label='Закрыть']")
        for button in close_buttons:
            if button.is_displayed() and button.is_enabled():
                if not any(b["element"] == button for b in found_buttons):
                    classes = button.get_attribute("class") or ""
                    found_buttons.append({
                        "element": button,
                        "method": "Aria-label: 'Закрыть'",
                        "text": "Закрыть (крестик)",
                        "tag": button.tag_name,
                        "classes": classes
                    })
                    print(f"   ✅ Найдена кнопка закрытия: (крестик) ({button.tag_name}) classes='{classes[:20]}...'")
    except Exception as e:
        print(f"   ⚠️ Ошибка поиска кнопки закрытия: {e}")
    
    # 3. ПОИСК ПО ARIA-LABEL И TITLE
    print("🔍 Ищем кнопки по aria-label и title...")
    for text in button_texts:
        try:
            # Поиск по aria-label
            xpath_aria = f"//button[@aria-label='{text}'] | //a[@aria-label='{text}']"
            buttons = driver.find_elements(By.XPATH, xpath_aria)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Aria-label: '{text}'",
                            "text": button.text or f"[aria-label='{text}']",
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка по aria-label: '{text}' ({button.tag_name})")
            
            # Поиск по title
            xpath_title = f"//button[@title='{text}'] | //a[@title='{text}']"
            buttons = driver.find_elements(By.XPATH, xpath_title)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Title: '{text}'",
                            "text": button.text or f"[title='{text}']",
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка по title: '{text}' ({button.tag_name})")
        except Exception as e:
            continue
    
    # 4. СПЕЦИАЛЬНЫЙ ПОИСК ДЛЯ ЯНДЕКС.КАРТ И COOKIE-БАННЕРОВ
    print("🔍 Специальный поиск для Яндекс.Карт и cookie-баннеров...")
    try:
        # Поиск кнопок с классами, содержащими 'close' или подобными
        close_selectors = [
            "button[class*='close']",
            "a[class*='close']", 
            "button.close-button",
            "a.close-button",
            # GDPR селекторы для Яндекс (ПРИОРИТЕТ!)
            ".gdpr-popup-v3-button",
            "div[class*='gdpr-popup-v3-button']",
            "#gdpr-popup-v3-button-all",
            "[class*='gdpr-popup-v3-button_id_all']",
            # НОВЫЕ СЕЛЕКТОРЫ ДЛЯ БАННЕРА ЯНДЕКС.КАРТ:
            "a.p1dba9a6a",  # Кнопка "Не сейчас" в баннере приложения
            "[id^='Y-A-'] a",  # Любые ссылки внутри баннера с ID Y-A-*
            "[id^='Y-A-'] [aria-label='Закрыть']",  # Кнопка закрытия в баннере
            "span[aria-label='Закрыть']",  # Кнопка-крестик
            # Cookie-специфичные селекторы
            "button[class*='cookie']",
            "div[class*='cookie']",
            "button[class*='accept']",
            "div[class*='accept']",
            "button[class*='consent']",
            "div[class*='consent']",
            "button[class*='agree']",
            "div[class*='agree']",
            "[data-testid*='cookie']",
            "[data-testid*='accept']",
            "[data-testid*='consent']",
            # Общие селекторы для модальных окон
            ".modal button",
            ".popup button",
            ".banner button",
            ".modal div",
            ".popup div",
            ".banner div",
            "[role='dialog'] button",
            "[role='banner'] button",
            "[role='dialog'] div",
            "[role='banner'] div"
        ]
        
        for selector in close_selectors:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"CSS селектор: {selector}",
                            "text": button.text or "[Без текста]",
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка по селектору: {selector}")
    except Exception as e:
        pass
    
    # 5. ПОИСК ВСЕХ ВИДИМЫХ КНОПОК (как запасной вариант)
    print("🔍 Поиск всех видимых кнопок...")
    try:
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        
        for button in all_buttons + all_links:
            if button.is_displayed() and button.is_enabled():
                button_text = button.text.lower()
                button_classes = (button.get_attribute("class") or "").lower()
                aria_label = (button.get_attribute("aria-label") or "").lower()
                
                # Проверяем, подходит ли эта кнопка
                relevant_keywords = [
                    "accept", "agree", "ok", "got it", "understood",
                    "принять", "согласен", "понятно", "хорошо",
                    "close", "dismiss", "not now", "later", "skip",
                    "закрыть", "не сейчас", "позже", "пропустить"
                ]
                
                is_relevant = any(keyword in f"{button_text} {button_classes} {aria_label}" 
                                for keyword in relevant_keywords)
                
                if is_relevant and not any(b["element"] == button for b in found_buttons):
                    found_buttons.append({
                        "element": button,
                        "method": "Поиск по ключевым словам",
                        "text": button.text or "[Без текста]",
                        "tag": button.tag_name,
                        "classes": button.get_attribute("class") or ""
                    })
                    print(f"   ✅ Найдена кнопка по ключевым словам: '{button.text}' ({button.tag_name})")
    except Exception as e:
        pass
    
    print(f"🎯 Всего найдено кнопок: {len(found_buttons)}")
    return found_buttons

def click_button_simple(driver, button_info):
    """
    Простой клик по кнопке (только основные методы)
    """
    element = button_info["element"]
    
    # Метод 1: Обычный клик
    try:
        element.click()
        print(f"   ✅ Обычный клик успешен")
        return True
    except Exception as e:
        print(f"   ❌ Обычный клик не сработал: {str(e)[:50]}")
    
    # Метод 2: JavaScript клик (самый надежный)
    try:
        driver.execute_script("arguments[0].click();", element)
        print(f"   ✅ JavaScript клик успешен")
        return True
    except Exception as e:
        print(f"   ❌ JavaScript клик не сработал: {str(e)[:50]}")
    
    print(f"   ❌ Все методы клика не сработали")
    return False

def detect_app_popup_simple(driver):
    """
    Простое обнаружение всплывающего окна приложения
    """
    popup_indicators = [
        "Установить приложение",
        "Загрузить приложение", 
        "Скачать приложение",
        "Download app",
        "Install app",
        "Get the app",
        "Download the app",
        "Install the app",
        "Get our app",
        "Try our app",
        # НОВЫЕ ИНДИКАТОРЫ ДЛЯ ЯНДЕКС.КАРТ:
        "В приложении Яндекс Карт",
        "Ищите адреса и выбирайте места",
        "даже без интернета"
    ]
    
    # 1. Поиск по тексту индикаторов
    for indicator in popup_indicators:
        try:
            xpath = f"//*[contains(text(), '{indicator}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            if any(elem.is_displayed() for elem in elements):
                print(f"🎯 Найдено всплывающее окно: '{indicator}'")
                return True
        except:
            continue
    
    # 2. Поиск баннера Яндекс.Карт по ID
    try:
        banners = driver.find_elements(By.CSS_SELECTOR, "[id^='Y-A-']")
        for banner in banners:
            if banner.is_displayed():
                print(f"🎯 Найден баннер Яндекс.Карт: ID={banner.get_attribute('id')}")
                return True
    except:
        pass
    
    return False

def detect_cookie_popup_simple(driver):
    """
    Простое обнаружение всплывающего окна с куками
    """
    cookie_indicators = [
        "cookie", "cookies", "куки", "кукис",
        "We use cookies", "This site uses cookies",
        "Accept cookies", "Accept all cookies",
        "Cookie policy", "Privacy policy",
        "Согласие на обработку", "Принять куки",
        "Принять все", "Accept all",
        "I agree", "Я согласен"
    ]
    
    for indicator in cookie_indicators:
        try:
            xpath = f"//*[contains(text(), '{indicator}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            if any(elem.is_displayed() for elem in elements):
                print(f"🍪 Найдено окно с куками: '{indicator}'")
                return True
        except:
            continue
    
    return False

def find_cookie_accept_button(driver):
    """
    Поиск кнопки принятия куков (Accept)
    """
    
    # Тексты кнопок для принятия куков (приоритет "Allow all")
    accept_texts = [
        "Allow all",  # Приоритет для Яндекс.Карт
        "Accept all",
        "Accept",
        "Accept cookies", 
        "Accept all cookies",
        "I agree",
        "Agree",
        "OK",
        "Got it",
        "Understood",
        "Allow",
        "Принять все",
        "Принять",
        "Принять куки",
        "Согласен",
        "Я согласен",
        "Понятно",
        "Хорошо",
        "Разрешить"
    ]
    
    found_buttons = []
    
    # 1. ПРИОРИТЕТНЫЙ ПОИСК "ALLOW ALL" (для Яндекс.Карт)
    print("🔍 Приоритетный поиск кнопки 'Allow all'...")
    try:
        # Ищем именно "Allow all" с разными вариантами (включая div!)
        allow_all_selectors = [
            "//div[text()='Allow all']",  # Яндекс использует div!
            "//button[text()='Allow all']",
            "//a[text()='Allow all']",
            "//div[contains(text(), 'Allow all')]",
            "//button[contains(text(), 'Allow all')]",
            "//a[contains(text(), 'Allow all')]",
            "//div[normalize-space(text())='Allow all']",
            "//button[normalize-space(text())='Allow all']",
            "//a[normalize-space(text())='Allow all']",
            # Поиск по ID и классам GDPR
            "//*[@id='gdpr-popup-v3-button-all']",
            "//*[contains(@class, 'gdpr-popup-v3-button_id_all')]"
        ]
        
        for selector in allow_all_selectors:
            buttons = driver.find_elements(By.XPATH, selector)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Приоритетный поиск: Allow all",
                            "text": button.text,
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   🎯 НАЙДЕНА КНОПКА 'Allow all': '{button.text}' ({button.tag_name})")
    except Exception as e:
        pass
    
    # 2. ПОИСК ПО ТЕКСТУ КНОПКИ ПРИНЯТИЯ
    print("🔍 Ищем кнопки принятия куков по тексту...")
    for text in accept_texts:
        try:
            # XPath поиск по точному тексту (включая div)
            xpath_exact = f"//button[text()='{text}'] | //a[text()='{text}'] | //div[text()='{text}']"
            buttons = driver.find_elements(By.XPATH, xpath_exact)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Точный текст: '{text}'",
                            "text": button.text,
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка: '{text}' ({button.tag_name})")
            
            # XPath поиск по содержанию текста (включая div)
            xpath_contains = f"//button[contains(text(), '{text}')] | //a[contains(text(), '{text}')] | //div[contains(text(), '{text}')]"
            buttons = driver.find_elements(By.XPATH, xpath_contains)
            
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"Содержит текст: '{text}'",
                            "text": button.text,
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка: '{button.text}' ({button.tag_name})")
        except Exception as e:
            continue
    
    # 3. ПОИСК ПО CSS СЕЛЕКТОРАМ ДЛЯ КУКОВ
    print("🔍 Поиск кнопок принятия куков по CSS селекторам...")
    try:
        cookie_selectors = [
            "button[class*='accept']",
            "button[class*='cookie']",
            "button[class*='consent']",
            "button[class*='agree']",
            "[data-testid*='accept']",
            "[data-testid*='cookie']",
            "[data-testid*='consent']",
            "[data-cy*='accept']",
            "[data-cy*='cookie']"
        ]
        
        for selector in cookie_selectors:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    if not any(b["element"] == button for b in found_buttons):
                        found_buttons.append({
                            "element": button,
                            "method": f"CSS селектор: {selector}",
                            "text": button.text or "[Без текста]",
                            "tag": button.tag_name,
                            "classes": button.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найдена кнопка по селектору: {selector}")
    except Exception as e:
        pass
    
    # 4. ПОИСК ВСЕХ КНОПОК В COOKIE-БАННЕРЕ
    print("🔍 Поиск всех кнопок в cookie-баннере...")
    try:
        # Ищем cookie-баннер
        banner_selectors = [
            "[class*='cookie']",
            "[class*='consent']", 
            "[class*='banner']",
            "[role='banner']",
            "[data-testid*='cookie']"
        ]
        
        for selector in banner_selectors:
            banners = driver.find_elements(By.CSS_SELECTOR, selector)
            for banner in banners:
                if banner.is_displayed():
                    # Ищем все кнопки внутри баннера
                    buttons_in_banner = banner.find_elements(By.TAG_NAME, "button")
                    links_in_banner = banner.find_elements(By.TAG_NAME, "a")
                    
                    for button in buttons_in_banner + links_in_banner:
                        if button.is_displayed() and button.is_enabled():
                            if not any(b["element"] == button for b in found_buttons):
                                found_buttons.append({
                                    "element": button,
                                    "method": f"Кнопка в баннере: {selector}",
                                    "text": button.text or "[Без текста]",
                                    "tag": button.tag_name,
                                    "classes": button.get_attribute("class") or ""
                                })
                                print(f"   ✅ Найдена кнопка в баннере: '{button.text}' ({button.tag_name})")
    except Exception as e:
        pass
    
    print(f"🎯 Всего найдено кнопок принятия куков: {len(found_buttons)}")
    return found_buttons

def handle_popup_simple(driver, verbose=False):
    """
    Простая обработка всплывающих окон (приложения и куки)
    
    Args:
        driver: Selenium WebDriver
        verbose: Подробный вывод (по умолчанию False для тихой работы)
    
    Returns:
        bool: True если окна закрыты или не найдены
    """
    
    if verbose:
        print("🔍 Простая обработка всплывающих окон...")
    
    success_count = 0
    
    # 1. ПРОВЕРЯЕМ ОКНА ПРИЛОЖЕНИЯ
    has_app_popup = detect_app_popup_simple(driver)
    if has_app_popup:
        if verbose:
            print("🎯 Всплывающее окно приложения обнаружено...")
        
        buttons = find_not_now_button(driver)
        if buttons:
            if verbose:
                print(f"🔘 Найдено {len(buttons)} кнопок для закрытия приложения")
            
            for i, button_info in enumerate(buttons):
                if verbose:
                    print(f"\n🖱️ Пробуем кнопку #{i+1}:")
                    print(f"   Метод поиска: {button_info['method']}")
                    print(f"   Текст: '{button_info['text']}'")
                
                success = click_button_simple(driver, button_info)
                if success:
                    time.sleep(1)
                    if not detect_app_popup_simple(driver):
                        if verbose:
                            print("✅ Окно приложения закрыто!")
                        success_count += 1
                        break
    
    # 2. ПРОВЕРЯЕМ ОКНА С КУКАМИ
    has_cookie_popup = detect_cookie_popup_simple(driver)
    if has_cookie_popup:
        if verbose:
            print("🍪 Всплывающее окно с куками обнаружено...")
        
        # Используем специальную функцию для поиска кнопок принятия куков
        cookie_buttons = find_cookie_accept_button(driver)
        if cookie_buttons:
            if verbose:
                print(f"🔘 Найдено {len(cookie_buttons)} кнопок принятия куков")
            
            for i, button_info in enumerate(cookie_buttons):
                if verbose:
                    print(f"\n🖱️ Пробуем кнопку принятия куков #{i+1}:")
                    print(f"   Метод поиска: {button_info['method']}")
                    print(f"   Текст: '{button_info['text']}'")
                
                success = click_button_simple(driver, button_info)
                if success:
                    time.sleep(1)
                    if not detect_cookie_popup_simple(driver):
                        if verbose:
                            print("✅ Куки приняты, окно закрыто!")
                        success_count += 1
                        break
                    else:
                        if verbose:
                            print("⚠️ Окно с куками все еще видно, пробуем следующую кнопку...")
        else:
            if verbose:
                print("❌ Кнопки принятия куков не найдены")
    
    # 3. ИТОГОВАЯ ПРОВЕРКА
    if not has_app_popup and not has_cookie_popup:
        if verbose:
            print("✅ Всплывающие окна не найдены")
        return True
    
    if success_count > 0:
        if verbose:
            print(f"✅ Обработано {success_count} всплывающих окон")
        return True
    else:
        if verbose:
            print("❌ Не удалось закрыть всплывающие окна")
        return False

# Экспорт основных функций
__all__ = [
    'handle_popup_simple',
    'find_not_now_button', 
    'detect_app_popup_simple',
    'click_button_simple'
] 