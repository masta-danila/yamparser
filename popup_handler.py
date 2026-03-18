#!/usr/bin/env python3
"""
Упрощенный обработчик всплывающих окон приложения
Только поиск и клик по кнопке "Не сейчас"
"""

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from thread_logger import thread_print

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
    
    # 0. ПРИОРИТЕТ: Крестик закрытия баннера "Установить Яндекс Карты"
    #    Только внутри Y-A-* с текстом попапа! Крестик карточки — в другом контейнере.
    thread_print("🔍 Приоритетный поиск: крестик баннера «Установить Яндекс Карты»...")
    try:
        banner_close_xpaths = [
            "//*[starts-with(@id, 'Y-A-') and contains(., 'Установить Яндекс Карты')]//*[@aria-label='Закрыть']",
            "//*[starts-with(@id, 'Y-A-') and contains(., 'Выбирайте нужные места')]//*[@aria-label='Закрыть']",
            "//span[@aria-label='Закрыть'][.//svg[@viewBox='0 0 14 14']]",  # Попап 36x36 (fallback)
        ]
        for xpath in banner_close_xpaths:
            buttons = driver.find_elements(By.XPATH, xpath)
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    # Исключаем крестик карточки (SVG 24x24)
                    try:
                        svg = btn.find_element(By.TAG_NAME, "svg")
                        w, h = svg.get_attribute("width"), svg.get_attribute("height")
                        if w == "24" or h == "24":
                            continue  # Это крестик карточки — пропускаем
                    except:
                        pass
                    if not any(b["element"] == btn for b in found_buttons):
                        found_buttons.append({
                            "element": btn,
                            "method": f"Баннер Яндекс.Карт: {xpath[:50]}...",
                            "text": "Закрыть (крестик попапа)",
                            "tag": btn.tag_name,
                            "classes": btn.get_attribute("class") or ""
                        })
                        print(f"   ✅ Найден крестик баннера Яндекс.Карт ({btn.tag_name})")
                    break
            if found_buttons:
                break
    except Exception as e:
        print(f"   ⚠️ Ошибка поиска крестика баннера: {e}")
    
    # 1. ПРИОРИТЕТНЫЙ ПОИСК ПО ID (самый надежный)
    thread_print("🔍 Приоритетный поиск по ID...")
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
    thread_print("🔍 Ищем кнопки по тексту...")
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
    thread_print("🔍 Дополнительный поиск для Яндекс.Карт...")
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
    #      Только внутри баннера попапа (Y-A-* с текстом "Установить")! Крестик карточки — вне баннера.
    print("🔍 Поиск кнопки закрытия по aria-label (только в баннере попапа)...")
    try:
        # Ищем только внутри Y-A-* с текстом попапа — не трогаем крестик карточки
        close_in_popup_xpath = "//*[starts-with(@id, 'Y-A-') and contains(., 'Установить Яндекс Карты')]//*[@aria-label='Закрыть']"
        close_buttons = driver.find_elements(By.XPATH, close_in_popup_xpath)
        for button in close_buttons:
            if button.is_displayed() and button.is_enabled():
                # Доп. проверка: исключаем SVG 24x24 (крестик карточки)
                try:
                    svg = button.find_element(By.TAG_NAME, "svg")
                    if svg.get_attribute("width") == "24" or svg.get_attribute("height") == "24":
                        continue
                except:
                    pass
                if not any(b["element"] == button for b in found_buttons):
                    classes = button.get_attribute("class") or ""
                    found_buttons.append({
                        "element": button,
                        "method": "Aria-label в баннере попапа",
                        "text": "Закрыть (крестик)",
                        "tag": button.tag_name,
                        "classes": classes
                    })
                    print(f"   ✅ Найдена кнопка закрытия в баннере: (крестик) ({button.tag_name})")
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
            # НОВЫЕ СЕЛЕКТОРЫ ДЛЯ БАННЕРА ЯНДЕКС.КАРТ (только "Не сейчас", крестик — через XPath с проверкой текста):
            "a.p1dba9a6a",  # Кнопка "Не сейчас" в баннере приложения
            "[id^='Y-A-'] a",  # Любые ссылки внутри баннера с ID Y-A-*
            # НЕ добавляем span[aria-label='Закрыть'] — найдёт крестик карточки (24x24)!
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
                    # Пропускаем крестик карточки (24x24)
                    if (button.get_attribute("aria-label") or "").strip() == "Закрыть":
                        try:
                            svg = button.find_element(By.TAG_NAME, "svg")
                            if svg.get_attribute("width") == "24" or svg.get_attribute("height") == "24":
                                continue
                        except:
                            pass
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
    
    # Прокручиваем к элементу (для span и overlay-кнопок)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.2)
    except:
        pass
    
    # Метод 1: JavaScript клик (надёжнее для span и overlay)
    try:
        driver.execute_script("arguments[0].click();", element)
        print(f"   ✅ JavaScript клик успешен")
        return True
    except Exception as e:
        print(f"   ❌ JavaScript клик не сработал: {str(e)[:50]}")
    
    # Метод 2: Обычный клик
    try:
        element.click()
        print(f"   ✅ Обычный клик успешен")
        return True
    except Exception as e:
        print(f"   ❌ Обычный клик не сработал: {str(e)[:50]}")
    
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
        "даже без интернета",
        "Выбирайте нужные места в приложении",
        "Установить Яндекс Карты"
    ]
    
    # 1. Поиск баннера "Установить Яндекс Карты" по ID — только если содержит текст попапа!
    #    Карточка организации тоже может иметь Y-A-*, но без этого текста — не кликать её крестик!
    try:
        banners = driver.find_elements(By.CSS_SELECTOR, "[id^='Y-A-']")
        popup_texts = ("Установить Яндекс Карты", "Выбирайте нужные места в приложении")
        for banner in banners:
            if banner.is_displayed():
                try:
                    banner_text = banner.text or ""
                    if any(t in banner_text for t in popup_texts):
                        print(f"🎯 Найден баннер «Установить Яндекс Карты»: ID={banner.get_attribute('id')}")
                        return True
                except:
                    pass
    except:
        pass
    
    # 2. Поиск по тексту индикаторов
    for indicator in popup_indicators:
        try:
            xpath = f"//*[contains(text(), '{indicator}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            if any(elem.is_displayed() for elem in elements):
                print(f"🎯 Найдено всплывающее окно: '{indicator}'")
                return True
        except:
            continue
    
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

