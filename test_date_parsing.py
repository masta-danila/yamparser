#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import re

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
        # "February 4", "January 4" - предполагаем текущий год
        if ' ' in date_str_clean:
            parts = date_str_clean.split()
            if len(parts) == 2:
                first_part, second_part = parts
                
                # Вариант 1: "May 28" (месяц день)
                if first_part in months and second_part.isdigit():
                    year = datetime.now().year
                    month = months[first_part]
                    day = second_part.zfill(2)
                    return f"{year}-{month}-{day}"
                
                # Вариант 2: "28 мая" (день месяц)
                elif first_part.isdigit() and second_part in months:
                    year = datetime.now().year
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
                    # Если есть 4-значное число, это год
                    year = datetime.now().year
                    day = numbers[0]
                    
                    for num in numbers:
                        if len(num) == 4 and num.isdigit():
                            year = int(num)
                            break
                    
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

def test_date_parsing():
    """Тестирование функции парсинга дат"""
    print("🧪 ТЕСТИРОВАНИЕ ФУНКЦИИ ПАРСИНГА ДАТ")
    print("=" * 50)
    
    # Тестовые данные из диагностики
    test_dates = [
        # Даты с годом
        'November 5, 2024',
        'November 19, 2024', 
        'January 30, 2024',
        'August 30, 2024',
        'April 19, 2023',
        'April 16, 2023',
        'August 12, 2023',
        'April 11, 2023',
        'April 29, 2022',
        'January 24, 2024',
        'September 21, 2022',
        'February 8, 2024',
        'November 17, 2023',
        'November 1, 2023',
        'May 17, 2022',
        'December 9, 2022',
        'June 16, 2022',
        'May 5, 2023',
        
        # Даты без года (текущий год)
        'February 4',
        'January 4',
        
        # Дополнительные тесты
        'March 15',
        'December 31, 2021',
        'Jul 4, 2020',
        
        # Русские даты
        '15 марта',
        '31 декабря, 2021',
        '4 июля, 2020'
    ]
    
    print(f"📅 Текущий год: {datetime.now().year}")
    print()
    
    for i, date_str in enumerate(test_dates, 1):
        result = parse_review_date(date_str)
        print(f"{i:2d}. '{date_str}' → '{result}'")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_date_parsing() 