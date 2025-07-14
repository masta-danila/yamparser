#!/usr/bin/env python3
"""
Тест функции fast_scroll_to_date_limit без браузера
"""

def test_scroll_logic():
    """Тестируем логику функции прокрутки"""
    import sys
    sys.path.append('.')
    
    from datetime import datetime, timedelta
    
    # Имитируем реальные условия
    max_days_back = 365
    cutoff_date = datetime.now() - timedelta(days=max_days_back)
    print(f"📅 Целевая дата: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Имитируем дату последнего отзыва (самая новая дата с логов)
    last_review_date_str = "15 мая"
    
    # Проверяем логику как в функции
    from reviews_parser import parse_review_date
    
    print(f"🔍 Последний отзыв на странице: дата = '{last_review_date_str}'")
    
    if last_review_date_str:
        try:
            parsed_date = parse_review_date(last_review_date_str)
            print(f"🔍 Парсенная дата: '{parsed_date}'")
            
            if parsed_date:
                review_date = datetime.strptime(parsed_date, '%Y-%m-%d')
                
                print(f"🔍 Сравнение {parsed_date} <= {cutoff_date.strftime('%Y-%m-%d')} = {review_date <= cutoff_date}")
                
                if review_date <= cutoff_date:
                    print(f"✅ ЦЕЛЕВАЯ ДАТА УЖЕ НАЙДЕНА: {parsed_date} <= {cutoff_date.strftime('%Y-%m-%d')}")
                    print(f"🚀 Прокрутка не нужна!")
                    return True
                else:
                    print(f"📅 Нужна прокрутка: {parsed_date} > {cutoff_date.strftime('%Y-%m-%d')}")
                    print(f"🚀 ДОЛЖНА ВЫПОЛНЯТЬСЯ ПРОКРУТКА!")
                    return False
            else:
                print(f"⚠️ Парсинг даты не удался")
        except Exception as e:
            print(f"❌ Ошибка парсинга даты: {e}")
    else:
        print(f"⚠️ Дата не найдена в последнем отзыве")
    
    return None

if __name__ == "__main__":
    result = test_scroll_logic()
    print(f"\n🎯 РЕЗУЛЬТАТ: функция должна вернуть {result}")
    if result is False:
        print("🔥 ПРОБЛЕМА: функция должна выполнить прокрутку, но возвращает True!") 