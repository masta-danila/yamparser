#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import stat

def setup_driver():
    """Настройка драйвера"""
    print("🚀 Настройка Selenium драйвера...")
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Создаем папку для профиля
    user_data_dir = os.path.join(os.getcwd(), "reviews_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
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

def analyze_review_dates(url):
    """Анализ дат отзывов на странице"""
    driver = setup_driver()
    
    try:
        print(f"🌐 Переходим на страницу: {url}")
        driver.get(url)
        time.sleep(5)
        
        print("📅 Анализируем даты отзывов...")
        
        # Находим все контейнеры отзывов
        review_containers = driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
        print(f"📝 Найдено отзывов: {len(review_containers)}")
        
        if not review_containers:
            print("❌ Отзывы не найдены!")
            return
        
        print("\n🔍 АНАЛИЗ ДАТ:")
        print("=" * 80)
        
        date_selectors = [
            ".business-review-view__date",
            ".review-date", 
            "[class*='date']",
            "time"
        ]
        
        for i, container in enumerate(review_containers[:10], 1):  # Первые 10 отзывов
            print(f"\n📝 ОТЗЫВ #{i}:")
            print("-" * 40)
            
            # Ищем дату разными способами
            date_found = False
            
            for selector in date_selectors:
                try:
                    date_elements = container.find_elements(By.CSS_SELECTOR, selector)
                    for date_elem in date_elements:
                        if date_elem and date_elem.text.strip():
                            date_text = date_elem.text.strip()
                            print(f"   📅 Селектор '{selector}': '{date_text}'")
                            date_found = True
                except:
                    continue
            
            # Если не нашли специфичные селекторы, ищем в общем тексте
            if not date_found:
                full_text = container.text
                lines = full_text.split('\n')
                print(f"   📄 Полный текст контейнера:")
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line:
                        print(f"      {line_num}: '{line}'")
                        # Ищем строки, похожие на даты
                        if any(month in line.lower() for month in 
                              ['january', 'february', 'march', 'april', 'may', 'june',
                               'july', 'august', 'september', 'october', 'november', 'december',
                               'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                               'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']):
                            print(f"      ⭐ ВОЗМОЖНАЯ ДАТА: '{line}'")
            
            print()
        
        print("\n🎯 ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ:")
        print("=" * 50)
        
        # Ищем все элементы, содержащие даты
        all_date_elements = []
        
        # Поиск по различным селекторам
        selectors_to_try = [
            "*[class*='date']",
            "time",
            "*[datetime]",
            "*[data-date]",
            ".business-review-view__date",
            "[class*='review'][class*='date']"
        ]
        
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.text.strip():
                        all_date_elements.append({
                            'selector': selector,
                            'text': elem.text.strip(),
                            'tag': elem.tag_name,
                            'class': elem.get_attribute('class') or '',
                            'datetime': elem.get_attribute('datetime') or '',
                            'data-date': elem.get_attribute('data-date') or ''
                        })
            except:
                continue
        
        print(f"📊 Найдено элементов с датами: {len(all_date_elements)}")
        
        for i, elem_info in enumerate(all_date_elements[:20], 1):  # Первые 20
            print(f"\n🔍 ЭЛЕМЕНТ #{i}:")
            print(f"   Селектор: {elem_info['selector']}")
            print(f"   Текст: '{elem_info['text']}'")
            print(f"   Тег: {elem_info['tag']}")
            print(f"   Класс: {elem_info['class']}")
            if elem_info['datetime']:
                print(f"   datetime: {elem_info['datetime']}")
            if elem_info['data-date']:
                print(f"   data-date: {elem_info['data-date']}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n⏹️ Закрываем браузер...")
        driver.quit()

if __name__ == "__main__":
    # URL для тестирования (Advert Pro)
    test_url = "https://yandex.ru/maps/org/bud_zdorov_/59625744337/reviews/?ll=37.596983%2C54.209918&z=17.63"
    analyze_review_dates(test_url) 