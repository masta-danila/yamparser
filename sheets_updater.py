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
                           publication_date: Optional[str] = None) -> bool:
        """
        Обновляет статус отзыва в Google Sheets
        
        Args:
            spreadsheet_url: URL таблицы Google Sheets
            sheet_name: Название листа
            row_number: Номер строки для обновления (1-based)
            new_status: Новый статус ("Размещен")
            publication_date: Дата публикации (опционально)
            
        Returns:
            True если обновление успешно, False иначе
        """
        if not self.gc:
            thread_print("❌ Google Sheets API не настроен")
            return False
        
        try:
            # Открываем таблицу
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
                return False
            
            # Обновляем статус
            worksheet.update_cell(row_number, status_col, new_status)
            thread_print(f"✅ Статус обновлен: лист '{sheet_name}', строка {row_number} -> '{new_status}'")
            
            # Обновляем дату публикации если указана
            if publication_date and date_col:
                worksheet.update_cell(row_number, date_col, publication_date)
                thread_print(f"✅ Дата публикации обновлена: строка {row_number} -> '{publication_date}'")
            
            return True
            
        except Exception as e:
            thread_print(f"❌ Ошибка обновления статуса: {e}")
            return False
    
    def batch_update_reviews(self, updates: List[Dict]) -> Dict[str, int]:
        """
        Пакетное обновление статусов отзывов
        
        Args:
            updates: Список словарей с информацией об обновлениях
                    Каждый словарь должен содержать:
                    - spreadsheet_url: URL таблицы
                    - sheet_name: Название листа
                    - row: Номер строки
                    - status: Новый статус
                    - date: Дата публикации (опционально)
        
        Returns:
            Словарь с результатами: {'success': count, 'failed': count}
        """
        if not updates:
            thread_print("⚠️ Нет обновлений для выполнения")
            return {'success': 0, 'failed': 0}
        
        results = {'success': 0, 'failed': 0}
        
        thread_print(f"📝 Начинаем пакетное обновление {len(updates)} записей...")
        
        for i, update in enumerate(updates, 1):
            try:
                success = self.update_review_status(
                    spreadsheet_url=update['spreadsheet_url'],
                    sheet_name=update['sheet_name'],
                    row_number=update['row'],
                    new_status=update['status'],
                    publication_date=update.get('date')
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                thread_print(f"📊 Прогресс: {i}/{len(updates)} ({results['success']} успешно, {results['failed']} ошибок)")
                
            except Exception as e:
                results['failed'] += 1
                thread_print(f"❌ Ошибка обновления записи {i}: {e}")
        
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