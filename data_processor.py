"""
Модуль для обработки и сохранения данных отзывов
"""

import json
import os
from datetime import datetime
from thread_logger import thread_print

# Импорт функций работы с базой данных
try:
    from reviews_database import save_reviews_to_db, get_existing_reviews_count
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Импорт настроек из config
try:
    from config import WRITE_TO_DATABASE
except ImportError:
    WRITE_TO_DATABASE = True  # По умолчанию записываем в БД

def create_checkpoint_data(url, card_id, reviews, page_info, stats):
    """Создание данных для checkpoint"""
    checkpoint_data = {
        'url': url,
        'card_id': card_id,
        'timestamp': datetime.now().isoformat(),
        'page_info': page_info,
        'reviews_count': len(reviews),
        'reviews': reviews,
        'stats': stats
    }
    return checkpoint_data

def save_checkpoint(checkpoint_data, checkpoint_file):
    """Сохранение checkpoint в файл"""
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        thread_print(f"💾 Checkpoint сохранен: {checkpoint_file}")
        return True
    except Exception as e:
        thread_print(f"❌ Ошибка сохранения checkpoint: {e}")
        return False

def load_checkpoint(checkpoint_file):
    """Загрузка checkpoint из файла"""
    try:
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            print(f"📂 Checkpoint загружен: {checkpoint_file}")
            return checkpoint_data
        else:
            print(f"⚠️ Checkpoint файл не найден: {checkpoint_file}")
            return None
    except Exception as e:
        print(f"❌ Ошибка загрузки checkpoint: {e}")
        return None

def save_reviews_to_database(reviews, card_id, url):
    """Сохранение отзывов в базу данных"""
    if not DATABASE_AVAILABLE:
        print("❌ Модуль базы данных недоступен")
        return False, 0, 0
    
    if not WRITE_TO_DATABASE:
        print("⚠️ Запись в БД отключена (WRITE_TO_DATABASE=False)")
        return True, 0, 0
    
    if not reviews:
        print("⚠️ Нет отзывов для сохранения")
        return True, 0, 0
    
    try:
        # Получаем количество существующих отзывов
        existing_count = get_existing_reviews_count(card_id)
        print(f"📊 Существующих отзывов в БД: {existing_count}")
        
        # Сохраняем отзывы
        saved_count = save_reviews_to_db(reviews, card_id, url)
        
        if saved_count > 0:
            print(f"✅ Сохранено новых отзывов в БД: {saved_count}")
            return True, saved_count, existing_count
        else:
            print("⚠️ Новых отзывов для сохранения не найдено")
            return True, 0, existing_count
            
    except Exception as e:
        print(f"❌ Ошибка сохранения в базу данных: {e}")
        return False, 0, 0

def process_and_save_results(reviews, card_id, url, checkpoint_file=None, page_info=None):
    """Обработка и сохранение результатов парсинга"""
    results = {
        'success': False,
        'reviews_count': len(reviews),
        'saved_to_db': False,
        'db_saved_count': 0,
        'db_existing_count': 0,
        'checkpoint_saved': False
    }
    
    try:
        # Сохранение в базу данных
        if DATABASE_AVAILABLE and WRITE_TO_DATABASE:
            db_success, saved_count, existing_count = save_reviews_to_database(reviews, card_id, url)
            results['saved_to_db'] = db_success
            results['db_saved_count'] = saved_count
            results['db_existing_count'] = existing_count
        elif not WRITE_TO_DATABASE:
            print("⚠️ Пропускаем сохранение в БД (WRITE_TO_DATABASE=False)")
            results['saved_to_db'] = True  # Считаем успешным, просто не сохраняем
        
        # Создание статистики
        stats = {
            'total_reviews': len(reviews),
            'reviews_with_text': len([r for r in reviews if r.get('text', '').strip()]),
            'reviews_with_rating': len([r for r in reviews if r.get('rating')]),
            'average_rating': None,
            'date_range': None
        }
        
        # Расчет среднего рейтинга
        ratings = [r['rating'] for r in reviews if r.get('rating')]
        if ratings:
            stats['average_rating'] = sum(ratings) / len(ratings)
        
        # Определение диапазона дат
        dates = [r['date'] for r in reviews if r.get('date')]
        if dates:
            stats['date_range'] = {'earliest': min(dates), 'latest': max(dates)}
        
        # Сохранение checkpoint
        if checkpoint_file:
            checkpoint_data = create_checkpoint_data(url, card_id, reviews, page_info, stats)
            checkpoint_success = save_checkpoint(checkpoint_data, checkpoint_file)
            results['checkpoint_saved'] = checkpoint_success
        
        results['success'] = True
        results['stats'] = stats
        
        # Вывод итоговой статистики
        print("\n" + "="*50)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*50)
        print(f"🔗 URL: {url}")
        print(f"🆔 ID карточки: {card_id}")
        print(f"📝 Всего отзывов: {stats['total_reviews']}")
        print(f"📄 С текстом: {stats['reviews_with_text']}")
        print(f"⭐ С рейтингом: {stats['reviews_with_rating']}")
        if stats['average_rating']:
            print(f"📊 Средний рейтинг: {stats['average_rating']:.1f}")
        if stats['date_range']:
            print(f"📅 Диапазон дат: {stats['date_range']['earliest']} - {stats['date_range']['latest']}")
        
        if DATABASE_AVAILABLE:
            print(f"💾 Сохранено в БД новых: {results['db_saved_count']}")
            print(f"📊 Было в БД ранее: {results['db_existing_count']}")
        
        if checkpoint_file:
            print(f"📂 Checkpoint: {'✅ Сохранен' if results['checkpoint_saved'] else '❌ Ошибка'}")
        
        print("="*50)
        
    except Exception as e:
        print(f"❌ Ошибка обработки результатов: {e}")
        results['success'] = False
    
    return results

def filter_reviews_by_date(reviews, max_days_back):
    """Фильтрация отзывов по дате"""
    if not max_days_back or max_days_back <= 0:
        return reviews
    
    from review_extractor import is_review_too_old
    
    filtered_reviews = []
    for review in reviews:
        if not is_review_too_old(review.get('date'), max_days_back):
            filtered_reviews.append(review)
        else:
            print(f"⏰ Отзыв от {review.get('date')} отфильтрован (слишком старый)")
    
    if len(filtered_reviews) < len(reviews):
        print(f"🗓️ Отфильтровано по дате: {len(reviews)} → {len(filtered_reviews)} отзывов")
    
    return filtered_reviews

def limit_reviews_count(reviews, max_reviews_limit):
    """Ограничение количества отзывов"""
    if not max_reviews_limit or max_reviews_limit <= 0:
        return reviews
    
    if len(reviews) > max_reviews_limit:
        print(f"🔢 Ограничение количества отзывов: {len(reviews)} → {max_reviews_limit}")
        return reviews[:max_reviews_limit]
    
    return reviews

def clean_review_data(reviews):
    """Очистка и нормализация данных отзывов"""
    cleaned_reviews = []
    
    for review in reviews:
        cleaned_review = {
            'author': (review.get('author') or 'Аноним').strip(),
            'rating': review.get('rating'),
            'text': (review.get('text') or '').strip(),
            'date': (review.get('date') or '').strip(),
            'photos_count': max(0, review.get('photos_count', 0)),
            'helpful_count': max(0, review.get('helpful_count', 0))
        }
        
        # Пропускаем пустые отзывы
        if not cleaned_review['text'] and not cleaned_review['rating']:
            continue
        
        cleaned_reviews.append(cleaned_review)
    
    return cleaned_reviews 