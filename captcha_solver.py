from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import stat
import time
import requests
import base64
from urllib.parse import urljoin, urlparse
import json
import uuid
import shutil
import random

def setup_driver(device_type="iPhone 13"):
    """Настройка мобильного драйвера для CAPTCHA"""
    print(f"📱🚀 Настройка мобильного Selenium драйвера ({device_type})...")
    
    # Настройки браузера
    options = Options()
    # options.add_argument("--headless")  # Оставляем видимым для CAPTCHA
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Создаем папку для мобильного профиля
    user_data_dir = os.path.join(os.getcwd(), "mobile_captcha_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Мобильные устройства
    mobile_devices = {
        "iPhone 13": {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        },
        "iPhone SE": {
            "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        },
        "Samsung Galaxy S21": {
            "deviceMetrics": {"width": 384, "height": 854, "pixelRatio": 2.75},
            "userAgent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        },
        "iPad": {
            "deviceMetrics": {"width": 768, "height": 1024, "pixelRatio": 2.0},
            "userAgent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }
    }
    
    if device_type in mobile_devices:
        device = mobile_devices[device_type]
        
        # Настройка эмуляции мобильного устройства
        mobile_emulation = {
            "deviceMetrics": device["deviceMetrics"],
            "userAgent": device["userAgent"]
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        print(f"📱 Устройство: {device_type}")
        print(f"📏 Разрешение: {device['deviceMetrics']['width']}x{device['deviceMetrics']['height']}")
        print(f"🔍 Pixel Ratio: {device['deviceMetrics']['pixelRatio']}")
    
    print(f"📁 Мобильный профиль: {user_data_dir}")
    
    # Получаем и настраиваем драйвер
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

def setup_driver_with_new_profile(device_type="iPhone 13"):
    """Настройка мобильного драйвера с НОВЫМ уникальным профилем для тестирования CAPTCHA"""
    print(f"🆕📱 Создаем НОВЫЙ профиль для тестирования CAPTCHA ({device_type})...")
    
    # Создаем уникальный ID для профиля
    profile_id = str(uuid.uuid4())[:8]
    print(f"🆔 ID профиля: {profile_id}")
    
    # Настройки браузера
    options = Options()
    # options.add_argument("--headless")  # Оставляем видимым для CAPTCHA
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Создаем папку для НОВОГО уникального профиля
    user_data_dir = os.path.join(os.getcwd(), f"captcha_test_profile_{profile_id}")
    
    # Удаляем папку если она уже существует (очистка)
    if os.path.exists(user_data_dir):
        print(f"🗑️ Удаляем старый профиль...")
        shutil.rmtree(user_data_dir)
    
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Дополнительные параметры для "свежего" браузера
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Мобильные устройства
    mobile_devices = {
        "iPhone 13": {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        },
        "iPhone SE": {
            "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        },
        "Samsung Galaxy S21": {
            "deviceMetrics": {"width": 384, "height": 854, "pixelRatio": 2.75},
            "userAgent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        },
        "iPad": {
            "deviceMetrics": {"width": 768, "height": 1024, "pixelRatio": 2.0},
            "userAgent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }
    }
    
    if device_type in mobile_devices:
        device = mobile_devices[device_type]
        
        # Настройка эмуляции мобильного устройства
        mobile_emulation = {
            "deviceMetrics": device["deviceMetrics"],
            "userAgent": device["userAgent"]
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        print(f"📱 Устройство: {device_type}")
        print(f"📏 Разрешение: {device['deviceMetrics']['width']}x{device['deviceMetrics']['height']}")
        print(f"🔍 Pixel Ratio: {device['deviceMetrics']['pixelRatio']}")
    
    print(f"📁 НОВЫЙ профиль: {user_data_dir}")
    
    # Получаем и настраиваем драйвер
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
        
        # Убираем webdriver флаги
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    else:
        raise Exception("ChromeDriver не найден!")

def detect_captcha(driver):
    """Обнаружение CAPTCHA на мобильной странице"""
    print("📱🔍 Проверяем наличие мобильной CAPTCHA...")
    
    # Мобильная прокрутка для поиска CAPTCHA
    print("📱 Прокручиваем мобильную страницу...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")
    
    # Различные селекторы для мобильной CAPTCHA Яндекса
    captcha_selectors = [
        # SmartCaptcha мобильные
        "iframe[src*='captcha']",
        "iframe[title*='captcha']",
        ".captcha",
        "[class*='captcha']",
        "[id*='captcha']",
        
        # Мобильные checkbox "Я не робот"
        "input[type='checkbox']",
        ".checkbox",
        "[role='checkbox']",
        ".mobile-checkbox",
        ".touch-checkbox",
        
        # Мобильные текстовые селекторы CAPTCHA
        "//*[contains(text(), 'Вы не робот')]",
        "//*[contains(text(), 'не робот')]",
        "//*[contains(text(), 'проверка')]",
        "//*[contains(text(), 'captcha')]",
        "//*[contains(text(), 'Подтвердите')]",
        "//*[contains(text(), 'человек')]",
        
        # Мобильные специфичные селекторы
        ".mobile-captcha",
        ".touch-captcha",
        "[data-mobile-captcha]",
        ".captcha-mobile"
    ]
    
    for selector in captcha_selectors:
        try:
            if selector.startswith("//"):
                # XPath селектор
                elements = driver.find_elements(By.XPATH, selector)
            else:
                # CSS селектор
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            if elements:
                element = elements[0]
                print(f"📱🤖 Мобильная CAPTCHA обнаружена! Селектор: {selector}")
                print(f"   📱 Размер элемента: {element.size}")
                print(f"   📱 Позиция: {element.location}")
                return True, element
        except:
            continue
    
    # Проверяем URL на наличие captcha
    if "captcha" in driver.current_url.lower():
        print("📱🤖 Мобильная CAPTCHA обнаружена в URL!")
        return True, None
    
    # Проверяем заголовок страницы
    title = driver.title.lower()
    if any(word in title for word in ["captcha", "не робот", "проверка", "showcaptcha"]):
        print("📱🤖 Мобильная CAPTCHA обнаружена в заголовке!")
        return True, None
    
    return False, None

def download_captcha_image(driver, image_element, filename="captcha_image.png"):
    """Скачивание изображения CAPTCHA"""
    try:
        print(f"📱📥 Скачиваем изображение CAPTCHA...")
        
        # Способ 1: Получаем src изображения
        image_src = image_element.get_attribute("src")
        if image_src:
            print(f"📱🔗 URL изображения: {image_src}")
            
            # Проверяем, является ли это data URL (base64)
            if image_src.startswith("data:image/"):
                print("📱💾 Обнаружено base64 изображение")
                # Извлекаем base64 данные
                header, data = image_src.split(',', 1)
                image_data = base64.b64decode(data)
                
                with open(filename, 'wb') as f:
                    f.write(image_data)
                print(f"✅📱 Base64 изображение сохранено: {filename}")
                return True
                
            else:
                # Обычный URL - скачиваем через requests
                print("📱🌐 Скачиваем изображение по URL...")
                
                # Получаем куки из Selenium для requests
                selenium_cookies = driver.get_cookies()
                cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
                
                # Получаем User-Agent из браузера
                user_agent = driver.execute_script("return navigator.userAgent;")
                
                headers = {
                    'User-Agent': user_agent,
                    'Referer': driver.current_url,
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                }
                
                # Если URL относительный, делаем его абсолютным
                if not image_src.startswith(('http://', 'https://')):
                    image_src = urljoin(driver.current_url, image_src)
                
                response = requests.get(image_src, cookies=cookies_dict, headers=headers, timeout=10)
                response.raise_for_status()
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅📱 Изображение скачано: {filename}")
                return True
                
        # Способ 2: Скриншот элемента (если src недоступен)
        print("📱📸 Делаем скриншот элемента изображения...")
        image_element.screenshot(filename)
        print(f"✅📱 Скриншот элемента сохранен: {filename}")
        return True
        
    except Exception as e:
        print(f"❌📱 Ошибка скачивания изображения: {e}")
        return False

def download_canvas_as_image(driver, canvas_element, filename="canvas_captcha.png"):
    """Скачивание canvas как изображение"""
    try:
        print(f"📱🎨 Конвертируем canvas в изображение...")
        
        # Получаем данные canvas как base64
        canvas_data = driver.execute_script("""
            var canvas = arguments[0];
            return canvas.toDataURL('image/png');
        """, canvas_element)
        
        if canvas_data and canvas_data.startswith("data:image/"):
            # Извлекаем base64 данные
            header, data = canvas_data.split(',', 1)
            image_data = base64.b64decode(data)
            
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"✅📱 Canvas сохранен как изображение: {filename}")
            return True
        else:
            print("❌📱 Не удалось получить данные canvas")
            return False
            
    except Exception as e:
        print(f"❌📱 Ошибка конвертации canvas: {e}")
        return False

def get_image_as_base64(driver, element):
    """Получение изображения в формате base64"""
    try:
        # Проверяем тип элемента
        tag_name = element.tag_name.lower()
        
        if tag_name == "canvas":
            # Для canvas используем toDataURL
            print("📱🎨 Получаем canvas как base64...")
            canvas_data = driver.execute_script("""
                var canvas = arguments[0];
                return canvas.toDataURL('image/png');
            """, element)
            
            if canvas_data and canvas_data.startswith("data:image/"):
                # Возвращаем только base64 часть без заголовка
                header, data = canvas_data.split(',', 1)
                return data
                
        elif tag_name == "img":
            # Для img элементов
            src = element.get_attribute("src")
            
            if src and src.startswith("data:image/"):
                # Уже base64
                print("📱💾 Изображение уже в base64 формате")
                header, data = src.split(',', 1)
                return data
            elif src:
                # Скачиваем и конвертируем в base64
                print("📱🌐 Скачиваем изображение для base64...")
                
                # Получаем куки и заголовки
                selenium_cookies = driver.get_cookies()
                cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
                user_agent = driver.execute_script("return navigator.userAgent;")
                
                headers = {
                    'User-Agent': user_agent,
                    'Referer': driver.current_url,
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                }
                
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(driver.current_url, src)
                
                response = requests.get(src, cookies=cookies_dict, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Конвертируем в base64
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return image_base64
            else:
                # Делаем скриншот элемента и конвертируем
                print("📱📸 Делаем скриншот элемента для base64...")
                screenshot_data = element.screenshot_as_png
                image_base64 = base64.b64encode(screenshot_data).decode('utf-8')
                return image_base64
        
        return None
        
    except Exception as e:
        print(f"❌📱 Ошибка получения base64: {e}")
        return None

def collect_captcha_images_base64(driver):
    """Сбор всех изображений CAPTCHA в формате base64"""
    print("📱🔍 Собираем изображения CAPTCHA в base64 формате...")
    
    captcha_data = {
        "timestamp": time.time(),
        "url": driver.current_url,
        "title": driver.title,
        "images": [],
        "canvases": [],
        "iframes": []
    }
    
    # Селекторы для изображений
    image_selectors = [
        "img[src*='captcha']", "img[alt*='captcha']", "img[class*='captcha']", "img[id*='captcha']",
        ".smart-captcha img", ".captcha-image img", ".captcha-container img",
        ".smart-captcha-image img", ".captcha-challenge img", ".captcha img", "[data-captcha] img",
        ".mobile-captcha img", ".touch-captcha img"
    ]
    
    # Canvas селекторы
    canvas_selectors = [
        "canvas[class*='captcha']", "canvas[id*='captcha']",
        ".smart-captcha canvas", ".captcha-image canvas", ".captcha-container canvas"
    ]
    
    # 1. Собираем обычные изображения
    for selector in image_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for i, element in enumerate(elements):
                if element.is_displayed():
                    print(f"📱🖼️ Обрабатываем изображение: {selector}")
                    
                    base64_data = get_image_as_base64(driver, element)
                    if base64_data:
                        image_info = {
                            "selector": selector,
                            "index": i,
                            "size": element.size,
                            "location": element.location,
                            "src": element.get_attribute("src"),
                            "alt": element.get_attribute("alt"),
                            "base64": base64_data
                        }
                        captcha_data["images"].append(image_info)
                        print(f"✅📱 Изображение добавлено в base64 ({len(base64_data)} символов)")
                        
        except Exception as e:
            print(f"❌📱 Ошибка с изображением {selector}: {e}")
    
    # 2. Собираем Canvas элементы
    for selector in canvas_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for i, element in enumerate(elements):
                if element.is_displayed():
                    print(f"📱🎨 Обрабатываем canvas: {selector}")
                    
                    base64_data = get_image_as_base64(driver, element)
                    if base64_data:
                        canvas_info = {
                            "selector": selector,
                            "index": i,
                            "size": element.size,
                            "location": element.location,
                            "base64": base64_data
                        }
                        captcha_data["canvases"].append(canvas_info)
                        print(f"✅📱 Canvas добавлен в base64 ({len(base64_data)} символов)")
                        
        except Exception as e:
            print(f"❌📱 Ошибка с canvas {selector}: {e}")
    
    # 3. Собираем из iframe
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='captcha'], iframe[title*='captcha']")
        for iframe_index, iframe in enumerate(iframes):
            try:
                iframe_src = iframe.get_attribute('src')
                print(f"📱🔍 Обрабатываем iframe: {iframe_src}")
                
                driver.switch_to.frame(iframe)
                iframe_data = {
                    "src": iframe_src,
                    "index": iframe_index,
                    "images": [],
                    "canvases": []
                }
                
                # Изображения в iframe
                images = driver.find_elements(By.TAG_NAME, "img")
                for img_index, img in enumerate(images):
                    if img.is_displayed():
                        base64_data = get_image_as_base64(driver, img)
                        if base64_data:
                            img_info = {
                                "index": img_index,
                                "size": img.size,
                                "location": img.location,
                                "src": img.get_attribute("src"),
                                "base64": base64_data
                            }
                            iframe_data["images"].append(img_info)
                
                # Canvas в iframe
                canvases = driver.find_elements(By.TAG_NAME, "canvas")
                for canvas_index, canvas in enumerate(canvases):
                    if canvas.is_displayed():
                        base64_data = get_image_as_base64(driver, canvas)
                        if base64_data:
                            canvas_info = {
                                "index": canvas_index,
                                "size": canvas.size,
                                "location": canvas.location,
                                "base64": base64_data
                            }
                            iframe_data["canvases"].append(canvas_info)
                
                if iframe_data["images"] or iframe_data["canvases"]:
                    captcha_data["iframes"].append(iframe_data)
                
                driver.switch_to.default_content()
                
            except Exception as e:
                print(f"❌📱 Ошибка в iframe: {e}")
                driver.switch_to.default_content()
    
    except Exception as e:
        print(f"❌📱 Ошибка поиска iframe: {e}")
    
    return captcha_data

def save_captcha_base64_data(captcha_data, filename="captcha_base64_data.json"):
    """Сохранение base64 данных в JSON файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(captcha_data, f, ensure_ascii=False, indent=2)
        
        total_images = len(captcha_data["images"]) + len(captcha_data["canvases"])
        for iframe in captcha_data["iframes"]:
            total_images += len(iframe["images"]) + len(iframe["canvases"])
        
        print(f"✅📱 Base64 данные сохранены: {filename}")
        print(f"📊📱 Всего изображений: {total_images}")
        return True
        
    except Exception as e:
        print(f"❌📱 Ошибка сохранения base64: {e}")
        return False

def print_base64_summary(captcha_data):
    """Вывод краткой информации о собранных base64 данных"""
    print("\n📱📊 Сводка по base64 данным:")
    print(f"🌐 URL: {captcha_data['url']}")
    print(f"📄 Заголовок: {captcha_data['title']}")
    print(f"🖼️ Обычных изображений: {len(captcha_data['images'])}")
    print(f"🎨 Canvas элементов: {len(captcha_data['canvases'])}")
    print(f"🔲 iframe элементов: {len(captcha_data['iframes'])}")
    
    if captcha_data["images"]:
        print("\n📱🖼️ Детали изображений:")
        for i, img in enumerate(captcha_data["images"], 1):
            print(f"   {i}. Селектор: {img['selector']}")
            print(f"      Размер: {img['size']}")
            print(f"      Base64 длина: {len(img['base64'])} символов")
            if img['src']:
                print(f"      Источник: {img['src'][:50]}...")
    
    if captcha_data["canvases"]:
        print("\n📱🎨 Детали Canvas:")
        for i, canvas in enumerate(captcha_data["canvases"], 1):
            print(f"   {i}. Селектор: {canvas['selector']}")
            print(f"      Размер: {canvas['size']}")
            print(f"      Base64 длина: {len(canvas['base64'])} символов")
    
    if captcha_data["iframes"]:
        print(f"\n📱🔲 Детали iframe:")
        for i, iframe in enumerate(captcha_data["iframes"], 1):
            print(f"   {i}. Источник: {iframe['src']}")
            print(f"      Изображений: {len(iframe['images'])}")
            print(f"      Canvas: {len(iframe['canvases'])}")

def find_and_download_captcha_images(driver):
    """Поиск и скачивание всех изображений CAPTCHA"""
    print("📱🔍 Ищем изображения SmartCaptcha...")
    
    # Различные селекторы для изображений CAPTCHA
    image_selectors = [
        # SmartCaptcha изображения
        "img[src*='captcha']",
        "img[alt*='captcha']",
        "img[class*='captcha']",
        "img[id*='captcha']",
        
        # Yandex SmartCaptcha специфичные
        ".smart-captcha img",
        ".captcha-image img",
        ".captcha-container img",
        ".smart-captcha-image img",
        ".captcha-challenge img",
        
        # Общие изображения в CAPTCHA контейнерах
        ".captcha img",
        "[data-captcha] img",
        
        # Дополнительные мобильные селекторы
        ".mobile-captcha img",
        ".touch-captcha img"
    ]
    
    # Canvas селекторы (обрабатываются отдельно)
    canvas_selectors = [
        "canvas[class*='captcha']",
        "canvas[id*='captcha']",
        ".smart-captcha canvas",
        ".captcha-image canvas",
        ".captcha-container canvas"
    ]
    
    downloaded_count = 0
    
    # 1. Поиск обычных изображений
    for selector in image_selectors:
        try:
            print(f"📱🔍 Проверяем изображения: {selector}")
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if element.is_displayed():
                    print(f"✅📱 Найдено изображение CAPTCHA: {selector}")
                    print(f"   📱 Размер: {element.size}")
                    print(f"   📱 Позиция: {element.location}")
                    
                    # Прокручиваем к изображению
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(1)
                    
                    filename = f"captcha_image_{downloaded_count + 1}.png"
                    if download_captcha_image(driver, element, filename):
                        downloaded_count += 1
                        
        except Exception as e:
            print(f"❌📱 Ошибка с изображением {selector}: {e}")
            continue
    
    # 2. Поиск Canvas элементов
    for selector in canvas_selectors:
        try:
            print(f"📱🔍 Проверяем canvas: {selector}")
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if element.is_displayed():
                    print(f"✅📱 Найден canvas CAPTCHA: {selector}")
                    print(f"   📱 Размер: {element.size}")
                    print(f"   📱 Позиция: {element.location}")
                    
                    # Прокручиваем к canvas
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(1)
                    
                    filename = f"captcha_canvas_{downloaded_count + 1}.png"
                    if download_canvas_as_image(driver, element, filename):
                        downloaded_count += 1
                        
        except Exception as e:
            print(f"❌📱 Ошибка с canvas {selector}: {e}")
            continue
    
    # 3. Поиск в iframe
    try:
        print("📱🔍 Проверяем iframe с CAPTCHA...")
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='captcha'], iframe[title*='captcha']")
        
        for iframe in iframes:
            try:
                print(f"📱🔍 Переключаемся в iframe: {iframe.get_attribute('src')}")
                driver.switch_to.frame(iframe)
                
                # Ищем изображения в iframe
                images = driver.find_elements(By.TAG_NAME, "img")
                for img in images:
                    if img.is_displayed():
                        filename = f"captcha_iframe_image_{downloaded_count + 1}.png"
                        if download_captcha_image(driver, img, filename):
                            downloaded_count += 1
                
                # Ищем canvas в iframe
                canvases = driver.find_elements(By.TAG_NAME, "canvas")
                for canvas in canvases:
                    if canvas.is_displayed():
                        filename = f"captcha_iframe_canvas_{downloaded_count + 1}.png"
                        if download_canvas_as_image(driver, canvas, filename):
                            downloaded_count += 1
                
                driver.switch_to.default_content()
                
            except Exception as e:
                print(f"❌📱 Ошибка в iframe: {e}")
                driver.switch_to.default_content()
                continue
                
    except Exception as e:
        print(f"❌📱 Ошибка поиска iframe: {e}")
    
    # 4. Поиск по любым изображениям на странице (если ничего не найдено)
    if downloaded_count == 0:
        print("📱🔍 Ищем любые изображения на странице...")
        try:
            all_images = driver.find_elements(By.TAG_NAME, "img")
            for i, img in enumerate(all_images):
                if img.is_displayed():
                    src = img.get_attribute("src") or ""
                    alt = img.get_attribute("alt") or ""
                    
                    # Проверяем, может ли это быть CAPTCHA
                    if any(keyword in (src + alt).lower() for keyword in ['captcha', 'challenge', 'verify', 'robot']):
                        print(f"✅📱 Найдено потенциальное изображение CAPTCHA: {src[:50]}...")
                        filename = f"potential_captcha_{downloaded_count + 1}.png"
                        if download_captcha_image(driver, img, filename):
                            downloaded_count += 1
                            
        except Exception as e:
            print(f"❌📱 Ошибка поиска всех изображений: {e}")
    
    print(f"📱📥 Всего скачано изображений CAPTCHA: {downloaded_count}")
    return downloaded_count > 0

def solve_captcha(driver, captcha_element=None):
    """Попытка решения мобильной CAPTCHA"""
    print("📱🎯 Пытаемся решить мобильную CAPTCHA...")
    
    # Делаем скриншот для анализа
    driver.save_screenshot("mobile_captcha_detected.png")
    print("📸📱 Скриншот мобильной CAPTCHA: mobile_captcha_detected.png")
    
    # Сначала ищем уже существующие изображения CAPTCHA
    print("📱🔍 Ищем существующие изображения CAPTCHA...")
    find_and_download_captcha_images(driver)
    
    # Собираем начальные base64 данные
    print("📱💾 Собираем начальные base64 данные...")
    initial_captcha_data = collect_captcha_images_base64(driver)
    save_captcha_base64_data(initial_captcha_data, "captcha_initial_state.json")
    print_base64_summary(initial_captcha_data)
    
    # Стратегия 1: Мобильные чекбоксы "Я не робот"
    mobile_checkbox_selectors = [
        "input[type='checkbox']",
        ".checkbox input",
        "[role='checkbox']",
        ".captcha-checkbox",
        ".smart-captcha-checkbox",
        "span.checkbox__control",
        ".checkbox__box",
        ".mobile-checkbox",
        ".touch-checkbox",
        ".captcha-mobile input"
    ]
    
    for selector in mobile_checkbox_selectors:
        try:
            print(f"📱🔍 Ищем мобильный чекбокс: {selector}")
            checkboxes = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for checkbox in checkboxes:
                if checkbox.is_displayed() and checkbox.is_enabled():
                    print("✅📱 Найден активный мобильный чекбокс!")
                    print(f"   📱 Размер: {checkbox.size}")
                    print(f"   📱 Позиция: {checkbox.location}")
                    
                    # Мобильная прокрутка к элементу
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", checkbox)
                    time.sleep(2)
                    
                    # Мобильный клик через JavaScript (надежнее)
                    try:
                        driver.execute_script("arguments[0].click();", checkbox)
                        print("🖱️📱 JavaScript клик по мобильному чекбоксу!")
                    except:
                        checkbox.click()
                        print("🖱️📱 Обычный клик по мобильному чекбоксу!")
                    
                    # Больше времени для мобильной анимации
                    time.sleep(4)
                    
                    # После клика ищем и скачиваем появившиеся изображения CAPTCHA
                    print("📱🔍 Ищем изображения после клика на 'Я не робот'...")
                    find_and_download_captcha_images(driver)
                    
                    # Собираем изображения в base64 формате
                    print("📱💾 Собираем base64 данные...")
                    captcha_base64_data = collect_captcha_images_base64(driver)
                    save_captcha_base64_data(captcha_base64_data, "captcha_after_checkbox_click.json")
                    print_base64_summary(captcha_base64_data)
                    
                    # Дополнительное ожидание для загрузки изображений
                    time.sleep(3)
                    
                    # Проверяем результат
                    if not detect_captcha(driver)[0]:
                        print("🎉📱 Мобильная CAPTCHA решена!")
                        return True
                    else:
                        print("📱🤖 Появились дополнительные задания CAPTCHA")
                        # Еще раз ищем изображения после дополнительного ожидания
                        find_and_download_captcha_images(driver)
                    
        except Exception as e:
            print(f"❌📱 Ошибка с мобильным селектором {selector}: {e}")
            continue
    
    # Стратегия 2: Мобильные текстовые элементы
    mobile_text_selectors = [
        "//*[contains(text(), 'Я не робот')]",
        "//*[contains(text(), 'не робот')]",
        "//*[contains(text(), 'I am not a robot')]",
        "//*[contains(text(), 'Подтвердите')]",
        "//*[contains(text(), 'человек')]"
    ]
    
    for selector in mobile_text_selectors:
        try:
            print(f"📱🔍 Ищем по мобильному тексту: {selector}")
            elements = driver.find_elements(By.XPATH, selector)
            
            for element in elements:
                if element.is_displayed():
                    print("✅📱 Найден мобильный элемент с текстом!")
                    
                    # Мобильная прокрутка и клик
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(2)
                    
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        print("🖱️📱 JavaScript клик по мобильному тексту!")
                    except:
                        element.click()
                        print("🖱️📱 Обычный клик по мобильному тексту!")
                    
                    time.sleep(4)
                    
                    # Ищем изображения после клика по тексту
                    print("📱🔍 Ищем изображения после клика по тексту...")
                    find_and_download_captcha_images(driver)
                    time.sleep(2)
                    
                    if not detect_captcha(driver)[0]:
                        print("🎉📱 Мобильная CAPTCHA решена через текст!")
                        return True
                        
        except Exception as e:
            print(f"❌📱 Ошибка с мобильным текстовым селектором: {e}")
            continue
    
    # Стратегия 3: Мобильные iframe с CAPTCHA
    try:
        print("📱🔍 Ищем мобильные iframe с CAPTCHA...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if "captcha" in src.lower():
                print("✅📱 Найден мобильный iframe с CAPTCHA!")
                
                # Переключаемся в iframe
                driver.switch_to.frame(iframe)
                
                # Ищем чекбокс внутри мобильного iframe
                try:
                    checkbox = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox'], [role='checkbox']"))
                    )
                    
                    # Мобильный клик в iframe
                    driver.execute_script("arguments[0].click();", checkbox)
                    print("🖱️📱 Клик в мобильном iframe выполнен!")
                    
                    time.sleep(4)
                    
                    # Возвращаемся в основной документ
                    driver.switch_to.default_content()
                    
                    # Ищем изображения после клика в iframe
                    print("📱🔍 Ищем изображения после клика в iframe...")
                    find_and_download_captcha_images(driver)
                    time.sleep(2)
                    
                    if not detect_captcha(driver)[0]:
                        print("🎉📱 Мобильная CAPTCHA решена через iframe!")
                        return True
                        
                except:
                    driver.switch_to.default_content()
                    
    except Exception as e:
        print(f"❌📱 Ошибка с мобильным iframe: {e}")
    
    print("❌📱 Не удалось автоматически решить мобильную CAPTCHA")
    return False

def test_captcha_on_reviews_page(driver, reviews_url):
    """Тест решения CAPTCHA на странице отзывов"""
    print(f"🗺️📱 Открываем страницу отзывов...")
    print(f"🔗 URL: {reviews_url}")
    driver.get(reviews_url)
    
    # Ждем загрузки страницы
    time.sleep(5)
    
    # Проверяем на мобильную CAPTCHA
    has_captcha, captcha_element = detect_captcha(driver)
    
    if has_captcha:
        print("🚨📱 Обнаружена CAPTCHA! Пытаемся решить...")
        
        # Пытаемся решить CAPTCHA
        if solve_captcha(driver, captcha_element):
            print("🎉📱 CAPTCHA успешно решена!")
            
            # Ждем перенаправления
            time.sleep(5)
            
            # Делаем финальный скриншот
            driver.save_screenshot("captcha_solved_success.png")
            print("📸📱 Скриншот после решения: captcha_solved_success.png")
            return True
            
        else:
            print("❌📱 Не удалось автоматически решить CAPTCHA")
            print("🤔📱 Попробуйте решить вручную...")
            return False
    else:
        print("✅📱 CAPTCHA не обнаружена! Страница загружена успешно.")
        driver.save_screenshot("no_captcha_detected.png")
        print("📸📱 Скриншот страницы: no_captcha_detected.png")
        return True

def demo_base64_usage():
    """Демонстрация использования base64 данных"""
    print("📱💡 Демонстрация работы с base64 данными:")
    
    # Проверяем, есть ли сохраненные данные
    json_files = [
        "captcha_initial_state.json",
        "captcha_after_checkbox_click.json"
    ]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            print(f"\n📱📄 Анализируем файл: {json_file}")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"🌐 URL: {data['url']}")
                print(f"📊 Изображений: {len(data['images'])}")
                print(f"🎨 Canvas: {len(data['canvases'])}")
                
                # Показываем пример использования base64
                if data['images']:
                    first_image = data['images'][0]
                    base64_data = first_image['base64']
                    
                    print(f"\n📱💾 Пример base64 данных:")
                    print(f"   Длина: {len(base64_data)} символов")
                    print(f"   Первые 50 символов: {base64_data[:50]}...")
                    print(f"   Последние 50 символов: ...{base64_data[-50:]}")
                    
                    # Сохраняем как отдельное изображение для проверки
                    try:
                        image_data = base64.b64decode(base64_data)
                        test_filename = f"test_base64_image_from_{json_file.replace('.json', '.png')}"
                        with open(test_filename, 'wb') as f:
                            f.write(image_data)
                        print(f"   ✅ Тестовое изображение создано: {test_filename}")
                    except Exception as e:
                        print(f"   ❌ Ошибка создания тестового изображения: {e}")
                
                if data['canvases']:
                    first_canvas = data['canvases'][0]
                    base64_data = first_canvas['base64']
                    
                    print(f"\n📱🎨 Пример Canvas base64:")
                    print(f"   Длина: {len(base64_data)} символов")
                    print(f"   Размер canvas: {first_canvas['size']}")
                    
                    # Сохраняем canvas как изображение
                    try:
                        image_data = base64.b64decode(base64_data)
                        test_filename = f"test_canvas_from_{json_file.replace('.json', '.png')}"
                        with open(test_filename, 'wb') as f:
                            f.write(image_data)
                        print(f"   ✅ Canvas изображение создано: {test_filename}")
                    except Exception as e:
                        print(f"   ❌ Ошибка создания canvas изображения: {e}")
                
            except Exception as e:
                print(f"❌ Ошибка чтения {json_file}: {e}")
        else:
            print(f"📱❓ Файл {json_file} не найден")
    
    print(f"\n📱🚀 Как использовать base64 данные:")
    print("1. 📤 Отправка через API:")
    print("   POST /api/solve-captcha")
    print("   {\"image\": \"base64_data_here\"}")
    
    print("\n2. 🔄 Конвертация обратно в изображение:")
    print("   import base64")
    print("   image_data = base64.b64decode(base64_string)")
    print("   with open('image.png', 'wb') as f:")
    print("       f.write(image_data)")
    
    print("\n3. 🌐 Использование в HTML:")
    print("   <img src=\"data:image/png;base64,{base64_data}\" />")
    
    print("\n4. 🤖 Отправка в AI сервисы:")
    print("   - OpenAI Vision API")
    print("   - Google Cloud Vision")
    print("   - Yandex Vision API")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo-base64":
        demo_base64_usage()
    else:
        # Тестовый прогон решения CAPTCHA на странице отзывов
        driver = None
        
        # URL страницы с отзывами (тот же, что в get_reviews.py)
        reviews_url = "https://yandex.ru/maps/org/advert_pro/168085394903/reviews/?ll=37.620510%2C55.627661&tab=reviews&z=17.57"
        
        # Выбор мобильного устройства (расширенный список)
        devices = [
            "iPhone 13", "iPhone SE", "iPhone 12", "iPhone 14 Pro",
            "Samsung Galaxy S21", "Samsung Galaxy S22", 
            "Pixel 6", "OnePlus 9", "iPad", "iPad Pro"
        ]
        print("🧪 ТЕСТ РЕШЕНИЯ CAPTCHA НА СТРАНИЦЕ ОТЗЫВОВ")
        print("=" * 50)
        print("📱 Доступные мобильные устройства:")
        for i, device in enumerate(devices, 1):
            print(f"   {i}. {device}")
        print("   5. 🎲 Случайное устройство")
        
        try:
            choice = input("\nВыберите устройство (1-5) или нажмите Enter для случайного: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= 4:
                selected_device = devices[int(choice) - 1]
                print(f"✅ Выбрано: {selected_device}")
            elif choice == "5":
                selected_device = random.choice(devices)
                print(f"🎲 Случайно выбрано: {selected_device}")
            else:
                # По умолчанию случайное устройство
                selected_device = random.choice(devices)
                print(f"🎲 Случайно выбрано по умолчанию: {selected_device}")
        except:
            selected_device = random.choice(devices)
            print(f"🎲 Случайно выбрано (ошибка ввода): {selected_device}")
        
        try:
            # Настройка мобильного драйвера с НОВЫМ профилем
            driver = setup_driver_with_new_profile(selected_device)
            print("✅📱 Мобильный драйвер с новым профилем запущен!")
            
            # Тестируем решение CAPTCHA на странице отзывов
            success = test_captcha_on_reviews_page(driver, reviews_url)
            
            if success:
                print(f"🌐📱 Финальный URL: {driver.current_url}")
                print(f"📄📱 Заголовок: {driver.title}")
                
                # Дополнительный тест взаимодействия
                print("\n📱 Тестируем взаимодействие...")
                driver.execute_script("window.scrollTo(0, 300);")
                time.sleep(2)
                driver.save_screenshot("interaction_test.png")
                print("📸📱 Скриншот взаимодействия: interaction_test.png")
            
            # Ожидание пользователя
            input("\n⏸️📱 Нажмите Enter, чтобы закрыть браузер...")
            
        except Exception as e:
            print(f"❌📱 Ошибка тестирования: {e}")
            
        finally:
            if driver:
                driver.quit()
                print("🔒📱 Браузер закрыт.") 