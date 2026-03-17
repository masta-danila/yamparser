"""
Интегрированный парсер для работы с Google Sheets и Яндекс.Карт
Объединяет чтение таблиц, парсинг отзывов и проверку совпадений
"""

import sys
import os
import time
import threading
import psutil
from threading import Thread
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Импорт основных модулей
from platforms import get_handler_for_url
from google_sheets_reader import GoogleSheetsReader
from sheets_updater import SheetsUpdater
from text_matcher import TextMatcher
from thread_logger import thread_print
from driver_manager import get_driver_creation_lock, initialize_profiles_cleanup, cleanup_all_profiles

# Настройка логирования
from logger_config import setup_logging 
import logging

# ============================================================
# ФУНКЦИИ МОНИТОРИНГА РЕСУРСОВ
# ============================================================

def monitor_system_resources():
    """Мониторинг системных ресурсов"""
    try:
        # Получаем информацию о системе
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Информация о процессах Chrome
        chrome_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    chrome_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Информация о потоках
        active_threads = threading.active_count()
        
        thread_print(f"📊 СИСТЕМНЫЕ РЕСУРСЫ:")
        thread_print(f"   💻 CPU: {cpu_percent}%")
        thread_print(f"   🧠 RAM: {memory.percent}% ({memory.used / 1024 / 1024 / 1024:.1f}GB / {memory.total / 1024 / 1024 / 1024:.1f}GB)")
        thread_print(f"   🧵 Активных потоков: {active_threads}")
        thread_print(f"   🌐 Chrome процессов: {len(chrome_processes)}")
        
        if chrome_processes:
            total_chrome_memory = sum(p['memory_mb'] for p in chrome_processes)
            thread_print(f"   📈 Chrome память: {total_chrome_memory:.1f}MB")
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'active_threads': active_threads,
            'chrome_processes': len(chrome_processes),
            'chrome_memory_mb': sum(p['memory_mb'] for p in chrome_processes) if chrome_processes else 0
        }
    except Exception as e:
        thread_print(f"❌ Ошибка мониторинга ресурсов: {e}")
        return None

# ============================================================
# ============================================================

