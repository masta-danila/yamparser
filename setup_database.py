#!/usr/bin/env python3
"""
Скрипт для создания базы данных reviews и таблицы yandexmaps
Автоматически выполняет SQL скрипт create_reviews_database.sql
"""

import psycopg2
import psycopg2.extensions
import os
import sys

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'daniladzhiev',  # Замените на ваше имя пользователя
    'password': '',  # Добавьте пароль если нужен
}

def create_database():
    """Создает базу данных reviews если она не существует"""
    print("🔧 Создание базы данных reviews...")
    
    try:
        # Подключаемся к postgres для создания новой БД
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='postgres'
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Проверяем, существует ли база данных
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'reviews'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE reviews WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C'")
            print("✅ База данных 'reviews' создана успешно!")
        else:
            print("ℹ️  База данных 'reviews' уже существует")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания базы данных: {e}")
        return False

def execute_sql_script():
    """Выполняет SQL скрипт для создания таблиц и индексов"""
    print("🔧 Выполнение SQL скрипта...")
    
    # Читаем SQL файл
    sql_file = 'create_reviews_database.sql'
    if not os.path.exists(sql_file):
        print(f"❌ Файл {sql_file} не найден!")
        return False
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Подключаемся к базе reviews
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='reviews'
        )
        
        cursor = conn.cursor()
        
        # Выполняем SQL скрипт
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ SQL скрипт выполнен успешно!")
        
        # Показываем информацию о созданной таблице
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'yandexmaps' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("\n📊 Структура таблицы yandexmaps:")
        print("-" * 80)
        print(f"{'Поле':<20} {'Тип':<20} {'NULL':<8} {'По умолчанию':<30}")
        print("-" * 80)
        
        for col in columns:
            column_name, data_type, is_nullable, column_default = col
            nullable = "YES" if is_nullable == "YES" else "NO"
            default = str(column_default) if column_default else ""
            print(f"{column_name:<20} {data_type:<20} {nullable:<8} {default:<30}")
        
        # Показываем индексы
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'yandexmaps'
            ORDER BY indexname
        """)
        
        indexes = cursor.fetchall()
        print(f"\n🔍 Индексы ({len(indexes)} шт.):")
        print("-" * 80)
        for idx_name, idx_def in indexes:
            print(f"• {idx_name}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка выполнения SQL скрипта: {e}")
        return False

def test_connection():
    """Тестирует подключение к созданной базе данных"""
    print("🧪 Тестирование подключения...")
    
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='reviews'
        )
        
        cursor = conn.cursor()
        
        # Тестовый запрос
        cursor.execute("SELECT COUNT(*) FROM yandexmaps")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        print(f"✅ Подключение успешно!")
        print(f"📊 Записей в таблице yandexmaps: {count}")
        print(f"🐘 PostgreSQL версия: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 Настройка базы данных для системы отзывов Yandex Maps")
    print("=" * 60)
    
    # Шаг 1: Создание базы данных
    if not create_database():
        print("❌ Не удалось создать базу данных. Остановка.")
        sys.exit(1)
    
    # Шаг 2: Выполнение SQL скрипта
    if not execute_sql_script():
        print("❌ Не удалось выполнить SQL скрипт. Остановка.")
        sys.exit(1)
    
    # Шаг 3: Тестирование
    if not test_connection():
        print("❌ Не удалось подключиться к базе данных.")
        sys.exit(1)
    
    print("\n🎉 Настройка базы данных завершена успешно!")
    print("\n📝 Следующие шаги:")
    print("1. Подключение: psql -U daniladzhiev -d reviews")
    print("2. Просмотр таблицы: \\d yandexmaps")
    print("3. Тестовый запрос: SELECT * FROM yandexmaps LIMIT 5;")
    
    print(f"\n💡 Пример вставки данных:")
    print("""
INSERT INTO yandexmaps (card_id, author_name, review_text, review_date, rating) 
VALUES ('168085394903', 'Тестовый пользователь', 'Отличное место!', '2024-12-01', 4.5);
    """)

if __name__ == "__main__":
    main() 