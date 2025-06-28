#!/usr/bin/env python3
"""
Модуль для работы с базой данных отзывов Yandex Maps
Содержит функции выгрузки и загрузки отзывов
"""

import psycopg2
import psycopg2.extras
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional, Union
import json

# Настройки подключения к базе данных
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'daniladzhiev',
    'password': '',
    'database': 'reviews'
}

class ReviewsDatabase:
    """Класс для работы с базой данных отзывов"""
    
    def __init__(self, config=None):
        """Инициализация подключения к БД"""
        self.config = config or DB_CONFIG
        self.connection = None
        
    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = psycopg2.connect(**self.config)
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.disconnect()

    # ===============================
    # ФУНКЦИИ ВЫГРУЗКИ ОТЗЫВОВ
    # ===============================
    
    def get_reviews_by_card_id(self, card_id: str, limit: int = None, offset: int = 0) -> List[Dict]:
        """
        Получить все отзывы по ID карточки организации
        
        Args:
            card_id: ID карточки организации
            limit: Максимальное количество отзывов (None = все)
            offset: Смещение для пагинации
            
        Returns:
            Список словарей с отзывами
        """
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    id, card_id, author_name, review_text, review_date, 
                    rating, status, created_at, updated_at
                FROM yandexmaps 
                WHERE card_id = %s 
                ORDER BY review_date DESC, id DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            cursor.execute(query, (card_id,))
            reviews = cursor.fetchall()
            cursor.close()
            
            # Конвертируем в обычные словари
            return [dict(review) for review in reviews]
            
        except Exception as e:
            print(f"❌ Ошибка получения отзывов по card_id {card_id}: {e}")
            return []
    
    def get_reviews_by_date_range(self, start_date: Union[str, date], end_date: Union[str, date] = None, card_id: str = None) -> List[Dict]:
        """
        Получить отзывы за период
        
        Args:
            start_date: Начальная дата (YYYY-MM-DD или объект date)
            end_date: Конечная дата (None = только start_date)
            card_id: Фильтр по карточке (None = все карточки)
            
        Returns:
            Список отзывов
        """
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Базовый запрос
            query = """
                SELECT 
                    id, card_id, author_name, review_text, review_date, 
                    rating, status, created_at, updated_at
                FROM yandexmaps 
                WHERE review_date >= %s
            """
            params = [start_date]
            
            # Добавляем конечную дату если указана
            if end_date:
                query += " AND review_date <= %s"
                params.append(end_date)
            
            # Добавляем фильтр по карточке если указан
            if card_id:
                query += " AND card_id = %s"
                params.append(card_id)
            
            query += " ORDER BY review_date DESC, id DESC"
            
            cursor.execute(query, params)
            reviews = cursor.fetchall()
            cursor.close()
            
            return [dict(review) for review in reviews]
            
        except Exception as e:
            print(f"❌ Ошибка получения отзывов по дате: {e}")
            return []
    
    def get_latest_review_by_card(self, card_id: str) -> Optional[Dict]:
        """
        Получить последний отзыв по карточке (для checkpoint системы)
        
        Args:
            card_id: ID карточки организации
            
        Returns:
            Словарь с последним отзывом или None
        """
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    id, card_id, author_name, review_text, review_date, 
                    rating, status, text_hash, text_preview, text_length,
                    created_at, updated_at
                FROM yandexmaps 
                WHERE card_id = %s 
                ORDER BY review_date DESC, id DESC 
                LIMIT 1
            """, (card_id,))
            
            review = cursor.fetchone()
            cursor.close()
            
            return dict(review) if review else None
            
        except Exception as e:
            print(f"❌ Ошибка получения последнего отзыва: {e}")
            return None
    
    def search_reviews(self, search_text: str, card_id: str = None, min_rating: float = None) -> List[Dict]:
        """
        Поиск отзывов по тексту
        
        Args:
            search_text: Текст для поиска
            card_id: Фильтр по карточке (None = все)
            min_rating: Минимальная оценка (None = любая)
            
        Returns:
            Список найденных отзывов
        """
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    id, card_id, author_name, review_text, review_date, 
                    rating, status, created_at, updated_at
                FROM yandexmaps 
                WHERE review_text ILIKE %s
            """
            params = [f"%{search_text}%"]
            
            if card_id:
                query += " AND card_id = %s"
                params.append(card_id)
            
            if min_rating is not None:
                query += " AND rating >= %s"
                params.append(min_rating)
            
            query += " ORDER BY review_date DESC"
            
            cursor.execute(query, params)
            reviews = cursor.fetchall()
            cursor.close()
            
            return [dict(review) for review in reviews]
            
        except Exception as e:
            print(f"❌ Ошибка поиска отзывов: {e}")
            return []
    
    def get_statistics(self, card_id: str = None) -> Dict:
        """
        Получить статистику по отзывам
        
        Args:
            card_id: ID карточки (None = общая статистика)
            
        Returns:
            Словарь со статистикой
        """
        try:
            cursor = self.connection.cursor()
            
            base_query = "FROM yandexmaps"
            params = []
            
            if card_id:
                base_query += " WHERE card_id = %s"
                params = [card_id]
            
            # Общая статистика
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total_reviews = cursor.fetchone()[0]
            
            # Средняя оценка
            cursor.execute(f"SELECT AVG(rating) {base_query} AND rating IS NOT NULL", params)
            avg_rating = cursor.fetchone()[0]
            
            # Распределение по оценкам
            cursor.execute(f"""
                SELECT rating, COUNT(*) 
                {base_query} AND rating IS NOT NULL 
                GROUP BY rating 
                ORDER BY rating
            """, params)
            rating_distribution = dict(cursor.fetchall())
            
            # Статистика по датам
            cursor.execute(f"""
                SELECT 
                    MIN(review_date) as earliest_date,
                    MAX(review_date) as latest_date
                {base_query}
            """, params)
            date_range = cursor.fetchone()
            
            cursor.close()
            
            return {
                'total_reviews': total_reviews,
                'average_rating': float(avg_rating) if avg_rating else None,
                'rating_distribution': rating_distribution,
                'earliest_date': date_range[0],
                'latest_date': date_range[1]
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {}

    # ===============================
    # ФУНКЦИИ ЗАГРУЗКИ ОТЗЫВОВ
    # ===============================
    
    def _calculate_text_fields(self, review_text: str) -> Dict:
        """Вычисляет дополнительные поля для текста отзыва"""
        return {
            'text_hash': hashlib.md5(review_text.encode('utf-8')).hexdigest(),
            'text_preview': review_text[:100],
            'text_length': len(review_text)
        }
    
    def add_review(self, card_id: str, author_name: str, review_text: str, 
                   review_date: Union[str, date], rating: float = None, 
                   status: str = 'not_found') -> Optional[int]:
        """
        Добавить новый отзыв
        
        Args:
            card_id: ID карточки организации
            author_name: Имя автора
            review_text: Текст отзыва
            review_date: Дата отзыва
            rating: Оценка (1.0-5.0)
            status: Статус ('found' или 'not_found')
            
        Returns:
            ID созданной записи или None при ошибке
        """
        try:
            # Вычисляем дополнительные поля
            text_fields = self._calculate_text_fields(review_text)
            
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO yandexmaps 
                (card_id, author_name, review_text, review_date, rating, status, 
                 text_hash, text_preview, text_length)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                card_id, author_name, review_text, review_date, rating, status,
                text_fields['text_hash'], text_fields['text_preview'], text_fields['text_length']
            ))
            
            review_id = cursor.fetchone()[0]
            self.connection.commit()
            cursor.close()
            
            print(f"✅ Отзыв добавлен с ID: {review_id}")
            return review_id
            
        except psycopg2.IntegrityError as e:
            self.connection.rollback()
            print(f"⚠️ Дубликат отзыва (пропускаем): {e}")
            return None
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Ошибка добавления отзыва: {e}")
            return None
    
    def add_reviews_batch(self, reviews: List[Dict]) -> Dict:
        """
        Добавить несколько отзывов одновременно (batch insert)
        
        Args:
            reviews: Список словарей с отзывами
            Формат: [{'card_id': '...', 'author_name': '...', 'review_text': '...', 
                     'review_date': '...', 'rating': 4.5, 'status': 'found'}, ...]
            
        Returns:
            Словарь с результатами: {'added': int, 'duplicates': int, 'errors': int}
        """
        results = {'added': 0, 'duplicates': 0, 'errors': 0}
        
        try:
            cursor = self.connection.cursor()
            
            for review in reviews:
                try:
                    # Вычисляем дополнительные поля
                    text_fields = self._calculate_text_fields(review['review_text'])
                    
                    cursor.execute("""
                        INSERT INTO yandexmaps 
                        (card_id, author_name, review_text, review_date, rating, status,
                         text_hash, text_preview, text_length)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        review['card_id'],
                        review['author_name'], 
                        review['review_text'],
                        review['review_date'],
                        review.get('rating'),
                        review.get('status', 'not_found'),
                        text_fields['text_hash'],
                        text_fields['text_preview'],
                        text_fields['text_length']
                    ))
                    
                    results['added'] += 1
                    
                except psycopg2.IntegrityError:
                    # Дубликат - откатываем только эту запись
                    self.connection.rollback()
                    results['duplicates'] += 1
                    continue
                    
                except Exception as e:
                    print(f"❌ Ошибка добавления отзыва: {e}")
                    results['errors'] += 1
                    continue
            
            self.connection.commit()
            cursor.close()
            
            print(f"📊 Результаты batch загрузки:")
            print(f"   ✅ Добавлено: {results['added']}")
            print(f"   ⚠️ Дубликатов: {results['duplicates']}")
            print(f"   ❌ Ошибок: {results['errors']}")
            
            return results
            
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Критическая ошибка batch загрузки: {e}")
            results['errors'] = len(reviews)
            return results
    
    def check_duplicate_review(self, card_id: str, author_name: str, 
                              review_date: Union[str, date], review_text: str = None, rating: float = None) -> Optional[Dict]:
        """
        Проверить, есть ли дубликат отзыва по алгоритму: дата + автор + рейтинг
        
        Args:
            card_id: ID карточки
            author_name: Автор
            review_date: Дата
            review_text: Текст отзыва (опционально, для дополнительной проверки)
            rating: Рейтинг (основной критерий уникальности)
            
        Returns:
            Словарь с найденным дубликатом или None
        """
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Основной поиск по дате + автор + рейтинг
            query = """
                SELECT * FROM yandexmaps 
                WHERE card_id = %s 
                AND author_name = %s 
                AND review_date = %s
            """
            params = [card_id, author_name, review_date]
            
            # Добавляем рейтинг если указан
            if rating is not None:
                query += " AND rating = %s"
                params.append(rating)
            
            cursor.execute(query, params)
            duplicates = cursor.fetchall()
            
            # Если найдено несколько совпадений и есть текст - проверяем по тексту
            if len(duplicates) > 1 and review_text:
                text_hash = hashlib.md5(review_text.encode('utf-8')).hexdigest()
                for duplicate in duplicates:
                    if duplicate.get('text_hash') == text_hash:
                        cursor.close()
                        return dict(duplicate)
            
            # Возвращаем первое найденное совпадение
            duplicate = duplicates[0] if duplicates else None
            cursor.close()
            
            return dict(duplicate) if duplicate else None
            
        except Exception as e:
            print(f"❌ Ошибка проверки дубликата: {e}")
            return None
    
    def update_review_status(self, review_id: int, status: str) -> bool:
        """
        Обновить статус отзыва
        
        Args:
            review_id: ID отзыва
            status: Новый статус ('found' или 'not_found')
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                UPDATE yandexmaps 
                SET status = %s, updated_at = NOW() 
                WHERE id = %s
            """, (status, review_id))
            
            rows_affected = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            if rows_affected > 0:
                print(f"✅ Статус отзыва {review_id} обновлен на '{status}'")
                return True
            else:
                print(f"⚠️ Отзыв с ID {review_id} не найден")
                return False
                
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Ошибка обновления статуса: {e}")
            return False

    def clear_all_reviews(self, card_id: str = None, confirm: bool = False) -> Dict:
        """
        Очистить все отзывы из базы данных
        
        Args:
            card_id: ID карточки для очистки (None = очистить все)
            confirm: Подтверждение операции (обязательно True)
            
        Returns:
            Словарь с результатами операции
        """
        if not confirm:
            print("❌ Операция очистки требует подтверждения (confirm=True)")
            return {"deleted": 0, "error": "Не подтверждено"}
        
        try:
            cursor = self.connection.cursor()
            
            if card_id:
                # Считаем отзывы перед удалением
                cursor.execute("SELECT COUNT(*) FROM yandexmaps WHERE card_id = %s", (card_id,))
                count_before = cursor.fetchone()[0]
                
                # Удаляем отзывы конкретной карточки
                cursor.execute("DELETE FROM yandexmaps WHERE card_id = %s", (card_id,))
                deleted_count = cursor.rowcount
                
                print(f"🗑️ Удалено {deleted_count} отзывов для карточки {card_id}")
            else:
                # Считаем все отзывы перед удалением
                cursor.execute("SELECT COUNT(*) FROM yandexmaps")
                count_before = cursor.fetchone()[0]
                
                # Удаляем все отзывы
                cursor.execute("DELETE FROM yandexmaps")
                deleted_count = cursor.rowcount
                
                print(f"🗑️ Удалено {deleted_count} отзывов из всей базы данных")
            
            self.connection.commit()
            cursor.close()
            
            print(f"✅ Очистка завершена успешно")
            return {"deleted": deleted_count, "error": None}
            
        except Exception as e:
            print(f"❌ Ошибка очистки базы данных: {e}")
            self.connection.rollback()
            return {"deleted": 0, "error": str(e)}

    def get_database_info(self) -> Dict:
        """
        Получить информацию о состоянии базы данных
        
        Returns:
            Словарь с информацией о БД
        """
        try:
            cursor = self.connection.cursor()
            
            # Общее количество отзывов
            cursor.execute("SELECT COUNT(*) FROM yandexmaps")
            total_reviews = cursor.fetchone()[0]
            
            # Количество уникальных карточек
            cursor.execute("SELECT COUNT(DISTINCT card_id) FROM yandexmaps")
            unique_cards = cursor.fetchone()[0]
            
            # Дата первого и последнего отзыва
            cursor.execute("""
                SELECT 
                    MIN(review_date) as first_date,
                    MAX(review_date) as last_date
                FROM yandexmaps 
                WHERE review_date IS NOT NULL
            """)
            date_range = cursor.fetchone()
            
            # Статистика по статусам
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM yandexmaps 
                GROUP BY status 
                ORDER BY COUNT(*) DESC
            """)
            status_stats = dict(cursor.fetchall())
            
            cursor.close()
            
            info = {
                "total_reviews": total_reviews,
                "unique_cards": unique_cards,
                "first_review_date": date_range[0] if date_range[0] else None,
                "last_review_date": date_range[1] if date_range[1] else None,
                "status_distribution": status_stats
            }
            
            return info
            
        except Exception as e:
            print(f"❌ Ошибка получения информации о БД: {e}")
            return {"error": str(e)}

    # ===============================
    # УТИЛИТЫ
    # ===============================
    
    def export_reviews_to_json(self, card_id: str = None, filename: str = None) -> str:
        """
        Экспорт отзывов в JSON файл
        
        Args:
            card_id: ID карточки (None = все отзывы)
            filename: Имя файла (None = автоматическое)
            
        Returns:
            Путь к созданному файлу
        """
        try:
            if card_id:
                reviews = self.get_reviews_by_card_id(card_id)
                default_filename = f"reviews_{card_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("SELECT * FROM yandexmaps ORDER BY review_date DESC")
                reviews = [dict(review) for review in cursor.fetchall()]
                cursor.close()
                default_filename = f"all_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filename = filename or default_filename
            
            # Конвертируем даты в строки для JSON
            for review in reviews:
                if 'review_date' in review and review['review_date']:
                    review['review_date'] = review['review_date'].isoformat()
                if 'created_at' in review and review['created_at']:
                    review['created_at'] = review['created_at'].isoformat()
                if 'updated_at' in review and review['updated_at']:
                    review['updated_at'] = review['updated_at'].isoformat()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
            
            print(f"📄 Экспорт завершен: {filename} ({len(reviews)} отзывов)")
            return filename
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return ""


