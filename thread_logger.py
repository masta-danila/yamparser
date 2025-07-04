"""
Модуль для логирования с префиксом потока
"""
import threading


def get_thread_prefix() -> str:
    """Возвращает префикс с именем текущего потока для логов"""
    thread_name = threading.current_thread().name
    if thread_name == "MainThread":
        return "[MAIN]"
    
    # Извлекаем номер потока из имени типа "Thread-1 (process_url_batch)"
    if "Thread-" in thread_name:
        # Ищем номер после "Thread-"
        import re
        match = re.search(r'Thread-(\d+)', thread_name)
        if match:
            thread_num = match.group(1)
            return f"[THREAD-{thread_num}]"
    
    # Если формат не распознан, возвращаем как есть
    return f"[{thread_name.upper()}]"


def thread_print(message: str, end: str = '\n'):
    """Печать сообщения с префиксом потока"""
    print(f"{get_thread_prefix()} {message}", end=end)


def thread_log(message: str):
    """Алиас для thread_print для совместимости"""
    thread_print(message) 