#!/usr/bin/env python3
"""
Простой тест для проверки конфигурации
"""

try:
    from config import DATABASE_CONFIG
    print("✅ Импорт config.py успешен")
    print(f"📊 DATABASE_CONFIG: {DATABASE_CONFIG}")
    
    # Проверяем типы данных
    print(f"🔍 Тип порта: {type(DATABASE_CONFIG['port'])}")
    print(f"🔍 Значение порта: {DATABASE_CONFIG['port']}")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
except Exception as e:
    print(f"❌ Другая ошибка: {e}")

try:
    import psycopg2
    print("✅ psycopg2 импортирован успешно")
except ImportError:
    print("❌ psycopg2 не установлен") 