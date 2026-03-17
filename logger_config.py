"""
Конфигурация логирования для парсера
Создает логи в формате YYYY-MM-DD.txt в папке logs/
"""

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

def setup_logging():
    """Настройка логирования с ротацией по дням"""
    
    # Создаем папку для логов
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Имя файла с текущей датой в формате YYYY-MM-DD.txt
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{current_date}.txt")
    
    # Настройка форматирования для ФАЙЛА (упрощенный)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка форматирования для КОНСОЛИ (упрощенный)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Обработчик для файла (ротация каждый день в полночь)
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Хранить логи за 30 дней
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Обработчик для консоли (если запускаем вручную)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Настройка root logger - отключаем все по умолчанию
    logging.basicConfig(
        level=logging.WARNING,  # Повышаем уровень чтобы блокировать INFO от библиотек
        handlers=[]  # Убираем обработчики из root
    )
    
    # НАСТРОЙКА ТОЛЬКО ДЛЯ НАШИХ МОДУЛЕЙ
    our_modules = [
        'integrated_parser', 'reviews_parser', 'google_sheets_reader', 
        'sheets_updater', 'text_matcher', 'thread_logger', 'logger_config',
        'driver_manager', 'data_processor'
    ]
    
    for module_name in our_modules:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(logging.INFO)
        module_logger.addHandler(file_handler)
        # НЕ добавляем console_handler - пусть только в файл
        module_logger.propagate = False  # Не передавать в root logger
    
    # Специально для thread_logger добавляем консольный вывод
    thread_logger = logging.getLogger('thread_logger')
    thread_logger.addHandler(console_handler)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Логирование настроено. Файл: {log_file}")
    
    return logger

def get_logger(name):
    """Получить логгер для модуля"""
    return logging.getLogger(name)