# ===============================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ===============================

def example_usage():
    """Примеры использования модуля"""
    
    print("🚀 Примеры работы с базой данных отзывов")
    print("=" * 50)
    
    # Используем контекстный менеджер для автоматического подключения/отключения
    with ReviewsDatabase() as db:
        
        # Пример 1: Добавление отзыва
        print("\n📝 Добавление тестового отзыва...")
        review_id = db.add_review(
            card_id="168085394903",
            author_name="Тестовый пользователь",
            review_text="Отличное место! Рекомендую всем.",
            review_date="2024-12-01",
            rating=4.5,
            status="found"
        )
        
        # Пример 2: Получение отзывов по карточке
        print("\n📊 Получение отзывов по карточке...")
        reviews = db.get_reviews_by_card_id("168085394903", limit=5)
        print(f"Найдено отзывов: {len(reviews)}")
        
        # Пример 3: Получение последнего отзыва (для checkpoint)
        print("\n🔍 Получение последнего отзыва...")
        latest = db.get_latest_review_by_card("168085394903")
        if latest:
            print(f"Последний отзыв от: {latest['review_date']}, автор: {latest['author_name']}")
        
        # Пример 4: Статистика
        print("\n📈 Статистика по отзывам...")
        stats = db.get_statistics("168085394903")
        print(f"Всего отзывов: {stats.get('total_reviews', 0)}")
        print(f"Средняя оценка: {stats.get('average_rating', 'N/A')}")


if __name__ == "__main__":
    example_usage() 