"""
Скрипт для чтения данных из всех листов Google Sheets
Поддерживает несколько методов: gspread, Google API, публичный CSV
"""

import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import os
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import re

class GoogleSheetsReader:
    """Класс для чтения данных из Google Sheets"""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Инициализация читателя Google Sheets
        
        Args:
            credentials_file: Путь к JSON файлу с учетными данными сервисного аккаунта
        """
        self.credentials_file = credentials_file
        self.gc = None
        self.service = None
        
        if credentials_file:
            self._setup_credentials()
    
    def _setup_credentials(self):
        """Настройка учетных данных для Google API"""
        try:
            # Настройка для gspread
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(creds)
            
            # Настройка для Google Sheets API
            self.service = build('sheets', 'v4', credentials=creds)
            
            print("✅ Учетные данные настроены успешно")
            
        except Exception as e:
            print(f"❌ Ошибка настройки учетных данных: {e}")
            print("💡 Убедитесь, что файл с учетными данными существует и доступен")
    
    def extract_spreadsheet_id(self, url: str) -> str:
        """Извлечение ID таблицы из URL"""
        # Извлекаем ID из URL вида: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Не удалось извлечь ID таблицы из URL")
    

    
    def get_all_sheet_names_api(self, spreadsheet_id: str) -> List[str]:
        """Получение списка всех листов через Google Sheets API"""
        if not self.service:
            raise ValueError("Google Sheets API не настроен. Укажите credentials_file")
        
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            
            sheet_names = []
            for sheet in sheets:
                sheet_name = sheet['properties']['title']
                sheet_names.append(sheet_name)
                print(f"📄 Найден лист: {sheet_name}")
            
            return sheet_names
            
        except Exception as e:
            print(f"❌ Ошибка получения списка листов: {e}")
            return []
    
    def read_sheet_api(self, spreadsheet_id: str, sheet_name: str, validate_columns: bool = True) -> pd.DataFrame:
        """Чтение конкретного листа через Google Sheets API"""
        if not self.service:
            raise ValueError("Google Sheets API не настроен. Укажите credentials_file")
        
        try:
            # Читаем все данные с листа
            range_name = f"'{sheet_name}'"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print(f"⚠️ Лист '{sheet_name}' пуст")
                return pd.DataFrame()
            
            # Получаем заголовки и данные
            headers = values[0] if values else []
            data_rows = values[1:] if len(values) > 1 else []
            
            # Создаем DataFrame с правильным количеством колонок
            if headers:
                # Дополняем короткие строки пустыми значениями до длины заголовков
                normalized_data = []
                for row in data_rows:
                    # Дополняем строку до нужной длины
                    while len(row) < len(headers):
                        row.append('')
                    # Обрезаем если строка длиннее заголовков
                    normalized_data.append(row[:len(headers)])
                
                df = pd.DataFrame(normalized_data, columns=headers)
            else:
                df = pd.DataFrame()
            
            # Валидация колонок (если требуется)
            if validate_columns and not df.empty:
                self.validate_columns(df, sheet_name)
            
            if not df.empty:
                print(f"✅ Загружено {len(df)} строк с листа '{sheet_name}'")
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка чтения листа '{sheet_name}': {e}")
            return pd.DataFrame()
    
    def validate_columns(self, df: pd.DataFrame, sheet_name: str):
        """Валидация наличия обязательных колонок"""
        required_columns = [
            "Ссылка",
            "Текст отзыва",
            "Дата публикации",
            "Статус"
        ]
        
        # Получаем текущие колонки в листе
        current_columns = list(df.columns)
        
        # Проверяем наличие всех обязательных колонок
        missing_columns = []
        for required_col in required_columns:
            if required_col not in current_columns:
                missing_columns.append(required_col)
        
        if missing_columns:
            error_msg = f"❌ ОШИБКА: В листе '{sheet_name}' отсутствуют обязательные колонки:\n"
            for i, col in enumerate(missing_columns, 1):
                error_msg += f"   {i}. '{col}'\n"
            
            error_msg += f"\n📋 Текущие колонки в листе ({len(current_columns)}):\n"
            for i, col in enumerate(current_columns, 1):
                error_msg += f"   {i}. '{col}'\n"
            
            error_msg += f"\n💡 Необходимые колонки ({len(required_columns)}):\n"
            for i, col in enumerate(required_columns, 1):
                error_msg += f"   {i}. '{col}'\n"
            
            print(error_msg)
            raise ValueError(f"Лист '{sheet_name}' не содержит все обязательные колонки")
        
        print(f"✅ Структура листа '{sheet_name}' корректна - все {len(required_columns)} колонок найдены")
    
    def check_missing_columns(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """Проверка недостающих колонок без вызова исключения"""
        required_columns = [
            "Ссылка",
            "Текст отзыва",
            "Дата публикации",
            "Статус"
        ]
        
        current_columns = list(df.columns)
        missing_columns = []
        
        for required_col in required_columns:
            if required_col not in current_columns:
                missing_columns.append(required_col)
        
        return missing_columns
    
    def check_review_data(self, df: pd.DataFrame, sheet_name: str):
        """Проверка данных в листе: проверка заполненности обязательных полей только в строках с ссылками"""
        if df.empty:
            return
        
        # Проверяем наличие нужных колонок
        required_filled_columns = ['Ссылка', 'Текст отзыва', 'Статус']
        missing_cols = [col for col in required_filled_columns if col not in df.columns]
        
        if missing_cols:
            print(f"⚠️ В листе '{sheet_name}' отсутствуют колонки для проверки данных: {missing_cols}")
            return
        
        # Ищем строки с заполненными ссылками, но незаполненными другими полями
        problem_rows = []
        rows_with_links = 0
        
        for index, row in df.iterrows():
            status = str(row['Статус']).strip()
            link = str(row['Ссылка']).strip()
            review_text = str(row['Текст отзыва']).strip()
            
            # Проверяем только строки с заполненными ссылками
            if link and link != 'nan' and link != '':
                rows_with_links += 1
                empty_fields = []
                
                # Проверяем заполненность других обязательных полей
                if not review_text or review_text == 'nan' or review_text == '':
                    empty_fields.append('Текст отзыва')
                    
                if not status or status == 'nan' or status == '':
                    empty_fields.append('Статус')
                
                # Если есть незаполненные поля, добавляем в проблемные строки
                if empty_fields:
                    problem_rows.append({
                        'row': index + 2,  # +2 потому что индекс с 0 + заголовок
                        'link': link,
                        'empty_fields': empty_fields
                    })
        
        # Выводим результаты проверки
        if rows_with_links == 0:
            print(f"ℹ️ В листе '{sheet_name}' нет строк с заполненными ссылками")
        elif problem_rows:
            print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: В листе '{sheet_name}' найдено {len(problem_rows)} строк с ссылками, но незаполненными обязательными полями:")
            for problem in problem_rows:
                empty_fields_str = ', '.join(problem['empty_fields'])
                print(f"   🔗 Строка {problem['row']}: {problem['link']} - не заполнено: {empty_fields_str}")
        else:
            print(f"✅ В листе '{sheet_name}' все строки с ссылками ({rows_with_links}) имеют заполненные обязательные поля")
    
    def read_all_sheets_api(self, spreadsheet_url: str, stop_on_validation_error: bool = True) -> Dict[str, pd.DataFrame]:
        """Чтение всех листов из одной Google Sheets таблицы через API"""
        spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
        
        print(f"📊 Начинаем чтение всех листов из таблицы: {spreadsheet_id}")
        
        # Получаем список всех листов
        sheet_names = self.get_all_sheet_names_api(spreadsheet_id)
        
        if not sheet_names:
            print("❌ Не найдено ни одного листа")
            return {}
        
        # Читаем все листы
        all_data = {}
        validation_errors = []
        
        for sheet_name in sheet_names:
            print(f"\n📖 Читаем лист: {sheet_name}")
            try:
                # Сначала читаем без валидации
                df = self.read_sheet_api(spreadsheet_id, sheet_name, validate_columns=False)
                if df.empty:
                    continue
                
                # Проверяем недостающие колонки
                missing_columns = self.check_missing_columns(df, sheet_name)
                
                if missing_columns:
                    # Показываем какие колонки отсутствуют
                    print(f"❌ В листе '{sheet_name}' отсутствуют колонки ({len(missing_columns)}):")
                    for i, col in enumerate(missing_columns, 1):
                        print(f"   {i}. '{col}'")
                    
                    validation_errors.append((sheet_name, missing_columns))
                    
                    if stop_on_validation_error:
                        print(f"\n🛑 ОСТАНОВКА: Обнаружена ошибка валидации в листе '{sheet_name}'")
                        print(f"⚠️ Для продолжения работы необходимо исправить структуру таблицы")
                        raise ValueError(f"Лист '{sheet_name}' не содержит все обязательные колонки")
                    else:
                        print(f"⚠️ Пропускаем лист '{sheet_name}' из-за ошибки валидации")
                        continue
                else:
                    # Все колонки на месте
                    print(f"✅ Структура листа '{sheet_name}' корректна - все 4 обязательные колонки найдены")
                    
                    # Проверяем данные в листе
                    self.check_review_data(df, sheet_name)
                    
                    all_data[sheet_name] = df
                    
            except Exception as e:
                print(f"❌ Общая ошибка чтения листа '{sheet_name}': {e}")
                continue
        
        if validation_errors and not stop_on_validation_error:
            print(f"\n⚠️ ВНИМАНИЕ: Обнаружены ошибки валидации в {len(validation_errors)} листах:")
            for sheet_name, missing_cols in validation_errors:
                print(f"   - {sheet_name}: отсутствуют {len(missing_cols)} колонок")
        
        print(f"\n🎉 Успешно прочитано {len(all_data)} листов")
        return all_data
    
    def process_multiple_spreadsheets(self, spreadsheet_urls: List[str], stop_on_validation_error: bool = True) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Обработка нескольких Google Sheets таблиц"""
        if not spreadsheet_urls:
            print("❌ Не предоставлено ни одной ссылки на таблицу")
            return {}
        
        print(f"🚀 Начинаем обработку {len(spreadsheet_urls)} таблиц")
        print("=" * 60)
        
        all_spreadsheets_data = {}
        total_sheets = 0
        total_rows = 0
        
        for i, url in enumerate(spreadsheet_urls, 1):
            try:
                spreadsheet_id = self.extract_spreadsheet_id(url)
                print(f"\n📋 ТАБЛИЦА {i}/{len(spreadsheet_urls)}: {spreadsheet_id}")
                print("-" * 50)
                
                # Читаем все листы из текущей таблицы
                spreadsheet_data = self.read_all_sheets_api(url, stop_on_validation_error)
                
                if spreadsheet_data:
                    all_spreadsheets_data[spreadsheet_id] = spreadsheet_data
                    sheets_count = len(spreadsheet_data)
                    rows_count = sum(len(df) for df in spreadsheet_data.values())
                    total_sheets += sheets_count
                    total_rows += rows_count
                    
                    print(f"✅ Таблица {spreadsheet_id}: {sheets_count} листов, {rows_count} строк")
                else:
                    print(f"⚠️ Таблица {spreadsheet_id}: нет данных для обработки")
                    
            except Exception as e:
                print(f"❌ Ошибка обработки таблицы {i}: {e}")
                continue
        
        # Итоговая статистика
        print(f"\n🎯 ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 60)
        print(f"📊 Обработано таблиц: {len(all_spreadsheets_data)}/{len(spreadsheet_urls)}")
        print(f"📄 Всего листов: {total_sheets}")
        print(f"📝 Всего строк: {total_rows}")
        
        if all_spreadsheets_data:
            print(f"\n📋 Детальная статистика по таблицам:")
            for spreadsheet_id, sheets_data in all_spreadsheets_data.items():
                sheets_count = len(sheets_data)
                rows_count = sum(len(df) for df in sheets_data.values())
                print(f"  📊 {spreadsheet_id}: {sheets_count} листов, {rows_count} строк")
        
        return all_spreadsheets_data
    
    def read_sheet_gspread(self, spreadsheet_url: str, sheet_name: str) -> pd.DataFrame:
        """Чтение конкретного листа через gspread"""
        if not self.gc:
            raise ValueError("gspread не настроен. Укажите credentials_file")
        
        try:
            # Открываем таблицу
            spreadsheet = self.gc.open_by_url(spreadsheet_url)
            
            # Открываем конкретный лист
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Получаем все данные
            data = worksheet.get_all_records()
            
            if not data:
                print(f"⚠️ Лист '{sheet_name}' пуст")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Валидация колонок
            self.validate_columns(df, sheet_name)
            
            print(f"✅ Загружено {len(df)} строк с листа '{sheet_name}'")
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка чтения листа '{sheet_name}': {e}")
            return pd.DataFrame()
    
    def read_all_sheets_gspread(self, spreadsheet_url: str) -> Dict[str, pd.DataFrame]:
        """Чтение всех листов из Google Sheets через gspread"""
        if not self.gc:
            raise ValueError("gspread не настроен. Укажите credentials_file")
        
        try:
            print(f"📊 Начинаем чтение всех листов через gspread")
            
            # Открываем таблицу
            spreadsheet = self.gc.open_by_url(spreadsheet_url)
            
            # Получаем список всех листов
            worksheets = spreadsheet.worksheets()
            
            print(f"📄 Найдено листов: {len(worksheets)}")
            
            all_data = {}
            for worksheet in worksheets:
                sheet_name = worksheet.title
                print(f"\n📖 Читаем лист: {sheet_name}")
                
                try:
                    data = worksheet.get_all_records()
                    
                    if data:
                        df = pd.DataFrame(data)
                        all_data[sheet_name] = df
                        print(f"✅ Загружено {len(df)} строк")
                    else:
                        print(f"⚠️ Лист пуст")
                        
                except Exception as e:
                    print(f"❌ Ошибка чтения листа '{sheet_name}': {e}")
                    continue
            
            print(f"\n🎉 Успешно прочитано {len(all_data)} листов")
            return all_data
            
        except Exception as e:
            print(f"❌ Ошибка при чтении таблицы: {e}")
            return {}
    
    def save_to_excel(self, data: Dict[str, pd.DataFrame], filename: str = 'google_sheets_data.xlsx'):
        """Сохранение данных в Excel файл"""
        if not data:
            print("❌ Нет данных для сохранения")
            return
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                for sheet_name, df in data.items():
                    # Очищаем название листа для Excel
                    clean_name = re.sub(r'[\\/*?:"<>|]', '_', sheet_name)[:31]
                    df.to_excel(writer, sheet_name=clean_name, index=False)
            
            print(f"💾 Данные сохранены в Excel файл: {filename}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения в Excel: {e}")


def main():
    """Основная функция для демонстрации использования"""
    
    # Список URL таблиц для обработки
    SPREADSHEET_URLS = [
        "https://docs.google.com/spreadsheets/d/1prLF8cF6wpdGkOdgDyZLZ8MHbG0NbdfN_rVQ-ilYX3Y/edit?gid=1731264931#gid=1731264931",
        "https://docs.google.com/spreadsheets/d/10v9VFoD6g-RRLLs_nG4PksfV_ZVLL5klxeTOD3WCrok/edit?gid=1998608722#gid=1998608722"
    ]
    
    print("🚀 Google Sheets Reader - Обработка нескольких таблиц")
    print("=" * 60)
    
    # Авторизованное чтение нескольких таблиц
    CREDENTIALS_FILE = 'credentials.json'  # Путь к вашему файлу
    
    if os.path.exists(CREDENTIALS_FILE):
        print(f"🔑 Используем учетные данные: {CREDENTIALS_FILE}")
        
        # Создаем читатель с авторизацией
        auth_reader = GoogleSheetsReader(CREDENTIALS_FILE)
        
        # Обрабатываем несколько таблиц (не останавливаемся на ошибках валидации)
        all_spreadsheets_data = auth_reader.process_multiple_spreadsheets(SPREADSHEET_URLS, stop_on_validation_error=False)
        
        if all_spreadsheets_data:
            print(f"\n💾 Данные успешно обработаны из {len(all_spreadsheets_data)} таблиц")
            # Сохранение данных отключено
            # auth_reader.save_to_excel(all_data_api)
        else:
            print("❌ Не удалось прочитать данные ни из одной таблицы")
    else:
        print(f"⚠️ Файл учетных данных не найден: {CREDENTIALS_FILE}")


def process_custom_spreadsheets(spreadsheet_urls: List[str], credentials_file: str = 'credentials.json'):
    """Функция для обработки пользовательского списка таблиц"""
    if not os.path.exists(credentials_file):
        print(f"❌ Файл учетных данных не найден: {credentials_file}")
        return
    
    print(f"🚀 Обработка {len(spreadsheet_urls)} пользовательских таблиц")
    print("=" * 60)
    
    # Создаем читатель с авторизацией
    reader = GoogleSheetsReader(credentials_file)
    
    # Обрабатываем таблицы
    results = reader.process_multiple_spreadsheets(spreadsheet_urls)
    
    return results


if __name__ == "__main__":
    main() 