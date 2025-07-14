#!/usr/bin/env python3
"""
Простой тест для диагностики проблемы с прокруткой
"""

def test_date_parsing():
    """Тестируем парсинг дат"""
    import sys
    sys.path.append('.')
    
    from datetime import datetime, timedelta
    from reviews_parser import parse_review_date
    
    # Тестируем с реальными данными
    cutoff_date = datetime.now() - timedelta(days=365)
    print(f"📅 Целевая дата: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Тестируем разные варианты дат
    test_dates = [
        "15 мая",
        "15 мая 2025", 
        "2025-05-15",
        "вчера",
        "сегодня"
    ]
    
    for date_str in test_dates:
        try:
            parsed_date = parse_review_date(date_str)
            print(f"🔍 '{date_str}' -> '{parsed_date}'")
            
            if parsed_date:
                review_date = datetime.strptime(parsed_date, '%Y-%m-%d')
                is_old = review_date <= cutoff_date
                print(f"   📅 {parsed_date} <= {cutoff_date.strftime('%Y-%m-%d')} = {is_old}")
                print(f"   🎯 Нужна прокрутка: {not is_old}")
        except Exception as e:
            print(f"❌ Ошибка для '{date_str}': {e}")
        print()

if __name__ == "__main__":
    test_date_parsing() 