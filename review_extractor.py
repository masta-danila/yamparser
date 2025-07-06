"""
Модуль для извлечения отзывов с Яндекс.Карт
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import random
import re
from datetime import datetime, timedelta
from thread_logger import thread_print

def expand_review_text(driver, review_element):
    """Развернуть текст отзыва, если он обрезан"""
    try:
        # Ищем кнопку "Ещё" или "More" внутри элемента отзыва
        expand_buttons = review_element.find_elements(By.CSS_SELECTOR, "button[type='button']")
        
        for button in expand_buttons:
            if button.is_displayed():
                button_text = button.text.strip().lower()
                # Проверяем различные варианты текста кнопки
                if any(keyword in button_text for keyword in ['ещё', 'more', 'еще', 'показать']):
                    thread_print(f"🔍 Найдена кнопка расширения: '{button.text}'")
                    try:
                        # Используем JavaScript клик для надежности
                        driver.execute_script("arguments[0].click();", button)
                        thread_print("✅ Текст отзыва развернут")
                        # Небольшая пауза для загрузки полного текста
                        time.sleep(0.5)
                        return True
                    except Exception as e:
                        thread_print(f"❌ Ошибка клика по кнопке расширения: {e}")
                        continue
        
        return False  # Кнопка не найдена или не кликнута
    except Exception as e:
        print(f"❌ Ошибка при развертывании текста отзыва: {e}")
        return False

def extract_review_data(driver, review_element):
    """Извлечение данных из одного отзыва"""
    review_data = {
        'author': None,
        'rating': None,
        'text': None,
        'date': None,
        'photos_count': 0,
        'helpful_count': 0
    }
    
    try:
        # Автор отзыва
        try:
            author_element = review_element.find_element(By.CSS_SELECTOR, ".business-review-view__author")
            review_data['author'] = author_element.text.strip()
        except:
            review_data['author'] = "Аноним"
        
        # Рейтинг (количество звезд)
        try:
            rating_element = review_element.find_element(By.CSS_SELECTOR, ".business-rating-badge-view__stars")
            rating_text = rating_element.get_attribute("aria-label") or ""
            # Извлекаем число из текста типа "5 звёзд" или "5 stars"
            rating_match = re.search(r'(\d+)', rating_text)
            if rating_match:
                review_data['rating'] = int(rating_match.group(1))
        except:
            review_data['rating'] = None
        
        # Развертываем текст отзыва если он обрезан
        expand_review_text(driver, review_element)
        
        # Текст отзыва
        try:
            text_element = review_element.find_element(By.CSS_SELECTOR, ".business-review-view__body-text")
            review_data['text'] = text_element.text.strip()
        except:
            review_data['text'] = ""
        
        # Дата отзыва
        try:
            date_element = review_element.find_element(By.CSS_SELECTOR, ".business-review-view__date")
            review_data['date'] = date_element.text.strip()
        except:
            review_data['date'] = None
        
        # Количество фотографий
        try:
            photo_elements = review_element.find_elements(By.CSS_SELECTOR, ".business-review-view__photo")
            review_data['photos_count'] = len(photo_elements)
        except:
            review_data['photos_count'] = 0
        
        # Количество "полезно"
        try:
            helpful_element = review_element.find_element(By.CSS_SELECTOR, ".business-review-view__helpful-count")
            helpful_text = helpful_element.text.strip()
            helpful_match = re.search(r'(\d+)', helpful_text)
            if helpful_match:
                review_data['helpful_count'] = int(helpful_match.group(1))
        except:
            review_data['helpful_count'] = 0
        
    except Exception as e:
        print(f"❌ Ошибка извлечения данных отзыва: {e}")
    
    return review_data

def find_reviews_on_page(driver):
    """Поиск всех отзывов на текущей странице"""
    try:
        # Основной селектор для отзывов
        review_selector = ".business-review-view"
        
        # Ждем загрузки отзывов
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, review_selector))
            )
        except:
            print("⚠️ Отзывы не найдены в течение 10 секунд")
            return []
        
        # Находим все элементы отзывов
        review_elements = driver.find_elements(By.CSS_SELECTOR, review_selector)
        
        if not review_elements:
            print("❌ Отзывы не найдены на странице")
            return []
        
        print(f"📝 Найдено отзывов на странице: {len(review_elements)}")
        
        reviews = []
        for i, review_element in enumerate(review_elements, 1):
            try:
                print(f"📖 Обрабатываем отзыв {i}/{len(review_elements)}...")
                review_data = extract_review_data(driver, review_element)
                
                if review_data['text'] or review_data['rating']:  # Отзыв должен содержать хотя бы текст или рейтинг
                    reviews.append(review_data)
                    print(f"   ✅ Автор: {review_data['author']}")
                    print(f"   ⭐ Рейтинг: {review_data['rating']}")
                    print(f"   📅 Дата: {review_data['date']}")
                    print(f"   📝 Текст: {review_data['text'][:100]}..." if len(review_data['text']) > 100 else f"   📝 Текст: {review_data['text']}")
                else:
                    print(f"   ⚠️ Отзыв пропущен (нет текста и рейтинга)")
                    
            except Exception as e:
                print(f"   ❌ Ошибка обработки отзыва {i}: {e}")
                continue
        
        print(f"✅ Успешно обработано отзывов: {len(reviews)}")
        return reviews
        
    except Exception as e:
        print(f"❌ Ошибка поиска отзывов на странице: {e}")
        return []

def parse_date_string(date_str):
    """Парсинг строки даты в объект datetime"""
    if not date_str:
        return None
    
    try:
        # Убираем лишние пробелы
        date_str = date_str.strip()
        
        # Относительные даты
        if "сегодня" in date_str.lower() or "today" in date_str.lower():
            return datetime.now().date()
        elif "вчера" in date_str.lower() or "yesterday" in date_str.lower():
            return (datetime.now() - timedelta(days=1)).date()
        elif "позавчера" in date_str.lower():
            return (datetime.now() - timedelta(days=2)).date()
        
        # Относительные даты с числом дней назад
        days_ago_match = re.search(r'(\d+)\s*(?:дней?|день|дня)\s*назад', date_str.lower())
        if days_ago_match:
            days = int(days_ago_match.group(1))
            return (datetime.now() - timedelta(days=days)).date()
        
        # Абсолютные даты в формате "1 января 2023"
        months_ru = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        for month_name, month_num in months_ru.items():
            if month_name in date_str.lower():
                # Ищем день и год
                day_match = re.search(r'(\d{1,2})', date_str)
                year_match = re.search(r'(\d{4})', date_str)
                
                if day_match:
                    day = int(day_match.group(1))
                    year = int(year_match.group(1)) if year_match else datetime.now().year
                    return datetime(year, month_num, day).date()
        
        # Попытка парсинга других форматов
        # Формат "01.01.2023"
        date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if date_match:
            day, month, year = map(int, date_match.groups())
            return datetime(year, month, day).date()
        
        # Формат "2023-01-01"
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if date_match:
            year, month, day = map(int, date_match.groups())
            return datetime(year, month, day).date()
        
        print(f"⚠️ Не удалось распарсить дату: '{date_str}'")
        return None
        
    except Exception as e:
        print(f"❌ Ошибка парсинга даты '{date_str}': {e}")
        return None

def is_review_too_old(review_date_str, max_days_back):
    """Проверка, не слишком ли старый отзыв"""
    if not max_days_back or max_days_back <= 0:
        return False  # Если лимит не установлен, отзыв не слишком старый
    
    review_date = parse_date_string(review_date_str)
    if not review_date:
        return False  # Если дату не удалось распарсить, не отбрасываем отзыв
    
    cutoff_date = datetime.now().date() - timedelta(days=max_days_back)
    is_too_old = review_date < cutoff_date
    
    if is_too_old:
        print(f"⏰ Отзыв от {review_date} слишком старый (лимит: {max_days_back} дней)")
    
    return is_too_old

def load_more_reviews(driver, max_attempts=5):
    """Попытка загрузить больше отзывов через кнопку 'Показать ещё' или прокрутку"""
    attempts = 0
    loaded_more = False
    
    while attempts < max_attempts:
        attempts += 1
        print(f"🔄 Попытка {attempts}/{max_attempts} загрузить больше отзывов...")
        
        try:
            # Сначала пытаемся найти кнопку "Показать ещё"
            show_more_selectors = [
                "button[class*='show-more']",
                "button[class*='load-more']", 
                "button:contains('Показать')",
                "button:contains('ещё')",
                "button:contains('More')"
            ]
            
            button_found = False
            for selector in show_more_selectors:
                try:
                    if ":contains(" in selector:
                        # Для селекторов с :contains используем XPath
                        text = selector.split(":contains('")[1].split("')")[0]
                        xpath = f"//button[contains(text(), '{text}')]"
                        buttons = driver.find_elements(By.XPATH, xpath)
                    else:
                        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            print(f"🔍 Найдена кнопка: '{button.text}'")
                            driver.execute_script("arguments[0].click();", button)
                            print("✅ Кнопка 'Показать ещё' нажата")
                            button_found = True
                            loaded_more = True
                            time.sleep(2)  # Ждем загрузки
                            break
                    
                    if button_found:
                        break
                        
                except Exception as e:
                    continue
            
            if not button_found:
                # Если кнопка не найдена, пробуем прокрутку
                print("🔄 Кнопка не найдена, пробуем прокрутку...")
                last_height = driver.execute_script("return document.body.scrollHeight")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height > last_height:
                    print("✅ Страница прокручена, новый контент загружен")
                    loaded_more = True
                else:
                    print("⚠️ Прокрутка не привела к загрузке нового контента")
                    break
            
        except Exception as e:
            print(f"❌ Ошибка при попытке загрузить больше отзывов: {e}")
            break
    
    return loaded_more 