"""
Модуль для обновления статусов в Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
from thread_logger import thread_print
import re
from datetime import datetime

class SheetsUpdater:
    """Класс для обновления статусов в Google Sheets"""
    
    def __init__(self, credentials_file: str = "credentials.json"):
        """
        Инициализация обновлятора Google Sheets
        
        Args:
            credentials_file: Путь к файлу с учетными данными
        """
        self.credentials_file = credentials_file
        self.gc = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Настройка учетных данных для Google API"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(creds)
            thread_print("✅ Учетные данные для обновления Google Sheets настроены")
            
        except Exception as e:
            thread_print(f"❌ Ошибка настройки учетных данных: {e}")
            self.gc = None
    
    def extract_spreadsheet_id(self, url: str) -> str:
        """Извлечение ID таблицы из URL"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Не удалось извлечь ID таблицы из URL")
    
    def update_review_status(self, spreadsheet_url: str, sheet_name: str, 
                           row_number: int,             new_status: str, 
                           publication_date: Optional[str] = None,
                           last_check: Optional[str] = None,
                           error_text: Optional[str] = None) -> bool:
        """
        Обновляет статус отзыва в Google Sheets.
        Опционально обновляет «Последняя проверка» и «Ошибки».
        """
        if not self.gc:
            thread_print("❌ Google Sheets API не настроен")
            return False
        
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            headers = worksheet.row_values(1)
            
            status_col = None
            date_col = None
            last_check_col = None
            error_col = None
            
            for i, header in enumerate(headers, 1):
                if header == "Статус":
                    status_col = i
                elif header == "Дата публикации":
                    date_col = i
                elif header == "Последняя проверка":
                    last_check_col = i
                elif header == "Ошибки":
                    error_col = i
            
            if not status_col:
                thread_print(f"❌ Колонка 'Статус' не найдена в листе '{sheet_name}'")
                return False
            
            worksheet.update_cell(row_number, status_col, new_status)
            thread_print(f"✅ Статус обновлен: лист '{sheet_name}', строка {row_number} -> '{new_status}'")
            
            if publication_date and date_col:
                worksheet.update_cell(row_number, date_col, publication_date)
                thread_print(f"✅ Дата публикации обновлена: строка {row_number} -> '{publication_date}'")
            
            if last_check_col is not None and last_check is not None:
                worksheet.update_cell(row_number, last_check_col, last_check)
            if error_col is not None:
                worksheet.update_cell(row_number, error_col, error_text or "")
            
            return True
            
        except Exception as e:
            thread_print(f"❌ Ошибка обновления статуса: {e}")
            return False

    def update_check_info(self, spreadsheet_url: str, sheet_name: str,
                         row_number: int, last_check: str, error_text: str = "") -> bool:
        """
        Обновляет только «Последняя проверка» и «Ошибки» (без статуса).
        Если колонок нет — возвращает True (без ошибки).
        """
        if not self.gc:
            return False
        try:
            last_check_col = self.find_column_index(spreadsheet_url, sheet_name, "Последняя проверка")
            error_col = self.find_column_index(spreadsheet_url, sheet_name, "Ошибки")
            if not last_check_col and not error_col:
                return True
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            if last_check_col:
                worksheet.update_cell(row_number, last_check_col, last_check)
            if error_col:
                worksheet.update_cell(row_number, error_col, error_text or "")
            return True
        except Exception as e:
            thread_print(f"❌ Ошибка обновления проверки: {e}")
            return False
    
    def batch_update_reviews(self, updates: List[Dict]) -> Dict[str, int]:
        """
        Пакетное обновление статусов и/или «Последняя проверка» + «Ошибки».
        Каждый update: row, last_check, error; опционально status, date.
        Колонки «Последняя проверка» и «Ошибки» создаются автоматически, если отсутствуют.
        Использует один batch_update на лист вместо цикла по записям.
        """
        if not updates:
            thread_print("⚠️ Нет обновлений для выполнения")
            return {'success': 0, 'failed': 0}
        
        if not self.gc:
            thread_print("❌ Google Sheets API не настроен")
            return {'success': 0, 'failed': len(updates)}
        
        # Убеждаемся, что колонки есть во всех затронутых листах
        seen_sheets = set()
        for update in updates:
            key = (update.get('spreadsheet_url'), update.get('sheet_name'))
            if key not in seen_sheets and key[0] and key[1]:
                seen_sheets.add(key)
                self.ensure_columns_exist(key[0], key[1])
        
        # Группируем обновления по (spreadsheet_url, sheet_name)
        grouped_updates = {}
        skipped = 0
        for update in updates:
            key = (update.get('spreadsheet_url'), update.get('sheet_name'))
            if key[0] and key[1]:
                if key not in grouped_updates:
                    grouped_updates[key] = []
                grouped_updates[key].append(update)
            else:
                skipped += 1
        
        results = {'success': 0, 'failed': skipped}
        thread_print(f"📝 Начинаем пакетное обновление {len(updates)} записей...")
        
        for (spreadsheet_url, sheet_name), sheet_updates in grouped_updates.items():
            try:
                spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
                spreadsheet = self.gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(sheet_name)
                headers = worksheet.row_values(1)
                
                status_col = None
                date_col = None
                last_check_col = None
                error_col = None
                for i, header in enumerate(headers, 1):
                    if header == "Статус":
                        status_col = i
                    elif header == "Дата публикации":
                        date_col = i
                    elif header == "Последняя проверка":
                        last_check_col = i
                    elif header == "Ошибки":
                        error_col = i
                
                batch_data = []
                batch_aborted = False
                for update in sheet_updates:
                    row_number = update['row']
                    last_check = update.get('last_check', '')
                    error_text = update.get('error', '') or ''
                    status = update.get('status')
                    date = update.get('date')
                    
                    if status is not None:
                        if not status_col:
                            thread_print(f"❌ Колонка 'Статус' не найдена в листе '{sheet_name}'")
                            results['failed'] += len(sheet_updates)
                            batch_aborted = True
                            break
                        batch_data.append({
                            'range': f'{self._get_column_letter(status_col)}{row_number}',
                            'values': [[status]]
                        })
                        if date and date_col:
                            batch_data.append({
                                'range': f'{self._get_column_letter(date_col)}{row_number}',
                                'values': [[date]]
                            })
                    
                    if last_check_col is not None:
                        batch_data.append({
                            'range': f'{self._get_column_letter(last_check_col)}{row_number}',
                            'values': [[last_check]]
                        })
                    if error_col is not None:
                        batch_data.append({
                            'range': f'{self._get_column_letter(error_col)}{row_number}',
                            'values': [[error_text]]
                        })
                
                if batch_data and not batch_aborted:
                    worksheet.batch_update(batch_data)
                    results['success'] += len(sheet_updates)
                    thread_print(f"✅ Лист '{sheet_name}': обновлено {len(sheet_updates)} записей")
                else:
                    results['failed'] += len(sheet_updates)
                    
            except Exception as e:
                thread_print(f"❌ Ошибка батчевого обновления в листе '{sheet_name}': {e}")
                results['failed'] += len(sheet_updates)
        
        thread_print(f"🎯 Пакетное обновление завершено: {results['success']} успешно, {results['failed']} ошибок")
        return results
    
    def get_cell_value(self, spreadsheet_url: str, sheet_name: str, 
                      row: int, col: int) -> Optional[str]:
        """
        Получает значение ячейки
        
        Args:
            spreadsheet_url: URL таблицы
            sheet_name: Название листа
            row: Номер строки (1-based)
            col: Номер колонки (1-based)
            
        Returns:
            Значение ячейки или None при ошибке
        """
        if not self.gc:
            return None
        
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            value = worksheet.cell(row, col).value
            return value
            
        except Exception as e:
            thread_print(f"❌ Ошибка получения значения ячейки: {e}")
            return None
    
    def ensure_columns_exist(self, spreadsheet_url: str, sheet_name: str) -> bool:
        """
        Добавляет колонки «Последняя проверка» и «Ошибки», если их нет.
        Возвращает True при успехе.
        """
        if not self.gc:
            return False
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            headers = worksheet.row_values(1)
            
            cols_to_add = []
            if "Последняя проверка" not in headers:
                cols_to_add.append("Последняя проверка")
            if "Ошибки" not in headers:
                cols_to_add.append("Ошибки")
            
            if not cols_to_add:
                return True
            
            next_col = len(headers) + 1
            for col_name in cols_to_add:
                worksheet.update_cell(1, next_col, col_name)
                thread_print(f"✅ Добавлена колонка '{col_name}' в лист '{sheet_name}'")
                next_col += 1
            return True
        except Exception as e:
            thread_print(f"❌ Ошибка добавления колонок в '{sheet_name}': {e}")
            return False

    def find_column_index(self, spreadsheet_url: str, sheet_name: str, 
                         column_name: str) -> Optional[int]:
        """
        Находит индекс колонки по названию
        
        Args:
            spreadsheet_url: URL таблицы
            sheet_name: Название листа
            column_name: Название колонки
            
        Returns:
            Индекс колонки (1-based) или None если не найдена
        """
        if not self.gc:
            return None
        
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            headers = worksheet.row_values(1)
            
            for i, header in enumerate(headers, 1):
                if header == column_name:
                    return i
            
            return None
            
        except Exception as e:
            thread_print(f"❌ Ошибка поиска колонки: {e}")
            return None
    
    def prepare_update_from_match(self, match: Dict, spreadsheet_url: str, 
                                sheet_name: str) -> Dict:
        """
        Подготавливает данные для обновления на основе найденного совпадения
        
        Args:
            match: Словарь с информацией о совпадении
            spreadsheet_url: URL таблицы
            sheet_name: Название листа
            
        Returns:
            Словарь с данными для обновления
        """
        sheet_review = match['sheet_review']
        parsed_review = match['parsed_review']
        
        # Получаем дату публикации из спаршенного отзыва
        publication_date = parsed_review.get('date', '')
        
        # Форматируем дату если нужно
        if publication_date:
            try:
                # Если дата в формате "X дней назад", преобразуем в обычную дату
                if 'дней назад' in publication_date or 'день назад' in publication_date:
                    # Оставляем как есть - пользователь увидит относительную дату
                    pass
                elif 'месяц назад' in publication_date or 'месяца назад' in publication_date:
                    pass
                # Можно добавить более сложную логику преобразования дат
            except:
                pass
        
        update_data = {
            'spreadsheet_url': spreadsheet_url,
            'sheet_name': sheet_name,
            'row': sheet_review.get('row', 0),
                            'status': 'Размещен',
            'date': publication_date,
            'similarity': match['similarity_percent']
        }
        
        return update_data
    
    def batch_reject_old_reviews(self, spreadsheet_url: str, max_days_back: int = 30) -> Dict[str, int]:
        """
        Батчевое отклонение старых отзывов ДО парсинга
        
        Args:
            spreadsheet_url: URL таблицы Google Sheets
            max_days_back: Количество дней назад для определения старых отзывов
            
        Returns:
            Словарь с результатами: {'success': count, 'failed': count}
        """
        if not self.gc:
            thread_print("❌ Google Sheets API не настроен")
            return {'success': 0, 'failed': 0}
        
        thread_print(f"🚀 БАТЧЕВОЕ ОТКЛОНЕНИЕ старых отзывов (старше {max_days_back} дней)")
        
        results = {'success': 0, 'failed': 0}
        all_rejections = []  # Накопитель ВСЕХ отклонений из ВСЕХ листов
        
        try:
            # Открываем таблицу
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheets = spreadsheet.worksheets()
            
            # Дата для сравнения
            from datetime import datetime, timedelta
            threshold_date = datetime.now() - timedelta(days=max_days_back)
            threshold_date_str = threshold_date.strftime('%d.%m.%Y')
            
            thread_print(f"📅 Пороговая дата: {threshold_date_str}")
            
            # ПЕРВЫЙ ЭТАП: Собираем ВСЕ старые отзывы из ВСЕХ листов
            for worksheet in worksheets:
                sheet_name = worksheet.title
                thread_print(f"📋 Обрабатываем лист: '{sheet_name}'")
                
                try:
                    # Получаем все данные листа
                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        thread_print(f"⚠️ Лист '{sheet_name}' пуст или нет данных")
                        continue
                    
                    headers = all_values[0]
                    
                    # Находим нужные колонки
                    status_col = None
                    date_col = None
                    
                    for i, header in enumerate(headers):
                        if header == "Статус":
                            status_col = i + 1  # gspread использует 1-based индексы
                        elif header == "Дата публикации":
                            date_col = i + 1
                    
                    if not status_col or not date_col:
                        thread_print(f"⚠️ В листе '{sheet_name}' не найдены колонки 'Статус' или 'Дата публикации'")
                        continue
                    
                    # Находим старые отзывы с статусом "Модерация"
                    old_reviews = []
                    for row_idx, row_data in enumerate(all_values[1:], start=2):  # Начинаем с 2 строки
                        if len(row_data) <= max(status_col, date_col) - 1:
                            continue
                        
                        current_status = row_data[status_col - 1] if len(row_data) > status_col - 1 else ""
                        current_date = row_data[date_col - 1] if len(row_data) > date_col - 1 else ""
                        
                        if current_status.strip() == "Модерация" and current_date:
                            try:
                                # Парсим дату публикации
                                review_date = datetime.strptime(current_date.strip(), '%d.%m.%Y')
                                if review_date < threshold_date:
                                    old_reviews.append({
                                        'row': row_idx,
                                        'date': current_date,
                                        'range': f'{self._get_column_letter(status_col)}{row_idx}'
                                    })
                                    thread_print(f"📅 Старый отзыв: строка {row_idx}, дата {current_date}")
                            except ValueError:
                                # Неверный формат даты
                                continue
                    
                    # Накапливаем обновления для последующего батча
                    if old_reviews:
                        for review in old_reviews:
                            all_rejections.append({
                                'worksheet': worksheet,
                                'sheet_name': sheet_name,
                                'range': review['range'],
                                'row': review['row'],
                                'date': review['date']
                            })
                        
                        thread_print(f"📝 Лист '{sheet_name}': найдено {len(old_reviews)} старых отзывов для отклонения")
                        results['success'] += len(old_reviews)
                    else:
                        thread_print(f"ℹ️ Лист '{sheet_name}': нет старых отзывов для отклонения")
                
                except Exception as e:
                    thread_print(f"❌ Ошибка обработки листа '{sheet_name}': {e}")
                    results['failed'] += 1
            
            # ВТОРОЙ ЭТАП: Выполняем ВСЕ накопленные отклонения ОДНИМ БАТЧЕМ
            if all_rejections:
                thread_print(f"\n🚀 УЛЬТРА-БАТЧ: Выполняем {len(all_rejections)} отклонений одним вызовом...")
                
                # Группируем по листам для батчевого обновления
                grouped_by_sheet = {}
                for rejection in all_rejections:
                    sheet_name = rejection['sheet_name']
                    if sheet_name not in grouped_by_sheet:
                        grouped_by_sheet[sheet_name] = {
                            'worksheet': rejection['worksheet'],
                            'updates': []
                        }
                    
                    grouped_by_sheet[sheet_name]['updates'].append({
                        'range': rejection['range'],
                        'values': [['Отклонен']]
                    })
                
                # Выполняем батчевое обновление для каждого листа
                total_updated = 0
                for sheet_name, sheet_data in grouped_by_sheet.items():
                    try:
                        worksheet = sheet_data['worksheet']
                        updates = sheet_data['updates']
                        
                        # Выполняем батчевое обновление для листа
                        worksheet.batch_update(updates)
                        
                        total_updated += len(updates)
                        thread_print(f"✅ Лист '{sheet_name}': батчево обновлено {len(updates)} записей")
                        
                    except Exception as e:
                        thread_print(f"❌ Ошибка батчевого обновления листа '{sheet_name}': {e}")
                        results['failed'] += len(updates)
                        results['success'] -= len(updates)  # Корректируем счетчик
                
                thread_print(f"🎯 УЛЬТРА-БАТЧ завершен: обновлено {total_updated} записей")
            else:
                thread_print("ℹ️ Нет старых отзывов для отклонения во всей таблице")
        
        except Exception as e:
            thread_print(f"❌ Ошибка батчевого отклонения: {e}")
            results['failed'] += 1
        
        thread_print(f"🎯 БАТЧЕВОЕ ОТКЛОНЕНИЕ завершено: {results['success']} успешно, {results['failed']} ошибок")
        return results
    
    def batch_update_to_placed(self, placement_updates: List[Dict]) -> Dict[str, int]:
        """
        Батчевое обновление найденных совпадений на "Размещен" ПОСЛЕ парсинга
        
        Args:
            placement_updates: Список обновлений с данными для размещения
                              Каждый элемент должен содержать:
                              - spreadsheet_url: URL таблицы
                              - sheet_name: Название листа  
                              - row: Номер строки
                              - date: Дата публикации (опционально)
                              
        Returns:
            Словарь с результатами: {'success': count, 'failed': count}
        """
        if not placement_updates:
            thread_print("⚠️ Нет данных для батчевого размещения")
            return {'success': 0, 'failed': 0}
        
        if not self.gc:
            thread_print("❌ Google Sheets API не настроен")
            return {'success': 0, 'failed': len(placement_updates)}
        
        thread_print(f"🚀 БАТЧЕВОЕ РАЗМЕЩЕНИЕ {len(placement_updates)} найденных совпадений")
        
        # Группируем обновления по таблицам и листам
        grouped_updates = {}
        for update in placement_updates:
            key = (update['spreadsheet_url'], update['sheet_name'])
            if key not in grouped_updates:
                grouped_updates[key] = []
            grouped_updates[key].append(update)
        
        results = {'success': 0, 'failed': 0}
        
        # Обрабатываем каждую группу (таблица + лист)
        for (spreadsheet_url, sheet_name), sheet_updates in grouped_updates.items():
            try:
                thread_print(f"📋 Размещаем в листе '{sheet_name}': {len(sheet_updates)} записей")
                
                # Открываем таблицу и лист
                spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
                spreadsheet = self.gc.open_by_key(spreadsheet_id)
                worksheet = spreadsheet.worksheet(sheet_name)
                
                # Получаем заголовки для определения колонок
                headers = worksheet.row_values(1)
                
                # Находим индексы нужных колонок
                status_col = None
                date_col = None
                
                for i, header in enumerate(headers, 1):
                    if header == "Статус":
                        status_col = i
                    elif header == "Дата публикации":
                        date_col = i
                
                if not status_col:
                    thread_print(f"❌ Колонка 'Статус' не найдена в листе '{sheet_name}'")
                    results['failed'] += len(sheet_updates)
                    continue
                
                # Подготавливаем данные для батчевого обновления
                batch_data = []
                
                for update in sheet_updates:
                    row_number = update['row']
                    publication_date = update.get('date')
                    
                    # Обновление статуса на "Размещен"
                    batch_data.append({
                        'range': f'{self._get_column_letter(status_col)}{row_number}',
                        'values': [['Размещен']]
                    })
                    
                    # Обновление даты если указана
                    if publication_date and date_col:
                        batch_data.append({
                            'range': f'{self._get_column_letter(date_col)}{row_number}',
                            'values': [[publication_date]]
                        })
                
                # Выполняем батчевое обновление
                if batch_data:
                    worksheet.batch_update(batch_data)
                    
                    thread_print(f"✅ Лист '{sheet_name}': размещено {len(sheet_updates)} записей")
                    results['success'] += len(sheet_updates)
                else:
                    thread_print(f"⚠️ Лист '{sheet_name}': нет данных для размещения")
                
            except Exception as e:
                thread_print(f"❌ Ошибка батчевого размещения в листе '{sheet_name}': {e}")
                results['failed'] += len(sheet_updates)
        
        thread_print(f"🎯 БАТЧЕВОЕ РАЗМЕЩЕНИЕ завершено: {results['success']} успешно, {results['failed']} ошибок")
        return results
    
    def _get_column_letter(self, col_num: int) -> str:
        """Преобразует номер колонки в букву (1=A, 2=B, и т.д.)"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord('A')) + result
            col_num //= 26
        return result 