def close_2gis_cookie_popup(driver):
    """
    Закрывает попап 2GIS «Мы используем cookies» — клик по крестику.
    """
    try:
        selectors = [
            (By.CSS_SELECTOR, "div._abwj39 div._13xlah4"),  # Крестик в баннере cookies
            (By.CSS_SELECTOR, "div._13xlah4"),
            (By.XPATH, "//div[contains(@class, '_abwj39')]//div[contains(@class, '_13xlah4')]"),
            (By.XPATH, "//div[contains(., 'Мы используем cookies')]/following-sibling::div[.//svg]"),
        ]
        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        el.click()
                        thread_print("✅ Попап cookies 2GIS закрыт")
                        time.sleep(1)
                        return True
            except Exception:
                pass
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка закрытия попапа cookies 2GIS: {e}")
        return False


def close_2gis_app_popup(driver):
    """
    Закрывает попап 2GIS «Выберите где продолжить» — клик по кнопке «Остаться».
    """
    try:
        # Кнопка «Остаться» — остаёмся на веб-версии
        selectors = [
            (By.XPATH, "//button[contains(text(), 'Остаться')]"),
            (By.CSS_SELECTOR, "button._xppdink"),
            (By.XPATH, "//*[contains(@class, '_xppdink') and contains(text(), 'Остаться')]"),
        ]
        for by, selector in selectors:
            try:
                buttons = driver.find_elements(by, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        thread_print("✅ Попап 2GIS закрыт (Остаться)")
                        time.sleep(1)
                        return True
            except Exception:
                pass
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка закрытия попапа 2GIS: {e}")
        return False


def close_google_maps_app_popup(driver):
    """
    Закрывает попап Google Maps «Удобнее пользоваться в приложении» —
    клик по кнопке «Вернуться в браузер».
    """
    try:
        selectors = [
            (By.XPATH, "//button[.//span[contains(text(), 'Вернуться в браузер')]]"),
            (By.XPATH, "//*[contains(text(), 'Вернуться в браузер')]"),
            (By.CSS_SELECTOR, "button.vfi8qf.l6mLne"),
            (By.XPATH, "//div[contains(@class, 'zc8u2b')]//button[contains(@jsaction, 'dismiss_action')]"),
        ]
        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", el)
                        thread_print("✅ Попап Google Maps закрыт (Вернуться в браузер)")
                        time.sleep(1)
                        return True
            except Exception:
                pass
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка закрытия попапа Google Maps: {e}")
        return False


def close_zoon_age_popup(driver):
    """
    Закрывает попап Zoon «Подтверждение возраста» —
    клик по кнопке «Мне исполнилось 18 лет».
    """
    try:
        selectors = [
            (By.XPATH, "//button[contains(text(), 'Мне исполнилось 18 лет')]"),
            (By.XPATH, "//*[contains(text(), 'Мне исполнилось 18 лет')]"),
            (By.CSS_SELECTOR, "button.z-button--primary"),
            (By.CSS_SELECTOR, "div.z-modal-footer button.z-button--primary"),
        ]
        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", el)
                        thread_print("✅ Попап Zoon закрыт (Мне исполнилось 18 лет)")
                        time.sleep(1)
                        return True
            except Exception:
                pass
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка закрытия попапа Zoon: {e}")
        return False


def close_zoon_cookie_popup(driver):
    """
    Закрывает попап Zoon «Мы используем файлы cookies» —
    клик по кнопке закрытия в div.cookie-consent.
    """
    try:
        selectors = [
            (By.CSS_SELECTOR, "div.cookie-consent button"),
            (By.CSS_SELECTOR, "[data-uitest='cookie-consent'] button"),
            (By.XPATH, "//div[contains(@class, 'cookie-consent')]//button"),
        ]
        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", el)
                        thread_print("✅ Попап cookies Zoon закрыт")
                        time.sleep(1)
                        return True
            except Exception:
                pass
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка закрытия попапа cookies Zoon: {e}")
        return False


def click_zoon_reviews_tab(driver):
    """
    Кликает на вкладку «Отзывы» в Zoon — переход к списку отзывов.
    Вызывает RuntimeError, если элемент не найден (критичный элемент, не попап).
    """
    selectors = [
        (By.CSS_SELECTOR, "a[data-id='reviews'][data-type='reviews']"),
        (By.XPATH, "//a[contains(@class, 'js-nav-item') and contains(@data-id, 'reviews')]"),
        (By.XPATH, "//a[contains(@href, '/reviews/') and contains(text(), 'Отзывы')]"),
        (By.XPATH, "//a[contains(., 'Отзывы') and contains(@href, 'reviews')]"),
    ]
    for by, selector in selectors:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", el)
                    thread_print("✅ Вкладка «Отзывы» Zoon открыта")
                    time.sleep(2)
                    return True
        except Exception:
            pass
    raise RuntimeError(
        "Вкладка «Отзывы» не найдена на странице Zoon. "
        "Проверьте структуру страницы или доступность сайта."
    )


# Экспорт основных функций
__all__ = [
    'handle_popup_simple',
    'find_not_now_button',
    'detect_app_popup_simple',
    'click_button_simple',
    'close_2gis_app_popup',
    'close_2gis_cookie_popup',
    'close_google_maps_app_popup',
    'close_zoon_age_popup',
    'close_zoon_cookie_popup',
    'click_zoon_reviews_tab',
] 