class IntegratedParser:
    """Интегрированный парсер для работы с Google Sheets и Яндекс.Карт"""
    
    def __init__(self, 
                 spreadsheet_url: str,
                 credentials_file: str = "credentials.json",
                 similarity_threshold: float = 0.85,
                 max_workers: int = 20):
        """
        Инициализация интегрированного парсера
        
        Args:
            spreadsheet_url: URL Google Sheets таблицы
            credentials_file: Путь к файлу с учетными данными
            similarity_threshold: Порог совпадения текстов (0.0 - 1.0)
            max_workers: Максимальное количество потоков
        """
        self.spreadsheet_url = spreadsheet_url
        self.credentials_file = credentials_file
        self.similarity_threshold = similarity_threshold
        self.max_workers = max_workers
        
        # Инициализация компонентов
        self.sheets_reader = GoogleSheetsReader(credentials_file)
        self.text_matcher = TextMatcher(similarity_threshold)
        self.sheets_updater = SheetsUpdater(credentials_file)
        
        # Блокировка для создания драйверов
        self.driver_creation_lock = get_driver_creation_lock()
        
        # Результаты работы
        self.results = {
            'total_sheets': 0,
            'processed_sheets': 0,
            'total_urls': 0,
            'processed_urls': 0,
            'total_matches': 0,
            'total_updates': 0,
            'errors': []
        }
        
        # Блокировка для многопоточности
        self.lock = threading.Lock()
    
    def _format_date_for_sheets(self, date_value) -> str:
        """
        Форматирует дату для записи в Google Sheets в формате DD.MM.YYYY
        
        Args:
            date_value: Строка с датой, объект date или None
            
        Returns:
            Отформатированная дата в формате DD.MM.YYYY
        """
        if not date_value:
            return ''
        
        # Преобразуем в строку если это объект date
        if hasattr(date_value, 'strftime'):
            return date_value.strftime('%d.%m.%Y')
        
        date_str = str(date_value)
        
        # Если дата уже в формате DD.MM.YYYY, возвращаем как есть
        import re
        if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str):
            return date_str
        
        # Попытка преобразовать различные форматы дат
        try:
            from datetime import datetime
            
            # Формат "19 июня"
            months_ru = {
                'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
            }
            
            for month_name, month_num in months_ru.items():
                if month_name in date_str:
                    # Извлекаем день
                    day_match = re.search(r'(\d{1,2})\s+' + month_name, date_str)
                    if day_match:
                        day = day_match.group(1).zfill(2)
                        year = str(datetime.now().year)  # Используем текущий год
                        return f"{day}.{month_num}.{year}"
            
            # Формат "17 June 2025" или похожие английские форматы
            months_en = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12'
            }
            
            date_lower = date_str.lower()
            for month_name, month_num in months_en.items():
                if month_name in date_lower:
                    # Ищем день и год
                    match = re.search(r'(\d{1,2})\s+' + month_name + r'\s+(\d{4})', date_lower)
                    if match:
                        day = match.group(1).zfill(2)
                        year = match.group(2)
                        return f"{day}.{month_num}.{year}"
            
            # Для относительных дат возвращаем как есть
            if any(word in date_str for word in ['назад', 'дней', 'день', 'месяц', 'года', 'вчера', 'сегодня']):
                return date_str
            
        except Exception:
            pass
        
        return date_str
    
    def get_sheet_data(self, sheet_name: str, max_days_back: int = 30, recheck_days: int = 30) -> Dict[str, Any]:
        """
        Получает данные листа и группирует их по URL
        
        Обрабатываются:
        - Отзывы со статусом "Модерация" и датой публикации не позднее max_days_back.
        - Отзывы со статусом "Размещен" и датой публикации не позднее recheck_days (для проверки удаления).
        Старые отзывы со статусом "Модерация" автоматически отклоняются (статус -> "Отклонен").
        
        Args:
            sheet_name: Название листа
            max_days_back: Максимальное количество дней назад для отзывов "Модерация"
            recheck_days: Максимальное количество дней для повторной проверки отзывов "Размещен"
            
        Returns:
            Словарь с данными листа
        """
        try:
            # Читаем лист
            df = self.sheets_reader.read_sheet_api(
                self.sheets_reader.extract_spreadsheet_id(self.spreadsheet_url),
                sheet_name,
                validate_columns=True
            )
            
            if df.empty:
                return {'urls': {}, 'error': 'Лист пуст'}
            
            # Проверяем наличие колонки "Дата публикации"
            has_publication_date_column = 'Дата публикации' in df.columns
            if not has_publication_date_column:
                thread_print(f"⚠️ Колонка 'Дата публикации' не найдена в листе '{sheet_name}', фильтрация по дате отключена")
            
            # Вычисляем пороговые даты
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=max_days_back)
            recheck_cutoff_date = datetime.now() - timedelta(days=recheck_days)
            
            # Группируем данные по URL
            urls_data = defaultdict(list)
            
            # Статистика фильтрации
            total_rows = 0
            filtered_by_empty = 0
            filtered_by_status = 0
            filtered_by_date = 0
            filtered_by_empty_date = 0
            auto_rejected_count = 0  # Счетчик автоматически отклоненных отзывов
            processed_rows = 0
            
            for index, row in df.iterrows():
                total_rows += 1
                card_id = row.get('id карточки', '').strip()
                review_text = row.get('Текст отзыва', '').strip()
                status = row.get('Статус', '').strip()
                publication_date = row.get('Дата публикации', '') if has_publication_date_column else None
                
                # Пропускаем строки без id карточки или с пустым текстом отзыва
                if not card_id or not review_text:
                    filtered_by_empty += 1
                    continue
                
                # Формируем URL из ID карточки (название не важно - Яндекс сделает редирект)
                url = f"https://yandex.ru/maps/org/{card_id}/reviews/"
                
                # Берем в работу отзывы "Модерация" или "Размещен" (для повторной проверки)
                if status not in ("Модерация", "Размещен"):
                    filtered_by_status += 1
                    continue
                
                # Фильтрация по дате публикации (если колонка есть)
                if has_publication_date_column:
                    if not publication_date or str(publication_date).strip() == '' or str(publication_date).strip().lower() in ['nan', 'none', 'null']:
                        filtered_by_empty_date += 1
                        continue
                    
                    # Парсим дату публикации
                    try:
                        # Пробуем разные форматы дат
                        publication_date_str = str(publication_date).strip()
                        publication_date_parsed = None
                        
                        # Формат DD.MM.YYYY
                        if '.' in publication_date_str:
                            try:
                                publication_date_parsed = datetime.strptime(publication_date_str, '%d.%m.%Y')
                            except ValueError:
                                pass
                        
                        # Формат YYYY-MM-DD
                        if not publication_date_parsed and '-' in publication_date_str:
                            try:
                                publication_date_parsed = datetime.strptime(publication_date_str, '%Y-%m-%d')
                            except ValueError:
                                pass
                        
                        # Формат DD/MM/YYYY
                        if not publication_date_parsed and '/' in publication_date_str:
                            try:
                                publication_date_parsed = datetime.strptime(publication_date_str, '%d/%m/%Y')
                            except ValueError:
                                pass
                        
                        # Если не удалось распарсить дату
                        if not publication_date_parsed:
                            thread_print(f"⚠️ Не удалось распарсить дату публикации '{publication_date_str}' в строке {index + 2}")
                            filtered_by_empty_date += 1
                            continue
                        
                        # Проверяем дату в зависимости от статуса
                        if status == "Модерация":
                            if publication_date_parsed < cutoff_date:
                                thread_print(f"📅 Автоматическое отклонение старого отзыва: строка {index + 2}, дата {publication_date_str}")
                                try:
                                    success = self.sheets_updater.update_review_status(
                                        spreadsheet_url=self.spreadsheet_url,
                                        sheet_name=sheet_name,
                                        row_number=index + 2,
                                        new_status='Отклонен',
                                        publication_date=None
                                    )
                                    if success:
                                        thread_print(f"✅ Старый отзыв отклонен: строка {index + 2} -> 'Отклонен'")
                                        auto_rejected_count += 1
                                    else:
                                        thread_print(f"❌ Не удалось отклонить старый отзыв в строке {index + 2}")
                                except Exception as update_error:
                                    thread_print(f"❌ Ошибка отклонения старого отзыва в строке {index + 2}: {update_error}")
                                filtered_by_date += 1
                                continue
                        elif status == "Размещен":
                            if publication_date_parsed < recheck_cutoff_date:
                                filtered_by_date += 1
                                continue
                            
                    except Exception as e:
                        thread_print(f"❌ Ошибка обработки даты публикации '{publication_date}' в строке {index + 2}: {e}")
                        filtered_by_empty_date += 1
                        continue
                
                review_data = {
                    'text': review_text,
                    'status': status,
                    'row': index + 2,  # +2 потому что индекс 0-based, а строки 1-based + заголовок
                    'url': url,
                    'card_id': card_id,  # Сохраняем ID карточки
                    'publication_date': publication_date if has_publication_date_column else None
                }
                
                urls_data[url].append(review_data)
                processed_rows += 1
            
            # Выводим статистику фильтрации
            thread_print(f"📊 Статистика фильтрации листа '{sheet_name}':")
            thread_print(f"   📝 Всего строк: {total_rows}")
            thread_print(f"   ❌ Отфильтровано пустых (без id карточки или текста): {filtered_by_empty}")
            thread_print(f"   ❌ Отфильтровано по статусу (не 'Модерация' и не 'Размещен'): {filtered_by_status}")
            
            if has_publication_date_column:
                thread_print(f"   ❌ Отфильтровано без даты публикации: {filtered_by_empty_date}")
                thread_print(f"   ❌ Отфильтровано по дате (старше {max_days_back} дней): {filtered_by_date}")
                if auto_rejected_count > 0:
                    thread_print(f"   🚫 Автоматически отклонено старых отзывов: {auto_rejected_count}")
                thread_print(f"   📅 Пороговая дата: {cutoff_date.strftime('%d.%m.%Y')}")
            
            thread_print(f"   ✅ Принято к обработке: {processed_rows}")
            thread_print(f"   🌐 Уникальных URL: {len(urls_data)}")
            
            return {'urls': dict(urls_data), 'error': None}
            
        except Exception as e:
            error_msg = f"Ошибка чтения листа '{sheet_name}': {e}"
            thread_print(f"❌ {error_msg}")
            return {'urls': {}, 'error': error_msg}
    
    def process_url_reviews(self, url: str, card_id: str, sheet_reviews: List[Dict], sheet_name: str,
                          device_type: str = "mobile", max_days_back: int = 30,
                          max_reviews_limit: int = 100) -> Dict[str, Any]:
        """
        Обрабатывает отзывы для конкретного URL
        
        Args:
            url: URL для парсинга
            card_id: ID карточки (уже известен из таблицы)
            sheet_reviews: Список отзывов из таблицы
            sheet_name: Имя листа
            device_type: Тип устройства
            max_days_back: Максимальное количество дней назад
            max_reviews_limit: Максимальное количество отзывов
            
        Returns:
            Словарь с результатами обработки
        """
        thread_print(f"🌐 Обработка URL: {url}")
        
        try:
            # Определяем платформу по URL и получаем обработчик
            handler = get_handler_for_url(url)
            if not handler:
                return {
                    'url': url,
                    'sheet_name': sheet_name,
                    'parsing_success': False,
                    'parsed_reviews': [],
                    'new_reviews': [],
                    'matches': [],
                    'updates': [],
                    'error': f"Платформа не поддерживается для URL: {url}"
                }
            
            thread_print(f"📌 Платформа: {handler.name}")
            
            # Получаем отзывы через обработчик платформы
            platform_result = handler.get_reviews(
                url=url,
                card_id=card_id,
                device_type=device_type,
                max_days_back=max_days_back,
                max_reviews_limit=max_reviews_limit,
                use_proxy=True,
                max_retries=3,
            )
            
            if not platform_result or not platform_result.get('success', False):
                error_msg = f"Ошибка парсинга URL {url}"
                if platform_result and platform_result.get('error'):
                    error_msg += f": {platform_result['error']}"
                
                return {
                    'url': url,
                    'sheet_name': sheet_name,
                    'parsing_success': False,
                    'parsed_reviews': [],
                    'new_reviews': [],
                    'matches': [],
                    'updates': [],
                    'error': error_msg
                }
            
            # Получаем информацию о результатах парсинга
            reviews_found = platform_result.get('reviews_found', 0)
            
            result = {
                'url': url,
                'sheet_name': sheet_name,
                'parsing_success': True,
                'parsed_reviews': platform_result.get('reviews', []),
                'new_reviews': [],
                'matches': [],
                'updates': [],
                'error': None
            }
            
            thread_print(f"✅ Спаршено отзывов: {reviews_found}")
            
            # Используем отзывы напрямую из результата парсинга
            parsed_reviews = platform_result.get('reviews', [])
            result['new_reviews'] = parsed_reviews
            result['parsed_reviews'] = parsed_reviews
            thread_print(f"📝 Отзывов для проверки совпадений: {len(parsed_reviews)}")
            
            # Ищем совпадения только среди новых отзывов
            matches = self.text_matcher.find_matches_in_reviews(
                sheet_reviews, 
                result['new_reviews']
            )
            
            result['matches'] = matches
            thread_print(f"🎯 Найдено совпадений: {len(matches)}")
            
            # Показываем детали совпадений
            for i, match in enumerate(matches, 1):
                thread_print(f"✅ Найдено совпадение {match['similarity_percent']:.1f}%:")
                thread_print(f"   📄 Лист: строка {match['sheet_review']['row']}")
                thread_print(f"   📝 Текст из таблицы: {match['sheet_review']['text'][:100]}...")
                thread_print(f"   🌐 Текст с карточки: {match['parsed_review']['text'][:100]}...")
            
            # Обновляем статусы в Google Sheets
            updates = []
            matched_sheet_reviews = {m['sheet_review']['row'] for m in matches}
            
            if matches:
                thread_print(f"📝 Обновляем статусы в Google Sheets для {len(matches)} совпадений...")
                try:
                    for match in matches:
                        sheet_review = match['sheet_review']
                        parsed_review = match['parsed_review']
                        # Только для "Модерация" -> "Размещен" (для "Размещен" совпадение = отзыв на месте, ничего не меняем)
                        if sheet_review.get('status') == 'Модерация':
                            publication_date = self._format_date_for_sheets(parsed_review.get('date', ''))
                            thread_print(f"📝 Совпадение добавлено для батчевого размещения: строка {sheet_review['row']}")
                            update_data = {
                                'spreadsheet_url': self.spreadsheet_url,
                                'sheet_name': sheet_name,
                                'row': sheet_review['row'],
                                'status': 'Размещен',
                                'date': publication_date,
                                'similarity_percent': match['similarity_percent']
                            }
                            updates.append(update_data)
                except Exception as e:
                    thread_print(f"❌ Ошибка при обновлении Google Sheets: {e}")
                    result['sheets_update_error'] = str(e)
            
            # Для "Размещен": если отзыв НЕ найден на карточке -> статус "Удален"
            for sheet_review in sheet_reviews:
                if sheet_review.get('status') == 'Размещен' and sheet_review['row'] not in matched_sheet_reviews:
                    thread_print(f"🗑️ Отзыв удалён с карточки: строка {sheet_review['row']} -> 'Удален'")
                    update_data = {
                        'spreadsheet_url': self.spreadsheet_url,
                        'sheet_name': sheet_name,
                        'row': sheet_review['row'],
                        'status': 'Удален',
                        'date': None,
                        'similarity_percent': 0
                    }
                    updates.append(update_data)
            
            if not updates:
                thread_print("ℹ️ Нет обновлений статусов")
            
            result['updates'] = updates
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка обработки URL {url}: {e}"
            result['error'] = error_msg
            thread_print(f"❌ {error_msg}")
            return result
    
    def process_sheet_worker(self, sheet_name: str, worker_id: int, 
                           device_type: str = "mobile", max_days_back: int = 30,
                           max_reviews_limit: int = 100, delay_between_urls: int = 3,
                           recheck_days: int = 30):
        """
        Обрабатывает лист в отдельном потоке
        
        Args:
            sheet_name: Имя листа для обработки
            worker_id: ID потока
            device_type: Тип устройства
            max_days_back: Максимальное количество дней назад
            max_reviews_limit: Максимальное количество отзывов
            delay_between_urls: Задержка между URL-ами
        """
        thread_print(f"🚀 Поток {worker_id}: Начинаем обработку листа '{sheet_name}'")
        
        try:
            # Получаем данные листа
            sheet_data = self.get_sheet_data(sheet_name, max_days_back, recheck_days)
            
            if sheet_data['error']:
                self.results['errors'].append({
                    'sheet': sheet_name,
                    'error': sheet_data['error']
                })
                return
            
            urls_data = sheet_data['urls']
            
            if not urls_data:
                thread_print(f"⚠️ Поток {worker_id}: Нет URL для обработки в листе '{sheet_name}'")
                return
            
            thread_print(f"📊 Поток {worker_id}: Найдено {len(urls_data)} уникальных URL")
            
            # Обрабатываем каждый URL
            all_updates = []
            
            for i, (url, sheet_reviews) in enumerate(urls_data.items(), 1):
                thread_print(f"🔄 Поток {worker_id}: URL {i}/{len(urls_data)}")
                
                # Получаем ID карточки из первого отзыва (все отзывы одного URL имеют одинаковый card_id)
                card_id = sheet_reviews[0]['card_id'] if sheet_reviews else None
                
                # Для отзывов «Размещен» парсим глубже (recheck_days), иначе — max_days_back
                has_placed = any(r.get('status') == 'Размещен' for r in sheet_reviews)
                effective_max_days = max(max_days_back, recheck_days) if has_placed else max_days_back
                
                # Обрабатываем URL
                url_result = self.process_url_reviews(
                    url=url,
                    card_id=card_id,
                    sheet_reviews=sheet_reviews,
                    sheet_name=sheet_name,
                    device_type=device_type,
                    max_days_back=effective_max_days,
                    max_reviews_limit=max_reviews_limit
                )
                
                # Собираем статистику
                self.results['processed_urls'] += 1
                
                if url_result['matches']:
                    self.results['total_matches'] += len(url_result['matches'])
                all_updates.extend(url_result['updates'])
                
                if url_result['error']:
                    self.results['errors'].append({
                        'sheet': sheet_name,
                        'url': url,
                        'error': url_result['error']
                    })
                
                # Пауза между URL-ами
                if i < len(urls_data):
                    time.sleep(delay_between_urls)
            
            # Статусы будут обновлены централизованно в ЭТАПЕ 3
            if all_updates:
                thread_print(f"📝 Поток {worker_id}: Накоплено {len(all_updates)} обновлений для финального батча")
            
            # Обновляем статистику
            with self.lock:
                self.results['processed_sheets'] += 1
                self.results['total_urls'] += len(urls_data)
            
            thread_print(f"✅ Поток {worker_id}: Лист '{sheet_name}' обработан")
            
        except Exception as e:
            error_msg = f"Критическая ошибка в потоке {worker_id} для листа '{sheet_name}': {e}"
            thread_print(f"❌ {error_msg}")
            self.results['errors'].append({
                'sheet': sheet_name,
                'error': error_msg
            })
    
    def run(self, device_type: str = "mobile", max_days_back: int = 30,
            max_reviews_limit: int = 100, delay_between_workers: int = 2,
            delay_between_urls: int = 3, recheck_days: int = 30) -> Dict[str, Any]:
        """
        Запускает интегрированный парсинг
        
        Args:
            device_type: Тип устройства ("mobile" или "desktop")
            max_days_back: Максимальное количество дней назад
            max_reviews_limit: Максимальное количество отзывов
            delay_between_workers: Задержка между запуском потоков
            delay_between_urls: Задержка между URL-ами
            
        Returns:
            Словарь с результатами работы
        """
        start_time = time.time()
        
        thread_print("🚀 Запуск интегрированного парсера...")
        thread_print(f"📊 Настройки:")
        thread_print(f"   🎯 Порог совпадения: {self.similarity_threshold * 100}%")
        thread_print(f"   👥 Максимальное количество потоков: {self.max_workers}")
        thread_print(f"   📱 Тип устройства: {device_type}")
        thread_print(f"   📅 Дней назад: {max_days_back}")
        thread_print(f"   📝 Максимум отзывов: {max_reviews_limit}")
        
        # Мониторинг ресурсов перед запуском
        thread_print("📊 Мониторинг ресурсов ПЕРЕД запуском потоков:")
        initial_resources = monitor_system_resources()
        
        try:
            # Получаем список всех листов
            spreadsheet_id = self.sheets_reader.extract_spreadsheet_id(self.spreadsheet_url)
            sheet_names = self.sheets_reader.get_all_sheet_names_api(spreadsheet_id)
            
            if not sheet_names:
                return {
                    'success': False,
                    'error': 'Не удалось получить список листов',
                    'results': self.results
                }
            
            # Отладочная информация
            thread_print(f"📄 Найдено листов: {len(sheet_names)}")
            for i, sheet_name in enumerate(sheet_names, 1):
                thread_print(f"   {i}. '{sheet_name}'")
            
            self.results['total_sheets'] = len(sheet_names)
            
            # Ограничиваем количество потоков
            actual_workers = min(self.max_workers, len(sheet_names))
            thread_print(f"👥 Используем потоков: {actual_workers}")
            
            # Распределяем листы между потоками
            sheet_batches = []
            for i in range(actual_workers):
                batch = []
                for j in range(i, len(sheet_names), actual_workers):
                    batch.append(sheet_names[j])
                if batch:
                    sheet_batches.append(batch)
            
            # Инициализируем общее количество URL (будет подсчитано в процессе)
            self.results['total_urls'] = 0
            thread_print(f"🌐 Количество URL будет подсчитано в процессе обработки")
            
            # Запускаем потоки
            threads = []
            
            def process_sheet_batch(sheet_batch: List[str], worker_id: int, delay: int = 0):
                """Обрабатывает батч листов в отдельном потоке"""
                if delay > 0:
                    time.sleep(delay)
                
                thread_print(f"🧵 Поток {worker_id}: Начало обработки {len(sheet_batch)} листов")
                
                for sheet_index, sheet_name in enumerate(sheet_batch, 1):
                    thread_print(f"🧵 Поток {worker_id}: Лист {sheet_index}/{len(sheet_batch)} - {sheet_name}")
                    
                    try:
                        self.process_sheet_worker(
                            sheet_name=sheet_name,
                            worker_id=worker_id,
                            device_type=device_type,
                            max_days_back=max_days_back,
                            max_reviews_limit=max_reviews_limit,
                            delay_between_urls=delay_between_urls,
                            recheck_days=recheck_days
                        )
                    except Exception as e:
                        thread_print(f"🧵 Поток {worker_id}: Ошибка обработки листа {sheet_name}: {e}")
                        self.results['errors'].append({
                            'sheet': sheet_name,
                            'error': str(e),
                            'worker_id': worker_id
                        })
                
                thread_print(f"🧵 Поток {worker_id}: Батч завершен")
            
            # Запускаем потоки с задержками
            for i, batch in enumerate(sheet_batches):
                delay = i * delay_between_workers
                thread = Thread(
                    target=process_sheet_batch,
                    args=(batch, i + 1, delay)
                )
                threads.append(thread)
                thread.start()
                thread_print(f"🚀 Запущен поток {i + 1}/{len(sheet_batches)}")
            
            # Мониторинг ресурсов после запуска всех потоков
            thread_print("📊 Мониторинг ресурсов ПОСЛЕ запуска всех потоков:")
            post_start_resources = monitor_system_resources()
            
            # Ожидаем завершения всех потоков
            for thread in threads:
                thread.join()
            
            # Мониторинг ресурсов после завершения всех потоков
            thread_print("📊 Мониторинг ресурсов ПОСЛЕ завершения всех потоков:")
            final_resources = monitor_system_resources()
            
            # Подсчитываем общее время
            total_time = time.time() - start_time
            
            # Формируем итоговый отчет
            thread_print("\n" + "="*60)
            thread_print("📊 ИТОГОВЫЙ ОТЧЕТ")
            thread_print("="*60)
            thread_print(f"📄 Листов обработано: {self.results['processed_sheets']}/{self.results['total_sheets']}")
            thread_print(f"🌐 URL обработано: {self.results['processed_urls']}/{self.results['total_urls']}")
            thread_print(f"🎯 Найдено совпадений: {self.results['total_matches']}")
            thread_print(f"📝 Обновлено статусов: {self.results['total_updates']}")
            thread_print(f"❌ Ошибок: {len(self.results['errors'])}")
            thread_print(f"⏱️ Общее время: {total_time:.1f} секунд")
            
            if self.results['errors']:
                thread_print("\n❌ ОШИБКИ:")
                for error in self.results['errors'][:5]:  # Показываем первые 5 ошибок
                    thread_print(f"   • {error.get('sheet', 'Unknown')}: {error.get('error', 'Unknown error')}")
                
                if len(self.results['errors']) > 5:
                    thread_print(f"   ... и еще {len(self.results['errors']) - 5} ошибок")
            
            return {
                'success': True,
                'execution_time': total_time,
                'results': self.results
            }
            
        except Exception as e:
            error_msg = f"Критическая ошибка интегрированного парсера: {e}"
            thread_print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'results': self.results
            }


