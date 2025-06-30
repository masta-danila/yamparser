import sys
import os
import time
import logging
from threading import Thread, Lock
from typing import List, Dict, Any
from reviews_parser import get_reviews_page
from profile_manager import SimpleProfileManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отключаем избыточные логи от сторонних библиотек
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.storage').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.modifier').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.handler').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.proxy').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)

# Оставляем наш логгер на уровне INFO
logger.setLevel(logging.INFO)

# Блокировка для создания драйверов
driver_creation_lock = Lock()

def parse_urls(urls: List[str], num_workers: int = 4) -> Dict[str, Any]:
    """
    Парсит список URL-ов в параллельном режиме
    
    Args:
        urls: Список URL-ов для парсинга
        num_workers: Количество параллельных потоков (по умолчанию 4)
    
    Returns:
        Словарь с результатами парсинга
    """
    if not urls:
        logger.error("Список URL-ов пустой")
        return {"success": False, "error": "Empty URLs list"}
    
    # Ограничиваем количество воркеров количеством URL-ов
    actual_workers = min(num_workers, len(urls))
    logger.info(f"Запуск парсинга {len(urls)} URL-ов в {actual_workers} потоков")
    
    # Инициализация менеджера профилей
    profile_manager = SimpleProfileManager()
    
    # Результаты для каждого потока
    results = {}
    threads = []
    
    def process_single_url(url: str, worker_id: int, delay: int = 0):
        """Обрабатывает один URL в отдельном потоке"""
        # Отключаем логи selenium-wire для этого потока
        logging.getLogger('seleniumwire').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.storage').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.modifier').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.handler').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.proxy').setLevel(logging.WARNING)
        
        if delay > 0:
            time.sleep(delay)
        
        logger.info(f"Поток {worker_id}: Начало обработки {url}")
        start_time = time.time()
        
        # Создание профиля
        with driver_creation_lock:
            profile_path, is_new = profile_manager.get_available_profile("mobile")
        
        try:
            # Запуск парсинга
            result = get_reviews_page(
                url=url,
                device_type="mobile",
                wait_time=3,
                max_days_back=10,
                max_reviews_limit=2000,
                use_proxy=True
            )
            
            execution_time = time.time() - start_time
            results[f"worker_{worker_id}"] = {
                "url": url,
                "result": result,
                "execution_time": execution_time,
                "profile_path": profile_path,
                "success": True
            }
            
            logger.info(f"Поток {worker_id}: Завершен за {execution_time:.1f}с")
            
        except Exception as e:
            execution_time = time.time() - start_time
            results[f"worker_{worker_id}"] = {
                "url": url,
                "error": str(e),
                "execution_time": execution_time,
                "profile_path": profile_path,
                "success": False
            }
            logger.error(f"Поток {worker_id}: Ошибка - {e}")
        
        finally:
            # Освобождение профиля
            profile_manager.release_profile(profile_path)
    
    # Запуск потоков с задержками
    start_time = time.time()
    
    for i in range(actual_workers):
        if i < len(urls):
            delay = i * 2  # Задержка 0, 2, 4, 6 секунд
            thread = Thread(
                target=process_single_url,
                args=(urls[i], i + 1, delay)
            )
            threads.append(thread)
            thread.start()
    
    # Ожидание завершения всех потоков
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Подготовка итогового отчета
    successful_workers = sum(1 for r in results.values() if r.get("success", False))
    failed_workers = len(results) - successful_workers
    
    summary = {
        "total_urls": len(urls),
        "workers_used": actual_workers,
        "successful_workers": successful_workers,
        "failed_workers": failed_workers,
        "total_execution_time": total_time,
        "results": results
    }
    
    # Итоговый отчет
    logger.info(f"ИТОГИ: {successful_workers}/{actual_workers} успешно за {total_time:.1f}с")
    
    return summary


if __name__ == "__main__":
    # Пример использования - вы можете изменить эти данные
    
    # Тестовые URL-ы
    test_urls = [
        "https://yandex.ru/maps/org/la_bottega_siciliana/61925386633/reviews/",
        "https://yandex.ru/maps/org/tulskiy_gosudarstvenny_tsirk/1100333178/reviews/", 
        "https://yandex.ru/maps/org/novikov/1254142092/reviews/",
        "https://yandex.ru/maps/org/okhotny_ryad/1064113182/reviews/"
    ]
    # Количество потоков
    workers_count = 2
    
    # Запуск парсинга
    logger.info("Запуск параллельного парсера...")
    results = parse_urls(test_urls, workers_count)
    
    # Вывод дополнительной статистики
    if results.get("results"):
        print("\n" + "=" * 60)
        print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")
        print("=" * 60)
        
        for worker_id, result in results["results"].items():
            print(f"\n{worker_id.upper()}:")
            print(f"  URL: {result['url']}")
            print(f"  Статус: {'УСПЕХ' if result.get('success') else 'ОШИБКА'}")
            print(f"  Время: {result['execution_time']:.1f} секунд")
            if not result.get("success"):
                print(f"  Ошибка: {result.get('error', 'Неизвестная ошибка')}") 