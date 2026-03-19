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
                # Нормализуем заголовки (убираем пробелы по краям) — "Дата публикации " -> "Дата публикации"
                headers = [str(h).strip() for h in headers]
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
            
        except ValueError:
            # Ошибка валидации колонок — пробрасываем, чтобы показать реальную причину
            raise
        except Exception as e:
            print(f"❌ Ошибка чтения листа '{sheet_name}': {e}")
            return pd.DataFrame()
    
    def validate_columns(self, df: pd.DataFrame, sheet_name: str):
        """Валидация наличия обязательных колонок. URL берётся из колонки Ссылка или URL."""
        required_columns = [
            "Текст отзыва",
            "Дата публикации",
            "Статус"
        ]
        url_columns = ["Ссылка", "URL"]

        # Получаем текущие колонки в листе
        current_columns = list(df.columns)

        # Проверяем наличие хотя бы одной колонки с URL
        has_url_column = any(col in current_columns for col in url_columns)
        if not has_url_column:
            missing_columns = ["Ссылка или URL"]
        else:
            missing_columns = []

        # Проверяем наличие остальных обязательных колонок
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
            
            needed = required_columns + ["Ссылка или URL (хотя бы одна)"]
            error_msg += f"\n💡 Необходимые колонки:\n"
            for i, col in enumerate(needed, 1):
                error_msg += f"   {i}. '{col}'\n"
            
            print(error_msg)
            raise ValueError(f"Лист '{sheet_name}' не содержит все обязательные колонки")
        else:
            print(f"✅ Все обязательные колонки найдены в листе '{sheet_name}'")
    
    def check_missing_columns(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """Проверка недостающих колонок без исключения. URL — из Ссылка или URL."""
        required_columns = [
            "Текст отзыва",
            "Дата публикации",
            "Статус"
        ]
        url_columns = ["Ссылка", "URL"]

        current_columns = list(df.columns)
        missing_columns = []

        if not any(col in current_columns for col in url_columns):
            missing_columns.append("Ссылка или URL")

        for required_col in required_columns:
            if required_col not in current_columns:
                missing_columns.append(required_col)

        return missing_columns
    
    def check_review_data(self, df: pd.DataFrame, sheet_name: str):
        """Проверка данных отзывов в листе"""
        if df.empty:
            print(f"⚠️ Лист '{sheet_name}' пуст")
            return
        
        # Проверяем количество строк
        total_rows = len(df)
        print(f"📊 Всего строк в листе '{sheet_name}': {total_rows}")
        
        # Проверяем заполненность ключевых колонок
        if 'Ссылка' in df.columns:
            non_empty_links = df['Ссылка'].notna().sum()
            print(f"🔗 Строк с заполненными ссылками: {non_empty_links}")
        
        if 'Текст отзыва' in df.columns:
            non_empty_reviews = df['Текст отзыва'].notna().sum()
            print(f"📝 Строк с заполненными отзывами: {non_empty_reviews}")
        
        if 'Статус' in df.columns:
            status_counts = df['Статус'].value_counts()
            print(f"📈 Статистика по статусам:")
            for status, count in status_counts.items():
                print(f"   • {status}: {count}")
    
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
                    print(f"✅ Структура листа '{sheet_name}' корректна - все обязательные колонки найдены")
                    
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