def main():
    """Основная функция для запуска интегрированного парсера"""
    
    # Настройка логирования в самом начале
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск интегрированного парсера Google Sheets + Яндекс.Карт")
    logger.info("="*60)
    
    # Инициализация с очисткой старых профилей
    initialize_profiles_cleanup()
    
    if not SPREADSHEETS:
        logger.error("❌ Не настроены таблицы для обработки!")
        logger.error("Добавьте URL таблиц в список SPREADSHEETS в настройках")
        return
    
    logger.info(f"📊 Найдено таблиц для обработки: {len(SPREADSHEETS)}")
    
    # ЭТАП 1: БАТЧЕВОЕ ОТКЛОНЕНИЕ старых отзывов ДО парсинга
    logger.info(f"\n🚀 ЭТАП 1: БАТЧЕВОЕ ОТКЛОНЕНИЕ старых отзывов во всех таблицах")
    logger.info("="*70)
    
    from sheets_updater import SheetsUpdater
    batch_updater = SheetsUpdater(CREDENTIALS_FILE)
    
    total_rejections = 0
    for i, spreadsheet_url in enumerate(SPREADSHEETS, 1):
        logger.info(f"📋 Обрабатываем таблицу {i}/{len(SPREADSHEETS)}")
        
        rejection_results = batch_updater.batch_reject_old_reviews(
            spreadsheet_url=spreadsheet_url,
            max_days_back=MAX_DAYS_BACK
        )
        
        total_rejections += rejection_results['success']
        logger.info(f"✅ Таблица {i}: отклонено {rejection_results['success']} старых отзывов")
    
    logger.info(f"\n🎯 ИТОГ ЭТАПА 1: Всего отклонено {total_rejections} старых отзывов")
    logger.info("="*70)
    
    # ЭТАП 2: Сбор URL для парсинга (после отклонения старых)
    logger.info(f"\n📋 ЭТАП 2: Сбор URL для парсинга...")
    
    # Собираем ВСЕ URL из ВСЕХ листов ВСЕХ таблиц
    all_urls = []  # Список кортежей (spreadsheet_url, sheet_name, url, sheet_reviews)
    reader = GoogleSheetsReader(CREDENTIALS_FILE)
    
    print("\n📋 Сбор информации о всех URL...")
    total_sheets = 0
    total_urls_count = 0
    
    for i, spreadsheet_url in enumerate(SPREADSHEETS, 1):
        print(f"🔗 Таблица {i}/{len(SPREADSHEETS)}: {spreadsheet_url}")
        
        try:
            # Получаем ID таблицы и список листов
            spreadsheet_id = reader.extract_spreadsheet_id(spreadsheet_url)
            sheet_names = reader.get_all_sheet_names_api(spreadsheet_id)
            
            if not sheet_names:
                print(f"⚠️ Таблица {i}: Нет доступных листов")
                continue
            
            print(f"📄 Найдено листов: {len(sheet_names)}")
            total_sheets += len(sheet_names)
            
            # Обрабатываем каждый лист и собираем URL
            for sheet_name in sheet_names:
                print(f"   📋 Анализируем лист: {sheet_name}")
                
                try:
                    # Создаем временный парсер для получения данных листа
                    temp_parser = IntegratedParser(
                        spreadsheet_url=spreadsheet_url,
                        credentials_file=CREDENTIALS_FILE,
                        similarity_threshold=SIMILARITY_THRESHOLD,
                        max_workers=1
                    )
                    
                    # Получаем данные листа
                    sheet_data = temp_parser.get_sheet_data(sheet_name, MAX_DAYS_BACK, RECHECK_DAYS)
                    
                    if sheet_data['error']:
                        print(f"   ⚠️ Ошибка в листе {sheet_name}: {sheet_data['error']}")
                        continue
                    
                    urls_data = sheet_data['urls']
                    
                    if not urls_data:
                        print(f"   ℹ️ Нет URL для обработки в листе {sheet_name}")
                        continue
                    
                    # Добавляем все URL из этого листа
                    for url, sheet_reviews in urls_data.items():
                        all_urls.append((spreadsheet_url, sheet_name, url, sheet_reviews))
                        total_urls_count += 1
                    
                    print(f"   ✅ Найдено URL: {len(urls_data)}")
                    
                except Exception as e:
                    print(f"   ❌ Ошибка анализа листа {sheet_name}: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Ошибка при обработке таблицы {i}: {e}")
            continue
    
    if not all_urls:
        print("❌ Не найдено ни одного URL для обработки!")
        return
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   📋 Всего таблиц: {len(SPREADSHEETS)}")
    print(f"   📄 Всего листов: {total_sheets}")
    print(f"   🌐 Всего URL: {len(all_urls)}")
    print(f"   👥 Максимум потоков: {MAX_WORKERS}")
    print(f"   🎯 Будет использовано потоков: {min(MAX_WORKERS, len(all_urls))}")
    
    # Общие результаты
    total_results = {
        'total_spreadsheets': len(SPREADSHEETS),
        'total_sheets': total_sheets,
        'processed_sheets': total_sheets,  # Все листы проанализированы
        'total_urls': len(all_urls),
        'processed_urls': 0,
        'total_matches': 0,
        'total_updates': 0,
        'placement_updates': [],  # Накопитель для финального батчевого размещения
        'total_time': 0,
        'errors': []
    }
    
    start_time = time.time()
    
    # Мониторинг ресурсов перед запуском
    print("📊 Мониторинг ресурсов ПЕРЕД запуском потоков:")
    initial_resources = monitor_system_resources()
    
    # Определяем количество потоков
    actual_workers = min(MAX_WORKERS, len(all_urls))
    print(f"👥 Используем потоков: {actual_workers}")
    
    # Распределяем URL между потоками РАВНОМЕРНО
    url_batches = []
    for i in range(actual_workers):
        batch = []
        for j in range(i, len(all_urls), actual_workers):
            batch.append(all_urls[j])
        if batch:
            url_batches.append(batch)
    
    print(f"📦 Распределение URL по потокам:")
    for i, batch in enumerate(url_batches, 1):
        print(f"   🧵 Поток {i}: {len(batch)} URL")
    
    # Блокировка для многопоточности
    results_lock = threading.Lock()
    
    def process_url_batch(url_batch: List[tuple], worker_id: int, delay: int = 0):
        """Обрабатывает батч URL в отдельном потоке"""
        if delay > 0:
            time.sleep(delay)
        
        print(f"🧵 Поток {worker_id}: Начало обработки {len(url_batch)} URL")
        
        # Локальные результаты потока
        local_results = {
            'processed_urls': 0,
            'total_matches': 0,
            'total_updates': 0,
            'placement_updates': [],  # Накопитель для батчевого размещения
            'errors': []
        }
        
        for url_index, (spreadsheet_url, sheet_name, url, sheet_reviews) in enumerate(url_batch, 1):
            print(f"🧵 Поток {worker_id}: URL {url_index}/{len(url_batch)}")
            print(f"   📋 Лист: {sheet_name}")
            print(f"   🌐 URL: {url}")
            
            try:
                # Создаем парсер для конкретной таблицы
                parser = IntegratedParser(
                    spreadsheet_url=spreadsheet_url,
                    credentials_file=CREDENTIALS_FILE,
                    similarity_threshold=SIMILARITY_THRESHOLD,
                    max_workers=1
                )
                
                # Получаем ID карточки из первого отзыва
                card_id = sheet_reviews[0]['card_id'] if sheet_reviews else None
                
                # Для отзывов «Размещен» парсим глубже (RECHECK_DAYS), иначе — MAX_DAYS_BACK
                has_placed = any(r.get('status') == 'Размещен' for r in sheet_reviews)
                effective_max_days = max(MAX_DAYS_BACK, RECHECK_DAYS) if has_placed else MAX_DAYS_BACK
                
                # Обрабатываем конкретный URL
                url_result = parser.process_url_reviews(
                    url=url,
                    card_id=card_id,
                    sheet_reviews=sheet_reviews,
                    sheet_name=sheet_name,
                    device_type=DEVICE_TYPE,
                    max_days_back=effective_max_days,
                    max_reviews_limit=MAX_REVIEWS_LIMIT
                )
                
                # Собираем результаты
                local_results['processed_urls'] += 1
                
                if url_result['matches']:
                    local_results['total_matches'] += len(url_result['matches'])
                local_results['total_updates'] += len(url_result.get('updates', []))
                
                # Накапливаем обновления (Размещен + Удален)
                for update in url_result.get('updates', []):
                    placement_data = {
                        'spreadsheet_url': spreadsheet_url,
                        'sheet_name': sheet_name,
                        'row': update.get('row'),
                        'status': update.get('status', 'Размещен'),
                        'date': update.get('date')
                    }
                    local_results['placement_updates'].append(placement_data)
                
                if url_result['error']:
                    local_results['errors'].append({
                        'sheet': sheet_name,
                        'url': url,
                        'error': url_result['error'],
                        'worker_id': worker_id
                    })
                
                # Пауза между URL-ами
                if url_index < len(url_batch):
                    time.sleep(DELAY_BETWEEN_URLS)
                
            except Exception as e:
                error_msg = f"Ошибка обработки URL {url}: {e}"
                print(f"🧵 Поток {worker_id}: ❌ {error_msg}")
                local_results['errors'].append({
                    'sheet': sheet_name,
                    'url': url,
                    'error': str(e),
                    'worker_id': worker_id
                })
        
        # Обновляем общие результаты
        with results_lock:
            total_results['processed_urls'] += local_results['processed_urls']
            total_results['total_matches'] += local_results['total_matches']
            total_results['total_updates'] += local_results['total_updates']
            total_results['placement_updates'].extend(local_results['placement_updates'])
            total_results['errors'].extend(local_results['errors'])
        
        print(f"🧵 Поток {worker_id}: Батч завершен")
        print(f"   🌐 Обработано URL: {local_results['processed_urls']}")
        print(f"   🎯 Найдено совпадений: {local_results['total_matches']}")
        print(f"   📝 Обновлено статусов: {local_results['total_updates']}")
    
    # Запускаем потоки
    threads = []
    print(f"\n🚀 Запуск {len(url_batches)} потоков...")
    
    for i, batch in enumerate(url_batches):
        delay = i * DELAY_BETWEEN_WORKERS
        thread = threading.Thread(
            target=process_url_batch,
            args=(batch, i + 1, delay)
        )
        threads.append(thread)
        thread.start()
        print(f"🚀 Запущен поток {i + 1}/{len(url_batches)}")
    
    # Мониторинг ресурсов после запуска всех потоков
    print("📊 Мониторинг ресурсов ПОСЛЕ запуска всех потоков:")
    post_start_resources = monitor_system_resources()
    
    # Ожидаем завершения всех потоков
    for thread in threads:
        thread.join()
    
    # Мониторинг ресурсов после завершения всех потоков
    print("📊 Мониторинг ресурсов ПОСЛЕ завершения всех потоков:")
    final_resources = monitor_system_resources()
    
    # Подсчитываем общее время
    total_results['total_time'] = time.time() - start_time
    
    # Выводим итоговые результаты
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ПО ВСЕМ ТАБЛИЦАМ И ЛИСТАМ")
    print("="*60)
    print(f"📋 Всего таблиц: {total_results['total_spreadsheets']}")
    print(f"📄 Всего листов: {total_results['total_sheets']}")
    print(f"✅ Обработано листов: {total_results['processed_sheets']}")
    print(f"🌐 Всего URL: {total_results['total_urls']}")
    print(f"✅ Обработано URL: {total_results['processed_urls']}")
    print(f"🎯 Всего совпадений: {total_results['total_matches']}")
    print(f"📝 Всего обновлений: {total_results['total_updates']}")
    print(f"⏱️ Общее время: {total_results['total_time']:.1f} секунд")
    print(f"👥 Использовано потоков: {actual_workers}")
    
    # ЭТАП 3: БАТЧЕВОЕ ОБНОВЛЕНИЕ статусов (Размещен + Удален) ПОСЛЕ парсинга
    if total_results['placement_updates']:
        print(f"\n🚀 ЭТАП 3: БАТЧЕВОЕ ОБНОВЛЕНИЕ статусов ({len(total_results['placement_updates'])} записей)")
        print("="*70)
        
        placement_results = batch_updater.batch_update_reviews(total_results['placement_updates'])
        
        print(f"🎯 ИТОГ ЭТАПА 3: Обновлено {placement_results['success']} записей")
        if placement_results['failed'] > 0:
            print(f"❌ Ошибок размещения: {placement_results['failed']}")
        print("="*70)
    else:
        print(f"\nℹ️ ЭТАП 3: Нет найденных совпадений для размещения")
    
    if total_results['errors']:
        print(f"\n❌ Ошибки ({len(total_results['errors'])}):")
        for error in total_results['errors'][:10]:  # Показываем первые 10 ошибок
            sheet = error.get('sheet', 'Unknown')
            url = error.get('url', 'Unknown')
            error_msg = error.get('error', 'Unknown error')
            worker_id = error.get('worker_id', 'Unknown')
            print(f"   • Поток {worker_id}, Лист '{sheet}': {error_msg}")
        
        if len(total_results['errors']) > 10:
            print(f"   ... и еще {len(total_results['errors']) - 10} ошибок")
    
    if total_results['processed_urls'] == total_results['total_urls']:
        print(f"\n🎉 Все URL обработаны успешно!")
    else:
        print(f"\n⚠️ Обработано {total_results['processed_urls']} из {total_results['total_urls']} URL")
    
    print(f"\n📈 Производительность:")
    if total_results['total_time'] > 0:
        urls_per_second = total_results['processed_urls'] / total_results['total_time']
        print(f"   🌐 URL в секунду: {urls_per_second:.2f}")
        print(f"   ⚡ Среднее время на URL: {total_results['total_time'] / max(total_results['processed_urls'], 1):.1f} сек")
        print(f"   🏆 Эффективность потоков: {(total_results['processed_urls'] / (actual_workers * total_results['total_time'] / 60)):.1f} URL/поток/мин")
    
    # Финальная очистка всех профилей
    cleanup_all_profiles()



# Импортируем все настройки из config.py
from config import (
    SPREADSHEETS, CREDENTIALS_FILE, 
    DEVICE_TYPE, WAIT_TIME, MAX_DAYS_BACK, MAX_REVIEWS_LIMIT, 
    USE_PROXY, SIMILARITY_THRESHOLD, MAX_WORKERS, 
    DELAY_BETWEEN_WORKERS, DELAY_BETWEEN_URLS, RECHECK_DAYS
)

# ============================================================================


if __name__ == "__main__":
    main() 